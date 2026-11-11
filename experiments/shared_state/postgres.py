"""Local synthetic PostgreSQL reference only; never imported by application startup.

No provider callback/client, credential discovery, public receipt or live adapter.
One fixed gate serializes authority transactions. No optimistic lock-free fallback.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hmac
import json
import os
import secrets
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from experiments.shared_state.contracts import (
    VERSION, Kind, Limits, SessionHandle, WorkerLease, Capability, Reservation,
    Denied, Unavailable, encode, digest, types,
)

PURPOSES = {Kind.ORDINARY: 'ordinary_plan', Kind.HANDOFF: 'handoff_only',
            Kind.PENDING: 'clarify_only', Kind.OPTIONS: 'browse_only',
            Kind.SELECTED: 'save_selection', Kind.ADVANCED_RESULTS: 'browse_only'}


def uuid(value):
    try:
        if type(value) is not str or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError):
        raise Denied('identity') from None
    return value


class LocalPostgres:
    """An explicitly constructed test store; no global instance or env selector.

    Requires a separately initialized synthetic database and key injection.
    It cannot open the configured Supabase host/role or initialize any schema.
    SQL principal is trusted server code, not an untrusted database tenant.
    """
    def __init__(self, *, key, password, limits, host='127.0.0.1', port=5432,
                 dbname='whereto_synthetic', user='whereto_synthetic_worker'):
        if (host != '127.0.0.1' or port != 5432 or dbname != 'whereto_synthetic'
                or user != 'whereto_synthetic_worker' or type(key) is not bytes or len(key) != 32
                or not isinstance(limits, Limits) or not password):
            raise Denied('local_synthetic_only')
        self._key, self._limits = key, limits
        self._pid, self._worker = os.getpid(), str(uuid4())
        self._connection = dict(host=host, port=port, dbname=dbname, user=user, password=password,
                                connect_timeout=2, prepare_threshold=None, row_factory=dict_row)
        types()  # Load existing DTO modules before acquiring any SQL authority lock.
        with self._tx():
            pass

    @contextmanager
    def _tx(self):
        if os.getpid() != self._pid:
            raise Denied('worker_instance')
        try:
            with psycopg.connect(**self._connection) as conn:
                conn.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                conn.execute("SET LOCAL statement_timeout='1500ms'")
                conn.execute("SET LOCAL lock_timeout='250ms'")
                gate = conn.execute('SELECT id FROM synthetic_state.gate WHERE id=1 FOR UPDATE').fetchone()
                if gate != {'id': 1}:
                    raise Denied('gate_missing')
                row = conn.execute('SELECT * FROM synthetic_state.policy WHERE id=1').fetchone()
                if (not row or row['version'] != VERSION or row['limits'] != asdict(self._limits)
                        or not hmac.compare_digest(row['key_fingerprint'], digest(self._key, 'key', VERSION))):
                    raise Denied('policy_identity')
                corrupt=conn.execute("""SELECT EXISTS(SELECT 1 FROM synthetic_state.operations o WHERE
                    NOT EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='RESERVED')
                    OR (SELECT kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence LIMIT 1)<>'RESERVED'
                    OR (EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind IN ('SUCCEEDED','FAILED'))
                        AND NOT EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='INTENT')))
                    AS corrupt""").fetchone()['corrupt']
                if corrupt:
                    raise Denied('operation_facts_corrupt')
                yield conn
        except psycopg.IntegrityError:
            raise Denied('conflict') from None
        except psycopg.Error:
            raise Unavailable() from None

    def _hash(self, value, domain):
        if type(value) is not str or not 40 <= len(value) <= 100:
            raise Denied('capability')
        return digest(self._key, domain, value)

    def _session(self, conn, handle, revision=None):
        if type(handle) is not SessionHandle:
            raise Denied('session_type')
        id = self._hash(handle.token, 'session')
        row = conn.execute('SELECT *,expires>clock_timestamp() AS live FROM synthetic_state.sessions WHERE id=%s', (id,)).fetchone()
        if not row or not row['live'] or row['revoked']:
            raise Denied('expired_or_revoked')
        if revision is not None and (type(revision) is not int or row['revision'] != revision):
            raise Denied('revision')
        return row

    def _owned(self, conn, lease):
        if type(lease) is not WorkerLease:
            raise Denied('worker_type')
        uuid(lease.worker)
        if lease.worker != self._worker:
            raise Denied('worker_instance')
        if type(lease.fence) is not int or lease.fence <= 0:
            raise Denied('worker_fence')
        s = self._session(conn, lease.session, lease.revision)
        if s['fence'] != lease.fence or str(s['worker']) != lease.worker:
            raise Denied('stale_worker')
        return s

    def _binding(self, kind, payload):
        return digest(self._key, 'evidence', kind.value + '\0' + encode(kind, payload))

    def _evidence(self, conn, s):
        kind = Kind(s['kind'])
        row = conn.execute('SELECT * FROM synthetic_state.evidence WHERE session=%s', (s['id'],)).fetchone()
        if not row or row['revision'] != s['revision']:
            raise Denied('evidence_missing')
        try:
            payload = types()[kind].model_validate_json(json.dumps(row['payload']))
        except ValueError:
            raise Denied('evidence_invalid') from None
        if not hmac.compare_digest(self._binding(kind, payload), s['binding']):
            raise Denied('evidence_integrity')
        return kind, payload

    def create(self, kind, payload, *, ttl=600):
        text = encode(kind, payload)
        if type(ttl) is not int or not 1 <= ttl <= 600:
            raise Denied('expiry')
        handle = SessionHandle(secrets.token_urlsafe(32))
        id = self._hash(handle.token, 'session')
        with self._tx() as c:
            count=c.execute('SELECT count(*) AS n FROM synthetic_state.sessions WHERE NOT revoked AND expires>clock_timestamp()').fetchone()['n']
            if count >= 50:
                raise Denied('session_capacity')
            c.execute('INSERT INTO synthetic_state.sessions(id,revision,expires,kind,binding) VALUES(%s,1,clock_timestamp()+%s*interval \'1 second\',%s,%s)',
                      (id, ttl, kind.value, self._binding(kind, payload)))
            c.execute('INSERT INTO synthetic_state.evidence VALUES(%s,1,%s)', (id, Jsonb(json.loads(text))))
        return handle

    def _abandon(self, c, session):
        rows = c.execute('''SELECT o.id,(SELECT kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence DESC LIMIT 1) AS state
                            FROM synthetic_state.operations o WHERE o.session=%s''', (session,)).fetchall()
        for row in rows:
            if row['state'] in ('RESERVED', 'INTENT'):
                c.execute("INSERT INTO synthetic_state.facts(operation,kind) VALUES(%s,'UNCERTAIN')", (row['id'],))

    def claim(self, handle, revision):
        worker = self._worker
        with self._tx() as c:
            s = self._session(c, handle, revision)
            self._evidence(c, s)
            self._abandon(c, s['id'])
            row = c.execute('UPDATE synthetic_state.sessions SET fence=fence+1,worker=%s WHERE id=%s RETURNING fence', (worker, s['id'])).fetchone()
        return WorkerLease(handle, revision, worker, row['fence'])

    def read(self, lease):
        with self._tx() as c:
            s = self._owned(c, lease)
            return self._evidence(c, s)[1]

    def revise(self, handle, revision, kind, payload):
        text = encode(kind, payload)
        with self._tx() as c:
            s = self._session(c, handle, revision)
            self._abandon(c, s['id'])
            c.execute('UPDATE synthetic_state.sessions SET revision=revision+1,fence=fence+1,worker=NULL,kind=%s,binding=%s WHERE id=%s',
                      (kind.value, self._binding(kind, payload), s['id']))
            c.execute('UPDATE synthetic_state.evidence SET revision=%s,payload=%s WHERE session=%s', (revision+1, Jsonb(json.loads(text)), s['id']))
        return revision+1  # absolute expiry and all financial anchors unchanged

    def revoke(self, handle, revision):
        with self._tx() as c:
            s = self._session(c, handle, revision)
            self._abandon(c, s['id'])
            c.execute('UPDATE synthetic_state.sessions SET revoked=true,fence=fence+1 WHERE id=%s', (s['id'],))

    def issue(self, lease, purpose, action):
        uuid(action)
        cap = Capability(secrets.token_urlsafe(32))
        with self._tx() as c:
            s = self._owned(c, lease)
            kind, _ = self._evidence(c, s)
            if PURPOSES[kind] != purpose:
                raise Denied('purpose')
            count=c.execute('SELECT count(*) AS n FROM synthetic_state.capabilities WHERE session=%s AND revision=%s',(s['id'],s['revision'])).fetchone()['n']
            if count >= 32:
                raise Denied('capability_capacity')
            c.execute('INSERT INTO synthetic_state.capabilities VALUES(%s,%s,%s,%s,%s,%s)',
                      (self._hash(cap.token, 'cap'), s['id'], lease.revision, purpose, action, s['binding']))
        return cap

    def reserve(self, lease, cap, operation, provider, charge):
        uuid(operation)
        if (type(cap) is not Capability or provider not in ('synthetic_ai', 'synthetic_maps')
                or type(charge) is not int or not 0 <= charge <= 10**12):
            raise Denied('reservation')
        with self._tx() as c:
            s = self._owned(c, lease)
            kind, _ = self._evidence(c, s)
            if kind is not Kind.ORDINARY:
                raise Denied('not_provider_ready')  # handoff/pending/browsing are never provider permission
            cap_id = self._hash(cap.token, 'cap')
            row = c.execute('SELECT * FROM synthetic_state.capabilities WHERE id=%s', (cap_id,)).fetchone()
            if (not row or row['session'] != s['id'] or row['revision'] != s['revision']
                    or row['binding'] != s['binding'] or row['purpose'] != 'ordinary_plan'):
                raise Denied('capability_binding')
            totals = c.execute('''SELECT count(*) AS attempts,coalesce(sum(charge),0) AS gross,
                       count(*) FILTER(WHERE provider=%s) AS provider_attempts,
                       coalesce(sum(charge) FILTER(WHERE provider=%s),0) AS provider_gross
                       FROM synthetic_state.operations''', (provider, provider)).fetchone()
            active = c.execute('''SELECT count(*) AS n FROM synthetic_state.operations o WHERE
                       COALESCE((SELECT kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence DESC LIMIT 1),'MISSING')
                       NOT IN ('SUCCEEDED','FAILED')''').fetchone()['n']
            p = self._limits
            if (totals['gross']+charge > p.gross or totals['provider_gross']+charge > p.provider_gross
                    or totals['attempts']+1 > p.attempts or totals['provider_attempts']+1 > p.provider_attempts
                    or active >= p.concurrency):
                raise Denied('budget_or_uncertainty')
            c.execute('INSERT INTO synthetic_state.operations(id,capability,session,revision,worker,fence,provider,charge) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                      (operation, cap_id, s['id'], s['revision'], lease.worker, lease.fence, provider, charge))
            c.execute("INSERT INTO synthetic_state.facts(operation,kind) VALUES(%s,'RESERVED')", (operation,))
        return Reservation(operation, lease, cap)

    def transition(self, reservation, kind):
        if type(reservation) is not Reservation or kind not in ('INTENT', 'SUCCEEDED', 'FAILED', 'UNCERTAIN'):
            raise Denied('transition')
        with self._tx() as c:
            s = self._owned(c, reservation.lease)
            self._evidence(c, s)
            row = c.execute('''SELECT o.*,(SELECT kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence DESC LIMIT 1) AS state
                               FROM synthetic_state.operations o WHERE id=%s''', (reservation.operation,)).fetchone()
            if (not row or row['session'] != s['id'] or row['fence'] != reservation.lease.fence
                    or str(row['worker']) != reservation.lease.worker
                    or row['capability'] != self._hash(reservation.capability.token, 'cap')):
                raise Denied('operation_binding')
            if not ((kind == 'INTENT' and row['state'] == 'RESERVED') or
                    (kind in ('SUCCEEDED', 'FAILED') and row['state'] == 'INTENT') or
                    (kind == 'UNCERTAIN' and row['state'] in ('RESERVED', 'INTENT'))):
                raise Denied('state_transition')
            c.execute('INSERT INTO synthetic_state.facts(operation,kind) VALUES(%s,%s)', (reservation.operation, kind))

    def snapshot(self):
        """Sanitized counts only. Status lookup never authorizes a resend."""
        with self._tx() as c:
            totals = c.execute('SELECT count(*) AS attempts,coalesce(sum(charge),0) AS gross FROM synthetic_state.operations').fetchone()
            states = c.execute('''SELECT kind,count(*) AS n FROM
                    (SELECT DISTINCT ON(operation) operation,kind FROM synthetic_state.facts ORDER BY operation,sequence DESC) f GROUP BY kind''').fetchall()
        return dict(attempts=int(totals['attempts']), gross=int(totals['gross']),
                    states={r['kind']: r['n'] for r in states}, planning_authorized=False)
