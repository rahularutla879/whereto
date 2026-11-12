import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair,SignJWT,exportJWK,createLocalJWKSet,jwtVerify} from 'jose';
import {randomBytes,createPrivateKey,createPublicKey} from 'node:crypto';
import {composeIdentityPort,createGoogleIdentityPort,requestBinding,hash,REQUEST_ISSUER,USER_ISSUER,type Enrollment,type IdentitySources} from './server-identity';
import {identityJSON} from './identity-json';
export async function fixture(){
 const work=await generateKeyPair('RS256'),user=await generateKeyPair('ES256');const seed=randomBytes(32),key=createPrivateKey({key:Buffer.concat([Buffer.from('302e020100300506032b657004220420','hex'),seed]),format:'der',type:'pkcs8'});
 const c:Enrollment={backendAudience:'https://backend.example.invalid',iapAudience:'/projects/0/locations/us-east4/services/frontend',serviceSubject:'synthetic-frontend',serviceEmail:'frontend@example.invalid',testers:['alice','bob'],build:'b'.repeat(64),environment:'offline-hosted-contract',epoch:'a'.repeat(64),signingKey:seed.toString('base64url')};
 const jwks={workload:{keys:[{...await exportJWK(work.publicKey),kid:'task52-offline-workload',alg:'RS256',use:'sig'}]},iap:{keys:[{...await exportJWK(user.publicKey),kid:'task52-offline-iap',alg:'ES256',use:'sig'}]}};
 async function token(kind:'workload'|'iap',changes:Record<string,unknown>={}){const now=Math.floor(Date.now()/1000);return new SignJWT({iss:kind==='workload'?'https://accounts.google.com':'https://cloud.google.com/iap',sub:kind==='workload'?c.serviceSubject:'alice',email:c.serviceEmail,email_verified:true,aud:kind==='workload'?c.backendAudience:c.iapAudience,iat:now,exp:now+(kind==='workload'?3600:600),...changes}).setProtectedHeader({alg:kind==='workload'?'RS256':'ES256',kid:'task52-offline-'+kind}).sign(kind==='workload'?work.privateKey:user.privateKey);}
 let requests=0,metadata=await token('workload');const sources:IdentitySources={fixture:true,workload:createLocalJWKSet(jwks.workload),iap:createLocalJWKSet(jwks.iap),metadata:async()=>{requests++;return new Response(metadata,{headers:{'Metadata-Flavor':'Google'}});}};
 return {c,jwks,sources,token,key,publicKey:createPublicKey(key),requests:()=>requests,setMetadata:(v:string)=>{metadata=v;}};
}
test('signed IAP, verified metadata and method/body-bound cross-service proofs',async()=>{
 const f=await fixture(),port=composeIdentityPort(f.c,f.sources),body=Buffer.from('{ "text": "coffee aur dinner" }');const assertion=await f.token('iap');const a=await port.verifyAndSeal({path:'/api/interpret',method:'POST',body,assertion,signal:new AbortController().signal});
 const ctx=JSON.parse(Buffer.from(a.context,'base64url').toString());const proof=(await jwtVerify(ctx.proof,f.publicKey,{issuer:REQUEST_ISSUER,audience:'backend'})).payload;const user=(await jwtVerify(ctx.forward,f.publicKey,{issuer:USER_ISSUER,audience:'public-user-pipeline'})).payload;
 assert.equal(proof.request,requestBinding('backend','POST','/api/interpret',body));assert.equal(proof.oidc,hash(a.workloadToken));assert.equal(user.iap,hash(assertion));assert.notEqual(proof.request,requestBinding('backend','POST','/api/interpret',Buffer.from('{}')));assert.notEqual(proof.request,requestBinding('backend','GET','/api/interpret',body));
});
test('concurrent cache uses one verified audience-specific acquisition and immutable enrollment',async()=>{
 const f=await fixture(),port=composeIdentityPort(f.c,f.sources),assertion=await f.token('iap');const input={path:'/health',method:'GET',body:new Uint8Array(),assertion,signal:new AbortController().signal};await Promise.all(Array.from({length:30},()=>port.verifyAndSeal(input)));assert.equal(f.requests(),1);f.c.backendAudience='https://forged.invalid';await port.verifyAndSeal(input);assert.equal(f.requests(),1);
});
test('cached token refreshes before expiry without reusing stale financial identity',async()=>{
 const f=await fixture();f.setMetadata(await f.token('workload',{exp:Math.floor(Date.now()/1000)+35}));const port=composeIdentityPort(f.c,f.sources),input={path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap'),signal:new AbortController().signal};await port.verifyAndSeal(input);assert.equal(f.requests(),1);
 f.setMetadata(await f.token('workload'));const now=Date.now;Date.now=()=>now()+6000;try{await port.verifyAndSeal(input);assert.equal(f.requests(),2);}finally{Date.now=now;}
});
test('missing/wrong audience, subject, expiry and metadata flavor refuse with bounded refresh',async()=>{
 for(const changes of [{aud:'wrong'},{sub:'wrong'},{exp:Math.floor(Date.now()/1000)-1},{iat:Math.floor(Date.now()/1000)+120},{email_verified:false}]){const f=await fixture();f.setMetadata(await f.token('workload',changes));const port=composeIdentityPort(f.c,f.sources);const input={path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap'),signal:new AbortController().signal};await assert.rejects(port.verifyAndSeal(input));await assert.rejects(port.verifyAndSeal(input));assert.equal(f.requests(),1);}
 const f=await fixture();for(const metadata of [async()=>new Response('',{status:404}),async()=>new Response('not-an-identity'),async()=>{throw Error('unavailable');}]){await assert.rejects(composeIdentityPort(f.c,{...f.sources,metadata}).verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap'),signal:new AbortController().signal}));}
});
test('IAP issuer/audience/principal/signature/expiry are independently verified before metadata',async()=>{
 const f=await fixture();for(const change of [{iss:'https://accounts.google.com'},{aud:'wrong'},{sub:'mallory'},{exp:1}]){await assert.rejects(composeIdentityPort(f.c,f.sources).verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap',change),signal:new AbortController().signal}));}assert.equal(f.requests(),0);
 const token=await f.token('iap');const [h,p,s]=token.split('.');const bytes=Buffer.from(s,'base64url');bytes[0]^=1;await assert.rejects(composeIdentityPort(f.c,f.sources).verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion:h+'.'+p+'.'+bytes.toString('base64url'),signal:new AbortController().signal}));
});
test('unknown methods, paths, oversized bytes and cancelled requests never acquire metadata',async()=>{
 const f=await fixture(),port=composeIdentityPort(f.c,f.sources),base={path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap'),signal:new AbortController().signal};for(const d of [{path:'/sign'},{method:'POST'},{path:'/api/interpret',method:'POST',body:new Uint8Array(65537)},{path:'/api/plans/save',method:'POST',body:new Uint8Array(4097)}])await assert.rejects(port.verifyAndSeal({...base,...d}));const a=new AbortController();a.abort();await assert.rejects(port.verifyAndSeal({...base,signal:a.signal}));assert.equal(f.requests(),0);
 const other=await fixture();let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>{release=r;}),begun=new Promise<void>(r=>{started=r;});const metadata=other.sources.metadata;other.sources.metadata=async signal=>{started();await gate;return metadata(signal);};const shared=composeIdentityPort(other.c,other.sources),cancel=new AbortController(),valid={...base,assertion:await other.token('iap')};const first=shared.verifyAndSeal({...valid,signal:cancel.signal});await begun;const second=shared.verifyAndSeal(valid);cancel.abort();await assert.rejects(first);release();await second;assert.equal(other.requests(),1);
});
test('default Google constructor rejects local fixture keys before any metadata/JWKS call',async()=>{
 const f=await fixture();assert.throws(()=>createGoogleIdentityPort(f.c));const original=globalThis.fetch;let calls=0;globalThis.fetch=async()=>{calls++;throw Error('No identity endpoints');};try{const port=createGoogleIdentityPort({...f.c,environment:'private-staging'});await assert.rejects(port.verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion:await f.token('iap'),signal:new AbortController().signal}));assert.equal(calls,0);assert.equal(f.requests(),0);}finally{globalThis.fetch=original;}
});
test('identity JSON rejects duplicate keys, malformed or executable-looking input and depth',()=>{
 for(const s of ['{"sub":"alice","sub":"bob"}','{"a":{"x":1,"x":2}}','[1,]','{} trailing','NaN','(()=>{})()', '['.repeat(34)+'0'+']'.repeat(34)])assert.throws(()=>identityJSON(s));assert.deepEqual(identityJSON(JSON.stringify({a:[true,null,'x"y']})),{a:[true,null,'x"y']});
});
