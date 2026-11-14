"""Offline, read-only preparation checks. No credentials, transport or journal access.

Run from the repository: PYTHONPATH=. backend/.venv/bin/python -m
scripts.task52b_prepare_openai. This checks committed payloads; it sends nothing.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '52b-openai-five-slot-offline-preparation-v1'
ARTIFACTS = ROOT / 'docs/task52b-openai-diagnostic-prepared-v1'
ANCHORS = {
    'docs/task52-cloud-prompt-v51-REVIEWED-v1.json': '02b20af7fbabeb93d9d305a10c1327b8e97043b2b995f830fc88ab44f218f5da',
    'docs/task52-q3-v51-PROPOSED-v3.json': '27544ec1e57ffccf2b07cc802b0d4778a145795ac3d41f42e017985f60c9fafc',
    'docs/task52-q1-rubric-v3-v51-PROPOSED.json': 'fd0686aeb3b136d34da7cf586fa5413593500c95837c45fb302d0d179cf93abe',
    'docs/task52-evaluation-corpus.json': '5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f',
}
SLOTS = (('extension-repeated', 2), ('journey-04', 2), ('extension-partial', 2),
         ('journey-06', 2), ('journey-21', 1))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def prepare(root=ROOT):
    """Construct data only; never call the frozen evaluator's paid entry points."""
    loaded = {}
    for path, expected in ANCHORS.items():
        raw = (root / path).read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError('Frozen artifact identity mismatch: ' + path)
        loaded[path] = json.loads(raw)
    reviewed, proposal, rubric, corpus = (loaded[p] for p in ANCHORS)
    if tuple((s['slot'][1], s['slot'][2]) for s in proposal['slots']) != SLOTS:
        raise ValueError('Slot sequence mismatch')
    if digest(rubric) != proposal['rubricDigest']:
        raise ValueError('Rubric identity mismatch')
    template = reviewed['frozenRequestTemplate']
    if digest(template['input']) != reviewed['promptHash']:
        raise ValueError('Prompt mismatch')
    cases = {c['id']: c for c in corpus['cases']}
    gold = {c['id']: c for c in rubric['cases']}
    records = []
    for i, slot in enumerate(proposal['slots'], 1):
        provider, case, repetition = slot['slot']
        text = cases[case]['text']
        if (provider != 'openai' or text != slot['source'] or
                sha256(text.encode()).hexdigest() != slot['sourceSHA256'] or
                digest(gold[case]) != slot['rubricCaseDigest'] or
                gold[case]['fields'] != slot['all24Expectations'] or
                len(gold[case]['fields']) != 24):
            raise ValueError('Source/rubric slot mismatch')
        body = deepcopy(template)
        body['input'][-1]['content'] = text
        if digest(body) != slot['proposedPayloadHash']:
            raise ValueError('Prepared request mismatch')
        # Documented count endpoint fields; preserve reasoning as well as full
        # input and strict schema. Generation-only controls remain in body.
        count = {key: deepcopy(body[key]) for key in ('model', 'input', 'text', 'reasoning')}
        stem = f'{i:02d}-{case}-r{repetition}'
        records.append({'slot': slot['slot'], 'sourceSHA256': slot['sourceSHA256'],
                        'rubricCaseDigest': slot['rubricCaseDigest'],
                        'requestFile': stem + '.request.json', 'requestSHA256': digest(body),
                        'countFile': stem + '.count.json', 'countSHA256': digest(count),
                        'request': body, 'countRequest': count,
                        'verifiedInputTokens': None, 'dispatchAuthorized': False})
    return records


def input_bound(count, *, request_hash, expected_hash):
    """Pure arithmetic only, NOT readiness certification or provider evidence.

    The historical 2,048-token margin is retained. Caller still needs authentic,
    fresh, exact-payload provider evidence and separately reviewed authorization.
    """
    if (type(count) is not int or count <= 0 or request_hash != expected_hash or
            count + 2048 > 12000):
        raise ValueError('Verified complete input bound unavailable or over cap')
    return count + 2048


def verify_artifacts():
    records = prepare()
    for record in records:
        for kind, key in (('request', 'requestFile'), ('countRequest', 'countFile')):
            if (ARTIFACTS / record[key]).read_bytes() != canonical(record[kind]):
                raise ValueError('Prepared file differs: ' + record[key])
    return {'identity': VERSION, 'slotsVerified': len(records), 'inputCounts': None,
            'readinessVerified': False, 'dispatchAuthorized': False}


if __name__ == '__main__':
    print(json.dumps(verify_artifacts(), sort_keys=True))
