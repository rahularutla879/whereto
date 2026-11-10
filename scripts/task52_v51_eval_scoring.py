"""Offline three-axis evidence, not a general semantic judge or planning issuer.

Only the five reviewed V5.1 Q3 sources are accepted. Mechanical checks can find errors;
24-field independent review is always required to establish full correctness.
No HTTP, credentials, ledger writers, session constructors or model factories.
"""
from copy import deepcopy
from datetime import datetime
import json

from scripts import task52_q1 as q1
from scripts import cloud_model52 as historical
from scripts import task52_ordering_v51 as ordering
from scripts.cloud_model52_semantics import evidence_failures
from backend.ai import parse_interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.journey import LIMITATION

VERSION = '52b-v51-three-axis-offline-v1'


def assess(slot, response):
    """Preserve immutable raw output; never normalize it into a semantic pass."""
    from scripts.task52_v51_eval_identity import plan as reviewed_plan
    plan = reviewed_plan()
    expected = next((s for s in plan['slots'] if s['slot'] == slot), None)
    if expected is None:
        raise ValueError('Unknown Q3 scoring slot')
    response = deepcopy(response)
    raw_hash = q1.digest(response)
    result = {'version': VERSION, 'slot': slot, 'responseHash': raw_hash,
              'structuredValid': False, 'raw': {'fullyCorrectIndependent': None, 'mechanicalFailures': [], 'extractionFailures': []},
              'legacy': None, 'guarded': None, 'mappingKnown': False,
              'requiresIndependentReview': True, 'planningAuthorized': False}
    failures = result['raw']['extractionFailures']
    result['systemFailures'] = []
    result['raw']['mechanicalGateScope'] = 'Q4C-compatible stop vector; extractionFailures separately reports raw errors; no independent correctness claim'
    try:
        if response.get('model') != 'gpt-6-luna':
            raise ValueError('model')
        items=response.get('output')
        if type(items)is not list or not items or any(type(item)is not dict or item.get('type')not in ('message','reasoning') for item in items):
            raise ValueError('unexpected_provider_output_or_tool')
        for item in items:
            if item['type']=='message' and (type(item.get('content'))is not list or
                    any(type(block)is not dict or block.get('type')not in ('output_text','refusal') for block in item['content'])):
                raise ValueError('unexpected_provider_content')
        content, usage, status = historical.Adapter('openai', None).decode(response)
        result['providerStatus'] = status
        if status != 'complete':
            raise ValueError('provider_status')
        if any(type(n) is not int or n < 0 for n in usage):
            raise ValueError('usage')
        result['usage'] = list(usage)
        reasoning = response.get('usage', {}).get('output_tokens_details', {}).get('reasoning_tokens', 0)
        if type(reasoning) is not int or not 0 <= reasoning <= usage[1]:
            raise ValueError('reasoning_usage')
        result['reasoningTokens'] = reasoning
        result['estimatedNanodollars'] = usage[0]*125 + usage[1]*500
        if usage[0] > 12000 or usage[1] > 2000:
            raise ValueError('token_cap')
        ai = parse_interpretation(content)  # duplicates/unknown properties rejected here
        wire = json.loads(content)
        if historical.missing_properties(wire, historical.schema()) or historical.missing_properties(wire, historical.schema(), unknown=True):
            raise ValueError('wire_required_or_unknown')
        result['structuredValid'] = True
    except (ValueError, TypeError, KeyError, AttributeError):
        failures.append('provider_structure_usage_or_cap')
        result['raw']['mechanicalFailures'] = list(failures)
        return result
    frozen = ai.model_dump(mode='json')
    fields = expected['Q1FieldExpectations']
    j = ai.journey
    stops = [fields[k]['expected'] or [] for k in ('required_activities', 'optional_activities')]
    wanted = sorted([s for group in stops for s in group], key=lambda s: s['index'])
    # Conservative finite-label comparison only. The reviewed generic-the rule
    # is source-bound; exact venue/brand identities are never article-stripped.
    from scripts.cloud_model52_offline import article_projection
    gold_stops = [{'source': s['sourcePhrase'], 'requirement': s['requirement'],
                   'kind': 'named_place' if any(n['index'] == s['index'] for n in fields['exact_named_identity']['expected'] or []) else 'activity'} for s in wanted]
    projected, changes = article_projection({'text': expected['source'], 'expectedExtraction': {
        'activities': [s['source'] for s in gold_stops], 'budget_per_person': None, 'date': None,
        'location': None, 'preferences': [], 'journey': {'stops': gold_stops}}}, ai)
    result['comparisonProjections'] = changes
    if j is None or len(j.stops) != len(wanted) or len(ai.activities) != len(wanted):
        failures.append('required_occurrence_count')
    else:
        for i, (actual, ref) in enumerate(zip(j.stops, wanted)):
            name = next((n for n in fields['exact_named_identity']['expected'] or [] if n['index'] == i), None)
            if name:
                same = actual.source == name['identity'] and actual.kind == name['kind']
            else:
                same = actual.kind == 'activity' and projected.journey.stops[i].source.casefold() == ref['sourcePhrase'].casefold()
            if not same or ai.activities[i] != actual.source or actual.requirement != ref['requirement']:
                failures.append('stop_identity_status_or_occurrence')
        failures.extend(evidence_failures(expected['source'], j))
    # These selected cases assert absence of all scalar constraints below.
    if any(getattr(ai, k) is not None for k in ('people','budget_per_person','budget_group','currency',
            'travel_total_minutes','travel_leg_minutes','transport','cost','start_time','end_time')):
        failures.append('invented_scalar_constraint')
    if ai.preferences or ai.time_expressions or ai.suggested_activities:
        failures.append('invented_preference_time_or_activity')
    date = fields['dates_timezones']['expected']
    if ai.date_expressions != date['expressions'] or ai.date is not None:
        failures.append('date_meaning')
    geography = fields['geography']['expected']
    if ai.location != (geography['destinationText'] if geography else None):
        failures.append('destination')
    if j:
        if any(s.duration is not None for s in j.stops) or j.deadline or j.shared_place:
            failures.append('invented_visit_deadline_or_shared_place')
        returned = fields['return_origin']['expected']
        if (j.endpoint is None) != (returned is None) or (j.endpoint and j.endpoint.kind != 'origin'):
            failures.append('endpoint')
        duration = fields['whole_trip_limit']['expected']
        if ((j.total_duration is None) != (duration is None) or
            (j.total_duration and (j.total_duration.minutes != duration['minutes'] or j.total_duration.relation != duration['relation']))):
            failures.append('whole_trip_relation')
    # The five reviewed sources have explicit, finite endpoint/time absence or
    # presence. A matching kind/number with a borrowed quote is not evidence.
    if j and j.endpoint and not ('return to the starting point' in j.endpoint.source.casefold() and ordering.spans(expected['source'],j.endpoint.source)):
        failures.append('endpoint_source_relationship')
    if j and j.total_duration and not ('within three hours' in j.total_duration.source.casefold() and ordering.spans(expected['source'],j.total_duration.source)):
        failures.append('whole_trip_source_relationship')
    # Ordering is inspected on raw copies BEFORE legacy mutation.
    proof = ordering.inspect_order(expected['source'], ai.model_copy(deep=True))
    contradiction = slot[1] == 'journey-21'
    if contradiction:
        clause = expected['source'].removeprefix('Visit ').removeprefix('the ').rstrip('.')
        if j is None or j.order or not j.clarification or clause not in j.clarification or not ordering.spans(expected['source'],j.clarification):
            failures.append('contradiction_not_preserved_for_clarification')
    elif proof['trustedGraph'] is None:
        failures.append('unsupported_missing_or_unproven_order')
    if ai.uncertainties and (not contradiction or any(clause not in u or not ordering.spans(expected['source'],u) for u in ai.uncertainties)):
        failures.append('invented_uncertainty')
    if j and not contradiction and j.clarification:
        failures.append('inappropriate_semantic_clarification')
    class Recorded:
        def interpret(self, text):
            if text != expected['source']:
                raise ValueError('Wrong replay source')
            return ai.model_copy(deep=True)
    case = {'text': expected['source']}
    # Frozen rubric is authoritative for this finite batch's timezone.
    with q1.offline():
        legacy = interpret_request(InterpretationInput(text=case['text'], calendarTimezone=date['syntheticCalendarTimezone']),
            provider=Recorded(), now=datetime.fromisoformat(plan['successorVersionSpecification']['referenceTime'].replace('Z','+00:00')))
    handoff = (legacy.executionStatus == 'advanced_unavailable' and legacy.issues == [LIMITATION]
               and legacy.unsupported == [LIMITATION] and legacy.context is not None and legacy.interpretation.journey is not None)
    accepted = handoff or not (legacy.issues or legacy.unsupported or legacy.questions)
    effective = legacy.interpretation.journey
    mapping = (j is not None and effective is not None and
               [(s.source,s.kind,s.requirement) for s in j.stops] == [(s.source,s.kind,s.requirement) for s in effective.stops] and
               j.endpoint == effective.endpoint and j.total_duration == effective.total_duration)
    result['mappingKnown'] = mapping
    if not mapping:
        result['systemFailures'].append('unresolved_effective_occurrence_mapping')
    effective_edges = [(e.before,e.after) for e in effective.order] if effective else []
    preserved = mapping and all(ordering.reach(effective_edges,a,b) for a,b in proof['requiredClosure'])
    result['legacy'] = {'disposition': 'advanced_handoff' if handoff else 'accepted_ordinary' if accepted else 'blocked_or_clarify',
                        'resultHash': q1.digest(legacy.model_dump(mode='json')), 'accepted': accepted,
                        'effectiveOrder': [list(e) for e in effective_edges], 'requiredOrderPreserved': preserved}
    disposition = ('appropriate_clarification' if contradiction and not accepted else
                   'blocked' if not accepted or proof['trustedGraph'] is None or not mapping else
                   'blocked_by_legacy_effective_order_loss' if not preserved else 'candidate_only')
    result['guarded'] = {'disposition': disposition, 'ordering': proof, 'planningAuthorized': False}
    if contradiction:
        if accepted:result['systemFailures'].append('contradiction_accepted_by_legacy')
    elif not accepted:
        result['systemFailures'].append('unexpected_legacy_rejection')
    if frozen != ai.model_dump(mode='json') or raw_hash != q1.digest(response):
        raise ValueError('Raw evidence mutation')
    result['raw']['outputHash'] = q1.digest(frozen)
    result['raw']['extractionFailures'] = sorted(set(failures))
    result['raw']['mechanicalFailures'] = sorted(set(failures + result['systemFailures']))
    result['usageEstimateBasis'] = 'Fictional historical125/500 nanodollar rates, not verified current prices'
    result['independentReviewIsSyntheticOnly'] = True
    # Durable facts use JSON arrays; normalize diagnostics only, never the raw
    # provider response/output. Recomputed outcome evidence must compare exactly.
    return json.loads(json.dumps(result,ensure_ascii=False))
