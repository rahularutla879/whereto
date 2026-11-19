"""Closed source identity for the new native slice, not hosted enrollment."""
from pathlib import Path
from hashlib import sha256
import json
from private_runtime.real_finance.profile import verify
ROOT=Path(__file__).resolve().parents[2]

def verify_application():
    verify();manifest=json.loads((Path(__file__).parent/'sources.json').read_bytes())
    if manifest['identity']!='52-real-native-six-role-v4' or manifest['releaseEligible'] is not False:raise ValueError('Native source enrollment changed')
    for name,h in {**manifest['inputs'],**manifest['backendOutputs']}.items():
        p=ROOT/name
        if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('Native source cohort mismatch: '+name)
    return sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()


def source_bytes(name):
    """Check an enrolled input BEFORE compiling/projecting its source bytes."""
    from experiments.shared_state.contracts import Denied
    if type(name)is not str or Path(name).is_absolute() or '..' in Path(name).parts:raise Denied('real_source_input')
    manifest=Path(__file__).parent/'sources.json'
    if manifest.is_symlink():raise Denied('real_source_input')
    doc=json.loads(manifest.read_bytes());expected=doc.get('inputs',{}).get(name);path=ROOT/name
    if doc.get('identity')!='52-real-native-six-role-v4' or type(expected)is not str or path.is_symlink():raise Denied('real_source_input')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected:raise Denied('real_source_input')
    return raw
