"""Pinned OFFLINE-only V5 evidence identity. Never supplies authority."""
import json
from scripts import task52_q1 as q1
from scripts.task52_q4c_identity import verify_build

IDENTITY='52b-v5-offline-amendment-manifest-v1'
DIGEST='19671baadf93c83bd323ba6215bf633c5a9045f6558b8fef24cc166cf61fcd35'


def verify_document(document):
    if q1.digest(document)!=DIGEST:
        raise ValueError('Unknown or mismatched V5 offline manifest')
    for name,expected in document['sources'].items():
        if q1.sha((q1.ROOT/name).read_bytes())!=expected:
            raise ValueError('V5 source/artifact identity mismatch: '+name)
    return document


def verify():
    q1.verify()
    verify_build(full=True)
    return verify_document(json.loads((q1.ROOT/'docs/task52-ordering-v5-manifest-v1.json').read_text()))
