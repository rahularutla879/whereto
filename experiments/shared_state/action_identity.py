"""Current inactive bridge build only; never an old evaluator identity or grant."""
import hashlib
import json
from pathlib import Path
from experiments.shared_state.contracts import Denied

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=Path(__file__).with_name('action-build.json')
MANIFEST_SHA='d4a89da59cebf615f0bd1cf697c958b88974dd15288b99afa384062ba5834c8c'
IDENTITY='52-server-action-bridge-local-v4'


def verify_build():
    try:
        raw=MANIFEST.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError()
        m=json.loads(raw)
        if m['identity']!=IDENTITY or m['productionActive'] or m['liveTransportAvailable']:raise ValueError()
        for name,digest in m['sources'].items():
            path=ROOT/name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError()
        from backend.ai import Interpretation
        schema=json.dumps(Interpretation.model_json_schema(),sort_keys=True,separators=(',',':')).encode()
        if hashlib.sha256(schema).hexdigest()!=m['canonicalSchemaSHA256']:raise ValueError()
        return m
    except (OSError,ValueError,KeyError,TypeError):raise Denied('unknown_bridge_build') from None
