"""Assigned Cloud Run identity only; no ADC, keys, impersonation or fixture fallback."""
import http.client
import time
from threading import Lock
from urllib.parse import urlencode
from experiments.hosted_identity.tokens import Tokens,GoogleKeys
from private_runtime.https import Endpoint
from experiments.shared_state.contracts import Denied,Unavailable

class GoogleIdentity:
    def __init__(self,config):
        if config.get('identityEnvironment') not in ('private-staging','production') or any(k in config for k in ('googleKeys','oidcTokens','certificate','tlsKey')):raise Denied('hosted_identity_configuration')
        self.enrolled=dict(config['enrollment'][config['principal']]);self.audiences=frozenset(config['audiences'].values())
        if not 1<=len(self.audiences)<=8:raise Denied('audiences')
        for audience in self.audiences:Endpoint(audience,audience)
        self.tokens=Tokens(GoogleKeys());self._cache={};self._last={};self._lock=Lock()
    def token(self,audience):
        if audience not in self.audiences:raise Denied('audience')
        with self._lock:
            now=time.time();prior=self._cache.get(audience)
            if prior and prior[1]>now+30:return prior[0]
            if now-self._last.get(audience,0)<5:raise Unavailable()
            self._last[audience]=now;self._cache.pop(audience,None)
            c=http.client.HTTPConnection('metadata.google.internal',timeout=2)
            try:
                c.request('GET','/computeMetadata/v1/instance/service-accounts/default/identity?'+urlencode({'audience':audience,'format':'full'}),headers={'Metadata-Flavor':'Google'})
                r=c.getresponse();raw=r.read(16385)
                if r.status!=200 or r.getheader('Metadata-Flavor')!='Google' or len(raw)>16384:raise Denied('metadata_response')
                token=raw.decode('ascii')
                if token!=token.strip():raise Denied('metadata_response')
                claims=self.tokens.verify(token,'workload',audience)
                if claims['sub']!=self.enrolled['sub'] or claims.get('email')!=self.enrolled['email'] or claims.get('email_verified') is not True or claims['exp']<=time.time()+30:raise Denied('assigned_identity')
                self._cache[audience]=(token,claims['exp']);return token
            except (OSError,UnicodeError,http.client.HTTPException):raise Unavailable() from None
            finally:c.close()
