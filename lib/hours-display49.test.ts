import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup as render} from 'react-dom/server';
import {destinationLabel,activityDisplay,transportLabel,outingDateLabel} from './display-format';
import {OpeningHours} from '../components/opening-hours';
import {SavedCards} from '../components/saved-cards';
import {RealVenueFacts} from '../components/real-venue-facts';
import {mergeRefreshed} from './saved-plan-refresh';
import {loadSavedDetails} from './saved-details-request';
import type {SavedPlan} from './saved-plans';
import type {HoursEvidence} from './venue-hours';
const hours:HoursEvidence={date:'2026-11-02',timezone:'America/New_York',basis:'current',status:'unverified',observedAt:'2026-11-02T12:00:00Z',periods:[{start:1320,end:1560}],weekly:['Monday: 10:00 PM–2:00 AM','Tuesday: Closed'],specialDay:true,message:'Arrival and activity availability are unverified.'};
test('central labels capitalize known values without changing arbitrary brands or provider identities',()=>{
 for(const [input,expected] of [['near me','Near Me'],['jersey city','Jersey City'],['new york','New York'],["O’Connor’s NY café","O’Connor’s NY café"],['iPhone experiences','iPhone experiences']])assert.equal(destinationLabel(input),expected);
 assert.equal(transportLabel('walking'),'Walking');assert.equal(transportLabel('driving'),'Driving');
 assert.equal(['dinner','drinks'].map(activityDisplay).join(' → '),'Dinner → Drinks');assert.equal(['food','mall'].map(activityDisplay).join(' → '),'Food → Mall');
 assert.equal(activityDisplay('custom:pottery class'),'Pottery class');assert.equal(activityDisplay('custom:Apple Store'),'Apple Store');assert.equal(activityDisplay('custom:NYC bookshops'),'NYC bookshops');assert.equal(outingDateLabel('2026-11-02'),'November 2, 2026');
});
test('expanded hours show date, timezone, overnight, special-day and indicative weekly status',()=>{
 const html=render(React.createElement(OpeningHours,{hours}));
 for(const text of ['Opening hours','November 2, 2026','America/New_York','10:00 PM','2:00 AM (next day)','Special-day hours','Typical weekly hours','Tuesday: Closed','unverified','Hours checked'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/Open during planned visit/);
 const typical=render(React.createElement(OpeningHours,{hours:{...hours,basis:'unavailable',periods:[],typicalPeriods:[{start:540,end:1020}],typicalClosed:false}}));assert.match(typical,/Typical hours: 9:00 AM–5:00 PM/);assert.match(typical,/Special-day changes are unverified/);
 assert.match(render(React.createElement(OpeningHours,{})),/Hours unverified/);
 assert.match(render(React.createElement(OpeningHours,{hours:{...hours,periods:[{start:0,end:1440}]}})),/Open 24 hours/);
});
test('real venue names and authorized ratings remain untouched alongside expanded hours',()=>{
 const html=render(React.createElement(RealVenueFacts,{venue:{name:'iPhone & NYC',address:'Verified ADDRESS',rating:4.5,ratingCount:12,hoursEvidence:hours} as never}));
 assert.match(html,/4.5/);assert.match(html,/12 Google ratings/);assert.match(html,/Verified ADDRESS/);assert.match(html,/Opening hours/);
});
const saved:SavedPlan={version:1,saved:true,dataMode:'real',hoursRefreshAvailable:true,selectedId:'one',expiresAt:'2026-12-01',liveDetailsAvailable:false,constraints:{location:'near me',date:'2026-11-02',activities:['food'],activityIntents:{food:'dinner'},startTime:600,endTime:1440,planningMode:'origin',transport:'walking',calendarTimezone:'America/New_York',firstTravel:null,betweenTravel:null,maxFirstLegTravel:null,maxLegTravel:null,travel:null,geography:{strictDestination:false,excludedRegions:[]},dinner:true,dinnerStops:[0],requireAvailability:false,requireWheelchairAccess:false,allowRevisits:false},itineraries:[{candidateId:'one',fictionalMetrics:null,stops:[{position:0,activity:'food',provider:'google_places',reference:'fixture',timingBasis:'unknown',start:null,end:null,duration:null,fictional:null}]}]};
test('saved selected view uses friendly casing, no quota introduction and a separate manual hours action',()=>{
 const html=render(React.createElement(SavedCards,{saved,venues:{fixture:{status:'refreshed',name:'iPhone & NYC',hoursEvidence:hours,website:'https://example.com',phone:'+12025550123',telephoneUrl:'tel:+12025550123',mapsUrl:'https://www.google.com/maps/search/?api=1&query=fixture'}},refresh(){},busy:false,message:''}));
 for(const text of ['Near Me','November 2, 2026','Walking','Dinner','iPhone &amp; NYC','Official website','Opening hours','Load opening hours'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/contacts Google Maps and uses API quota|Current venue information is shown below|Load current names/);
});
test('hours-only response preserves independently timestamped names and contact facts in page memory',()=>{
 const merged=mergeRefreshed({one:{status:'refreshed',name:'Original name',website:'https://example.com',refreshedAt:'earlier',attributions:[{provider:'Original credit',uri:'https://example.com/one'}]}},{one:{status:'refreshed',name:'New lookup name',hoursEvidence:hours,attributions:[{provider:'Hours credit',uri:'https://example.com/two'}]}},true);
 assert.equal(merged.one.name,'Original name');assert.equal(merged.one.website,'https://example.com');assert.equal(merged.one.refreshedAt,'earlier');assert.equal(merged.one.hoursEvidence,hours);assert.equal(merged.one.attributions?.length,2);
 const contacts=mergeRefreshed(merged,{one:{status:'refreshed',name:'New current name',website:'https://example.com/new'}});assert.equal(contacts.one.hoursEvidence,hours);assert.equal(contacts.one.attributions?.length,2);
});
test('default automatic action never requests hours; manual hours is one bounded explicit action',async()=>{
 const previous=globalThis.fetch;const bodies:Record<string,unknown>[]=[];
 globalThis.fetch=async(_url,init)=>{bodies.push(JSON.parse(String(init?.body)));return Response.json({candidateId:'selected',venues:{}});};
 try{await loadSavedDetails('A'.repeat(43),'selected');await loadSavedDetails('A'.repeat(43),'selected',false,true);}finally{globalThis.fetch=previous;}
 assert.equal(bodies[0].includeHours,undefined);assert.equal(bodies[0].includeContacts,false);assert.equal(bodies[1].includeHours,true);assert.equal(bodies[1].includeContacts,false);assert.notEqual(bodies[0].refreshId,bodies[1].refreshId);
});
