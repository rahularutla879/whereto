"""Explicit source projection; never broaden the frozen root .dockerignore."""
from pathlib import Path
import shutil,sys,json
from hashlib import sha256

def prepare(source,target):
 source,target=Path(source).resolve(),Path(target).resolve()
 if target.exists() or target==source or source in target.parents:raise ValueError('isolated build context required')
 files=[Path(x) for x in ['package.json','package-lock.json','next.config.ts','tsconfig.json','postcss.config.mjs','data/demo-plans.json','data/mock-venues.json','deployment/frontend-entry.mjs','deployment/build-identity-port.mjs','deployment/private-startup-v1.json','deployment/build-network-port.mjs','deployment/private-network-v1.json','deployment/Dockerfile.frontend-network']]
 for directory in ('app','components','lib'):
  files += [p.relative_to(source) for p in (source/directory).rglob('*') if p.is_file() and p.suffix in ('.ts','.tsx','.json','.css','.svg') and not any(x in p.name for x in ('.test.','.spec.'))]
 for p in files:
  src=source/p
  if src.is_symlink() or source not in src.resolve().parents or not src.is_file():raise ValueError('source projection')
  dst=target/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 return {str(p):sha256((source/p).read_bytes()).hexdigest() for p in files}
if __name__=='__main__':print(json.dumps(prepare(*sys.argv[1:]),sort_keys=True))
