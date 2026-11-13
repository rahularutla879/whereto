"""Inactive TLS-only restricted-role connections; no discovery, bootstrap or retry."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import LifoQueue, Empty
from threading import Lock
from pathlib import Path
from time import monotonic
import os,re
import psycopg
from psycopg.rows import tuple_row
from experiments.shared_state.contracts import Denied,Unavailable

IDENTITY_QUERY = 'SELECT private_runtime.connection_identity()'
@dataclass(frozen=True,repr=False)
class PostgreSQL:
    host:str
    port:int
    database:str
    user:str
    password:str=field(repr=False)
    ca_file:str
    contract:str
    memberships:tuple=()
    maximum:int=4
    purpose:str='runtime'
    connection_mode:str='direct'
    def __post_init__(self):
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}',self.host) or type(self.port) is not int or not 1<=self.port<=65535
            or any(not re.fullmatch(r'[a-z][a-z0-9_]{0,62}',x) for x in (self.database,self.user,*self.memberships))
            or any(x.startswith('pg_') for x in self.memberships) or not self.password or not Path(self.ca_file).is_file() or not re.fullmatch('[0-9a-f]{64}',self.contract)
            or self.connection_mode!='direct' or 'pooler' in self.host.casefold() or self.port==6543 or self.purpose not in ('runtime','issuer','counter','delivery','nonce','witness-factory','witness-counter','witness-delivery','recovery') or type(self.maximum) is not int or not 1<=self.maximum<=4):raise Denied('sql_enrollment')

class SQLPool:
    """Bounded process-local reuse. Failed operations are NEVER replayed/retried.

    The protected contract function is independently installed by an administrator;
    runtime has EXECUTE only. Bootstrap/admin functions are intentionally absent.
    """
    def __init__(self,configuration):
        if type(configuration) is not PostgreSQL:raise Denied('sql_enrollment')
        self.c=configuration;self._idle=LifoQueue(configuration.maximum);self._lock=Lock();self._count=0;self._closed=False;self._pid=os.getpid();self.created=0
    def _check(self,c):
        if not c.pgconn.ssl_in_use:raise Denied('sql_tls')
        row=c.execute("SELECT current_database(),session_user,current_user,r.rolsuper,r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls,has_database_privilege(session_user,current_database(),'CREATE'),r.rolcanlogin AND coalesce(r.rolvaliduntil>clock_timestamp(),true),pg_backend_pid(),ARRAY(SELECT parent.rolname::text FROM pg_roles parent WHERE parent.oid<>r.oid AND pg_has_role(r.oid,parent.oid,'MEMBER') ORDER BY parent.rolname) FROM pg_roles r WHERE r.rolname=session_user").fetchone()
        if row is None or tuple(row[:3])!=(self.c.database,self.c.user,self.c.user) or any(row[3:9]) or row[9] is not True or tuple(row[11])!=tuple(sorted(self.c.memberships)):raise Denied('sql_role')
        c._whereto_server_pid=row[10]
        if c.execute(IDENTITY_QUERY).fetchone()[0]!={'contract':self.c.contract,'purpose':self.c.purpose}:raise Denied('sql_contract')
        c.commit()
    def _new(self):
        c=psycopg.connect(host=self.c.host,port=self.c.port,dbname=self.c.database,user=self.c.user,password=self.c.password,
            sslmode='verify-full',sslrootcert=self.c.ca_file,connect_timeout=2,prepare_threshold=None,
            options='-c statement_timeout=1500 -c lock_timeout=250 -c idle_in_transaction_session_timeout=1500')
        self.created+=1;c._whereto_born=monotonic();c.isolation_level=psycopg.IsolationLevel.READ_COMMITTED
        try:self._check(c);return c
        except BaseException:c.close();raise
    def _take(self):
        with self._lock:
            if self._closed or os.getpid()!=self._pid:raise Denied('sql_lifecycle')
            try:c=self._idle.get_nowait()
            except Empty:c=None
            if c is not None:
                if not c.closed and monotonic()-c._whereto_born<300:return c
                c.close();self._count-=1
            if self._count>=self.c.maximum:raise Unavailable()
            self._count+=1
        try:return self._new()
        except BaseException:
            with self._lock:self._count-=1
            raise
    @contextmanager
    def connection(self,*,row_factory=None):
        c=None;healthy=False
        try:
            c=self._take();c.row_factory=tuple_row;self._check(c);c.row_factory=row_factory or tuple_row
            yield c
            if not c.autocommit:c.commit()
            healthy=True
        except psycopg.Error:raise Unavailable() from None
        finally:
            if c is not None:
                try:
                    c.rollback();c.autocommit=True;c.execute('DISCARD ALL');c.autocommit=False;c.row_factory=tuple_row
                except psycopg.Error:healthy=False
                with self._lock:
                    if healthy and not self._closed and not c.closed:self._idle.put_nowait(c)
                    else:c.close();self._count-=1
    def start(self):
        with self.connection():pass
        return self
    def close(self):
        with self._lock:
            self._closed=True
            while True:
                try:self._idle.get_nowait().close();self._count-=1
                except Empty:break
    def __enter__(self):return self.start()
    def __exit__(self,*_):self.close()
