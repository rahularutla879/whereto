"""Original source archive + fictional immutable successful GET binding tests."""
from datetime import datetime,timezone
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from backend.task52b_count_tls_fixture import successful_get_fixture
from scripts import task52b_count_only as c
from scripts import task52b_get_evidence as proof


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.base=self.root/'private';self.base.mkdir(mode=0o700);(self.root/'docs').mkdir()
        self.enroll=self.base/'enrollment.json';c.private_create(self.enroll,{'fixtureOnly':True})
        self.identity=c.digest(self.enroll.read_bytes());self.now=datetime(2026,11,18,12,tzinfo=timezone.utc)
        self.path,_=successful_get_fixture(self.root,self.base,self.identity,self.now.isoformat())
        for p in (patch.object(c.e,'BASE',self.base),patch.object(c.e,'PRIVATE_ENROLLMENT',self.enroll)):
            p.start();self.addCleanup(p.stop)
    def validate(self):return proof.verify(self.path,self.now,c.fresh)
    def rewrite(self,name,change):
        b=json.loads(self.path.read_bytes());p=self.base/b['operation']/name;value=json.loads(p.read_bytes());change(value);p.write_text(json.dumps(value));b['privateFilesSHA256'][name]=c.digest(p.read_bytes());self.path.write_text(json.dumps(b))
    def test_original_archive_and_successful_consumed_chain(self):
        got=self.validate();self.assertEqual(got['model'],c.q.MODEL);self.assertEqual(got['expiresAt'],'2026-11-19T00:00:00+00:00')
        self.assertFalse(c.AUTHORIZATION.exists());self.assertFalse(c.STATE.exists())
    def test_exact_expiry_refuses_without_renewal(self):
        self.now=datetime(2026,11,19,tzinfo=timezone.utc)
        with self.assertRaisesRegex(c.q.Refused,'prior_evidence_stale'):self.validate()
    def test_original_source_or_manifest_substitution_refuses(self):
        b=json.loads(self.path.read_bytes());b['sourceBuildSHA256']='0'*64;self.path.write_text(json.dumps(b))
        with self.assertRaisesRegex(c.q.Refused,'prior_get_original_build'):self.validate()
    def test_missing_or_changed_immutable_record_refuses(self):
        b=json.loads(self.path.read_bytes());p=self.base/b['operation']/'consumed.json';p.write_text('{}')
        with self.assertRaisesRegex(c.q.Refused,'prior_scope_integrity'):self.validate()
    def test_cross_project_or_inference_capability_refuses_even_if_rehashed(self):
        self.rewrite('scope.json',lambda s:s.update(project='OTHER',inferenceMaximum=1))
        with self.assertRaisesRegex(c.q.Refused,'prior_get_scope_binding'):self.validate()
    def test_substituted_credential_or_loaded_wire_refuses(self):
        c.e.PRIVATE_ENROLLMENT.write_text('{"fixtureOnly":"different"}')
        with self.assertRaisesRegex(c.q.Refused,'prior_get_authority_binding'):self.validate()
    def test_runtime_attestation_refuses(self):
        self.rewrite('runtime.json',lambda s:s.update(loadedWireIdentitySHA256='0'*64))
        with self.assertRaisesRegex(c.q.Refused,'prior_get_supervision'):self.validate()
    def test_extended_record_expiry_refuses_even_if_rehashed(self):
        self.rewrite('validated.json',lambda s:s.update(expiresAt='2026-11-20T00:00:00+00:00'))
        with self.assertRaisesRegex(c.q.Refused,'prior_get_validation'):self.validate()
    def test_changed_authorization_and_extra_file_refuse(self):
        b=json.loads(self.path.read_bytes());p=self.base/(b['operation']+'.send-authorization.json');p.write_text('{}')
        with self.assertRaisesRegex(c.q.Refused,'prior_get_authorization_integrity'):self.validate()
    def test_count_selector_model_and_payload_are_fixed(self):
        b=json.loads(self.path.read_bytes());b['model']='OTHER';self.path.write_text(json.dumps(b))
        with self.assertRaisesRegex(c.q.Refused,'prior_get_selector_binding'):self.validate()
    def test_source_archive_is_local_only_and_path_bounded(self):
        with self.assertRaisesRegex(c.q.Refused,'prior_get_archive_path'):proof.blobs('HEAD',['../credential'])
