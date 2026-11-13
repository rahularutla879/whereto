import test from 'node:test';import assert from 'node:assert/strict';
import {privateOuting} from './private-outing';
import {generateOuting,type PendingOuting} from './planning-client';
import {createOrdinaryProfile} from './private-server-boundary';
const handle=()=>({version:'52-private-ordinary-outing-v1' as const,handle:'A'.repeat(43),revision:1,expiresMs:Date.now()+60000});
test('opaque private ownership is versioned, bounded and optional; malformed/expired values refuse',()=>{
 assert.equal(privateOuting(undefined),undefined);const v=handle();assert.deepEqual(privateOuting(v),v);
 for(const v of [{...handle(),version:'other'},{...handle(),handle:'graph'},{...handle(),revision:0},{...handle(),expiresMs:1},{...handle(),root:'chosen'}])assert.throws(()=>privateOuting(v));
});
test('actual browser client retains tab-local ownership and sends answers without raw pending evidence',async()=>{
 let pending:PendingOuting|null=null;const owned=handle(),bodies:Record<string,unknown>[]=[];
 const send:typeof fetch=async(_url,init)=>{bodies.push(JSON.parse(String(init?.body)));return Response.json({privateOuting:owned,issues:['Date required'],notes:[],questions:[{field:'date',question:'Which date?',kind:'essential'}],pending:{text:'Coffee',interpretation:{activities:['coffee']},answers:{},referenceTime:'2026-11-02T13:00:00Z'}});};
 await generateOuting('Coffee',undefined,{onClarification:v=>{pending=v;}},send);assert.ok(pending);assert.deepEqual((pending as PendingOuting).privateOuting,owned);
 await generateOuting('Coffee',undefined,{continuation:pending,answers:{date:'2026-11-07'}},send);assert.deepEqual(bodies[1].privateOuting,owned);assert.equal(bodies[1].pending,undefined);assert.deepEqual(bodies[1].answers,{date:'2026-11-07'});assert.equal(bodies.length,2);
});
test('selected ordinary proxy seals exact bytes, strips credentials, and keeps every other route blocked',async()=>{
 let sent=0;const raw='{ "text" : "Coffee" }';const port={async verifyAndSeal(v:{body:Uint8Array}){assert.equal(Buffer.from(v.body).toString(),raw);return {workloadToken:'server-only',context:'sealed'};}};
 const profile=createOrdinaryProfile('https://front.invalid','https://backend.invalid',port,async(_url,init)=>{sent++;assert.equal(new Headers(init?.headers).get('authorization'),'Bearer server-only');assert.equal(init?.redirect,'manual');assert.equal(Buffer.from(init?.body as Uint8Array).toString(),raw);return Response.json({privateOuting:handle(),issues:[],notes:[]},{headers:{'set-cookie':'secret'}});});
 const request=(headers={})=>new Request('https://front.invalid/api/interpret',{method:'POST',body:raw,headers:{Origin:'https://front.invalid','X-Goog-IAP-JWT-Assertion':'server-verifies-this',...headers}});
 const response=await profile.handle('/api/interpret',request());assert.equal(response.status,200);assert.equal(response.headers.get('set-cookie'),null);
 for(const h of [{Origin:'https://evil.invalid'},{Authorization:'forged'},{'X-Goog-IAP-JWT-Assertion':''}])assert.notEqual((await profile.handle('/api/interpret',request(h))).status,200);
 assert.equal((await profile.handle('/api/plans/options',request())).status,503);assert.equal(sent,1);
});
test('body read timeout refuses valid-looking partial input before sealing or dispatch',async()=>{
 let seals=0,sends=0;const profile=createOrdinaryProfile('https://front.invalid','https://backend.invalid',{async verifyAndSeal(){seals++;return {workloadToken:'unused',context:'unused'};}},async()=>{sends++;return Response.json({issues:[],notes:[]});});
 const keepAlive=setTimeout(()=>{},7000);
 try{
  const stream=new ReadableStream<Uint8Array>({start(c){c.enqueue(new TextEncoder().encode('{"text":"Coffee"}'));}});
  const init={method:'POST',body:stream,duplex:'half',headers:{Origin:'https://front.invalid','X-Goog-IAP-JWT-Assertion':'unused'}} as RequestInit&{duplex:'half'};
  const response=await profile.handle('/api/interpret',new Request('https://front.invalid/api/interpret',init));assert.equal(response.status,503);assert.equal(seals,0);assert.equal(sends,0);
 }finally{clearTimeout(keepAlive);}
});
