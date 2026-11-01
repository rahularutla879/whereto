import test from "node:test";
import assert from "node:assert/strict";
import * as React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {SavedCards} from "../components/saved-cards";
import {ResultsInformation} from "../components/results-information";
import Home from "../app/page";
import type {SavedPlan} from "./saved-plans";
const document:SavedPlan={version:1,saved:true,dataMode:"real",selectedId:"two",expiresAt:"2026-12-01",liveDetailsAvailable:false,
 constraints:{location:"Hyderabad",date:"2026-11-14",activities:["movie"],activityIntents:{movie:"movie"},startTime:600,endTime:1440,planningMode:"origin",transport:"driving",calendarTimezone:"Asia/Kolkata",firstTravel:{value:10,unit:"minutes",mode:"strict",exclusive:false},betweenTravel:null,maxFirstLegTravel:null,maxLegTravel:null,travel:null,geography:{strictDestination:false,excludedRegions:[]},dinner:false,dinnerStops:null,requireAvailability:false,requireWheelchairAccess:false,allowRevisits:false},
 itineraries:["one","two","three"].map(candidateId=>({candidateId,fictionalMetrics:null,stops:[{position:0,activity:"movie",provider:"google_places",reference:"Fixture49_"+candidateId,timingBasis:"unknown",start:null,end:null,duration:null,fictional:null}]}))};
test("saved real cards preserve order/selection with clean placeholders, never raw IDs or demo plans",()=>{
 const html=renderToStaticMarkup(React.createElement(SavedCards,{saved:document,venues:{},refresh(){},busy:false,message:""}));
 assert.equal((html.match(/class="plan-card/g)??[]).length,1);
 assert.doesNotMatch(html,/Saved option 1|Saved option 3/);
 assert.match(html,/Saved option 2, selected/);assert.match(html,/>Movie</);
 assert.doesNotMatch(html,/Fixture49_|DEMO PLAN|\b0 minutes|estimated minutes between stops/);
 assert.match(html,/Load current venue details/);assert.match(html,/Strict: up to 10 minutes/);
});
test("refreshed names and closure are current in-memory facts; failed stops retain placeholders",()=>{
 const html=renderToStaticMarkup(React.createElement(SavedCards,{saved:{...document,selectedId:"one"},venues:{Fixture49_one:{status:"refreshed",name:"Synthetic current cinema",businessStatus:"CLOSED_PERMANENTLY",refreshedAt:"2026-10-31T12:00:00Z"},Fixture49_two:{status:"unavailable",message:"Current details unavailable"}},refresh(){},busy:false,message:"Partial refresh"}));
 assert.match(html,/Synthetic current cinema/);assert.match(html,/Reported permanently closed/);assert.doesNotMatch(html,/Current details unavailable/);assert.match(html,/Original route estimates were not retained/);assert.doesNotMatch(html,/Fixture49_/);
});
test("normal explanations contain one shared notice and no raw JSON, cost ledger or ranking internals",()=>{
 const html=renderToStaticMarkup(React.createElement(ResultsInformation,{real:true,needsChecking:true,notes:['Development usage {"apiSpend":123}','Beam score raw JSON','Calendar reference UTC']}));
 assert.equal((html.match(/Before you go/g)??[]).length,2); // aria label + visible heading
 assert.match(html,/<details[^>]*><summary>About these recommendations/);
 assert.doesNotMatch(html,/Developer diagnostics|apiSpend|Beam score|Calendar reference|UTC/);
});
test("ordinary cards precede all save/reopen controls in DOM and no expanded saved document displaces demo",()=>{
 const html=renderToStaticMarkup(React.createElement(Home));
 assert.ok(html.indexOf('class="plans-grid"')<html.indexOf('aria-label="Save and reopen plans"'));
 assert.match(html,/Reopen another saved plan/);assert.doesNotMatch(html,/Before you choose/);
});
test("production payloads omit internal diagnostics while preserving saved structures and normal notes",async()=>{
 const {publicPlanningPayload}=await import('./public-planning-payload');
 const env=process.env as Record<string,string|undefined>;
 const prior=env.NODE_ENV;env.NODE_ENV='production';
 try{
  const payload=publicPlanningPayload({diagnostics:{raw:'internal'},notes:['Development usage JSON','Calendar reference: UTC','Useful limitation'],candidateId:'original'});
  assert.deepEqual(payload,{notes:['Useful limitation'],candidateId:'original'});
 }finally{if(prior===undefined)delete env.NODE_ENV;else env.NODE_ENV=prior;}
});
test("later explicit refresh replaces current facts; failure keeps earlier names with stale status",async()=>{
 const {mergeRefreshed}=await import('./saved-plan-refresh');
 const old={id:{status:'refreshed',name:'Earlier name',businessStatus:'OPERATIONAL',refreshedAt:'2026-10-30T12:00:00Z'}};
 const updated=mergeRefreshed(old,{id:{status:'refreshed',name:'Current name',businessStatus:'CLOSED_PERMANENTLY'}});
 assert.equal(updated.id.name,'Current name');assert.equal(updated.id.businessStatus,'CLOSED_PERMANENTLY');
 const failed=mergeRefreshed(old,{id:{status:'unavailable',message:'Provider unavailable'}});
 assert.equal(failed.id.name,'Earlier name');assert.equal(failed.id.status,'stale');assert.equal(failed.id.message,'Provider unavailable');
});

test("selected multi-stop partial load keeps the verified title and both ordered stops",()=>{
 const saved:SavedPlan={...document,constraints:{...document.constraints,activities:['movie','food'],activityIntents:{movie:'movie',food:'dinner'}},itineraries:document.itineraries.map(option=>({...option,stops:[option.stops[0],{...option.stops[0],position:1,activity:'food',reference:option.stops[0].reference+'_food'}]}))};
 const html=renderToStaticMarkup(React.createElement(SavedCards,{saved,venues:{Fixture49_two:{status:'refreshed',name:'Synthetic cinema',mapsUrl:'https://maps.google.com/?cid=123'},Fixture49_two_food:{status:'unavailable',message:'Details unavailable'}},refresh(){},busy:false,message:'Partial load'}));
 assert.match(html,/Synthetic cinema → Food/);assert.match(html,/Details unavailable/);assert.match(html,/Business status unavailable/);
 assert.equal((html.match(/<li>/g)??[]).length,2);assert.equal((html.match(/>Load current venue details</g)??[]).length,1);
 assert.ok(html.indexOf('Synthetic cinema</h4>')<html.indexOf('Food</h4>'));
 assert.doesNotMatch(html,/Fixture49_|Saved option 1|Saved option 3/);
});
