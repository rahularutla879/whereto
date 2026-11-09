"""Opt-in source-first policy. Shadow observes; never authorizes a plan.

V1/V2/V3 and production enforcement stay frozen. Source analysis discards the model graph and
derives qualifier ownership before using V2's bounded relationship grammar.
Only a separately proved unordered list permits an audited graph projection.
This is ordering-only: canonical identity/time/endpoint validation still applies.
"""
import hashlib
import json
import re

from scripts import cloud_model52_ordering_v2 as v2
from scripts.cloud_model52_ordering import bind_occurrences, spans, reach, QUALIFIER, RETRACTION

VERSION = '52b-order-policy-v4-shadow'
LIMIT = 8000
POTENTIAL = re.compile(v2.CUE.pattern + r'|\b(?:next|prior|subsequently|sequence|order)\b', re.I)
LOCAL_OPTIONAL = re.compile(r'\s*(?:and\s+)?(?:maybe|optionally)\s+(?:(?:get|grab|have|visit)\s+|stop\s+(?:at|for)\s+)?(?:the\s+|a\s+)?', re.I)
LIST_GAP = re.compile(r'\s*(?:,\s*(?:and\s+)?|;\s*|and\s+)' + v2.LEAD + r'\s*', re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def blank(text, a, b):
    return text[:a] + ' ' * (b-a) + text[b:]


def start_finish(raw, masked, owned, location, requirements):
    """Two/three visits; exact source-owned prefix, connectors and neutral tail.

    Global first/last scope establishes the middle relations, not list order.
    All global edges require the WHOLE supporting first/last clause in evidence.
    """
    if len(owned) not in (2,3) or any(r!='required' for r in requirements):return []
    first,last=owned[0],owned[-1]
    prefix=re.fullmatch(r'\s*start (?:with|at)\s+(?:the\s+|a\s+)?',raw[:first[0]],re.I)
    if not prefix:return []
    if len(owned)==2:
        connectors=bool(re.fullmatch(r'\s*(?:,|and)\s*finish at\s+(?:the\s+|a\s+)?',raw[first[1]:last[0]],re.I))
    else:
        middle=owned[1]
        connectors=bool(re.fullmatch(r'\s*,\s*visit\s+(?:the\s+|a\s+)?',raw[first[1]:middle[0]],re.I)
            and re.fullmatch(r'\s*,\s*and finish at\s+(?:the\s+|a\s+)?',raw[middle[1]:last[0]],re.I))
    tail=masked[last[1]:]
    if location and not POTENTIAL.search(location) and not QUALIFIER.search(location):
        tail=re.sub(r'\bin\s+'+re.escape(location)+r'\b',' ',tail,flags=re.I)
    neutral=bool(re.fullmatch(r'\s*(?:(?:now|today|tomorrow|tonight)\s*)?[.!?]*\s*',tail,re.I))
    # Home is not a source-confirmed visit or a confirmed origin. Keep it unknown.
    endpoint_ambiguity=any(re.fullmatch(r'(?:the\s+)?(?:home|start|starting point)',raw[a:b],re.I) for a,b in owned)
    if not connectors or not neutral or endpoint_ambiguity:return []
    cue=re.search(r'start',raw[:first[0]],re.I)
    return [{'before':i,'after':i+1,'rule':'global_start_finish_'+str(len(owned)),
        'span':[cue.start(),last[1]],'cueSpan':list(cue.span()),'source':raw[cue.start():last[1]]}
        for i in range(len(owned)-1)]


def source_analysis(raw, ai):
    """Graph-independent bounded intent proof, with original codepoint offsets.

    Stop labels must already be strict parsed/source-bound. This does not prove
    completeness of the activity extraction or exact business identity.
    """
    r={'category':'unknown','proofs':[],'issues':[],'qualifiers':[],
       'requirements':[],'sourceHash':digest(raw),'absenceProof':None}
    if len(raw)>LIMIT or not ai.journey or len(ai.journey.stops)>32:
        r['issues']=['bounded_input_or_missing_contract'];return r
    if any(s.kind!='named_place' and (POTENTIAL.search(s.source) or QUALIFIER.search(s.source))
           for s in ai.journey.stops):
        r['issues']=['semantic_marker_inside_generic_label'];return r
    owned,error=bind_occurrences(raw,ai.journey.stops)
    if error:
        r['issues']=[error];return r
    r['occurrences']=[list(s) for s in owned]
    masked=raw
    # Only an actual source-leading imperative outside the first owned stop.
    if owned and re.fullmatch(r"\s*do\s+",raw[:owned[0][0]],re.I):
        masked=blank(masked,0,owned[0][0])
    for i,(a,b) in enumerate(owned):
        # A qualifier belongs only to an independently delimited single stop.
        # Never erase a qualifier over A-before-B or an arbitrary parenthesis.
        previous=owned[i-1][1] if i else 0
        boundary=max(raw.rfind(c,previous,a) for c in ',;.!?')
        begin=boundary+1 if boundary>=0 else 0
        if i and re.fullmatch(r'\s+and\s+(?:maybe|optionally)\s+.*',raw[previous:a],re.I):
            begin=previous
        prefix=raw[begin:a]
        optional=LOCAL_OPTIONAL.fullmatch(prefix)
        requirement='required'
        if optional and (i==0 or boundary>=previous or begin==previous):
            next_start=owned[i+1][0] if i+1<len(owned) else len(raw)
            tail=raw[b:next_start]
            # Optional A before B is not a mandatory edge or a local list item.
            if not POTENTIAL.search(tail) and (i+1==len(owned) or re.match(r'\s*[,;]',tail)):
                marker=re.search(r'\b(?:maybe|optionally)\b',prefix,re.I)
                marker_start=begin+marker.start()
                requirement='optional';masked=blank(masked,marker_start,a)
                r['qualifiers'].append({'index':i,'kind':'optional','span':[marker_start,a]})
        tail_end=owned[i+1][0] if i+1<len(owned) else len(raw)
        flexible=re.match(r'\s+whenever convenient\b',raw[b:tail_end],re.I)
        independent=i==0 or LIST_GAP.fullmatch(raw[previous:a])
        if flexible and independent:
            masked=blank(masked,b,b+flexible.end())
            r['qualifiers'].append({'index':i,'kind':'independently_flexible_required','span':[b,b+flexible.end()]})
        r['requirements'].append(requirement)
    # Work on an independent graph-free copy. Its proof spans are always mapped
    # back to the ORIGINAL text; masked text never becomes model evidence.
    scratch=ai.model_copy(deep=True)
    scratch.journey.order=[];scratch.journey.order_conflict=False;scratch.journey.clarification=None
    for stop,req in zip(scratch.journey.stops,r['requirements']):stop.requirement=req
    proof=v2.inspect_order(masked,scratch)
    r['proofs']=proof['proofs']
    # Exact global first/last grammar, never generic list position inference.
    global_proofs = start_finish(raw, masked, owned, ai.location, r['requirements'])
    if global_proofs:
        r['proofs']=global_proofs
    outside=masked
    for a,b in reversed(owned):outside=blank(outside,a,b)
    flexible=re.search(r',?\s*whichever is closer first\s*,?',outside,re.I)
    r['mode']='flexible' if flexible else 'unspecified'
    if flexible:outside=blank(outside,*flexible.span())
    endpoint=ai.journey.endpoint
    # A separate named endpoint can own "finish at", but never a visit stop.
    # Verify source text and non-overlap, retaining endpoint semantics elsewhere.
    if endpoint and endpoint.source and not POTENTIAL.search(endpoint.source):
        endpoint_clause=re.search(r'\band finish at\s+'+re.escape(endpoint.source)+r'\b',raw,re.I)
        if endpoint_clause and not any(a<endpoint_clause.end() and endpoint_clause.start()<b for a,b in owned):
            outside=blank(outside,*endpoint_clause.span())
    # Qualifiers remaining outside owned spans are deliberately NOT discarded.
    if QUALIFIER.search(outside) or RETRACTION.search(outside):
        r['issues'].append('unowned_conditional_negative_or_qualifier')
    for p in r['proofs']:
        p['source']=raw[slice(*p['span'])]
        outside=blank(outside,*p['span'])
    if POTENTIAL.search(outside):r['issues'].append('unproven_potential_ordering')
    if r['proofs']:
        # V2 issues from source scope remain binding; graph omissions are not
        # source-analysis failures because the scratch graph is intentionally empty.
        r['issues'] += [x for x in proof['issues'] if x not in
            ('missing_proven_required_relationship',) and not (r['proofs'][0]['rule'].startswith('global_start_finish') and x=='unproven_cue_scope')]
        if not r['issues']:
            covered={x for p in r['proofs'] for x in (p['before'],p['after'])}
            r['category']='explicit' if len(covered)==len(owned) else 'partial'
            r['mode']='constrained'
    elif not r['issues']:
        # Absence needs a complete finite unordered-list parse, not absence of
        # recognized cues. Unknown connectors/clauses cannot authorize deletion.
        text=masked
        if flexible:text=blank(text,*flexible.span())
        tail=text[owned[-1][1]:] if owned else text
        location=ai.location
        if location and not POTENTIAL.search(location) and not QUALIFIER.search(location):
            tail=re.sub(r'\bin\s+'+re.escape(location)+r'\b',' ',tail,flags=re.I)
        tail=re.sub(r'\b(?:now|tomorrow|today|tonight)\b',' ',tail,flags=re.I)
        tail=re.sub(r'\bfor\s+\d+\s+minutes?\b',' ',tail,flags=re.I)
        tail=re.sub(r'(?:,?\s*and\s+)?return to (?:where I started|the starting point)\s*(?:within \d+ minutes?)?',' ',tail,flags=re.I)
        tail=re.sub(r'\bin the same mall\b',' ',tail,flags=re.I)
        # Endpoint-only finish is not an order between extracted visits. Keep
        # its original endpoint requirements for separate canonical validation.
        if endpoint and endpoint.source and not POTENTIAL.search(endpoint.source):
            tail=re.sub(r'\s+and finish at\s+'+re.escape(endpoint.source)+r'\b',' ',tail,flags=re.I)
        prefix_ok=bool(owned and (v2.PREFIX.fullmatch(text[:owned[0][0]])
            or re.fullmatch(r'\s*(?:go|plan)\s+',text[:owned[0][0]],re.I)))
        gaps_ok=all(LIST_GAP.fullmatch(text[a[1]:b[0]]) for a,b in zip(owned,owned[1:]))
        if prefix_ok and gaps_ok and re.fullmatch(r'[\s,.;!?]*',tail):
            r['category']='unordered';r['absenceProof']='bounded_complete_unordered_list_v4'
        else:r['issues'].append('absence_not_independently_proven')
    r['issues']=sorted(set(r['issues']))
    if r['issues']:r['category']='unknown'
    return r


def inspect_order(raw,ai):
    """One decision authority; preserves raw mistakes and never mutates output."""
    analysis=source_analysis(raw,ai)
    j=ai.journey
    r={'version':VERSION,'outcome':'clarification_required','orderingOnly':True,
       'productionActivated':False,'source':analysis,'rawHash':digest(ai.model_dump(mode='json')),
       'issues':list(analysis['issues']),'originalGraph':[], 'trustedGraph':None,
       'unsupportedModelEdges':[],'normalization':None,'rawModelOrderingCorrect':False,
       'safeNextAction':'clarify_or_rephrase_original_source'}
    if not j:return r
    proposed=[(x.before,x.after) for x in j.order]
    r['originalGraph']=[list(x) for x in proposed]
    if j.order_conflict or [s.source for s in j.stops]!=ai.activities:
        r['issues'].append('graph_or_activity_contract_conflict')
    if [s.requirement for s in j.stops]!=analysis['requirements']:
        r['issues'].append('source_optionality_mismatch')
    if j.clarification:r['issues'].append('existing_source_clarification_requires_review')
    if analysis['category']=='unordered':
        if (j.ordering=='flexible') != (analysis['mode']=='flexible'):
            r['issues'].append('source_flexible_mode_mismatch')
        r['unsupportedModelEdges']=r['originalGraph']
        # Retain the narrow historical forward-only safety gate. A reversed,
        # cyclic or ungrounded graph is not silently repaired even on a list.
        owned=analysis['occurrences']
        for edge in j.order:
            if not (0<=edge.before<edge.after<len(owned)) or not any(
                len(edge.source)<=500 and q[0]<=owned[edge.before][0] and owned[edge.after][1]<=q[1]
                for q in spans(raw,edge.source)):
                r['issues'].append('unordered_model_edge_not_safe_to_normalize')
        if not r['issues']:
            r['trustedGraph']=[]
            if proposed:r['normalization']='audited_clear_source_unordered_projection'
    elif analysis['category'] in ('explicit','partial'):
        proofs=analysis['proofs']
        for edge in j.order:
            okay=any(len(edge.source)<=500 and reach([
                (p['before'],p['after']) for p in proofs if q[0]<=p['span'][0] and p['span'][1]<=q[1]],
                edge.before,edge.after) for q in spans(raw,edge.source))
            if not okay:r['unsupportedModelEdges'].append([edge.before,edge.after])
        if r['unsupportedModelEdges']:r['issues'].append('unproven_model_edge')
        if any(not reach(proposed,p['before'],p['after']) for p in proofs):
            r['issues'].append('missing_proven_required_relationship')
        if not r['issues']:r['trustedGraph']=r['originalGraph']
    if r['trustedGraph'] is not None and not r['issues']:
        r['outcome']='verified_order' if analysis['proofs'] else 'verified_no_mandatory_order'
        r['rawModelOrderingCorrect']=not r['unsupportedModelEdges']
        r['safeNextAction']='continue_remaining_canonical_validation_only'
    r['issues']=sorted(set(r['issues']))
    return r


def project(raw,ai,decision):
    """Explicit offline projection with immutable raw evidence/hash binding."""
    if decision!=inspect_order(raw,ai) or decision['trustedGraph'] is None:
        raise ValueError('Missing, stale or untrusted ordering decision')
    result=ai.model_copy(deep=True)
    if decision['normalization']:
        result.journey.order=[];result.journey.ordering=decision['source']['mode']
    return result
