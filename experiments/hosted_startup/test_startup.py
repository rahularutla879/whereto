"""Startup refusals, never production activation or readiness from config flags."""
import unittest,subprocess,os,json
from pathlib import Path
from unittest.mock import patch
from deployment.private_startup import main,blockers
class StartupTests(unittest.TestCase):
 def test_private_profile_is_unconditionally_nonlaunchable(self):
  self.assertGreaterEqual(len(blockers()),6);self.assertEqual(main(),78)
 def test_environment_booleans_cannot_enable_it(self):
  with patch.dict(os.environ,{'WHERETO_ENV':'production','K_SERVICE':'fixture','WHERETO_SHARED_READY':'1','WHERETO_FINANCIAL_READY':'1'}):self.assertEqual(main(),78)
 def test_original_backend_production_guard_is_intact(self):
  r=subprocess.run([os.sys.executable,'-c','import backend.main'],capture_output=True,env={**os.environ,'PYTHONPATH':str(Path.cwd()),'WHERETO_ENV':'production','K_SERVICE':'fixture'})
  self.assertNotEqual(r.returncode,0);self.assertIn(b'Production requires verified shared',r.stderr)
 def test_caller_ready_fields_are_not_credentials(self):
  d=json.loads(Path('deployment/private-startup-v1.json').read_text());self.assertFalse(d['launchable']);self.assertFalse(d['providerDispatchEnabled']);self.assertNotIn('force',d)
 def test_production_payload_still_excludes_fixture_modules(self):
  d=json.loads(Path('deployment/backend-files.json').read_text());self.assertFalse(any('experiments/' in f for f in d['files']))
if __name__=='__main__':unittest.main(verbosity=2)
