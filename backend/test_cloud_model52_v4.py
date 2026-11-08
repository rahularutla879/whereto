"""Free-count fakes only; never opens the owner journal/credentials or network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import cloud_model52 as e
from scripts import cloud_model52_v4 as v
from scripts import cloud_model52_proposal as p


BASELINE = {'sha256': v.JOURNAL_SHA, 'rows': [], 'counts': {'openai': 4, 'google': 2, 'anthropic': 1}}


class V4ReadinessTests(unittest.TestCase):
    def test_new_identity_without_mutating_v3_examples_schema_limits(self):
        before = copy.deepcopy(e.metadata()); config = v.configuration()
        self.assertNotEqual(e.digest(config), e.digest(before))
        for key in before:
            if key not in ('promptHash', 'promptVersion'): self.assertEqual(config[key], before[key])
        self.assertEqual(p.messages('')[1:], e.messages('')[1:])
        self.assertEqual(len(e.compact_examples()[0]), 19)
        self.assertEqual(len(p.ADDITION.encode()), 370)
        self.assertEqual(config['schemaHash'], before['schemaHash'])
        self.assertEqual(e.metadata(), before)
        for provider in e.CANDIDATES:
            for case in e.corpus()['cases']:
                self.assertEqual(v.payload(case['id'], provider), p.payload(provider, case['text']))
        with self.assertRaises(e.AdmissionError): v.payload('private or uncontrolled input', 'openai')
        with patch.object(p, 'ADDITION', 'X' * 370):
            with self.assertRaisesRegex(e.AdmissionError, 'Exact reviewed'):
                v.configuration()

    def test_count_bodies_include_exact_system_examples_schema_settings(self):
        path, body = v.count_body('journey-04', 'openai'); full = v.payload('journey-04', 'openai')
        self.assertEqual(path, '/responses/input_tokens')
        self.assertEqual(body, {k: full[k] for k in ('model', 'input', 'text', 'reasoning')})
        path, body = v.count_body('journey-04', 'anthropic'); full = v.payload('journey-04', 'anthropic')
        self.assertEqual(body, {k: x for k, x in full.items() if k != 'max_tokens'})
        _, body = v.count_body('journey-04', 'google'); full = v.payload('journey-04', 'google')
        request = body['generateContentRequest']
        self.assertEqual(request['contents'][:-1], full['contents'])
        self.assertEqual(request['systemInstruction'], full['systemInstruction'])
        self.assertEqual(json.loads(request['contents'][-1]['parts'][0]['text']), e.wire_schema('google'))

    def test_inference_endpoints_and_methods_never_reach_transport(self):
        with patch.object(v.old, 'HTTP') as http:
            for provider in e.CANDIDATES:
                transport = v.CountingHTTP(provider, 'fake-secret')
                for method, path in [('POST', v.old.inference_path(provider)),
                        ('GET', v.COUNT_PATHS[provider]), ('POST', '/responses'), ('POST', '/messages')]:
                    with self.assertRaises(e.AdmissionError): transport.request(method, path, {})
            http.return_value.request.assert_not_called()

    def test_66_counts_resume_skip_and_google_coverage_stays_explicit(self):
        with tempfile.TemporaryDirectory() as root, patch.object(v, 'journal_snapshot', return_value=BASELINE):
            for provider in e.CANDIDATES:
                http = Mock(); http.request.return_value = {'_http_status': 200, 'object': 'response.input_tokens', 'input_tokens': 5100, 'totalTokens': 5800}
                directory = Path(root) / provider
                result = v.prepare(provider, directory, http)
                self.assertEqual(http.request.call_count, 66)
                self.assertEqual(result['casesCounted'], 66)
                self.assertFalse(result['paidDispatchAuthorized'])
                self.assertEqual(result['completeStructuredInputCount'], provider != 'google')
                self.assertEqual(v.prepare(provider, directory, http), result)
                self.assertEqual(http.request.call_count, 66)

    def test_failed_count_timeout_malformed_and_caps_are_fail_closed(self):
        with patch.object(v, 'journal_snapshot', return_value=BASELINE):
            for response in ({'_http_status': 403, 'input_tokens': 5000},
                    {'_http_status': 200, 'object': 'unexpected', 'input_tokens': 5000},
                    {'_http_status': 200, 'input_tokens': True}, {'_http_status': 200, 'input_tokens': -1}):
                with tempfile.TemporaryDirectory() as root:
                    http = Mock(); http.request.return_value = response
                    for _ in range(2):
                        with self.assertRaises(e.AdmissionError): v.prepare('openai', root, http)
                    self.assertEqual(http.request.call_count, 1)
            with tempfile.TemporaryDirectory() as root:
                http = Mock(); http.request.side_effect = TimeoutError('fake private detail')
                with self.assertRaises(e.AdmissionError): v.prepare('openai', root, http)
                text = '\n'.join(x.read_text() for x in Path(root).glob('*.json'))
                self.assertNotIn('fake private detail', text)
                with self.assertRaises(e.AdmissionError): v.prepare('openai', root, http)
                self.assertEqual(http.request.call_count, 1)
            with tempfile.TemporaryDirectory() as root:
                http = Mock(); http.request.return_value = {'_http_status': 200, 'input_tokens': 11489}
                self.assertFalse(v.prepare('anthropic', root, http)['capPass'])

    def test_expired_checkpoint_and_interrupted_marker_never_replayed_implicitly(self):
        with patch.object(v, 'journal_snapshot', return_value=BASELINE), tempfile.TemporaryDirectory() as root:
            http = Mock(); http.request.return_value = {'_http_status': 200, 'object': 'response.input_tokens', 'input_tokens': 5100}
            v.prepare('openai', root, http)
            first = Path(root) / 'openai-journey-01.json'
            row = json.loads(first.read_text()); row['observedAtUTC'] = '2000-01-01T00:00:00+00:00'
            first.write_text(json.dumps(row))  # Disposable test artifact only.
            with self.assertRaisesRegex(e.AdmissionError, 'expired'): v.prepare('openai', root, http)
            self.assertEqual(http.request.call_count, 66)
        with patch.object(v, 'journal_snapshot', return_value=BASELINE), tempfile.TemporaryDirectory() as root:
            # A crash between marker and result cannot silently repeat a count.
            path, body = v.count_body('journey-01', 'openai')
            binding = {'configurationHash': e.digest(v.configuration()), 'provider': 'openai', 'caseId': 'journey-01',
                       'payloadHash': e.digest(v.payload('journey-01', 'openai')), 'countBodyHash': e.digest(body)}
            v.audit.append_json(Path(root) / 'openai-journey-01.started.json', binding)
            http = Mock()
            with self.assertRaisesRegex(e.AdmissionError, 'Interrupted count'): v.prepare('openai', root, http)
            http.request.assert_not_called()

    def test_grammar_projection_has_identical_expanded_constraints(self):
        original = e.wire_schema('anthropic'); proposed = v.anthropic_grammar_proposal()
        def expanded(schema):
            def walk(node):
                if isinstance(node, dict):
                    if '$ref' in node: return walk(schema['$defs'][node['$ref'].split('/')[-1]])
                    return {k: walk(x) for k, x in node.items() if k != '$defs'}
                if isinstance(node, list): return [walk(x) for x in node]
                return node
            return walk(schema)
        self.assertEqual(expanded(original), expanded(proposed))
        self.assertEqual(p.schema_stats(original)['unionNodes'], 15)
        self.assertEqual(p.schema_stats(proposed)['unionNodes'], 14)
        self.assertEqual(p.schema_stats(original)['optionalProperties'], 0)


if __name__ == '__main__': unittest.main()
