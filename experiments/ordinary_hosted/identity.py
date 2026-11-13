"""Separate source identity; no real execution grant."""
from pathlib import Path
from hashlib import sha256
import json
PIN='7b9b2998e68c2396c519e909c8988aeefd4d793ddda5dcc3cc2e15638161d21d'
def verify():
 from experiments.hosted_identity.identity import verify as parent
 parent();root=Path(__file__).resolve().parents[2];raw=(root/'experiments/ordinary_hosted/build.json').read_bytes()
 if sha256(raw).hexdigest()!=PIN:raise RuntimeError('Ordinary build mismatch')
 for p,h in json.loads(raw)['sources'].items():
  f=root/p
  if f.is_symlink() or sha256(f.read_bytes()).hexdigest()!=h:raise RuntimeError('Ordinary source mismatch')
 return PIN
