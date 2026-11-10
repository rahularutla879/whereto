"""Owner-confirmed V5.1 OFFLINE ordering. No runtime, projection repair or dispatch."""
from copy import deepcopy
import re
from scripts import task52_ordering_v5 as parent
from scripts import task52_q1 as q1

VERSION='52b-order-policy-v5.1-owner-decisions-offline'
SCORER='52b-semantic-v5.1-owner-decisions-PROPOSED'
CONNECTOR_VERSION='52b-hi-roman-aur-v1'
CONNECTORS=({'token':'aur','language':'Hindi, Roman script','meaning':'and',
             'scope':'whole-word connector between source-owned itinerary occurrences only'},)
closure=parent.closure
reach=parent.reach
spans=parent.spans
bind_occurrences=parent.bind_occurrences


def source_analysis(raw,ai):
    """Reuse frozen V5 English grammar with a bounded, offset-preserving view.

    Only reviewed connector tokens and an exact original corpus request frame
    are recognized. Raw text, extracted stops and model evidence never change.
    """
    view=raw;connectors=[];frame=None
    j=ai.journey
    if j and len(raw)<=parent.LIMIT and 0<len(j.stops)<=32:
        owned,error=bind_occurrences(raw,j.stops)
        if not error:
            edits=[]
            for left,right in zip(owned,owned[1:]):
                for match in re.finditer(r'\baur\b',raw[left[1]:right[0]],re.I):
                    a,b=left[1]+match.start(),left[1]+match.end()
                    edits.append((a,b,'and'));connectors.append({'span':[a,b],'source':raw[a:b],'table':CONNECTOR_VERSION})
            # Fixed existing corpus frame only; Kal is NOT resolved as a date.
            # Unknown destinations/other Hindi syntax are not generalized.
            if ai.location=='Hyderabad' and re.fullmatch(r'Kal Hyderabad mein\s+',raw[:owned[0][0]],re.I) and re.fullmatch(r'\s+plan karo[.!?]*\s*',raw[owned[-1][1]:],re.I):
                a,b=0,owned[0][0];edits.append((a,b,' '*(b-a)))
                a,b=owned[-1][1],len(raw);edits.append((a,b,' '*(b-a)))
                frame='original-corpus-Kal-Hyderabad-mein-list-plan-karo; date meaning unresolved'
            for a,b,value in sorted(edits,reverse=True):view=view[:a]+value+view[b:]
    result=deepcopy(parent.source_analysis(view,ai))
    result['policy']=VERSION;result['sourceSHA256']=q1.sha(raw.encode())
    result['reviewedConnectors']=connectors;result['reviewedFrame']=frame
    result['ownerOptionalSequenceRuleConfirmed']=True
    for item in result['occurrences']:item['source']=raw[slice(*item['span'])]
    proofs=[]
    for item in result['proofs']:
        value={k:deepcopy(v) for k,v in item.items() if k!='evidenceHash'}
        value['source']=raw[slice(*value['span'])];value['source_sha256']=q1.sha(raw.encode())
        cue=value['cue_span']
        if cue and any(cue[0]<=c['span'][0] and c['span'][1]<=cue[1] for c in connectors):value['rule']='default_list_hi_aur'
        proofs.append({**value,'evidenceHash':q1.digest({'policy':VERSION,**value})})
    result['proofs']=proofs
    return result


def inspect_order(raw,ai):
    frozen=ai.model_dump(mode='json');analysis=source_analysis(raw,ai)
    result={'version':VERSION,'scorer':SCORER,'orderingOnly':True,'productionActivated':False,'planningAuthorized':False,
            'source':analysis,'rawHash':q1.digest(frozen),'issues':list(analysis['issues']),
            'outcome':'clarification_required','trustedGraph':None,'normalization':None,'edges':[],'requiredClosure':[],'impliedRelationships':[]}
    j=ai.journey
    if j is None:return result
    if j.order_conflict or [s.source for s in j.stops]!=ai.activities:result['issues'].append('graph_or_activity_contract_conflict')
    if analysis['requirements'] and [s.requirement for s in j.stops]!=analysis['requirements']:result['issues'].append('source_optionality_mismatch')
    if j.clarification:result['issues'].append('existing_source_clarification_requires_review')
    all_edges=[(p['before'],p['after']) for p in analysis['proofs']];proposed=[(e.before,e.after) for e in j.order]
    result['requiredClosure']=closure(all_edges,len(j.stops))
    result['mandatoryRequiredVisitClosure']=[p for p in result['requiredClosure'] if all(j.stops[i].requirement=='required' for i in p)]
    result['conditionalClosure']=[p for p in result['requiredClosure'] if any(j.stops[i].requirement=='optional' for i in p)]
    result['impliedRelationships']=[p for p in result['requiredClosure'] if tuple(p)not in all_edges]
    for edge in j.order:
        proofs_in_quote=[]
        for q in spans(raw,edge.source):
            contained=[(p['before'],p['after']) for p in analysis['proofs'] if q[0]<=p['span'][0] and p['span'][1]<=q[1]]
            if len(edge.source)<=500 and reach(contained,edge.before,edge.after):proofs_in_quote.append(list(q))
        result['edges'].append({'before':edge.before,'after':edge.after,'assertionKind':'model_explicit_edge',
            'proven':bool(proofs_in_quote),'quoteSpans':proofs_in_quote})
        if not proofs_in_quote:result['issues'].append('unsupported_direction_scope_or_occurrence')
    if any(not reach(proposed,a,b) for a,b in all_edges):result['issues'].append('missing_source_required_relationship')
    for i,marker in analysis.get('optionalMarkerSpans',{}).items():
        occurrence=analysis['occurrences'][i]['span']
        if not any(q[0]<=marker[0] and occurrence[1]<=q[1] for q in spans(raw,j.stops[i].evidence)):
            result['issues'].append('optional_evidence_not_owned')
    if analysis['category']not in ('unknown','contradictory') and not result['issues']:
        result['outcome']='verified_order' if all_edges else 'verified_no_mandatory_order';result['trustedGraph']=[list(e) for e in proposed]
    result['issues']=sorted(set(result['issues']))
    if frozen!=ai.model_dump(mode='json'):raise ValueError('Raw model mutated')
    return result


def selected_visit_projection(decision,selected):
    """Offline consequences only; not an itinerary, plan repair or authority."""
    if decision.get('version')!=VERSION or decision.get('trustedGraph')is None:
        raise ValueError('Verified V5.1 ordering decision required')
    requirements=decision['source']['requirements'];n=len(requirements)
    if not isinstance(selected,list) or any(type(i)is not int or not 0<=i<n for i in selected) or len(set(selected))!=len(selected):
        raise ValueError('Invalid selected occurrence set')
    if any(i not in selected for i,r in enumerate(requirements) if r=='required'):
        raise ValueError('Required visit cannot be omitted')
    graph=[p for p in decision['requiredClosure'] if all(i in selected for i in p)]
    return {'version':VERSION,'selectedOccurrences':sorted(selected),'requiredReachability':graph,
            'planningAuthorized':False,'rawOutputChanged':False}
