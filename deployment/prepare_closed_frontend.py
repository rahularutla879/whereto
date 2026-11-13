"""Explicit closed-entry context; never changes the frozen network projection."""
from pathlib import Path
from hashlib import sha256
import json,shutil,sys
from deployment.prepare_network_context import prepare as base
EXTRA=['deployment/frontend-private-launch.sh','deployment/Dockerfile.frontend-private','deployment/build-private-frontend.mjs','deployment/frontend-private-entry.mjs','deployment/private-role-cohort-v1.json','experiments/hosted_ports/frontend_fixture_identity.mjs']
def prepare(source,target):
 source,target=Path(source).resolve(),Path(target).resolve();values=base(source,target)
 for name in EXTRA:
  p=source/name
  if not p.is_file() or p.is_symlink():raise ValueError('Closed source missing')
  out=target/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out);values[name]=sha256(p.read_bytes()).hexdigest()
 return values
if __name__=='__main__':print(json.dumps(prepare(*sys.argv[1:]),sort_keys=True))
