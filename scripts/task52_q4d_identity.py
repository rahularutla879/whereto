"""Q4D exact offline build allowlist; never a financial/execution grant."""
import json
from scripts import task52_q1 as q1
from scripts import task52_v51_eval_identity as parent

IDENTITY = '52b-q4d-v51-journal-bridge-OFFLINE-v1'
MANIFEST = q1.ROOT / 'docs/task52-q4d-build-v1.json'
MANIFEST_SHA = '4e9c2cd268a589cfa2d3e32a04aac67da6dfdf809792afa26e08e8d9a91841f4'


def verify(*, full=False):
    if q1.sha(MANIFEST.read_bytes()) != MANIFEST_SHA:
        raise ValueError('Unknown Q4D offline build')
    m = json.loads(MANIFEST.read_text())
    if (m['identity'] != IDENTITY or not m['syntheticOnly'] or m['liveDispatchAvailable']
            or m['realWritableAdapter'] or m['financialApproval']):
        raise ValueError('Wrong Q4D purpose')
    for path, expected in m['artifactHashes'].items():
        if q1.sha((q1.ROOT / path).read_bytes()) != expected:
            raise ValueError('Q4D source/build mismatch')
    p = parent.verify_build(full=full)
    if (m['parentBuildSHA256'] != parent.MANIFEST_SHA or
            m['parentBindingHash'] != q1.digest(p['binding']) or
            m['planHash'] != q1.digest(p['plan'])):
        raise ValueError('Q4D parent version mismatch')
    return m
