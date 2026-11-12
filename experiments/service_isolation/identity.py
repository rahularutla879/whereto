"""Exact inactive service build, not enrollment, financial approval or hosted identity."""
from pathlib import Path
from hashlib import sha256
import json
from experiments.shared_state.contracts import Denied
ROOT=Path(__file__).resolve().parents[2]
PIN='e38ca7b4b84a4c5df6a1a30de8d91f3b3d7a203c8f20adb787f898bee1f6c1ec'
def verify():
    from experiments.shared_state.native_identity import verify as parent
    parent()
    try:
        raw=(ROOT/'experiments/service_isolation/build.json').read_bytes()
        if sha256(raw).hexdigest()!=PIN:raise ValueError()
        m=json.loads(raw)
        if m['productionActive'] or m['realProviderTransport'] or m['identity']!='52-service-isolation-local-v1':raise ValueError()
        for name,h in m['sources'].items():
            p=ROOT/name
            if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h:raise ValueError()
        return PIN
    except (OSError,ValueError,KeyError,TypeError):raise Denied('service_build') from None
