"""Reuse existing request proofs/user propagation; replace only the HTTPS channel."""
from copy import deepcopy
from private_runtime.https import Endpoint,HTTPS,Refused

class ServiceClient:
    def __init__(self,config,identity,transport=None):
        # identity is a trusted server-owned token port, never request JSON.
        self.c=deepcopy(config);self.identity=identity;self.transport=transport or HTTPS()
        self.targets={name:(Endpoint(v['url'],v['audience']),v['service']) for name,v in self.c['networkTargets'].items()}
        if not 1<=len(self.targets)<=8:raise Refused('targets')
        for endpoint,service in self.targets.values():
            if endpoint.audience!=self.c['audiences'][service]:raise Refused('audience')
    def request(self,target,path,value,*,context=None,raw=None):
        from experiments.hosted_identity.auth import USER,PRODUCT,proof
        from experiments.service_isolation.auth import b64,MAX_BODY
        from experiments.shared_state.evidence_models import canonical,strict_json
        from experiments.shared_state.contracts import Denied,Unavailable
        c=self.c
        if target not in self.targets or path not in c['networkMethods'].get(target,[]):raise Denied('network_method')
        ep,service=self.targets[target];wire=canonical(value) if raw is None else raw
        if type(wire) is not bytes or len(wire)>MAX_BODY:raise Denied('body_bound')
        user=(context if context is not None else USER.get()) or {'iap':'','forward':''}
        iap=user['iap'] if service in ('backend','factory') and path in PRODUCT else '';forward=user['forward'] if iap else ''
        token=self.identity.token(ep.audience)
        ctx=dict(proof=proof(c,service,path,wire,token,iap,forward),iap=iap,forward=forward)
        try:
            data=self.transport.request(ep,'POST',path,wire,{'Content-Type':'application/json','Authorization':'Bearer '+token,'X-Whereto-Context':b64(canonical(ctx))})
            result=strict_json(data)
            if type(result) is not dict or set(result)!={'result'}:raise Denied('service_response')
            return result['result']
        except Refused:raise Unavailable() from None
