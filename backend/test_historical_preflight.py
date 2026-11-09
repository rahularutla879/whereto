"""B2 preflight fail-closed regressions; no retained-code execution."""
import importlib.metadata
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import task52_historical_preflight as gate
from scripts import task52_version_review as history


class HistoricalPreflightTests(unittest.TestCase):
    def test_retained_sources_are_verified_but_matching_versions_do_not_unlock_execution(self):
        result=gate.audit()
        self.assertTrue(result['historicalIdentity']['snapshotVerified'])
        self.assertTrue(result['allPinnedVersionsMatch'])
        self.assertTrue(result['pythonVersionMatchesB1'])
        self.assertFalse(result['historicalArtifactEnvironmentVerified'])
        self.assertFalse(result['historicalCodeExecuted'])
        self.assertFalse(result['runtimeExtractionPermitted'])
        self.assertEqual(result['providerRequests'],0)
        self.assertEqual(result['approvedExecutionEnvironmentCount'],0)
        with self.assertRaises(gate.HistoricalReplayBlocked):gate.require_execution_ready()

    def test_missing_wrong_and_unpinned_dependencies_are_not_silently_substituted(self):
        self.assertEqual(gate.requirement_pins(b'psycopg[binary]==3.3.3\n'),{'psycopg':'3.3.3'})
        for raw in (b'pydantic>=2\n',b'https://example.invalid/a.whl\n',
                    b'pydantic==2\npydantic==2\n',b'-r requirements.txt\n'):
            with self.assertRaises(history.VersionError):gate.requirement_pins(raw)
        def missing(_):raise importlib.metadata.PackageNotFoundError('synthetic')
        self.assertFalse(gate.version_comparison({'pydantic':'2'},lambda _:'3')[0]['matches'])
        self.assertFalse(gate.version_comparison({'pydantic':'2'},missing)[0]['matches'])

    def test_missing_or_changed_historical_source_fails_before_dependency_audit(self):
        with patch.object(history,'verify',side_effect=history.VersionError()), \
             patch.object(gate.importlib.metadata,'version') as installed:
            with self.assertRaises(history.VersionError):gate.audit()
            installed.assert_not_called()

    def test_changed_b1_manifest_cannot_claim_artifact_approval(self):
        original=json.loads(gate.B1_MANIFEST.read_text())
        original['historicalArtifactEnvironmentVerified']=True
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'manifest.json';p.write_text(json.dumps(original))
            with patch.object(gate,'B1_MANIFEST',p),self.assertRaises(history.VersionError):gate.audit()

    def test_no_force_argument_or_caller_assertion_can_unlock_gate(self):
        with self.assertRaises(TypeError):gate.require_execution_ready(force=True)
        with patch.object(gate,'audit',return_value={'historicalArtifactEnvironmentVerified':True}):
            with self.assertRaises(gate.HistoricalReplayBlocked):gate.require_execution_ready()

    def test_preflight_does_not_load_credential_or_journal_modules(self):
        # This audit only needs metadata and Git reads; importing a live adapter,
        # reading a key/config or opening the journal would violate this guard.
        read=Path.read_bytes
        allowed=gate.B1_MANIFEST.resolve(),history.MANIFEST.resolve()
        def limited(path):
            if path.resolve() not in allowed:self.fail('Unexpected file read in preflight')
            return read(path)
        with patch.object(Path,'read_bytes',limited),patch('sqlite3.connect',side_effect=AssertionError('No journal')):
            self.assertFalse(gate.audit()['paidJournalAccessedByThisTool'])
