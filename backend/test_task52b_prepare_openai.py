"""Offline artifact checks, not provider qualification or reviewer signoff."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import task52b_prepare_openai as prep
from scripts import cloud_model52 as original
from scripts import task52_q4c_protocol as accounting
from backend.ai import Interpretation


class PreparationTests(unittest.TestCase):
    def test_five_exact_proposed_slots_and_payloads(self):
        records = prep.prepare()
        self.assertEqual(tuple((r['slot'][1], r['slot'][2]) for r in records), prep.SLOTS)
        self.assertEqual(len({r['requestSHA256'] for r in records}), 5)
        self.assertTrue(all(not r['dispatchAuthorized'] for r in records))

    def test_committed_bytes_are_canonical_and_complete(self):
        self.assertEqual(prep.verify_artifacts()['slotsVerified'], 5)
        self.assertFalse(prep.verify_artifacts()['readinessVerified'])
        for r in prep.prepare():
            self.assertEqual(prep.canonical(json.loads(prep.canonical(r['request']))),
                             prep.canonical(r['request']))

    def test_all_19_examples_unchanged_and_structurally_valid(self):
        reviewed = json.loads((prep.ROOT / next(iter(prep.ANCHORS))).read_text())
        for record in prep.prepare():
            messages = record['request']['input']
            self.assertEqual(len(messages), 40)
            self.assertEqual(messages[:-1], reviewed['frozenRequestTemplate']['input'][:-1])
            for index in range(2, 39, 2):
                value = json.loads(messages[index]['content'])
                Interpretation.model_validate(value)
                # Frozen teaching examples are compact, not complete provider
                # responses. Do not add defaults to the frozen prompt.
                self.assertEqual(original.missing_properties(value, original.schema(), unknown=True), [])

    def test_exact_model_and_controls(self):
        for r in prep.prepare():
            b = r['request']
            self.assertEqual(set(b), {'model', 'input', 'temperature', 'reasoning',
                                     'service_tier', 'max_output_tokens', 'store', 'text'})
            self.assertEqual((b['model'], b['temperature'], b['reasoning'],
                              b['service_tier'], b['max_output_tokens'], b['store']),
                             ('gpt-6-luna', 0, {'effort': 'none'}, 'default', 2000, False))
            self.assertTrue(b['text']['format']['strict'])
            self.assertEqual(prep.digest(b['text']['format']['schema']),
                             'c272ae5a066c43bd76f65932a608303472df27b3aa400db936e3728849cb0766')

    def test_count_projection_includes_full_schema_and_reasoning(self):
        for r in prep.prepare():
            self.assertEqual(set(r['countRequest']), {'model', 'input', 'text', 'reasoning'})
            for key in r['countRequest']:
                self.assertEqual(r['countRequest'][key], r['request'][key])
            self.assertIsNone(r['verifiedInputTokens'])

    def test_changed_frozen_artifacts_refuse(self):
        for changed in prep.ANCHORS:
            with self.subTest(path=changed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for path in prep.ANCHORS:
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((prep.ROOT / path).read_bytes())
                (root / changed).write_bytes((root / changed).read_bytes() + b' ')
                with self.assertRaisesRegex(ValueError, 'Frozen artifact identity'):
                    prep.prepare(root)

    def test_changed_prepared_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(prep, 'ARTIFACTS', Path(directory)):
                for r in prep.prepare():
                    for key, value in [('requestFile', 'request'), ('countFile', 'countRequest')]:
                        (prep.ARTIFACTS / r[key]).write_bytes(prep.canonical(r[value]))
                path = prep.ARTIFACTS / prep.prepare()[0]['requestFile']
                path.write_bytes(path.read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'Prepared file differs'):
                    prep.verify_artifacts()

    def test_counts_unknown_malformed_or_over_cap_refuse(self):
        # These are fictional arithmetic inputs, never provider count evidence.
        for count in (None, True, False, 0, -1, 9953, 12000, 1.0, '100'):
            with self.subTest(count=count), self.assertRaises(ValueError):
                prep.input_bound(count, request_hash='x', expected_hash='x')
        self.assertEqual(prep.input_bound(9952, request_hash='x', expected_hash='x'), 12000)
        with self.assertRaises(ValueError):
            prep.input_bound(1, request_hash='altered', expected_hash='x')

    def test_frozen_accounting_exact_boundaries(self):
        # Reuse frozen Q4C arithmetic, not a new ledger or financial grant.
        accounting.admission(593, 197, 11997500000, 4, 10000000)
        for args in [(594, 0, 0, 0, 0), (0, 198, 0, 0, 0),
                     (0, 0, 11997500001, 0, 0), (0, 0, 0, 5, 0),
                     (0, 0, 0, 0, 10000001), (True, 0, 0, 0, 0),
                     (0, 0, -1, 0, 0)]:
            with self.subTest(args=args), self.assertRaises(accounting.auth.Denied):
                accounting.admission(*args)

    def test_decoder_preserves_original_synthetic_response(self):
        response = {'status': 'completed', 'error': None,
                    'output': [{'content': [{'type': 'output_text', 'text': '{"raw":true}'}]}],
                    'usage': {'input_tokens': 1, 'output_tokens': 2}}
        before = deepcopy(response)
        self.assertEqual(original.Adapter('openai', None).decode(response),
                         ('{"raw":true}', (1, 2), 'complete'))
        self.assertEqual(response, before)

    def test_provider_errors_incomplete_and_refusal_not_success(self):
        adapter = original.Adapter('openai', None)
        for response, status in [({'error': {'code': 'fictional'}}, 'provider_error'),
                                 ({'status': 'incomplete'}, 'incomplete'),
                                 ({'output': [{'content': [{'type': 'refusal'}]}]}, 'refusal')]:
            self.assertEqual(adapter.decode(response)[2], status)

    def test_required_and_unknown_response_fields_remain_enforced(self):
        # The strict response contract is distinct from compact teaching examples.
        self.assertIn('$.activities', original.missing_properties({}, original.schema()))
        self.assertEqual(original.missing_properties({'invented': 1},
                         original.schema(), unknown=True), ['$.invented'])

    def test_no_network_or_authority_created(self):
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            self.assertEqual(prep.verify_artifacts()['dispatchAuthorized'], False)
        self.assertFalse(hasattr(prep, 'live_dispatch'))


if __name__ == '__main__':
    unittest.main()
