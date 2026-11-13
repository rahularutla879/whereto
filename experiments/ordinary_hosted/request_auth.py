"""Extend the frozen HTTP liveness proof to two fixed ordinary methods, not native RPC."""
from experiments.hosted_startup.public_auth import binding,REQUEST,FORWARD
from experiments.hosted_identity.auth import verify_proof,digest
from experiments.service_isolation.auth import unb64
from experiments.shared_state.evidence_models import strict_json
from experiments.shared_state.contracts import Denied
PATHS={'/health':'GET','/api/interpret':'POST','/api/plans/generate':'POST'}
class RequestVerifier:
 def __init__(self,auth):self.a=auth
 def check(self,headers,method,path,body):
  a=self.a;c=a.c
  if PATHS.get(path)!=method or len(body)>65536 or (method=='GET' and body) or a.epoch()!=c['epoch']:raise Denied('ordinary_scope')
  if any(len(headers.get_all(h,[]))!=1 for h in ('Authorization','X-Whereto-Context')):raise Denied('ordinary_headers')
  if any(headers.get(h) for h in ('X-Serverless-Authorization','X-Whereto-User','X-Goog-Authenticated-User-Id','X-Goog-Authenticated-User-Email')):raise Denied('ordinary_headers')
  token=headers['Authorization']
  if not token.startswith('Bearer '):raise Denied('ordinary_auth')
  token=token[7:];ctx=strict_json(unb64(headers['X-Whereto-Context']))
  if set(ctx)!={'forward','iap','proof'}:raise Denied('ordinary_context')
  principal,p=verify_proof(c,ctx['proof'],REQUEST,'backend');claims=a.tokens.verify(token,'workload',c['audiences']['backend']);enrolled=c['enrollment'].get(principal,{})
  if principal!='frontend' or principal in c['revoked'] or claims['sub']!=enrolled.get('sub') or claims.get('email')!=enrolled.get('email') or claims.get('email_verified') is not True:raise Denied('ordinary_caller')
  if set(p)!=set('iss sub aud iat exp jti build environment epoch request oidc iap forward'.split()) or p['request']!=binding('backend',method,path,body) or p['oidc']!=digest(token.encode()) or p['iap']!=digest(ctx['iap'].encode()) or p['forward']!=digest(ctx['forward'].encode()):raise Denied('ordinary_binding')
  signer,f=verify_proof(c,ctx['forward'],FORWARD,'public-user-pipeline')
  if signer!='frontend' or set(f)!=set('iss sub aud iat exp jti build environment epoch request iap'.split()) or f['request']!=binding('public-user-pipeline',method,path,body) or f['iap']!=digest(ctx['iap'].encode()):raise Denied('ordinary_user')
  owner=a.user(ctx['iap']);a.consume(c['service'],'frontend-user',f['jti'],f['request'],f['exp']*1000);a.consume(c['service'],principal,p['jti'],p['request'],p['exp']*1000)
  return owner
