import {StartingConfirmation} from "./starting-confirmation";
import test from "node:test";
import assert from "node:assert/strict";
import {currentRelative,explicitOrigin,recoveryCode} from "./destination-context";
import {generateOuting,type LocationContext} from "./planning-client";
import {EMPTY_PREFERENCES,type PlannerResult} from "./planner";
import {requestLocation} from "./location";
import {ItineraryPages} from "./itinerary-pages";
import demo from "../data/demo-plans.json";

test("relative destination paraphrases and named-destination precedence",()=>{
  for(const words of ["near me","around me","around here","nearby","in my area","near my current location","around my location","close to me"]){
    assert.equal(currentRelative("Dinner "+words),true);
  }
  for(const text of ["Dinner near my friend","Dinner near me in manhattan","Dinner in Midtown Manhattan","Dinner in Hyderabad","Dinner near me in the Bronx"])assert.equal(currentRelative(text),false);
  assert.equal(currentRelative("Dinner near me in the evening"),true);
  assert.equal(explicitOrigin("Dinner near me, starting from Bryant Park."),"Bryant Park");
});
test("submission preflight obtains nearby permission before interpretation, preserving separate manual origin",async()=>{
  const events:string[]=[];
  const context:LocationContext={planningMode:"origin",calendarTimezone:"Asia/Kolkata",
    startingLocation:{point:{id:"authorized-start",coordinates:{latitude:0,longitude:0}},explicitly_authorized:true,source:"manual",label:"Synthetic confirmed place"},
    currentArea:{coordinates:{latitude:1,longitude:1}}};
  const send:typeof fetch=async(path,init)=>{
    events.push(String(path));
    const body=JSON.parse(String(init?.body));
    if(path==="/api/interpret"){
      assert.equal(body.hasCurrentLocation,true);assert.equal(body.calendarTimezone,"Asia/Kolkata");
      return Response.json({issues:[],notes:[],request:{location:"near me",activities:["food","drinks"],people:2,date:"2026-11-07",
        budget:null,travel:null,groupBudget:null,maxLegTravel:null,cost:"balanced",startTime:600,endTime:1440,transport:"driving",dinnerStops:[0],
        calendarTimezone:"Asia/Kolkata",explicitStart:false,explicitEnd:false}});
    }
    assert.equal(body.startingLocation.source,"manual");
    assert.notDeepEqual(body.currentArea.coordinates,body.startingLocation.point.coordinates);
    assert.equal(body.date,"2026-11-07");
    return Response.json({code:"destination_unresolved",message:"Confirm the search area."},{status:422});
  };
  const result=await generateOuting("Plan dinner and drinks around me today for 2 people, starting from Bryant Park.",EMPTY_PREFERENCES,{
    prepareOrigin:async input=>{
      events.push(input.destinationRelative?"permission":"confirmed-origin");
      if(input.destinationRelative)assert.equal(input.manualOriginText,"Bryant Park");
      return context;
    }
  },send);
  assert.deepEqual(events,["permission","/api/interpret","confirmed-origin","/api/plans/generate"]);
  assert.equal(result.recoveryCode,"destination_unresolved");
});
test("denied preflight preserves request without invoking interpretation or providers",async()=>{
  let prepared=0,sent=0;
  const result=await generateOuting("Dinner around me today for 2 people",EMPTY_PREFERENCES,{
    prepareOrigin:async()=>{prepared++;return null;}
  },async()=>{sent++;throw Error("Unexpected request");});
  assert.equal(prepared,1);assert.equal(sent,0);assert.equal(result.requestFailed,false);
  assert.match(result.message,/manual nearby search area/);
});
test("named destination does not perform a location preflight",async()=>{
  let preparation=0;
  await generateOuting("Dinner in Midtown Manhattan tomorrow for 2 people",EMPTY_PREFERENCES,{
    prepareOrigin:async()=>{preparation++;return null;}
  },async()=>Response.json({issues:["Date needs clarification"],notes:[],request:null}));
  assert.equal(preparation,0);
});
test("permission errors distinguish denial, unavailable and timeout and never infer an origin",async()=>{
  for(const [code,message] of [[1,/denied/],[2,/unavailable/],[3,/timed out/]] as const){
    await assert.rejects(requestLocation({getCurrentPosition(_success,error){error?.({code} as GeolocationPositionError);}},true),message);
  }
});
test("expiry classifications preserve saved pages and unknown codes are not exposed",()=>{
  const pages=new ItineraryPages();const first=structuredClone(demo) as PlannerResult;
  pages.append(first);
  const second=structuredClone(first);
  second.plans=second.plans.map(p=>({...p,venues:p.venues.map(v=>({...v,id:v.id+"-next"}))}));
  pages.append(second);
  for(const code of ["expired","outing_date_expired","outing_time_expired"]){
    assert.equal(recoveryCode(code),code);
    assert.equal(pages.navigate(-1)?.plans[0].date,first.plans[0].date);
    assert.equal(pages.navigate(1)?.plans.length,3);
  }
  assert.equal(pages.pages.length,2);
  assert.equal(recoveryCode("secret-provider-error"),undefined);
});


test("manual fallback confirmation resumes the same pending nearby submission without retyping",async()=>{
  const pending=new StartingConfirmation();let requests=0;let ready=false;
  const original="Dinner and drinks around me today for 2 people";
  const running=generateOuting(original,EMPTY_PREFERENCES,{
    prepareOrigin:async input=>{
      if(input.destinationRelative){ready=true;return pending.wait();}
      return {planningMode:"origin",startingLocation:{point:{id:"authorized-start",coordinates:{latitude:0,longitude:0}},explicitly_authorized:true,source:"manual"}};
    }
  },async(_path,init)=>{
    requests++;
    const body=JSON.parse(String(init?.body));
    assert.equal(body.text,original);
    return Response.json({issues:["Fixture stops before provider work"],notes:[],request:null});
  });
  assert.equal(ready,true);assert.equal(requests,0);
  pending.confirm({currentArea:{coordinates:{latitude:0,longitude:0}},calendarTimezone:"Asia/Kolkata",
    startingLocation:{point:{id:"authorized-start",coordinates:{latitude:0,longitude:0}},explicitly_authorized:true,source:"manual"}});
  await running;assert.equal(requests,1);assert.equal(pending.waiting,false);
});

test("options proxy preserves safe calendar/session codes and removes unknown provider codes",async()=>{
  const {providerProxy}=await import("./provider-proxy");
  const original=globalThis.fetch;
  try{
    for(const code of ["outing_date_expired","outing_time_expired","expired","raw-private-provider-code"]){
      globalThis.fetch=async()=>Response.json({code,message:"Safe explanation"},{status:422});
      const response=await providerProxy("/api/plans/options",new Request("http://localhost/api/plans/options",{method:"POST",body:JSON.stringify({token:"synthetic"})}));
      const data=await response.json();
      assert.equal(data.code,recoveryCode(code));assert.equal(data.message,"Safe explanation");
    }
  }finally{globalThis.fetch=original;}
});
