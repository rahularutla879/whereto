"""Inactive shared-authority contracts. No production issuer or transport."""
from dataclasses import dataclass
from enum import Enum
import hmac
import json

from backend.planning_admission import _plain

VERSION = '52-shared-authority-financial-core-v3'
MAX_EVIDENCE = 65536


class Denied(ValueError):
    def __init__(self, code='state_denied'):
        self.code = code
        super().__init__(code)  # Never include source, tokens or database exceptions.


class Unavailable(RuntimeError):
    def __init__(self):
        super().__init__('shared_state_unavailable')


class Kind(str, Enum):
    ORDINARY = 'ordinary'
    HANDOFF = 'advanced_handoff'
    PENDING = 'pending_effective'
    OPTIONS = 'options'
    ADVANCED_RESULTS = 'advanced_results'
    SELECTED = 'selected'


def types():
    from backend.real_planning import PlannerInput
    from backend.interpretation import InterpretationResult, PendingClarification
    from backend.ranking import RankingResult
    from backend.saved_plans import SavedDocument
    from backend.advanced_planning import AdvancedResult
    return {Kind.ORDINARY: PlannerInput, Kind.HANDOFF: InterpretationResult,
            Kind.PENDING: PendingClarification, Kind.OPTIONS: RankingResult,
            Kind.SELECTED: SavedDocument, Kind.ADVANCED_RESULTS: AdvancedResult}


def encode(kind, payload):
    if not isinstance(kind, Kind) or type(payload) is not types()[kind]:
        raise Denied('evidence_type')
    if kind is Kind.HANDOFF and (payload.executionStatus != 'advanced_unavailable'
            or not payload.context or not payload.interpretation.journey):
        raise Denied('handoff_type')
    try:
        text = json.dumps(_plain(payload), sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise Denied('evidence_encoding') from None
    if len(text.encode()) > MAX_EVIDENCE:
        raise Denied('evidence_capacity')
    return text


def digest(key, domain, value):
    return hmac.digest(key, (domain + '\0' + value).encode(), 'sha256').hex()


@dataclass(frozen=True, repr=False)
class SessionHandle:
    token: str


@dataclass(frozen=True, repr=False)
class WorkerLease:
    session: SessionHandle
    revision: int
    worker: str
    fence: int


@dataclass(frozen=True, repr=False)
class Capability:
    token: str


@dataclass(frozen=True, repr=False)
class Reservation:
    operation: str
    lease: WorkerLease
    capability: Capability

    @property
    def planning_authorized(self):
        return False  # This prototype never replaces application admission.


@dataclass(frozen=True)
class Limits:
    gross: int
    provider_gross: int
    attempts: int
    provider_attempts: int
    concurrency: int = 1

    def __post_init__(self):
        if any(type(x) is not int or not 0 <= x <= 10**12 for x in
               (self.gross, self.provider_gross, self.attempts, self.provider_attempts)):
            raise Denied('limits')
        if type(self.concurrency) is not int or not 1 <= self.concurrency <= 16:
            raise Denied('limits')
