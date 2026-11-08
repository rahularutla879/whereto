"""Opt-in OFFLINE ordering proof experiment. Never imported by application/runner.

This is a bounded relation recognizer, not a replacement interpreter. It never
adds, removes or repairs an edge. Unknown scope/ownership requires clarification.
Passes concern ordering alone; canonical/source/other semantic gates still apply.
Offsets are Python Unicode code-point positions in the unmodified source.
"""
import re

VERSION = '52b-order-proof-v1-offline'
MAX_BINDING_WORK = 256
CUE = re.compile(r'\b(?:then|before|after|first|second|last|finally|afterward|followed)\b|→|⇒|➜|⟶|->', re.I)
QUALIFIER = re.compile(r"\b(?:no|not|never|unless|if|maybe|optional|optionally|whichever|whenever|either|or)\b|don't|do not", re.I)
RETRACTION = re.compile(r'\b(?:ignore|disregard|cancel|scratch|reverse)\b|\b(?:any order|never mind)\b', re.I)
LEAD = r'(?:(?:go|walk|drive|head)\s+to\s+|(?:get|visit|buy|have|play)\s+|stop\s+(?:at|for)\s+)?(?:the\s+|a\s+|an\s+)?'
PREFIX = re.compile(r'\s*' + LEAD + r'\s*', re.I)
GAPS = (
    ('then', re.compile(r'\s*,?\s*(?:and\s+)?(?:first\s*,?\s*)?(?:then|finally|afterward)\s+' + LEAD, re.I), False),
    ('rank_then', re.compile(r'\s+second\s*,\s*then\s+' + LEAD, re.I), False),
    ('before', re.compile(r'\s+before\s+' + LEAD, re.I), False),
    ('after', re.compile(r'\s+after\s+' + LEAD, re.I), True),
    ('arrow', re.compile(r'\s*(?:→|⇒|➜|⟶|->)\s*' + LEAD, re.I), False),
    ('followed_by', re.compile(r'\s*,?\s*followed\s+by\s+' + LEAD, re.I), False),
)


def spans(raw, phrase):
    if not phrase: return []
    found = []
    for match in re.finditer(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', raw, re.I):
        found.append(match.span())
        if len(found) == 65: break
    return found


def bind_occurrences(raw, stops):
    """Unique source-order assignment, not greedy first-match resolution.

    Overlapping shorter names cannot steal a mention of a longer supplied stop.
    Extra mentions/references can cause ambiguity; no model offset is trusted.
    """
    options = [spans(raw, s.source) for s in stops]
    if any(len(choices) > 64 for choices in options):
        return None, 'occurrence_binding_work_limit'
    for i, choices in enumerate(options):
        options[i] = [a for a in choices if not any(b[0] <= a[0] and a[1] <= b[1]
            and b != a for k, other in enumerate(options) if k != i for b in other)]
    answers = []
    work = 0
    def search(index, selected):
        nonlocal work
        work += 1
        if work > MAX_BINDING_WORK or len(answers) > 1:
            return
        if index == len(stops):
            answers.append(selected)
            return
        for span in options[index]:
            if not selected or span[0] >= selected[-1][1]:
                search(index + 1, selected + [span])
    search(0, [])
    if work > MAX_BINDING_WORK:
        return None, 'occurrence_binding_work_limit'
    if len(answers) != 1:
        return None, 'missing_or_ambiguous_occurrence_ownership'
    if {s for choices in options for s in choices} - set(answers[0]):
        return None, 'unowned_additional_stop_mentions'
    return answers[0], None


def reach(edges, start, end):
    pending = [start]; seen = set()
    while pending:
        node = pending.pop()
        if node == end: return True
        if node in seen: continue
        seen.add(node)
        pending.extend(b for a, b in edges if a == node)
    return False


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
        suffixes = {'', 'again', 'first', 'second', 'today', 'tomorrow', 'tonight'}
        if ai.location:
            suffixes.update(('in ' + ai.location + ending).casefold()
                           for ending in ('', ' today', ' tomorrow', ' tonight'))
        suffix_ok = suffix in suffixes or any(pattern.fullmatch(tail) for _, pattern, _ in GAPS)
        match = next(((kind, reverse) for kind, pattern, reverse in GAPS if pattern.fullmatch(gap)), None)
        # Explicit adjacent ranks: A first, B second. A bare `first` alone
        # never manufactures relationships to all other nearby activities.
        if re.fullmatch(r'\s+first\s*,\s*' + LEAD, gap, re.I) and re.match(r'\s+second\b', tail, re.I):
            match = ('adjacent_ranks', False)
        prefix_ok = (PREFIX.fullmatch(prefix) or any(pattern.fullmatch(' ' + prefix) for _, pattern, _ in GAPS)
            or re.fullmatch(r'first\s*,\s*' + LEAD, prefix, re.I))
        clause_start = max((raw.rfind(c, 0, a[0]) for c in '.;!?'), default=-1) + 1
        context = raw[clause_start:b[0]] + tail
        if match and prefix_ok and suffix_ok and not QUALIFIER.search(context):
            if j.stops[i].requirement != 'required' or j.stops[i + 1].requirement != 'required':
                unresolved.append('optional_relationship_requires_review'); continue
            kind, reverse = match
            cue = CUE.search(gap)
            cue_span = (a[1] + cue.start(), a[1] + cue.end())
            end = b[1]
            if kind == 'adjacent_ranks':
                end += re.match(r'\s+second\b', tail, re.I).end()
            proof = {'before': i + 1 if reverse else i, 'after': i if reverse else i + 1,
                'rule': kind, 'span': [a[0], end], 'cueSpan': list(cue_span),
                'source': raw[a[0]:end]}
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
