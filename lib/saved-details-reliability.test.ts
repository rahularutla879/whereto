import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {SavedPlans} from "../components/saved-plans";
import {detailsFeedback,loadSavedDetails} from "./saved-details-request";
import {mergeRefreshed} from "./saved-plan-refresh";
test("compact link management keeps collapsed paste support without raw-link help",()=>{
 const html=renderToStaticMarkup(React.createElement(SavedPlans,{active:false,onOpen(){},contextKey:"new"}));
 assert.match(html,/<details><summary>Reopen another saved plan/);
 assert.doesNotMatch(html,/Link and help|Select and copy|Existing copies work/);
});
test("partial feedback identifies the shared admission limit instead of generic venue absence",()=>{
 const text=detailsFeedback({one:{status:"refreshed",name:"Invented"},two:{status:"unavailable",reason:"local_minute",message:"Shared minute limit reached."}});
 assert.match(text,/1 stop loaded/);assert.match(text,/Shared minute limit/);assert.doesNotMatch(text,/Some details are unavailable/);
});
test("failed current refresh preserves facts and recovery classification in memory",()=>{
 const updated=mergeRefreshed({one:{status:"refreshed",name:"Original"}},{one:{status:"unavailable",message:"Minute limit",retryAfterSeconds:42,reason:"local_minute",retryable:true}});
 assert.equal(updated.one.name,"Original");assert.equal(updated.one.status,"stale");assert.equal(updated.one.retryAfterSeconds,42);
});
test("one selected-option details request has a fresh UUID, no retries or extra fields",async()=>{
 const old=globalThis.fetch;const calls:RequestInit[]=[];
 globalThis.fetch=async (_url,init)=>{calls.push(init!);return Response.json({candidateId:"selected",venues:{one:{status:"refreshed",name:"Invented"}}});};
 try{
  await loadSavedDetails("A".repeat(43),"selected");
  assert.equal(calls.length,1);const data=JSON.parse(calls[0].body as string);
  assert.equal(data.includeContacts,false);assert.equal(data.candidateId,"selected");assert.match(data.refreshId,/^[a-f0-9-]{36}$/);
 }finally{globalThis.fetch=old;}
});
test("failed admission is one request and never automatically retried",async()=>{
 const old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({message:"Database unavailable"},{status:503});};
 try{await assert.rejects(loadSavedDetails("A".repeat(43),"selected"),/Database unavailable/);assert.equal(calls,1);}finally{globalThis.fetch=old;}
});
test("timing metadata forwards only numeric development measurements",async()=>{
 const {timingHeaders}=await import('./server-timing');
 assert.deepEqual(timingHeaders('backend;dur=12.5',15),{'Server-Timing':'backend;dur=12.5, proxy;dur=2.500'});
 assert.deepEqual(timingHeaders('secret arbitrary header',15),{});
 const env=process.env as Record<string,string|undefined>;const old=env.NODE_ENV;env.NODE_ENV='production';
 try{assert.deepEqual(timingHeaders('backend;dur=12.5',15),{});}finally{if(old===undefined)delete env.NODE_ENV;else env.NODE_ENV=old;}
});
