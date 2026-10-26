"""Bounded source grammar for travel scope and inclusive/exclusive boundaries.

Validates AI extraction; never selects activities, destinations or provider facts.
"""
import re
from backend.models import TransportationMode

SCOPE = r'(?:total between stops|total travel|travel total|total driving|total walking|total|travel|between (?:stops|activities|venues|places)|per leg|each leg|per stop|(?:of|from) (?:me|my (?:(?:current|starting) )?(?:location|point)))'
AMOUNT = r'(?<![\w.-])(?P<amount>-?\d+(?:\.\d+)?)\s*(?P<unit>minutes?|mins?|hours?|hrs?|miles?|kilometers?|km)\b'
CAP = r'(?:under|less than|at most|no more than|within|maximum(?: of)?|up to)'
AFTER = re.compile(r'(?P<cap>'+CAP+r')?\s*'+AMOUNT+r'\s*(?:of )?(?P<scope>'+SCOPE+r')\b', re.I)
BEFORE = re.compile(r'(?P<scope>between (?:stops|activities|venues|places))\s+(?P<cap>'+CAP+r')\s*'+AMOUNT, re.I)
CONTEXT = re.compile(r'\b(?:travel|driving|drive|walking|between (?:stops|activities|venues|places)|starting point)\b', re.I)


def travel_evidence(raw):
    result = []
    for pattern in (BEFORE, AFTER):
        for match in pattern.finditer(raw):
            if any(match.start() < end and match.end() > start for start, end in (v['span'] for v in result)):
                continue
            scope = match['scope'].lower()
            kind = 'first' if re.match(r'of |from ', scope) else 'leg' if re.search(r'between|per leg|each leg|per stop', scope) and 'total' not in scope else 'total'
            unit = match['unit'].lower()
            result.append({'scope': kind, 'amount': float(match['amount']) * (60 if unit.startswith(('hour', 'hr')) else 1),
                           'distance': unit.startswith(('mile', 'kilometer', 'km')),
                           'explicitMaximum': bool(match['cap']),
                           'exclusive': (match['cap'] or '').lower() in ('under', 'less than'), 'span': match.span()})
    return result


def exclusive_limit(raw, scope):
    matches = [m for m in travel_evidence(raw) if m['scope'] == scope and not m['distance']]
    minimum = min((m['amount'] for m in matches), default=None)
    return any(m['amount'] == minimum and m['exclusive'] for m in matches)


def resolved_travel_label(label, raw, interpretation):
    """Clear ONLY a verbatim supported cap already extracted in the right scope.

    No free-form uncertainty, qualification, conflicting amount or unknown scope
    is dismissed. Independent source guards still validate the full request.
    """
    normalize = lambda text: ' '.join(text.strip(' .').casefold().split())
    for item in travel_evidence(raw):
        if item['distance'] or not 0 <= item['amount'] <= 1440 or not item['amount'].is_integer():
            continue
        if normalize(label) != normalize(raw[slice(*item['span'])]):
            continue
        field = {'leg': 'travel_leg_minutes', 'total': 'travel_total_minutes'}.get(item['scope'])
        if field and getattr(interpretation, field) == item['amount']:
            return True
        if item['scope'] == 'first' and interpretation.travel_leg_minutes is None and interpretation.travel_total_minutes is None:
            return True
    return False


def normalize_verbatim_travel(raw, interpretation):
    """Normalize an AI-returned verbatim cap, like activity phrase aliases.

    Only repair missing numeric fields for an exact source maximum phrase, not
    an inferred intent or an incorrect competing extraction. Unrecognized or
    qualified uncertainty stays blocking, as do all independent source guards.
    """
    if re.search(r"\b(?:or|not|never|minimum|maybe|approximately|around|except|if|unless|assuming|depending|roughly|about)\b|don't|at least", raw, re.I):
        return
    normalize = lambda text: ' '.join(text.strip(' .').casefold().split())
    labels = {normalize(label) for label in interpretation.uncertainties}
    modes = {mode for mode in ('driving', 'walking', 'cycling', 'transit') if re.search(r'\b' + mode + r'\b', raw, re.I)}
    if len(modes) > 1:
        return
    for item in travel_evidence(raw):
        if not item['explicitMaximum'] or item['distance'] or not 0 <= item['amount'] <= 1440 or not item['amount'].is_integer():
            continue
        if normalize(raw[slice(*item['span'])]) not in labels:
            continue
        field = {'leg': 'travel_leg_minutes', 'total': 'travel_total_minutes'}.get(item['scope'])
        if not field:
            continue
        if interpretation.travel_leg_minutes is None and interpretation.travel_total_minutes is None:
            setattr(interpretation, field, int(item['amount']))
        if (getattr(interpretation, field) == item['amount'] and interpretation.transport is None
                and re.search(r'\bdriving\b', raw, re.I)
                and not re.search(r'\b(?:walking|cycling|transit|bus|train|bike)\b', raw, re.I)):
            interpretation.transport = TransportationMode.driving
