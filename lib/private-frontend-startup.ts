// Server-only composition, bundled only by the separate private frontend image.
import {createHash,createPublicKey,verify} from 'node:crypto';
import {identityJSON} from './identity-json';
import {createGoogleIdentityPort,type ServerIdentityPort,type Enrollment} from './server-identity';
import {createHTTPSChannel} from './server-https';
import {createOrdinaryUIProfile,createRealOrdinaryUIProfile,installPrivateProfile} from './private-server-boundary';
export type ReadyIdentity=ServerIdentityPort&{initialize():Promise<void>;close?():void};
export type ManagedChannel=typeof fetch&{close():void;initialize():Promise<void>};
type Configuration=Enrollment&{version:string;origin:string;backendEndpoint:string};
const fail=()=>new Error('Private frontend enrollment unavailable');
const digest=(v:Uint8Array|string)=>createHash('sha256').update(v).digest('hex');
function exact(v:unknown,keys:string[]):asserts v is Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join()!==keys.sort().join())throw fail();}
export function configuration(raw:Uint8Array,approvalRaw:Uint8Array,artifact:string,cohort:string):Readonly<Configuration>{
 if(raw.byteLength>65536||approvalRaw.byteLength>4096)throw fail();
 const v=identityJSON(Buffer.from(raw).toString('utf8')),a=identityJSON(Buffer.from(approvalRaw).toString('utf8'));
 exact(v,['version','origin','backendEndpoint','backendAudience','iapAudience','serviceSubject','serviceEmail','testers','build','environment','epoch','signingKey']);
 exact(a,['version','artifact','configurationSHA256','purpose','publicTraffic','financialAuthorization']);
 if(a.version!=='52-private-frontend-enrollment-v1'||a.artifact!==artifact||a.configurationSHA256!==digest(raw)||a.purpose!=='private-synthetic-ordinary-only'||a.publicTraffic!==false||a.financialAuthorization!==false)throw fail();
 return validateValues(v,cohort,'52-closed-private-frontend-v1');
}
function validateValues(v:Record<string,unknown>,cohort:string,version:string):Readonly<Configuration>{
 exact(v,['version','origin','backendEndpoint','backendAudience','iapAudience','serviceSubject','serviceEmail','testers','build','environment','epoch','signingKey']);
 if(v.version!==version||v.environment!=='private-staging'||v.build!==cohort||![v.build,v.epoch].every(x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x)))throw fail();
 for(const value of [v.origin,v.backendEndpoint,v.backendAudience]){if(typeof value!=='string')throw fail();const u=new URL(value);if(u.protocol!=='https:'||u.origin!==value||u.username||u.password||u.search||u.hash)throw fail();}
 if(typeof v.iapAudience!=='string'||!/^\/projects\/\d+\/locations\/[a-z0-9-]+\/services\/[a-z0-9-]+$/.test(v.iapAudience)||typeof v.serviceSubject!=='string'||!/^\d{10,30}$/.test(v.serviceSubject)||typeof v.serviceEmail!=='string'||!/^[-a-z0-9]+@[-a-z0-9]+\.iam\.gserviceaccount\.com$/.test(v.serviceEmail))throw fail();
 if(!Array.isArray(v.testers)||!v.testers.length||v.testers.length>1000||v.testers.some(x=>typeof x!=='string'||!x.length||x.length>256)||new Set(v.testers).size!==v.testers.length||typeof v.signingKey!=='string'||!/^[-_A-Za-z0-9]{43}$/.test(v.signingKey))throw fail();
 return Object.freeze({...v,testers:Object.freeze([...v.testers])}) as unknown as Readonly<Configuration>;
}
export function realConfiguration(raw:Uint8Array,approvalRaw:Uint8Array,artifact:string,cohort:string,publicKey:string):Readonly<Configuration>{
 if(raw.byteLength>65536||approvalRaw.byteLength>4096||!/^[A-Za-z0-9_-]{43}$/.test(publicKey))throw fail();
 const v=identityJSON(Buffer.from(raw).toString('utf8')),a=identityJSON(Buffer.from(approvalRaw).toString('utf8'));
 exact(a,['version','artifact','configurationSHA256','purpose','publicTraffic','financialAuthorization','signature']);
 if(a.version!=='52-real-frontend-enrollment-v1'||a.artifact!==artifact||a.configurationSHA256!==digest(raw)||a.purpose!=='private-real-ordinary-only'||a.publicTraffic!==false||a.financialAuthorization!==false||typeof a.signature!=='string'||!/^[A-Za-z0-9_-]{86}$/.test(a.signature))throw fail();
 const key=createPublicKey({key:Buffer.concat([Buffer.from('302a300506032b6570032100','hex'),Buffer.from(publicKey,'base64url')]),format:'der',type:'spki'});
 if(!verify(null,Buffer.from(JSON.stringify([a.version,a.artifact,a.configurationSHA256,a.purpose,false,false])),key,Buffer.from(a.signature,'base64url')))throw fail();
 if(!v||typeof v!=='object'||Array.isArray(v))throw fail();
 return validateValues(v as Record<string,unknown>,cohort,'52-closed-real-frontend-v1');
}
export type Dependencies={identity:(c:Enrollment)=>ReadyIdentity;network:(c:{audience:string;endpoint:string})=>ManagedChannel;install:typeof installPrivateProfile};
// Only trusted test code may inject ports. This export is removed from the image.
export function composeFrontend(c:Readonly<Configuration>,dependencies:Dependencies,real=false){
 let state:'new'|'starting'|'ready'|'closed'='new';let pending:Promise<void>|undefined;let network:ManagedChannel|undefined;let identity:ReadyIdentity|undefined;
 return Object.freeze({start(){
  if(state==='starting')return pending!;if(state!=='new')return Promise.reject(fail());state='starting';
  pending=(async()=>{try{identity=dependencies.identity(c);network=dependencies.network({audience:c.backendAudience,endpoint:c.backendEndpoint});await identity.initialize();await network.initialize();if(state!=='starting')throw fail();dependencies.install((real?createRealOrdinaryUIProfile:createOrdinaryUIProfile)(c.origin,c.backendAudience,identity,network));state='ready';}catch{state='closed';network?.close();identity?.close?.();throw fail();}})();return pending;
 },close(){state='closed';network?.close();identity?.close?.();},status(){return state;}});
}
export function startPrivateFrontend(c:Readonly<Configuration>){
 return composeFrontend(c,{identity:v=>createGoogleIdentityPort(v) as ReadyIdentity,network:v=>createHTTPSChannel(v) as ManagedChannel,install:installPrivateProfile});
}

export function startRealFrontend(c:Readonly<Configuration>){
 return composeFrontend(c,{identity:v=>createGoogleIdentityPort(v) as ReadyIdentity,network:v=>createHTTPSChannel(v) as ManagedChannel,install:installPrivateProfile},true);
}
