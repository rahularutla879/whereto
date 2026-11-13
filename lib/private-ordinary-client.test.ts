import test from 'node:test';import assert from 'node:assert/strict';
import {PrivateOrdinaryClient} from './private-ordinary-client';
import {EMPTY_PREFERENCES} from './planner';
const handle=(revision=1)=>({version:'52-private-ordinary-outing-v1',handle:'A'.repeat(43),revision,expiresMs:Date.now()+60000});
const pending=(revision=1)=>({privateOuting:handle(revision),questions:[{field:'date',question:'Which date?'}],issues:['date required'],interpretation:{mustNotRetain:'private raw'},pending:{interpretation:{mustNotRetain:'private raw'}}});
test('private pending answers carry exact original source and handle; no browser raw evidence',async()=>{
 const calls:{path:string;body:Record<string,unknown>}[]=[];const c=new PrivateOrdinaryClient(async(url,init)=>{calls.push({path:String(url),body:JSON.parse(String(init?.body))});return Response.json(pending(calls.length));});
 await c.interpret('Coffee',EMPTY_PREFERENCES);await c.answer({date:'2026-11-07'});
 assert.equal(calls.length,2);assert.equal(calls[1].body.text,'Coffee');assert.deepEqual(calls[1].body.preferences,EMPTY_PREFERENCES);assert.equal(calls[1].body.pending,undefined);assert.ok(calls[1].body.privateOuting);assert.equal(JSON.stringify(c.view).includes('mustNotRetain'),false);
});
test('lost response blocks further planning and never repeats a request',async()=>{
 let calls=0;const c=new PrivateOrdinaryClient(async()=>{calls++;throw Error('uncertain synthetic transport');});await c.interpret('Coffee');assert.equal(c.view.phase,'blocked');assert.equal(calls,1);await c.answer({date:'2026-11-07'});assert.equal(calls,1);assert.equal(c.view.phase,'blocked');
});
test('discard revokes current handle before allowing meaning edits; no automatic re-interpretation',async()=>{
 const paths:string[]=[];const c=new PrivateOrdinaryClient(async(url)=>{paths.push(String(url));return Response.json(paths.length===1?pending():{discarded:true});});await c.interpret('Coffee');await assert.rejects(c.interpret('Museum'));await c.discard();assert.deepEqual(paths,['/api/interpret','/api/private-ordinary/revoke']);assert.equal(c.view.phase,'empty');
});
test('late interpretation after page discard cannot revive authority',async()=>{
 let deliver!:(r:Response)=>void;const c=new PrivateOrdinaryClient(()=>new Promise<Response>(resolve=>{deliver=resolve;}));const work=c.interpret('Coffee');c.clear();deliver(Response.json(pending()));await work;assert.equal(c.view.phase,'empty');assert.equal(c.view.expiresMs,undefined);
});
test('advanced extraction never calls advanced or ordinary generation',async()=>{
 let calls=0;const c=new PrivateOrdinaryClient(async()=>{calls++;return Response.json({...pending(),questions:[],request:null,advancedToken:'unavailable'});});await c.interpret('Coffee optional');assert.equal(c.view.phase,'blocked');await c.generate(39.29,-76.61);assert.equal(calls,1);assert.match(c.view.message,/No current executable/);
});
test('read-only expiry discards authority without extending expiry or sending requests',async()=>{
 let calls=0;const c=new PrivateOrdinaryClient(async()=>{calls++;return Response.json(pending());});await c.interpret('Coffee');const expiry=c.view.expiresMs!;const before=Date.now;Date.now=()=>expiry+1;try{c.expire();assert.equal(c.view.phase,'blocked');assert.equal(c.view.expiresMs,expiry);assert.equal(calls,1);}finally{Date.now=before;}
});

test('default transport does not bind native fetch to the controller',async()=>{
 const original=globalThis.fetch;let calls=0;globalThis.fetch=async function(this:unknown){assert.notEqual(this instanceof PrivateOrdinaryClient,true);calls++;return Response.json(pending());};
 try{const c=new PrivateOrdinaryClient();await c.interpret('Coffee');assert.equal(c.view.phase,'pending');assert.equal(calls,1);}finally{globalThis.fetch=original;}
});

test('normal startup exposes no private revocation operation',async()=>{
 const {POST}=await import('../app/api/private-ordinary/revoke/route');
 const r=await POST(new Request('http://127.0.0.1/api/private-ordinary/revoke',{method:'POST',body:'{}'}));assert.equal(r.status,404);
});
test('selected UI readiness is GET-only, non-entitling, and does not expose other routes',async()=>{
 const {createOrdinaryUIProfile}=await import('./private-server-boundary');let calls=0;
 const profile=createOrdinaryUIProfile('https://front.invalid','https://backend.invalid',{async verifyAndSeal(v){assert.equal(v.path,'/api/planning-mode');assert.equal(v.method,'GET');assert.equal(v.body.length,0);return {workloadToken:'server-only',context:'proof'};}},async()=>{calls++;return Response.json({enabled:false,mode:'unavailable',privateOrdinary:{version:'52-private-ordinary-ui-v1',dependencyReady:true,financialAuthorization:false,productionReady:false}});});
 const request=new Request('https://front.invalid/api/planning-mode',{headers:{'X-Goog-IAP-JWT-Assertion':'offline-port-validates'}});const r=await profile.handle('/api/planning-mode',request);const d=await r.json();assert.equal(r.status,200);assert.equal(d.enabled,false);assert.equal(d.privateOrdinary.financialAuthorization,false);
 assert.equal((await profile.handle('/api/plans/options',request)).status,503);assert.equal((await profile.handle('/api/planning-mode',new Request(request,{method:'POST'}))).status,403);assert.equal(calls,1);
});

test('default planning window is not displayed as a source-owned time requirement',async()=>{
 const c=new PrivateOrdinaryClient(async()=>Response.json({privateOuting:handle(),questions:[],issues:[],request:{startTime:600,endTime:1440},interpretation:{time_expressions:[],cost:null}}));await c.interpret('Coffee');assert.equal(c.view.summary?.explicitTime,false);assert.equal(c.view.summary?.explicitCost,false);
});

test('synthetic summary changes presentation only; normal summary keeps its existing label',async()=>{
 const {outingDetails}=await import('../components/outing-summary');
 const c=new PrivateOrdinaryClient(async()=>Response.json({privateOuting:handle(),questions:[],issues:[],request:{activities:['coffee'],location:'Baltimore',date:'2026-11-07',transport:'walking',travel:null,startTime:600,endTime:1440},interpretation:{}}));await c.interpret('Coffee');const value=c.view.summary!;
 assert.match(Object.fromEntries(outingDetails(value,true,true)).Transport,/synthetic route evidence/);
 assert.match(Object.fromEntries(outingDetails(value,true)).Transport,/Google Maps estimates/);
 assert.equal(value.request.transport,'walking');
});
