"""Pinned RPC source checks; no storage, credentials or provider access."""
from pathlib import Path
from unittest.mock import patch
import unittest
from experiments.shared_state.contracts import Denied
from .identity import ROOT,source_bytes

class Tests(unittest.TestCase):
    def test_exact_parent_source_bytes(self):
        name='experiments/service_isolation/factory.py'
        self.assertEqual(source_bytes(name),(ROOT/name).read_bytes())
    def test_changed_input_refuses_before_projection(self):
        original=Path.read_bytes;target=ROOT/'experiments/service_isolation/factory.py'
        def changed(path):return original(path)+b'\n# substituted code' if path==target else original(path)
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(Denied):source_bytes('experiments/service_isolation/factory.py')
    def test_unenrolled_or_outside_path_refuses(self):
        for value in ('../unenrolled-input','/tmp/unenrolled-input','backend/test_real_planning.py'):
            with self.assertRaises(Denied):source_bytes(value)

class ClosedEntryTests(unittest.TestCase):
    def test_ordinary_image_cannot_select_real_startup(self):
        import types,sys
        from .entry import main
        fake=types.ModuleType('private_runtime.image_build');fake.ROLE='counter';fake.PROFILE='unapproved'
        with patch.dict(sys.modules,{'private_runtime.image_build':fake}),patch('os.getuid',return_value=10001),patch.dict('os.environ',{'K_SERVICE':'fictional-local-service'},clear=True),patch('os.open',side_effect=AssertionError('No secret access')):
            with self.assertRaises(Denied):main()
    def test_environment_credential_or_tls_override_refuses_before_secret(self):
        from .entry import main
        for name in ('OPENAI_API_KEY','GOOGLE_APPLICATION_CREDENTIALS','SSL_CERT_FILE'):
            with patch('os.getuid',return_value=10001),patch.dict('os.environ',{name:'FICTIONAL-OVERRIDE'},clear=True),patch('os.open',side_effect=AssertionError('No secret access')):
                with self.assertRaises(Denied):main()
    def test_counter_cannot_enroll_provider_credential(self):
        from .entry import credential
        with patch('os.open',side_effect=AssertionError('No secret access')):
            with self.assertRaises(Denied):credential({'service':'counter'})
