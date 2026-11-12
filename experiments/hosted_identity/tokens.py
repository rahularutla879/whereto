"""Independent Google workload/IAP verification. No token acquisition or enrollment."""
import json,time,ssl,http.client,re,os
from threading import Lock
import jwt
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.service_isolation.auth import unb64

ISSUERS={'workload':'https://accounts.google.com','iap':'https://cloud.google.com/iap'}
URLS={'workload':('www.googleapis.com','/oauth2/v3/certs'),'iap':('www.gstatic.com','/iap/verify/public_key-jwk')}
ALGORITHMS={'workload':'RS256','iap':'ES256'}


def object_json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError()
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))


def header(token):
    if type(token) is not str or len(token)>16384:raise Denied('identity_token')
    try:
        h,p,s=token.split('.');v=object_json(unb64(h));object_json(unb64(p))
        if type(v) is not dict or set(v)-{'alg','kid','typ'} or v.get('typ','JWT')!='JWT' or type(v.get('kid')) is not str or not 1<=len(v['kid'])<=128:raise ValueError()
        return v
    except (ValueError,KeyError,TypeError):raise Denied('identity_token') from None


def keyset(doc,kind,*,offline=False):
    if type(doc) is not dict or set(doc)!=({'keys','fixture'} if offline else {'keys'}) or (offline and doc['fixture'] is not True):raise Denied('jwks_origin')
    keys=doc['keys']
    if type(keys) is not list or not 1<=len(keys)<=32:raise Denied('jwks_bound')
    result={}
    for k in keys:
        if type(k) is not dict or k.get('alg')!=ALGORITHMS[kind] or k.get('use')!='sig' or type(k.get('kid')) is not str or k['kid'] in result or len(k['kid'])>128:raise Denied('jwks_key')
        if not offline and k['kid'].startswith('task52-offline-'):raise Denied('fixture_key')
        if any(x in k for x in ('d','p','q','dp','dq','qi','oth','k','x5u','jku')):raise Denied('jwks_private_or_remote')
        try:
            value=jwt.PyJWK.from_dict(k,algorithm=ALGORITHMS[kind])
            if kind=='workload' and (k.get('kty')!='RSA' or value.key.key_size<2048):raise ValueError()
            if kind=='iap' and (k.get('kty')!='EC' or k.get('crv')!='P-256'):raise ValueError()
            result[k['kid']]=value.key
        except (ValueError,KeyError,jwt.PyJWTError):raise Denied('jwks_key') from None
    return result

class GoogleKeys:
    """Fixed Google HTTPS origins only. Dormant; tests never call real endpoints."""
    def __init__(self):self._cache={};self._lock=Lock();self._last={}
    def key(self,kind,kid):
        if kind not in URLS or kid.startswith('task52-offline-'):raise Denied('fixture_key')
        with self._lock:
            now=time.monotonic();old=self._cache.get(kind)
            if old and old[0]>now and kid in old[1]:return old[1][kid]
            if now-self._last.get(kind,-1000)<60:raise Denied('jwks_refresh_bound')
            self._last[kind]=now;host,path=URLS[kind]
            c=http.client.HTTPSConnection(host,timeout=5,context=ssl.create_default_context())
            try:
                c.request('GET',path,headers={'Accept':'application/json'});r=c.getresponse();raw=r.read(100001)
                if r.status!=200 or len(raw)>100000:raise ValueError()
                m=re.search(r'(?:^|,)\s*max-age=(\d+)',r.getheader('Cache-Control',''))
                if not m or int(m[1])==0:raise ValueError()
                parsed=keyset(object_json(raw),kind);self._cache[kind]=(now+min(int(m[1]),3600),parsed)
            except (OSError,ValueError,http.client.HTTPException):raise Unavailable() from None
            finally:c.close()
            if kid not in parsed:raise Denied('unknown_key')
            return parsed[kid]

class OfflineKeys:
    """Only disposable-container fixtures. Never accepted by the production verifier."""
    def __init__(self,docs):
        from pathlib import Path
        if any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or os.environ.get('NODE_ENV')=='production' or os.environ.get('WHERETO_ENV')=='production' or not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:raise Denied('offline_keys_only')
        self.docs={k:keyset(v,k,offline=True) for k,v in docs.items()}
    def key(self,kind,kid):
        try:return self.docs[kind][kid]
        except KeyError:raise Denied('unknown_key') from None

class Tokens:
    def __init__(self,keys,*,offline=False):
        if type(keys) is not (OfflineKeys if offline else GoogleKeys):raise Denied('key_source')
        self.keys=keys;self.offline=offline
    def verify(self,token,kind,audience):
        h=header(token)
        if h.get('alg')!=ALGORITHMS[kind] or (not self.offline and h['kid'].startswith('task52-offline-')):raise Denied('identity_algorithm_or_fixture')
        try:
            v=jwt.decode(token,self.keys.key(kind,h['kid']),algorithms=[ALGORITHMS[kind]],audience=audience,issuer=ISSUERS[kind],
                options={'require':['iss','aud','sub','iat','exp'],'strict_aud':True},leeway=5)
            now=int(time.time());maximum=3600 if kind=='workload' else 660
            if type(v['iat']) is not int or type(v['exp']) is not int or v['exp']<=v['iat'] or v['exp']<=now or v['iat']>now+5 or v['exp']>v['iat']+maximum or not isinstance(v['sub'],str) or not 1<=len(v['sub'])<=256:raise ValueError()
            return v
        except (ValueError,TypeError,jwt.PyJWTError):raise Denied('identity_claims') from None
