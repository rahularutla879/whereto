"""Opt-in offline scoring v3. No transport, credential access or journal writes.

Historical v2 score/audits and active inference payloads remain unchanged.
"""
import copy
import re

from backend.ai import Interpretation, parse_interpretation
from backend.interpretation import ALIASES, activity_category
from scripts import cloud_model52 as e
from scripts.cloud_model52_semantics import compare_reference

VERSION = '52b-semantic-v3-source-bound-generic-the'
# Narrow subset of generic labels already recognized by production normalization.
# No broad category equivalence, verb removal, plural reduction or name rewriting.
GENERIC = frozenset({'bank', 'grocery store', 'groceries', 'grocery shopping',
    'supermarket', 'pharmacy', 'atm', 'coffee', 'coffee shop', 'museum',
    'dinner', 'lunch', 'food', 'drinks', 'movie'})


def occurrences(text, stops):
    """Source-order boundary spans; unprovable/repetition-count cases stay strict."""
    cursor = 0
    spans = []
    for stop in stops:
        match = re.search(r'(?<!\w)' + re.escape(stop.source) + r'(?!\w)', text[cursor:], re.I)
        if match is None:
            return None
        span = (cursor + match.start(), cursor + match.end())
        spans.append(span)
        cursor = span[1]
    return spans


def article_projection(case, actual):
    """A comparison copy only; original output and trusted validation are untouched.

    Permit only lower-case `the X` vs `X`, for a finite known generic X, same
    activity-kind occurrence, requirement, production category and source span.
    Capitalized source names, brands and named places never use this exception.
    """
    projected = actual.model_copy(deep=True)
    changes = []
    if 'expectedExtraction' not in case or not actual.journey:
        return projected, changes
    gold = Interpretation.model_validate(case['expectedExtraction'])
    if not gold.journey or len(actual.journey.stops) != len(gold.journey.stops):
        return projected, changes
    if actual.activities != [s.source for s in actual.journey.stops]:
        return projected, changes
    source = case['text']
    left = occurrences(source, actual.journey.stops)
    right = occurrences(source, gold.journey.stops)
    if left is None or right is None:
        return projected, changes
    for i, (got, wanted) in enumerate(zip(actual.journey.stops, gold.journey.stops)):
        if got.source == wanted.source:
            continue
        if got.kind != 'activity' or wanted.kind != 'activity' or got.requirement != wanted.requirement:
            continue
        longer, shorter = sorted((got.source, wanted.source), key=len, reverse=True)
        if longer != 'the ' + shorter or shorter not in GENERIC or shorter not in ALIASES:
            continue
        # Require actual original-case text, not merely model-labeled generic kind.
        if source[slice(*left[i])] != got.source or source[slice(*right[i])] != wanted.source:
            continue
        a, b = (left[i], right[i]) if len(got.source) > len(wanted.source) else (right[i], left[i])
        if (a[0] + 4, a[1]) != b or activity_category(longer) != activity_category(shorter):
            continue
        projected.activities[i] = wanted.source
        projected.journey.stops[i].source = wanted.source
        changes.append({'occurrence': i, 'actual': got.source, 'reference': wanted.source,
                        'actualSpan': list(left[i]), 'referenceSpan': list(right[i])})
    return projected, changes


def score(case, content):
    """Re-score saved/fake output explicitly; never changes v2 or paid recovery."""
    result = copy.deepcopy(e.score(case, content))
    result['historicalEvaluatorVersion'] = result.get('evaluatorVersion')
    result['evaluatorVersion'] = VERSION
    result['comparisonProjections'] = []
    if not result['structuredValid']:
        return result
    raw = parse_interpretation(content)
    # Local legacy parsing permits journey=None; the strict evaluation wire
    # contract requires a non-null Journey object even for ordinary cases.
    if raw.journey is None:
        result.update(structuredValid=False, validatedAccepted=False,
                      wireContractFailures=['$.journey: non-null object required'])
        return result
    if 'expectedExtraction' not in case:
        return result
    projected, changes = article_projection(case, raw)
    _, trusted = e.validate(case, content)
    target = Interpretation.model_validate(case['expectedExtraction'])
    checks = result['automatedChecks']
    checks['activities'] = projected.activities == target.activities
    result['referenceFailures'] = compare_reference(case, projected, trusted)
    checks['journeySemantics'] = not result['referenceFailures']
    result['automatedFailures'] = [k for k, passed in checks.items() if not passed]
    result['comparisonProjections'] = changes
    # Original occurrence/evidence attachment and trusted acceptance are retained.
    # A rejected result cannot become an accepted extraction through projection.
    return result
