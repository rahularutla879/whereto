import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { LocationControls } from "../components/location-controls";
import { outingDetails } from "../components/outing-summary";
import { StartingAreaSession } from "./starting-areas";
import { StartingConfirmation } from "./starting-confirmation";
import { requestLocation } from "./location";
import type { ValidatedOuting } from "./planning-client";

const input={location:"Washington, DC",activities:["bowling","food"],transport:"driving",firstTravel:{value:8,unit:"miles",mode:"strict"}} as const;
const match={placeId:"Synthetic_public",name:"Synthetic public station",address:"Synthetic Washington, DC",coordinates:{latitude:0,longitude:0},precision:"address_or_place",attributions:[],reason:"Three checked first-stop routes",score:300};
test("three origin choices render without fetching or requesting permission",()=>{
  let changes=0;
  const html=renderToStaticMarkup(createElement(LocationControls,{onChange(){changes++;},lookupEnabled:true}));
  for(const choice of ["Use my current location","Enter my starting location","Choose a starting area for me","Minutes","Miles","Flexible preference","Strict maximum"]) assert.ok(html.includes(choice));
  assert.equal((html.match(/type="radio"/g)||[]).length,3);
  assert.doesNotMatch(html,/checked=""|latitude|longitude/);
  assert.equal(changes,0);
});
test("suggested references require explicit confirmation, reuse one request and cancellation rejects stale choice",async()=>{
  let calls=0;const session=new StartingAreaSession();const choice=new StartingConfirmation();
  const send:typeof fetch=async(url,init)=>{calls++;assert.equal(url,"/api/starting-areas");const body=JSON.parse(init!.body as string);assert.equal(body.destination,"Washington, DC");assert.equal(body.firstTravel.unit,"miles");return Response.json({matches:[match],referenceToken:"reference"});};
  const query={...input,activities:[...input.activities]};
  const pending=choice.wait();
  await session.get(query,send);await session.get(query,send);assert.equal(calls,1);
  choice.cancel();assert.equal(await pending,null);
  assert.equal(choice.confirm({locationFirst:true}),false);
  session.clear();await session.get(query,send);assert.equal(calls,2);
});
test("suggestion failure, quota and malformed provider facts fail closed without automatic retry",async()=>{
  for(const response of [()=>Response.json({message:"Quota reached"},{status:422}),()=>Response.json({matches:[{...match,coordinates:{latitude:999,longitude:0}}]})]){
    const session=new StartingAreaSession();let calls=0;
    const send:typeof fetch=async()=>{calls++;return response();};
    for(let i=0;i<2;i++)await assert.rejects(session.get({...input,activities:[...input.activities]},send),/Quota reached|could not be verified/);
    assert.equal(calls,1);
  }
});
test("current location preserves reported accuracy and permission denial has a manual alternative",async()=>{
  let requests=0;
  const geo={getCurrentPosition(success:PositionCallback){requests++;success({coords:{latitude:0,longitude:0,accuracy:125}} as GeolocationPosition);}};
  assert.equal(requests,0);
  assert.deepEqual(await requestLocation(geo,true),{latitude:0,longitude:0,accuracyMeters:125});
  const denied={getCurrentPosition(_success:PositionCallback,error?:PositionErrorCallback|null){error?.({code:1} as GeolocationPositionError);}};
  await assert.rejects(requestLocation(denied,true),/denied.*Enter a starting place/);
  await assert.rejects(requestLocation(undefined,false),/localhost or HTTPS/);
});
test("summary keeps first-road-distance preference separate from between-stop constraints",()=>{
  const value={request:{activities:["bowling","food"],date:"2026-11-14",location:"Washington, DC",people:3,budget:null,travel:null,maxLegTravel:5,maxLegTravelExclusive:true,firstTravel:{value:8,unit:"miles",mode:"flexible"}}} as ValidatedOuting;
  const details=Object.fromEntries(outingDetails(value,true));
  assert.equal(details["First journey"],"Prefer around 8 miles from the confirmed start; maximum 16 miles");
  assert.equal(details["Each journey"],"Under 5 min between stops");
});
