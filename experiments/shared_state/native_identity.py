"""Inactive source-cohort pin. No execution grant or production enrollment."""
from pathlib import Path
from hashlib import sha256
import json
from experiments.shared_state.contracts import Denied
ROOT=Path(__file__).resolve().parents[2]
PIN='a398b07ad95aaa642fae7f991f12c57076f0e6b44c6454fa4e739effb34a2fd5'
def verify():
    from experiments.shared_state.grant_identity import verify as parent
    parent()
    try:
        raw=(ROOT/'experiments/shared_state/native-build.json').read_bytes()
        if sha256(raw).hexdigest()!=PIN:raise ValueError()
        m=json.loads(raw)
        if m['identity']!='52-native-session-reconstruction-local-v1' or m['productionActive'] or m['liveTransportAvailable']:raise ValueError()
        for f,h in m['sources'].items():
            p=ROOT/f
            if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h:raise ValueError()
        return PIN
    except (OSError,ValueError,KeyError,TypeError):raise Denied('native_build') from None
