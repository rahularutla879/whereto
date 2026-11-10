"""Independent OFFLINE owner-policy V5. No projection, runtime or dispatch.

Bounded itinerary lists default to sequence. Explicit exceptions take priority.
This proves ordering only; all canonical non-order validation remains required.
"""
from dataclasses import dataclass,asdict
import re
from scripts import task52_q1 as q1
from scripts import cloud_model52_ordering_v4 as v4
from scripts.cloud_model52_ordering import bind_occurrences,spans,reach

VERSION='52b-order-policy-v5-offline'
SCORER='52b-semantic-v4-owner-list-order-PROPOSED'
LIMIT=8000
LEAD=r'(?:(?:go|walk|drive|head)\s+to\s+|head\s+out\s+for\s+|(?:get|grab|visit|buy|have|play|stop for|stop at)\s+)?(?:the\s+|a\s+|an\s+)?'
PREFIX=re.compile(r'\s*(?:(?:plan|do)\s+)?'+LEAD+r'\s*',re.I)
GAP=re.compile(r'\s*(?P<cue>[,，]\s*(?:(?:and\s+)?then\s+|and\s+)?|and\s+(?:then\s+)?|then\s+|→\s*|⇒\s*|->\s*)' +
               r'(?P<optional>(?:maybe|optionally)\s+)?'+LEAD+r'\s*',re.I)
DANGER=re.compile(r"\b(?:no|not|never|unless|if|would|could|might|consider|discuss|hypothetical|ignore|schema|pretend|instead|or|reverse)\b|don't",re.I)
GLOBAL_UNORDERED=re.compile(r'\s*[,，]?\s*(?:in any order|in either order|either order)\s*[.!?]*\s*$',re.I)


@dataclass(frozen=True)
class Evidence:
    before:int
    after:int
    rule:str
    span:tuple[int,int]
    cue_span:tuple[int,int]|None
    source:str
    source_sha256:str
    conditional:bool=False


def closure(edges,n):return [[i,j] for i in range(n) for j in range(n) if i!=j and reach(edges,i,j)]


def proof(raw,a,b,rule,span,cue=None,conditional=False):
    value=asdict(Evidence(a,b,rule,tuple(span),tuple(cue) if cue else None,raw[slice(*span)],q1.sha(raw.encode()),conditional))
    return {**value,'evidenceHash':q1.digest({'policy':VERSION,**value})}


def neutral_tail(tail,location):
    parts=[r'(?:now|today|tomorrow|tonight|again)',r'for\s+\d+\s+people',r'(?:near|around)\s+me',r'in\s+(?:the\s+)?same mall',
        r'(?:and\s+|then\s+|→\s*)?return\s+(?:to\s+(?:where I started|the starting point|my starting point)|home)(?:\s+(?:within|in less than)\s+(?:\d+|one|two|three)\s+(?:minutes?|hours?))?']
    if location and not DANGER.search(location) and not v4.POTENTIAL.search(location):parts.append(r'in\s+'+re.escape(location))
    return bool(re.fullmatch(r'[\s,，.;!?]*(?:(?:'+ '|'.join(parts) +r')[\s,，.;!?]*)*',tail,re.I))


def source_analysis(raw,ai):
    result={'category':'unknown','proofs':[],'issues':[],'requirements':[], 'occurrences':[],
            'sourceSHA256':q1.sha(raw.encode()),'independent':[],'conditionalSemantics':'order if both visited; closure before optional projection',
            'nonOrderValidationRequired':True}
    j=ai.journey
    if len(raw)>LIMIT or j is None or not 0<len(j.stops)<=32:
        result['issues']=['bounded_input_or_missing_occurrence_contract'];return result
    if any(s.kind=='activity' and (v4.POTENTIAL.search(s.source) or v4.QUALIFIER.search(s.source) or re.search(r'\b(?:return|home|starting point|origin)\b',s.source,re.I)) for s in j.stops):
        result['issues']=['semantic_marker_or_endpoint_inside_generic_stop'];return result
    # Two conflicting references are NOT four visits. Recognize only this exact
    # binary contradiction; other repeated-reference ambiguity remains unknown.
    if len(j.stops)==2:
        a,b=[s.source for s in j.stops]
        pat=r'\s*(?:visit\s+)?(?:the\s+)?'+re.escape(a)+r'\s+before\s+(?:the\s+)?'+re.escape(b)+r',\s*but\s+(?:the\s+)?'+re.escape(b)+r'\s+before\s+(?:the\s+)?'+re.escape(a)+r'[.!?]*\s*'
        if re.fullmatch(pat,raw,re.I):
            result.update(category='contradictory',requirements=['required','required'],issues=['contradictory_source_relations'])
            return result
    owned,error=bind_occurrences(raw,j.stops)
    if error:result['issues']=[error];return result
    result['occurrences']=[{'index':i,'id':f's{i}','span':list(s),'source':raw[slice(*s)]} for i,s in enumerate(owned)]
    outside=raw
    for a,b in reversed(owned):outside=outside[:a]+' '*(b-a)+outside[b:]
    # Quotes/headings/groups outside owned names are not itinerary-list syntax.
    if re.search(r'''["“”‘’'():\[\]{}]''',outside):
        result['issues']=['quoted_heading_or_group_scope_requires_review'];return result
    global_unordered=GLOBAL_UNORDERED.search(raw[owned[-1][1]:])
    masked_outside=outside
    if global_unordered:
        start=owned[-1][1]+global_unordered.start();masked_outside=outside[:start]+' '*(len(raw)-start)
    if DANGER.search(masked_outside):result['issues']=['conditional_negative_hypothetical_or_unowned_scope'];return result
    # Before/after, rank and flexible clause grammar stay explicitly bounded.
    explicit=bool(re.search(r'\b(?:before|after|first|second|third|last|followed|whichever|start|finish)\b',outside,re.I))
    if explicit and not re.match(r'\s*start (?:with|at)\b',raw,re.I):
        old=v4.source_analysis(raw,ai.model_copy(deep=True))
        mixed=bool(len(owned)>2 and re.search(r'\b(?:before|after)\b',outside,re.I) and ';'not in raw and not old.get('qualifiers'))
        if old['category']in ('explicit','partial','unordered') and not mixed and not global_unordered:
            result.update(category=old['category'],requirements=old['requirements'],independent=[q['index'] for q in old['qualifiers'] if q['kind']=='independently_flexible_required'])
            result['optionalMarkerSpans']={q['index']:q['span'] for q in old['qualifiers'] if q['kind']=='optional'}
            result['proofs']=[proof(raw,p['before'],p['after'],'explicit_'+p['rule'],p['span'],p['cueSpan']) for p in old['proofs']]
            return result
        result['issues']=['explicit_partial_or_cue_scope_requires_review'];return result
    requirements=['required']*len(owned);flex=set();gaps=[];proofs=[]
    prefix=raw[:owned[0][0]]
    first_optional=re.match(r'\s*(maybe|optionally)\s+',prefix,re.I)
    optional_markers={}
    if first_optional:
        optional_markers[0]=list(first_optional.span(1));requirements[0]='optional';prefix=prefix[first_optional.end():]
    start_finish=bool(re.fullmatch(r'\s*start (?:with|at)\s+(?:the\s+|a\s+)?',prefix,re.I))
    if not start_finish and not PREFIX.fullmatch(prefix):result['issues']=['not_a_bounded_itinerary_prefix'];return result
    for i,(left,right) in enumerate(zip(owned,owned[1:])):
        gap=raw[left[1]:right[0]]
        convenient=re.match(r'\s+whenever convenient\b',gap,re.I)
        offset=left[1]
        if convenient:flex.add(i);offset+=convenient.end();gap=gap[convenient.end():]
        if start_finish:
            okay=re.fullmatch(r'\s*,\s*visit\s+(?:the\s+|a\s+)?',gap,re.I) if i==0 and len(owned)==3 else re.fullmatch(r'\s*(?:,\s*(?:and\s+)?|and\s+)finish at\s+(?:the\s+|a\s+)?',gap,re.I)
            if not okay:result['issues']=['global_start_finish_scope_requires_review'];return result
            gaps.append(('explicit_global',None));continue
        m=GAP.fullmatch(gap)
        if not m:result['issues']=['not_a_complete_bounded_list_connector'];return result
        if m['optional']:
            requirements[i+1]='optional';optional_markers[i+1]=[offset+m.start('optional'),offset+m.end('optional')]
        cue=m['cue'];kind='explicit_then' if re.search(r'\bthen\b|→|⇒|->',cue,re.I) else 'default_list'
        gaps.append((kind,[offset+m.start('cue'),offset+m.end('cue')]))
    tail=raw[owned[-1][1]:]
    convenient=re.match(r'\s+whenever convenient\b',tail,re.I)
    if convenient:flex.add(len(owned)-1);tail=tail[convenient.end():]
    if global_unordered:
        # Suffix exception scopes the entire bounded list only. It cannot erase
        # explicit then/arrows/global first/last or a nested subgroup relation.
        if start_finish or any(k!='default_list' for k,_ in gaps):result['issues']=['conflicting_global_unordered_and_explicit_order'];return result
        tail=tail[:GLOBAL_UNORDERED.search(tail).start()]
    if not neutral_tail(tail,ai.location):result['issues']=['unconsumed_context_or_terminal_scope'];return result
    if start_finish and (len(owned)not in (2,3) or requirements!=['required']*len(owned) or any(s.source.casefold()in ('home','start','starting point') for s in j.stops)):
        result['issues']=['ambiguous_global_endpoint_or_optionality'];return result
    if first_optional and len(owned)>1 and gaps[0][0]!='explicit_then':result['issues']=['leading_optional_group_scope_requires_review'];return result
    sequence=[i for i in range(len(owned)) if i not in flex]
    if not global_unordered:
        for a,b in zip(sequence,sequence[1:]):
            kind,cue=gaps[a] if b==a+1 else ('default_list_skipping_flexible',None)
            span=[owned[a][0],owned[b][1]]
            if start_finish:
                kind='explicit_global_first_last';span=[0,owned[-1][1]]
            proofs.append(proof(raw,a,b,kind,span,cue,requirements[a]=='optional' or requirements[b]=='optional'))
    result.update(category='unordered' if global_unordered else 'partial' if flex else 'sequence' if len(owned)>1 else 'single',
                  requirements=requirements,proofs=proofs,independent=sorted(flex),optionalMarkerSpans=optional_markers)
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
