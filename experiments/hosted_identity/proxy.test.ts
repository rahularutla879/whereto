import {test} from "node:test";
import assert from "node:assert/strict";
import {createInactiveForwarder,routes,type ServerIdentityPort} from "./proxy.server";
const origin="https://frontend.example.invalid";
const identity:ServerIdentityPort={async verifyAndSeal(input){assert.equal(input.assertion,"offline-verified-by-server-port");return {workloadToken:"server-owned-not-browser",context:"scoped-user-proof"};}};
const request=(body="{}",headers:Record<string,string>={})=>new Request(origin+"/api/plans/save",{method:"POST",body,headers:{origin,"x-goog-iap-jwt-assertion":"offline-verified-by-server-port",...headers}});
test("fixed route coverage, server credentials only, no browser leakage",async()=>{
 let calls=0;const forward=createInactiveForwarder(origin,"https://backend.example.invalid",identity,async(_url,init)=>{calls++;assert.equal(init?.redirect,"manual");const h=new Headers(init?.headers);assert.equal(h.get("authorization"),"Bearer server-owned-not-browser");assert.equal(h.get("cookie"),null);assert.equal(h.get("x-user"),null);assert.equal(h.get("x-goog-authenticated-user-id"),null);return new Response("{}",{headers:{authorization:"secret","set-cookie":"bad=1"}});});
 for(const p of Object.keys(routes) as (keyof typeof routes)[]){const read=p==="/api/health"||p==="/api/planning-mode";const q=read?new Request(origin+p,{headers:{"x-goog-iap-jwt-assertion":"offline-verified-by-server-port"}}):request("{}",{cookie:"cap=untrusted","x-user":"forged","x-goog-authenticated-user-id":"forged"});const r=await forward(p,q);assert.equal(r.status,200);assert.equal(r.headers.get("authorization"),null);assert.equal(r.headers.get("set-cookie"),null);}
 assert.equal(calls,12);
 for(const status of [404,409,413,422]){const refused=createInactiveForwarder(origin,"https://backend.example.invalid",identity,async()=>new Response("private internal detail",{status}));const result=await refused("/api/plans/save",request());assert.equal(result.status,status);assert.equal((await result.json()).error,"upstream_refused");}
});
test("untrusted identity, cross-origin, missing IAP and oversize refuse before send",async()=>{
 let calls=0;const f=createInactiveForwarder(origin,"https://backend.example.invalid",identity,async()=>{calls++;throw Error();});
 for(const h of ([{authorization:"Bearer forged"},{"x-whereto-user":"alice"},{origin:"https://evil.invalid"}] as Record<string,string>[]))assert.equal((await f("/api/plans/save",request("{}",h))).status,403);
 const missing=request();missing.headers.delete("x-goog-iap-jwt-assertion");assert.equal((await f("/api/plans/save",missing)).status,401);
 assert.equal((await f("/api/plans/save",request("x".repeat(4097)))).status,413);assert.equal(calls,0);
});
test("redirect, cancellation and verifier errors have no retry or fallback",async()=>{
 let calls=0;const f=createInactiveForwarder(origin,"https://backend.example.invalid",identity,async()=>{calls++;return new Response(null,{status:307,headers:{location:"https://evil.invalid"}});});assert.equal((await f("/api/plans/save",request())).status,503);assert.equal(calls,1);
 const bad=createInactiveForwarder(origin,"https://backend.example.invalid",{async verifyAndSeal(){throw Error("do not expose tokens");}},async()=>{throw Error("must not send");});assert.equal((await bad("/api/plans/save",request())).status,503);
 const a=new AbortController();a.abort();const q=new Request(origin+"/api/plans/save",{method:"POST",body:"{}",signal:a.signal,headers:{origin,"x-goog-iap-jwt-assertion":"offline-verified-by-server-port"}});assert.equal((await f("/api/plans/save",q)).status,503);assert.equal(calls,1);
});
