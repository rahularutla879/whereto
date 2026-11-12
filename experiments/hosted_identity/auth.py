"""Google identity plus distinct request/user proofs; no synthetic identity fallback."""
from contextvars import ContextVar
from hashlib import sha256
import time,secrets,json,http.client
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from experiments.service_isolation.auth import TLS,b64,unb64,MAX_BODY,MAX_RESPONSE,binding
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.hosted_identity.tokens import Tokens,OfflineKeys,GoogleKeys

USER=ContextVar('verified_user_forward',default=None)
PROOF='urn:whereto:request-proof:v1';FORWARD='urn:whereto:iap-forward:v1'
PRODUCT={'/interpret','/lookup','/continue','/select','/refresh'}

def digest(v):return sha256(v).hexdigest()
def private(c):return Ed25519PrivateKey.from_private_bytes(unb64(c['signingKey']))
def signed(c,doc):return jwt.encode(doc,private(c),algorithm='EdDSA',headers={'kid':c['principal']})
def proof(c,target,path,body,oidc,iap,forward):
    now=int(time.time());return signed(c,dict(iss=PROOF,sub=c['principal'],aud=target,iat=now,exp=now+60,jti=secrets.token_hex(16),
        build=c['identityBuild'],environment=c['identityEnvironment'],epoch=c['epoch'],request=binding(target,path,body),oidc=digest(oidc.encode()),iap=digest(iap.encode()),forward=digest(forward.encode())))
def verify_proof(c,token,issuer,audience):
    from experiments.hosted_identity.tokens import header
    try:
        h=header(token)
        if h.get('alg')!='EdDSA':raise ValueError()
        principal=h['kid'];pub=Ed25519PublicKey.from_public_bytes(unb64(c['trust'][principal]['publicKey']))
        d=jwt.decode(token,pub,algorithms=['EdDSA'],audience=audience,issuer=issuer,options={'require':['iss','sub','aud','iat','exp','jti'],'strict_aud':True})
        now=int(time.time())
        if d['sub']!=principal or type(d['iat']) is not int or type(d['exp']) is not int or not now-60<=d['iat']<=now or not now<d['exp']<=d['iat']+60 or type(d['jti']) is not str or len(d['jti'])!=32 or any(x not in '0123456789abcdef' for x in d['jti']):raise ValueError()
        if d['build']!=c['identityBuild'] or d['environment']!=c['identityEnvironment'] or d['epoch']!=c['epoch']:raise ValueError()
        return principal,d
    except (KeyError,ValueError,TypeError,jwt.PyJWTError):raise Denied('request_proof') from None

class _Boundary:
    """Common policy checks; trust roots are selected by distinct constructors."""
    def user(self,assertion):
        c=self.c;v=self.tokens.verify(assertion,'iap',c['iapAudience'])
        if v['sub'] not in c['testers']:raise Denied('tester_access')
        return 'iap-v1:'+digest(canonical([v['iss'],v['aud'],v['sub']]))
    def forward(self,path,body,iap):
        self.user(iap);now=int(time.time());v=self.tokens.verify(iap,'iap',self.c['iapAudience'])
        return signed(self.c,dict(iss=FORWARD,sub='frontend',aud='native-user-pipeline',iat=now,exp=min(now+60,v['exp']),jti=secrets.token_hex(16),build=self.c['identityBuild'],environment=self.c['identityEnvironment'],epoch=self.c['epoch'],request=binding('native-user-pipeline',path,body),iap=digest(iap.encode())))
    def check(self,headers,path,raw):
        c=self.c
        try:
            if self.epoch()!=c['epoch']:raise Denied('restore_epoch')
            for name in ('Authorization','X-Whereto-Context'):
                if len(headers.get_all(name,[]))!=1:raise Denied('auth_headers')
            if headers.get('X-Serverless-Authorization') or headers.get('X-Goog-Authenticated-User-Id') or headers.get('X-Goog-Authenticated-User-Email') or headers.get('X-Whereto-User'):raise Denied('untrusted_identity_header')
            auth=headers['Authorization']
            if not auth.startswith('Bearer '):raise Denied('authentication')
            oidc=auth[7:];ctx=strict_json(unb64(headers['X-Whereto-Context']))
            if set(ctx)!={'proof','iap','forward'}:raise Denied('auth_context')
            principal,p=verify_proof(c,ctx['proof'],PROOF,c['service'])
            if set(p)!=set('iss sub aud iat exp jti build environment epoch request oidc iap forward'.split()):raise Denied('proof_fields')
            claims=self.tokens.verify(oidc,'workload',c['audiences'][c['service']]);enrolled=c['enrollment'][principal]
            if claims['sub']!=enrolled['sub'] or claims.get('email')!=enrolled['email'] or claims.get('email_verified') is not True or principal in c['revoked'] or principal not in c['allow'].get(path,[]):raise Denied('caller')
            if p['request']!=binding(c['service'],path,raw) or p['oidc']!=digest(oidc.encode()) or p['iap']!=digest(ctx['iap'].encode()) or p['forward']!=digest(ctx['forward'].encode()):raise Denied('request_binding')
            owner=None
            if c['service'] in ('backend','factory') and path in PRODUCT:
                if not ctx['iap'] or not ctx['forward']:raise Denied('user_required')
                signer,f=verify_proof(c,ctx['forward'],FORWARD,'native-user-pipeline')
                if set(f)!=set('iss sub aud iat exp jti build environment epoch request iap'.split()) or signer!='frontend' or f['request']!=binding('native-user-pipeline',path,raw) or f['iap']!=digest(ctx['iap'].encode()):raise Denied('user_scope')
                owner=self.user(ctx['iap']);self.consume(c['service'],'frontend-user',f['jti'],f['request'],f['exp']*1000)
            elif ctx['iap'] or ctx['forward']:raise Denied('unexpected_user_context')
            self.consume(c['service'],principal,p['jti'],p['request'],p['exp']*1000)
            return owner,ctx
        except (ValueError,TypeError,KeyError):raise Denied('authentication') from None

class Auth(_Boundary):
    """Explicit offline fixture constructor; never a production trust root."""
    def __init__(self,c,consume,epoch):
        if c.get('identityEnvironment')!='offline-hosted-contract':raise Denied('offline_environment')
        self.c=c;self.consume=consume;self.epoch=epoch;self.tokens=Tokens(OfflineKeys(c['googleKeys']),offline=True)

class HostedAuth(_Boundary):
    """Dormant production constructor: fixed Google roots, no injected test keys."""
    def __init__(self,c,consume,epoch):
        if 'googleKeys' in c or c.get('identityEnvironment') not in ('private-staging','production'):raise Denied('hosted_enrollment')
        self.c=c;self.consume=consume;self.epoch=epoch;self.tokens=Tokens(GoogleKeys())

class Client:
    def __init__(self,c):self.c=c
    def request(self,target,path,value,*,context=None,raw=None,auth_override=None):
        c=self.c;t=c['targets'][target];service=t.get('service',target);wire=canonical(value) if raw is None else raw
        if len(wire)>MAX_BODY:raise Denied('body_bound')
        user=(context if context is not None else USER.get()) or {'iap':'','forward':''}
        iap=user['iap'] if service in ('backend','factory') and path in PRODUCT else '';forward=user['forward'] if iap else ''
        oidc=c['oidcTokens'][c['audiences'][service]];ctx=dict(proof=proof(c,service,path,wire,oidc,iap,forward),iap=iap,forward=forward)
        headers={'Content-Type':'application/json','Authorization':'Bearer '+oidc,'X-Whereto-Context':b64(canonical(ctx))}
        if auth_override is not None:headers.update(auth_override)
        conn=TLS(t['port'],t['hostname'],c['ca'],120)
        try:
            conn.request('POST',path,wire,headers);r=conn.getresponse();data=r.read(MAX_RESPONSE+1)
            if r.status!=200 or len(data)>MAX_RESPONSE:raise Denied('service_refused')
            d=strict_json(data)
            if set(d)!={'result'}:raise Denied('service_response')
            return d['result']
        except (OSError,http.client.HTTPException):raise Unavailable() from None
        finally:conn.close()
