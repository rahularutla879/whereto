import { persistenceProxy } from "./persistence-proxy";
import test from "node:test";
import assert from "node:assert/strict";
import { fragmentToken, privateLink, preferenceText, validateSaved } from "./saved-plans";

const token = "A".repeat(43);
const doc = { version:1, saved:true, dataMode:"real", selectedId:"candidate", expiresAt:"2026-12-01", liveDetailsAvailable:false,
  constraints:{activities:["coffee","museum"]}, itineraries:[{candidateId:"candidate",fictionalMetrics:null,stops:["coffee","museum"].map((activity,position)=>({activity,position,provider:"google_places",reference:`Place_${position}`,fictional:null,start:null,end:null,duration:null}))}] };

test("private link uses only a fragment and round trips after refresh",()=>{
  const link=privateLink("http://localhost:3000",token);assert.equal(new URL(link).search,"");assert.equal(fragmentToken(new URL(link).hash),token);
});
test("malformed references cannot be opened",()=>{
  for(const hash of ["#saved=1","#saved="+token+"&other=x","#saved=../../../","?token="+token])assert.equal(fragmentToken(hash),undefined);
  assert.throws(()=>privateLink("http://localhost","guess"));
});
test("stored real plans preserve order and never imply live content",()=>{
  assert.equal(validateSaved(doc).itineraries[0].stops[1].activity,"museum");
  for(const change of [{start:600},{fictional:{name:"copied Google name"}},{provider:"other"}]){
    const changed=structuredClone(doc);Object.assign(changed.itineraries[0].stops[0],change);assert.throws(()=>validateSaved(changed));
  }
});
test("missing selected itinerary and malformed order fail safely",()=>{
  assert.throws(()=>validateSaved({...doc,selectedId:"unknown"}));
  const changed=structuredClone(doc);changed.itineraries[0].stops.reverse();assert.throws(()=>validateSaved(changed));
});
test("Strict and Flexible preferences retain their original boundary",()=>{
  assert.equal(preferenceText({value:5,unit:"minutes",mode:"strict",exclusive:true}),"Strict: under 5 minutes");
  assert.match(preferenceText({value:5,unit:"minutes",mode:"flexible",exclusive:false}),/maximum 10 minutes/);
});
test("save proxy blocks cross-origin requests before upstream access",async()=>{
  const result=await persistenceProxy("/api/plans/save",new Request("http://localhost/api/plans/save",{method:"POST",headers:{origin:"https://evil.example"},body:"{}"}));
  assert.equal(result.status,403);
});
test("save proxy bounds streaming bodies without content length",async()=>{
  const result=await persistenceProxy("/api/plans/save",new Request("http://localhost/api/plans/save",{method:"POST",body:"x".repeat(4097)}));
  assert.equal(result.status,413);
});
test("proxy sends private capability in body and only fixed upstream path",async()=>{
  const previous=globalThis.fetch;
  globalThis.fetch=(async(input,init)=>{assert.equal(String(input),"http://127.0.0.1:8000/api/plans/reopen");assert.ok(!String(input).includes(token));assert.equal(JSON.parse(init!.body as string).accessToken,token);return Response.json(doc);}) as typeof fetch;
  try{
    const response=await persistenceProxy("/api/plans/reopen",new Request("http://localhost/api/plans/reopen",{method:"POST",body:JSON.stringify({accessToken:token})}));
    assert.equal(response.status,200);assert.equal(response.headers.get("cache-control"),"no-store");assert.deepEqual(await response.json(),doc);
  }finally{globalThis.fetch=previous;}
});
test("database outages expose a fixed error and no credentials",async()=>{
  const previous=globalThis.fetch;globalThis.fetch=(async()=>{throw new Error("postgres password SECRET");}) as typeof fetch;
  try{const response=await persistenceProxy("/api/plans/save",new Request("http://localhost/api/plans/save",{method:"POST",body:"{}"}));assert.equal(response.status,503);assert.ok(!(await response.text()).includes("SECRET"));}finally{globalThis.fetch=previous;}
});
test("proxy accepts Next's mapped loopback address and actual browser Host",async()=>{
  const previous=globalThis.fetch;
  globalThis.fetch=(async(_input,init)=>{assert.equal((init!.headers as Record<string,string>)["X-WhereTo-Proxied"],"0");return Response.json(doc);}) as typeof fetch;
  try{const response=await persistenceProxy("/api/plans/reopen",new Request("http://localhost:3049/api/plans/reopen",{method:"POST",headers:{host:"127.0.0.1:3049",origin:"http://127.0.0.1:3049","x-forwarded-for":"::ffff:127.0.0.1","x-forwarded-host":"127.0.0.1:3049"},body:JSON.stringify({accessToken:token})}));assert.equal(response.status,200);}finally{globalThis.fetch=previous;}
});
test("proxy rejects public forwarding even with a local Host",async()=>{
  for(const [name,value] of [["x-forwarded-for","203.0.113.1"],["x-forwarded-host","evil.example"],["forwarded","for=127.0.0.1"]]){
    const response=await persistenceProxy("/api/plans/save",new Request("http://localhost/api/plans/save",{method:"POST",headers:{[name]:value},body:"{}"}));assert.equal(response.status,403);
  }
});

test("save proxy preserves actionable database errors and correlation evidence",async()=>{
  const previous=globalThis.fetch;
  const failure={code:"database_runtime_role_required",message:"Use the restricted saved-plan login.",correlationId:"0123456789abcdef"};
  globalThis.fetch=(async()=>Response.json(failure,{status:503})) as typeof fetch;
  try { const response=await persistenceProxy("/api/plans/save",new Request("http://localhost/api/plans/save",{method:"POST",body:"{}"}));assert.equal(response.status,503);assert.deepEqual(await response.json(),failure); } finally { globalThis.fetch=previous; }
});


test("malformed saved JSON is a validation error before contacting Python", async()=>{
  const previous=globalThis.fetch;
  globalThis.fetch=(async()=>{throw new Error("Unexpected backend call");}) as typeof fetch;
  try {
    for(const body of ["{", "[]", "null", "123"]) {
      const response=await persistenceProxy("/api/plans/reopen",new Request("http://localhost/api/plans/reopen",{method:"POST",body}));
      assert.equal(response.status,422);
      assert.equal(response.headers.get("cache-control"),"no-store");
    }
  } finally {globalThis.fetch=previous;}
});
