"""Pure, deterministic candidate relevance and conservative entity deduplication.

Input is already geographically checked. No transport/authentication, external
lookups, ranking, scheduling, persistence or fictional replacements.
"""
from collections import Counter
from copy import deepcopy
from itertools import groupby
import json
import re
from typing import Literal

from pydantic import Field, ValidationError

from backend.models import ActivityType, ContractModel
from backend.venue_geography import distance_m, normalized
from backend.venue_models import VenueFacts
from backend.venue_normalization import _assign, _supplied

# Specific provider evidence only. Broad types (stadium, park, theater) do not
# establish a particular sport, trail, picnic facility or kind of performance.
RULES = {
    'food': ({'restaurant', 'food_court', 'diner', 'cafeteria', 'meal_takeaway'}, r'restaurant|diner|bistro|grill|pizzeria|food court'),
    'drinks': ({'bar', 'pub', 'brewpub', 'beer_garden', 'night_club', 'wine_bar', 'cocktail_bar', 'sports_bar', 'lounge_bar', 'bar_and_grill', 'brewery'}, r'bar|pub|brewery|brewpub|taproom|cocktail|tavern'),
    'movie': ({'movie_theater'}, r'cinema|cinemas|movie theater|movie theatre|multiplex'),
    'coffee': ({'cafe', 'coffee_shop', 'coffee_stand', 'cat_cafe', 'dog_cafe'}, r'coffee|cafe|café|espresso'),
    'bowling': ({'bowling_alley'}, r'bowling|bowl|lanes'),
    'arcade': ({'video_arcade'}, r'arcade|arcades'),
    'museum': ({'museum', 'art_museum', 'history_museum'}, r'museum|museums'),
    'art': ({'art_gallery', 'art_museum'}, r'art gallery|art galleries|art museum'),
    'outdoors': ({'park', 'city_park', 'state_park', 'national_park', 'botanical_garden', 'garden', 'hiking_area'}, r'park|gardens|garden|nature preserve|trail|trails'),
    'karaoke': ({'karaoke'}, r'karaoke'),
    'escape': (set(), r'escape room|escape rooms|escape game|escape games'),
    'miniGolf': ({'miniature_golf_course'}, r'mini golf|miniature golf|putt putt'),
    'shopping': ({'shopping_mall', 'department_store', 'market'}, r'mall|shopping center|shopping centre|outlet shops|marketplace'),
    'zoo': ({'zoo', 'wildlife_park'}, r'zoo|zoological|wildlife park'),
    'hiking': ({'hiking_area'}, r'hiking|trail|trails|trailhead'),
    'picnic': ({'picnic_ground', 'barbecue_area'}, r'picnic|picnic grounds'),
    'skating': ({'ice_skating_rink'}, r'skating rink|skate rink|ice rink|roller rink'),
    'baseball': (set(), r'baseball|ballpark'),
    'basketball': (set(), r'basketball'),
    'football': (set(), r'football'),
    'soccer': (set(), r'soccer|football pitch'),
    'hockey': (set(), r'hockey'),
    'sports': ({'stadium', 'arena', 'sports_complex', 'athletic_field'}, r'stadium|arena|sports complex|ballpark'),
    'concert': ({'concert_hall', 'live_music_venue', 'philharmonic_hall'}, r'concert|live music|music hall|philharmonic'),
    'theater': ({'performing_arts_theater'}, r'performing arts|playhouse|repertory theater|repertory theatre'),
    'musical': (set(), r'musical theater|musical theatre|broadway'),
    'ballet': (set(), r'ballet'),
    'opera': ({'opera_house'}, r'opera house|opera'),
    'comedy': ({'comedy_club'}, r'comedy|improv'),
}

# These types and business descriptions are affirmative evidence of a different
# purpose, not a closed-world assumption that missing types mean irrelevance.
UNRELATED_TYPES = {'dentist', 'doctor', 'hospital', 'lawyer', 'insurance_agency',
                   'real_estate_agency', 'car_dealer', 'car_repair', 'car_wash',
                   'accounting', 'bank', 'funeral_home', 'plumber', 'electrician',
                   'hair_salon', 'barber_shop', 'corporate_office', 'supplier'}
SERVICE_NAME = re.compile(r'\b(dental clinic|dental care|dental office|dentist|insurance|law firm|attorneys?|real estate|'
                          r'equipment supplier|supply store|repair shop|funeral home|'
                          r'car dealership|auto repair)\b')


class Relevance(ContractModel):
    status: Literal['strong', 'uncertain', 'mismatch']
    reason: str


class DistinctVenue(ContractModel):
    facts: VenueFacts
    # Every original identity and source observation survives, including conflicts.
    sources: list[VenueFacts]
    activities: list[ActivityType]
    relevance: dict[ActivityType, Relevance]


class QualityResult(ContractModel):
    venues: list[DistinctVenue]
    excluded_count: int
    diagnostics: dict[str, int] = Field(default_factory=dict, exclude=True, repr=False)
    stages: dict = Field(default_factory=dict, exclude=True, repr=False)


def relevance(venue: VenueFacts) -> Relevance:
    activity = venue.activity.value
    types = set(venue.providerTypes or []) | ({venue.primaryType} if venue.primaryType else set())
    expected, pattern = RULES[activity]
    matched_types = types & expected
    if activity == 'food':
        matched_types |= {t for t in types if t.endswith('_restaurant')}
    name = normalized(venue.name)
    if SERVICE_NAME.search(name) or (activity == 'bowling' and re.search(r'\bbowling green (?:park|gardens|university)\b', name)):
        # A second real activity type can contradict a misleading business name;
        # keep that mixed evidence uncertain rather than inventing confidence.
        return Relevance(status='uncertain' if matched_types else 'mismatch', reason='conflicting_business_name')
    if matched_types:
        return Relevance(status='strong', reason='matching_provider_type')
    if types & UNRELATED_TYPES:
        return Relevance(status='mismatch', reason='unrelated_business_type')
    if re.search(r'\b(?:' + pattern + r')\b', name):
        return Relevance(status='uncertain', reason='name_support_only')
    if activity == 'bowling' and ('video_arcade' in types or re.search(r'\barcades?\b', name)):
        return Relevance(status='mismatch', reason='arcade_without_bowling_evidence')
    # A narrow, mutually incompatible building type is enough to reject obvious
    # wrong searches. Broad/multi-purpose places remain uncertain.
    exclusive = {'movie_theater', 'bowling_alley', 'zoo', 'art_gallery', 'museum',
                 'video_arcade', 'comedy_club', 'miniature_golf_course'}
    incompatible = {
        'movie': exclusive - {'movie_theater'},
        'bowling': {'movie_theater', 'art_gallery', 'museum', 'zoo'},
        'zoo': {'movie_theater', 'bowling_alley', 'art_gallery'},
        'hiking': {'movie_theater', 'bowling_alley', 'video_arcade'},
        'picnic': {'movie_theater', 'bowling_alley', 'video_arcade'},
    }
    if types & incompatible.get(activity, set()):
        return Relevance(status='mismatch', reason='incompatible_venue_type')
    # Missing types can still carry explicit contradictory name evidence.
    if activity == 'movie' and re.search(r'\b(bowling alley|art gallery|miniature golf)\b', name):
        return Relevance(status='mismatch', reason='incompatible_venue_name')
    if activity == 'bowling' and re.search(r'\b(movie theater|movie theatre|cinema|dental)\b', name):
        return Relevance(status='mismatch', reason='incompatible_venue_name')
    return Relevance(status='uncertain', reason='insufficient_activity_evidence')


def _key(venue):
    return venue.model_dump_json(exclude_none=True)


def _alias(a, b):
    if (a.provider, a.evidence) != (b.provider, b.evidence):
        return False
    if a.id == b.id:
        return True
    name = normalized(a.name)
    generic = {'point_of_interest', 'establishment', 'food'}
    a_types, b_types = set(a.providerTypes or []) - generic, set(b.providerTypes or []) - generic
    # Exact full name and address (including suite/screen numbers), very close
    # coordinates, plus a shared venue-specific website URL. Names/address/point
    # alone cannot distinguish same-brand concessions or cinemas in a complex.
    # This extra corroboration is normally unavailable under today's mask: keep
    # ambiguous different IDs, rather than buying a detail lookup.
    return bool(len(name.split()) >= 2 and name == normalized(b.name)
                and a.address and b.address and normalized(a.address) == normalized(b.address)
                and re.search(r'\d', a.address)
                and a.coordinates and b.coordinates and distance_m(a.coordinates, b.coordinates) <= 10
                and a.websiteUrl and a.websiteUrl == b.websiteUrl
                and len(a.websiteUrl.path or '') > 1
                and normalized(a.websiteUrl.path or '') not in {'locations', 'stores', 'home', 'index html'}
                and (not a.primaryType or not b.primaryType or a.primaryType == b.primaryType)
                and (not a_types or not b_types or bool(a_types & b_types)))


def _merge(records):
    # Sort before merging so conflicting equal-time observations have a stable
    # choice. Newer receipts win; no null erases a known value. Atomic lists of
    # periods are never stitched into an invented opening-hours schedule.
    records = sorted(records, key=lambda v: (v.id, _key(v)))
    primary = records[0]
    payload = primary.model_dump()
    observations = {}
    for record in records:
        for path, value in _supplied(record.model_dump(exclude={'observedAt', 'id', 'activity',
                                                               'provider', 'evidence', 'resourceName'})):
            stamp = record.observedAt.get('.'.join(path))
            rank = (stamp.timestamp() if stamp else float('-inf'), _key(record))
            observations.setdefault(path, []).append((rank, value, stamp))
    for path, choices in sorted(observations.items()):
        for _, value, stamp in sorted(choices, key=lambda c: c[0], reverse=True):
            updated = deepcopy(payload)
            _assign(updated, path, value)
            try:
                VenueFacts.model_validate(updated)
            except ValidationError:
                continue  # Conflicting nested bounds/currencies remain in sources.
            payload = updated
            if stamp is not None:
                payload['observedAt']['.'.join(path)] = stamp
            else:
                payload['observedAt'].pop('.'.join(path), None)
            break
    # Types and credits are sets of independent assertions, unlike hours snapshots.
    for field in ('providerTypes', 'attributions'):
        values = [item for record in records for item in (record.model_dump()[field] or [])]
        if values:
            unique = {json.dumps(item, sort_keys=True, default=str): item for item in values}
            payload[field] = [unique[k] for k in sorted(unique)]
            contributors = [v for v in records if getattr(v, field)]
            stamps = [v.observedAt.get(field) for v in contributors]
            if all(stamp is not None for stamp in stamps):
                # Unioning an older credit/type must not give it a newer receipt.
                payload['observedAt'][field] = min(stamps)
            else:
                payload['observedAt'].pop(field, None)
    return VenueFacts.model_validate(payload)


def assess_candidates(records: list[VenueFacts], *, require_support: set[ActivityType] | None = None) -> QualityResult:
    """Geographically accepted canonical observations, in provider search order.

    Output order follows first occurrence. Group identity, fact selection and
    activity associations are independent of input order. No transitive alias
    chain can join records without pairwise corroboration.
    """
    records = [VenueFacts.model_validate(v.model_dump()) for v in records]
    diagnostics = Counter()
    groups = []
    # Primary provider identities are grouped before considering different IDs.
    ordered = sorted(enumerate(records), key=lambda item: (item[1].provider, item[1].id, _key(item[1])))
    for _, values in groupby(ordered, key=lambda item: (item[1].provider, item[1].id)):
        group = list(values)
        target = next((g for g in groups if all(_alias(a[1], b[1]) for a in g for b in group)), None)
        if target is None:
            groups.append(group)
        else:
            target.extend(group)
    venues, rejected_by_activity = [], {}
    for group in sorted(groups, key=lambda g: min(item[0] for item in g)):
        sources = sorted([item[1] for item in group], key=lambda v: (v.id, _key(v)))
        facts = _merge(sources)
        verdicts = {}
        diagnostics['duplicate_place_id'] += len(sources) - len({(v.provider, v.id) for v in sources})
        diagnostics['corroborated_alias'] += len({(v.provider, v.id) for v in sources}) - 1
        for activity in sorted({v.activity for v in sources}, key=lambda a: a.value):
            # Merge identity facts before evaluating associations: a second query
            # can supply the evidence missing from the first observation.
            candidate = VenueFacts.model_validate({**facts.model_dump(), 'activity': activity})
            verdict = relevance(candidate)
            if activity in (require_support or set()) and verdict.reason == 'insufficient_activity_evidence':
                verdict = Relevance(status='mismatch', reason='activity_evidence_required')
            diagnostics[verdict.reason] += sum(v.activity == activity for v in sources)
            if verdict.status != 'mismatch':
                verdicts[activity] = verdict
            else:
                rejected_by_activity.setdefault(activity, Counter())[verdict.reason] += 1
        if not verdicts:
            continue
        activities = list(verdicts)
        facts = VenueFacts.model_validate({**facts.model_dump(), 'activity': activities[0]})
        venues.append(DistinctVenue(facts=facts, sources=sources, activities=activities, relevance=verdicts))
    return QualityResult(venues=venues, excluded_count=len(records)-len(venues),
        stages={a.value: {"afterDeduplication": sum(any(source.activity == a for _, source in group) for group in groups),
                         "afterRelevance": sum(a in v.activities for v in venues),
                         "relevanceRejectedByReason": dict(rejected_by_activity.get(a, {})),
                         "duplicatesRemoved": sum(v.activity == a for v in records) - sum(any(source.activity == a for _, source in group) for group in groups)} for a in {v.activity for v in records}},
                         diagnostics={k: v for k, v in sorted(diagnostics.items()) if v})
