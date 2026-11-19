"""Offline real-image compiler tests; registry receipts below are fictional."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import json
from deployment import cloud_run_real as c
from deployment import test_cloud_run as old_tests

class RealCloudRunTests(TestCase):
 def setUp(self):self.config=c.original.read(c.ROOT/'deployment/cloud-run/staging.example.json')
 def filled(self):
  fixture=old_tests.CloudRunTests();fixture.setUp();return fixture.filled()
 def test_exact_real_manifest(self):
  m=c.pins();self.assertTrue(m['realProviderTransport']);self.assertTrue(m['containerAcceptancePassed']);self.assertFalse(m['releaseEligible']);self.assertEqual(set(m['candidateForReview']),set(c.original.ROLES))
 def test_empty_enrollment_cannot_deploy(self):
  p=c.compile_plan(self.config);self.assertFalse(p['provisioningAuthorized']);self.assertFalse(p['releaseEligible']);self.assertTrue(p['realDemoSupportedByCurrentImages'])
  self.assertTrue(all(v['commandForReviewOnly'] is None for v in p['roles'].values()));self.assertTrue(any('frontend' in s and 'trust' in s for s in p['blockers']))
 def test_counter_can_only_invoke_existing_dispatcher_boundary(self):
  p=c.compile_plan(self.config);grants=p['iamCommandsForReviewOnly'];member='--member=serviceAccount:'+c.original.sa('counter')
  selected=[g for g in grants if member in g and 'roles/run.invoker' in ' '.join(g)]
  self.assertEqual(len(selected),1);self.assertIn('whereto-dispatcher',selected[0])
 def test_credential_mounts_remain_role_scoped(self):
  p=c.compile_plan(self.config)
  for role,v in p['roles'].items():self.assertEqual('/run/secrets/whereto-openai-key.json' in v['mounts'],role=='dispatcher')
  self.assertEqual(p['roles']['counter']['sqlPurposes'],{'database':'counter','witness':'witness-counter'})
 def test_unsigned_approval_hashes_are_not_receipts_or_authority(self):
  config=self.filled();p=c.compile_plan(config)
  self.assertTrue(all(v['commandForReviewOnly']is None for v in p['roles'].values()));self.assertFalse(p['providerBindings']['enabled']);self.assertFalse(p['imageContentReview']['securityAccepted'])
 def test_parent_source_mutation_refuses(self):
  with patch.object(c,'PARENT_SHA256','0'*64):
   with self.assertRaises(ValueError):c.reviewed_parent()
 def fixture(self,role):
  raw=(c.CANDIDATE/'config'/f'{role}.json').read_bytes();doc=json.loads(raw);config='sha256:'+c.original.sha(raw)
  manifest=json.dumps(dict(schemaVersion=2,mediaType='application/vnd.oci.image.manifest.v1+json',config=dict(digest=config,size=len(raw),mediaType='application/vnd.oci.image.config.v1+json'),layers=[dict(digest=d,size=1,mediaType='application/vnd.oci.image.layer.v1.tar') for d in doc['rootfs']['diff_ids']]),sort_keys=True).encode()
  return manifest,raw
 def test_actual_configs_prove_all_six_content_identities_offline(self):
  for role in c.original.ROLES:
   manifest,raw=self.fixture(role);r=c.publication_receipt(role,manifest,c.original.sha(manifest),raw)
   self.assertEqual(r['localConfigDigest'],c.pins()['configDigests'][role]);self.assertEqual(r['localImage'],c.pins()['candidateForReview'][role])
 def test_changed_config_or_manifest_refuses(self):
  m,r=self.fixture('counter')
  for manifest,raw,digest in ((m,r+b' ',c.original.sha(m)),(m+b' ',r,c.original.sha(m)),(m,r,'0'*64)):
   with self.assertRaises(c.original.Refused):c.publication_receipt('counter',manifest,digest,raw)
 def test_cross_role_config_refuses(self):
  m,r=self.fixture('counter')
  with self.assertRaises(c.original.Refused):c.publication_receipt('dispatcher',m,c.original.sha(m),r)
 def test_wrong_registry_digest_cannot_emit_deploy_command(self):
  conf=self.filled();m,r=self.fixture('counter')
  with self.assertRaises(c.original.Refused):c.compile_plan(conf,{'counter':(m,r)})
 def test_fixed_targets_no_extra_roles_or_public_backend(self):
  p=c.compile_plan(self.config);self.assertEqual(set(p['roles']),set(c.original.ROLES));self.assertFalse(p['providerBindings']['enabled'])
  changed=deepcopy(self.config);changed['project']='other-project'
  with self.assertRaises(c.original.Refused):c.compile_plan(changed)
 def test_publication_uses_local_images_not_config_or_guessed_registry_digests(self):
  p=c.compile_plan(self.config);images=c.pins()
  for item in p['publicationForReviewOnly']:
   self.assertEqual(item['commands'][0][2],images['candidateForReview'][item['role']]);self.assertEqual(item['localConfigDigest'],images['configDigests'][item['role']])

 def test_duplicate_or_malformed_oci_json_refuses(self):
  for raw in (b'{"schemaVersion":2,"schemaVersion":1}',b'{',b'x'*2000001):
   with self.assertRaises(c.original.Refused):c.decode(raw)
 def test_missing_layers_refuses(self):
  m,r=self.fixture('counter');v=json.loads(m);v['layers']=[];m=json.dumps(v).encode()
  with self.assertRaises(c.original.Refused):c.publication_receipt('counter',m,c.original.sha(m),r)
