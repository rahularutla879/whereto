import test from "node:test";
import assert from "node:assert/strict";
import {spawn, type ChildProcess} from "node:child_process";
import {createServer} from "node:net";
import {readFileSync} from "node:fs";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {POST as interpret} from "../app/api/interpret/route";
import {persistenceProxy} from "./persistence-proxy";
import {generateOuting} from "./planning-client";
import {continueAdvanced} from "./advanced-planning";
import {PlanCard} from "../components/plan-card";
import {SavedCards} from "../components/saved-cards";
import {VenueDetailsSession} from "./venue-details";
import {validateSaved} from "./saved-plans";
import {EMPTY_PREFERENCES, type PlannerResult} from "./planner";

type FixtureCase = {id:string;text:string};
const cases = JSON.parse(readFileSync("scripts/task52_v51_application_cases.json","utf8")).cases as FixtureCase[];

async function fixture(legacy=false){
  const socket=createServer();
  await new Promise<void>(resolve=>socket.listen(0,"127.0.0.1",resolve));
  const port=(socket.address() as {port:number}).port;
  await new Promise<void>(resolve=>socket.close(()=>resolve()));
  const child=spawn("backend/.venv/bin/python",["-m","scripts.task52_v51_application_fixture","--port",String(port),...(legacy?["--legacy"]:[])],{
    env:{PATH:process.env.PATH, PYTHONPATH:".",NODE_ENV:"test",WHERETO_AI_WARMUP_DEV:"0"},stdio:["ignore","ignore","pipe"],
  });
  const base=`http://127.0.0.1:${port}`;
  let error="";
  child.stderr.on("data",value=>{error+=String(value).slice(0,2000);});
  for(let attempt=0;attempt<150;attempt++){
    if(child.exitCode!==null)throw new Error("Synthetic backend failed to start");
    try{if((await fetch(base+"/health")).ok)return {base,child};}catch{/* local startup */}
    await new Promise(resolve=>setTimeout(resolve,50));
  }
  await stop(child);
  throw new Error("Synthetic backend startup timed out "+error.slice(0,100));
}
async function stop(child:ChildProcess){
  if(child.exitCode!==null)return;
  await new Promise<void>(resolve=>{child.once("exit",()=>resolve());child.kill("SIGTERM");});
}
const local=(path:string,body:unknown)=>new Request("http://127.0.0.1:3027"+path,{
  method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),
});
const send:typeof fetch=async(url,init)=>{
  const path=String(url);
  const request=new Request("http://127.0.0.1:3027"+path,init);
  if(path==="/api/interpret")return interpret(request);
  if(path==="/api/plans/advanced")return persistenceProxy(path,request);
  throw new Error("Unexpected frontend operation "+path);
};
async function counts(base:string){return await (await fetch(base+"/__test/counts")).json();}
async function complete(result:PlannerResult){
  if(result.advanced?.data.questions.some(q=>q.field==="origin")){
    const point={point:{id:"Synthetic_origin",coordinates:{latitude:40.75,longitude:-73.98}},source:"manual" as const,explicitly_authorized:true as const};
    result=await continueAdvanced(result.advanced,{startingLocation:point},undefined,send);
  }
  if(result.advanced?.data.questions.some(q=>q.field==="date")){
    result=await continueAdvanced(result.advanced,{date:"2026-11-20"},undefined,send);
  }
  if(result.advanced?.data.questions.some(q=>q.field==="destination")){
    result=await continueAdvanced(result.advanced,{destination:"New York"},undefined,send);
  }
  return result;
}

test("V5.1 source → Next interpretation proxy → FastAPI sessions → synthetic routes → selected save/reopen",async()=>{
  let server=await fixture();
  const previous=process.env.BACKEND_URL;
  process.env.BACKEND_URL=server.base;
  try{
    const outcomes:Record<string,PlannerResult>={};
    const selectedCases=cases.filter(c=>c.id!=="ordinary-off").sort((a,b)=>Number(a.id==="journey-06")-Number(b.id==="journey-06"));
    for(const [index,item] of selectedCases.entries()){
      // Each independent outing owns a fresh process-local test allowance.
      // Never reset or enlarge a live session's existing provider budget.
      if(index>0){await stop(server.child);server=await fixture();process.env.BACKEND_URL=server.base;}
      const before=await counts(server.base);
      let result=await generateOuting(item.text,undefined,undefined,send);
      const unsafe=["journey-21","unsupported","ambiguous"].includes(item.id);
      if(unsafe){
        assert.equal(result.plans.length,0,item.id);
        assert.equal(result.advanced,undefined,item.id);
        const after=await counts(server.base);
        assert.equal(after.searches,before.searches,item.id);
        assert.equal(after.matrixRequests,before.matrixRequests,item.id);
        assert.equal(after.externalSends,0,item.id);
        continue;
      }
      // Explicitly provide missing context through the same typed answers used
      // by the existing form. Never insert it into the supplied extraction.
      if(item.id==="extension-repeated"&&result.advanced){
        result=await continueAdvanced(result.advanced,{startingLocation:{
          point:{id:"Synthetic_origin",coordinates:{latitude:40.75,longitude:-73.98}},
          source:"manual",explicitly_authorized:true,
        }},undefined,send);
      }
      result=await complete(result);
      assert.ok(result.plans.length>0,item.id+" "+result.message);
      assert.ok(result.plans.every(p=>["confirmed","provisional"].includes(p.feasibility)),item.id);
      const orders=result.plans.map(p=>p.advanced!.stops.map(s=>s.occurrence));
      if(item.id==="extension-partial")assert.ok(orders.every(o=>o.indexOf(0)<o.indexOf(1)&&o.includes(2)));
      else assert.ok(orders.every(o=>o.every((n,i)=>i===0||o[i-1]<n)),item.id);
      const html=renderToStaticMarkup(createElement(PlanCard,{plan:result.plans[0],index:0,detailsSession:new VenueDetailsSession()}));
      assert.match(html,/View plan/);
      assert.ok(html.includes("Synthetic")||item.id==="journey-04");
      if(item.id==="extension-repeated"){
        assert.ok(result.plans.every(p=>p.advanced!.ending==="origin"));
        assert.ok(result.plans.every(p=>p.advanced!.totalConstraint?.minutes===180));
        assert.match(html,/Total time not yet verified/);
      }
      if(item.id==="journey-04")assert.match(html,/SUNY College of Optometry/);
      assert.equal((await counts(server.base)).externalSends,0,item.id);
      outcomes[item.id]=result;
    }
    const result=outcomes["journey-06"];
    const selected=result.plans[1]??result.plans[0];
    const savedResponse=await persistenceProxy("/api/plans/save",local("/api/plans/save",{
      receipt:result.saveReceipt,accessToken:result.saveAccessToken,candidateIds:result.plans.map(p=>p.id),selectedId:selected.id,
    }));
    assert.equal(savedResponse.status,200);
    assert.equal((await savedResponse.json()).saved,true);
    const reopened=await persistenceProxy("/api/plans/reopen",local("/api/plans/reopen",{accessToken:result.saveAccessToken}));
    assert.equal(reopened.status,200);
    const saved=validateSaved(await reopened.json());
    assert.equal(saved.itineraries.length,1);
    assert.equal(saved.selectedId,selected.id);
    assert.equal(saved.itineraries[0].advanced!.journey.stops[1].requirement,"optional");
    assert.deepEqual(saved.itineraries[0].advanced!.journey.order.map(e=>[e.before,e.after]),[[0,1]]);
    const html=renderToStaticMarkup(createElement(SavedCards,{saved,venues:{},refresh(){},busy:false,message:""}));
    assert.match(html,/coffee.*optional/);
    assert.match(html,/Current timing is unverified/);
    const forged=await persistenceProxy("/api/plans/save",local("/api/plans/save",{
      receipt:result.saveReceipt,accessToken:"x".repeat(43),candidateIds:[selected.id],selectedId:selected.id,
    }));
    assert.equal(forged.status,409);
    assert.equal((await counts(server.base)).externalSends,0);
    const hostile=await fetch(server.base+"/health",{headers:{origin:"https://public.example"}});
    assert.equal(hostile.status,403);
    const injected=await interpret(local("/api/interpret",{text:cases[0].text,extraction:{},preserve_order:true}));
    assert.equal(injected.status,422);
  }finally{
    if(previous===undefined)delete process.env.BACKEND_URL;else process.env.BACKEND_URL=previous;
    await stop(server.child);
  }
});

test("legacy fixture keeps production interpretation behavior and only synthetic provider operations",async()=>{
  const server=await fixture(true);
  try{
    const optional=cases.find(c=>c.id==="journey-06")!;
    const raw=await (await fetch(server.base+"/api/interpret",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:optional.text})})).json();
    assert.deepEqual(raw.interpretation.journey.order,[]);
    assert.equal(raw.interpretation.journey.stops[1].requirement,"optional");
    assert.equal(raw.interpretation.journey.ordering,"unspecified");
    const ordinary=cases.find(c=>c.id==="ordinary-off")!;
    const response=await fetch(server.base+"/api/interpret",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:ordinary.text})});
    assert.equal(response.status,200);
    const interpreted=await response.json();
    assert.deepEqual(interpreted.request.activities,["food","bowling"]);
    assert.equal(interpreted.request.date,"2026-11-06");
    assert.equal(interpreted.advancedToken,null);
    assert.equal((await counts(server.base)).externalSends,0);
  }finally{await stop(server.child);}
});


test("local pending answers and source edits use new proof, selected saves retain the revision",async()=>{
  const server=await fixture();const previous=process.env.BACKEND_URL;process.env.BACKEND_URL=server.base;
  try{
    const source="Buy groceries and maybe stop for coffee.";
    const initial=await generateOuting(source,undefined,undefined,send);
    assert.equal(initial.plans.length,0);
    assert.ok(initial.advanced?.data.questions.some(q=>q.field==="date"));
    const unlocated=await persistenceProxy("/api/plans/advanced",local("/api/plans/advanced",{token:initial.advanced!.data.token,date:"tomorrow"}));
    assert.equal(unlocated.status,422);
    const answered=await generateOuting(source,undefined,{continuation:initial.advanced!.continuation,
      answers:{date:"2026-11-20",location:"New York"}},send);
    assert.ok(answered.plans.length);
    assert.equal((await counts(server.base)).extractions,1);
    const prefs={...EMPTY_PREFERENCES,date:"2026-11-20",location:"New York",transport:"walking" as const};
    // A changed textarea has no continuation. Its new occurrence zero is coffee.
    const edited=await generateOuting("Coffee, then groceries.",prefs,undefined,send);
    assert.ok(edited.plans.length,edited.message);
    assert.deepEqual(edited.plans[0].advanced!.stops.map(s=>s.requested),["Coffee","groceries"]);
    assert.ok(edited.plans.every(p=>p.transport==="walking"));
    const required=await generateOuting("Buy groceries and coffee.",prefs,undefined,send);
    assert.ok(required.plans.length,required.message);
    assert.ok(required.plans.every(p=>p.advanced!.stops.every(s=>s.requirement==="required")));
    const selected=required.plans[0];
    const wrong=await persistenceProxy("/api/plans/save",local("/api/plans/save",{
      receipt:answered.saveReceipt,accessToken:required.saveAccessToken,candidateIds:[selected.id],selectedId:selected.id}));
    assert.equal(wrong.status,409);
    const save=await persistenceProxy("/api/plans/save",local("/api/plans/save",{
      receipt:required.saveReceipt,accessToken:required.saveAccessToken,candidateIds:required.plans.map(p=>p.id),selectedId:selected.id}));
    assert.equal(save.status,200);
    const opened=validateSaved(await (await persistenceProxy("/api/plans/reopen",local("/api/plans/reopen",{accessToken:required.saveAccessToken}))).json());
    assert.equal(opened.itineraries.length,1);
    assert.ok(opened.itineraries[0].advanced!.journey.stops.every(s=>s.requirement==="required"));
    assert.equal((await counts(server.base)).extractions,3);
    assert.equal((await counts(server.base)).externalSends,0);
  }finally{if(previous===undefined)delete process.env.BACKEND_URL;else process.env.BACKEND_URL=previous;await stop(server.child);}
});

test("local manual mode edit reuses proved raw evidence; stale and invalid capabilities refuse",async()=>{
  const server=await fixture();const previous=process.env.BACKEND_URL;process.env.BACKEND_URL=server.base;
  try{
    const source="Buy groceries and maybe stop for coffee.";
    const prefs={...EMPTY_PREFERENCES,date:"2026-11-20",location:"New York"};
    const first=await generateOuting(source,prefs,undefined,send);
    assert.ok(first.plans.length);
    const walked=await generateOuting(source,{...prefs,transport:"walking"},{continuation:first.advanced!.continuation},send);
    assert.ok(walked.plans.length,walked.message);
    assert.notEqual(walked.advanced!.data.token,first.advanced!.data.token);
    assert.ok(walked.plans.every(p=>p.advanced!.legs.every(l=>l.mode==="walk")));
    assert.equal((await counts(server.base)).extractions,1);
    const bad=structuredClone(first.advanced!.continuation!.pending);
    (bad.interpretation as {journey:{order:unknown[]}}).journey.order=[];
    const rejected=await generateOuting(source,prefs,{continuation:{pending:bad,questions:[]}},send);
    assert.equal(rejected.plans.length,0);assert.equal(rejected.advanced,undefined);
    const invalid=await persistenceProxy("/api/plans/advanced",local("/api/plans/advanced",{token:"x".repeat(43)}));
    assert.equal(invalid.status,422);
    assert.equal((await counts(server.base)).externalSends,0);
  }finally{if(previous===undefined)delete process.env.BACKEND_URL;else process.env.BACKEND_URL=previous;await stop(server.child);}
});
