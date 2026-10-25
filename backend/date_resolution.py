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
from typing import Literal

from backend.planner import supports_location

MONTHS = ('january february march april may june july august september october november december').split()
MONTH_NUMBERS = {name: i + 1 for i, month in enumerate(MONTHS) for name in (month, month[:3])}
MONTH_NUMBERS['sept'] = 9
MONTH = '(?:' + '|'.join(sorted(MONTH_NUMBERS, key=len, reverse=True)) + r')\.?'
DAY = r'\d{1,2}(?:st|nd|rd|th)?'
WEEKDAY = r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
DATE_WORDING = re.compile(
    rf'\b(?:\d{{4}}-\d{{2}}-\d{{2}}|{MONTH}\s+{DAY}(?:(?:,\s*|\s+)\d{{4}})?|'
    rf'{DAY}\s+(?:of\s+)?{MONTH}(?:(?:,\s*|\s+)\d{{4}})?|'
    rf'tomorrow(?:\s+(?:evening|night))?|today|tonight|'
    rf'(?:(?:this|next)\s+)?{WEEKDAY}(?:\s+(?:evening|night))?|'
    r'(?:this|next)\s+(?:weekend|week|month))\b', re.I)
CLOCK = r'(?:noon|midnight|\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)'
TIME_WORDING = re.compile(
    rf'\b(?:between\s+{CLOCK}\s+and\s+{CLOCK}|'
    rf'(?:from\s+)?{CLOCK}\s*(?:to|until|through|[-–])\s*{CLOCK}|'
    rf'(?:after|before|at|start(?:ing|s)?(?:\s+at)?|end(?:ing|s)?(?:\s+at)?|by|until)\s+{CLOCK}|'
    r'noon|midnight|\d{1,2}:\d{2}(?:\s*[ap]\.?m\.?)?|\d{1,2}\s*[ap]\.?m\.?)\b', re.I)


CalendarReason = Literal['missing_date', 'missing_year', 'weekend', 'past_date',
                         'invalid_date', 'date_conflict', 'unsupported_date',
                         'invalid_time', 'time_conflict', 'overnight', 'timezone', 'dst', 'past_time']
DATE_HELP = 'Try tomorrow, this Saturday, next Friday, Nov 11, 11 Nov 2026, or YYYY-MM-DD.'
CALENDAR_HELP = {
    'missing_date': DATE_HELP,
    'missing_year': 'Enter a four-digit year.',
    'weekend': 'Reply Saturday or Sunday, or enter an exact date.',
    'past_date': 'Enter today or a future date, such as tomorrow or YYYY-MM-DD.',
    'invalid_date': 'Check the day and month; include a year if needed.',
    'date_conflict': 'Enter one outing date.',
    'unsupported_date': DATE_HELP,
    'invalid_time': 'Use an overall window such as from 6 PM to 10 PM.',
    'time_conflict': 'Enter one same-day window with the end after the start.',
    'overnight': 'Choose a same-day window ending by midnight.',
    'timezone': 'Use local times at the outing location.',
    'dst': 'Choose a local window wholly before or after the clock change.',
    'past_time': 'Choose a later time or another date.',
}


@dataclass
class CalendarIssue:
    reason: CalendarReason
    message: str
    help_text: str = ''

    @property
    def field(self) -> Literal['date', 'time']:
        return 'date' if self.reason in {'missing_date', 'missing_year', 'weekend', 'past_date',
                                        'invalid_date', 'date_conflict', 'unsupported_date'} else 'time'

    @property
    def question(self) -> str:
        if self.reason == 'invalid_time':
            return 'What overall time window do you mean? Include AM/PM, for example from 6 PM to 10 PM.'
        return self.message

    @property
    def guidance(self) -> str:
        return self.help_text or CALENDAR_HELP[self.reason]


class DateExpressionError(ValueError):
    def __init__(self, reason: CalendarReason, message: str, help_text: str = ''):
        super().__init__(message)
        self.problem = CalendarIssue(reason, message, help_text)


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
    problems: list[CalendarIssue] = field(default_factory=list)

    def add_issue(self, reason: CalendarReason, message: str, help_text: str = ''):
        self.problems.append(CalendarIssue(reason, message, help_text))
        self.issues.append(message)


NAMED_DATE = re.compile(
    rf'(?:({MONTH})\s+({DAY})|({DAY})\s+(?:of\s+)?({MONTH}))(?:(?:,\s*|\s+)(\d{{4}}))?', re.I)


def _named_date_parts(expression: str) -> tuple[int, int, int | None] | None:
    match = NAMED_DATE.fullmatch(expression.strip())
    if not match:
        return None
    month = (match[1] or match[4]).rstrip('.').lower()
    day = re.sub(r'(st|nd|rd|th)$', '', match[2] or match[3], flags=re.I)
    return MONTH_NUMBERS[month], int(day), int(match[5]) if match[5] else None


def complete_year_answer(context: str, answer: str) -> str:
    """Expand a year-only correction only for one unambiguous named month/day.

    The context is the previous date answer, or original date wording. Never
    choose one of several different dates or invent a month/day from a year.
    """
    if not re.fullmatch(r'\d{4}', answer):
        return answer
    phrases = [m.group() for m in DATE_WORDING.finditer(context)]
    parts = [_named_date_parts(phrase) for phrase in phrases]
    if parts and all(part is not None for part in parts):
        days = {(part[0], part[1]) for part in parts}
        if len(days) == 1:
            month, day = next(iter(days))
            return f'{MONTHS[month - 1]} {day}, {answer}'
    return answer


def _date_expression(expression: str, today: date) -> date:
    text = re.sub(r'^on\s+', '', expression.lower().strip())
    text = re.sub(r'\s+(evening|night)$', '', text)
    if text in {'today', 'tonight'}:
        return today
    if text == 'tomorrow':
        return today + timedelta(days=1)
    if 'weekend' in text:
        raise DateExpressionError('weekend', 'Did you mean Saturday or Sunday?')
    weekdays = 'monday tuesday wednesday thursday friday saturday sunday'.split()
    day = text.split()[-1]
    if day in weekdays:
        target = weekdays.index(day)
        if text.startswith('next '):
            return today + timedelta(days=7 - today.weekday() + target)
        return today + timedelta(days=(target - today.weekday()) % 7)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            raise DateExpressionError('invalid_date', "That date doesn't exist. Please enter a valid date.") from None
    parts = _named_date_parts(text)
    if parts:
        month, day, year = parts
        try:
            candidate = date(today.year if year is None else year, month, day)
        except ValueError:
            if year is None and (month, day) == (2, 29):
                raise DateExpressionError('missing_year',
                    'February 29 needs a leap year. Which year would you like to plan for?',
                    'Enter a four-digit leap year.') from None
            raise DateExpressionError('invalid_date', "That date doesn't exist. Please enter a valid date.") from None
        if year is None and candidate < today:
            raise DateExpressionError('missing_year',
                f'{MONTHS[month - 1].title()} {day} has already passed this year. Which year would you like to plan for?',
                'Enter a four-digit leap year.' if (month, day) == (2, 29)
                else f'Enter a four-digit year, for example {today.year + 1}.')
        return candidate
    raise DateExpressionError('unsupported_date', 'Which date would you like? Enter a supported day or calendar date.')


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
    zone = ZoneInfo('America/New_York' if location and (supports_location(location.strip()) or re.fullmatch(r'Washington\s*,?\s*(?:DC|D\.C\.)', location.strip(), re.I)) else 'UTC')
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
                raise DateExpressionError('date_conflict', 'Date expressions disagree. Which one outing date should we use?')
            result.date = next(iter(dates), None)
    except DateExpressionError as error:
        result.add_issue(error.problem.reason, error.problem.message, error.problem.help_text)
    except (ValueError, OverflowError):
        result.add_issue('invalid_date', "That date doesn't exist. Please enter a valid date.")
    if not manual_date and re.search(r"\bday after tomorrow\b", raw, re.I):
        result.add_issue('unsupported_date', 'This day wording needs clarification. Which exact date should we use?')
    if re.search(r"\b(?:morning|afternoon)\b", raw, re.I):
        result.add_issue('invalid_time', 'This time wording needs clarification. State an explicit clock window.')
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
        except ValueError:
            result.add_issue('invalid_time', 'The time is unclear or invalid. Include valid hours and AM/PM.')
    if len(exact_starts) > 1:
        result.add_issue('time_conflict', 'Multiple start times disagree. What one overall time window should we use?')
    # A day-part supplies a documented default only where an explicit bound is absent.
    evening = bool(re.search(r'\b(?:tonight|evening|night)\b', raw, re.I))
    if evening and not starts:
        starts.append(1080)
        result.notes.append('Evening/night defaults to a 6 PM earliest start and midnight cutoff; explicit time bounds take precedence.')
    result.start = max(starts) if starts else (0 if ends and min(ends) <= 600 else 600)
    result.end = min(ends) if ends else 1440
    if re.search(r'\b(?:following|next)\s+(?:day|morning)\b|\bovernight\b', raw, re.I):
        result.add_issue('overnight', 'Overnight outings are not supported by the single-day planner. Choose a window ending by midnight.')
    if result.end <= result.start:
        overnight = result.start >= 1080 and result.end <= 360
        result.add_issue('overnight' if overnight else 'time_conflict', 'Overnight outings are not supported; the end would be on the following day. Choose a window ending by midnight.' if overnight else 'Time requirements conflict: the end must be later than the start on the same day.')
    if not 0 <= result.start < 1440:
        result.add_issue('time_conflict', 'No start time remains before midnight; choose another window.')
    if not manual_date and re.search(r'\blast\s+(?:' + WEEKDAY + r'|week|month|weekend)\b|\byesterday\b', raw, re.I):
        result.add_issue('past_date', 'That date has already passed. Please choose today or a future date.')
    if re.search(r'\b(?:UTC|GMT|[ECMP][SD]T|[ECMP]T)\b|[+-]\d{2}:\d{2}\b', raw):
        result.add_issue('timezone', 'An explicit timezone/offset needs clarification. Use outing-location local clock times for this planner.')
    if result.date:
        if result.date < local_now.date():
            result.add_issue('past_date', 'That date has already passed. Please choose today or a future date.')
        for minute in set(starts + ends):
            if 0 <= minute <= 1440:
                issue = _wall_issue(result.date, minute, zone)
                if issue:
                    result.add_issue('dst', issue)
        if 0 <= result.start < result.end <= 1440:
            midnight = datetime.combine(result.date, datetime.min.time())
            left = (midnight + timedelta(minutes=result.start)).replace(tzinfo=zone)
            right = (midnight + timedelta(minutes=result.end)).replace(tzinfo=zone)
            if left.utcoffset() != right.utcoffset():
                result.add_issue('dst', 'This window crosses a daylight-saving clock change. The single-day planner uses wall-clock durations; choose a window wholly before or after the change.')
        if result.date == local_now.date():
            current_minute = local_now.hour * 60 + local_now.minute + (1 if local_now.second or local_now.microsecond else 0)
            if starts and result.start < current_minute:
                result.add_issue('past_time', 'The requested start time today has passed. Choose a later time or another date; it was not moved automatically.')
            elif not starts:
                result.start = max(result.start, current_minute)
                result.notes.append('Today’s earliest start is no earlier than the current local minute.')
            if result.end <= current_minute or result.start >= 1440:
                result.add_issue('past_time', 'The requested time window today has passed. Choose another date or later window.')
    return result
