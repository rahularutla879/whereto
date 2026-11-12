"""Separate fictional financial build; never a production enrollment or grant."""
from hashlib import sha256
import json
from pathlib import Path
from experiments.shared_state.contracts import Denied

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=Path(__file__).with_name('grant-build.json')
MANIFEST_SHA='f52bdd92b86806eca16491c0d81d460649a2344c8c051c105a9595887e44cfa8'
IDENTITY='52-application-financial-authority-local-v1'


def verify():
    try:
        from experiments.shared_state.evidence_identity import verify as parent
        previous=parent();raw=MANIFEST.read_bytes()
        if sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError()
        m=json.loads(raw)
        if m['identity']!=IDENTITY or m['parentIdentity']!=previous['identity'] or m['productionActive'] or m['liveTransportAvailable'] or m['realGrantEnrolled']:raise ValueError()
        for name,digest in m['sources'].items():
            p=ROOT/name
            if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError()
        return m
    except (OSError,ValueError,KeyError,TypeError):raise Denied('unknown_grant_build') from None
