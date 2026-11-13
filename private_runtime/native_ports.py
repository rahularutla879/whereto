"""Connection-only versioned extension of the unchanged PostgreSQL state machine."""
from contextlib import contextmanager
from dataclasses import asdict
import os,secrets
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
from experiments.shared_state.postgres import LocalPostgres
from experiments.shared_state.contracts import Denied,Unavailable,Limits,VERSION,digest,types
from private_runtime.registry import current

class PersistentPostgres(LocalPostgres):
    def __init__(self,*,key,password,limits):
        p=current('factory')
        if type(key) is not bytes or len(key)!=32 or type(limits) is not Limits or password!=p.pools['database'].c.password:raise Denied('native_enrollment')
        self._key,self._limits=key,limits;self._pid,self._worker=os.getpid(),str(uuid4());self._pool=p.pools['database'];types()
        with self._tx():pass
    @contextmanager
    def _tx(self):
        if self._pid!=os.getpid():raise Denied('worker_instance')
        try:
            with self._pool.connection(row_factory=dict_row) as c:
                c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                c.execute("SET LOCAL statement_timeout='1500ms'");c.execute("SET LOCAL lock_timeout='250ms'")
                self._invoke(c,'check',dict(version=VERSION,limits=asdict(self._limits),fingerprint=digest(self._key,'key',VERSION)))
                yield c
        except (psycopg.IntegrityError,psycopg.errors.RaiseException,psycopg.DataError,psycopg.errors.NoDataFound):raise Denied('database_protocol') from None
        except psycopg.Error:raise Unavailable() from None

def require_native():
    """Private projection's alternative to local-dev flags, never a network grant."""
    from backend.action_dispatch import _active
    from experiments.shared_state.native_sessions import NativeBroker
    p=current('factory');broker=_active.get()
    if type(broker) is not NativeBroker or broker.store._pool is not p.pools['database']:raise Denied('native_action_required')
    broker._check() # Existing source/owner/admission/cancellation checks remain mandatory.
