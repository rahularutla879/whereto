"""Separate execution-kernel build pin; no enrollment or spending permission."""
import json
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/task52b-execution-boundary-build-v1.json'
MANIFEST_SHA='a566f2c7e13acf83b991ee1d035586f09897c5830e132f7fa86e76f26f2746d9'


def verify(*, full=False):
    raw=MANIFEST.read_bytes()
    if sha256(raw).hexdigest()!=MANIFEST_SHA: raise ValueError('Execution build mismatch')
    data=json.loads(raw)
    if data['operationalEnrollmentAvailable'] is not False: raise ValueError('No live enrollment')
    for name,expected in data['filesSHA256'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=expected: raise ValueError('Execution source/request mismatch')
    from scripts.task52_diag_identity import verify as frozen
    frozen(full=False)
    from scripts.task52_phase_b2_identity import verify as b2
    if full: b2()
    return data


def requests():
    verify()
    data=json.loads((ROOT/'docs/task52b-openai-preparation-build-v1.json').read_bytes())
    result=[]
    for entry in data['slots']:
        raw=(ROOT/'docs/task52b-openai-diagnostic-prepared-v1'/entry['requestFile']).read_bytes()
        if sha256(raw).hexdigest()!=entry['requestSHA256']: raise ValueError('Prepared bytes mismatch')
        result.append({**entry,'bytes':raw})
    return result
