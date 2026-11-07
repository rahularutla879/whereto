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
PREP = e.STATE / 'readiness-v3.json'
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
    return {'openai': '/responses', 'anthropic': '/messages',
            'google': '/models/gemini-3.8-flash:generateContent'}[provider]


def allowed_paths(provider):
    return {inference_path(provider), *{
        'openai': ['/responses/input_tokens'],
        'anthropic': ['/models/claude-haiku-5-5', '/messages/count_tokens'],
        'google': ['/models/gemini-3.8-flash', '/models/gemini-3.8-flash:countTokens'],
    }[provider]}


def validate_google_request(payload):
    """Fail closed against reviewed v1beta REST fields/JSON Schema subset.

    Source: official v1beta discovery ThinkingConfig/GenerationConfig/
    TextResponseFormat and structured-output guide, reviewed 2026-11-07 UTC.
    This proves documented shape, not remote schema-compilation success.
    """
    if set(payload) != {'systemInstruction', 'contents', 'generationConfig'}:
        raise e.AdmissionError('Unexpected Developer API request fields')
    gen = payload['generationConfig']
    if set(gen) != {'maxOutputTokens', 'thinkingConfig', 'responseFormat'} or gen['maxOutputTokens'] != e.OUTPUT_CAP:
        raise e.AdmissionError('Unexpected generation settings/cap')
    if gen['thinkingConfig'] != {'thinkingLevel': 'LOW'}:
        raise e.AdmissionError('REST thinking level must be LOW')
    if set(gen['responseFormat']) != {'text'}:
        raise e.AdmissionError('Expected text response format only')
    fmt = gen['responseFormat']['text']
    if set(fmt) != {'mimeType', 'schema'} or fmt['mimeType'] != 'APPLICATION_JSON':
        raise e.AdmissionError('Expected standard JSON Schema response format')
    schema = fmt['schema']
    if schema != e.wire_schema('google'):
        raise e.AdmissionError('Prepared Google schema drift')
    keywords = {'$defs', '$ref', 'type', 'description', 'properties', 'required',
                'additionalProperties', 'anyOf', 'enum', 'const', 'items', 'format',
                'minimum', 'maximum', 'minItems', 'maxItems', 'minLength', 'maxLength'}
    def visit(node):
        if not isinstance(node, dict) or set(node) - keywords:
            raise e.AdmissionError('Unreviewed JSON Schema keyword')
        if '$ref' in node:
            prefix = '#/$defs/'
            if not node['$ref'].startswith(prefix) or node['$ref'][len(prefix):] not in schema['$defs']:
                raise e.AdmissionError('Unresolved/local-only schema reference')
        if 'type' in node and node['type'] not in ('object','array','string','integer','number','boolean','null'):
            raise e.AdmissionError('Expected standard JSON Schema type')
        if node.get('type') == 'object' and set(node['required']) != set(node['properties']):
            raise e.AdmissionError('Required schema properties changed')
        for key in ('properties', '$defs'):
            for child in node.get(key, {}).values():
                visit(child)
        for child in node.get('anyOf', []):
            visit(child)
        if 'items' in node:
            visit(node['items'])
    visit(schema)
    if payload['systemInstruction'] != {'parts': [{'text': e.SYSTEM_PROMPT}]}:
        raise e.AdmissionError('System instruction drift')
    for message in payload['contents']:
        if set(message) != {'role', 'parts'} or message['role'] not in ('user', 'model') or len(message['parts']) != 1 or set(message['parts'][0]) != {'text'}:
            raise e.AdmissionError('Unexpected content/message representation')
    return True


def count_body(provider, payload):
    if provider == 'openai':
        # Exact Responses input and schema representation, not an estimate of a
        # different Chat Completions request. Generation-only controls excluded.
        return '/responses/input_tokens', {k: payload[k] for k in ('model', 'input', 'text')}
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


def prepare(providers=None):
    keys = credentials()
    cases = e.corpus()['cases']
    report = {'configHash': e.digest(e.metadata()), 'preparedAt': datetime.now(timezone.utc).isoformat(),
              'inferenceRequests': 0, 'providers': {}}
    with e.exclusive(e.STATE):
        if providers is not None and PREP.exists():
            prior = json.loads(PREP.read_text())
            if prior['configHash'] != report['configHash']:
                raise e.AdmissionError('Cannot merge readiness across configurations')
            report['providers'] = prior['providers']
            for previous in report['providers'].values():
                previous.setdefault('preparedAt', prior['preparedAt'])
        for provider in (e.CANDIDATES if providers is None else providers):
            http = HTTP(provider, keys[provider])
            adapter = e.Adapter(provider, http)
            entry = {'ready': False, 'nonInferenceRequests': 0,
                     'preparedAt': datetime.now(timezone.utc).isoformat()}
            try:
                if provider != 'openai':
                    model = http.request('GET', '/models/' + e.CANDIDATES[provider]['model'])
                    entry['nonInferenceRequests'] += 1
                    entry['modelMetadata'] = model
                    if model['_http_status'] != 200:
                        raise e.AdmissionError('Model metadata access refused')
                if provider == 'google':
                    for case in cases:
                        validate_google_request(adapter.payload(case['text']))
                counts = {}
                for case in cases:
                    path, body = count_body(provider, adapter.payload(case['text']))
                    counted = http.request('POST', path, body)
                    entry['nonInferenceRequests'] += 1
                    if counted['_http_status'] != 200:
                        entry['tokenCountResponse'] = counted
                        raise e.AdmissionError('Token counting access refused')
                    count = counted.get('totalTokens') if provider == 'google' else counted.get('input_tokens')
                    if type(count) is not int or count <= 0:
                        raise e.AdmissionError('No valid provider token count')
                    counts[case['id']] = count
                    time.sleep(.1)
                # Anthropic counts its injected schema/formatting; retain 512
                # additional tokens for documented small counting variability.
                # Google schema-as-text may differ from actual format injection:
                # retain the existing larger 2048-token framing allowance.
                margin = 512 if provider == 'anthropic' else 2048
                bound = max(counts.values()) + margin
                entry.update(counts=counts, countMargin=margin, countedInputTokens=max(counts.values()),
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


# Root paid-journal configuration is never replaced. A reviewed v3 revision is
# recorded beside it and on new attempt rows; original slots/costs stay intact.
LEGACY_CONFIG_HASH = 'c195b4bd8cfec037238e542574a8613186e26d76f1fd033236e8a8fa7b2fc8ca'
LEGACY_RECORD_HASH = '7a0545f019b16337faa5d02f3efd73f32b3052698eb16384ef98b2b182577305'


def acknowledged_legacy_failure(row):
    return (tuple(row[:5]) == ('google', 'journey-01', 1, 'recorded', 16500000)
            and LEGACY_RECORD_HASH is not None and e.digest(json.loads(row[5])) == LEGACY_RECORD_HASH)


def continuation_ledger(path):
    import sqlite3
    if not path.exists():
        raise e.AdmissionError('Original paid journal missing; cannot recreate')
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise e.AdmissionError('Journal integrity failed')
        original = json.loads(db.execute('SELECT config FROM metadata').fetchone()[0])
        if e.digest(original) != LEGACY_CONFIG_HASH:
            raise e.AdmissionError('Unreviewed original journal configuration')
        current = e.metadata()
        allowed_changes = {'promptVersion', 'promptHash', 'wireSchemaHashes', 'sampling', 'transportVersion'}
        if {k:v for k,v in original.items() if k not in allowed_changes} != {k:v for k,v in current.items() if k not in allowed_changes}:
            raise e.AdmissionError('Revision changes immutable experiment authorization')
        row = db.execute("SELECT provider,case_id,repetition,status,charge,record FROM attempts WHERE provider='google' AND case_id='journey-01' AND repetition=1").fetchone()
        if not row or not acknowledged_legacy_failure(row):
            raise e.AdmissionError('Original consumed Google attempt changed/missing')
    finally:
        db.close()
    revision = {'originalConfigurationHash': e.digest(original), 'configuration': current}
    destination = path.parent / ('configuration-' + e.digest(current) + '.json')
    if destination.exists():
        if json.loads(destination.read_text()) != revision:
            raise e.AdmissionError('Recorded revision changed')
    else:
        # Exclusive creation: never overwrite a recorded revision.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(revision, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
    return e.Ledger(path, original)


def live(max_new_attempts=None):
    if datetime.now(timezone.utc).date().isoformat() != '2026-11-07':
        raise e.AdmissionError('Readiness/pricing must be reverified on a new date')
    readiness = json.loads(PREP.read_text())
    if readiness['configHash'] != e.digest(e.metadata()):
        raise e.AdmissionError('Readiness configuration drift')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(readiness['preparedAt'])).total_seconds()
    if not 0 <= age <= 86400:
        raise e.AdmissionError('Readiness expired')
    if max_new_attempts is not None and (type(max_new_attempts) is not int or max_new_attempts < 1):
        raise e.AdmissionError('Invalid explicit dispatch bound')
    dispatched = 0
    keys = credentials()
    # Whole-run lock prevents simultaneous writers/repeated or overlapping sends.
    with e.exclusive(e.STATE):
        ledger = continuation_ledger(e.STATE / 'journal.sqlite')
        try:
            for provider, entry in readiness['providers'].items():
                if not entry['ready']:
                    continue
                rows = ledger.db.execute('SELECT provider,case_id,repetition,status,charge,record FROM attempts WHERE provider=?', (provider,)).fetchall()
                if any(row[3] == 'reserved_uncertain' or (json.loads(row[5])['status'] != 'complete' and not acknowledged_legacy_failure(row)) for row in rows):
                    print(json.dumps({'provider': provider, 'stopped': 'Prior failed/uncertain attempt; no automatic further dispatch'}), flush=True)
                    continue
                provider_age = (datetime.now(timezone.utc) - datetime.fromisoformat(entry['preparedAt'])).total_seconds()
                if not 0 <= provider_age <= 86400:
                    raise e.AdmissionError('Provider-specific readiness expired')
                if not entry.get('accountGatesReviewed'):
                    raise e.AdmissionError('Credit, processing and endpoint readiness must be reviewed before live dispatch')
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
                            dispatched += 1
                            if max_new_attempts is not None and dispatched >= max_new_attempts:
                                return
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
