"""Pin the inactive first-slot extension independently of every frozen parent."""
from hashlib import sha256
import json
from pathlib import Path
from scripts import task52b_execution_identity as parent
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/task52b-first-slot-build-v1.json'
MANIFEST_SHA='5247519e91a71023ca63cea418e33174a817cbcd78add61f94752e71df73a41b'


def verify(*,full=False):
    raw=MANIFEST.read_bytes()
    if sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('First-slot build mismatch')
    data=json.loads(raw)
    if data['activated'] is not False or data['realEnrollmentAvailable'] is not False:
        raise ValueError('First-slot operational enrollment unavailable')
    for name,expected in data['filesSHA256'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('First-slot source mismatch')
    parent.verify(full=full)
    return data


def requests():return parent.requests()[:1]
def first_request():return requests()[0]['bytes']
