"""Offline cryptographic adversarial cases; no real Google token or key retrieval."""
import json,time,unittest,copy
from pathlib import Path
from unittest.mock import patch
import jwt
from experiments.hosted_identity.tokens import Tokens,OfflineKeys,GoogleKeys,keyset,ISSUERS
from experiments.shared_state.contracts import Denied

class TokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.control=json.loads(Path('/tmp/hosted-control.json').read_text());cls.c=cls.control['configs']['factory']
    def setUp(self):self.t=Tokens(OfflineKeys(self.c['googleKeys']),offline=True)
    def make(self,kind='workload',**changes):
        now=int(time.time());v=dict(iss=ISSUERS[kind],aud=self.c['audiences']['factory'] if kind=='workload' else self.c['iapAudience'],sub='synthetic',iat=now,exp=now+(3600 if kind=='workload' else 600));v.update(changes)
        return jwt.encode(v,self.control['fixtureSigners'][kind],algorithm='RS256' if kind=='workload' else 'ES256',headers={'kid':'task52-offline-'+kind})
    def test_valid_distinct_issuer_audience_algorithm(self):
        for k in ('workload','iap'):self.assertEqual(self.t.verify(self.make(k),k,self.c['audiences']['factory'] if k=='workload' else self.c['iapAudience'])['sub'],'synthetic')
    def test_wrong_audience_issuer_and_missing_claims(self):
        for kwargs in ({'aud':'wrong'},{'iss':'https://evil.invalid'},{'aud':['wrong',self.c['audiences']['factory']]},{'sub':''}):
            with self.subTest(kwargs=kwargs),self.assertRaises(Denied):self.t.verify(self.make(**kwargs),'workload',self.c['audiences']['factory'])
        now=int(time.time());claims=dict(iss=ISSUERS['workload'],aud=self.c['audiences']['factory'],sub='synthetic',iat=now,exp=now+3600)
        for missing in ('iss','aud','sub','iat','exp'):
            value={k:v for k,v in claims.items() if k!=missing};token=jwt.encode(value,self.control['fixtureSigners']['workload'],algorithm='RS256',headers={'kid':'task52-offline-workload'})
            with self.subTest(missing=missing),self.assertRaises(Denied):self.t.verify(token,'workload',self.c['audiences']['factory'])
    def test_expired_future_bad_types_and_lifetime(self):
        now=int(time.time())
        for kwargs in ({'iat':now-3700,'exp':now-1},{'iat':now+120,'exp':now+3600},{'iat':True},{'exp':'bad'},{'exp':now+4000},{'iat':now+3,'exp':now+2}):
            with self.subTest(kwargs=kwargs),self.assertRaises(Denied):self.t.verify(self.make(**kwargs),'workload',self.c['audiences']['factory'])
    def test_signature_kid_algorithm_and_cross_token_confusion(self):
        from experiments.service_isolation.auth import unb64,b64
        good=self.make();h,p,s=good.split('.');a=bytearray(unb64(s));a[0]^=1
        for bad in (h+'.'+p+'.'+b64(a),'invalid',self.make('iap')):
            with self.assertRaises(Denied):self.t.verify(bad,'workload',self.c['audiences']['factory'])
        token=jwt.encode({'iss':ISSUERS['workload']},self.control['fixtureSigners']['workload'],algorithm='RS256',headers={'kid':'unknown'})
        with self.assertRaises(Denied):self.t.verify(token,'workload',self.c['audiences']['factory'])
    def test_iap_expiry_scope_and_workload_not_user(self):
        now=int(time.time())
        for kw in ({'exp':now+700},{'aud':'/projects/0/global/backendServices/0'},{'iss':ISSUERS['workload']},{'iat':now+60,'exp':now+600}):
            with self.assertRaises(Denied):self.t.verify(self.make('iap',**kw),'iap',self.c['iapAudience'])
    def test_production_rejects_offline_key_objects_and_fixture_kids_before_network(self):
        with self.assertRaises(Denied):Tokens(OfflineKeys(self.c['googleKeys']))
        with patch('http.client.HTTPSConnection',side_effect=AssertionError('No identity endpoint contact')) as network:
            for kind in ('iap','workload'):
                with self.assertRaises(Denied):Tokens(GoogleKeys()).verify(self.make(kind),kind,self.c['iapAudience'] if kind=='iap' else self.c['audiences']['factory'])
            self.assertEqual(network.call_count,0)
    def test_hosted_constructor_rejects_fixture_enrollment(self):
        from experiments.hosted_identity.auth import HostedAuth
        with self.assertRaises(Denied):HostedAuth(self.c,None,None)
        c=copy.deepcopy(self.c);c.pop('googleKeys');c['identityEnvironment']='private-staging'
        h=HostedAuth(c,None,None)
        with patch('http.client.HTTPSConnection',side_effect=AssertionError('No real identity endpoint')) as network:
            with self.assertRaises(Denied):h.tokens.verify(self.make(),'workload',c['audiences']['factory'])
            self.assertEqual(network.call_count,0)
    def test_offline_keys_refuse_hosted_and_production_environments(self):
        import os
        for env in ({'K_SERVICE':'synthetic-hosted'},{'NODE_ENV':'production'},{'WHERETO_ENV':'production'}):
            with patch.dict(os.environ,env),self.assertRaises(Denied):OfflineKeys(self.c['googleKeys'])
    def test_jwks_duplicate_private_algorithm_and_fixture_rejection(self):
        original=self.c['googleKeys']['workload']
        for mutation in ('duplicate','private','algorithm','remote'):
            d=copy.deepcopy(original)
            if mutation=='duplicate':d['keys']*=2
            if mutation=='private':d['keys'][0]['d']='private'
            if mutation=='algorithm':d['keys'][0]['alg']='HS256'
            if mutation=='remote':d['keys'][0]['jku']='https://evil.invalid'
            with self.assertRaises(Denied):keyset(d,'workload',offline=True)
        with self.assertRaises(Denied):keyset(original,'workload')
    def test_jwks_cache_expiry_unknown_key_no_redirect_and_origin(self):
        # Transport mock solely exercises the dormant fixed-origin cache parser.
        public=copy.deepcopy(self.c['googleKeys']['workload']);public.pop('fixture');public['keys'][0]['kid']='unit-cache-key'
        class Response:
            status=200
            def read(self,n):return json.dumps(public).encode()
            def getheader(self,n,default=None):return 'max-age=1'
        class Connection:
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        with patch('http.client.HTTPSConnection',return_value=Connection()) as network:
            cache=GoogleKeys();cache.key('workload','unit-cache-key');cache.key('workload','unit-cache-key');self.assertEqual(network.call_count,1);self.assertEqual(network.call_args.args[0],'www.googleapis.com')
            with self.assertRaises(Denied):cache.key('workload','unknown')
            with patch('experiments.hosted_identity.tokens.time.monotonic',return_value=time.monotonic()+2):
                with self.assertRaises(Denied):cache.key('workload','unit-cache-key')
        with patch.object(Response,'status',302),patch('http.client.HTTPSConnection',return_value=Connection()):
            with self.assertRaises(Exception):GoogleKeys().key('workload','unit-cache-key')

if __name__=='__main__':unittest.main(verbosity=2)
