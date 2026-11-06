"""Explicit Task 52B synthetic-only preparation and single-attempt dispatch.

Run prepare (non-inference model metadata/token counts), then live. Credentials
never enter artifacts, arguments, environment exports, or ordinary logs. No SDK
retries, redirects, proxy fallback, Maps authentication, or arbitrary endpoints.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import socket
import time
from contextlib import nullcontext
from unittest.mock import patch

import requests

from scripts import cloud_model52 as e

ENV = e.ROOT / 'backend/.env.cloud-evaluation'
PREP = e.STATE / 'readiness.json'
VARS = {'openai': 'OPENAI_API_KEY', 'google': 'GEMINI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY'}
BASE = {'openai': 'https://api.openai.com/v1',
        'google': 'https://generativelanguage.googleapis.com/v1beta',
        'anthropic': 'https://api.anthropic.com/v1'}


def private_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Atomic replacement, private from creation onward.
    temporary = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def credentials():
    if ENV.is_symlink() or stat.S_IMODE(ENV.stat().st_mode) != 0o600:
        raise e.AdmissionError('Evaluation credential file must be a regular mode-600 file')
    rows = [line.split('=', 1) for line in ENV.read_text().splitlines() if line.strip()]
    values = dict(rows)
    if len(rows) != len(values) or set(values) != set(VARS.values()) or not all(values.values()):
        raise e.AdmissionError('Expected exactly three evaluation credentials')
    return {p: values[name] for p, name in VARS.items()}


class HTTP:
    def __init__(self, provider, key):
        self.provider, self.key = provider, key
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    def request(self, method, path, body=None):
        if path not in allowed_paths(self.provider):
            raise e.AdmissionError('Endpoint outside evaluation allowlist')
        expected_method = 'GET' if path.startswith('/models/') and ':' not in path else 'POST'
        if method != expected_method:
            raise e.AdmissionError('Method outside evaluation allowlist')
        headers = {'Content-Type': 'application/json'}
        if self.provider == 'openai':
            headers['Authorization'] = 'Bearer ' + self.key
        elif self.provider == 'google':
            headers['x-goog-api-key'] = self.key
        else:
            headers.update({'x-api-key': self.key, 'anthropic-version': '2023-06-01'})
        # This Mac's approved restriction is its verified IPv4 egress. Select
        # that transport family locally; do not broaden the cloud allowlist.
        family = (patch('urllib3.util.connection.allowed_gai_family', return_value=socket.AF_INET)
                  if self.provider == 'google' else nullcontext())
        with family:
            response = self.session.request(method, BASE[self.provider] + path,
                                            headers=headers, json=body, timeout=(10, 120),
                                            allow_redirects=False)
        # Complete body consumed before timing ends. Do not retain auth/headers.
        raw = response.content.decode('utf-8').replace(self.key, '[REDACTED_KEY]')
        try:
            value = json.loads(raw)
        except ValueError:
            value = {'error': {'type': 'non_json_response'}}
        if not isinstance(value, dict):
            value = {'error': {'type': 'unexpected_response_shape'}}
        value['_http_status'] = response.status_code
        value['_request_id'] = response.headers.get('request-id') or response.headers.get('x-request-id')
        if response.status_code != 200 and 'error' not in value:
            value['error'] = {'type': 'http_error'}
        return value

    def __call__(self, payload):
        return self.request('POST', inference_path(self.provider), payload)


def inference_path(provider):
    return {'openai': '/chat/completions', 'anthropic': '/messages',
            'google': '/models/gemini-3.8-flash:generateContent'}[provider]


def allowed_paths(provider):
    return {inference_path(provider), *{
        'openai': ['/responses/input_tokens'],
        'anthropic': ['/models/claude-haiku-5-5', '/messages/count_tokens'],
        'google': ['/models/gemini-3.8-flash', '/models/gemini-3.8-flash:countTokens'],
    }[provider]}


def count_body(provider, payload):
    if provider == 'openai':
        return '/responses/input_tokens', {'model': payload['model'], 'input': payload['messages'],
            'text': {'format': {'type': 'json_schema', 'name': 'outing_interpretation',
                                'strict': True, 'schema': e.wire_schema(provider)}}}
    if provider == 'anthropic':
        return '/messages/count_tokens', {k: v for k, v in payload.items() if k != 'max_tokens'}
    # Count all actual messages/system AND schema serialized as extra text.
    # CountTokens can omit generationConfig/schema; explicitly include it here.
    # It is a free count operation, never an instruction sent for inference.
    return '/models/gemini-3.8-flash:countTokens', {
        'generateContentRequest': {'model': 'models/gemini-3.8-flash',
            'systemInstruction': payload['systemInstruction'],
            'contents': payload['contents'] + [{'role': 'user', 'parts': [
                {'text': json.dumps(e.wire_schema(provider), ensure_ascii=False)}]}]}}


def prepare():
    keys = credentials()
    cases = e.corpus()['cases']
    longest = max(cases, key=lambda c: len(c['text'].encode()))
    report = {'configHash': e.digest(e.metadata()), 'preparedAt': datetime.now(timezone.utc).isoformat(),
              'inferenceRequests': 0, 'providers': {}}
    with e.exclusive(e.STATE):
        for provider in e.CANDIDATES:
            http = HTTP(provider, keys[provider])
            adapter = e.Adapter(provider, http)
            entry = {'ready': False, 'nonInferenceRequests': 0}
            try:
                if provider != 'openai':
                    model = http.request('GET', '/models/' + e.CANDIDATES[provider]['model'])
                    entry['nonInferenceRequests'] += 1
                    entry['modelMetadata'] = model
                    if model['_http_status'] != 200:
                        raise e.AdmissionError('Model metadata access refused')
                path, body = count_body(provider, adapter.payload(longest['text']))
                counted = http.request('POST', path, body)
                entry['nonInferenceRequests'] += 1
                entry['tokenCountResponse'] = counted
                if counted['_http_status'] != 200:
                    raise e.AdmissionError('Token counting access refused')
                count = counted.get('totalTokens') if provider == 'google' else counted.get('input_tokens')
                if type(count) is not int or count <= 0:
                    raise e.AdmissionError('No valid provider token count')
                # Counted complete payload plus 2048 for provider framing/schema
                # differences and the UTF-8 byte bound on replacing the last input.
                bound = count + 2048 + 2 * len(longest['text'].encode())
                entry.update(countedCaseId=longest['id'], countedInputTokens=count,
                    inputUpperBound=bound, payloadHashes={c['id']: e.digest(adapter.payload(c['text'])) for c in cases})
                if bound > e.INPUT_CAP:
                    raise e.AdmissionError('Conservative input bound exceeds approved 12000')
                entry['ready'] = True
            except Exception as error:
                entry['blockerType'] = type(error).__name__
                if isinstance(error, e.AdmissionError):
                    entry['blocker'] = str(error)
            report['providers'][provider] = entry
            print(json.dumps({'provider': provider, 'ready': entry['ready'],
                'inputUpperBound': entry.get('inputUpperBound'), 'blocker': entry.get('blocker', entry.get('blockerType'))}), flush=True)
        private_json(PREP, report)
    return report


def live():
    if datetime.now(timezone.utc).date().isoformat() != '2026-11-06':
        raise e.AdmissionError('Readiness/pricing must be reverified on a new date')
    readiness = json.loads(PREP.read_text())
    if readiness['configHash'] != e.digest(e.metadata()):
        raise e.AdmissionError('Readiness configuration drift')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(readiness['preparedAt'])).total_seconds()
    if not 0 <= age <= 86400:
        raise e.AdmissionError('Readiness expired')
    keys = credentials()
    # Whole-run lock prevents simultaneous writers/repeated or overlapping sends.
    with e.exclusive(e.STATE):
        ledger = e.Ledger(e.STATE / 'journal.sqlite', e.metadata())
        try:
            for provider, entry in readiness['providers'].items():
                if not entry['ready']:
                    continue
                rows = ledger.db.execute('SELECT status,record FROM attempts WHERE provider=?', (provider,)).fetchall()
                if any(status == 'reserved_uncertain' or (json.loads(record)['status'] != 'complete') for status, record in rows):
                    print(json.dumps({'provider': provider, 'stopped': 'Prior failed/uncertain attempt; no automatic further dispatch'}), flush=True)
                    continue
                adapter = e.Adapter(provider, HTTP(provider, keys[provider]))
                stop = False
                for repeat in (1, 2, 3):
                    for case in e.corpus()['cases']:
                        if e.digest(adapter.payload(case['text'])) != entry['payloadHashes'][case['id']]:
                            raise e.AdmissionError('Prepared payload drift')
                        # Reuse the existing committed-before-dispatch reservation.
                        row = e._run_one(ledger, adapter, case, repeat, entry['inputUpperBound'])
                        if row:
                            print(json.dumps({k: row.get(k) for k in ('provider','caseId','repetition','status','latencyMs','accountedNanodollars')}), flush=True)
                            if row.get('reviewHalt'):
                                raise e.AdmissionError('Accepted semantic mismatch: experiment stopped for review')
                            if row['status'] != 'complete':
                                stop = True
                                break
                            time.sleep(1)  # Explicit pacing; no concurrency/warmup.
                    if stop:
                        break
        finally:
            ledger.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'live'))
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    else:
        live()


if __name__ == '__main__':
    main()
