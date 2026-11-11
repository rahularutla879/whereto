"""Python-only development boundary for source-proven V5.1 journeys."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re

from backend.date_resolution import DATE_WORDING, resolve_datetime
from backend.interpretation import (ALIASES, LOCATION_QUESTION, InterpretationContext,
                                    InterpretationResult, activity_category)
from backend.journey import DURATION_WORDING, LIMITATION, REPHRASE, duration_relation, duration_value
from backend.location_policy import geographic_intent
from backend.travel_mode import resolve_mode
from backend.validation_phases import validate_legacy
from scripts import task52_ordering_v51 as ordering
from scripts.task52_ordering_v5 import DANGER, GAP, GLOBAL_UNORDERED, LEAD, PREFIX


# Only recognize complete terminal clauses. A supplied location still needs
# ordinary provider verification; a bound phrase is not a resolved place.
NAME = re.compile(r"(?:[A-Z][\w’'-]*(?:\s+(?:[A-Z][\w’'-]*|of|the|at|in|[0-9]+))*)")
AREA = re.compile(r"[^\W\d_]+(?:[ ’'\-]+[^\W\d_]+){0,5}", re.UNICODE)
CONTEXT_WORDS = re.compile(
    r'\b(?:and|aur|then|before|after|maybe|optional|whenever|return|finish|home|'
    r'within|budget|spend|under|over|car|foot|driving|walking|today|tomorrow|tonight|'
    r'please|must|need|only|near|from|with|for|excluding|exclude|avoid|afterward|'
    r'at night|in the morning|afterwards|include|add|visit|where|when)\b', re.I)
ORIGIN = re.compile(r'return to (?:where I started|the starting point|my starting point)', re.I)
TERMINAL = re.compile(r'(?:finish|end) at (?P<place>.+)', re.I)
MODE = re.compile(r'(?:by car|on foot|by foot|driving)', re.I)
FLEXIBLE = re.compile(r'\s+whenever convenient\b', re.I)
BINARY = re.compile(r'\s+(?:before|after)\s+' + LEAD, re.I)
INDEPENDENT = re.compile(r'\s*[,;]\s*(?:and\s+)?' + LEAD, re.I)
ACTIVITY_LABELS = ALIASES.keys() | {'coffee shop', 'coffee shops'}
NAMED_VISIT = re.compile(
    r'\b(?:visit|go to|head to|walk to|drive to|stop at|start at|finish at)\s+(?:the\s+)?$', re.I)
SEPARATOR = r'\s*(?:[,;]\s*)?'


@dataclass(frozen=True)
class DevelopmentValidation:
    result: InterpretationResult = field(repr=False)
    raw_snapshot: bytes | None = field(repr=False)
    legacy_snapshot: bytes = field(repr=False)
    disposition: str


@dataclass(frozen=True)
class TerminalContext:
    ordering_end: int
    date: str | None
    mode: str | None
    endpoint: str | None
    duration: str | None


def _run_legacy(value, extraction, now):
    class SuppliedExtraction:
        def interpret(self, text):
            if text != value.text:
                raise ValueError('Development extraction source changed')
            return extraction

    return validate_legacy(value, SuppliedExtraction(), now=now)


def interpret_for_development(value, *, extraction, now=None, preserve_order=False):
    if not preserve_order:
        return _run_legacy(value, extraction, now).result
    return validate_for_development(value, extraction=extraction, now=now).result


def validate_for_development(value, *, extraction, now=None):
    """Validate a fresh supplied extraction and keep the two input views apart."""
    if (value.pending is not None or value.hasCurrentLocation
            or value.preferences.model_dump(exclude_defaults=True)
            or value.answers.model_dump(exclude_defaults=True)):
        raise ValueError('This development profile requires fresh source text without overrides')
    reference = now if now is not None else datetime.now(timezone.utc)
    legacy = _run_legacy(value, extraction, reference)
    raw = legacy.raw_model
    result = legacy.result

    def finish(candidate, disposition):
        return DevelopmentValidation(candidate, legacy.raw_snapshot, result.model_dump_json().encode(), disposition)

    def block(reason):
        return finish(result.model_copy(update={
            'interpretation': raw or result.interpretation, 'executionStatus': 'clarification_required', 'issues': [REPHRASE],
            'notes': [], 'unsupported': [], 'questions': [], 'request': None,
            'pending': None, 'advancedToken': None,
        }), reason)

    if raw is None or not raw.journey or not 2 <= len(raw.journey.stops) <= 4 or not _labels_supported(raw):
        return block('unsupported_stops')
    source = value.text
    proof = ordering.inspect_order(source, raw)
    if proof['source']['category'] == 'contradictory':
        return block('contradictory_order')
    occurrences, error = ordering.bind_occurrences(source, raw.journey.stops)
    if error or not _same_occurrences(legacy, occurrences):
        return block('unresolved_occurrences')
    if any(stop.kind == 'named_place' and not NAMED_VISIT.search(source[:start])
           for stop, (start, _) in zip(raw.journey.stops, occurrences)):
        return block('unproved_named_visit')
    if len({(e.before, e.after) for e in raw.journey.order}) != len(raw.journey.order):
        return block('duplicate_edge')

    terminal = _terminal_context(source, occurrences[-1][1], raw)
    if terminal is None:
        return block('unsupported_context')
    order_text = source[:terminal.ordering_end]
    if proof['trustedGraph'] is None:
        # The prefix preserves original offsets and exact quotes. A quote
        # crossing removed context is never rewritten to make it pass.
        proof = ordering.inspect_order(order_text, raw)
    if proof['trustedGraph'] is None or not _complete_order_clause(order_text, occurrences, proof):
        return block('unproved_order')

    context, expected = _validate_context(source, raw, terminal, reference)
    if context is None or value.calendarTimezone not in (None, context.timezone):
        return block('unverified_constraints')
    effective = result.interpretation
    if effective != expected:
        # Recognize only the legacy all-edges deletion. Compare the entire
        # remaining interpretation before copying any original edges back.
        dropped = expected.model_copy(deep=True)
        dropped.journey.order = []
        dropped.journey.ordering = 'unspecified'
        if not expected.journey.order or effective != dropped:
            return block('unexpected_effective_change')

    if result.executionStatus == 'advanced_unavailable':
        if (result.context != context or result.request is not None or result.issues != [LIMITATION]
                or result.unsupported != [LIMITATION] or result.notes or result.questions):
            return block('unverified_advanced_context')
    elif not _compatible_ordinary(result, context, expected):
        return block('legacy_validation_blocked')

    pending = result.pending
    if (result.advancedToken is not None or pending is None or pending.interpretation != effective
            or pending.text != source or pending.referenceTime != reference
            or pending.answers.model_dump(exclude_defaults=True)):
        return block('unverified_legacy_disposition')

    # Ordinary legacy planning is linear. Use the same existing advanced
    # handoff for all proved graphs so flexibility and repeats stay explicit.
    preserved = result.model_copy(deep=True)
    preserved.interpretation = expected
    preserved.pending.interpretation = expected.model_copy(deep=True)
    preserved.context = context
    preserved.executionStatus = 'advanced_unavailable'
    preserved.issues = preserved.unsupported = [LIMITATION]
    preserved.notes = []
    preserved.questions = []
    preserved.request = None
    return finish(preserved, 'source_order_preserved')


def _labels_supported(raw):
    journey = raw.journey
    return [s.source for s in journey.stops] == raw.activities and all(
        (s.kind == 'activity' and s.source.casefold() in ACTIVITY_LABELS)
        or (s.kind == 'named_place' and _is_name(s.source) and s.source.casefold() not in ACTIVITY_LABELS)
        for s in journey.stops
    )


def _is_name(text):
    return (len(text) <= 100 and NAME.fullmatch(text) and not DANGER.search(text)
            and not CONTEXT_WORDS.search(text) and not DATE_WORDING.search(text))


def _same_occurrences(legacy, occurrences):
    p = legacy.preparation
    return (p is not None and p.source_kind == 'raw_model'
            and len(p.mapping) == len(p.occurrences) == len(occurrences)
            and all(item.status == 'same_source_span' and item.original_index == item.effective_index == i
                    and tuple(occurrences[i]) == p.occurrences[i].span
                    and p.occurrences[i].evidence_status != 'unresolved'
                    for i, item in enumerate(p.mapping)))


def _terminal_context(source, start, raw):
    tail = source[start:]
    flex = FLEXIBLE.match(tail)
    offset = start + (flex.end() if flex else 0)
    tail = source[offset:]
    unordered = GLOBAL_UNORDERED.fullmatch(tail)
    if unordered:
        return TerminalContext(len(source), None, None, None, None)

    area = raw.location
    if area and (not AREA.fullmatch(area) or area.casefold() in ACTIVITY_LABELS
                 or DANGER.search(area) or CONTEXT_WORDS.search(area)):
        return None
    # Date, mode and location must occupy separate suffix clauses. The exact
    # supplied location must consume the entire location phrase.
    area_pattern = rf'in\s+(?P<area>{re.escape(area)})\b' if area else r'(?!)'
    endpoint = raw.journey.endpoint
    end_pattern = r'(?!)'
    if endpoint and endpoint.kind == 'named_place':
        terminal = TERMINAL.fullmatch(endpoint.source)
        if terminal and _is_name(terminal['place']):
            end_pattern = re.escape(endpoint.source)
    return_pattern = rf'(?P<origin>{ORIGIN.pattern})(?:\s+(?P<duration>within\s+{DURATION_WORDING.pattern}))?'
    match = re.fullmatch(
        rf'(?:{SEPARATOR}(?i:{area_pattern}))?'
        rf'(?:{SEPARATOR}(?:(?i:on)\s+)?(?P<date>{DATE_WORDING.pattern}))?'
        rf'(?:{SEPARATOR}(?P<mode>{MODE.pattern}))?'
        rf'(?:{SEPARATOR}(?:{return_pattern}|(?P<destination>{end_pattern})))?'
        r'\s*[.!?]?\s*',
        tail, re.I,
    )
    if not match or (area and match.groupdict().get('area') is None):
        return None
    return TerminalContext(offset, match['date'], match['mode'],
                           match['origin'] or match['destination'], match['duration'])


def _complete_order_clause(text, occurrences, proof):
    analysis = proof['source']
    rules = {p['rule'] for p in analysis['proofs']}
    # The frozen fallback for before/after can prove an edge without consuming
    # unrelated prose. Admit just the full binary clause and its optional
    # explicitly flexible third visit in this development profile.
    if rules & {'explicit_before', 'explicit_after'}:
        if len(occurrences) not in (2, 3) or len(rules) != 1 or len(analysis['proofs']) != 1:
            return False
        a, b, *rest = occurrences
        if not PREFIX.fullmatch(text[:a[0]]) or not BINARY.fullmatch(text[a[1]:b[0]]):
            return False
        if rest:
            c = rest[0]
            return (analysis['independent'] == [2] and INDEPENDENT.fullmatch(text[b[1]:c[0]])
                    and re.fullmatch(FLEXIBLE.pattern + r'\s*[.!?]?\s*', text[c[1]:], re.I))
        return bool(re.fullmatch(r'\s*[.!?]?\s*', text[b[1]:]))
    # For list syntax require complete source coverage even when a frozen
    # delegated rule proved only one edge. The list grammar stays shared.
    supported = {'explicit_then', 'default_list', 'default_list_hi_aur',
                 'default_list_skipping_flexible', 'explicit_global_first_last'}
    if not rules <= supported:
        return False
    if rules == {'explicit_global_first_last'}:
        return True  # V5 independently consumes the complete start/finish frame.
    prefix = re.sub(r'^\s*(?:maybe|optionally)\s+', '', text[:occurrences[0][0]], flags=re.I)
    if not PREFIX.fullmatch(prefix):
        return False
    flexible = analysis['independent']
    for i, (left, right) in enumerate(zip(occurrences, occurrences[1:])):
        gap = FLEXIBLE.sub('', text[left[1]:right[0]], count=1)
        gap = re.sub(r'\baur\b', 'and', gap, flags=re.I)
        match = GAP.fullmatch(gap)
        if not match or (i in flexible or i + 1 in flexible) and re.search(
                r'\bthen\b|→|⇒|->', match['cue'], re.I):
            return False
    tail = FLEXIBLE.sub('', text[occurrences[-1][1]:], count=1)
    if analysis['category'] == 'unordered':
        return bool(GLOBAL_UNORDERED.fullmatch(tail))
    return bool(re.fullmatch(r'\s*[.!?]?\s*', tail))


def _validate_context(source, raw, terminal, now):
    j = raw.journey
    if (raw.preferences or raw.uncertainties or raw.suggested_activities or raw.date is not None
            or raw.date_expressions not in ([], [terminal.date]) or raw.time_expressions
            or any(getattr(raw, key) is not None for key in (
                'people', 'budget_per_person', 'budget_group', 'currency', 'cost',
                'travel_total_minutes', 'travel_leg_minutes', 'start_time', 'end_time'))
            or j.deadline or j.shared_place or any(s.duration for s in j.stops)):
        return None, None
    if terminal.endpoint:
        kind = 'origin' if ORIGIN.fullmatch(terminal.endpoint) else 'named_place'
        if j.endpoint is None or j.endpoint.kind != kind or j.endpoint.source != terminal.endpoint:
            return None, None
    elif j.endpoint:
        return None, None
    if terminal.duration:
        if (j.total_duration is None or j.total_duration.source != terminal.duration
                or j.total_duration.minutes != duration_value(terminal.duration)
                or j.total_duration.relation != duration_relation(terminal.duration)):
            return None, None
    elif j.total_duration:
        return None, None

    mode, issues = resolve_mode(source, raw.transport)
    if issues or (raw.transport and not terminal.mode and not re.match(r'\s*(?:walk|drive)\s+to\b', source, re.I)):
        return None, None
    calendar = resolve_datetime(source, raw.date_expressions, [], raw.location, now=now)
    if (calendar.issues or calendar.time_expressions
            or calendar.date_expressions != ([terminal.date] if terminal.date else [])):
        return None, None
    if terminal.date and calendar.timezone == 'UTC':
        # No area/calendar confirmation can be borrowed from the local clock.
        return None, None
    expected = raw.model_copy(deep=True)
    expected.date_expressions = calendar.date_expressions
    if terminal.mode or re.match(r'\s*(?:walk|drive)\s+to\b', source, re.I):
        expected.transport = mode
    # The advanced engine can honor an unordered group only in flexible mode.
    if not j.order and len(j.stops) > 1 and j.ordering != 'flexible':
        return None, None
    return InterpretationContext(
        destination=raw.location, date=calendar.date, timezone=calendar.timezone,
        timezoneBasis='destination_calendar' if calendar.timezone != 'UTC' else 'unknown',
        transport=mode, geography=geographic_intent(source, raw.location),
    ), expected


def _compatible_ordinary(result, context, expected):
    if result.executionStatus is not None or result.context is not None or result.unsupported:
        return False
    if result.request:
        request = result.request
        return not result.issues and not result.questions and (
            request.activities == [activity_category(s.source) for s in expected.journey.stops]
            and request.location == context.destination and request.date == context.date
            and request.transport == context.transport and request.calendarTimezone == context.timezone
            and not request.explicitStart and not request.explicitEnd
            and request.budget is None and request.groupBudget is None and request.travel is None)
    missing = set()
    if context.date is None:
        missing.add(('date', 'What day are you planning to go?'))
    if context.destination is None:
        missing.add(('location', LOCATION_QUESTION))
    return (bool(missing) and {(q.field, q.question) for q in result.questions} == missing
            and set(result.issues) == {question for _, question in missing})
