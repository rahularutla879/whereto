import assert from "node:assert/strict";
import test from "node:test";
import { providerDiagnosticNotes } from "./provider-diagnostics";
import { FirstPreference } from "./first-preference";
import { generateOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";

test("validated extraction hydrates original amount/unit/flexibility without converting display to the double maximum",()=>{
  const editor=new FirstPreference();
  assert.deepEqual(editor.hydrate({value:20,unit:"minutes",mode:"flexible"}),{value:20,unit:"minutes",mode:"flexible"});
  assert.equal(editor.value!.value*2,40);
  editor.hydrate({value:5,unit:"miles",mode:"strict",exclusive:true});
  assert.equal(editor.value?.unit,"miles");assert.equal(editor.value?.exclusive,true);
});
test("explicit edits win across hydration, clarification, rerender and delayed confirmation",async()=>{
  const editor=new FirstPreference();editor.hydrate({value:20,unit:"minutes",mode:"flexible"});
  editor.edit({value:7,unit:"miles",mode:"strict",exclusive:false});
  for(const incoming of [null,{value:20,unit:"minutes" as const,mode:"flexible" as const},{value:3,unit:"minutes" as const,mode:"strict" as const}])editor.hydrate(incoming);
  await Promise.resolve();assert.deepEqual(editor.value,{value:7,unit:"miles",mode:"strict",exclusive:false});
  editor.edit(null);editor.hydrate({value:20,unit:"minutes",mode:"flexible"});assert.equal(editor.value,null);
});
test("manual first-stop edit replaces legacy duplicate caps while between-stop constraints survive",async()=>{
  let submitted:Record<string,unknown>|undefined;
  const send:typeof fetch=async(url,init)=>{
    if(url==="/api/interpret")return Response.json({issues:[],notes:[],request:{activities:["bowling","food"],location:"Washington, DC",people:3,date:"2026-11-14",budget:null,travel:null,cost:"balanced",firstTravel:{value:20,unit:"minutes",mode:"strict",exclusive:true},maxFirstLegTravel:20,maxFirstLegTravelExclusive:true,maxLegTravel:5,maxLegTravelExclusive:true}});
    submitted=JSON.parse(init!.body as string);return Response.json({message:"done"},{status:422});
  };
  await generateOuting("First stop under 20 minutes",EMPTY_PREFERENCES,{prepareOrigin:async()=>({startingLocation:{point:{id:"authorized-start",coordinates:{latitude:0,longitude:0}},explicitly_authorized:true},firstTravel:{value:7,unit:"miles",mode:"flexible",exclusive:false}})},send);
  assert.deepEqual(submitted?.firstTravel,{value:7,unit:"miles",mode:"flexible",exclusive:false});
  assert.equal(submitted?.maxFirstLegTravel,null);assert.equal(submitted?.maxLegTravel,5);assert.equal(submitted?.maxLegTravelExclusive,true);
});
test("a missing origin prevents the client from publishing any plan request",async()=>{
  let requests=0;
  const send:typeof fetch=async()=>{requests++;return Response.json({issues:[],notes:[],request:{activities:["bowling"],location:"Washington, DC"}});};
  const result=await generateOuting("Bowling",EMPTY_PREFERENCES,{prepareOrigin:async()=>null},send);
  assert.equal(requests,1);assert.equal(result.plans.length,0);assert.match(result.message,/starting-location/);
});

test("developer failure accounting admits only fixed labels and counters",()=>{
  const notes=providerDiagnosticNotes({service:"places.googleapis.com",requestCategory:"search",quotaBoundary:"daily",placesSearchRequests:5,reservedMatrixElements:36,providerAttempts:7,raw:"SECRET",latitude:38.9});
  assert.match(notes[0],/daily.*7.*5.*36/);assert.doesNotMatch(notes[0],/SECRET|38.9/);
});
