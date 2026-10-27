import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { LocationControls } from "../components/location-controls";
import { SurpriseHistory } from "./surprise-history";
import { FirstPreference } from "./first-preference";
import { generateOuting, adaptRanking } from "./planning-client";
import { EMPTY_PREFERENCES,type Plan } from "./planner";
import { outingDetails } from "../components/outing-summary";

test("Surprise choice renders with no implicit lookup, permission, or landmark selection",()=>{
  let calls=0;
  const html=renderToStaticMarkup(createElement(LocationControls,{onChange(){calls++;}}));
  assert.match(html,/Surprise me!/);assert.match(html,/choose where to start/);
  assert.doesNotMatch(html,/Choose a starting area for me|Find starting areas|Share my location/);
  assert.equal((html.match(/type="radio"/g)||[]).length,3);assert.equal(calls,0);
});
test("ID-only page history expires, bounds entries and ignores ordinary plans",()=>{
  const history=new SurpriseHistory();
  const plan=(id:string,mode:"origin"|"surprise"="surprise")=>({planningMode:mode,venues:[{id,providerPlaceId:id,name:"NOT_RETAINED"}]} as Plan);
  history.record([plan("A"),plan("B","origin")],100);
  assert.deepEqual(history.ids(200),["A"]);
  history.record(Array.from({length:150},(_,i)=>plan("Place_"+i)),200);
  assert.equal(history.ids(201).length,120);
  assert.deepEqual(history.ids(600200),[]);
  history.record([plan("C")],700000);history.clear();assert.deepEqual(history.ids(700001),[]);
});
test("independent first and between editors preserve units, strictness and manual precedence",()=>{
  const first=new FirstPreference(),between=new FirstPreference();
  first.hydrate({value:20,unit:"minutes",mode:"flexible"});
  between.hydrate({value:10,unit:"minutes",mode:"strict",exclusive:true});
  between.edit({value:5,unit:"miles",mode:"flexible"});
  between.hydrate({value:10,unit:"minutes",mode:"strict",exclusive:true});
  assert.equal(first.value?.value,20);assert.equal(between.value?.unit,"miles");assert.equal(between.value?.mode,"flexible");
});
test("explicit first-constraint removal clears only the first scope; edited between preference replaces its duplicate cap",async()=>{
  let payload:Record<string,unknown>|undefined;
  const send:typeof fetch=async(url,init)=>{
    if(url==="/api/interpret")return Response.json({issues:[],notes:[],request:{activities:["bowling","food"],location:"Washington, DC",people:3,date:"2026-11-14",budget:null,travel:30,cost:"balanced",firstTravel:{value:20,unit:"minutes",mode:"strict"},maxFirstLegTravel:20,maxLegTravel:10}});
    payload=JSON.parse(init!.body as string);return Response.json({message:"fixture"},{status:422});
  };
  await generateOuting("fixture",EMPTY_PREFERENCES,{prepareOrigin:async()=>null},send);
  assert.equal(payload,undefined,"conflict must stop before publishing");
  await generateOuting("fixture",EMPTY_PREFERENCES,{prepareOrigin:async()=>({planningMode:"surprise",firstTravel:null,betweenTravel:{value:5,unit:"miles",mode:"flexible"}})},send);
  assert.equal(payload!.firstTravel,null);assert.equal(payload!.maxFirstLegTravel,null);
  assert.equal(payload!.maxLegTravel,null);assert.equal(payload!.travel,30);
  assert.equal(payload!.startingLocation,undefined);assert.equal(payload!.planningMode,"surprise");
});
test("summary describes Surprise beginning and doubled per-leg distance separately",()=>{
  const details=Object.fromEntries(outingDetails({request:{activities:["bowling","food"],location:"Washington, DC",date:"2026-11-14",people:3,cost:"balanced",planningMode:"surprise",betweenTravel:{value:5,unit:"miles",mode:"flexible"}}} as Parameters<typeof outingDetails>[0],true));
  assert.match(details.Beginning,/first activity/);
  assert.match(details["Between activities"],/5 miles; maximum 10 miles per leg/);
  assert.equal(details["First journey"],undefined);
});
test("offline Surprise HTTP pipeline has no origin, landmark or first-leg requests; mock continuation stays isolated",async()=>{
  const listener=createServer();listener.listen(0,"127.0.0.1");await once(listener,"listening");
  const address=listener.address();assert.ok(address&&typeof address==="object");
  await new Promise<void>(r=>listener.close(()=>r()));
  const base="http://127.0.0.1:"+address.port;
  const child=spawn("backend/.venv/bin/python",["-m","backend.real_fixture_server","--port",String(address.port)]);
  const post=(path:string,body:unknown)=>fetch(base+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const request={activities:["bowling","food"],location:"Baltimore",date:"2026-11-14",people:3,planningMode:"surprise",locationFirst:true};
  try{
    for(let i=0;i<100;i++){try{if((await fetch(base+"/health")).ok)break;}catch{ /* Local fixture server is starting. */ }await new Promise(r=>setTimeout(r,50));}
    const response=await post("/api/plans/generate",request);assert.equal(response.status,200);
    const raw=await response.json(),result=adaptRanking(raw);
    assert.equal(result.plans.length,3);assert.ok(result.plans.every(p=>p.firstLeg===null&&p.planningMode==="surprise"));
    const invented=structuredClone(raw);invented.provisionalPlans[0].firstLeg={minutes:5};
    assert.throws(()=>adaptRanking(invented),/cannot include an origin journey/);
    const invalidMode=structuredClone(raw);invalidMode.request.planningMode="unsupported";
    assert.throws(()=>adaptRanking(invalidMode),/Invalid planning mode/);
    const invalidDistance=structuredClone(raw);invalidDistance.provisionalPlans[0].routeEvidence[0].route.distance_meters=-1;
    assert.throws(()=>adaptRanking(invalidDistance),/Invalid route evidence/);
    const counts=await(await fetch(base+"/__test/counts")).json();
    assert.equal(counts.details,0);assert.ok(counts.elements<=36);assert.ok(counts.searches<=3);
    const conflict=await post("/api/plans/generate",{...request,firstTravel:{value:20,unit:"minutes",mode:"strict"}});
    assert.equal(conflict.status,422);assert.match((await conflict.json()).message,/first activity/);
    assert.deepEqual(await(await fetch(base+"/__test/counts")).json(),counts);
    await post("/__test/scenario",{name:"mock"});
    const mock=await post("/api/plans/generate",request);assert.equal(mock.status,200);
    const m=await mock.json();assert.ok(adaptRanking(m).plans.length);
    const more=await post("/api/plans/options",{token:m.optionsToken});assert.equal(more.status,200);
    const next=adaptRanking(await more.json());
    const signatures=new Set(adaptRanking(m).plans.map(p=>p.venues.map(v=>v.id).join("/")));
    assert.ok(next.plans.every(p=>!signatures.has(p.venues.map(v=>v.id).join("/"))));
    assert.deepEqual(await(await fetch(base+"/__test/counts")).json(),counts,"mock must not invoke any provider fixture");
    const miles=await post("/api/plans/generate",{...request,betweenTravel:{value:5,unit:"miles",mode:"strict"}});
    assert.equal(miles.status,422);assert.match((await miles.json()).message,/no road-mile evidence/);
    await post("/__test/scenario",{name:"normal"});
    const changed=await post("/api/plans/options",{token:m.optionsToken});
    assert.equal(changed.status,422);assert.match((await changed.json()).message,/mock data/);
  }finally{child.kill();await once(child,"exit");}
});
