"""Offline projection contracts. No Docker, secret lookup or provider requests."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import ast,json
from deployment.prepare_real_services import prepare,sha,ROOT,ROLES

class ProjectionTests(TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=TemporaryDirectory();cls.target=Path(cls.tmp.name)/'roles';cls.cohort=prepare(cls.target)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_exact_real_profile_not_release_authority(self):
  self.assertEqual(self.cohort['profile'],'52-real-native-six-role-v4');self.assertTrue(self.cohort['realProviderTransport']);self.assertFalse(self.cohort['releaseEligible'])
 def test_every_role_exact_source(self):
  for role in ROLES:
   own=json.loads((self.target/role/'private-role.json').read_bytes())
   self.assertIn('private_runtime/entry.py',own['files'])
   for name in own['files']:self.assertEqual(sha((self.target/role/name).read_bytes()),self.cohort['outputs'][role+'/'+name])
 def test_original_proof_is_not_python_module(self):
  manifest=json.loads((ROOT/'private_runtime/real_application/sources.json').read_bytes())
  for name,h in {**manifest['inputs'],**manifest['backendOutputs']}.items():
   p=self.target/'counter/source-proof'/(name+('.txt' if name.endswith('.py') else ''))
   self.assertEqual(sha(p.read_bytes()),h)
  self.assertFalse(list((self.target/'counter/source-proof').rglob('*.py')))
 def test_no_fixture_or_synthetic_graph_runtime(self):
  for name in self.cohort['outputs']:
   if '/source-proof/' in name:continue
   self.assertFalse(any(x.startswith(('test_','run_')) or x in ('testing_clock','bootstrap','simulation','journey_fixtures','real_fixtures') for x in Path(name).parts))
  root=self.target/'counter'
  for name in ('experiments/hosted_identity/tokens.py','experiments/hosted_identity/auth.py'):
   tree=ast.parse((root/name).read_text());classes={n.name for n in ast.walk(tree) if isinstance(n,ast.ClassDef)}
   self.assertFalse(classes&{'OfflineKeys','Auth','Client'})
  self.assertNotIn('class Session',(root/'experiments/shared_state/native_sessions.py').read_text())
 def test_exact_existing_dependencies_and_bases(self):
  self.assertEqual(sha((self.target/'requirements.lock').read_bytes()),self.cohort['dependencyLockSHA256'])
  self.assertEqual((self.target/'requirements.lock').read_bytes(),(self.target/'authority-requirements.lock').read_bytes())
  for value in self.cohort['baseImages']['images'].values():self.assertIn('@sha256:',value['reference'])
 def test_loaded_code_and_raw_sources_are_independent(self):
  code=(self.target/'factory/private_runtime/real_application/identity.py').read_text()
  self.assertIn('verify_image();verify()',code);self.assertIn("name+'.txt'",code)
  self.assertIn("PROFILE='52-real-native-six-role-v4'",(self.target/'factory/private_runtime/image_build.py').read_text())
 def test_cannot_overwrite_context(self):
  with self.assertRaises(ValueError):prepare(self.target)
