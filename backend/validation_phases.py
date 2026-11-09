"""Internal legacy boundary, not V4 enforcement or a new public DTO.

Pinned interpreter/journey retain B–E atomically, including legacy ordering.
Only fresh strict extraction can support a new internal admission attestation.
Browser pending snapshots remain effective legacy evidence, never raw output.
"""
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING
from backend.source_preparation import (PreparedSource, RUNTIME_ID, strict_extraction,
                                        prepare_source, observe_effective)

if TYPE_CHECKING:
    from backend.ai import Interpretation
    from backend.interpretation import InterpretationInput, InterpretationResult

LEGACY_PROFILE = 'legacy-pinned-52b-v1'
PHASES = ('strict_extraction', 'source_occurrence_capture_b1',
          'legacy_source_order_calendar_atomic', 'effective_occurrence_observation_b1',
          'final_disposition')


@dataclass(frozen=True, repr=False)
class LegacyDisposition:
    result: 'InterpretationResult' = field(repr=False)
    source_kind: Literal['raw_model','legacy_effective_pending']
    raw_snapshot: bytes | None = field(repr=False)
    input: 'InterpretationInput' = field(repr=False)
    phases: tuple[str, ...] = PHASES
    preparation: PreparedSource | None = field(default=None, repr=False)

    @property
    def raw_model(self):
        # A consumer receives a new copy; the pre-normalization snapshot stays
        # immutable even if a later validator or observer mutates its copy.
        if self.raw_snapshot is None:return None
        from backend.ai import Interpretation
        return Interpretation.model_validate_json(self.raw_snapshot)


def validate_legacy(value, provider=None, *, now=None, profile=LEGACY_PROFILE, _operation=None):
    """Run exactly one existing interpreter, no fallback, projection or V4.

    The provider still returns its original object to the unchanged interpreter.
    Raw audit capture is a private copy. No matching pending => lazy provider;
    matching pending => no provider call and no raw provenance attestation.
    """
    if profile != LEGACY_PROFILE:
        raise ValueError('Unsupported validation profile')
    from backend import interpretation as legacy
    value = value.model_copy(deep=True)
    captured = []

    class Capture:
        def interpret(self, text):
            original = (provider if provider is not None else legacy.create_provider()).interpret(text)
            captured.append(prepare_source(value, strict_extraction(original),
                                           source_kind='raw_model', now=now))
            return original

    operation = _operation if _operation is not None else legacy.interpret_request
    kwargs = {'now':now} if now is not None else {}
    result = operation(value, provider=Capture(), **kwargs)
    prepared = captured[0] if captured else None
    if prepared is None and value.pending and value.pending.text == value.text:
        prepared = prepare_source(value, value.pending.interpretation,
                                  source_kind='legacy_effective_pending', now=now)
    if prepared is not None:
        prepared = observe_effective(prepared, value, result)
    return LegacyDisposition(result, 'raw_model' if captured else 'legacy_effective_pending',
                             captured[0].basis_snapshot if captured else None, value,
                             preparation=prepared)


def interpret_legacy_result(value, operation, **kwargs):
    """Application adapter: identical public result; no registry/receipt by default."""
    return validate_legacy(value, _operation=operation, **kwargs).result
