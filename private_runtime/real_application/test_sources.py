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
