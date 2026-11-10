"""Read-only original-journal bridge and factory-only FICTIONAL writer facade.

No caller-selected database, real writer, transport, credentials, enrollment,
CLI or environment activation. Q4D adds compatibility binding and a terminal
legacy-order-loss gate; frozen Q4C/V5.1 algorithms and artifacts stay unchanged.
"""
from copy import deepcopy
from scripts import task52_q4b as reader
from scripts import task52_v51_eval_identity as parent
from scripts import task52_v51_eval_protocol as protocol
from scripts import task52_q4d_identity as identity

live_dispatch = protocol.live_dispatch  # Unconditional refusal, even with grants.
Denied = protocol.auth.Denied
LOSS = 'blocked_by_legacy_effective_order_loss'


def compatibility(report):
    """Pure comparison; an inspection report cannot mint execution authority."""
    baseline = parent.binding()['originalBaseline']
    baseline = {**baseline, 'rowHashes': [r['rowHash'] for r in baseline['rows']]}
    fields = ('journalSHA256', 'rootHash', 'rowHashes', 'counts', 'attempts',
              'accountedNanodollars', 'remainingNanodollars')
    if any(report.get(k) != baseline[k] for k in fields):
        raise Denied('Original journal identity/accounting mismatch')
    if (not report.get('persistentHistoricalHalt') or not report.get('correctionsUnchanged')
            or report.get('privateFilesUnchanged') != 324 or
            not report.get('sourcePinsAndQ4ABuildVerified') or
            not report.get('historicalStorageSnapshotCompatible') or
            report.get('continuationReady') is not False or
            report.get('executionAuthorized') is not False):
        raise Denied('Historical evidence or refusal boundary missing')
    return {'identity': identity.IDENTITY, 'buildSHA256': identity.MANIFEST_SHA,
            'original': deepcopy(report), 'parentBuildSHA256': parent.MANIFEST_SHA,
            'schemaCompatible': True, 'originalPrefixCompatible': True,
            'realWritableAdapter': False, 'realContinuationReady': False,
            'executionAuthorized': False, 'planningAuthorized': False,
            'liveDispatchAvailable': False,
            'syntheticWriter': 'Factory-only exact-DDL Q4C/V5.1; fictional root/rows/money, not a journal copy',
            'lockContract': 'Original existing experiment.lock SH read; fictional same-name EX lock. Future real writer must share original inode.'}


def inspect_original():
    """The sole real-state operation: fixed Q4B mode=ro/query-only inspection."""
    identity.verify(full=True)
    return compatibility(reader.inspect_original())


class FictionalContinuation:
    """Creates only NEW temporary synthetic state; no path-opening constructor.

    Synthetic V5.1 envelopes retain their original signed identity. This Q4D
    build adds a stricter outer gate, not another approval issuer or permission.
    Private Python attributes are not a hostile same-UID security sandbox.
    """
    def __init__(self, trust, *, base_charge=1000000):
        self.compatibility = inspect_original()  # Read only; not authorization.
        self._fixture = protocol.SyntheticJournal(trust, base_charge=base_charge)
        self._engine = self._fixture.engine()

    def _checked_state(self):
        identity.verify()
        return self._engine.state()  # Frozen registry/prefix/facts/identity checks.

    def fixture_binding(self):
        """Public hashes needed by the test-only signer; never signing material."""
        self._checked_state()
        return {'scope': self._fixture.scope, 'journal_hash': self._fixture.journal_hash}

    @staticmethod
    def _loss(facts):
        return any(f['kind'] == 'OUTCOME' and
                   (f['data']['assessment'].get('guarded') or {}).get('disposition') == LOSS
                   for f in facts)

    def _progression(self):
        _, facts, _, _ = self._checked_state()
        if self._loss(facts):
            raise Denied('Legacy ordering loss: separate decision/build required; no progression')

    def activate_synthetic_scope(self, packets, now):
        self._progression()
        return self._engine.activate_synthetic_scope(packets, now)

    def simulate_one(self, permission, transport, now, *, crash_at=None):
        self._progression()
        outcome = self._engine.simulate_one(permission, transport, now, crash_at=crash_at)
        # Preserve original assessment/response. Add only a terminal policy fact.
        # Restart after OUTCOME but before HALT still refuses via _progression.
        with self._engine.lock():
            _, facts, _, _ = self._checked_state()
            if self._loss(facts) and facts[-1]['kind'] != 'HALT':
                self._engine.append('HALT', outcome['operation'],
                    {'reason': 'legacy_order_loss_requires_separate_decision'}, facts, now)
        return outcome

    def record_review(self, packet, now):
        self._progression()
        return self._engine.record_review(packet, now)

    def report(self):
        rows, facts, exposure, extra = self._checked_state()
        outcomes = [f for f in facts if f['kind'] == 'OUTCOME']
        return {'identity': identity.IDENTITY, 'syntheticOnly': True,
                'attempts': len(rows), 'childAttempts': len(rows) - 10,
                'exposureNanodollars': exposure, 'childExposureNanodollars': extra,
                'historicalHaltPreserved': rows[9][4] == 'recorded_halted',
                'childHalted': any(f['kind'] == 'HALT' for f in facts),
                'legacyOrderLoss': self._loss(facts),
                'progressionBlocked': self._loss(facts) or any(f['kind'] == 'HALT' for f in facts),
                'outcomeHashes': [f['hash'] for f in outcomes],
                'planningAuthorized': False, 'executionAuthorized': False,
                'liveDispatchAvailable': False}

    def close(self):
        self._fixture.close()
