"""Closed source identity for the new native slice, not hosted enrollment."""
from pathlib import Path
from hashlib import sha256
import json
from private_runtime.real_finance.profile import verify
ROOT=Path(__file__).resolve().parents[2]

def verify_application():
    verify();manifest=json.loads((Path(__file__).parent/'sources.json').read_bytes())
    if manifest['identity']!='52-real-native-ordinary-slice-v1' or manifest['releaseEligible'] is not False:raise ValueError('Native source enrollment changed')
    for name,h in {**manifest['inputs'],**manifest['backendOutputs']}.items():
        p=ROOT/name
        if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('Native source cohort mismatch: '+name)
    return sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
