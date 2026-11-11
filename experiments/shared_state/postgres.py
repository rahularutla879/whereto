"""Inactive local client for the constrained PostgreSQL protocol.

No direct table privileges, provider transport, credential discovery or hosted adapter.
The SECURITY DEFINER database routine enforces every protected transition.
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


def uuid(value):
    try:
        if type(value) is not str or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError):
        raise Denied('identity') from None
    return value


class LocalPostgres:
    """Explicit local-only runtime client; bootstrap/admin credentials are separate.

    SQL deliberately repeats authorization checks: bypassing this Python wrapper
    cannot bypass the database state machine. No application admission is issued.
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
        types()
        with self._tx():
            pass

    @staticmethod
    def _invoke(c, action, args):
        return c.execute('SELECT synthetic_state.protocol(%s,%s) AS result',
                         (action, Jsonb(args))).fetchone()['result']

    @contextmanager
    def _tx(self):
        if os.getpid() != self._pid:
            raise Denied('worker_instance')
        try:
            with psycopg.connect(**self._connection) as c:
                c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                c.execute("SET LOCAL statement_timeout='1500ms'")
                c.execute("SET LOCAL lock_timeout='250ms'")
                self._invoke(c, 'check', dict(version=VERSION, limits=asdict(self._limits),
                    fingerprint=digest(self._key,'key',VERSION)))
                yield c
        except (psycopg.IntegrityError, psycopg.errors.RaiseException,
                psycopg.DataError, psycopg.errors.NoDataFound):
            raise Denied('database_protocol') from None
        except psycopg.Error:
            raise Unavailable() from None

    def _call(self, verb, **args):
        with self._tx() as c:
            return self._invoke(c, verb, args)

    def _hash(self, value, domain):
        if type(value) is not str or not 40 <= len(value) <= 100:
            raise Denied('capability')
        return digest(self._key, domain, value)

    def _session(self, handle, revision):
        if type(handle) is not SessionHandle or type(revision) is not int or not 1 <= revision <= 10**12:
            raise Denied('session_revision')
        return dict(session=self._hash(handle.token,'session'),revision=revision)

    def _lease(self, lease):
        if (type(lease) is not WorkerLease or lease.worker != self._worker
                or type(lease.fence) is not int or lease.fence <= 0):
            raise Denied('worker_instance')
        return dict(**self._session(lease.session,lease.revision),worker=uuid(lease.worker),fence=lease.fence)

    def _binding(self, kind, payload):
        return digest(self._key, 'evidence', kind.value + '\0' + encode(kind, payload))

    def _prepared(self, kind, payload):
        return dict(kind=kind.value if isinstance(kind,Kind) else None,
                    payload=json.loads(encode(kind,payload)),binding=self._binding(kind,payload))

    def create(self, kind, payload, *, ttl=600):
        if type(ttl) is not int or not 1 <= ttl <= 600:
            raise Denied('expiry')
        h=SessionHandle(secrets.token_urlsafe(32))
        self._call('create',session=self._hash(h.token,'session'),ttl=ttl,**self._prepared(kind,payload))
        return h

    def claim(self, handle, revision):
        result=self._call('claim',**self._session(handle,revision),worker=self._worker)
        return WorkerLease(handle,revision,self._worker,result['fence'])

    def read(self, lease):
        result=self._call('read',**self._lease(lease))
        try:
            kind=Kind(result['kind'])
            payload=types()[kind].model_validate_json(json.dumps(result['payload']))
        except (ValueError,KeyError):
            raise Denied('evidence_invalid') from None
        if not hmac.compare_digest(self._binding(kind,payload),result['binding']):
            raise Denied('evidence_integrity')
        return payload

    def revise(self, handle, revision, kind, payload):
        return self._call('revise',**self._session(handle,revision),**self._prepared(kind,payload))['revision']

    def revoke(self, handle, revision):
        self._call('revoke',**self._session(handle,revision))

    def issue(self, lease, purpose, action):
        cap=Capability(secrets.token_urlsafe(32))
        self._call('issue',**self._lease(lease),purpose=purpose,action=uuid(action),
                   capability=self._hash(cap.token,'cap'))
        return cap

    def reserve(self, lease, cap, operation, provider, charge):
        if (type(cap) is not Capability or type(charge) is not int or not 0 <= charge <= 10**12
                or provider not in ('synthetic_ai','synthetic_maps')):
            raise Denied('reservation')
        self._call('reserve',**self._lease(lease),capability=self._hash(cap.token,'cap'),
                   operation=uuid(operation),provider=provider,charge=charge)
        return Reservation(operation,lease,cap)

    def transition(self, reservation, kind):
        if type(reservation) is not Reservation:
            raise Denied('transition')
        self._call('transition',**self._lease(reservation.lease),state=kind,
                   capability=self._hash(reservation.capability.token,'cap'),operation=uuid(reservation.operation))

    def snapshot(self):
        return self._call('snapshot')
