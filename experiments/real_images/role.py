"""Out-of-image fixture driver; never part of a production projection."""
from pathlib import Path
import json,types,ast
from datetime import datetime,timezone
from private_runtime.real_application.ports import Ports
from private_runtime.real_application.startup import compose
from private_runtime.real_application.entry import serve
from private_runtime.https import HTTPS,Endpoint
from private_runtime.provider_callbacks import OpenAIHTTP
from backend.provider_responses import HTTPResult,google_request
from experiments.hosted_identity.auth import _Boundary
# Original offline verifier lives ONLY under /testing, not on the image path.
n=types.ModuleType('fixture_tokens');n.__file__='/testing/tokens.py';exec(compile(Path(n.__file__).read_bytes(),n.__file__,'exec'),vars(n))
class FixtureTokens:
    """External signed-fixture test port; never the production Google trust root."""
    def __init__(self,docs):self.keys={k:n.keyset(v,k,offline=True) for k,v in docs.items()}
    def verify(self,token,kind,audience):
        import time
        h=n.header(token)
        if h['alg']!=n.ALGORITHMS[kind]:raise ValueError('Fixture algorithm')
        v=n.jwt.decode(token,self.keys[kind][h['kid']],algorithms=[n.ALGORITHMS[kind]],audience=audience,issuer=n.ISSUERS[kind],options={'require':['iss','aud','sub','iat','exp'],'strict_aud':True},leeway=5)
        now=int(time.time());maximum=3600 if kind=='workload' else 660
        if type(v['iat'])is not int or type(v['exp'])is not int or not v['iat']<v['exp'] or v['exp']<=now or v['iat']>now+5 or v['exp']>v['iat']+maximum or not isinstance(v['sub'],str) or not 1<=len(v['sub'])<=256:raise ValueError('Fixture claims')
        return v
class FixtureAuth(_Boundary):
    def __init__(self,c,consume,epoch):
        assert c['identityEnvironment']=='private-staging' and 'googleKeys' in c
        self.c,self.consume,self.epoch=c,consume,epoch;self.tokens=FixtureTokens(c['googleKeys'])
class Identity:
    def __init__(self,c):self.c=c
    def token(self,audience):return self.c['oidcTokens'][audience]
class Transport:
    def __init__(self,p,cert):self.http=HTTPS(ca_file=cert);self.endpoint=Endpoint('https://localhost:'+str(p),'https://localhost:'+str(p))
    def request(self,endpoint,method,path,body,headers):
        assert endpoint.url=='https://api.openai.com'
        return self.http.request(self.endpoint,method,path,body,headers)
class Google:
    account='fictional-google-project'
    def __init__(self,t):self.t=t
    def __call__(self,wire,sku,units):
        v,s,u=google_request(wire);assert (s,u)==(sku,units)
        path='/v1/places:searchText' if v['operation']=='search' else '/distanceMatrix/v2:computeRouteMatrix'
        return HTTPResult(200,self.t.http.request(self.t.endpoint,'POST',path,json.dumps(v['body']).encode(),{'Content-Type':'application/json'}))
v=json.loads(Path('/testing/config.json').read_bytes());c=v['config'];role=c['service']
with Ports(role,c,identity=Identity(c),authentication_factory=FixtureAuth,transport=HTTPS(ca_file=v['certificate'])) as ports:
    provider=google=None
    if role=='dispatcher':
        t=Transport(v['provider'],v['certificate']);provider={p:OpenAIHTTP(c['openaiProject'],lambda:'sk-FICTIONAL-IMAGE-TEST',t,purpose=p) for p in ('count','generation')};google=Google(t)
    r=compose(ports,provider=provider,google=google)
    print('IMAGE_ROLE_READY',flush=True);serve(r,tls=(v['certificate'],v['tlsKey']))
