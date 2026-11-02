import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup as render} from 'react-dom/server';
import {execFileSync} from 'node:child_process';
import Home from '../app/page';
import Guide from '../app/how-it-works/page';
import Privacy from '../app/privacy/page';
import Terms from '../app/terms/page';
import Activities from '../app/supported-activities/page';
import {ResultsInformation} from '../components/results-information';
import {FirstLegTravel} from '../components/first-leg-travel';
import {SavedCards} from '../components/saved-cards';
import {adaptRanking,generateOuting} from './planning-client';
import {emptyPreferenceState,editPreference,manualPreferences,displayInterpretedPreferences,interpretedPreferences} from './preferences';
import {validateSaved,type SavedPlan} from './saved-plans';

function ranking(mode:'walking'|'driving'){
 const source=`import json\nfrom backend.test_travel_mode49 import PlannerModes\nt=PlannerModes()\nt.setUp()\ntry:\n result,_=t.run_mode('${mode}')\n print(result.model_dump_json())\nfinally:t.doCleanups()`;
 return JSON.parse(execFileSync('backend/.venv/bin/python',['-c',source],{encoding:'utf8',maxBuffer:5*1024*1024}));
}
const walking=ranking('walking'),driving=ranking('driving');
test('product cleanup retains honest examples and secure native information links',()=>{
 const html=render(React.createElement(Home));
 assert.doesNotMatch(html,/A little demo|Try an example|REAL DATA|LOCAL DEV|MOCK DATA|Give it a go|A small demo\. A big idea\.|All venues, events, schedules, capacities, prices, and travel times are fictional/);
 for(const path of ['/how-it-works','/privacy','/terms'])assert.ok(html.includes(`href="${path}" target="_blank" rel="noopener noreferrer"`));
 assert.equal((html.match(/Where To\? is still growing/g)??[]).length,1);
 assert.match(html,/These example itineraries use fictional venues/);
 assert.match(html,/Travel mode/);assert.match(html,/<option value="driving" selected="">Driving/);assert.match(html,/<option value="walking">Walking/);
});
test('guide is user-facing and policies preserve storage and automatic-open accuracy',()=>{
 const guide=render(React.createElement(Guide));
 for(const phrase of ['Strict maximum','Flexible preference','Show different options','Explore farther','Copy link','Open saved plan','Supported activities','Walking','Previous / Next'])assert.ok(guide.includes(phrase));
 assert.doesNotMatch(guide,/FastAPI|Next\.js|Ollama|Qwen|Supabase|beam|request budget|developer flag/);
 const privacy=render(React.createElement(Privacy));assert.match(privacy,/Ordinary homepage navigation/);assert.match(privacy,/deliberately opening or reloading/);assert.match(privacy,/not enabled universally or in production/);assert.doesNotMatch(privacy,/Reopening never automatically contacts Google/);
 for(const page of [Privacy,Terms]){const html=render(React.createElement(page));assert.match(html,/information-page legal-page/);assert.ok((html.match(/<h2>/g)??[]).length>=4);assert.match(html,/policies.google.com\/privacy/);assert.match(html,/Back to planner/);}
 assert.doesNotMatch(render(React.createElement(Activities)),/mock mode|fictional Baltimore|provider mode|backend/);
});
test('manual walking persists through interpreted preferences, unrelated edits and regeneration input',()=>{
 let state=editPreference(emptyPreferenceState(),'transport','walking');
 state=editPreference(state,'location','Baltimore');
 state=displayInterpretedPreferences(state,interpretedPreferences({...driving.request,transport:'driving'}));
 assert.equal(state.values.transport,'walking');assert.equal(manualPreferences(state).transport,'walking');
 assert.equal(manualPreferences(editPreference(state,'date','2026-11-14')).transport,'walking');
 const automatic=displayInterpretedPreferences(emptyPreferenceState(),interpretedPreferences(walking.request));
 assert.equal(automatic.values.transport,'walking');assert.equal(manualPreferences(automatic).transport,undefined);
});
test('walking preference reaches interpretation and generation; actual backend results have different mode-specific travel',async()=>{
 for(const [mode,raw] of [['walking',walking],['driving',driving]] as const){
  const sent:{path:string;body:Record<string,unknown>}[]=[];
  const send:typeof fetch=async(path,init)=>{
   const body=JSON.parse(String(init?.body));sent.push({path:String(path),body});
   if(String(path)==='/api/interpret')return Response.json({interpretation:{},issues:[],notes:[],request:raw.request});
   assert.equal(body.transport,mode);return Response.json(raw);
  };
  const result=await generateOuting('Bowling and dinner in Baltimore on November 7, 2026',manualPreferences(editPreference(emptyPreferenceState(),'transport',mode)),{},send);
  assert.equal(result.plans.length,3);assert.equal(result.plans[0].transport,mode);
  assert.equal((sent[0].body.preferences as {transport:string}).transport,mode);
  assert.match(result.plans[0].description,new RegExp(`minutes ${mode} between stops`));
  const first=render(React.createElement(FirstLegTravel,{plan:result.plans[0]}));assert.match(first,new RegExp(`minutes ${mode}`));
 }
 assert.ok(adaptRanking(walking).plans[0].travel!>adaptRanking(driving).plans[0].travel!);
});
test('client refuses a driving response labeled walking; missing route stays unknown',()=>{
 const mixed=structuredClone(driving);mixed.request.transport='walking';assert.throws(()=>adaptRanking(mixed),/Mixed travel modes/);
 const unknown=structuredClone(walking);for(const p of unknown.provisionalPlans){p.totalTravel=null;p.legs.forEach((l:{minutes:number|null})=>l.minutes=null);}
 const result=adaptRanking(unknown);assert.equal(result.plans[0].travel,null);assert.match(result.plans[0].description,/not verified/);assert.doesNotMatch(result.plans[0].description,/0 minutes/);
});
test('walking warning is shared once and does not claim safe or accessible paths',()=>{
 const html=render(React.createElement(ResultsInformation,{real:true,walking:true,notes:[],needsChecking:true}));
 assert.equal((html.match(/Walking routes are in beta/g)??[]).length,1);assert.match(html,/may omit sidewalks or pedestrian paths/);assert.match(html,/safety and accessibility are not verified/);
 assert.doesNotMatch(render(React.createElement(ResultsInformation,{real:true,walking:false,notes:[],needsChecking:true})),/Walking routes are in beta/);
});
test('legacy absent/null saved mode defaults driving; walking selection survives with no old route estimates',()=>{
 const raw={version:1,saved:true,dataMode:'real',selectedId:'selected',expiresAt:'2026-12-01',liveDetailsAvailable:false,
 constraints:{...walking.request,transport:'walking'},itineraries:[{candidateId:'selected',fictionalMetrics:null,stops:walking.request.activities.map((activity:string,position:number)=>({position,activity,provider:'google_places',reference:'fixture-'+position,timingBasis:'unknown',start:null,end:null,duration:null,fictional:null}))}]} as SavedPlan;
 for(const mode of ['walking','driving',null,undefined,'cycling']){
  const saved=validateSaved({...raw,constraints:{...raw.constraints,transport:mode}});
  assert.equal(saved.constraints.transport,mode??'driving');
  const html=render(React.createElement(SavedCards,{saved,venues:{},refresh(){},busy:false,message:''}));assert.match(html,new RegExp(mode==='walking'?'Walking':mode==='cycling'?'Original travel preference':'Driving'));assert.match(html,/Original route estimates were not retained/);
 }
});
