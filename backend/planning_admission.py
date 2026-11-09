"""Server-only, single-process admission foundations. No public receipt fields.

Ordinary startup remains legacy: guards are no-ops. Explicit Python-only test
scope exercises the contract, NOT V4. Deferred continuation/manual/saved paths
fail closed in that scope rather than promoting old snapshots to raw evidence.
No registry is installed globally; no logging, disk storage or provider calls.
"""
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hmac
import json
import secrets
from threading import Lock
from time import monotonic
from typing import Any

from pydantic import BaseModel
from backend.validation_phases import LEGACY_PROFILE

_required = ContextVar('foundation_admission_required', default=False)
_active = ContextVar('foundation_admission_lease', default=None)
TTL = 600
MAX_ENTRIES = 50
MAX_BYTES = 32768


class AdmissionError(ValueError):
    def __init__(self):
        super().__init__('A current server-owned validation admission is required.')


def _plain(value):
    # Include declared excluded/private execution fields, notably confirmed
    # origin/search geometry. Never rely on public model_dump redaction to bind.
    if isinstance(value, BaseModel):
        return {name: _plain(getattr(value, name)) for name in type(value).model_fields}
    if isinstance(value, dict):return {str(k): _plain(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):return [_plain(v) for v in value]
    if isinstance(value, Enum):return value.value
    if isinstance(value, (date,datetime)):return value.isoformat()
    if isinstance(value, Decimal):return str(value)
    if value is None or type(value) in (str,int,float,bool):return value
    raise AdmissionError()


@dataclass(repr=False)
class _Scope:
    owner: Any = field(repr=False)
    created: float
    revision: int = 0
    attempted_revision: int = 0
    revoked: bool = False


@dataclass(frozen=True, repr=False)
class AdmissionReceipt:
    _handle: str = field(repr=False)


@dataclass(repr=False)
class _Entry:
    receipt: AdmissionReceipt
    scope: _Scope
    revision: int
    policy: str
    kind: str
    payload: Any = field(repr=False)
    binding: bytes = field(repr=False)
    evidence: bytes = field(repr=False)
    expires: float
    consumed: bool = False


@dataclass(repr=False)
class _Lease:
    registry: Any
    entry: _Entry
    payload: Any = field(repr=False)
    active: bool = True


@dataclass(frozen=True, repr=False)
class AdmissionOutcome:
    disposition: Any = field(repr=False)
    receipt: AdmissionReceipt | None = field(repr=False)


class AdmissionRegistry:
    """Explicit trusted server caller only; capabilities never serialized to UI.

    Identity-checked handles + keyed request fingerprints, absolute 600s scope
    lifetime, monotonic revisions, no eviction of live/tombstone entries. This
    is not cross-process durability or protection from arbitrary Python code.
    """
    def __init__(self, *, clock=monotonic):
        self._clock = clock
        self._key = secrets.token_bytes(32)
        self._lock = Lock()
        self._entries = OrderedDict()
        self._validating = 0

    def new_scope(self):
        return _Scope(self, self._clock())

    def _fingerprint(self, value):
        try:data=json.dumps(_plain(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        except (TypeError,ValueError):raise AdmissionError() from None
        if len(data)>MAX_BYTES:raise AdmissionError()
        return hmac.digest(self._key,data,'sha256')

    def _scope(self, scope):
        if (not isinstance(scope,_Scope) or scope.owner is not self or scope.revoked
                or not 0<=self._clock()-scope.created<TTL):raise AdmissionError()

    def validate(self, value, scope, revision, provider=None, *, now=None, execution=None):
        # Reserve bounded revision/capacity BEFORE interpretation work. Failed
        # validation never restores an older request revision or schedules a retry.
        with self._lock:
            self._scope(scope)
            self._entries=OrderedDict((k,v) for k,v in self._entries.items() if v.expires>self._clock())
            if (type(revision) is not int or revision<=scope.attempted_revision
                    or len(self._entries)+self._validating>=MAX_ENTRIES):raise AdmissionError()
            scope.attempted_revision=revision
            self._validating+=1
        try:return self._validate(value,scope,revision,provider,now=now,execution=execution)
        finally:
            with self._lock:self._validating-=1

    def _validate(self, value, scope, revision, provider, *, now, execution):
        from backend.validation_phases import validate_legacy
        # This is the ONLY issuer path. No API accepts an alleged validated DTO.
        d=validate_legacy(value,provider,now=now)
        result=d.result
        if d.source_kind!='raw_model':return AdmissionOutcome(d,None)
        if result.request is not None and not result.issues:
            from backend.real_planning import PlannerInput
            execution=execution or {}
            allowed={'startingLocation','currentArea','locationFirst','useOriginAsSearchAnchor',
                     'referenceToken','manualStartingPlace','searchRadius'}
            if not isinstance(execution,dict) or set(execution)-allowed:raise AdmissionError()
            payload=PlannerInput.model_validate({**result.request.model_dump(),**execution})
            kind='ordinary'
        else:
            from backend.journey import LIMITATION
            if (result.executionStatus!='advanced_unavailable' or result.unsupported!=[LIMITATION]
                    or result.context is None or result.interpretation.journey is None):
                return AdmissionOutcome(d,None)
            # Handoff authority is NOT provider-ready authority. Existing advanced
            # checks remain responsible for endpoint/date/origin answers later.
            payload={'text':d.input.text,'result':result,'preferences':d.input.preferences}
            kind='advanced_handoff'
        evidence=self._fingerprint({'input':d.input,'raw':d.raw_model,'effective':result,
                                    'profile':LEGACY_PROFILE,'kind':kind})
        binding=self._fingerprint(payload)
        with self._lock:
            self._scope(scope)
            if type(revision) is not int or revision<=scope.revision:raise AdmissionError()
            now_mono=self._clock()
            self._entries=OrderedDict((k,v) for k,v in self._entries.items() if v.expires>now_mono)
            if len(self._entries)>=MAX_ENTRIES:raise AdmissionError()
            receipt=AdmissionReceipt(secrets.token_urlsafe(32))
            self._entries[receipt._handle]=_Entry(receipt,scope,revision,LEGACY_PROFILE,kind,
                deepcopy(payload),binding,evidence,scope.created+TTL)
            scope.revision=revision
        return AdmissionOutcome(d,receipt)

    def invalidate(self, scope):
        with self._lock:
            self._scope(scope)
            scope.revoked=True

    def run(self, receipt, scope, revision, candidate, operation, *, policy=LEGACY_PROFILE):
        """Consume once before work; even uncertain/failed work stays consumed.

        operation receives an owned COPY, never the caller's mutable candidate.
        Existing provider quotas/ledger/locks still admit every actual attempt.
        """
        with self._lock:
            self._scope(scope)
            if not isinstance(receipt,AdmissionReceipt):raise AdmissionError()
            e=self._entries.get(receipt._handle)
            if (not e or e.receipt is not receipt or e.scope is not scope or e.revision!=revision
                    or type(revision) is not int or e.policy!=policy or e.consumed
                    or e.expires<=self._clock() or scope.revision!=revision or scope.attempted_revision!=revision):raise AdmissionError()
            if not hmac.compare_digest(e.binding,self._fingerprint(candidate)):raise AdmissionError()
            e.consumed=True
            lease=_Lease(self,e,deepcopy(e.payload))
        mode=_required.set(True);active=_active.set(lease)
        try:return operation(lease.payload)
        finally:
            lease.active=False
            _active.reset(active);_required.reset(mode)

    def _check(self, lease):
        with self._lock:
            e=lease.entry
            self._scope(e.scope)
            if (not lease.active or self._entries.get(e.receipt._handle) is not e
                    or not e.consumed or e.expires<=self._clock() or e.policy!=LEGACY_PROFILE
                    or e.scope.revision!=e.revision or e.scope.attempted_revision!=e.revision
                    or not hmac.compare_digest(e.binding,self._fingerprint(lease.payload))):raise AdmissionError()


def _check(kind=None, candidate=None):
    if not _required.get():return
    lease=_active.get()
    try:
        if lease is None:raise AdmissionError()
        lease.registry._check(lease)
        if kind is not None:
            if lease.entry.kind!=kind:raise AdmissionError()
            if candidate is not None and not hmac.compare_digest(
                    lease.entry.binding,lease.registry._fingerprint(candidate)):raise AdmissionError()
    except AdmissionError:
        from backend.provider_budget import ProviderLimitError
        raise ProviderLimitError('A current server-owned validation admission is required.',
                                 reason='validation_required') from None
    return lease


def _fresh_ordinary(request):
    from backend.location_context import outing_problem
    if outing_problem(request):
        from backend.provider_budget import ProviderLimitError
        raise ProviderLimitError('The validated outing needs a current date and time.',
                                 reason='validation_required')


def guard_ordinary(request):
    if _check('ordinary',request) is not None:
        _fresh_ordinary(request)


def guard_handoff(text,result,preferences):
    _check('advanced_handoff',{'text':text,'result':result,'preferences':preferences})


def guard_provider():
    lease=_check('ordinary')
    if lease is not None:_fresh_ordinary(lease.payload)


def guard_deferred():
    # No unsafe snapshot-based issuer for continuation/refresh/manual lookup.
    if _required.get():
        from backend.provider_budget import ProviderLimitError
        raise ProviderLimitError('This work needs its own validated admission revision.',
                                 reason='validation_required')


@contextmanager
def require_foundation_for_test():
    """Explicit Python-only negative-test scope. Not an enforcement profile."""
    token=_required.set(True)
    try:yield
    finally:_required.reset(token)
