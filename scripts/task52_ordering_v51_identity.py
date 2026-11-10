"""Exact V5.1 OFFLINE manifest; no financial or planning authority."""
import json
from scripts import task52_q1 as q1
from scripts.task52_ordering_v5_identity import verify as verify_parent
DIGEST='7e1dd8f0bc1c249677d7c9dbdc18d37cf776f998d1ccec1809ebe88c783a54e7'


def verify_document(document):
    if q1.digest(document)!=DIGEST:raise ValueError('Unknown or mismatched V5.1 offline identity')
    for name,expected in document['sources'].items():
        if q1.sha((q1.ROOT/name).read_bytes())!=expected:raise ValueError('V5.1 source/artifact mismatch: '+name)
    return document


def verify():
    verify_parent()
    return verify_document(json.loads((q1.ROOT/'docs/task52-ordering-v51-manifest-v1.json').read_text()))
