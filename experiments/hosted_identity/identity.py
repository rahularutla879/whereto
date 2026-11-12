"""Separate inactive identity. No hosted enrollment or execution permission."""
from pathlib import Path
from hashlib import sha256
import json
from experiments.shared_state.contracts import Denied
PIN='afbd644bbd4af7efbe8d2ab8db18c94ff6236ee1aee25dd78effa0627dabdfa5'
ROOT=Path(__file__).resolve().parents[2]
def verify():
    from experiments.service_isolation.identity import verify as parent
    parent()
    try:
        raw=(ROOT/'experiments/hosted_identity/build.json').read_bytes()
        if sha256(raw).hexdigest()!=PIN:raise ValueError()
        m=json.loads(raw)
        if m['identity']!='52-hosted-identity-contract-offline-v1' or m['productionActive']:raise ValueError()
        for p,h in m['sources'].items():
            f=ROOT/p
            if f.is_symlink() or sha256(f.read_bytes()).hexdigest()!=h:raise ValueError()
        return PIN
    except (ValueError,KeyError,TypeError,OSError):raise Denied('hosted_identity_build') from None
