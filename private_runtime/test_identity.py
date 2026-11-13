"""Metadata protocol unit tests. Positive claims are a test stub, not Google proof."""
import unittest,time
from unittest.mock import patch
from private_runtime.google_identity import GoogleIdentity
from experiments.shared_state.contracts import Denied,Unavailable
class Response:
 status=200
 def getheader(self,k):return 'Google'
 def read(self,n):return b'explicitly-synthetic-opaque-token'
class Connection:
 calls=[]
 def __init__(self,host,timeout):self.host=host
 def request(self,*a,**k):self.calls.append((self.host,a,k))
 def getresponse(self):return Response()
 def close(self):pass
class Stub:
 def verify(self,t,kind,aud):return dict(sub='expected',email='expected@example.invalid',email_verified=True,exp=int(time.time())+300)
def config():return dict(identityEnvironment='private-staging',principal='backend',enrollment={'backend':{'sub':'expected','email':'expected@example.invalid'}},audiences={'factory':'https://factory.invalid'})
class Tests(unittest.TestCase):
 def setUp(self):
  p=patch('socket.socket.connect',side_effect=AssertionError('No identity network'));p.start();self.addCleanup(p.stop)
 def test_fixed_metadata_origin_exact_audience_cache_and_no_external_call(self):
  with patch('private_runtime.google_identity.Tokens',return_value=Stub()),patch('private_runtime.google_identity.http.client.HTTPConnection',Connection):
   Connection.calls=[];p=GoogleIdentity(config());self.assertEqual(p.token('https://factory.invalid'),p.token('https://factory.invalid'));self.assertEqual(len(Connection.calls),1);host,args,kw=Connection.calls[0];self.assertEqual(host,'metadata.google.internal');self.assertIn('audience=https%3A%2F%2Ffactory.invalid',args[1]);self.assertEqual(kw['headers'],{'Metadata-Flavor':'Google'})
 def test_wrong_principal_and_failed_acquisition_no_stale_fallback(self):
  c=config();c['enrollment']['backend']['sub']='wrong'
  with patch('private_runtime.google_identity.Tokens',return_value=Stub()),patch('private_runtime.google_identity.http.client.HTTPConnection',Connection):
   p=GoogleIdentity(c)
   with self.assertRaises(Denied):p.token('https://factory.invalid')
   with self.assertRaises(Unavailable):p.token('https://factory.invalid')
 def test_bad_metadata_flavor_and_near_expiry_refuse(self):
  with patch('private_runtime.google_identity.Tokens',return_value=Stub()),patch('private_runtime.google_identity.http.client.HTTPConnection',Connection):
   with patch.object(Response,'getheader',return_value='wrong'),self.assertRaises(Denied):GoogleIdentity(config()).token('https://factory.invalid')
   with patch.object(Stub,'verify',return_value=dict(sub='expected',email='expected@example.invalid',email_verified=True,exp=int(time.time())+10)),self.assertRaises(Denied):GoogleIdentity(config()).token('https://factory.invalid')
 def test_fixture_configuration_and_wrong_audience_refuse_before_network(self):
  with patch('private_runtime.google_identity.http.client.HTTPConnection',side_effect=AssertionError('No network')):
   for extra in ('googleKeys','oidcTokens','certificate','tlsKey'):
    with self.assertRaises(Denied):GoogleIdentity({**config(),extra:{}})
   with self.assertRaises(Denied):GoogleIdentity(config()).token('https://other.invalid')
if __name__=='__main__':unittest.main(verbosity=2)
