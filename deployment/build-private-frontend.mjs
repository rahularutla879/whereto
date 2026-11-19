// New derived artifact, leaving frozen identity/network source bytes untouched.
import process from 'node:process';import fs from 'node:fs';import ts from 'typescript';import {createHash} from 'node:crypto';
const root='private-runtime',fixture=process.argv.includes('--local-fixture'),real=process.argv.includes('--real-profile');fs.mkdirSync(root,{recursive:true});
const sha=v=>createHash('sha256').update(v).digest('hex');
function replace(s,a,b){if(s.split(a).length!==2)throw Error('Reviewed frontend projection changed');return s.replace(a,b);}
const inputs={},files={};
const argument=name=>{const at=process.argv.indexOf(name);return at<0?undefined:process.argv[at+1];};
const publicFile=argument('--enrollment-public-key');const publicKey=real&&publicFile?fs.readFileSync(publicFile,'utf8').trim():null;
if(real&&(!publicKey||!/^[A-Za-z0-9_-]{43}$/.test(publicKey)))throw Error('Reviewed real frontend enrollment public key required');
const cohortFile=real?'deployment/real-role-cohort-v1.json':'deployment/private-role-cohort-v1.json';let cohort;
if(real&&fixture)cohort='1'.repeat(64);
else {
 if(real){if(!fs.existsSync(cohortFile))throw Error('Reviewed real role projection required; synthetic cohort is forbidden');const d=JSON.parse(fs.readFileSync(cohortFile,'utf8'));if(d.identity!=='52-real-native-role-cohort-v1'||d.profile!=='52-real-native-six-role-v4'||d.realProviderTransport!==true||d.releaseEligible!==false||!d.outputs||typeof d.outputs!=='object')throw Error('Real role cohort refused');}
 const raw=fs.readFileSync(cohortFile);cohort=sha(raw);inputs[cohortFile]=sha(raw);
}
for(const [name,target] of [['identity-json','identity-json'],['server-identity','identity-port-v2'],['server-https','network-port-v2'],['private-server-boundary','boundary-v1'],['private-frontend-startup','frontend-startup']]){
 let s=fs.readFileSync(`lib/${name}.ts`,'utf8');inputs[`lib/${name}.ts`]=sha(s);
 if(name==='server-identity'){
  s=replace(s,'return Object.freeze({async verifyAndSeal','return Object.freeze({close(){stopped=true;cached=undefined;},async initialize(){await load();if(typeof s.iap.reload==="function")await s.iap.reload();},async verifyAndSeal');
  s=replace(s,'let cached:','let stopped=false;let cached:');s=replace(s,'async function load(){','async function load(){if(stopped)throw refused();');s=replace(s,'cached={token,claims};','if(stopped)throw refused();cached={token,claims};');
  if(!fixture)s=replace(s,'export function composeIdentityPort','function composeIdentityPort');
  for(const a of ['export const REQUEST_ISSUER','export const hash','export const requestBinding'])s=replace(s,a,a.replace('export ',''));
 }
 if(name==='server-https'){
  s="import tls from 'node:tls';\n"+s;
  if(fixture){s="import process from 'node:process';import fs from 'node:fs';\n"+s;s=replace(s,'rejectUnauthorized:true,minVersion:',"ca:fs.readFileSync('/run/secrets/local-fixture-ca.crt'),rejectUnauthorized:true,minVersion:");}
  s=replace(s,'let active=0;','let active=0,closed=false;');s=replace(s,"return async(input,init)=>{","const send=async(input:RequestInfo|URL,init?:RequestInit)=>{if(closed)throw Error('Network closed');");
  s=replace(s,'  init.signal?.throwIfAborted();active++;','  init.signal?.throwIfAborted();active++;');
  s=replace(s,' };\n}',` };\n return Object.assign(send,{close(){closed=true;agent.destroy();},async initialize(){if(closed)throw Error('Network closed');const u=new URL(c.endpoint);await new Promise<void>((resolve,reject)=>{const socket=tls.connect({host:u.hostname,port:Number(u.port||443),servername:u.hostname,rejectUnauthorized:true,minVersion:'TLSv1.2',ca:agent.options.ca},()=>{socket.end();resolve();});socket.setTimeout(2000,()=>socket.destroy(Error('Peer unavailable')));socket.once('error',reject);});}});\n}`);
  if(fixture&&real)s=s.replaceAll("fs.readFileSync('/run/secrets/local-fixture-ca.crt')","fs.readFileSync(new URL('../secrets/local-fixture-ca.crt',import.meta.url))");
  if(!fixture)s=replace(s,'export function channel','function channel');
 }
 if(name==='private-frontend-startup'){
  s=replace(s,'export function composeFrontend','function composeFrontend');s=replace(s,'export function configuration','function configuration');
  s += '\nexport {configuration};\n';
  if(fixture&&real)s=replace(s,"v.environment!=='private-staging'","v.environment!=='offline-hosted-contract'");
  if(fixture)s=replace(s,"import {createGoogleIdentityPort,type ServerIdentityPort,type Enrollment} from './server-identity';","import type {ServerIdentityPort,Enrollment} from './server-identity';\nimport {createGoogleIdentityPort} from './fixture-identity.mjs';");
 }
 for(const [a,b] of [['identity-json','identity-json'],['server-identity','identity-port-v2'],['server-https','network-port-v2'],['private-server-boundary','boundary-v1']])s=s.replaceAll(`'./${a}'`,`'./${b}.mjs'`);
 const r=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,removeComments:true},reportDiagnostics:true});if(r.diagnostics?.some(x=>x.category===ts.DiagnosticCategory.Error))throw Error('Frontend compilation refused');
 files[target+'.mjs']=r.outputText;
}
if(fixture){const name=real?'experiments/real_frontend/identity.mjs':'experiments/hosted_ports/frontend_fixture_identity.mjs';files['fixture-identity.mjs']=fs.readFileSync(name,'utf8');inputs[name]=sha(files['fixture-identity.mjs']);}
files['frontend-launch.sh']=fs.readFileSync('deployment/frontend-private-launch.sh','utf8');inputs['deployment/frontend-private-launch.sh']=sha(files['frontend-launch.sh']);
files['frontend-entry.mjs']=fs.readFileSync('deployment/frontend-private-entry.mjs','utf8');inputs['deployment/frontend-private-entry.mjs']=sha(files['frontend-entry.mjs']);inputs['deployment/build-private-frontend.mjs']=sha(fs.readFileSync('deployment/build-private-frontend.mjs'));
if(fixture&&real){files['frontend-entry.mjs']=replace(files['frontend-entry.mjs'],"const root='/app'","const root=new URL('../',import.meta.url).pathname.slice(0,-1)");files['frontend-entry.mjs']=files['frontend-entry.mjs'].replaceAll('/run/secrets/',"'+root+'/secrets/");}
if(fixture)files['frontend-entry.mjs']=replace(files['frontend-entry.mjs'],"if(!process.env.K_SERVICE||FIXTURE)","if(process.env.K_SERVICE||!FIXTURE)");
if(fixture&&real)files['frontend-entry.mjs']=replace(files['frontend-entry.mjs'],'s.uid!==0','s.uid!==process.getuid()');
for(const [p,v] of Object.entries(files))fs.writeFileSync(root+'/'+p,v);
// Include the actual built application, not only bootstrap components.
function walk(path){return fs.readdirSync(path,{withFileTypes:true}).flatMap(d=>d.isDirectory()?walk(path+'/'+d.name):d.isFile()?[path+'/'+d.name]:[]);}
for(const dir of ['app','components','lib','data'])for(const p of walk(dir))if(!/\.(test|spec)\./.test(p))inputs[p]=sha(fs.readFileSync(p));
for(const p of ['package.json','package-lock.json','next.config.ts','deployment/Dockerfile.frontend-private'])inputs[p]=sha(fs.readFileSync(p));
const app={};for(const p of walk('.next/standalone'))if(!p.includes('/node_modules/'))app[p.replace('.next/standalone/','')]=sha(fs.readFileSync(p));
for(const p of walk('.next/static'))app[p]=sha(fs.readFileSync(p));
const manifest={identity:'52-closed-private-frontend-v1',fixture,real,enrollmentPublicKey:publicKey,cohort,inputs,outputs:Object.fromEntries(Object.entries(files).map(([p,v])=>[p,sha(v)])),application:app};
const bytes=JSON.stringify(manifest,null,2)+'\n';fs.writeFileSync(root+'/frontend-build.json',bytes);fs.writeFileSync(root+'/frontend-pin.mjs',`export const PIN=${JSON.stringify(sha(bytes))};export const FIXTURE=${fixture};export const REAL=${real};export const ENROLLMENT_PUBLIC_KEY=${JSON.stringify(publicKey)};\n`);
