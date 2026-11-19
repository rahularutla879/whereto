"""Real namespace over the existing bounded TLS SQL/Redis/identity lifecycle."""
from hashlib import sha256
import re
from private_runtime.registry import Ports as Parent
from private_runtime.redis_port import EvidenceRedis,RedisConfiguration
from private_runtime.service_client import ServiceClient
from experiments.shared_state.redis_evidence import Keys
from experiments.service_isolation.auth import unb64
from experiments.shared_state.evidence_models import canonical
from experiments.shared_state.contracts import Denied

class Evidence(EvidenceRedis):
    def path(self,environment,epoch,sid):
        if environment not in ('real',self.c.environment) or epoch!=self.c.epoch or not re.fullmatch('[0-9a-f]{64}',sid):raise Denied('real_evidence_namespace')
        return '52-real-source:{real:'+epoch+'}:'+sid

class Ports(Parent):
    def start(self):
        if self._started:raise Denied('ports_lifecycle')
        import os
        if self.pid!=os.getpid():raise Denied('ports_lifecycle')
        try:
            from .identity import verify_application
            source=verify_application()
            if self.c.get('sourceBuild')!=source:raise Denied('real_source_build')
            for pool in self.pools.values():self.stack.enter_context(pool)
            self._started=True
            if self.epoch()!=self.c['epoch']:raise Denied('restore_epoch')
            with self.connection('witness') as c:c.execute('SELECT provider_witness.assert_runtime(%s,%s,%s,%s)',(sha256(canonical(self.c)).hexdigest(),self.c['build'],self.c['epoch'],source))
            if self.role in ('factory','dispatcher'):
                cfg=RedisConfiguration(**self.c['redis']);keys=Keys(self.c['evidenceKeyId'],{self.c['evidenceKeyId']:unb64(self.c['encryptionKey'])})
                self.evidence=self.stack.enter_context(Evidence(cfg,keys))
            if self.role=='counter':
                if set(self.c.get('networkTargets',{}))!={'dispatcher'} or self.c.get('networkMethods')!={'dispatcher':['/count-provider']}:raise Denied('counter_network_scope')
            if self.role=='recovery':
                from private_runtime.registry import NoOutbound
                if self.c.get('networkTargets') or self.c.get('networkMethods'):raise Denied('recovery_network_scope')
                self.client=NoOutbound()
            else:self.client=ServiceClient(self.c,self.identity,self.transport)
            return self
        except BaseException:self._started=False;self.stack.close();raise
    def epoch(self):
        with self.connection('witness') as c:return c.execute('SELECT provider_witness.epoch()').fetchone()[0]
