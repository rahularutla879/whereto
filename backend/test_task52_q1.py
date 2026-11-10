"""Q1 review contract tests. No app/runtime selection, live transport or writes."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts import task52_q1 as q


class QualificationContractTests(unittest.TestCase):
    def test_manifest_and_all_66_field_records(self):
        m=q.verify();self.assertFalse(m['paidDispatchAuthorized']);self.assertFalse(m['planningAuthorized'])
        r=json.loads((q.ROOT/'docs/task52-q1-rubric-v1.json').read_text())
        from collections import Counter
        self.assertEqual(Counter(c['referenceKind'] for c in r['cases']),{'journey':25,'ordinary':26,'extension':15})
        self.assertEqual(len(r['dimensions']),24)
        self.assertEqual(sum(f['applicability']=='awaiting_review' for c in r['cases'] for f in c['fields'].values()),6)
        self.assertEqual(sum(bool(c['gaps']) for c in r['cases']),7)
        self.assertTrue(all(not c['independentReviewComplete'] for c in r['cases']))
        for c in r['cases']:
            for field in c['fields'].values():
                self.assertEqual(field['independentReview'],'pending')
                if field['applicability']=='not_applicable':self.assertIsNone(field['expected'])

    def test_no_independent_approval_prefilled(self):
        w=json.loads((q.ROOT/'docs/task52-q1-independent-review-v1.json').read_text())
        self.assertEqual(len(w['cases']),66)
        self.assertIsNone(w['independentOfRubricAuthor'])
        self.assertTrue(all(c['approvedForQualification'] is None for c in w['cases']))
        self.assertTrue(all(v is None for c in w['cases'] for v in c['fieldJudgments'].values()))

    def test_unknown_identity_and_changed_manifest_fail(self):
        with self.assertRaises(ValueError):q.verify(identity='paid-or-production')
        with patch.object(q,'MANIFEST_SHA','0'*64):
            with self.assertRaises(ValueError):q.verify()

    def test_changed_source_or_corpus_fails_closed(self):
        real=Path.read_bytes
        for name in ('docs/task52-q1-rubric-v1.json','docs/task52-evaluation-corpus.json','scripts/cloud_model52_ordering_v4.py'):
            def read(path):return real(path)+b' ' if path==q.ROOT/name else real(path)
            with self.subTest(path=name),patch.object(Path,'read_bytes',read):
                with self.assertRaises(ValueError):q.verify()

    def test_readonly_network_and_journal_boundary(self):
        import socket,sqlite3,requests
        with q.offline():
            with self.assertRaises(AssertionError):requests.get('https://example.invalid')
            with socket.socket() as sock:
                with self.assertRaises(AssertionError):sock.connect(('127.0.0.1',1))
            with self.assertRaises(ValueError):sqlite3.connect(q.ROOT/'backend/.local/task52-model-evaluation/journal.sqlite')
            with self.assertRaises(ValueError):sqlite3.connect('file:/tmp/not-the-paid-journal?mode=ro',uri=True)
            with self.assertRaises(ValueError):sqlite3.connect(f'file:{q.ROOT}/backend/.local/task52-model-evaluation/journal.sqlite?fake=mode=ro',uri=True)

    def test_seven_replay_both_failures_and_original_evidence(self):
        before=q.private_hashes();r=q.replay()
        self.assertEqual(r['counts'],{'responses':7,'structuredValid':7,'agentRubricCorrect':5,'rawFailures':2,'legacyAccepted':6,'guardCandidateCompatible':5,'independentSignoffs':0})
        self.assertEqual(before,q.private_hashes());self.assertTrue(r['journal']['persistentHalt'])
        by={c['slot'][1]:c for c in r['results']}
        unsafe=by['extension-repeated']
        self.assertEqual(unsafe['legacy']['disposition'],'accepted_advanced_handoff')
        self.assertEqual(unsafe['proposedGuarded']['disposition'],'blocked_by_independent_ordering')
        self.assertEqual(unsafe['proposedGuarded']['unsupportedModelEdges'],[[0,1]])
        self.assertIn([1,2],unsafe['proposedGuarded']['provedRelationships'])
        self.assertEqual(by['journey-07']['proposedGuarded']['disposition'],'blocked_by_complete_legacy_validation')
        self.assertEqual(by['journey-01']['original']['originalClassification'],'provider_error')
        self.assertTrue(all(c['raw']['fullyCorrectIndependent'] is None for c in r['results']))
        saved=json.loads((q.ROOT/'docs/task52-q1-openai-replay-v1.json').read_text())
        self.assertEqual(r,saved)

    def test_reference_fields_not_reinterpreted_as_model_accuracy(self):
        r=json.loads((q.ROOT/'docs/task52-q1-rubric-v1.json').read_text())
        cases={c['id']:c for c in r['cases']}
        self.assertEqual(cases['extension-repeated']['fields']['mandatory_order']['expected']['requiredReachability'],[[1,2]])
        self.assertEqual(cases['extension-partial']['fields']['optional_activities']['applicability'],'not_applicable')
        self.assertEqual(cases['journey-06']['fields']['optional_activities']['expected'][0]['index'],1)
        self.assertEqual(cases['journey-12']['fields']['home_ambiguity']['expected']['homeEqualsOrigin'],False)
        self.assertEqual(cases['ordinary-multilingual']['fields']['dates_timezones']['applicability'],'awaiting_review')
        self.assertEqual(cases['ordinary-budget']['fields']['budget_transport']['applicability'],'awaiting_review')
        self.assertEqual(cases['extension-exclusive']['fields']['whole_trip_limit']['expected']['relation'],'under')
        self.assertEqual(cases['extension-zero']['fields']['budget_transport']['expected']['perPerson'],0)


if __name__=='__main__':unittest.main()
