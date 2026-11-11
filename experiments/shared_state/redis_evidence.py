"""Inactive synthetic-only Redis/SQL evidence adapter; no live transport or keys."""
from dataclasses import dataclass,field
from hashlib import sha256
import hmac
import os
from pathlib import Path
from threading import RLock
from types import MappingProxyType
import re
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import redis
from psycopg.types.json import Jsonb

from experiments.shared_state.action_bridge import BridgeStore,LocalIssuer
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import VERSION,MAX_BYTES,canonical,pack,unpack

# Single Redis instance / non-cluster Memorystore. All keys explicitly passed.
CAS='''
local t=redis.call('TIME');local now=tonumber(t[1])*1000+math.floor(tonumber(t[2])/1000)
local expired=redis.call('ZRANGEBYSCORE',KEYS[2],'-inf',now,'LIMIT',0,351)
if #expired>350 or redis.call('ZCARD',KEYS[2])>350 or redis.call('HLEN',KEYS[3])>350 then return -3 end
for _,k in ipairs(expired) do redis.call('ZREM',KEYS[2],k);redis.call('HDEL',KEYS[3],k) end
local current=redis.call('GET',KEYS[1])
if (ARGV[1]=='new' and current) or (ARGV[1]=='old' and current~=ARGV[2]) then return -1 end
local deadline=tonumber(ARGV[4]);if not deadline or deadline<=now then return -2 end
local total=0;for _,v in ipairs(redis.call('HVALS',KEYS[3])) do total=total+tonumber(v) end
local prior=tonumber(redis.call('HGET',KEYS[3],KEYS[1]) or '0')
if total-prior+string.len(ARGV[3])>tonumber(ARGV[5]) then return -3 end
if not current and redis.call('ZCARD',KEYS[2])>=350 then return -3 end
local oldscore=tonumber(redis.call('ZSCORE',KEYS[2],KEYS[1]) or '0')
redis.call('HSET',KEYS[3],KEYS[1],math.max(prior,string.len(ARGV[3])))
redis.call('ZADD',KEYS[2],math.max(oldscore,deadline),KEYS[1])
local latest=redis.call('ZREVRANGE',KEYS[2],0,0,'WITHSCORES')
redis.call('PEXPIREAT',KEYS[2],latest[2]);redis.call('PEXPIREAT',KEYS[3],latest[2])
redis.call('SET',KEYS[1],ARGV[3],'PXAT',deadline)
redis.call('HSET',KEYS[3],KEYS[1],string.len(ARGV[3]));redis.call('ZADD',KEYS[2],deadline,KEYS[1])
return 1
'''


@dataclass(frozen=True,repr=False)
class Keys:
    active: str
    read_keys: dict=field(repr=False)

    def __post_init__(self):
        object.__setattr__(self,"read_keys",MappingProxyType(dict(self.read_keys)))

    def key(self,kid):
        if type(kid) is not str:raise Denied('encryption_key')
        value=self.read_keys.get(kid)
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',kid) or type(value) is not bytes or len(value)!=32:
            raise Denied('encryption_key')
        return value


class RedisEvidence:
    """No credential discovery. Only network-isolated disposable fixtures admitted.

    A future hosted adapter needs separate enrollment/TLS configuration review.
    This class cannot be selected by application startup or target a cloud host.
    """
    def __init__(self,password,keys,*,maximum=128*1024*1024,tls_ca=None):
        if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:
            raise Denied('isolated_fixture_required')
        if type(keys) is not Keys or type(maximum) is not int or not MAX_BYTES<=maximum<=128*1024*1024:
            raise Denied('evidence_configuration')
        keys.key(keys.active)
        self.keys,self.maximum=keys,maximum
        if tls_ca not in (None,'/tmp/synthetic-redis-ca.crt'):raise Denied('local_tls_fixture')
        tls=dict(ssl=True,ssl_cert_reqs='required',ssl_check_hostname=True,ssl_ca_certs=tls_ca) if tls_ca else {}
        self.client=redis.Redis(host='127.0.0.1',port=6380 if tls_ca else 6379,password=password,**tls,
            socket_connect_timeout=1,socket_timeout=1,max_connections=4,
            retry=redis.retry.Retry(redis.backoff.NoBackoff(),0),decode_responses=False)

    def _run(self,fn):
        try:return fn()
        except redis.RedisError:raise Unavailable() from None

    def path(self,env,epoch,sid):
        if env!='synthetic' or not re.fullmatch('[0-9a-f]{64}',epoch) or not re.fullmatch('[0-9a-f]{64}',sid):
            raise Denied('evidence_namespace')
        return f'{VERSION}:{{{env}:{epoch}}}:{sid}'

    def get(self,path):
        raw=self._run(lambda:self.client.get(path))
        if raw is None or len(raw)>MAX_BYTES+28:raise Denied('evidence_missing')
        return raw

    def publish(self,path,old,blob,expires):
        if type(blob) is not bytes or not 28<=len(blob)<=MAX_BYTES+28 or type(expires) is not int:
            raise Denied('evidence_capacity')
        prefix=path.rsplit(':',1)[0]
        result=self._run(lambda:self.client.eval(CAS,3,path,prefix+':index',prefix+':sizes',
                         'new' if old is None else 'old',old or b'',blob,expires,self.maximum))
        if result!=1:raise Denied('evidence_cas_or_capacity')


class EvidenceStore(BridgeStore):
    """Additive SQL front door; financial algorithms remain the frozen V4 code."""
    def __init__(self,*,evidence,current_epoch,verifier,**kwargs):
        from experiments.shared_state.evidence_identity import verify
        verify()
        self.evidence,self.current_epoch=evidence,current_epoch
        self._verifier=verifier
        self._proof=None
        self._dispatch_lock=RLock()
        super().__init__(**kwargs)

    def _invoke(self,c,action,args):
        try:epoch=self.current_epoch()  # Must be supplied outside both DB and Redis.
        except OSError:raise Unavailable() from None
        if type(epoch) is not str or not re.fullmatch('[0-9a-f]{64}',epoch):raise Denied('restore_epoch')
        return c.execute('SELECT synthetic_state.evidence_protocol(%s,%s,%s,%s,%s) AS result',
            (action,Jsonb(args),'synthetic',epoch,self._proof)).fetchone()['result']

    def create(self,kind,payload,*,ttl=600):
        from experiments.shared_state.contracts import SessionHandle,Kind
        prepared=self._prepared(kind,payload)
        maximum=1800 if kind is Kind.ACTION and payload.purpose in ('details','refresh') else 600
        if type(ttl) is not int or not 1<=ttl<=maximum:raise Denied('expiry')
        handle=SessionHandle(secrets.token_urlsafe(32))
        self._call('create',session=self._hash(handle.token,'session'),ttl=ttl,**prepared)
        return handle

    def _prepared(self,kind,payload):
        from experiments.shared_state.contracts import Kind
        if kind is not Kind.ACTION:raise Denied("private_sql_payload_forbidden")
        return super()._prepared(kind,payload)

    def meta(self,lease):return super()._call('evidence_meta',**self._lease(lease))

    def _aad(self,meta,anchor):
        # Worker/fence checked live in SQL; excluding them here permits safe reclamation.
        return canonical({'version':VERSION,'session':meta['session'],'revision':meta['revision'],
            'binding':meta['binding'],'action':meta['action'],'budget':meta['budget'],'anchor':anchor})

    def recover(self,lease):
        m=self.meta(lease);a=m['anchor']
        if not a or a['epoch']!=self.current_epoch() or a['environment']!='synthetic':raise Denied('evidence_anchor')
        blob=self.evidence.get(self.evidence.path('synthetic',a['epoch'],m['session']))
        if not hmac.compare_digest(sha256(blob).hexdigest(),a['commitment']):raise Denied('evidence_integrity')
        # Commitment is over ciphertext; it cannot also be AEAD associated data.
        aad={k:v for k,v in a.items() if k!='commitment'}
        try:raw=AESGCM(self.evidence.keys.key(a['key_id'])).decrypt(blob[:12],blob[12:],self._aad(m,aad))
        except (InvalidTag,ValueError):raise Denied('evidence_integrity') from None
        records=unpack(raw)
        # Recheck under SQL lock after Redis IO; concurrent revision/anchor changes refuse.
        if self.meta(lease)!=m:raise Denied('evidence_changed')
        return records,a['commitment']

    def _call(self,verb,**args):
        with self._dispatch_lock:
            if verb not in ('reserve','dispatch'):return super()._call(verb,**args)
            lease=getattr(self,'_active_evidence_lease',None)
            if lease is None or self._lease(lease)!={k:args[k] for k in ('session','revision','worker','fence')}:
                raise Denied('evidence_lease')
            self._proof=self._verifier.authorize(self,lease,verb,args)
            try:return super()._call(verb,**args)
            finally:self._proof=None

    def claim(self,handle,revision):
        lease=super().claim(handle,revision);self._active_evidence_lease=lease
        return lease

    def publish(self,lease,records,provenance,issuer_connection,*,previous=0,lifetime=None,absolute_deadline=None):
        # Only the separately supplied issuer connection can commit the SQL anchor.
        raw=pack(records,provenance)
        if type(previous) is not int or not 0<=previous<=10**12:raise Denied('evidence_cas')
        maximum=1800 if 'membership' in records and records['membership'].purpose in ('details','refresh') else 600
        lifetime=maximum if lifetime is None else lifetime
        if type(lifetime) is not int or not 1<=lifetime<=maximum:raise Denied('evidence_expiry')
        m=self.meta(lease);a=m['anchor']
        if (a is None and previous!=0) or (a and a['generation']!=previous):raise Denied('evidence_cas')
        if a:
            self.recover(lease)
            old=self.evidence.get(self.evidence.path('synthetic',a['epoch'],m['session']))
            if not hmac.compare_digest(sha256(old).hexdigest(),a['commitment']):raise Denied('evidence_changed')
        else:old=None
        # All authorities use fixed original SQL expiry. Routes use <=300s.
        now=self._call('evidence_clock')['now_ms']
        deadline=min(m['expires_ms'],now+lifetime*1000,a['expires_ms'] if a else m['expires_ms'])
        if absolute_deadline is not None:
            if type(absolute_deadline) is not int or not 0<absolute_deadline<10**13:raise Denied('evidence_expiry')
            deadline=min(deadline,absolute_deadline)
        if 'route' in records:
            deadline=min(deadline,now+300000)
            for leg in records['route'].legs:
                observed=leg.observed_at
                if observed is None or observed.tzinfo is None or observed.utcoffset() is None:
                    raise Denied('route_observation')
                stamp=int(observed.timestamp()*1000)
                if stamp>now or stamp+300000<=now:raise Denied('route_observation')
                deadline=min(deadline,stamp+300000)
        anchor=dict(session=m['session'],revision=m['revision'],generation=previous+1,
            expires_ms=deadline,key_id=self.evidence.keys.active,environment='synthetic',epoch=self.current_epoch())
        nonce=secrets.token_bytes(12)
        blob=nonce+AESGCM(self.evidence.keys.key(anchor['key_id'])).encrypt(nonce,raw,self._aad(m,anchor))
        self.evidence.publish(self.evidence.path('synthetic',anchor['epoch'],m['session']),old,blob,deadline)
        try:
            with issuer_connection() as c:
                c.execute('SELECT synthetic_state.evidence_anchor(%s,%s,%s,%s,%s,%s,%s,%s)',
                    (m['session'],m['revision'],previous,sha256(blob).hexdigest(),anchor['key_id'],deadline,'synthetic',anchor['epoch']))
        except Exception:
            # Never roll back/refund financial state or silently repair a torn publication.
            raise Denied('evidence_commit') from None
        return previous+1


class EvidenceVerifier:
    """Trusted synthetic verifier; only it receives an issuer connection factory.

    Production must isolate this code/key/connection behind workload authentication.
    A worker-controlled digest is never accepted as a read attestation.
    """
    def __init__(self,connection):self.__connection=connection

    def authorize(self,store,lease,verb,args):
        if verb not in ('reserve','dispatch') or store._lease(lease)!={k:args[k] for k in ('session','revision','worker','fence')}:
            raise Denied('evidence_command')
        _,commitment=store.recover(lease)
        nonce=secrets.token_hex(32)
        try:
            with self.__connection() as c:
                c.execute('SELECT synthetic_state.evidence_attest(%s,%s,%s,%s,%s,%s)',
                    (nonce,verb,Jsonb(args),commitment,'synthetic',store.current_epoch()))
        except Exception:raise Denied('evidence_attestation') from None
        return nonce


class EvidenceIssuer(LocalIssuer):
    def __init__(self,connection,root,records):
        super().__init__(connection,root);self._connection=connection;self._records=records

    def register(self,store,lease,http,inference=None,refresh=None):
        super().register(store,lease,http,inference,refresh)

    def approve(self,store,lease,cap,outing,plans):
        super().approve(store,lease,cap,outing,plans)
        records,provenance=self._records()
        store.publish(lease,records,provenance,self._connection)
