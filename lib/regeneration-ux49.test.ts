import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup as render} from 'react-dom/server';
import {generateOuting} from './planning-client';
import {EMPTY_PREFERENCES} from './planner';
import {SavedCards} from '../components/saved-cards';
import {AlternativeActions} from '../components/alternative-actions';
import type {SavedPlan} from './saved-plans';
import type {FirstTravel} from './starting-areas';
import {failureText} from './failure-diagnostics';

const constraints={...EMPTY_PREFERENCES,activities:['food','coffee'],location:'Jersey City',date:'2026-11-07',activityIntents:{food:'dinner',coffee:'coffee'},startTime:620,endTime:1440,explicitStart:false,explicitEnd:false,planningMode:'origin',transport:'walking',calendarTimezone:'America/New_York',firstTravel:{value:10,unit:'minutes',mode:'flexible',exclusive:false},betweenTravel:null,maxFirstLegTravel:null,maxLegTravel:null,travel:null,geography:{strictDestination:false,excludedRegions:[]},dinner:true,dinnerStops:[0],requireAvailability:false,requireWheelchairAccess:false,allowRevisits:false};
const saved={version:1,saved:true,dataMode:'real',selectedId:'chosen',expiresAt:'2026-12-01',liveDetailsAvailable:false,constraints,itineraries:[{candidateId:'chosen',fictionalMetrics:null,stops:['food','coffee'].map((activity,position)=>({position,activity,provider:'google_places',reference:'fixture'+position,timingBasis:'unknown',start:null,end:null,duration:null,fictional:null}))}]} as unknown as SavedPlan;
test('saved preferences distinguish default planning boundaries, midnight, mode and exact limits',()=>{
 const html=render(React.createElement(SavedCards,{saved,venues:{},refresh(){},busy:false,message:''}));
 for(const text of ['Saved preferences','<dl','Date and time','planning start, not a requested arrival','midnight at the end of this date','planning cutoff','America/New_York','Walking','maximum 20 minutes','No repeated venues','Dinner at stop 1','Exact starting location was not retained','Include phone number and website'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/existing paid contact tier|Saved planning constraints|10:20 AM–12:00 AM/);
 const explicit=render(React.createElement(SavedCards,{saved:{...saved,constraints:{...saved.constraints,explicitStart:true,explicitEnd:true,endTime:780}},venues:{},refresh(){},busy:false,message:''}));
 assert.doesNotMatch(explicit,/planning start, not a requested arrival|planning cutoff/);assert.match(explicit,/1:00 PM/);
});
test('all three exploration controls carry one distinct explanation',()=>{
 const html=render(React.createElement(AlternativeActions,{real:true,nearby:true,canCombine:true,canExplore:true,canShowBeyond:true,busy:false,disabled:false,notice:'',onAction(){},onAdjust(){}}));
 for(const text of ['Try new combinations of places already found, within your travel limits.','Discover more places while keeping your current travel limits.','See additional options that exceed your travel limit. Your original preference won’t change.'])assert.equal(html.split(text).length-1,1);
});
test('new regeneration configurations replace first/between evidence and preserve source, origin, date and manual mode',async()=>{
 const source='Dinner and coffee in Jersey City tomorrow';
 const origin={point:{id:'authorized-start',coordinates:{latitude:40.7,longitude:-74.05}},explicitly_authorized:true as const,source:'manual' as const};
 for(const mode of ['driving','walking','driving'] as const){
  for(const flexibility of ['strict','flexible'] as const){
   for(const amount of [10,20,null]){
    const first:FirstTravel|null=amount===null?null:{value:amount,unit:'minutes',mode:flexibility};
    let count=0;
    const send:typeof fetch=async(path,init)=>{
     const body=JSON.parse(String(init?.body));count++;
     if(path==='/api/interpret'){
      assert.equal(body.text,source);assert.equal(body.preferences.transport,mode);assert.equal(body.preferences.location,'Hyderabad');assert.equal(body.preferences.date,'2026-11-08');
      return Response.json({notes:[],issues:[],request:{...constraints,budget:null,transport:mode,date:body.preferences.date,location:body.preferences.location,firstTravel:{value:5,unit:'minutes',mode:'strict'},maxFirstLegTravel:5,maxFirstLegTravelExclusive:true,maxLegTravel:5,maxLegTravelExclusive:true}});
     }
     assert.equal(path,'/api/plans/generate');assert.deepEqual(body.firstTravel,first);assert.deepEqual(body.betweenTravel,first);assert.equal(body.transport,mode);assert.deepEqual(body.startingLocation,origin);
     assert.equal(body.maxFirstLegTravel,null);assert.equal(body.maxLegTravel,null);assert.equal(body.maxFirstLegTravelExclusive,false);assert.equal(body.maxLegTravelExclusive,false);assert.equal(body.date,'2026-11-08');assert.equal(body.location,'Hyderabad');assert.equal(body.optionsToken,undefined);
     return Response.json({message:'No eligible fixture venues under these limits.'},{status:422});
    };
    await generateOuting(source,{...EMPTY_PREFERENCES,transport:mode,location:'Hyderabad',date:'2026-11-08'},{prepareOrigin:async()=>({startingLocation:origin,firstTravel:first,betweenTravel:first})},send);
    assert.equal(count,2);
   }
  }
 }
});
test('local admission and true provider errors retain distinct safe explanations',()=>{
 for(const code of ['provider_local_rate_limit','provider_local_admission','provider_service_error'])assert.match(failureText({code,message:code,correlationId:'a'.repeat(16)},'fallback'),new RegExp(code));
});
