import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import process from 'node:process';
import {PIN,FIXTURE} from './frontend-pin.mjs';
import {configuration,startPrivateFrontend} from './frontend-startup.mjs';
const root='/app',sha=v=>createHash('sha256').update(v).digest('hex');let runtime;
function sealed(file,maximum){const s=fs.lstatSync(file);if(!s.isFile()||s.uid!==0||(s.mode&0o222)!==0||s.size>maximum)throw Error('Enrollment');return fs.readFileSync(file);}
try{
 if(!process.env.K_SERVICE||FIXTURE)throw Error('Hosted enrollment');
 if(['NODE_OPTIONS','NODE_PATH','NODE_EXTRA_CA_CERTS','NODE_TLS_REJECT_UNAUTHORIZED'].some(k=>process.env[k])||Object.entries(process.env).some(([k,v])=>k.startsWith('WHERETO_')&&k.endsWith('_DEV')&&v&&v!=='0')||Object.keys(process.env).some(k=>/^NEXT_PUBLIC_.*(?:KEY|SECRET|TOKEN|PASSWORD|DATABASE|SUPABASE|DB_)/i.test(k)))throw Error('Unsafe environment');
 const raw=sealed(root+'/private-runtime/frontend-build.json',1000000);if(sha(raw)!==PIN)throw Error('Build');const manifest=JSON.parse(raw);
 if(manifest.fixture!==FIXTURE||manifest.identity!=='52-closed-private-frontend-v1')throw Error('Build');
 for(const [base,files] of [[root+'/private-runtime',manifest.outputs],[root,manifest.application]])for(const [name,expected] of Object.entries(files)){
  if(path.isAbsolute(name)||name.split('/').some(x=>x==='..'))throw Error('Path');const file=path.join(base,name);if(sha(sealed(file,20000000))!==expected)throw Error('Source');
 }
 const c=configuration(sealed('/run/secrets/whereto-frontend.json',65536),sealed('/run/secrets/whereto-frontend-enrollment.json',4096),PIN,manifest.cohort);
 runtime=startPrivateFrontend(c);await runtime.start();
 const port=process.env.PORT??'8080';if(!/^\d+$/.test(port)||+port<1||+port>65535)throw Error('Port');
 process.env.NODE_ENV='production';process.env.HOSTNAME='0.0.0.0';process.env.PORT=port;
 process.once('SIGTERM',()=>runtime.close());process.once('SIGINT',()=>runtime.close());
 await import('../server.js');
}catch{runtime?.close();process.stderr.write('Private frontend startup refused: verified enrollment, identity and network required.\n');process.exitCode=78;}
