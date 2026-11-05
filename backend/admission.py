"""Local admission implementation and the atomic lease contract for cloud adapters.

No Google ledger here. HMAC fingerprints stay in memory and never enter logs.
No user identity or daily itinerary allowance. Production is deliberately gated.
"""
from collections import deque
from contextvars import ContextVar
from hashlib import sha256
import hmac
import os
from secrets import token_bytes
from threading import Lock
from time import monotonic, perf_counter
from typing import Protocol


class AdmissionError(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        self.code = {'duplicate': 'request_in_progress', 'burst': 'request_burst_limited'}.get(reason, 'service_busy')
        super().__init__(self.code)


class Lease(Protocol):
    def bind(self, key: bytes): ...
    def retain(self): ...
    def release(self): ...


class AdmissionStore(Protocol):
    """Atomic acquire of capacity + duplicate ownership + rolling burst token.

    Future shared implementations need fencing, renewable bounded leases, failure
    reconciliation and TTLs; releasing a lease must never refund provider usage.
    """
    def acquire(self, key: bytes, operation: str) -> Lease: ...
    def snapshot(self) -> dict: ...


class LocalLease:
    def __init__(self, store, key):
        self.store, self.key, self.references = store, key, 1

    def bind(self, key):
        """Atomically replace reader ownership with exact-operation ownership."""
        with self.store.lock:
            if key in self.store.active:
                raise AdmissionError('duplicate')
            self.store.active.remove(self.key)
            self.key = key
            self.store.active.add(key)

    def retain(self):
        with self.store.lock:
            self.references += 1

    def release(self):
        with self.store.lock:
            self.references -= 1
            if self.references == 0:
                self.store.active.remove(self.key)


class LocalAdmission:
    def __init__(self, capacity=16, burst=240, interval=10, clock=monotonic):
        self.lock = Lock()
        self.capacity, self.burst, self.interval, self.clock = capacity, burst, interval, clock
        self.active = set()
        self.recent = deque()

    def acquire(self, key, operation):
        from backend.operations import event
        started = perf_counter()
        with self.lock:
            now = self.clock()
            while self.recent and now-self.recent[0] >= self.interval:
                self.recent.popleft()
            reason = ('duplicate' if key in self.active else
                      'capacity' if len(self.active) >= self.capacity else
                      'burst' if len(self.recent) >= self.burst else None)
            if reason:
                event('rejected', operation, reason=reason)
                raise AdmissionError(reason)
            self.active.add(key)
            self.recent.append(now)
        event('admitted', operation)
        event('stage_finished', 'admission', duration_ms=(perf_counter()-started)*1000)
        return LocalLease(self, key)

    def snapshot(self):
        with self.lock:
            return {'active': len(self.active), 'capacity': self.capacity,
                    'queued': 0, 'scope': 'process', 'burstIntervalSeconds': self.interval}


active_lease = ContextVar('request_admission_lease', default=None)
requests = LocalAdmission()
inference = LocalAdmission(capacity=1, burst=240)
_secret = token_bytes(32)


def fingerprint(path, body):
    # Canonical JSON suppresses whitespace/key-order double submissions. Invalid
    # JSON is left for the existing strict endpoint validators.
    import json
    try:
        parsed = json.loads(body)
        body = json.dumps(parsed, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    except (ValueError, UnicodeError, RecursionError):
        pass
    return hmac.digest(_secret, path.encode()+b'\0'+body, sha256)


def validate_environment():
    environment = os.environ.get('WHERETO_ENV', 'development')
    if environment not in ('development', 'test', 'production'):
        raise RuntimeError('Unknown application environment.')
    hosted = any(os.environ.get(k) for k in ('VERCEL', 'RENDER', 'K_SERVICE',
        'WEBSITE_HOSTNAME', 'NETLIFY', 'FLY_APP_NAME', 'RAILWAY_ENVIRONMENT', 'DYNO', 'AWS_EXECUTION_ENV'))
    if environment == 'production' or os.environ.get('NODE_ENV') == 'production' or hosted:
        # There is intentionally no environment flag asserting imaginary safety.
        raise RuntimeError('Production requires verified shared admission, provider accounting, ephemeral sessions and cloud inference. Activation is deferred to Task 52.')
