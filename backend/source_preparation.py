"""Phase B capture/lexical preparation only; never semantic or planning authority.

The mutating legacy normalizers stay in their original validator call sites.
These private transient records report uncertainty instead of repairing output.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel

PREPARATION_VERSION = '52b-source-preparation-b1'
RUNTIME_ID = '52b-runtime-phase-b1'
MAX_BINDING_WORK = 256
EvidenceKind = Literal['raw_model', 'legacy_effective_pending']


@dataclass(frozen=True, repr=False)
class Occurrence:
    logical_id: str
    original_index: int
    journey_index: int | None
    phrase: str = field(repr=False)
    span: tuple[int, int] | None
    evidence_span: tuple[int, int] | None
    evidence_status: Literal['unspecified', 'lexically_bound', 'unresolved']


@dataclass(frozen=True, repr=False)
class OccurrenceMapping:
    logical_id: str
    original_index: int
    effective_index: int | None
    status: Literal['same_source_span', 'unresolved']


@dataclass(frozen=True, repr=False)
class PreparedSource:
    source_kind: EvidenceKind
    text: str = field(repr=False)
    basis_snapshot: bytes = field(repr=False)
    explicit_fields: tuple[str, ...]
    manual_snapshot: bytes = field(repr=False)
    answer_snapshot: bytes = field(repr=False)
    pending_answer_snapshot: bytes | None = field(repr=False)
    calendar_timezone: str | None = field(repr=False)
    has_current_location: bool
    reference_time: datetime | None
    reference_basis: Literal['pending_reference', 'explicit_now', 'legacy_clock_unobserved']
    occurrences: tuple[Occurrence, ...]
    effective_snapshot: bytes | None = field(default=None, repr=False)
    mapping: tuple[OccurrenceMapping, ...] = ()
    preparation_version: str = PREPARATION_VERSION
    runtime_identity: str = RUNTIME_ID


def strict_extraction(extracted):
    # Exactly the former validation_phases helper, not a new parser.
    from backend.ai import Interpretation
    return Interpretation.model_validate(extracted).model_copy(deep=True)


def _fields(value, prefix=''):
    paths=[]
    if isinstance(value, BaseModel):
        for name in sorted(value.model_fields_set):
            path=prefix+'.'+name if prefix else name
            paths.append(path)
            paths.extend(_fields(getattr(value,name),path))
    elif isinstance(value,list):
        for i,item in enumerate(value):paths.extend(_fields(item,f'{prefix}[{i}]'))
    return paths


def _spans(text, phrase):
    # Literal phrase only, exact original code-point offsets; no article/alias,
    # punctuation repair, grammar interpretation, or invented count ownership.
    if not phrase:return ()
    left=r'(?<!\w)' if phrase[0].isalnum() or phrase[0]=='_' else ''
    right=r'(?!\w)' if phrase[-1].isalnum() or phrase[-1]=='_' else ''
    return tuple(m.span() for m in re.finditer(left+re.escape(phrase)+right,text,re.I))


def _bindings(text, phrases):
    """Return only a unique nonoverlapping source-order lexical assignment.

    This is not proof of requiredness, cue scope, order or completeness. A single
    'coffee twice' mention cannot acquire two fabricated spans. Reaching the
    bounded search limit makes every binding unresolved, never picks a solution.
    """
    if not phrases:return ()
    candidates=[_spans(text,p) for p in phrases]
    solutions=[];work=0;limited=False
    def visit(index,end,chosen):
        nonlocal work,limited
        if len(solutions)>1 or limited:return
        if index==len(candidates):
            solutions.append(tuple(chosen));return
        for span in candidates[index]:
            work+=1
            if work>MAX_BINDING_WORK:
                limited=True;return
            if span[0]>=end:visit(index+1,span[1],chosen+[span])
            if len(solutions)>1 or limited:return
    visit(0,0,[])
    return solutions[0] if len(solutions)==1 and not limited else (None,)*len(phrases)


def prepare_source(value, extracted, *, source_kind: EvidenceKind, now=None):
    """Capture already strict data. No mutation and no validation disposition."""
    if source_kind not in ('raw_model','legacy_effective_pending'):
        raise ValueError('Unknown preparation evidence kind')
    matched=value.pending if value.pending and value.pending.text==value.text else None
    if (source_kind=='legacy_effective_pending') != bool(matched):
        raise ValueError('Preparation evidence origin does not match the input')
    reference=matched.referenceTime if matched else now
    basis='pending_reference' if matched else 'explicit_now' if now is not None else 'legacy_clock_unobserved'
    spans=_bindings(value.text,extracted.activities)
    j=extracted.journey
    aligned=j is not None and [s.source for s in j.stops]==extracted.activities
    occurrences=[]
    for i,(phrase,span) in enumerate(zip(extracted.activities,spans)):
        evidence=j.stops[i].evidence if aligned else ''
        quotes=[q for q in _spans(value.text,evidence) if span and q[0]<=span[0] and span[1]<=q[1]] if evidence else []
        quote=quotes[0] if len(quotes)==1 else None
        occurrences.append(Occurrence(f'basis:{i}',i,i if aligned else None,phrase,span,quote,
            'unspecified' if not evidence else 'lexically_bound' if quote else 'unresolved'))
    return PreparedSource(source_kind,value.text,extracted.model_dump_json().encode(),tuple(_fields(extracted)),
        value.preferences.model_dump_json().encode(),value.answers.model_dump_json().encode(),
        matched.answers.model_dump_json().encode() if matched else None,value.calendarTimezone,value.hasCurrentLocation,reference,basis,tuple(occurrences))


def observe_effective(prepared, value, result):
    """Map only identical uniquely bound source spans; never remap model edges.

    Changed/removed endpoint occurrences and user activity-answer rewrites can
    remain unresolved. No ordinal guessing, endpoint inference or normalization.
    """
    effective=result.interpretation
    spans=_bindings(prepared.text,effective.activities)
    has_answers=bool(value.answers.activities or
                     value.pending and value.pending.text==value.text and value.pending.answers.activities)
    mapping=[]
    for original in prepared.occurrences:
        matches=[i for i,span in enumerate(spans) if span is not None and span==original.span]
        index=matches[0] if len(matches)==1 and not has_answers else None
        mapping.append(OccurrenceMapping(original.logical_id,original.original_index,index,
                                        'same_source_span' if index is not None else 'unresolved'))
    return replace(prepared,effective_snapshot=effective.model_dump_json().encode(),mapping=tuple(mapping))
