"""Synthetic token port is test-only; production clients never load fixture keys."""
from private_runtime.https import HTTPS
from private_runtime.service_client import ServiceClient
from experiments.hosted_identity.auth import Auth
from experiments.shared_state.contracts import Denied
class Identity:
 def __init__(self,c):self.c=c;self.verifier=Auth(c,lambda *a:None,lambda:c['epoch']).tokens
 def token(self,audience):
  token=self.c['oidcTokens'][audience];v=self.verifier.verify(token,'workload',audience);e=self.c['enrollment'][self.c['principal']]
  if v['sub']!=e['sub'] or v.get('email')!=e['email'] or v.get('email_verified') is not True:raise Denied('assigned_fixture_identity')
  return token
class Client(ServiceClient):
 def __init__(self,c):
  c={**c,'networkTargets':{k:dict(url='https://'+v['hostname']+':'+str(v['port']),audience=c['audiences'][v.get('service',k)],service=v.get('service',k)) for k,v in c['targets'].items()},'networkMethods':{k:['/ordinary','/ui-probe','/count','/send','/dispatch-check'] for k in c['targets']}}
  super().__init__(c,Identity(c),HTTPS(ca_file=c['ca']))
