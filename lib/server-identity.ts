import {identityJSON} from './identity-json';
// Server-only identity protocol. No application startup imports this factory.
import {createHash,randomBytes,createPrivateKey} from 'node:crypto';
import {SignJWT,jwtVerify,createRemoteJWKSet,decodeProtectedHeader,customFetch,type JWTVerifyGetKey,type JWTPayload} from 'jose';
export interface ServerIdentityPort {
 verifyAndSeal(input:{path:string;method:string;body:Uint8Array;assertion:string;signal:AbortSignal}):Promise<{workloadToken:string;context:string}>;
}
export type Enrollment={backendAudience:string;iapAudience:string;serviceSubject:string;serviceEmail:string;testers:readonly string[];build:string;environment:string;epoch:string;signingKey:string};
export type IdentitySources={metadata:(signal:AbortSignal)=>Promise<Response>;workload:JWTVerifyGetKey;iap:JWTVerifyGetKey;fixture:boolean};
const PUBLIC=new Set(['/api/interpret','/api/plans/generate','/api/plans/advanced','/api/plans/options','/api/plans/save','/api/plans/reopen','/api/plans/refresh','/api/venues/details','/api/starting-areas','/api/starting-places','/api/planning-mode','/health']);
export const REQUEST_ISSUER='urn:whereto:http-request-proof:v1', USER_ISSUER='urn:whereto:http-iap-forward:v1';
export const hash=(v:Uint8Array|string)=>createHash('sha256').update(v).digest('hex');
export const requestBinding=(aud:string,method:string,path:string,body:Uint8Array)=>hash(JSON.stringify([aud,method,path,hash(body)]));
const refused=()=>new Error('Private identity unavailable');
async function bounded(response:Response,maximum:number,signal:AbortSignal){
 const reader=response.body?.getReader();if(!reader)throw refused();const chunks:Uint8Array[]=[];let size=0;
 const cancel=()=>{void reader.cancel();};signal.addEventListener('abort',cancel,{once:true});
 try{while(true){signal.throwIfAborted();const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>maximum)throw refused();chunks.push(value);}signal.throwIfAborted();return Buffer.concat(chunks);}
 finally{signal.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});}
}
async function waitFor<T>(work:Promise<T>,signal:AbortSignal):Promise<T>{
 signal.throwIfAborted();return new Promise<T>((resolve,reject)=>{const cancel=()=>reject(signal.reason??refused());signal.addEventListener('abort',cancel,{once:true});work.then(v=>{signal.removeEventListener('abort',cancel);if(signal.aborted)reject(signal.reason);else resolve(v);},e=>{signal.removeEventListener('abort',cancel);reject(e);});});
}
async function verified(token:string,kind:'workload'|'iap',c:Enrollment,s:IdentitySources){
 if(typeof token!=='string'||token.length>16384)throw refused();const segments=token.split('.');if(segments.length!==3)throw refused();identityJSON(Buffer.from(segments[0],'base64url').toString('utf8'));identityJSON(Buffer.from(segments[1],'base64url').toString('utf8'));const h=decodeProtectedHeader(token);
 if(Object.keys(h).some(k=>!['alg','kid','typ'].includes(k))||typeof h.kid!=='string'||!h.kid.length||h.kid.length>128||h.typ&&h.typ!=='JWT'||!s.fixture&&h.kid.startsWith('task52-offline-'))throw refused();
 const issuer=kind==='workload'?'https://accounts.google.com':'https://cloud.google.com/iap';
 const {payload}=await jwtVerify(token,s[kind],{algorithms:[kind==='workload'?'RS256':'ES256'],issuer,audience:kind==='workload'?c.backendAudience:c.iapAudience,requiredClaims:['iss','aud','sub','iat','exp'],clockTolerance:5});
 const now=Math.floor(Date.now()/1000),max=kind==='workload'?3600:660;
 if(payload.aud!==(kind==='workload'?c.backendAudience:c.iapAudience)||!Number.isSafeInteger(payload.iat)||!Number.isSafeInteger(payload.exp)||payload.exp!<=now||payload.exp!<=payload.iat!||payload.iat!>now+5||payload.exp!>payload.iat!+max||typeof payload.sub!=='string'||!payload.sub.length||payload.sub.length>256)throw refused();
 if(kind==='workload'&&(payload.sub!==c.serviceSubject||payload.email!==c.serviceEmail||payload.email_verified!==true))throw refused();
 if(kind==='iap'&&!c.testers.includes(payload.sub))throw refused();return payload;
}
// Explicit dependency injection is for reviewed server composition, never JSON or
// browser input. Production construction below fixes both Google trust sources.
export function composeIdentityPort(config:Enrollment,s:IdentitySources):ServerIdentityPort {
 if(!Array.isArray(config.testers)||!config.testers.length||config.testers.length>1000||config.testers.some(v=>typeof v!=='string'||!v.length||v.length>256)||typeof config.signingKey!=='string'||!/^[-_A-Za-z0-9]{43}$/.test(config.signingKey)||Buffer.from(config.signingKey,'base64url').byteLength!==32)throw refused();
 const c=Object.freeze({...config,testers:Object.freeze([...config.testers])});
 if(typeof window!=='undefined'||!/^https:\/\/[^/?#@]+\/?$/.test(c.backendAudience)||!/^\/projects\/\d+\/locations\/[a-z0-9-]+\/services\/[a-z0-9-]+$/.test(c.iapAudience)||!c.testers.length||!c.serviceSubject||!c.serviceEmail||!c.environment||![c.build,c.epoch].every(v=>/^[a-f0-9]{64}$/.test(v)))throw refused();
 const key=createPrivateKey({key:Buffer.concat([Buffer.from('302e020100300506032b657004220420','hex'),Buffer.from(c.signingKey,'base64url')]),format:'der',type:'pkcs8'});
 if(key.asymmetricKeyType!=='ed25519')throw refused();
 let cached:{token:string;claims:JWTPayload}|undefined,pending:Promise<void>|undefined,nextRequest=0;
 async function load(){
  const now=Date.now();if(cached&&cached.claims.exp!*1000>now+30000)return;
  if(pending)return pending;if(now<nextRequest)throw refused();nextRequest=now+5000;cached=undefined;
  // One shared bounded acquisition; one cancelled browser must not cancel other
  // waiters. Their own request signals are checked before any dispatch.
  pending=(async()=>{const signal=AbortSignal.timeout(2000);const r=await s.metadata(signal);if(r.status!==200||r.headers.get('metadata-flavor')!=='Google')throw refused();const raw=await bounded(r,16384,signal);const token=raw.toString('utf8');if(token.trim()!==token)throw refused();const claims=await verified(token,'workload',c,s);if(claims.exp!*1000<=Date.now()+30000)throw refused();cached={token,claims};})();
  try{await pending;}finally{pending=undefined;}
 }
 async function sign(iss:string,aud:string,claims:Record<string,unknown>,exp:number){const now=Math.floor(Date.now()/1000);return new SignJWT({...claims,build:c.build,environment:c.environment,epoch:c.epoch}).setProtectedHeader({alg:'EdDSA',kid:'frontend'}).setIssuer(iss).setSubject('frontend').setAudience(aud).setIssuedAt(now).setExpirationTime(exp).setJti(randomBytes(16).toString('hex')).sign(key);}
 return Object.freeze({async verifyAndSeal(input:Parameters<ServerIdentityPort['verifyAndSeal']>[0]){
  const {path,method,body,assertion,signal}=input;signal.throwIfAborted();
  if(!PUBLIC.has(path)||method!==(['/health','/api/planning-mode'].includes(path)?'GET':'POST')||body.byteLength>(['/api/plans/save','/api/plans/reopen','/api/plans/refresh','/api/plans/advanced'].includes(path)?4096:65536)||method==='GET'&&body.byteLength)throw refused();
  const user=await waitFor(verified(assertion,'iap',c,s),signal);await waitFor(load(),signal);signal.throwIfAborted();if(!cached||cached.claims.exp!*1000<=Date.now()+30000)throw refused();
  const exp=Math.min(Math.floor(Date.now()/1000)+60,user.exp!);const forward=await sign(USER_ISSUER,'public-user-pipeline',{request:requestBinding('public-user-pipeline',method,path,body),iap:hash(assertion)},exp);
  const proof=await sign(REQUEST_ISSUER,'backend',{request:requestBinding('backend',method,path,body),oidc:hash(cached.token),iap:hash(assertion),forward:hash(forward)},exp);
  signal.throwIfAborted();return {workloadToken:cached.token,context:Buffer.from(JSON.stringify({forward,iap:assertion,proof},Object.keys({forward:1,iap:1,proof:1}).sort())).toString('base64url')};
 }});
}
export function createGoogleIdentityPort(c:Enrollment):ServerIdentityPort {
 if(!['private-staging','production'].includes(c.environment)||JSON.stringify(c).includes('task52-offline-'))throw refused();
 const network:typeof fetch=async(input,init)=>{
  const url=String(input);if(!['https://www.googleapis.com/oauth2/v3/certs','https://www.gstatic.com/iap/verify/public_key-jwk'].includes(url))throw refused();
  const signal=AbortSignal.any([...(init?.signal?[init.signal]:[]),AbortSignal.timeout(5000)]);const r=await fetch(input,{...init,signal,redirect:'manual',cache:'no-store'});
  if(r.status!==200||Number(/(?:^|,)\s*max-age=(\d+)/.exec(r.headers.get('cache-control')??'')?.[1]??0)<60)throw refused();const bytes=await bounded(r,100000,signal);identityJSON(bytes.toString('utf8'));return new Response(bytes,{status:200,headers:r.headers});
 };
 const options={timeoutDuration:5000,cooldownDuration:60000,cacheMaxAge:60000,[customFetch]:network};
 const metadata=new URL('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity');metadata.searchParams.set('audience',c.backendAudience);metadata.searchParams.set('format','full');
 return composeIdentityPort(c,{fixture:false,workload:createRemoteJWKSet(new URL('https://www.googleapis.com/oauth2/v3/certs'),options),iap:createRemoteJWKSet(new URL('https://www.gstatic.com/iap/verify/public_key-jwk'),options),metadata:signal=>fetch(metadata,{headers:{'Metadata-Flavor':'Google'},redirect:'manual',cache:'no-store',signal})});
}
