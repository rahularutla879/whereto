"""This source profile is local test evidence, never a production dispatch grant."""
from hashlib import sha256
import json
from pathlib import Path
from experiments.shared_state.contracts import Denied

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=Path(__file__).with_name('evidence-build.json')
MANIFEST_SHA='19171e94dfe1c2d52a4d80a56035ee12519ad0b2d8201a759b4792b340913911'


def verify():
    try:
        from experiments.shared_state.action_identity import verify_build
        from experiments.shared_state.evidence_models import VERSION,canonical,model_types
        parent=verify_build();raw=MANIFEST.read_bytes()
        if sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError()
        m=json.loads(raw)
        if m['identity']!=VERSION or m['productionActive'] or m['liveTransportAvailable'] or m['realDataAdmitted']:raise ValueError()
        if m['parentIdentity']!=parent['identity']:raise ValueError()
        for name,digest in m['sources'].items():
            p=ROOT/name
            if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError()
        schema=canonical({k:v.model_json_schema() for k,v in model_types().items()})
        if sha256(schema).hexdigest()!=m['schemasSHA256']:raise ValueError()
        return m
    except (OSError,ValueError,KeyError,TypeError):raise Denied('unknown_evidence_build') from None
