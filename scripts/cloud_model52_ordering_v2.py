"""Version2 OFFLINE ordering compatibility experiment; production stays unchanged.

V1 remains frozen. Reuse its bounded ownership/path primitives; use separately
versioned anchored grammar. No model, provider, routing or credential access.
"""
import re
from scripts.cloud_model52_ordering import bind_occurrences, spans, reach, RETRACTION, QUALIFIER

VERSION = '52b-order-proof-v2-offline'
CUE = re.compile(r'\b(?:then|before|after|first|second|third|fourth|last|finally|afterward|followed|start|finish)\b|→|⇒|➜|⟶|->', re.I)
LEAD = r'(?:(?:go|walk|drive|head)\s+to\s+|head\s+out\s+for\s+|(?:get|visit|buy|have|play)\s+|stop\s+(?:at|for)\s+)?(?:the\s+|a\s+|an\s+)?'
PREFIX = re.compile(r'\s*(?:first\s*,?\s*)?' + LEAD + r'\s*', re.I)
RANKS = {'first':1,'second':2,'third':3,'fourth':4,'last':99}
GAPS = (
 ('then', re.compile(r'\s*[,，—–]?\s*(?:first\s*(?:,|and)?\s*)?(?:and\s+)?(?:then|finally|afterward)\s+' + LEAD, re.I), False),
 ('rank_then', re.compile(r'\s+(?:second|third)\s*,\s*(?:and\s+)?then\s+' + LEAD, re.I), False),
 ('before', re.compile(r'\s+before\s+' + LEAD, re.I), False),
 ('after', re.compile(r'\s+after\s+' + LEAD, re.I), True),
 ('arrow', re.compile(r'\s*(?:→|⇒|➜|⟶|->)\s*' + LEAD, re.I), False),
 ('followed_by', re.compile(r'\s*,?\s*followed\s+by\s+' + LEAD, re.I), False),
 ('short_break', re.compile(r'\s*,\s*then,\s*after a short break,\s*' + LEAD, re.I), False),
)
RETURN_SUFFIX = re.compile(r'\s*(?:and\s+)?(?:be|get|come)\s+back\s+within\s+(?:\d+|one|two|three)\s+(?:minutes?|hours?)\s*',re.I)
FRONT = re.compile(r'\s*(after\s+(?:visiting|going\s+to)|before\s+going\s+to)\s+(?:the\s+|a\s+|an\s+)?',re.I)
BRIDGE = re.compile(r'\s*,\s*' + LEAD,re.I)


def relation(raw, owned, i, gap, prefix, tail):
    """Return anchored proof kind/direction/span, never skip arbitrary prose."""
    a,b=owned[i],owned[i+1]
    match=next(((kind, reverse, a[0], b[1]) for kind, pattern, reverse in GAPS if pattern.fullmatch(gap)),None)
    clause_start=max(raw.rfind(c,0,a[0]) for c in '.;!?')+1
    clause_end=min((p for c in '.;!?' if (p:=raw.find(c,b[1]))>=0),default=len(raw))
    clause_members=sum(clause_start<=s[0] and s[1]<=clause_end for s in owned)
    front=FRONT.fullmatch(raw[clause_start:a[0]])
    if front and clause_members==2 and BRIDGE.fullmatch(gap):
        match=('front_'+front[1].split()[0].casefold(),front[1].casefold().startswith('before'),clause_start+front.start(1),b[1])
    # Start/finish is supported only for exactly two extracted occurrences.
    if len(owned)==2 and re.fullmatch(r'\s*start with\s+(?:the\s+|a\s+)?',raw[:a[0]],re.I) and re.fullmatch(r'\s*,\s*finish at\s+(?:the\s+|a\s+)?',gap,re.I):
        match=('start_finish',False,len(raw)-len(raw.lstrip()),b[1])
    left=re.fullmatch(r'\s+(first|second|third)\s*[,;]\s*'+LEAD,gap,re.I)
    right=re.match(r'\s+(second|third|fourth|last)\b',tail,re.I)
    if left and right and (RANKS[right[1].lower()]==RANKS[left[1].lower()]+1 or len(owned)==2 and left[1].lower()=='first' and right[1].lower()=='last'):
        match=('adjacent_ranks',False,a[0],b[1]+right.end())
    # Prefix ordinals must be consecutive; named words remain inside owned spans.
    left_prefix=re.fullmatch(r'\s*(first|second|third)\s*,?\s*'+LEAD,prefix,re.I)
    right_prefix=re.fullmatch(r'\s*,\s*(second|third|fourth)\s*,?\s*'+LEAD,gap,re.I)
    if left_prefix and right_prefix and RANKS[right_prefix[1].lower()]==RANKS[left_prefix[1].lower()]+1:
        match=('prefix_ranks',False,a[0]-len(prefix),b[1])
    return match


def inspect_order(raw, ai):
    """Independent proof plus exact evidence containment; no output mutation.

    Recognize only adjacent source occurrences with anchored connector grammar.
    Transitive edges need a path whose complete proof spans fit the same quote.
    Unsupported wording is unknown, never permission to fill in a sequence.
    """
    result = {'version': VERSION, 'outcome': 'clarification_required',
        'orderingOnly': True, 'productionActivated': False, 'issues': [], 'proofs': [], 'edges': []}
    j = ai.journey
    if j is None:
        result['issues'].append('missing_journey_contract'); return result
    if j.order_conflict or [s.source for s in j.stops] != ai.activities:
        result['issues'].append('graph_or_activity_contract_conflict'); return result
    owned, error = bind_occurrences(raw, j.stops)
    if error:
        result['issues'].append(error); return result
    result['occurrences'] = [{'index': i, 'span': list(s), 'text': raw[s[0]:s[1]]} for i, s in enumerate(owned)]
    outside_mentions = raw
    for a, b in reversed(owned):
        outside_mentions = outside_mentions[:a] + ' ' * (b - a) + outside_mentions[b:]
    if RETRACTION.search(outside_mentions):
        result['issues'].append('retraction_or_flexible_scope_requires_review')
        return result
    unresolved = []
    proofs = []
    for i in range(len(owned) - 1):
        a, b = owned[i], owned[i + 1]
        gap = raw[a[1]:b[0]]
        # No cross-sentence/semicolon scope or arbitrary prose deletion.
        previous = owned[i - 1][1] if i else 0
        prefix = re.split(r'[.;!?]', raw[previous:a[0]])[-1].lstrip(' ,')
        tail_end = owned[i + 2][0] if i + 2 < len(owned) else len(raw)
        tail = re.split(r'[.;!?]', raw[b[1]:tail_end])[0]
        suffix = re.split(r'[,.;!?]', tail)[0].strip().casefold()
        suffixes = {'', 'again', 'first', 'second', 'third', 'fourth', 'last', 'now', 'today', 'tomorrow', 'tonight'}
        if ai.location:
            suffixes.update(('in ' + ai.location + ending).casefold()
                           for ending in ('', ' today', ' tomorrow', ' tonight'))
        suffix_ok = suffix in suffixes or any(pattern.fullmatch(tail) for _, pattern, _ in GAPS) or RETURN_SUFFIX.fullmatch(tail)
        match = relation(raw, owned, i, gap, prefix, tail)
        prefix_ok = (PREFIX.fullmatch(prefix) or any(pattern.fullmatch(' ' + prefix) for _, pattern, _ in GAPS)
            or re.fullmatch(r'first\s*,\s*' + LEAD, prefix, re.I))
        clause_start = max((raw.rfind(c, 0, a[0]) for c in '.;!?'), default=-1) + 1
        context_end = b[1] + len(tail)
        context = outside_mentions[clause_start:context_end]
        prefix_ok = prefix_ok or match and match[0] in ('front_after','front_before','start_finish','prefix_ranks')
        if match and prefix_ok and suffix_ok and not QUALIFIER.search(context):
            if j.stops[i].requirement != 'required' or j.stops[i + 1].requirement != 'required':
                unresolved.append('optional_relationship_requires_review'); continue
            kind, reverse, begin, end = match
            cue = CUE.search(outside_mentions[begin:end])
            proof = {'before': i + 1 if reverse else i, 'after': i if reverse else i + 1,
                'rule': kind, 'span': [begin,end],
                'cueSpan': [begin+cue.start(),begin+cue.end()], 'source':raw[begin:end]}
            proofs.append(proof)
        elif CUE.search(gap) or (CUE.search(prefix) and not any(
                {p['before'], p['after']} == {i - 1, i} for p in proofs)):
            unresolved.append('unproven_cue_scope')
    result['proofs'] = proofs
    if unresolved: result['issues'].extend(sorted(set(unresolved)))
    proposed = {(x.before, x.after) for x in j.order}
    for edge in j.order:
        quote_spans = spans(raw, edge.source)
        # Source evidence must cover the OWNED occurrences and actual relation
        # cue. Labels elsewhere in a broad quote cannot transfer cue ownership.
        usable = []
        for quote in quote_spans:
            contained = [(p['before'], p['after']) for p in proofs
                if quote[0] <= p['span'][0] and p['span'][1] <= quote[1]]
            if len(edge.source) <= 500 and reach(contained, edge.before, edge.after):
                usable.append(quote)
        okay = bool(usable)
        result['edges'].append({'before': edge.before, 'after': edge.after,
            'proven': okay, 'quoteSpans': [list(s) for s in usable],
            'reason': 'supported_path_inside_owned_quote' if okay else 'unproven_direction_scope_or_occurrence'})
        if not okay: result['issues'].append('unproven_model_edge')
    if any(not reach(proposed, p['before'], p['after']) for p in proofs):
        result['issues'].append('missing_proven_required_relationship')
    if j.clarification:
        result['issues'].append('existing_source_clarification_requires_review')
    result['issues'] = sorted(set(result['issues']))
    if not result['issues']:
        result['outcome'] = 'verified_order' if proofs else 'verified_no_mandatory_order'
    return result
