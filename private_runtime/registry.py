"""One reviewed per-process lifecycle; credentials never selected by request data."""
from contextlib import ExitStack
from copy import deepcopy
import os
from private_runtime.connections import SQLPool,PostgreSQL
from private_runtime.service_client import ServiceClient
from private_runtime.google_identity import GoogleIdentity
from experiments.service_isolation.auth import unb64
from experiments.shared_state.contracts import Denied

ROLES={'backend':{'witness'},'factory':{'database','issuer','witness'},'counter':{'database','witness'},'dispatcher':{'database','witness'},'recovery':{'witness'}}
PURPOSES={'backend':{'witness':'nonce'},'factory':{'database':'runtime','issuer':'issuer','witness':'witness-factory'},'counter':{'database':'counter','witness':'witness-counter'},'dispatcher':{'database':'delivery','witness':'witness-delivery'},'recovery':{'witness':'recovery'}}
class NoOutbound:
    def request(self,*_args,**_kwargs):raise Denied('role_has_no_outbound_rpc')

_active=None
class Lease:
    """Compatibility for existing context-managed DB consumers; never reconnects."""
    def __init__(self,pool,**kwargs):self._cm=pool.connection(**kwargs);self._connection=self._cm.__enter__();self._closed=False;self._witness=pool.c.purpose in ('nonce','witness-factory','witness-counter','witness-delivery','recovery');self._server_pid=self._connection._whereto_server_pid
    def __enter__(self):
        if self._closed:raise Denied('sql_lifecycle')
        return self
    def __exit__(self,*args):
        if self._closed:raise Denied('sql_lifecycle')
        self._closed=True;return self._cm.__exit__(*args)
    def execute(self,*args,**kwargs):
        if self._closed:raise Denied('sql_lifecycle')
        if self._witness:
            query=args[0]
            if type(query) is not str:raise Denied('witness_statement')
            if query.startswith('SELECT ') and ' FROM ' not in query.upper():
                query='WITH _whereto_session AS MATERIALIZED (SELECT private_runtime.assert_session('+str(self._server_pid)+')) '+query+' FROM _whereto_session'
                args=(query,*args[1:])
            elif query not in ("SET lock_timeout='5s'",'SET TRANSACTION READ ONLY'):raise Denied('witness_statement')
        return self._connection.execute(*args,**kwargs)
    @property
    def autocommit(self):return self._connection.autocommit
    @autocommit.setter
    def autocommit(self,value):self._connection.autocommit=value

class Ports:
    def __init__(self,role,configuration,*,identity=None,authentication_factory=None,transport=None):
        if role not in ROLES or configuration.get('service')!=role or set(configuration['sql'])!=ROLES[role]:raise Denied('role_enrollment')
        self.c=deepcopy(configuration);self.role=role;self.pid=os.getpid();self.stack=ExitStack();self.pools={};self.client=None;self.evidence=None;self._started=False
        # Bootstrap/admin credentials are rejected both here and by actual SQL roles.
        for name,values in self.c['sql'].items():
            if values.get('purpose')!=PURPOSES[role][name]:raise Denied('sql_purpose')
            self.pools[name]=SQLPool(PostgreSQL(**values))
        if role=='factory' and len({(x.c.host,x.c.port,x.c.database) for x in (self.pools['database'],self.pools['witness'])})!=2:raise Denied('independent_witness_required')
        from experiments.hosted_identity.auth import HostedAuth
        self.authentication_factory=authentication_factory or HostedAuth
        self.transport=transport
        self.identity=identity if identity is not None else GoogleIdentity(self.c)
    def start(self):
        if self._started or os.getpid()!=self.pid:raise Denied('ports_lifecycle')
        try:
            for pool in self.pools.values():self.stack.enter_context(pool)
            if self.role in ('factory','dispatcher'):
                from private_runtime.redis_port import EvidenceRedis,RedisConfiguration
                from experiments.shared_state.redis_evidence import Keys
                cfg=RedisConfiguration(**self.c['redis']);keys=Keys(self.c['evidenceKeyId'],{self.c['evidenceKeyId']:unb64(self.c['encryptionKey'])})
                self.evidence=self.stack.enter_context(EvidenceRedis(cfg,keys))
            if self.role in ('counter','recovery'):
                if self.c.get('networkTargets') or self.c.get('networkMethods'):raise Denied('role_outbound_enrollment')
                self.client=NoOutbound()
            else:self.client=ServiceClient(self.c,self.identity,self.transport)
            self._started=True
            if self.epoch()!=self.c['epoch']:raise Denied('restore_epoch')
            return self
        except BaseException:self._started=False;self.stack.close();raise
    def connection(self,name='database',**kwargs):
        if not self._started or self.pid!=os.getpid() or name not in self.pools:raise Denied('connection_role')
        return Lease(self.pools[name],**kwargs)
    def epoch(self):
        with self.connection('witness') as c:return c.execute('SELECT witness.epoch()').fetchone()[0]
    def close(self):self._started=False;self.stack.close()
    def __enter__(self):return self.start()
    def __exit__(self,*_):self.close()

def install(ports):
    global _active
    if _active is not None or type(ports) is not Ports or not ports._started:raise Denied('ports_installation')
    _active=ports

def current(role=None):
    if _active is None or not _active._started or _active.pid!=os.getpid() or role is not None and _active.role!=role:raise Denied('ports_missing')
    return _active

def connection(_config,key='database'):return current().connection(key)
def client(_config):return current().client
def cache(_config):
    p=current()
    if p.evidence is None:raise Denied('evidence_role')
    return p.evidence

def epoch(_config=None):return current().epoch()
