"""Source identity, never execution or financial authorization."""
from pathlib import Path
from hashlib import sha256
import json
PIN='283f026a044df840564ede56d132b09cc04e7f8e8a1d24a70cef9ac5a3cae9cd'
def verify():
 from experiments.hosted_identity.identity import verify as parent
 parent();root=Path(__file__).resolve().parents[2];raw=(root/'experiments/hosted_startup/build.json').read_bytes()
 if sha256(raw).hexdigest()!=PIN:raise RuntimeError('Startup build mismatch')
 for p,h in json.loads(raw)['sources'].items():
  f=root/p
  if f.is_symlink() or sha256(f.read_bytes()).hexdigest()!=h:raise RuntimeError('Startup source mismatch')
 return PIN
