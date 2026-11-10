"""Exact reviewed V5.1 OFFLINE profile. No real grants or live writer."""
from copy import deepcopy
import json
from pathlib import Path
from scripts import task52_q1 as q1
from scripts.task52_q4c_identity import verify_build as verify_core
from scripts.task52_ordering_v51_identity import verify as verify_policy
from scripts.task52_q4b import inspect_original

MANIFEST=q1.ROOT/'docs/task52-v51-evaluator-build-v1.json'
MANIFEST_SHA='756976849efc43e58032f4c3ff5abeef8465f85e4b1860d3b93e5b128aefaf07'
IDENTITY='52b-v51-signed-offline-evaluator-v1'


def verify_build(*,full=False):
    if q1.sha(MANIFEST.read_bytes())!=MANIFEST_SHA:raise ValueError('Unknown V5.1 offline build')
    m=json.loads(MANIFEST.read_text())
    if m['identity']!=IDENTITY or not m['syntheticOnly'] or m['liveDispatchAvailable'] or m['paidApproval']:
        raise ValueError('Wrong V5.1 offline purpose')
    verify_core(full=full)
    for path,expected in m['artifactHashes'].items():
        if q1.sha((q1.ROOT/path).read_bytes())!=expected:raise ValueError('V5.1 profile source/config mismatch: '+path)
    if full:
        verify_policy()
        if inspect_original()['journalSHA256']!=m['binding']['originalBaseline']['journalSHA256']:raise ValueError('Original journal changed')
    return m


def binding():
    m=verify_build()
    return {**deepcopy(m['binding']),'executionBuildHash':MANIFEST_SHA}


def plan():
    m=verify_build()
    return deepcopy(m['plan'])
