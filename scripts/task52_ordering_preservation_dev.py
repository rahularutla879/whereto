"""Explicit local development profile for the five reviewed V5.1 requests.

Normal application startup never imports this module. It accepts a supplied
extraction and runs the existing interpretation pipeline with an in-memory
provider. It issues no session, admission receipt or provider-work authority.
"""
from datetime import datetime

from backend.interpretation import InterpretationContext
from backend.journey import LIMITATION, REPHRASE, Journey
from backend.validation_phases import validate_legacy

KNOWN_LOSS = ('openai', 'journey-06', 2)


def interpret_for_development(value, *, extraction, now=None, preserve_order=False):
    class SuppliedExtraction:
        def interpret(self, text):
            if text != value.text:
                raise ValueError('Development extraction source changed')
            return extraction

    fixture = SuppliedExtraction()
    if not preserve_order:
        return validate_legacy(value, fixture, now=now).result

    from scripts.task52_v51_eval_identity import plan

    reviewed = plan()
    slot = next((s for s in reviewed['slots'] if s['source'] == value.text), None)
    if (slot is None or value.pending is not None or value.hasCurrentLocation
            or value.preferences.model_dump(exclude_defaults=True)
            or value.answers.model_dump(exclude_defaults=True)):
        raise ValueError('This development profile requires a fresh reviewed request')
    reference = datetime.fromisoformat(reviewed['successorVersionSpecification']['referenceTime'])
    fields = slot['Q1FieldExpectations']
    calendar = fields['dates_timezones']['expected']
    if ((now is not None and now != reference)
            or value.calendarTimezone not in (None, calendar['syntheticCalendarTimezone'])):
        raise ValueError('This development profile requires the reviewed calendar context')

    disposition = validate_legacy(value, fixture, now=reference)
    raw = disposition.raw_model
    result = disposition.result
    if (raw is None or raw.journey is None or not _reviewed_extraction(slot, raw)
            or not _reviewed_context(result, fields)
            or not _same_occurrences(disposition, raw)):
        return _blocked(result)

    if slot['slot'][1] == 'journey-21':
        if (result.executionStatus == 'clarification_required' and result.issues == [REPHRASE]
                and not (result.notes or result.unsupported or result.questions)
                and result.request is None and result.advancedToken is None and result.pending is None
                and result.interpretation == raw):
            return result
        return _blocked(result)

    if (result.executionStatus != 'advanced_unavailable' or result.issues != [LIMITATION]
            or result.unsupported != [LIMITATION] or result.questions or result.notes
            or result.request is not None or result.advancedToken is not None
            or result.pending is None or result.pending.interpretation != result.interpretation
            or result.pending.text != value.text or result.pending.referenceTime != reference
            or result.pending.answers.model_dump(exclude_defaults=True)):
        return _blocked(result)

    if result.interpretation == raw:
        return result

    # The only allowable difference is the exact legacy deletion of the
    # source-proven optional-coffee edge and its constrained ordering mode.
    if tuple(slot['slot']) != KNOWN_LOSS or len(raw.journey.order) != 1:
        return _blocked(result)
    dropped = raw.model_copy(deep=True)
    dropped.journey.order = []
    dropped.journey.ordering = 'unspecified'
    if result.interpretation != dropped:
        return _blocked(result)

    repaired = result.model_copy(deep=True)
    repaired.interpretation.journey = Journey.model_validate(raw.journey)
    repaired.pending.interpretation.journey = Journey.model_validate(raw.journey)
    return repaired


def _same_occurrences(disposition, raw):
    preparation = disposition.preparation
    return (preparation is not None and preparation.source_kind == 'raw_model'
            and len(preparation.mapping) == len(raw.journey.stops)
            and all(m.status == 'same_source_span' and m.original_index == m.effective_index
                    for m in preparation.mapping))


def _reviewed_context(result, fields):
    # These five requests have no manual context, departure, travel or endpoint
    # answer. The legacy default driving mode is a planner default, not AI input.
    area = fields['geography']['expected']
    calendar = fields['dates_timezones']['expected']
    return result.context == InterpretationContext(
        destination=area['destinationText'] if area else None,
        date=calendar['resolvedDateIfKnown'],
        timezone=calendar['syntheticCalendarTimezone'] if area else 'UTC',
        timezoneBasis='destination_calendar' if area else 'unknown',
        transport='driving', geography={},
    )


def _reviewed_extraction(slot, raw):
    from backend.ai import Interpretation
    from scripts.cloud_model52_semantics import evidence_failures
    from scripts.task52_ordering_v51 import inspect_order

    fields = slot['Q1FieldExpectations']
    text = slot['source']
    journey = raw.journey
    stops = sorted((fields['required_activities']['expected'] or [])
                   + (fields['optional_activities']['expected'] or []), key=lambda s: s['index'])
    named = {item['index']: item['identity'] for item in fields['exact_named_identity']['expected'] or []}
    expected_stops = [(named.get(s['index'], s['sourcePhrase']),
                       'named_place' if s['index'] in named else 'activity', s['requirement']) for s in stops]
    if ([(s.source, s.kind, s.requirement) for s in journey.stops] != expected_stops
            or evidence_failures(text, journey)):
        return False

    area = fields['geography']['expected']
    expected = Interpretation(activities=[s[0] for s in expected_stops], preferences=[],
                              date=None, budget_per_person=None, location=area['destinationText'] if area else None,
                              date_expressions=fields['dates_timezones']['expected']['expressions'])
    if raw.model_dump(exclude={'journey'}) != expected.model_dump(exclude={'journey'}):
        return False

    if journey.deadline or journey.shared_place or any(s.duration for s in journey.stops):
        return False
    if fields['return_origin']['expected']:
        if (not journey.endpoint or journey.endpoint.kind != 'origin'
                or 'return to the starting point' not in journey.endpoint.source.casefold()):
            return False
    elif journey.endpoint:
        return False

    limit = fields['whole_trip_limit']['expected']
    duration = journey.total_duration
    if limit:
        if (not duration or (duration.minutes, duration.relation) != (limit['minutes'], limit['relation'])
                or 'within three hours' not in duration.source.casefold()):
            return False
    elif duration:
        return False

    edges = {(e.before, e.after) for e in journey.order}
    if len(edges) != len(journey.order):
        return False
    proof = inspect_order(text, raw)
    if slot['slot'][1] == 'journey-21':
        return (proof['source']['category'] == 'contradictory' and not journey.order
                and not journey.order_conflict and journey.clarification
                and 'pharmacy before the bank, but the bank before the pharmacy' in journey.clarification
                and journey.clarification in text)
    order = fields['mandatory_order']['expected']
    return (proof['outcome'] == 'verified_order'
            and proof['mandatoryRequiredVisitClosure'] == order['requiredReachability']
            and proof['conditionalClosure'] == order.get('conditionalReachability', []))


def _blocked(result):
    return result.model_copy(update={
        'executionStatus': 'clarification_required', 'issues': [REPHRASE],
        'notes': [], 'unsupported': [], 'questions': [], 'request': None,
        'pending': None, 'advancedToken': None,
    })
