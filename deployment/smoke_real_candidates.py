"""Actual local image checks. No network, enrollment or runtime secret mounts."""
from pathlib import Path
import json,subprocess,sys
P=Path(sys.argv[1]).resolve();D=['docker','--context','colima-whereto-task52'];images=json.loads((P/'images.json').read_bytes());results={};expected=__import__('hashlib').sha256((P/'roles/cohort.json').read_bytes()).hexdigest()
for role,item in images.items():
 image=item['image'];base=D+['run','--rm','--platform','linux/amd64','--read-only','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','1','--pids-limit','128']
 refusal=subprocess.run(base+[image],capture_output=True,text=True,timeout=30)
 assert refusal.returncode==78,(role,'unenrolled startup did not refuse',refusal.returncode)
 if role=='frontend':
  code="const fs=require('fs');const m=JSON.parse(fs.readFileSync('/app/private-runtime/frontend-build.json'));if(m.fixture||!m.real||m.enrollmentPublicKey!==null)process.exit(2);if(fs.statSync('/app/server.js').mode&0o222)process.exit(3);console.log(JSON.stringify({node:process.version,uid:process.getuid(),next:require('/app/node_modules/next/package.json').version,cohort:m.cohort,artifact:require('crypto').createHash('sha256').update(fs.readFileSync('/app/private-runtime/frontend-build.json')).digest('hex'),fixture:m.fixture,real:m.real,publicTrustEnrolled:m.enrollmentPublicKey!==null}));"
  run=subprocess.run(base+['--entrypoint','node',image,'-e',code],capture_output=True,text=True,timeout=30)
 else:
  code="from private_runtime.image_identity import verify\nfrom private_runtime.real_application.identity import verify_application\nfrom private_runtime.image_build import ROLE\nimport os,sys,json,pathlib\nassert not pathlib.Path('/testing').exists()\nassert not list(pathlib.Path('/app/source-proof').rglob('*.py'))\nassert not pathlib.Path('/app/experiments/real_images').exists()\nassert not pathlib.Path('/app/private_runtime/real_application/test_services.py').exists()\nassert not pathlib.Path('/app/private_runtime/real_application/run_native.py').exists()\nassert not pathlib.Path('/app/private_runtime/entry.py').stat().st_mode&0o222\nprint(json.dumps(dict(role=ROLE,cohort=verify(),native=verify_application(),python=sys.version.split()[0],uid=os.getuid())))"
  run=subprocess.run(base+['--entrypoint','python',image,'-c',code],capture_output=True,text=True,timeout=30)
 assert run.returncode==0,(role,'image check failed',run.stderr)
 value=json.loads(run.stdout);assert value['uid']!=0;assert value['cohort']==expected
 if role=='frontend':assert value['next']=='16.4.5'
 assert (value['node'].startswith('v24.') if role=='frontend' else value['python'].startswith('3.12.'))
 results[role]=dict(image=image,unenrolledStartupExit=refusal.returncode,closedStartupMessage=refusal.stderr.strip() or refusal.stdout.strip(),verified=value,readOnly=True,network='none',capabilitiesDropped='ALL',fixtureMounts=False)
 (P/'smoke.json').write_text(json.dumps(results,indent=2)+'\n');print(role,'PASS',flush=True)
