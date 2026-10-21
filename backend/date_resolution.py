"""Small, deterministic local-calendar resolver. AI values never do arithmetic.

See ARCHITECTURE.md for the intentionally bounded grammar and calendar policy.
The injected clock must be aware. Unknown locations use disclosed UTC, never a
made-up location timezone. Existing single-day planner minutes remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo

from backend.planner import supports_location

MONTHS = ('january february march april may june july august september october november december').split()
MONTH = '(?:' + '|'.join(m + '|' + m[:3] for m in MONTHS) + ')'
DAY = r'\d{1,2}(?:st|nd|rd|th)?'
WEEKDAY = r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
DATE_WORDING = re.compile(
    rf'\b(?:\d{{4}}-\d{{2}}-\d{{2}}|{MONTH}\s+{DAY}(?:,?\s+\d{{4}})?|'
    rf'{DAY}\s+(?:of\s+)?{MONTH}(?:,?\s+\d{{4}})?|'
    rf'tomorrow(?:\s+(?:evening|night))?|today|tonight|'
    rf'(?:(?:this|next)\s+)?{WEEKDAY}(?:\s+(?:evening|night))?|'
    r'(?:this|next)\s+(?:weekend|week|month))\b', re.I)
CLOCK = r'(?:noon|midnight|\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)'
TIME_WORDING = re.compile(
    rf'\b(?:between\s+{CLOCK}\s+and\s+{CLOCK}|'
    rf'(?:from\s+)?{CLOCK}\s*(?:to|until|through|[-–])\s*{CLOCK}|'
    rf'(?:after|before|at|start(?:ing|s)?(?:\s+at)?|end(?:ing|s)?(?:\s+at)?|by|until)\s+{CLOCK}|'
    r'noon|midnight|\d{1,2}:\d{2}(?:\s*[ap]\.?m\.?)?|\d{1,2}\s*[ap]\.?m\.?)\b', re.I)


@dataclass
class DateResolution:
    date: date | None = None
    start: int = 600
    end: int = 1440
    timezone: str = 'UTC'
    date_expressions: list[str] = field(default_factory=list)
    time_expressions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def _date_expression(expression: str, today: date) -> date:
    text = re.sub(r'^on\s+', '', expression.lower().strip())
    text = re.sub(r'\s+(evening|night)$', '', text)
    if text in {'today', 'tonight'}:
        return today
    if text == 'tomorrow':
        return today + timedelta(days=1)
    if 'weekend' in text:
        raise ValueError('Choose Saturday or Sunday (or an exact Date) for this single-day planner.')
    weekdays = 'monday tuesday wednesday thursday friday saturday sunday'.split()
    day = text.split()[-1]
    if day in weekdays:
        target = weekdays.index(day)
        if text.startswith('next '):
            return today + timedelta(days=7 - today.weekday() + target)
        return today + timedelta(days=(target - today.weekday()) % 7)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return date.fromisoformat(text)
    text = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', text).replace(',', '').replace(' of ', ' ')
    parts = text.split()
    if len(parts) in {2, 3}:
        if parts[0].isdigit():
            parts[0], parts[1] = parts[1], parts[0]
        months = {name: i + 1 for i, m in enumerate(MONTHS) for name in (m, m[:3])}
        if parts[0] in months:
            if len(parts) == 2:
                raise ValueError('A spoken calendar date needs a year; please supply an exact Date.')
            return date(int(parts[2]), months[parts[0]], int(parts[1]))
    raise ValueError('Use an exact Date or a supported relative day; this expression needs clarification.')


def _clock(text: str, inherited: str | None = None) -> int:
    text = re.sub(r'[.\s]', '', text.lower())
    if text in {'noon', 'midnight'}:
        return 720 if text == 'noon' else 0
    match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', text)
    if not match:
        raise ValueError('Use a clock time such as 6 PM, 18:00, noon or midnight.')
    hour, minute, meridiem = int(match[1]), int(match[2] or 0), match[3]
    meridiem = meridiem or (inherited if match[2] is None else None)
    if minute > 59 or (meridiem and not 1 <= hour <= 12) or (not meridiem and hour > 23):
        raise ValueError('Invalid clock time; check hours and minutes.')
    if not meridiem and match[2] is None:
        raise ValueError('Specify AM or PM for a time without minutes.')
    return (hour % 12 + (12 if meridiem == 'pm' else 0)) * 60 + minute if meridiem else hour * 60 + minute


def _time_expression(expression: str) -> tuple[int | None, int | None]:
    text = expression.lower().strip()
    pair = re.fullmatch(rf'(?:between\s+|from\s+)?({CLOCK})\s*(?:and|to|until|through|[-–])\s*({CLOCK})', text, re.I)
    if pair:
        suffix = re.search(r'([ap])\.?m\.?$', pair[2].strip())
        start = _clock(pair[1], suffix[1] + 'm' if suffix else None)
        end = _clock(pair[2])
        return start, 1440 if end == 0 and start > 0 else end
    bound = re.fullmatch(rf'(after|before|at|start(?:ing|s)?(?:\s+at)?|end(?:ing|s)?(?:\s+at)?|by|until)\s+({CLOCK})', text, re.I)
    if bound:
        minute = _clock(bound[2])
        if bound[1] in {'before', 'by', 'until'} or bound[1].startswith('end'):
            # Midnight as an end boundary means the end of the chosen day.
            minute = minute or 1440
            return None, minute - (1 if bound[1] == 'before' else 0)
        return minute + (1 if bound[1] == 'after' else 0), None
    return _clock(text), None


def _wall_issue(day: date, minute: int, zone: ZoneInfo) -> str | None:
    wall = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)
    possibilities = set()
    for fold in (0, 1):
        local = wall.replace(tzinfo=zone, fold=fold)
        utc = local.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == wall:
            possibilities.add(utc)
    if not possibilities:
        return 'This local time does not exist during the daylight-saving clock change. Choose another time.'
    if len(possibilities) > 1:
        return 'This local time occurs twice during the daylight-saving clock change. Choose an unambiguous time.'
    return None


def resolve_datetime(raw: str, date_expressions: list[str], time_expressions: list[str],
                     location: str | None, *, manual_date: str = '', now: datetime | None = None) -> DateResolution:
    result = DateResolution()
    zone = ZoneInfo('America/New_York' if location and supports_location(location.strip()) else 'UTC')
    result.timezone = zone.key
    reference = now if now is not None else datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError('The reference clock must include a timezone.')
    local_now = reference.astimezone(zone)
    result.date_expressions = list(dict.fromkeys([*date_expressions, *[m.group() for m in DATE_WORDING.finditer(raw)]]))
    clock_source = DATE_WORDING.sub(lambda m: ' ' * len(m.group()), raw)
    result.time_expressions = list(dict.fromkeys([*time_expressions, *[m.group() for m in TIME_WORDING.finditer(clock_source)]]))
    if result.date_expressions or manual_date:
        result.notes.append(f'Calendar reference: {local_now.date().isoformat()} in {zone.key}.')
        if zone.key == 'UTC':
            result.notes.append('Location timezone is unknown; UTC is the fallback calendar reference, not a verified local timezone. Select an exact Date if it differs locally.')
    try:
        if manual_date:
            result.date = date.fromisoformat(manual_date)
            if result.date.isoformat() != manual_date:
                raise ValueError('Use YYYY-MM-DD for the manual Date.')
        else:
            dates = {_date_expression(expr, local_now.date()) for expr in result.date_expressions}
            if len(dates) > 1:
                raise ValueError('Date expressions disagree. Choose one outing date; no date was substituted.')
            result.date = next(iter(dates), None)
    except (ValueError, OverflowError) as error:
        result.issues.append(f'Date wording ({", ".join(result.date_expressions) or manual_date}): {error}')
    if (not manual_date and re.search(r"\bday after tomorrow\b", raw, re.I)) or re.search(r"\b(?:morning|afternoon)\b", raw, re.I):
        result.issues.append('This day/time wording needs clarification. Supply an exact Date and explicit clock window.')
    starts, ends = [], []
    exact_starts = set()
    time_parts = []
    for phrase in result.time_expressions:
        matches = list(TIME_WORDING.finditer(phrase))
        remainder = TIME_WORDING.sub(' ', phrase)
        if len(matches) > 1 and not re.sub(r'\band\b|[\s,;]', '', remainder, flags=re.I):
            time_parts.extend(m.group() for m in matches)
        else:
            time_parts.append(phrase)
    for expression in time_parts:
        if expression.casefold() in {'tonight', 'evening', 'night'}:
            continue
        if any(expression.casefold() != other.casefold() and expression.casefold() in other.casefold()
               for other in time_parts):
            continue
        try:
            start, end = _time_expression(expression)
            if start is not None and not re.match(r'after\b', expression, re.I):
                exact_starts.add(start)
            if start is not None:
                starts.append(start)
            if end is not None:
                ends.append(end)
        except ValueError as error:
            result.issues.append(f'Time wording ({expression}): {error}')
    if len(exact_starts) > 1:
        result.issues.append('Multiple start times disagree. State one overall outing window.')
    # A day-part supplies a documented default only where an explicit bound is absent.
    evening = bool(re.search(r'\b(?:tonight|evening|night)\b', raw, re.I))
    if evening and not starts:
        starts.append(1080)
        result.notes.append('Evening/night defaults to a 6 PM earliest start and midnight cutoff; explicit time bounds take precedence.')
    result.start = max(starts) if starts else (0 if ends and min(ends) <= 600 else 600)
    result.end = min(ends) if ends else 1440
    if re.search(r'\b(?:following|next)\s+(?:day|morning)\b|\bovernight\b', raw, re.I):
        result.issues.append('Overnight outings are not supported by the single-day planner. Choose a window ending by midnight.')
    if result.end <= result.start:
        overnight = result.start >= 1080 and result.end <= 360
        result.issues.append('Overnight outings are not supported; the end would be on the following day. Choose a window ending by midnight.' if overnight else 'Time requirements conflict: the end must be later than the start on the same day.')
    if not 0 <= result.start < 1440:
        result.issues.append('No start time remains before midnight; choose another window.')
    if not manual_date and re.search(r'\blast\s+(?:' + WEEKDAY + r'|week|month|weekend)\b|\byesterday\b', raw, re.I):
        result.issues.append('Past-date wording needs a future exact Date; no future day was substituted.')
    if re.search(r'\b(?:UTC|GMT|[ECMP][SD]T|[ECMP]T)\b|[+-]\d{2}:\d{2}\b', raw):
        result.issues.append('An explicit timezone/offset needs clarification. Use outing-location local clock times for this planner.')
    if result.date:
        if result.date < local_now.date():
            result.issues.append('The selected date is in the past. Choose a future date; it was not moved automatically.')
        for minute in set(starts + ends):
            if 0 <= minute <= 1440:
                issue = _wall_issue(result.date, minute, zone)
                if issue:
                    result.issues.append(issue)
        if 0 <= result.start < result.end <= 1440:
            midnight = datetime.combine(result.date, datetime.min.time())
            left = (midnight + timedelta(minutes=result.start)).replace(tzinfo=zone)
            right = (midnight + timedelta(minutes=result.end)).replace(tzinfo=zone)
            if left.utcoffset() != right.utcoffset():
                result.issues.append('This window crosses a daylight-saving clock change. The single-day planner uses wall-clock durations; choose a window wholly before or after the change.')
        if result.date == local_now.date():
            current_minute = local_now.hour * 60 + local_now.minute + (1 if local_now.second or local_now.microsecond else 0)
            if starts and result.start < current_minute:
                result.issues.append('The requested start time today has passed. Choose a later time or another date; it was not moved automatically.')
            elif not starts:
                result.start = max(result.start, current_minute)
                result.notes.append('Today’s earliest start is no earlier than the current local minute.')
            if result.end <= current_minute or result.start >= 1440:
                result.issues.append('The requested time window today has passed. Choose another date or later window.')
    return result
