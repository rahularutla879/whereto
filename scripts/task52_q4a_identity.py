"""Reviewed offline build allowlist. Cannot authorize network or paid state."""
import json
import platform
from importlib.metadata import version
from scripts import task52_q1 as q1

MANIFEST = q1.ROOT/'docs/task52-q4a-execution-manifest-v1.json'
MANIFEST_SHA = '8406905232a36726c17960d56cf66527edd79111750530871502378c711275c1'


def verify(*, full=False):
    if q1.sha(MANIFEST.read_bytes()) != MANIFEST_SHA:
        raise ValueError('Unknown Q4A execution manifest')
    m = json.loads(MANIFEST.read_text())
    if m['identity'] != '52b-q4a-openai-b2-v4-OFFLINE-v1' or m['liveDispatchAvailable'] or m['paidApproval']:
        raise ValueError('Wrong execution purpose')
    for path, digest in m['artifactHashes'].items():
        if q1.sha((q1.ROOT/path).read_bytes()) != digest:
            raise ValueError('Q4A source/prompt/schema/corpus/rubric/build mismatch')
    build = m['buildIdentity']
    if platform.python_version() != build['python'] or any(version(p) != build[p] for p in ('pydantic', 'fastapi')):
        raise ValueError('Q4A current reconstruction dependency mismatch')
    if full:
        q1.verify()  # Includes B2 dependency/source identity and original paid refusal.
    return m
