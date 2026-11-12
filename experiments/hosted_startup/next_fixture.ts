// Local test driver, excluded from production images. No environment activation.
import {readFileSync,writeFileSync} from 'node:fs';import {createServer} from 'node:http';import {spawn} from 'node:child_process';
import next from 'next';import {createLocalJWKSet} from 'jose';
import {composeIdentityPort,type Enrollment} from '../../lib/server-identity';
import {createStatusOnlyProfile,installPrivateProfile} from '../../lib/private-server-boundary';
async function main(){
if(process.env.K_SERVICE||process.env.VERCEL||process.env.RENDER)throw Error('Local fixture only');
const data=JSON.parse(readFileSync(process.argv[2],'utf8'));const c=data.frontend;
if(c.identityEnvironment!=='offline-hosted-contract'||!Object.values(c.googleKeys).every((v)=>typeof v==='object'&&v!==null&&'fixture' in v&&v.fixture===true))throw Error('Explicit fixture required');
const enrollment:Enrollment={backendAudience:c.audiences.backend,iapAudience:c.iapAudience,serviceSubject:c.enrollment.frontend.sub,serviceEmail:c.enrollment.frontend.email,testers:c.testers,build:c.identityBuild,environment:c.identityEnvironment,epoch:c.epoch,signingKey:c.signingKey};
let metadataCalls=0,nextBackend=0;
const identity=composeIdentityPort(enrollment,{fixture:true,workload:createLocalJWKSet(c.googleKeys.workload),iap:createLocalJWKSet(c.googleKeys.iap),metadata:async()=>{metadataCalls++;return new Response(c.oidcTokens[c.audiences.backend],{headers:{'Metadata-Flavor':'Google'}});}});
const send:typeof fetch=async(url,init)=>{
 if(String(url)!==c.audiences.backend+'/health'||init?.method!=='GET'||init.redirect!=='manual')throw Error('Fixed status transport');
 const body=JSON.stringify({index:nextBackend++%2,headers:Object.fromEntries(new Headers(init.headers))});
 writeFileSync(data.capture,JSON.stringify(Object.fromEntries(new Headers(init.headers))),{mode:0o600});
 const source=`import sys,json\nfrom pathlib import Path\nfrom experiments.service_isolation.auth import TLS\np=json.load(open('/tmp/hosted-control.json'));v=json.load(sys.stdin);c=p['configs']['worker-a' if v['index']==0 else 'worker-b'];f=Path('/tmp/startup-client-ca');f.write_text(c['caPem']);conn=TLS(8098+v['index'],'worker-a.task52.invalid' if v['index']==0 else 'worker-b.task52.invalid',str(f),3);conn.request('GET','/health',headers=v['headers']);r=conn.getresponse();wire=r.read(100001);assert len(wire)<=100000;print(json.dumps({'status':r.status,'body':wire.decode()}));conn.close()`;
 return new Promise((resolve,reject)=>{const child=spawn('docker',['--context','colima-whereto-task52','exec','-i',data.client,'python','-c',source],{stdio:['pipe','pipe','pipe']});let output='';const cancel=()=>child.kill('SIGKILL');init.signal?.addEventListener('abort',cancel,{once:true});child.stdout.on('data',b=>{output+=b;if(output.length>150000)cancel();});child.on('error',reject);child.on('exit',code=>{init.signal?.removeEventListener('abort',cancel);if(code!==0||init.signal?.aborted)return reject(Error('Local bridge unavailable'));try{const r=JSON.parse(output);resolve(new Response(r.body,{status:r.status}));}catch{reject(Error('Local response'));}});child.stdin.end(body);});
};
installPrivateProfile(createStatusOnlyProfile('https://frontend-task52-offline.run.app',c.audiences.backend,identity,send));
const app=next({dev:false,dir:process.cwd()});await app.prepare();const handle=app.getRequestHandler();
const server=createServer((req,res)=>{
 if(req.headers['x-task52-local-ingress']!==data.ingress){res.writeHead(403);res.end();return;}
 void handle(req,res);
});server.listen(Number(process.argv[3]),'127.0.0.1',()=>process.stdout.write('Local Next status fixture ready\n'));
for(const signal of ['SIGTERM','SIGINT'] as const)process.on(signal,()=>{server.close();void app.close().then(()=>{process.stdout.write('Local metadata acquisitions: '+metadataCalls+'\n');process.exit(0);});});

}
void main().catch(()=>{process.stderr.write("Local Next status startup refused.\n");process.exitCode=78;});
