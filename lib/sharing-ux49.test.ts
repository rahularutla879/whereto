import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import Home from '../app/page';
import Activities from '../app/supported-activities/page';
import {ClarificationField} from '../components/clarification-field';
import {SavedCards} from '../components/saved-cards';
import {BeyondPreferences} from '../components/beyond-preferences';
import {supportedActivityGroups} from './supported-activities';
import {diagnosticBoundary} from './development-access';
import {planWarnings} from './results-presentation';
import {ItineraryPages,BEYOND_NOTICE} from './itinerary-pages';
import {safeWebsite,safeMapsUrl} from './venue-details';
import type {Plan,PlannerResult} from './planner';
import type {SavedPlan} from './saved-plans';
import registry from '../data/mock-venues.json';
import demo from '../data/demo-plans.json';
const saved:SavedPlan={version:1,saved:true,dataMode:'real',selectedId:'chosen',expiresAt:'2026-12-01',liveDetailsAvailable:false,
 constraints:{location:'Jersey City',date:'2026-11-07',activities:['food','coffee'],activityIntents:{food:'dinner',coffee:'coffee'},startTime:600,endTime:1440,planningMode:'surprise',transport:'driving',calendarTimezone:'America/New_York',firstTravel:null,betweenTravel:null,maxFirstLegTravel:null,maxLegTravel:null,travel:null,geography:{strictDestination:false,excludedRegions:[]},dinner:false,dinnerStops:null,requireAvailability:false,requireWheelchairAccess:false,allowRevisits:false},itineraries:[{candidateId:'chosen',fictionalMetrics:null,stops:['food','coffee'].map((activity,position)=>({position,activity,provider:'google_places',reference:String(position),timingBasis:'unknown',start:null,end:null,duration:null,fictional:null}))}]};
test('independent websites/phones render as safe useful links for two saved stops',()=>{
 for(const website of ['https://example.com/official','http://example.com/official',undefined]){
  const html=renderToStaticMarkup(React.createElement(SavedCards,{saved,venues:{0:{status:'refreshed',name:'Invented dinner',website},1:{status:'refreshed',name:'Invented coffee',phone:'Fixture phone',telephoneUrl:'tel:+12025550149'}},refresh(){},busy:false,message:''}));
  assert.equal((html.match(/>Official website</g)??[]).length,website?1:0);assert.match(html,/tel:\+12025550149/);
  assert.ok(html.indexOf('Invented dinner</h4>')<html.indexOf('Invented coffee</h4>'));
 }
 assert.equal(safeMapsUrl('http://www.google.com/maps'),null);assert.equal(safeMapsUrl('https://example.com/maps'),null);assert.equal(safeMapsUrl('https://www.google.com/maps'),'https://www.google.com/maps');
 for(const unsafe of ['javascript:alert(1)','data:text/html,x','https://u:p@example.com','https://example.com/\nprivate','https://example.com:bad'])assert.equal(safeWebsite(unsafe),null);
});
test('normal app has no developer disclosure or technical JSON',()=>{
 const html=renderToStaticMarkup(React.createElement(Home));assert.doesNotMatch(html,/Local development tools|Sanitized development diagnostics|Load diagnostics|rankingAudit|localAiTiming/);
});
test('developer boundary is server enforced for production, remote/forwarded and cross-origin callers',()=>{
 const env=process.env as Record<string,string|undefined>;const old=env.NODE_ENV;
 try{
  env.NODE_ENV='development';assert.ok(diagnosticBoundary(new Request('http://localhost:3000/dev/diagnostics')));
  for(const request of [new Request('http://example.com/dev/diagnostics'),new Request('http://localhost:3000/dev/diagnostics',{headers:{'x-forwarded-for':'203.0.113.1'}}),new Request('http://localhost:3000/dev/diagnostics',{headers:{origin:'https://example.com'}})])assert.equal(diagnosticBoundary(request),null);
  env.NODE_ENV='production';assert.equal(diagnosticBoundary(new Request('http://localhost:3000/dev/diagnostics')),null);
 }finally{if(old===undefined)delete env.NODE_ENV;else env.NODE_ENV=old;}
});
test('supported reference is registry-driven, grouped by scheduled metadata, with honest sports/open-ended descriptions',()=>{
 const groups=supportedActivityGroups();assert.equal(groups.flatMap(g=>g.items).length,Object.keys(registry.catalog).length);
 assert.deepEqual(new Set(groups.flatMap(g=>g.items.map(i=>i.label))),new Set(Object.values(registry.catalog).map(i=>i.label)));
 const html=renderToStaticMarkup(React.createElement(Activities));assert.match(html,/Soccer match/);assert.match(html,/not mean a place to play/);assert.match(html,/not exhaustive/);assert.match(html,/Zara outlet/);assert.doesNotMatch(html,/custom:|eventStart|api\/|<pre/);
});
test('activity clarification alone has a secure separate-tab reference; location/date questions do not',()=>{
 for(const field of ['activities','location','date'] as const){
  const question={field,question:'One concise question',kind:'ambiguous' as const};
  const html=renderToStaticMarkup(React.createElement(ClarificationField,{question,value:'Original answer',onChange(){}}));
  assert.equal((html.match(/View supported activities/g)??[]).length,field==='activities'?1:0);
  assert.match(html,/value="Original answer"/);
  if(field==='activities')assert.match(html,/href="\/supported-activities" target="_blank" rel="noopener noreferrer"/);
 }
});
const real=():Plan=>({...structuredClone(demo.plans[0]) as Plan,dataMode:'real',travelClassification:'outside_preference',travelDeviations:['Journey to the first stop: preferred 10 minutes; verified 12 min 1 sec, 2 min 1 sec over.'],constraintIssues:[{code:'extra_first_travel',field:'travel',status:'unknown',message:'Generic extra travel warning'}]});
test('specific flexible warning replaces equivalent generic warning without changing constraints or independent gaps',()=>{
 const p=real();assert.deepEqual(planWarnings(p),[]);
 p.constraintIssues!.push({code:'accessibility_conflict',field:'accessibility',status:'violation',message:'Wheelchair access conflict'});
 assert.deepEqual(planWarnings(p),['Wheelchair access conflict']);assert.equal(p.constraintIssues!.length,2);
 p.travel=null;assert.match(planWarnings(p).join(' '),/Travel time is missing/);
 p.travelClassification='beyond_limit';assert.match(planWarnings(p).join(' '),/Generic extra travel warning/);
});
test('one group explanation survives mixed options and page history with precise hard exceptions',()=>{
 const p=real();const result={...structuredClone(demo),plans:[p]} as PlannerResult;
 const render=(r:PlannerResult)=>renderToStaticMarkup(React.createElement(BeyondPreferences,{result:r}));
 let html=render(result);assert.equal((html.match(/<p>/g)??[]).length,1);assert.match(html,/These options exceed your preferred travel range/);assert.doesNotMatch(html,/These additional outings|don't meet all/);
 const matching={...p,id:'other',travelClassification:'matching' as const,venues:p.venues.map(v=>({...v,id:v.id+'other'}))};
 html=render({...result,plans:[p,matching]});assert.match(html,/Some options/);
 html=render({...result,plans:[matching]});assert.equal(html,'');
 html=render({...result,plans:[{...p,travelClassification:'beyond_limit'},matching]});assert.match(html,/Some options.*hard travel limit.*explicit opt-in/);
 const pages=new ItineraryPages();pages.append(result);pages.append({...result,plans:[matching]});assert.equal(render(pages.navigate(-1)!),render(result));assert.equal(BEYOND_NOTICE.includes('preferred travel range'),true);
});
