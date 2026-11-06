"""Offline checks for the explicit single-attempt HTTP boundary."""
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import cloud_model52 as e
from scripts import cloud_model52_live as live


class LiveBoundaryTests(unittest.TestCase):
    def test_transport_no_redirect_retry_and_redacts_secret(self):
        response = Mock(content=b'{"error":{"message":"test-secret"}}', status_code=403,
                        headers={'request-id': 'test-request'})
        with patch.object(live.requests.Session, 'request', return_value=response) as send:
            client = live.HTTP('anthropic', 'test-secret')
            result = client.request('GET', '/models/claude-haiku-5-5')
            self.assertNotIn('test-secret', json.dumps(result))
            self.assertEqual(result['_http_status'], 403)
            self.assertEqual(client.session.get_adapter('https://').max_retries.total, 0)
            self.assertFalse(send.call_args.kwargs['allow_redirects'])
            self.assertEqual(send.call_count, 1)
            self.assertFalse(client.session.trust_env)
            with self.assertRaises(e.AdmissionError):
                client.request('GET', 'https://maps.googleapis.com/')
            with self.assertRaises(e.AdmissionError):
                client.request('POST', '/models/claude-haiku-5-5')
            self.assertEqual(send.call_count, 1)

    def test_timeout_propagates_without_retry(self):
        with patch.object(live.requests.Session, 'request', side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):
                live.HTTP('google', 'test-key').request('POST', live.inference_path('google'), {})
            self.assertEqual(send.call_count, 1)

    def test_all_count_operations_are_non_inference(self):
        for provider in e.CANDIDATES:
            path, body = live.count_body(provider, e.Adapter(provider, None).payload(e.corpus()['cases'][0]['text']))
            self.assertNotEqual(path, live.inference_path(provider))
            self.assertIn(path, live.allowed_paths(provider))
            self.assertNotIn('key', body)
        google = live.count_body('google', e.Adapter('google', None).payload('synthetic'))[1]
        self.assertEqual(google['generateContentRequest']['contents'][-1]['parts'][0]['text'],
                         json.dumps(e.wire_schema('google'), ensure_ascii=False))

    def test_frozen_provider_settings_and_conservative_ceiling(self):
        bodies = {p: e.Adapter(p, None).payload('synthetic') for p in e.CANDIDATES}
        self.assertEqual(bodies['openai']['model'], 'gpt-6-luna')
        self.assertEqual(bodies['openai']['reasoning_effort'], 'none')
        self.assertFalse(bodies['openai']['store'])
        self.assertNotIn('temperature', bodies['anthropic'])
        self.assertEqual(bodies['anthropic']['thinking'], {'type':'disabled'})
        self.assertEqual(bodies['google']['generationConfig']['thinkingConfig'], {'thinkingLevel':'low'})
        self.assertEqual(sum((e.INPUT_CAP*v['rates'][0]+e.OUTPUT_CAP*v['rates'][1])*198 for v in e.CANDIDATES.values()), 4197600000)

    def test_private_file_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.json'
            live.private_json(path, {'synthetic': True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {'synthetic': True})

    def test_prepare_failure_never_calls_inference_or_opens_paid_journal(self):
        paths = []
        def refused(_self, method, path, body=None):
            paths.append(path)
            return {'_http_status': 403, 'error': {'type':'synthetic-denied'}}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(live, 'credentials', return_value={p:'fake' for p in e.CANDIDATES}), \
             patch.object(live.HTTP, 'request', refused), \
             patch.object(e, 'STATE', Path(directory)), \
             patch.object(live, 'PREP', Path(directory)/'readiness.json'):
            report = live.prepare()
            self.assertTrue(all(not x['ready'] for x in report['providers'].values()))
            self.assertFalse((Path(directory)/'journal.sqlite').exists())
            self.assertFalse(set(paths) & {live.inference_path(p) for p in e.CANDIDATES})

    def test_live_recovery_does_not_repeat_failed_paid_slot(self):
        class Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 6, 18, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(e, 'STATE', Path(directory)), \
             patch.object(live, 'PREP', Path(directory)/'readiness.json'), \
             patch.object(live, 'credentials', return_value={p:'fake' for p in e.CANDIDATES}), \
             patch.object(live, 'HTTP') as transport, patch.object(live, 'datetime', Frozen):
            entry = {'ready': True, 'inputUpperBound': 1000, 'payloadHashes': {}}
            live.private_json(live.PREP, {'configHash': e.digest(e.metadata()),
                'preparedAt': live.datetime.now(live.timezone.utc).isoformat(),
                'providers': {'google': entry}})
            ledger = e.Ledger(Path(directory)/'journal.sqlite', e.metadata())
            case = e.corpus()['cases'][0]
            e.run_one(ledger, e.Adapter('google', lambda _: {'error': {'type':'synthetic_400'}}), case, 1, 1000)
            ledger.close()
            live.live()
            transport.assert_not_called()
            reopened = e.Ledger(Path(directory)/'journal.sqlite', e.metadata())
            self.assertEqual(reopened.db.execute('SELECT count(*),sum(charge) FROM attempts').fetchone(), (1,16500000))
            reopened.close()


if __name__ == '__main__':
    unittest.main()
