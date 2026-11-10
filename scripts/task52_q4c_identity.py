"""Q4C offline source/build allowlist, not real dispatch enrollment."""
import json
from pathlib import Path
from scripts import task52_q1 as q1
from scripts.task52_q4a_identity import verify as prior

MANIFEST=q1.ROOT/'docs/task52-q4c-build-v1.json'
MANIFEST_SHA='f09da947167d8e37deebee5b69bfb86cac62b402e49acc770cb25b4ad38511fb'


def verify_build(*,full=False):
    if q1.sha(MANIFEST.read_bytes())!=MANIFEST_SHA:raise ValueError('Unknown Q4C build')
    m=json.loads(MANIFEST.read_text())
    if m['identity']!='52b-q4c-signed-real-schema-OFFLINE-v1' or m['liveDispatchAvailable'] or not m['syntheticOnly']:
        raise ValueError('Wrong Q4C purpose')
    if q1.sha(Path('/usr/bin/ssh-keygen').read_bytes())!=m['sshKeygenSHA256']:raise ValueError('OpenSSH binary changed')
    for p,h in m['artifactHashes'].items():
        if q1.sha((q1.ROOT/p).read_bytes())!=h:raise ValueError('Q4C source/configuration identity mismatch')
    prior(full=full)
    return m


def binding():
    m=verify_build()
    return {**m['binding'],'executionBuildHash':MANIFEST_SHA}
