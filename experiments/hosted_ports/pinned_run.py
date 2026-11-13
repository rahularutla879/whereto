"""Read-only source snapshot + sealed fictional transcript; no hosted entry point."""
from pathlib import Path
import os,sys,json,subprocess,hashlib,shutil,marshal,inspect,datetime

def digest(raw):return hashlib.sha256(raw).hexdigest()
def main():
 if sys.flags.optimize or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')):raise RuntimeError('Local unoptimized verification only')
 if '--frozen' not in sys.argv:
  import tempfile
  evidence=Path(tempfile.mkdtemp(prefix='whereto-pinned-evidence-'));evidence.chmod(0o700);root=evidence/'source';root.mkdir()
  names=sorted({x for x in subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0') if x and Path(x).is_file()})
  hashes={}
  for name in names:
   p=Path(name)
   if p.is_symlink():raise RuntimeError('Source symlink')
   raw=p.read_bytes();hashes[name]=digest(raw);out=root/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
  images=Path('/tmp/task52-closed-front-images.json').read_bytes();(evidence/'closed-images.json').write_bytes(images)
  roles=Path('/tmp/continuation-private-images.json').read_bytes();(evidence/'role-images.json').write_bytes(roles)
  # Preserve old diagnostics instead of silently overwriting their /tmp paths.
  prior=evidence/'prior-output';prior.mkdir()
  for pattern in ('continuation*.json','continuation*.log','network-resource*.json'):
   for p in Path('/tmp').glob(pattern):
    if p.is_file():shutil.copyfile(p,prior/p.name)
  record={'identity':'52-immutable-post-browser-harness-v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'sourceFiles':hashes,'closedImagesSHA256':digest(images),'roleImagesSHA256':digest(roles),'python':sys.version,'scenario':['two independent owned outings','cross-factory deterministic date clarification','three provisional ordinary cards','actual closed-entry browser pending/date/origin/cards/details','discard/edit/refresh','committed reservation and INTENT','kill factory before callback/delivery','restart and attempt old action; no new dispatch'],'expectedTuple':[6845,1,0]}
  (evidence/'run-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
  for p in root.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
  root.chmod(0o555)
  Path('/tmp/task52-finish-current-run.json').write_text(json.dumps({'evidence':str(evidence),'source':str(root),'manifestSHA256':digest((evidence/'run-manifest.json').read_bytes())})+'\n')
  env={**os.environ,'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1','TASK52_PINNED_EVIDENCE':str(evidence),'TASK52_CLOSED_IMAGES':str(evidence/'closed-images.json'),'TASK52_HOSTED_PORTS_BROWSER_HOLD':'1'}
  status=subprocess.run([sys.executable,'-m','experiments.hosted_ports.pinned_run','--frozen'],cwd=root,env=env).returncode
  unchanged=all(digest((root/p).read_bytes())==sha for p,sha in hashes.items());(evidence/'source-after.json').write_text(json.dumps({'unchanged':unchanged,'exit':status})+'\n')
  if not unchanged:raise RuntimeError('Pinned harness mutated')
  raise SystemExit(status)
 evidence=Path(os.environ['TASK52_PINNED_EVIDENCE']);root=Path.cwd();manifest=json.loads((evidence/'run-manifest.json').read_text())
 if not all(digest((root/p).read_bytes())==sha for p,sha in manifest['sourceFiles'].items()):raise RuntimeError('Snapshot mismatch')
 from experiments.hosted_ports.fault_contract import assert_state
 loaded={'module':str(Path(inspect.getfile(assert_state)).relative_to(root)),'source':inspect.getsource(assert_state),'bytecodeSHA256':digest(marshal.dumps(assert_state.__code__)),'expected':[6845,1,0]};(evidence/'assertion-before.json').write_text(json.dumps(loaded,indent=2)+'\n')
 from unittest.mock import patch
 from experiments.hosted_ports import native_cluster,run_local
 from experiments.hosted_ports.finish_cluster import FinishCluster
 with patch.object(native_cluster,'Cluster',FinishCluster):run_local.main()
 if digest(marshal.dumps(assert_state.__code__))!=loaded['bytecodeSHA256']:raise RuntimeError('Loaded assertion changed')
 print('IMMUTABLE_COMBINED_VERIFICATION_PASS',flush=True)
if __name__=='__main__':main()
