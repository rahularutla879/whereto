"""Offline image content, least-privilege and pre-Node startup refusal checks."""
from pathlib import Path
import json,subprocess
import argparse,re
p=argparse.ArgumentParser(description='Local, offline closed frontend image acceptance; never starts a hosted service.');p.add_argument('--images',required=True);p.add_argument('--output',required=True);a=p.parse_args()
D=['docker','--context','colima-whereto-task52'];images=json.loads(Path(a.images).read_text());results={}
assert set(images)=={'production','fixture'}
assert all(re.fullmatch('sha256:[a-f0-9]{64}',m['id']) for m in images.values())
probe="""import fs from 'node:fs';import assert from 'node:assert/strict';import {FIXTURE} from './private-runtime/frontend-pin.mjs';
const i=await import('./private-runtime/identity-port-v2.mjs'),n=await import('./private-runtime/network-port-v2.mjs'),s=await import('./private-runtime/frontend-startup.mjs');
assert.notEqual(process.getuid(),0);assert(!fs.existsSync('/var/run/docker.sock'));assert(!fs.existsSync('/app/fixture'));assert(!fs.existsSync('/run/secrets/whereto-frontend.json'));assert(!fs.existsSync('/usr/local/bin/npm'));
if(!FIXTURE){assert.deepEqual(Object.keys(i),['createGoogleIdentityPort']);assert.deepEqual(Object.keys(n),['createHTTPSChannel']);assert(!fs.existsSync('./private-runtime/fixture-identity.mjs'));}
assert.deepEqual(Object.keys(s).sort(),['configuration','startPrivateFrontend']);
let count=0;function check(dir){for(const d of fs.readdirSync(dir,{withFileTypes:true})){let p=dir+'/'+d.name;if(d.isDirectory())check(p);else if(d.isFile()){const st=fs.statSync(p);assert.equal(st.uid,0);assert.equal(st.mode&0o222,0);assert(!/\\.(pem|key|sqlite)$/.test(p));count++;}}}check('/app/private-runtime');console.log(JSON.stringify({fixture:FIXTURE,checkedFiles:count,closedExports:true,nonroot:true,readonly:true}));"""
for label,m in images.items():
 r=subprocess.run(D+['run','--rm','--network','none','--platform','linux/amd64','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--entrypoint','node',m['id'],'--input-type=module','-e',probe],capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
 refused=subprocess.run(D+['run','--rm','--network','none','--platform','linux/amd64','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m',m['id']],capture_output=True,text=True,timeout=20);assert refused.returncode==78,(label,refused.stderr)
 attacks=[]
 for key,value in [('NODE_OPTIONS',"--import=data:text/javascript,console.log('PRELOAD_EXECUTED')"),('NODE_TLS_REJECT_UNAUTHORIZED','0'),('NODE_EXTRA_CA_CERTS','/untrusted'),('NODE_DEBUG','http'),('HTTP_PROXY','http://untrusted.invalid')]:
  attack=subprocess.run(D+['run','--rm','--network','none','--platform','linux/amd64','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','-e',key+'='+value,m['id']],capture_output=True,text=True,timeout=20)
  assert attack.returncode==78 and 'PRELOAD_EXECUTED' not in attack.stdout,(label,key,attack.returncode)
  attacks.append(key)
 results[label]={'image':m['id'],'inspection':json.loads(r.stdout),'unenrolledStartupExit':refused.returncode,'preNodeRefusals':attacks}
Path(a.output).write_text(json.dumps(results,indent=2)+'\n');print('Both closed image export/content/default-refusal checks passed')
