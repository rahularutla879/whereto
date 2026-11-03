"""Transient semantic requirements, never provider identities or routing evidence.

Indexes refer to source-order stop occurrences, not an optimized visit order.
An empty edge list means no user ordering requirement. Legacy activity lists
default to required discoverable stops; no optionality/order is invented.
"""
import re
from typing import Annotated, Literal
from pydantic import ConfigDict, Field, model_validator
from backend.models import ContractModel, Nonblank


class JourneyModel(ContractModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False,revalidate_instances='always')


class Duration(JourneyModel):
    minutes: int = Field(strict=True, ge=0, le=10080)
    relation: Literal['exact', 'minimum', 'maximum', 'under', 'approximate'] = 'exact'
    source: Nonblank = Field(max_length=500)


class RequestedStop(JourneyModel):
    source: Nonblank = Field(max_length=500)
    kind: Literal['activity', 'brand', 'named_place'] = 'activity'
    requirement: Literal['required', 'optional'] = 'required'
    evidence: str = Field(default='', max_length=500)
    duration: Duration | None = None


class OrderConstraint(JourneyModel):
    before: int = Field(strict=True, ge=0, le=31)
    after: int = Field(strict=True, ge=0, le=31)
    source: Nonblank = Field(max_length=500)


class Endpoint(JourneyModel):
    kind: Literal['origin', 'home', 'named_place', 'activity', 'brand']
    source: Nonblank = Field(max_length=500)


class Deadline(JourneyModel):
    source: Nonblank = Field(max_length=500)
    relation: Literal['by', 'before'] = 'by'
    # Populated only by deterministic source validation, never AI arithmetic.
    minute: int | None = Field(default=None, strict=True, ge=0, lt=1440)


class SharedPlace(JourneyModel):
    kind: Literal['same_mall'] = 'same_mall'
    stops: list[Annotated[int,Field(strict=True,ge=0,le=31)]] = Field(strict=True, min_length=2, max_length=32)
    source: Nonblank = Field(max_length=500)


class Journey(JourneyModel):
    stops: list[RequestedStop] = Field(default_factory=list, strict=True, max_length=32)
    order: list[OrderConstraint] = Field(default_factory=list, strict=True, max_length=64)
    ordering: Literal['unspecified', 'constrained', 'flexible'] = 'unspecified'
    endpoint: Endpoint | None = None
    total_duration: Duration | None = None
    deadline: Deadline | None = None
    shared_place: SharedPlace | None = None
    # Derived by validation, never a model assertion or permission to execute.
    order_conflict: bool = Field(default=False,strict=True)
    # Source-grounded ambiguity, e.g. incompatible order or mixed leg modes.
    clarification: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def consistent(self):
        if self.order and 'ordering' not in self.model_fields_set:
            self.ordering = 'constrained'
        self.order_conflict = bool(self.order) != (self.ordering == 'constrained')
        graph = {i: [] for i in range(len(self.stops))}
        if self.shared_place and (len(set(self.shared_place.stops)) != len(self.shared_place.stops) or any(type(i) is not int or i not in graph for i in self.shared_place.stops)):
            raise ValueError('Invalid shared-place stop references')
        for edge in self.order:
            if edge.before not in graph or edge.after not in graph or edge.before == edge.after:
                raise ValueError('Invalid stop occurrence reference')
            graph[edge.before].append(edge.after)
        visited = set()
        def visit(i, path):
            if i in path:
                self.order_conflict = True
                return
            if i in visited:
                return
            for j in graph[i]:
                visit(j, path | {i})
            visited.add(i)
        for i in graph:
            visit(i, set())
        return self


LIMITATION = "We understand your stops and requirements, but advanced route planning for this kind of trip is still being added."
REPHRASE = "Some stop or timing instructions are unclear or conflict. Please edit the request to clarify them; your original text is kept."

# Bounded omission guards complement the model; they never generate stops.
ADVANCED = re.compile(r'\b(?:return|back home|head home|go home|(?:head|get|come|go) back|where I started|finish at|end at|maybe|optionally|optional|if there.s time|if time permits|whichever|on the way back|half an hour|at least an hour|about (?:\w+|\d+) hours?|by \d)\b', re.I)
NAMED_REFERENCE = re.compile(r'\b(?:[Gg]o to|[Vv]isit|[Ss]top at)\s+(?:the\s+)?([A-Z][\w’-]+(?:\s+(?:[A-Z][\w’-]+|of|the|on|at|\d+)\b){1,8})')
NUMBERS = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twenty':20,'thirty':30,'forty':40,'forty-five':45,'sixty':60,'an':1,'a':1,'half':.5}
DURATION_WORDING = re.compile(r'(?<![\w.])(-?(?:\d+(?:\.\d+)?|'+'|'.join(NUMBERS)+r'))\s+(?:of\s+)?(?:an?\s+)?(hours?|minutes?|mins?|hrs?)\b', re.I)


def duration_value(source):
    matches = list(DURATION_WORDING.finditer(source))
    if not matches:
        return None
    total = 0
    for match in matches:
        token=match[1].lower().lstrip('-')
        n = (float(token) if re.fullmatch(r'\d+(?:\.\d+)?',token) else NUMBERS[token]) * (-1 if match[1].startswith('-') else 1)
        total += n * (60 if match[2].lower().startswith('h') else 1)
    return total


def duration_relation(source):
    if re.search(r'\b(?:at least|minimum|no less than)\b', source, re.I): return 'minimum'
    if re.search(r'\b(?:under|less than)\b', source, re.I): return 'under'
    if re.search(r'\b(?:about|around|roughly|approximately)\b', source, re.I): return 'approximate'
    if re.search(r'\b(?:within|at most|maximum|up to|no more than)\b', source, re.I): return 'maximum'
    if re.search(r'\b(?:I|we) have\b|\b(?:finish|return|back)\b.*\bin\s+',source,re.I): return 'maximum'
    return 'exact'


def normalize_explicit_durations(raw, guarded, journey):
    """Recover explicit time evidence after valid AI stop extraction.

    This mirrors existing raw-date/verbatim-travel normalization. It never runs
    after AI failure, selects venues/stops, invents minutes or guesses between
    competing stop associations. Existing conflicting values are not overwritten.
    """
    boundaries=list(re.finditer(r'\b(?:and|then|before|after)\b|[,;!?]|(?<!\d)\.(?!\d)',raw,re.I))
    for match in DURATION_WORDING.finditer(guarded):
        prefix=raw[:match.start()]
        operator=re.search(r'\b(?:at least|minimum|no less than|at most|under|less than|no more than|up to|about|around|roughly|approximately|within|in under|in less than)\s*$',prefix,re.I)
        start=operator.start() if operator else match.start()
        phrase=raw[start:match.end()]
        minutes=duration_value(phrase)
        if minutes is None or minutes<0 or minutes>10080 or isinstance(minutes,float) and not minutes.is_integer():
            continue
        before=raw[max(0,start-120):start]
        whole=re.search(r'\b(?:(?:I|we) have|finish (?:everything|all(?: errands| stops| activities)?|(?:the )?(?:whole )?(?:outing|trip|journey)))\b[^.;!?]*$',before,re.I)
        endpoint=journey.endpoint
        returning=bool(endpoint and endpoint.kind in ('home','origin') and endpoint.source.casefold() in before.casefold()
                       and (operator or re.search(r'\bin\s*$',before,re.I)))
        if whole or returning:
            if journey.total_duration is None:
                if not operator:
                    begin=max(0,start-120)+(whole.start() if whole else before.casefold().rfind(endpoint.source.casefold()))
                    phrase=raw[begin:match.end()]
                if len(phrase)<=500:
                    journey.total_duration=Duration(minutes=int(minutes),relation=duration_relation(phrase),source=phrase)
            continue
        left=max((b.end() for b in boundaries if b.end()<=match.start()),default=0)
        right=min((b.start() for b in boundaries if b.start()>=match.end()),default=len(raw))
        clause=raw[left:right].strip()
        candidates=[s for s in journey.stops if s.source.casefold() in clause.casefold()]
        if len(candidates)!=1 or candidates[0].duration is not None or len(DURATION_WORDING.findall(clause))!=1:
            continue
        dwell=(re.search(r'\bspend(?:ing)?\b',clause,re.I)
               or re.search(r'\bfor\s*$',raw[left:start],re.I)
               or re.match(r'\s+(?:at|on)\b',raw[match.end():right],re.I))
        if dwell and len(clause)<=500 and not re.search(r'\b(?:drive|driving|walk|walking|travel)\b',clause,re.I):
            candidates[0].duration=Duration(minutes=int(minutes),relation=duration_relation(clause),source=clause)


def normalize_extracted_references(raw, ai):
    """Normalize only AI-supplied verbatim references, never discover missing stops.

    Like activity aliases and verbatim travel repair, these repairs have exact
    source evidence. Missing/unrecognized constraints still fail validation.
    """
    j = ai.journey
    if not j or [s.source.casefold() for s in j.stops] != [p.casefold() for p in ai.activities]:
        return
    if j.order_conflict:
        return
    if any(s.source.casefold() not in raw.casefold() for s in j.stops):
        return
    generic = {'bank','grocery store','groceries','grocery shopping','supermarket',
               'pharmacy','atm','coffee','coffee shop','museum','dinner','lunch','food','drinks','movie'}
    cursor = 0
    for i,stop in enumerate(j.stops):
        match = re.search(re.escape(stop.source),raw[cursor:],re.I)
        found=cursor+match.start() if match else None
        if match:
            stop.source=match[0]
            ai.activities[i]=match[0]
            cursor += match.end()
        indefinite = found is not None and stop.source.islower() and re.search(r'\b(?:a|an|any)\s+$',raw[:found],re.I)
        if stop.source.casefold() in generic and (stop.kind=='brand' or stop.kind=='named_place' and indefinite):
            stop.kind = 'activity'
    # A model-extracted final 'go home' is an endpoint, not venue discovery.
    if j.stops:
        last=j.stops[-1]
        home = re.fullmatch(r'(?:go|head|return|come back|get back)\s+home',last.source,re.I)
        origin = re.fullmatch(r'(?:head|get|come|go) back',last.source,re.I)
        matching_endpoint = not j.endpoint or j.endpoint.kind in ('home','origin') and last.source.casefold() in j.endpoint.source.casefold()
        if last.requirement=='required' and (home or origin) and matching_endpoint:
            index=len(j.stops)-1
            if any(e.before==index for e in j.order):
                return
            if not j.endpoint:
                j.endpoint=Endpoint(kind='home' if home else 'origin',source=last.source)
            j.stops.pop();ai.activities.pop()
            j.order=[e for e in j.order if e.after!=index]
            if not j.order and j.ordering=='constrained':j.ordering='unspecified'
    if j.endpoint:
        # Full clauses and bare final names are equivalent only when the exact
        # final-destination clause occurs in the request.
        phrase=re.search(r'\b(?:finish|end|head)\s+(?:at|to)\s+'+re.escape(j.endpoint.source)+r'\b',raw,re.I)
        if phrase:j.endpoint.source=phrase[0]
        if (j.endpoint.kind=='origin' and re.search(r'\bhome\b',j.endpoint.source,re.I)
                and not re.search(r'\b(?:start|starting|started|origin)\b',j.endpoint.source,re.I)):
            # An unresolved home can never acquire origin identity from AI.
            j.endpoint.kind='home'


def is_reference_occurrence(raw, ai, match):
    """A relationship/location reference is not another requested occurrence."""
    if ai.location:
        for area in re.finditer(re.escape(ai.location),raw,re.I):
            label=re.split(r'\b(?:and|then)\b',area[0],maxsplit=1,flags=re.I)[0]
            if area.start()<=match.start()<area.start()+len(label) and re.search(r'\b(?:in|near|around)\s+(?:the\s+)?$',raw[:area.start()],re.I):
                return True
    for origin in re.finditer(r'\b(?:start|starting) from\s+([^.,;!?]+)',raw,re.I):
        label=re.split(r'\b(?:and|then)\b',origin[1],maxsplit=1,flags=re.I)[0]
        if origin.start(1)<=match.start()<origin.start(1)+len(label):
            return True
    if ai.journey:
        endpoint=ai.journey.endpoint
        if endpoint:
            # Only the final reference is excluded, not earlier activities in
            # an overly broad model-copied endpoint clause.
            cues=list(re.finditer(r'\b(?:finish|end|finally|head|go|return|back)\b(?:\s+(?:at|to))?\s+',endpoint.source,re.I))
            if cues:
                suffix=endpoint.source[cues[-1].end():]
                name=re.split(r'\b(?:and|then)\b|[,;.]',suffix,maxsplit=1,flags=re.I)[0].strip()
                for final in re.finditer(re.escape(endpoint.source),raw,re.I):
                    begin=final.start()+cues[-1].end()
                    if name and begin<=match.start()<begin+len(name):return True
        for edge in ai.journey.order:
            a,b=ai.journey.stops[edge.before].source,ai.journey.stops[edge.after].source
            for pattern in (re.escape(a)+r'\s+before\s+(?:the\s+)?'+re.escape(b),
                            re.escape(b)+r'\s+after\s+(?:the\s+)?'+re.escape(a)):
                for clause in re.finditer(pattern,raw,re.I):
                    if clause.start()<=match.start()<clause.end():return True
    return False


def validate_journey(raw, ai):
    """Return (blocking explanation, needs clarification). Never repairs by guessing."""
    j = ai.journey
    # Existing first/between/total-travel scopes are not journey durations.
    from backend.location_policy import first_intent
    from backend.between_policy import between_intent
    from backend.travel_constraints import travel_evidence
    _, first_spans, _ = first_intent(raw)
    _, between_spans, _ = between_intent(raw)
    spans = [(a,b) for a,b,_ in first_spans] + [(a,b) for a,b,*_ in between_spans]
    spans += [x['span'] for x in travel_evidence(raw)]
    guarded = raw
    for a,b in sorted(spans,reverse=True): guarded = guarded[:a]+' '*(b-a)+guarded[b:]
    if j is None:
        if ADVANCED.search(guarded) or DURATION_WORDING.search(guarded) or NAMED_REFERENCE.search(guarded): return REPHRASE, True
        return None, False
    normalize_extracted_references(raw, ai)
    normalize_explicit_durations(raw,guarded,j)
    # Qwen sometimes encodes a plain source-order list as forward edges. Those
    # edges add nothing to the legacy source-order contract. Remove only this
    # redundant representation, never reversed/cyclic or explicitly ordered intent.
    from backend.date_resolution import DATE_WORDING, TIME_WORDING
    order_words = TIME_WORDING.sub(' ', DATE_WORDING.sub(' ', guarded))
    if (j.order and not j.order_conflict and j.ordering=='constrained'
            and not re.search(r'\b(?:first|then|after|before|finally|afterward|followed|order)\b',order_words,re.I)
            and all(e.before<e.after and e.source.casefold() in raw.casefold()
                    and j.stops[e.before].source.casefold() in e.source.casefold()
                    and j.stops[e.after].source.casefold() in e.source.casefold() for e in j.order)):
        j.order=[]
        j.ordering='unspecified'
    if any(duration_value(m[0])<0 or re.search(r'\b(?:minus|negative)\s*$',guarded[:m.start()],re.I) for m in DURATION_WORDING.finditer(guarded)):
        return REPHRASE, True
    def grounded(s): return bool(s) and s.casefold() in raw.casefold()
    if [s.source for s in j.stops] != ai.activities:
        return REPHRASE, True
    sources = [s.source for s in j.stops] + [e.source for e in j.order]
    sources += [s.evidence for s in j.stops if s.evidence]
    sources += [x.source for x in [j.endpoint, j.total_duration, j.deadline, j.shared_place] if x]
    if j.clarification: sources.append(j.clarification)
    durations = [s.duration for s in j.stops if s.duration] + ([j.total_duration] if j.total_duration else [])
    sources += [d.source for d in durations]
    if not all(grounded(s) for s in sources): return REPHRASE, True
    if j.order_conflict:
        return REPHRASE, True
    from backend.travel_mode import resolve_mode, PATTERNS
    mode, mode_issues = resolve_mode(raw, ai.transport)
    if mode_issues:
        if any('mixed travel modes' in issue for issue in mode_issues):
            ai.transport = None
        return mode_issues[0], True
    if mode and re.search(PATTERNS[mode.value],raw,re.I):
        ai.transport = mode
    if j.shared_place and not re.search(r'\bsame mall\b',j.shared_place.source,re.I): return REPHRASE, True
    if len(j.stops)>1 and re.search(r'\bsame mall\b',raw,re.I) and not j.shared_place:
        return REPHRASE, True
    if any(not any(m[0].casefold() in d.source.casefold() for d in durations) for m in DURATION_WORDING.finditer(guarded)):
        return REPHRASE, True
    cursor = 0
    activity_spans=[]
    for s in j.stops:
        found = raw.casefold().find(s.source.casefold(), cursor)
        if found < 0:
            # Existing repeated-stop convention: one phrase plus an explicit
            # repetition count is allowed; otherwise no invented occurrences.
            repeated = re.search(re.escape(s.source)+r'\s+(twice|two times|2 times|three times|3 times)\b',raw,re.I)
            count = sum(x.source.casefold()==s.source.casefold() for x in j.stops)
            if not repeated or count != (3 if repeated[1].lower() in ('three times','3 times') else 2):
                return REPHRASE, True
        else:
            cursor = found + len(s.source)
            activity_spans.append((found,cursor))
    from backend.interpretation import OCCURRENCES
    from backend.travel_mode import is_walking_route_phrase
    for occurrence in OCCURRENCES.finditer(guarded):
        if occurrence[0].casefold()=='play' and re.match(r'\s+(?:a\s+)?(?:movie|film|soccer|basketball|football|hockey|baseball)\b',raw[occurrence.end():],re.I):continue
        if occurrence[0].casefold()=='walking' and ai.transport is not None:continue
        if is_walking_route_phrase(raw,occurrence.start(),occurrence.end()) or is_reference_occurrence(raw,ai,occurrence):continue
        if not any(a<occurrence.end() and occurrence.start()<b for a,b in activity_spans):
            return REPHRASE, True
    for d in durations:
        if 'relation' not in d.model_fields_set:
            d.relation=duration_relation(d.source)
        if duration_value(d.source) != d.minutes or duration_relation(d.source) != d.relation:
            return REPHRASE, True
        if re.search(r'\b(?:travel|driv\w*|walk\w*|between stops|first stop)\b', d.source, re.I):
            return REPHRASE, True
    if j.total_duration:
        evidence=travel_evidence(raw)
        for field,scope in [('travel_total_minutes','total'),('travel_leg_minutes','leg')]:
            if getattr(ai,field)==j.total_duration.minutes and not any(e['scope']==scope for e in evidence):
                return REPHRASE, True
    if any(re.fullmatch(r'(?:all |some )?errands',s.source,re.I) for s in j.stops) or not j.stops and re.search(r'\berrands\b',raw,re.I):
        return "Which errands would you like to include? Please name the stops in your request; your timing requirement is kept.", True
    if any(s.kind=='named_place' and re.fullmatch(r'(?:the )?(?:college|school|university)',s.source,re.I) for s in j.stops):
        return "Which college or destination do you mean? Please name it in your request; your other stops are kept.", True
    for s in j.stops:
        if s.duration:
            if j.total_duration and raw.casefold().count(s.duration.source.casefold())==1 and (s.duration.source.casefold() in j.total_duration.source.casefold() or j.total_duration.source.casefold() in s.duration.source.casefold()):
                return REPHRASE, True
            clauses = re.split(r'\b(?:and|then|before|after)\b|[,;]|(?<!\d)\.(?!\d)',raw,flags=re.I)
            if not any(s.source.casefold() in c.casefold() and s.duration.source.casefold() in c.casefold() for c in clauses):
                return REPHRASE, True
        # A precise establishment/branch may not be downgraded to discovery.
        if (re.search(r'\bon (?:Route\s+\d+|\w+ (?:Street|Road|Avenue))\b', s.source, re.I)
                and s.kind != 'named_place'):
            return REPHRASE, True
        if s.requirement == 'optional' and (s.source.casefold() not in s.evidence.casefold() or not re.search(r'\b(?:maybe|optional|if|perhaps|might)\b', s.evidence, re.I)):
            return REPHRASE, True
        if s.requirement == 'optional':
            cue=re.search(r'\b(?:maybe|optional|if|perhaps|might)\b',s.evidence,re.I)
            start=s.evidence.casefold().find(s.source.casefold())
            if cue and start>cue.end() and re.search(r'\b(?:before|after|then|and)\b',s.evidence[cue.end():start],re.I):
                return REPHRASE, True
        if s.requirement == 'required' and re.search(r'\b(?:maybe|optionally|if there.s time|if time permits)\b', s.evidence, re.I):
            return REPHRASE, True
    if j.deadline:
        if not re.search(r'\b(?:by|before)\b',j.deadline.source,re.I) or not re.search(r'\b(?:back|return|finish|end|everything|whole (?:trip|journey))\b',raw,re.I):
            return REPHRASE, True
        m = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b', j.deadline.source, re.I)
        if not m or not 1 <= int(m[1]) <= 12 or int(m[2] or 0)>59: return REPHRASE, True
        minute = (int(m[1]) % 12 + (12 if m[3].upper()=='PM' else 0))*60+int(m[2] or 0)
        if j.deadline.minute not in (None, minute): return REPHRASE, True
        if j.deadline.relation != ('before' if re.search(r'\bbefore\b',j.deadline.source,re.I) else 'by'):
            return REPHRASE, True
        j.deadline.minute = minute
    if j.endpoint:
        home_origin = bool(re.search(r'\b(?:start|starting|leave|leaving)\s+(?:from|at)\s+(?:(?:my|our)\s+)?home\b',raw,re.I))
        if j.endpoint.kind=='home' and home_origin:
            j.endpoint.kind='origin'
        expected = {'origin':r'\b(?:return|back)\b.*\b(?:origin|start|starting|started)\b|^(?:head|get|come|go) back$',
                    'home':r'\bhome\b',
                    'named_place':r'\b(?:finish|end|finally|head|go|return|back)\b',
                    'activity':r'\b(?:finish|end|finally|head|go)\b',
                    'brand':r'\b(?:finish|end|finally|head|go)\b'}
        bare_return = j.endpoint.kind=='origin' and j.endpoint.source.casefold()=='return' and bool(re.search(r'\breturn(?:\s+(?:within|in|by|before)\b|[.!]?\s*$)',raw,re.I))
        if not bare_return and not re.search(expected[j.endpoint.kind], j.endpoint.source, re.I) and not (j.endpoint.kind=='origin' and home_origin and re.search(r'\bhome\b',j.endpoint.source,re.I)):
            return REPHRASE, True
        if j.endpoint.kind=='origin' and not home_origin and re.search(r'\bhome\b',j.endpoint.source,re.I) and not re.search(r'\b(?:start|starting|started|origin)\b', j.endpoint.source,re.I):
            return REPHRASE, True
        if j.endpoint.kind in ('activity','brand') and re.search(r'\b(?:at|to)\s+[A-Z][\w’-]+\s+[A-Z][\w’-]+|\bon Route\s+\d+',j.endpoint.source):
            return REPHRASE, True
    for edge in j.order:
        if not re.search(r'\b(?:first|then|after|before|finally|afterward|followed)\b',edge.source,re.I):
            return REPHRASE, True
        a,b = j.stops[edge.before].source,j.stops[edge.after].source
        if a.casefold() not in edge.source.casefold() or b.casefold() not in edge.source.casefold():
            return REPHRASE, True
        wrong = (re.escape(a)+r'\s+after\s+(?:the\s+)?'+re.escape(b),
                 re.escape(b)+r'\s+before\s+(?:the\s+)?'+re.escape(a))
        if any(re.search(p,edge.source,re.I) for p in wrong): return REPHRASE, True
    # Detect the common irreconcilable A-before-B / B-before-A form even when
    # a model keeps only one edge. Never select one requirement over another.
    for i,a in enumerate(j.stops):
        for b in j.stops[i+1:]:
            def before(x,y):
                return bool(re.search(re.escape(x)+r'\s+before\s+(?:the\s+)?'+re.escape(y),raw,re.I))
            if before(a.source,b.source) and before(b.source,a.source) and not j.clarification:
                return REPHRASE, True
    # Missing semantic objects must not pass merely because JSON was valid.
    checks = [
        (r'\b(?:return|back home|head home|go home|(?:head|get|come|go) back|where I started)\b', bool(j.endpoint)),
        (r'\b(?:finish at|end at)\b', bool(j.endpoint)),
        (r'\b(?:maybe|optionally|if there.s time|if time permits)\b', any(s.requirement=='optional' for s in j.stops)),
        (r'\b(?:whichever|any order)\b', j.ordering=='flexible'),
        (r'\b(?:spend|for (?:five|twenty|\d+) minutes)\b', bool(durations)),
        (r'\b(?:within|in under|less than|about)\s+(?:\d+|half|two)\s+(?:an?\s+)?(?:minutes?|hours?)\b', bool(j.total_duration or durations)),
        (r'\bby\s+\d', bool(j.deadline)),
        (r'\b(?:back|return|finish|end)\b[^.;]{0,80}\bbefore\s+\d', bool(j.deadline)),
    ]
    from backend.date_resolution import DATE_WORDING, TIME_WORDING
    order_raw = TIME_WORDING.sub(' ',DATE_WORDING.sub(' ',guarded))
    if len(j.stops)>1 and re.search(r'\b(?:then|afterward|before|after|first|finally)\b',order_raw,re.I) and not (j.order or j.ordering=='flexible' or j.clarification):
        return REPHRASE, True
    for pattern, present in checks:
        if re.search(pattern, raw, re.I) and not present and not j.clarification:
            # Travel-only wording remains validated by existing source checks.
            if 'minutes' in pattern and re.search(r'\btravel|between stops|first stop\b', raw, re.I): continue
            return REPHRASE, True
    # Bounded proper-name omissions: the original exact reference must survive
    # in a stop or endpoint. This detects omissions; it does not create a stop.
    for match in NAMED_REFERENCE.finditer(raw):
        named = match[1]
        if not any(named.casefold() in s.source.casefold() and s.kind=='named_place' for s in j.stops) and not (j.endpoint and named.casefold() in j.endpoint.source.casefold()):
            return REPHRASE, True
    if j.clarification: return REPHRASE, True
    # Home is a distinct unresolved endpoint, never inferred from device origin.
    if j.endpoint and j.endpoint.kind=='home':
        return "Where should the outing end? Please name home in your request or say ‘return to my starting point’ if that is what you mean.", True
    from backend.retail import intent as retail_intent
    unhandled_brand = any(s.kind=='brand' and not ((retail := retail_intent(s.source)) and retail.brands) for s in j.stops)
    advanced = (any(s.kind=='named_place' or s.requirement=='optional' or s.duration for s in j.stops)
                or unhandled_brand or j.endpoint or j.total_duration or j.deadline or j.shared_place or j.ordering=='flexible'
                or any(e.before>e.after for e in j.order))
    # A partial order cannot be enforced by the legacy linear planner.
    edge_pairs = {(e.before,e.after) for e in j.order}
    if j.order and not all((i,i+1) in edge_pairs for i in range(len(j.stops)-1)):
        advanced = True
    return (LIMITATION, False) if advanced else (None, False)
