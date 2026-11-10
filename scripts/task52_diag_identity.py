"""Exact proposed diagnostic-only OFFLINE build; no real execution authority."""
import json
from copy import deepcopy
from scripts import task52_q1 as q1
from scripts import task52_q4d_identity as q4d
from scripts import task52_v51_eval_identity as parent

IDENTITY='52b-v51-known-legacy-loss-diagnostic-PROPOSED-offline-v1'
PURPOSE='synthetic_diagnostic_known_legacy_loss_only_v1'
MANIFEST=q1.ROOT/'docs/task52-diagnostic-progression-build-v1.json'
MANIFEST_SHA='2241ea0c394ca6cab78b9c16b485641d2e08d68c6e20aa376b88e539657c332b'


def verify(*,full=False):
    if q1.sha(MANIFEST.read_bytes())!=MANIFEST_SHA:raise ValueError('Unknown diagnostic build')
    m=json.loads(MANIFEST.read_text())
    if (m['identity']!=IDENTITY or m['purpose']!=PURPOSE or not m['syntheticOnly']
            or m['liveDispatchAvailable'] or m['financialApproval']):raise ValueError('Wrong diagnostic purpose')
    q4d.verify(full=full)
    if m['parentQ4DBuildHash']!=q4d.MANIFEST_SHA or m['parentV51BuildHash']!=parent.MANIFEST_SHA:raise ValueError('Wrong diagnostic parents')
    for p,h in m['artifactHashes'].items():
        if q1.sha((q1.ROOT/p).read_bytes())!=h:raise ValueError('Diagnostic source/policy mismatch')
    return m


def defect():return deepcopy(verify()['allowlistedDefect'])
def defect_hash():return q1.digest(defect())
def plan():return {**parent.plan(),'identity':IDENTITY,'purpose':PURPOSE}
def binding():
    return {**parent.binding(),'parentExecutionBuildHash':parent.MANIFEST_SHA,
            'executionBuildHash':MANIFEST_SHA,'diagnosticPurpose':PURPOSE,
            'allowlistedDefectHash':defect_hash()}

# Fixed alias for unchanged inherited synthetic regression interfaces.
verify_build=verify
