"""TLS/AUTH Redis port reusing the existing bounded encrypted-evidence CAS."""
from dataclasses import dataclass,field
from pathlib import Path
import re,os
import redis
from experiments.shared_state.redis_evidence import RedisEvidence,Keys
from experiments.shared_state.evidence_models import MAX_BYTES,VERSION
from experiments.shared_state.contracts import Denied,Unavailable

@dataclass(frozen=True,repr=False)
class RedisConfiguration:
    host:str
    port:int
    username:str
    password:str=field(repr=False)
    ca_file:str
    environment:str
    epoch:str
    maximum:int=128*1024*1024
    protocol_alias:str|None=None
    def __post_init__(self):
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}',self.host) or type(self.port) is not int or not 1<=self.port<=65535
            or not re.fullmatch('[a-z][a-z0-9_-]{0,62}',self.username) or not self.password or not Path(self.ca_file).is_file()
            or self.environment not in ('private-staging','synthetic') or not re.fullmatch('[0-9a-f]{64}',self.epoch)
            or self.protocol_alias not in (None,'synthetic') or type(self.maximum) is not int or not MAX_BYTES<=self.maximum<=128*1024*1024):raise Denied('redis_enrollment')

class EvidenceRedis(RedisEvidence):
    def __init__(self,config,keys):
        if type(config) is not RedisConfiguration or type(keys) is not Keys:raise Denied('redis_enrollment')
        keys.key(keys.active);self.c=config;self.keys=keys;self.maximum=config.maximum;self._pid=os.getpid();self._closed=False
        self.client=redis.Redis(host=config.host,port=config.port,username=config.username,password=config.password,
            ssl=True,ssl_cert_reqs='required',ssl_check_hostname=True,ssl_ca_certs=config.ca_file,
            socket_connect_timeout=1,socket_timeout=1,max_connections=4,decode_responses=False,
            retry=redis.retry.Retry(redis.backoff.NoBackoff(),0))
    def _run(self,fn):
        if self._closed or os.getpid()!=self._pid:raise Denied('redis_lifecycle')
        return super()._run(fn)
    def path(self,environment,epoch,sid):
        if environment not in (self.c.environment,self.c.protocol_alias) or epoch!=self.c.epoch or not re.fullmatch('[0-9a-f]{64}',sid):raise Denied('evidence_namespace')
        return f'{VERSION}:{{{self.c.environment}:{epoch}}}:{sid}'
    def start(self):
        if self._run(self.client.ping) is not True:raise Unavailable()
        return self
    def close(self):self._closed=True;self.client.close();self.client.connection_pool.disconnect()
    def __enter__(self):return self.start()
    def __exit__(self,*_):self.close()
