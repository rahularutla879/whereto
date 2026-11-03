import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {adaptAdvanced,continueAdvanced, type AdvancedData} from './advanced-planning';
import {generateOuting} from './planning-client';
import {advancedDraft} from './advanced-preferences';
import {AdvancedPreferenceFields} from '../components/advanced-preferences';
import {AdvancedClarifications} from '../components/advanced-plan';
import {PlanCard} from '../components/plan-card';
import {VenueDetailsSession} from './venue-details';
import {validateSaved} from './saved-plans';
import {SavedCards} from '../components/saved-cards';

// Cross-language integration: these are the actual minimized server projections,
// generated using invented Google-shaped responses with real network forbidden.
const fixture=JSON.parse(execFileSync('backend/.venv/bin/python',['-c',`
import json
from backend.test_advanced_planning import IntegrationTests
from backend.saved_plans import SaveRequest,receipts
from backend.test_advanced_routing import start
h=IntegrationTests('test_named_roundtrip_dto_and_receipt');h.setUp()
try:
 s=h.session(endpoint={'kind':'origin','source':'return to start'},total_duration={'minutes':45,'relation':'maximum','source':'within 45 minutes'})
 r=h.run_session(s,startingLocation=start())
 d=receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[p.id for p in r.options],selectedId=r.options[0].id))
 print(json.dumps({'data':r.model_dump(mode='json'),'saved':{**d.model_dump(mode='json'),'saved':True,'liveDetailsAvailable':False,'expiresAt':'2026-12-07T00:00:00Z'}}))
finally:h.doCleanups()
`],{encoding:'utf8'})) as {data:AdvancedData;saved:unknown};

test('trusted advanced projection renders complete return route and prominent uncertainty',()=>{
 const result=adaptAdvanced(fixture.data,{});
 assert.equal(result.plans.length,1);assert.equal(result.plans[0].feasibility,'provisional');
 const html=renderToStaticMarkup(createElement(PlanCard,{plan:result.plans[0],index:0,detailsSession:new VenueDetailsSession()}));
 assert.match(html,/Return to starting point/);assert.match(html,/Total time not yet verified/);assert.match(html,/whole journey/i);assert.doesNotMatch(html,/Select itinerary/);assert.doesNotMatch(html,/Return travel is not included|10:00 AM|latitude/);
 const question=renderToStaticMarkup(createElement(AdvancedClarifications,{state:result.advanced!,busy:false,onAnswer(){}}));
 assert.match(question,/How long/);assert.match(question,/Visit times and itinerary preferences/);assert.doesNotMatch(question,/<form/);assert.doesNotMatch(html,/do not guarantee actual arrival/);
});
test('normal submission routes a server-issued advanced token without ordinary dispatch',async()=>{
 const paths:string[]=[];
 const result=await generateOuting('Synthetic public advanced request',undefined,undefined,async(url,init)=>{
  paths.push(String(url));
  if(url==='/api/interpret')return Response.json({interpretation:{activities:['SUNY College of Optometry','coffee']},advancedToken:fixture.data.token,context:{destination:'New York'},unsupported:['Old limitation'],issues:['Old limitation'],notes:[],request:null});
  assert.equal(JSON.parse(String(init?.body)).token,fixture.data.token);
  return Response.json(fixture.data);
 });
 assert.deepEqual(paths,['/api/interpret','/api/plans/advanced']);assert.equal(result.plans.length,1);assert.equal(result.advancedUnavailable,undefined);
});
test('field-only answers retain the active token/configuration and never invoke extraction',async()=>{
 const state=adaptAdvanced(fixture.data,{}).advanced!;
 const result=await continueAdvanced(state,{dwell:{occurrence:1,minutes:15,relation:'maximum'}},undefined,async(url,init)=>{
  assert.equal(url,'/api/plans/advanced');assert.deepEqual(JSON.parse(String(init?.body)),{token:fixture.data.token,dwell:{occurrence:1,minutes:15,relation:'maximum'}});return Response.json(fixture.data);
 });assert.equal(result.plans[0].id,fixture.data.options[0].id);
});
test('infeasible and incomplete upstream options cannot be adapted as compliant cards',()=>{
 const raw=structuredClone(fixture.data);Object.assign(raw.options[0],{state:'infeasible'});
 assert.throws(()=>adaptAdvanced(raw,{}));assert.throws(()=>adaptAdvanced({...fixture.data,options:[...fixture.data.options,...fixture.data.options]},{}));
});
test('version two saved selected itinerary preserves requirements without retained Google metrics',()=>{
 const saved=validateSaved(fixture.saved);
 assert.equal(saved.version,2);assert.equal(saved.itineraries.length,1);assert.equal(saved.itineraries[0].advanced?.ending,'origin');
 const html=renderToStaticMarkup(createElement(SavedCards,{saved,venues:{},refresh(){},busy:false,message:''}));
 assert.match(html,/Return to starting point/);assert.match(html,/Current timing is unverified/);assert.match(html,/Departure unspecified/);assert.doesNotMatch(html,/10:00 AM/);
 const corrupt=structuredClone(saved);corrupt.itineraries[0].advanced!.occurrenceOrder=[1,0];corrupt.itineraries[0].advanced!.omittedOccurrences=[];
 assert.throws(()=>validateSaved(corrupt));
});

test('advanced proxy preserves planning validation errors instead of calling them save failures',async()=>{
 const {persistenceProxy}=await import('./persistence-proxy');
 const original=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({code:'invalid_request',message:'Check the advanced answer format. Your request is kept.'},{status:422});
 try{
  const response=await persistenceProxy('/api/plans/advanced',new Request('http://localhost:3000/api/plans/advanced',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:'x'.repeat(43),departure:''})}));
  assert.equal(response.status,422);assert.match((await response.json()).message,/advanced answer format/);
 }finally{globalThis.fetch=original;}
});

test('advanced cards share ordinary card primitives, readable formatting and the original save workflow',()=>{
 const plan=adaptAdvanced(fixture.data,{}).plans[0];
 const html=renderToStaticMarkup(createElement(PlanCard,{plan,index:0,detailsSession:new VenueDetailsSession()}));
 for(const primitive of ['card-visual','real-route-poster','card-description','activity-route','card-facts','plan-link','stop-number'])assert.ok(html.includes(primitive));
 assert.match(html,/November 7, 2026/);assert.match(html,/View plan/);
 assert.doesNotMatch(html,/Select itinerary|Requested stop [0-9]|New York · 2026-/);
});
test('date and area questions use canonical planner fields, not duplicate forms',()=>{
 const state=adaptAdvanced({...fixture.data,questions:[{field:'date',question:'Choose a date'},{field:'destination',question:'Choose an area'}]},{}).advanced!;
 const html=renderToStaticMarkup(createElement(AdvancedClarifications,{state,busy:false,nearOrigin:true,onAnswer(){}}));
 assert.match(html,/Date above/);assert.match(html,/Location above/);assert.match(html,/Search near my confirmed starting point/);
 assert.doesNotMatch(html,/<form|<input/);
});
test('advanced continuation exposes real actions and history navigation makes no calls',async()=>{
 const {ItineraryPages}=await import('./itinerary-pages');
 const first=adaptAdvanced({...fixture.data,canExpand:true,canDiscover:true,canShowBeyond:true},{});
 assert.equal(first.canExpand,true);assert.equal(first.canDiscover,true);assert.equal(first.canShowBeyond,true);
 let calls=0;
 const second=await continueAdvanced(first.advanced!,{action:'different'},undefined,async(url,init)=>{
  calls++;assert.equal(url,'/api/plans/advanced');assert.equal(JSON.parse(String(init?.body)).action,'different');
  return Response.json({...fixture.data,options:fixture.data.options.map(p=>({...p,id:p.id+'_next',stops:p.stops.map(s=>({...s,placeId:s.placeId+'_next'}))}))});
 });
 const pages=new ItineraryPages();pages.append(first);pages.append(second);
 assert.equal(pages.pages.length,2);assert.equal(pages.navigate(-1)?.plans[0].id,first.plans[0].id);
 assert.equal(pages.navigate(1)?.plans[0].id,second.plans[0].id);assert.equal(calls,1);
});

test('the canonical date answer keeps one native control and offers supported words',async()=>{
 const {OutingDateField}=await import('../components/outing-date-field');
 const html=renderToStaticMarkup(createElement(OutingDateField,{value:'',onChange(){},real:true,allowNatural:true}));
 assert.equal((html.match(/<input/g)??[]).length,1);assert.match(html,/type="date"/);assert.match(html,/name="outing-date"/);assert.match(html,/Enter a date in words/);
});

test('follow-up cards omit repeated unknown warnings and technical hours copy',()=>{
 const plan=adaptAdvanced(fixture.data,{}).plans[0];
 const html=renderToStaticMarkup(createElement(PlanCard,{plan,index:0,detailsSession:new VenueDetailsSession()}));
 assert.doesNotMatch(html,/Activity illustrations|Check this option|Visit hours need checking|Visit duration not supplied|Hours checked|America\/New_York|Visit hours:/);
 assert.doesNotMatch(html,/without live traffic/);
 assert.equal((html.match(/aria-label="Opening hours"/g)??[]).length,plan.advanced!.stops.length);
});
test('duration control states minutes, integer bounds and no approximate default',()=>{
 const state=adaptAdvanced({...fixture.data,questions:[{field:'dwell',occurrence:0,question:'How many minutes grocery shopping?'}]},{}).advanced!;
 const html=renderToStaticMarkup(createElement(AdvancedPreferenceFields,{data:state.data,draft:advancedDraft(state.data)!,busy:false,onChange(){}}));
 assert.match(html,/duration \(minutes\)/);assert.match(html,/placeholder="20"/);assert.match(html,/step="1"/);assert.match(html,/max="10080"/);
 assert.match(html,/value="exact" selected=""/);assert.match(html,/no guaranteed maximum/);
});
test('readable projected clocks retain destination-local offset rather than browser timezone',()=>{
 const raw=structuredClone(fixture.data);raw.options[0].stops[0].arrival='2026-11-07T10:00:00-05:00';raw.options[0].stops[0].departure='2026-11-07T10:20:00-05:00';
 const plan=adaptAdvanced(raw,{}).plans[0];
 const html=renderToStaticMarkup(createElement(PlanCard,{plan,index:0,detailsSession:new VenueDetailsSession()}));
 assert.match(html,/10:00 AM/);assert.match(html,/10:20 AM/);assert.doesNotMatch(html,/15:00/);
});

test('saved zero counted time never claims a realistic zero-minute visit',()=>{
 const saved=validateSaved(fixture.saved);const advanced=saved.itineraries[0].advanced!;
 advanced.budgetScope='travel';advanced.journey.stops[advanced.occurrenceOrder[0]].duration={minutes:0,relation:'exact',source:'Explicit counted-time override'};
 const html=renderToStaticMarkup(createElement(SavedCards,{saved,venues:{},refresh(){},busy:false,message:''}));
 assert.match(html,/Zero counted visit time; actual visit duration was not established/);
 assert.doesNotMatch(html,/exact 0 minutes/);
});
