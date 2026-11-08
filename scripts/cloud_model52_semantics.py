"""Evaluation-only reference comparison. Production grounding is unchanged."""
from functools import lru_cache
import re

VERSION = '52b-semantic-v2-grounded-provenance'
SCALARS = ('people','budget_per_person','budget_group','currency','travel_total_minutes',
           'travel_leg_minutes','transport','cost','location')


def reference_wire(case):
    from backend.ai import Interpretation
    value = Interpretation.model_validate(case['expectedExtraction']).model_dump(mode='json')
    value.pop('start_time'); value.pop('end_time')
    value['journey'].pop('order_conflict')
    if value['journey']['deadline']:
        value['journey']['deadline'].pop('minute')
    return value


@lru_cache(maxsize=25)
def reference_result(case_id):
    from scripts import cloud_model52 as e
    import json
    case = next(c for c in e.corpus()['cases'] if c['id'] == case_id)
    return e.validate(case, json.dumps(reference_wire(case)))[1]


def evidence_failures(text, actual, reference=None):
    """Validate optional evidence AND its attachment to a source occurrence.

    Empty/omitted reference evidence is an unspecified exact quotation, not a
    demand for an empty model value. Stop.source is always mandatory. Optional
    stops still require evidence under unchanged trusted rules. An explicit
    nonempty reference evidence string remains an exact assertion.
    """
    failures=[]
    if actual is None:
        return failures
    raw=text.casefold();cursor=0
    expected=reference.stops if reference else []
    for i,stop in enumerate(actual.stops):
        source=stop.source.casefold();position=raw.find(source,cursor)
        if position<0:
            # The production validator supports an explicit repetition count.
            repeat=re.search(re.escape(source)+r'\s+(twice|two times|2 times|three times|3 times)\b',raw)
            count=sum(s.source.casefold()==source for s in actual.stops)
            if repeat and count==(3 if repeat[1] in ('three times','3 times') else 2):
                position=raw.find(source)
            else:
                failures.append(f'stops[{i}].sourceOccurrence')
        else:
            cursor=position+len(source)
        evidence=stop.evidence
        if evidence:
            spans=[(m.start(),m.end()) for m in re.finditer(re.escape(evidence.casefold()),raw)]
            if not any(a<=position and position+len(source)<=b for a,b in spans):
                failures.append(f'stops[{i}].evidenceAttachment')
        elif stop.requirement=='optional':
            failures.append(f'stops[{i}].requiredEvidence')
        if i<len(expected) and expected[i].evidence and evidence!=expected[i].evidence:
            failures.append(f'stops[{i}].explicitReferenceEvidence')
    return failures


def compare_reference(case, actual, result):
    """Strict substantive facts, trusted normalization, narrowly scoped quotes.

    Both sides run through the same trusted pipeline/frozen clock. Source quote
    wording may differ only for non-identity constraint evidence already checked
    for grounding, direction, scope, duration relation and occurrence attachment.
    Stop identities and named endpoint source strings are never stripped.
    """
    from backend.ai import Interpretation
    expected_raw=Interpretation.model_validate(case['expectedExtraction'])
    expected=reference_result(case['id'])
    wanted=expected.interpretation
    got=actual
    failures=evidence_failures(case['text'], actual.journey, expected_raw.journey)
    def compare(a,b,path='$'):
        if type(a)!=type(b):
            failures.append(path);return
        if isinstance(a,dict):
            for key in sorted(set(a)|set(b)):
                if key=='evidence':
                    continue # Individually audited above; never globally ignored.
                if key=='source':
                    stop_identity=bool(re.fullmatch(r'\$\.stops\[\d+\]',path))
                    named_endpoint=path=='$.endpoint' and b.get('kind') in ('named_place','activity','brand')
                    if not (stop_identity or named_endpoint):
                        continue # Only trusted, relationship-bound provenance wording.
                compare(a.get(key),b.get(key),path+'.'+key)
        elif isinstance(a,list):
            if len(a)!=len(b): failures.append(path+'.length');return
            for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
        elif a!=b:
            failures.append(path)
    def facts(journey):
        if journey is None:return None
        data=journey.model_dump(mode='json')
        # Constraint list order and redundant transitive edges do not change a
        # partial order. Occurrence indexes stay distinct, including repeats.
        edges={(edge['before'],edge['after']) for edge in data['order']}
        for k in range(len(data['stops'])):
            edges |= {(a,b) for a,k1 in list(edges) for k2,b in list(edges) if k1==k==k2}
        data['order']=[{'before':a,'after':b} for a,b in sorted(edges)]
        return data
    compare(facts(got.journey),facts(expected_raw.journey))
    # Clock/source normalization is checked in addition to raw substantive facts.
    if result.interpretation.journey and wanted.journey:
        a=result.interpretation.journey.deadline;b=wanted.journey.deadline
        if a and b and a.minute!=b.minute:failures.append('deadline.resolvedMinute')
    for key in SCALARS:
        if getattr(got,key)!=getattr(expected_raw,key):failures.append('interpretation.'+key)
    # Preserve explicitly asserted date/time meaning, not a default absence.
    for key in ('date_expressions','time_expressions'):
        if key in case['expectedExtraction'] and getattr(got,key)!=getattr(expected_raw,key):
            failures.append('interpretation.'+key)
    # Different trusted outcomes/clarification needs are not semantic successes.
    if [q.field for q in result.questions]!=[q.field for q in expected.questions]:
        failures.append('clarification.fields')
    if result.issues!=expected.issues or result.unsupported!=expected.unsupported:
        failures.append('trustedDisposition')
    if result.executionStatus!=expected.executionStatus:
        failures.append('executionStatus')
    if result.request and expected.request:
        for key in ('date','location','people','budget','groupBudget','maxLegTravel','travel',
                    'firstTravel','betweenTravel','transport','startTime','endTime'):
            if getattr(result.request,key)!=getattr(expected.request,key):failures.append('request.'+key)
    return sorted(set(failures))
