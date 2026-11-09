"""One extracted legacy duration normalizer; no new semantic rules."""

def normalize_explicit_durations(raw, guarded, journey):
    """Recover explicit time evidence after valid AI stop extraction.

    This mirrors existing raw-date/verbatim-travel normalization. It never runs
    after AI failure, selects venues/stops, invents minutes or guesses between
    competing stop associations. Existing conflicting values are not overwritten.
    """
    from backend import journey as legacy
    boundaries=list(legacy.re.finditer(r'\b(?:and|then|before|after)\b|[,;!?]|(?<!\d)\.(?!\d)',raw,legacy.re.I))
    for match in legacy.DURATION_WORDING.finditer(guarded):
        prefix=raw[:match.start()]
        operator=legacy.re.search(r'\b(?:at least|minimum|no less than|at most|under|less than|no more than|up to|about|around|roughly|approximately|within|in under|in less than)\s*$',prefix,legacy.re.I)
        start=operator.start() if operator else match.start()
        phrase=raw[start:match.end()]
        minutes=legacy.duration_value(phrase)
        if minutes is None or minutes<0 or minutes>10080 or isinstance(minutes,float) and not minutes.is_integer():
            continue
        before=raw[max(0,start-120):start]
        whole=legacy.re.search(r'\b(?:(?:I|we) have|finish (?:everything|all(?: errands| stops| activities)?|(?:the )?(?:whole )?(?:outing|trip|journey)))\b[^.;!?]*$',before,legacy.re.I)
        endpoint=journey.endpoint
        returning=bool(endpoint and endpoint.kind in ('home','origin') and endpoint.source.casefold() in before.casefold()
                       and (operator or legacy.re.search(r'\bin\s*$',before,legacy.re.I)))
        # A bare, explicit return clause has a whole-trip budget even while
        # its endpoint is awaiting the user's confirmation. No endpoint is invented.
        bare_back=bool(operator and legacy.unresolved_return_clause(raw) and legacy.re.search(r'\b(?:return|(?:be|get|come|go|head) back)\s*$',before,legacy.re.I))
        if whole or returning or bare_back:
            if journey.total_duration is None:
                if not operator:
                    begin=max(0,start-120)+(whole.start() if whole else before.casefold().rfind(endpoint.source.casefold()))
                    phrase=raw[begin:match.end()]
                if len(phrase)<=500:
                    journey.total_duration=legacy.Duration(minutes=int(minutes),relation=legacy.duration_relation(phrase),source=phrase)
            continue
        left=max((b.end() for b in boundaries if b.end()<=match.start()),default=0)
        right=min((b.start() for b in boundaries if b.start()>=match.end()),default=len(raw))
        clause=raw[left:right].strip()
        candidates=[s for s in journey.stops if s.source.casefold() in clause.casefold()]
        if len(candidates)!=1 or candidates[0].duration is not None or len(legacy.DURATION_WORDING.findall(clause))!=1:
            continue
        dwell=(legacy.re.search(r'\bspend(?:ing)?\b',clause,legacy.re.I)
               or legacy.re.search(r'\bfor\s*$',raw[left:start],legacy.re.I)
               or legacy.re.match(r'\s+(?:at|on)\b',raw[match.end():right],legacy.re.I))
        if dwell and len(clause)<=500 and not legacy.re.search(r'\b(?:drive|driving|walk|walking|travel)\b',clause,legacy.re.I):
            candidates[0].duration=legacy.Duration(minutes=int(minutes),relation=legacy.duration_relation(clause),source=clause)
