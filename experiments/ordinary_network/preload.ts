// Test-only preload, mounted separately; never copied into the application image.
import {readFileSync,writeFileSync,appendFileSync} from 'node:fs';
import {Agent} from 'node:https';
import {createLocalJWKSet} from 'jose';
import {composeIdentityPort,type Enrollment} from '../../lib/server-identity';
import {createOrdinaryUIProfile,installPrivateProfile} from '../../lib/private-server-boundary';
import {channel} from '../../lib/server-https';
if(process.env.K_SERVICE||process.env.VERCEL||process.env.RENDER)throw Error('Offline preload only');
const data=JSON.parse(readFileSync('/app/fixture/frontend.json','utf8'));const c=data.frontend;
if(c.identityEnvironment!=='offline-hosted-contract'||!Object.values(c.googleKeys).every((v)=>typeof v==='object'&&v!==null&&'fixture' in v&&v.fixture===true))throw Error('Explicit offline trust required');
const enrollment:Enrollment={backendAudience:c.audiences.backend,iapAudience:c.iapAudience,serviceSubject:c.enrollment.frontend.sub,serviceEmail:c.enrollment.frontend.email,testers:c.testers,build:c.ordinaryBuild,environment:c.identityEnvironment,epoch:c.epoch,signingKey:c.signingKey};
const identity=composeIdentityPort(enrollment,{fixture:true,workload:createLocalJWKSet(c.googleKeys.workload),iap:createLocalJWKSet(c.googleKeys.iap),metadata:async()=>new Response(c.oidcTokens[c.audiences.backend],{headers:{'Metadata-Flavor':'Google'}})});
class MeasuredAgent extends Agent {
 createConnection(options:Parameters<Agent['createConnection']>[0],callback:Parameters<Agent['createConnection']>[1]){const start=performance.now();const socket=super.createConnection(options,callback);socket?.once('secureConnect',()=>span('frontendTLSConnect',start,true));return socket;}
}
const channels=data.network.endpoints.map((endpoint:string)=>channel({audience:c.audiences.backend,endpoint},new MeasuredAgent({keepAlive:false,maxSockets:4,maxTotalSockets:4,ca:c.caPem,rejectUnauthorized:true,minVersion:'TLSv1.2'})));
let index=0;
function span(stage:string,start:number,ok:boolean){appendFileSync('/tmp/network-spans.jsonl',JSON.stringify({stage,nanoseconds:Math.round((performance.now()-start)*1e6),ok})+'\n',{mode:0o600});}
const send:typeof fetch=async(url,init)=>{const target=index++%channels.length;writeFileSync('/tmp/last-proof.json',JSON.stringify({index:target,path:new URL(String(url)).pathname,method:init?.method,body:init?.body?Buffer.from(init.body as Uint8Array).toString('base64url'):'',headers:Object.fromEntries(new Headers(init?.headers))}),{mode:0o600});const start=performance.now();let ok=false;try{const response=await channels[target](url,init);ok=true;return response;}finally{span('frontendHTTPS',start,ok);}};
const measured={async verifyAndSeal(input:Parameters<typeof identity.verifyAndSeal>[0]){const start=performance.now();let ok=false;try{const result=await identity.verifyAndSeal(input);ok=true;return result;}finally{span('frontendIdentity',start,ok);}}};
installPrivateProfile(createOrdinaryUIProfile('https://frontend-task52-offline.run.app',c.audiences.backend,measured,send));
