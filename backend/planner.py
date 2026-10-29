"""Deterministic Task 26 candidates, without feasibility filtering or ranking.

Use generate_candidates for a serializable result, or iter_itinerary_candidates
for lazy traversal of larger catalogs. Neither API truncates candidate options.
"""

from collections.abc import Iterator
from hashlib import sha256
import json
import re

from backend.mock_data import get_mock_venues, load_mock_venues
from backend.models import (
    CandidateGenerationResult, CandidateItinerary, CandidateStop, OutingRequest,
    PlanningError, ScheduledEvent, Venue, fixed_times_compatible,
)


def supports_location(location: str) -> bool:
    """Shared coverage check for generation and independent candidate evaluation."""
    return re.fullmatch(r"baltimore(?:\s*,?\s*(?:md|maryland))?", location, re.IGNORECASE) is not None


def _pools(request: OutingRequest) -> tuple[list[list[Venue | ScheduledEvent]], list[PlanningError]]:
    if not supports_location(request.location):
        return [], [PlanningError(code="unsupported_location", field="location",
                                  message="The fictional catalog only covers Baltimore.")]
    records = load_mock_venues()
    by_activity = {activity: get_mock_venues(activity, event_date=request.date, venues=records)
                   for activity in dict.fromkeys(request.activities)}
    errors = [PlanningError(code="no_availability", field="activities",
                            message=f"No mock records for {activity.value} on "
                                    f"{request.date or 'a flexible day'}. No activity was substituted.")
              for activity, pool in by_activity.items() if not pool]
    return [by_activity[activity] for activity in request.activities], errors


def _walk(request: OutingRequest, pools: list[list[Venue | ScheduledEvent]]) -> Iterator[CandidateItinerary]:
    route: list[Venue | ScheduledEvent] = []
    used: set[str] = set()
    request_identity = request.model_dump(mode="json", exclude={"calendarTimezone","explicitStart","explicitEnd","destinationContext","people","activityIntents"})

    def visit(index: int) -> Iterator[CandidateItinerary]:
        if index == len(pools):
            # Encode boundaries and request context so IDs are stable and unambiguous.
            identity = [request_identity, [v.id for v in route]]
            candidate_id = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            venues = [v.model_copy(deep=True) for v in route]
            stops = [CandidateStop(
                venue=v, start=v.start if isinstance(v, ScheduledEvent) else None,
                end=v.start + v.duration if isinstance(v, ScheduledEvent) and v.duration is not None else None,
            ) for v in venues]
            yield CandidateItinerary(id=f"candidate-{candidate_id}", venues=venues, stops=stops,
                                     people=request.people, date=request.date,
                                     allowRevisits=request.allowRevisits)
            return
        for venue in pools[index]:
            if not request.allowRevisits and venue.id in used:
                continue
            route.append(venue)
            if fixed_times_compatible(route):
                if not request.allowRevisits:
                    used.add(venue.id)
                yield from visit(index + 1)
                if not request.allowRevisits:
                    used.remove(venue.id)
            route.pop()

    yield from visit(0)


def iter_itinerary_candidates(request: OutingRequest) -> Iterator[CandidateItinerary]:
    """Yield all candidates in fixture order with O(pool sizes + route depth) memory.

    Invalid input belongs at the OutingRequest validation boundary. A supported
    request with missing data or incompatible identities/times yields nothing;
    generate_candidates provides structured explanations for these empty cases.
    """
    pools, errors = _pools(request)
    if not errors:
        yield from _walk(request, pools)


def generate_candidates(request: OutingRequest) -> CandidateGenerationResult:
    """Collect the small shared catalog's candidates; never select a top three.

    Current fixture has three matches per activity/date and at most four stops
    (at most 81 combinations). Larger future catalogs should use the lazy API.
    Candidates are not feasible plans: budget, capacity, travel, dinner timing,
    ordinary availability and ranking are intentionally deferred to Task 27.
    """
    pools, errors = _pools(request)
    candidates = [] if errors else list(_walk(request, pools))
    if not candidates and not errors:
        errors = [PlanningError(code="infeasible", field="activities",
                                message="No combination preserves record identity and fixed event order/times.")]
    return CandidateGenerationResult(
        request=request, candidates=candidates, errors=errors,
        message=("Unranked fictional candidates; feasibility has not been evaluated."
                 if candidates else "No candidates available for the complete request."),
    )
