from pathlib import Path
from hashlib import sha256
import json
PIN='5640cd4c898f1f87c0e5ae04e03d77934d09a3e86be2b85a58d7befbec160f7d'
def verify():
 from experiments.ordinary_ui.identity import verify as parent
 # Read the unchanged parent function directly, even when a test service replaces
 # its module export with this child verifier.
 root=Path(__file__).resolve().parents[2]
 raw=(root/'experiments/ordinary_ui/build.json').read_bytes()
 if sha256(raw).hexdigest()!='c48e7b24d950ea3c28f767f8b49e724238c2299b60b3c2b597e42a6fcfc8f3d5':raise RuntimeError('Frozen parent changed')
 for p,h in json.loads(raw)['sources'].items():
  if sha256((root/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen parent source changed')
 from experiments.hosted_identity.identity import verify as base
 base()
 raw=(root/'experiments/ordinary_network/build.json').read_bytes()
 if sha256(raw).hexdigest()!=PIN:raise RuntimeError('Network manifest changed')
 for p,h in json.loads(raw)['sources'].items():
  if (root/p).is_symlink() or sha256((root/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Network source changed')
 return PIN
