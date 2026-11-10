"""Original-journal review interface with a synthetic-only append rehearsal."""
from contextlib import contextmanager
from os import getpid
from threading import get_ident

from scripts import task52_diag_protocol as diagnostic
from scripts import task52_integration_identity as identity
from scripts import task52_q1 as q1
from scripts import task52_q4d as historical

live_dispatch = diagnostic.live_dispatch
Denied = diagnostic.auth.Denied

# These are the existing Q4C state and reservation statements. A parent SQL
# change requires reviewing the integration rather than widening the boundary.
_READS = frozenset({
    "PRAGMA integrity_check",
    "SELECT name,sql FROM sqlite_master WHERE type='table'",
    "SELECT * FROM sqlite_master",
    "SELECT rowid,* FROM attempts ORDER BY rowid",
    "SELECT id,config FROM metadata",
})
_APPEND = "INSERT INTO attempts VALUES(?,?,?,?,?,?)"


def inspect_original():
    manifest = identity.verify()
    inspection = historical.inspect_original()
    if q1.digest(inspection) != manifest["originalInspectionDigest"]:
        raise Denied("Original journal inspection differs from pinned evidence")
    return {
        "integrationBuildSHA256": identity.MANIFEST_SHA,
        "ownerDecisionSHA256": manifest["ownerDecisionSHA256"],
        "inspection": inspection,
        "executionAuthorized": False,
        "planningAuthorized": False,
    }


class _JournalSQL:
    """Private SQL surface for the existing synthetic continuation engine."""

    def __init__(self, connection, require_lock):
        self._connection = connection
        self._require_lock = require_lock

    def execute(self, statement, parameters=()):
        self._require_lock()
        if statement not in _READS and statement not in ("BEGIN IMMEDIATE", _APPEND):
            raise Denied("Statement outside the append-only SQL boundary")
        cursor = self._connection.execute(statement, parameters)
        # Only reads return rows. Keep the raw cursor and connection internal.
        try:
            return _Rows(cursor.fetchall()) if statement in _READS else None
        finally:
            cursor.close()

    def commit(self):
        self._require_lock()
        self._connection.commit()

    def close(self):
        self._connection.close()


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _AppendEngine(diagnostic.Engine):
    _held_lock = None

    def check(self):
        identity.verify()
        return super().check()

    @contextmanager
    def lock(self):
        with super().lock():
            self._held_lock = (getpid(), get_ident(), object())
            try:
                yield
            finally:
                self._held_lock = None

    def db(self):
        lock = self._held_lock

        def require_lock():
            if lock is None or lock is not self._held_lock or lock[:2] != (getpid(), get_ident()):
                raise Denied("Synthetic journal SQL requires the current experiment lock")

        require_lock()
        return _JournalSQL(super().db(), require_lock)


class SyntheticIntegration:
    """Rehearse the exact-schema append boundary on a newly created fixture."""

    def __init__(self, trust, *, base_charge=1000000):
        self._original = inspect_original()
        self._fixture = diagnostic.SyntheticJournal(trust, base_charge=base_charge)
        try:
            self._engine = _AppendEngine(self._fixture.directory, trust)
        except Exception:
            self._fixture.close()
            raise

    def fixture_binding(self):
        return {
            "scope": self._fixture.scope,
            "journal_hash": self._fixture.journal_hash,
        }

    def activate_synthetic_scope(self, packets, now):
        return self._engine.activate_synthetic_scope(packets, now)

    def simulate_one(self, permission, transport, now, *, crash_at=None):
        return self._engine.simulate_one(permission, transport, now, crash_at=crash_at)

    def record_review(self, packet, now):
        return self._engine.record_review(packet, now)

    def report(self):
        with self._engine.lock():
            rows, facts, exposure, child_exposure = self._engine.state()
            counts = {provider: sum(row[1] == provider for row in rows)
                      for provider in ("openai", "google", "anthropic")}
            return {
                "integrationBuildSHA256": identity.MANIFEST_SHA,
                "ownerDecisionSHA256": self._original["ownerDecisionSHA256"],
                "originalInspectionDigest": q1.digest(self._original["inspection"]),
                "syntheticJournalHash": self._fixture.journal_hash,
                "childScopeHash": facts[0]["hash"] if facts else None,
                "counts": counts,
                "attempts": len(rows),
                "exposureNanodollars": exposure,
                "childExposureNanodollars": child_exposure,
                "historicalHaltPreserved": rows[9][4] == "recorded_halted",
                "factKinds": [fact["kind"] for fact in facts],
                "syntheticOnly": True,
                "executionAuthorized": False,
                "planningAuthorized": False,
            }

    def close(self):
        self._fixture.close()
