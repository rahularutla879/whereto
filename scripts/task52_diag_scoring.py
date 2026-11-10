"""Five-axis diagnostic policy: preserve raw evidence and blocked planning.

Only a mechanically intact, independently proven raw graph with one exact,
reproducible legacy mutation can be eligible for a later signed synthetic review.
Eligibility never constitutes independent human certification or real authority.
"""
from datetime import datetime
from copy import deepcopy
from scripts import task52_q1 as q1
from scripts import task52_diag_identity as identity
from scripts import task52_v51_eval_scoring as parent
from scripts import cloud_model52 as historical
from backend.ai import parse_interpretation
from backend.interpretation import InterpretationInput,interpret_request
from backend.journey import validate_journey,LIMITATION

VERSION='52b-v51-known-legacy-loss-diagnostic-policy-v1'


def delta(before,after,path=''):
    if type(before)is dict and type(after)is dict and before.keys()==after.keys():
        return sum((delta(before[k],after[k],path+'/'+k) for k in before),[])
    return [] if q1.digest(before)==q1.digest(after) else [path]


def assess(slot,response):
    identity.verify()
    result=parent.assess(slot,response)  # Complete original A/B/C, unchanged.
    result['diagnostic']={'policy':VERSION,'purpose':identity.PURPOSE,
        'mechanicallyEligibleAfterReview':False,'allowlistedDefect':None,
        'systemIncompatible':None,'reviewRequired':True,'disposition':'halt',
        'independentCertification':None,'actualContinuationAuthorized':False,
        'planningAuthorized':False}
    d=result['diagnostic']
    if (not result['structuredValid'] or result['raw']['mechanicalFailures']
            or not result['mappingKnown']):return result
    entry=next(s for s in identity.plan()['slots'] if s['slot']==slot)
    ai=parse_interpretation(historical.Adapter('openai',None).decode(response)[0])
    before=ai.model_dump(mode='json')
    class Recorded:
        def interpret(self,text):
            if text!=entry['source']:raise ValueError('Wrong diagnostic source')
            return ai.model_copy(deep=True)
    with q1.offline():
        legacy=interpret_request(InterpretationInput(text=entry['source'],calendarTimezone=entry['Q1FieldExpectations']['dates_timezones']['expected']['syntheticCalendarTimezone']),
            provider=Recorded(),now=datetime.fromisoformat(identity.plan()['successorVersionSpecification']['referenceTime'].replace('Z','+00:00')))
    after=legacy.interpretation.model_dump(mode='json');changed=delta(before,after)
    d['mutationPaths']=changed
    d['rawInterpretationHash']=q1.digest(before);d['effectiveInterpretationHash']=q1.digest(after)
    if q1.digest(legacy.model_dump(mode='json'))!=result['legacy']['resultHash']:
        return blocked(result,'nonreproducible_complete_legacy_result')
    disposition=result['guarded']['disposition']
    if disposition=='blocked_by_legacy_effective_order_loss':
        allow=identity.defect();j=ai.journey;effective=legacy.interpretation.journey
        witness=ai.model_copy(deep=True)
        with q1.offline():issue,ambiguous=validate_journey(entry['source'],witness)
        proof=result['guarded']['ordering']
        matched=(slot==allow['slot'] and entry['sourceSHA256']==allow['sourceSHA256']
            and changed==allow['mutationPaths'] and issue==LIMITATION and ambiguous is False
            and q1.digest(witness.model_dump(mode='json'))==q1.digest(after) and j is not None and effective is not None
            and legacy_envelope_hash(legacy)==allow['legacyEnvelopeHash']
            and j.ordering=='constrained' and len(j.order)==1
            and [[e.before,e.after] for e in j.order]==allow['rawEdges']
            and effective.order==[] and effective.ordering=='unspecified'
            and proof['trustedGraph']is not None and result['legacy']['accepted']
            and result['legacy']['disposition']=='advanced_handoff'
            and result['legacy']['effectiveOrder']==[] and not result['legacy']['requiredOrderPreserved'])
        if not matched:return blocked(result,'unallowlisted_legacy_difference')
        d.update(allowlistedDefect=identity.defect_hash(),systemIncompatible=True,
                 mechanicallyEligibleAfterReview=True,disposition='known_legacy_loss_review_required')
    elif changed:
        return blocked(result,'unknown_effective_mutation')
    elif disposition in ('candidate_only','appropriate_clarification'):
        d.update(mechanicallyEligibleAfterReview=True,systemIncompatible=False,disposition='standard_review_required')
    else:return blocked(result,'unsafe_or_unknown_guard_result')
    return result


def blocked(result,reason):
    # Keep raw extractionFailures untouched: a system/policy discrepancy is not
    # a claim of hallucination. The inherited stop vector must still halt.
    result['systemFailures']=sorted(set(result['systemFailures']+[reason]))
    result['raw']['mechanicalFailures']=sorted(set(result['raw']['mechanicalFailures']+[reason]))
    result['diagnostic'].update(disposition='halt',reason=reason)
    return result


def legacy_envelope_hash(result):
    """Hash all disposition/calendar/pending state, masking identical AI copies.

    No result/output is changed; hashes of original complete DTO remain intact.
    """
    d=deepcopy(result.model_dump(mode='json'))
    if type(d.get('pending'))is not dict or q1.digest(d['pending'].get('interpretation'))!=q1.digest(d['interpretation']):
        return None
    d['interpretation']='EFFECTIVE_AI';d['pending']['interpretation']='EFFECTIVE_AI'
    return q1.digest(d)
