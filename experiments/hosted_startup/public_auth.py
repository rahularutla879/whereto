"""Method-aware public HTTP proof, separately named from frozen native POST RPC.
Only health is admissible here. This is not a public/native planning adapter.
"""
from hashlib import sha256
from experiments.hosted_identity.auth import verify_proof,digest
from experiments.service_isolation.auth import unb64
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.shared_state.contracts import Denied
REQUEST='urn:whereto:http-request-proof:v1';FORWARD='urn:whereto:http-iap-forward:v1'
def binding(audience,method,path,body):return sha256(canonical([audience,method,path,sha256(body).hexdigest()])).hexdigest()
class StatusVerifier:
    def __init__(self,identity):self.identity=identity
    def check(self,headers,method,path,body):
        a=self.identity;c=a.c
        if method!='GET' or path!='/health' or body or a.epoch()!=c['epoch']:raise Denied('status_scope')
        if any(len(headers.get_all(h,[]))!=1 for h in ('Authorization','X-Whereto-Context')):raise Denied('status_headers')
        if any(headers.get(h) for h in ('X-Serverless-Authorization','X-Whereto-User','X-Goog-Authenticated-User-Id','X-Goog-Authenticated-User-Email')):raise Denied('status_headers')
        token=headers['Authorization']
        if not token.startswith('Bearer '):raise Denied('status_auth')
        token=token[7:];ctx=strict_json(unb64(headers['X-Whereto-Context']))
        if set(ctx)!={'forward','iap','proof'}:raise Denied('status_context')
        principal,p=verify_proof(c,ctx['proof'],REQUEST,'backend')
        claims=a.tokens.verify(token,'workload',c['audiences']['backend']);enrolled=c['enrollment'].get(principal,{})
        if principal!='frontend' or principal in c['revoked'] or claims['sub']!=enrolled.get('sub') or claims.get('email')!=enrolled.get('email') or claims.get('email_verified') is not True:raise Denied('status_caller')
        if set(p)!=set('iss sub aud iat exp jti build environment epoch request oidc iap forward'.split()) or p['request']!=binding('backend',method,path,body) or p['oidc']!=digest(token.encode()) or p['iap']!=digest(ctx['iap'].encode()) or p['forward']!=digest(ctx['forward'].encode()):raise Denied('status_binding')
        signer,f=verify_proof(c,ctx['forward'],FORWARD,'public-user-pipeline')
        if signer!='frontend' or set(f)!=set('iss sub aud iat exp jti build environment epoch request iap'.split()) or f['request']!=binding('public-user-pipeline',method,path,body) or f['iap']!=digest(ctx['iap'].encode()):raise Denied('status_user')
        owner=a.user(ctx['iap'])
        a.consume('backend','frontend-user',f['jti'],f['request'],f['exp']*1000);a.consume('backend',principal,p['jti'],p['request'],p['exp']*1000)
        return owner
