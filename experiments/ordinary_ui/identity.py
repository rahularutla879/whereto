"""New reviewed composition; never repins the frozen ordinary parent."""
from pathlib import Path
from hashlib import sha256
import json
PIN='c48e7b24d950ea3c28f767f8b49e724238c2299b60b3c2b597e42a6fcfc8f3d5'
def verify():
 from experiments.hosted_identity.identity import verify as base
 base();root=Path(__file__).resolve().parents[2]
 parent=(root/'experiments/ordinary_hosted/build.json').read_bytes()
 if sha256(parent).hexdigest()!='7b9b2998e68c2396c519e909c8988aeefd4d793ddda5dcc3cc2e15638161d21d':raise RuntimeError('Frozen parent artifact changed')
 for p,h in json.loads(parent)['sources'].items():
  if p.startswith('experiments/ordinary_hosted/') and sha256((root/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Frozen ordinary implementation changed')
 raw=(root/'experiments/ordinary_ui/build.json').read_bytes()
 if sha256(raw).hexdigest()!=PIN:raise RuntimeError('UI manifest changed')
 for p,h in json.loads(raw)['sources'].items():
  f=root/p
  if f.is_symlink() or sha256(f.read_bytes()).hexdigest()!=h:raise RuntimeError('UI source changed')
 return PIN
