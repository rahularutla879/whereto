"""Offline manifest threat probes; no provider, runtime or paid-ledger changes."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from scripts import task52_version_review as v

H='52b-historical-evaluator-b04'
R='52b-runtime-legacy-b04'


class VersionReviewTests(TestCase):
    def test_historical_snapshots_survive_new_runtime_without_false_current_equality(self):
        for name,role in [(H,'historical_evaluator'),(R,'runtime_legacy_foundation')]:
            result=v.verify(name,role)
            self.assertTrue(result['snapshotVerified'])
            self.assertFalse(result['dispatchAuthorized'])
            with self.assertRaises(v.VersionError):v.verify(name,role,working=True)

    def test_unknown_missing_role_and_historical_runtime_confusion_fail(self):
        for name,role in [('missing','historical_evaluator'),(None,'historical_evaluator'),
                          (H,'runtime_legacy_foundation'),(R,'historical_evaluator'),(H,None)]:
            with self.assertRaises(v.VersionError):v.identity(name,role)

    def test_altered_or_missing_manifest_hash_cannot_self_assert_authority(self):
        data=json.loads(v.MANIFEST.read_text())
        with TemporaryDirectory() as tmp:
            file=Path(tmp)/'manifest.json'
            for edit in ('pin','missing','tree','root','format'):
                changed=deepcopy(data)
                entry=changed['identities'][H]
                if edit=='pin':entry['originalSixPins']['backend/journey.py']='0'*64
                if edit=='missing':entry['originalSixPins'].pop('backend/journey.py')
                if edit=='tree':entry['gitTree']='0'*40
                if edit=='root':entry['implementationRootSHA256']='0'*64
                if edit=='format':changed['format']='unknown'
                file.write_text(json.dumps(changed))
                with patch.object(v,'MANIFEST',file),self.assertRaises(v.VersionError):
                    v.verify(H,'historical_evaluator')

    def test_missing_manifest_never_falls_back(self):
        with TemporaryDirectory() as tmp:
            with patch.object(v,'MANIFEST',Path(tmp)/'absent.json'),self.assertRaises(v.VersionError):
                v.verify(H,'historical_evaluator')

    def test_missing_git_snapshot_never_falls_back_to_current_tree(self):
        with patch.object(v,'git',side_effect=v.VersionError()),self.assertRaises(v.VersionError):
            v.verify(H,'historical_evaluator')

    def test_working_source_changes_do_not_pass_as_historical_equality(self):
        real=Path.read_bytes
        def changed(path):
            data=real(path)
            return data+b'\n# synthetic mutation' if str(path).endswith('backend/journey.py') else data
        # Snapshot-only verification deliberately remains valid; current-tree equality must fail.
        from scripts import task52_phase_b2_identity as current
        self.assertTrue(current.verify()['verified'])
        with patch.object(Path,'read_bytes',changed):
            self.assertTrue(v.verify(H,'historical_evaluator')['snapshotVerified'])
            with self.assertRaises(v.VersionError):current.verify()

    def test_replay_has_new_identity_preserves_original_and_defaults_unreviewed(self):
        original={'operationId':'synthetic-1','evaluator':'recorded-old-label',
                  'responseHash':'a'*64,'configurationHash':'b'*64,'outcome':'historical_rejection'}
        before=deepcopy(original)
        replay=v.replay_descriptor(original,expected_original_hash=v.digest(original),target=R)
        self.assertEqual(original,before)
        self.assertEqual(replay['original'],before)
        self.assertEqual(replay['replayDisposition'],'unreviewed')
        self.assertFalse(replay['paidAttemptAuthorized'])
        self.assertFalse(replay['historicalOutcomeRewritten'])
        replay['original']['outcome']='edited copy'
        self.assertEqual(original,before)
        with self.assertRaises(v.VersionError):
            v.replay_descriptor(original,expected_original_hash=v.digest(original),target=H)
        with self.assertRaises(v.VersionError):
            v.replay_descriptor({**original,'outcome':'changed'},expected_original_hash=v.digest(original),target=R)

    def test_missing_original_evidence_or_same_label_replay_refused(self):
        for original in ({'operationId':'synthetic'},
                         {'operationId':'synthetic','evaluator':R,'responseHash':'a','configurationHash':'b'}):
            with self.assertRaises(v.VersionError):
                v.replay_descriptor(original,expected_original_hash=v.digest(original),target=R)


class AdmissionReviewThreatTests(TestCase):
    def setUp(self):
        # Reuse fake setup without inheriting/duplicating the original 22 tests.
        from backend import test_planning_admission as existing
        self.fixture=existing.PlanningAdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_restart_cannot_recover_or_copy_old_process_authority(self):
        from backend.planning_admission import AdmissionRegistry,AdmissionError
        f=self.fixture;out=f.issue();candidate=f.candidate(out)
        restarted=AdmissionRegistry(clock=lambda:0.)
        from unittest.mock import Mock
        work=Mock()
        with self.assertRaises(AdmissionError):
            restarted.run(out.receipt,restarted.new_scope(),1,candidate,work)
        work.assert_not_called()
        self.assertEqual(f.budget._requests,0)

    def test_budget_and_terminal_identity_mutation_never_authorize_work(self):
        from backend import test_planning_admission as existing
        from backend.planning_admission import AdmissionError
        from backend.journey import Endpoint
        f=self.fixture;out=f.issue();candidate=f.candidate(out)
        with self.assertRaises(AdmissionError):
            f.registry.run(out.receipt,f.scope,1,candidate.model_copy(update={'budget':1}),f.attempt)
        text,data,_=existing.CASES[3]
        out=f.issue(revision=2,value=existing.InterpretationInput(text=text),data=data)
        result=out.disposition.result.model_copy(deep=True)
        result.interpretation.journey.endpoint=Endpoint(kind='origin',source='invented return')
        payload={'text':text,'result':result,'preferences':out.disposition.input.preferences}
        with self.assertRaises(AdmissionError):f.registry.run(out.receipt,f.scope,2,payload,lambda _:self.fail('No work'))
        self.assertEqual(f.budget._requests,0)
