import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {adaptAdvanced,continueAdvanced, type AdvancedData} from './advanced-planning';
import {generateOuting} from './planning-client';
import {AdvancedPlanCard,AdvancedClarifications} from '../components/advanced-plan';
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
 const html=renderToStaticMarkup(createElement(AdvancedPlanCard,{plan:result.plans[0],index:0,selected:false,onSelect(){}}));
 assert.match(html,/Return to Start/);assert.match(html,/Return to starting point/);assert.match(html,/Requirements not fully verified/);assert.match(html,/whole journey/i);assert.match(html,/Select itinerary/);assert.doesNotMatch(html,/Return travel is not included|10:00 AM|latitude/);
 const question=renderToStaticMarkup(createElement(AdvancedClarifications,{state:result.advanced!,busy:false,onAnswer(){}}));
 assert.match(question,/How long/);assert.match(question,/My estimate \(approximate\)/);assert.match(question,/bounded search/);assert.match(question,/do not guarantee actual arrival/);assert.doesNotMatch(html,/do not guarantee actual arrival/);
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
