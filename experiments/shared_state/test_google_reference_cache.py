"""ID-only records through existing restricted SQL and encrypted Redis fixture."""
import unittest,os
from dataclasses import replace
from experiments.shared_state import test_application_grants as g
from experiments.shared_state.contracts import Denied
from backend.google_retention import ReferenceCache,GoogleReferences,references_from_search

@unittest.skipUnless(os.environ.get('SYNTHETIC_WITNESS_ADMIN_PASSWORD'),'disposable SQL/Redis fixture required')
class ReferenceTests(unittest.TestCase):
    def setUp(self):g.fixture();self.s=g.store();self.lease,_,_=g.maps(self.s);self.cache=ReferenceCache(self.s,self.lease)
    def test_encrypt_absolute_expiry_no_renewal_and_delete(self):
        record=references_from_search({'places':[{'id':'Fixture_A','displayName':{'text':'Excluded authored name'},'location':{'latitude':1,'longitude':2}}]})
        before=self.s.snapshot()['gross']
        with self.assertRaises(Denied):self.cache.put(GoogleReferences.model_construct(place_ids=({'name':'Excluded'},)))
        self.cache.put(record)
        raw=self.s.evidence.get(self.cache.path);self.assertNotIn(b'Fixture_A',raw);self.assertNotIn(b'Excluded authored name',raw)
        ttl=self.s.evidence.client.pttl(self.cache.path);self.assertGreater(ttl,0);self.assertLessEqual(ttl,600000)
        self.assertEqual(self.cache.get(),record)
        with self.assertRaises(Denied):self.cache.put(record)
        self.assertLessEqual(self.s.evidence.client.pttl(self.cache.path),ttl)
        self.cache.forget()
        with self.assertRaises(Denied):self.cache.get()
        self.assertEqual(self.s.snapshot()['gross'],before)
    def test_missing_corrupt_wrong_key_and_stale_source(self):
        with self.assertRaises(Denied):self.cache.get()
        self.cache.put(GoogleReferences(place_ids=('Fixture_A',)))
        stale=replace(self.lease,revision=self.lease.revision+1)
        with self.assertRaises(Denied):ReferenceCache(self.s,stale)
        from experiments.shared_state.redis_evidence import Keys
        original=self.s.evidence.keys;self.s.evidence.keys=Keys('wrong',{'wrong':b'z'*32})
        try:
            with self.assertRaises(Denied):self.cache.get()
        finally:self.s.evidence.keys=original
        raw=self.s.evidence.get(self.cache.path);self.s.evidence.client.set(self.cache.path,raw[:-3]+b'bad')
        with self.assertRaises(Denied):self.cache.get()
        self.cache.forget()
    def test_revocation_refuses_read_and_owned_cleanup_still_works(self):
        self.cache.put(GoogleReferences(place_ids=('Fixture_A',)))
        self.s.revoke(self.lease.session,self.lease.revision)
        with self.assertRaises(Denied):self.cache.get()
        self.cache.forget();self.assertIsNone(self.s.evidence.client.get(self.cache.path))
