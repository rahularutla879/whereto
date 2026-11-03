import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {advancedDraft,advancedEdits,rememberAdvancedEdit,type AdvancedPreferences} from './advanced-preferences';
import type {AdvancedData} from './advanced-planning';
import {AdvancedPreferenceFields} from '../components/advanced-preferences';
import {VenueDetails,GoogleCredits} from '../components/venue-details';
import {VenueDetailsSession} from './venue-details';
import type {DisplayVenue} from './planner';
const atm={minutes:5,relation:'exact' as const,source:'ATM for 5 minutes'};
const preferences:AdvancedPreferences={stops:[{occurrence:0,requested:'Grocery shopping',duration:{minutes:20,relation:'exact',source:'Explicit user override'},originalDuration:null,override:true},{occurrence:1,requested:'ATM',duration:atm,originalDuration:atm,override:false}],budget:{minutes:45,relation:'maximum',source:'within 45 minutes'},budgetScope:'outing',scopeOverride:false,departure:null,departureOverride:false,returnToOrigin:true,endpoint:'return to start',choices:[]};
const data={preferences,questions:[]} as unknown as AdvancedData;
test('accepted answers hydrate editable canonical preferences and diff only changed grocery duration',()=>{
 const draft=advancedDraft(data)!;assert.equal(draft.stops[0].minutes,'20');assert.equal(draft.stops[1].minutes,'5');
 assert.deepEqual(advancedEdits(data,draft),{});draft.stops[0].minutes='10';
 assert.deepEqual(advancedEdits(data,draft),{dwell:[{occurrence:0,minutes:10,relation:'exact',zeroCountedTime:false}]});
 assert.equal(data.preferences!.stops[0].duration!.minutes,20);
});
test('scope edit keeps the single original budget and all stop answers',()=>{
 const draft=advancedDraft(data)!;draft.budgetScope='travel';assert.deepEqual(advancedEdits(data,draft),{budgetScope:'travel'});
 assert.equal(draft.stops.length,2);assert.equal(draft.stops[1].minutes,'5');
});
test('replay merges each occurrence and preserves independent choices and departure',()=>{
 const first=rememberAdvancedEdit([],{edits:{dwell:[{occurrence:0,minutes:20}],departure:'10:00',budgetScope:'travel'}});
 const next=rememberAdvancedEdit(first,{edits:{dwell:[{occurrence:0,minutes:10},{occurrence:1,minutes:8}]}});
 assert.deepEqual(next,[{edits:{dwell:[{occurrence:0,minutes:10},{occurrence:1,minutes:8}],departure:'10:00',budgetScope:'travel',choices:[]}}]);
 const reset=rememberAdvancedEdit(next,{edits:{resetDwell:[1],resetDeparture:true}});
 assert.deepEqual(reset,[{edits:{dwell:[{occurrence:0,minutes:10}],budgetScope:'travel',choices:[]}}]);
});
test('same preferences panel shows effective minutes original ATM scope and return',()=>{
 const html=renderToStaticMarkup(createElement(AdvancedPreferenceFields,{data,draft:advancedDraft(data)!,busy:false,onChange(){}}));
 for(const value of ['Grocery shopping duration (minutes)','value="20"','ATM duration (minutes)','value="5"','45 minutes for the entire outing, including stops','45 minutes for travel only','Original request: Exactly 5 minutes','Return to my confirmed starting point'])assert.ok(html.includes(value),value);
 assert.doesNotMatch(html,/<form/);
});
test('zero duration has an explicit counted-time acknowledgement and no omission control',()=>{
 const draft=advancedDraft(data)!;draft.budgetScope='travel';draft.stops[0].minutes='0';
 const html=renderToStaticMarkup(createElement(AdvancedPreferenceFields,{data,draft,busy:false,onChange(){}}));
 assert.match(html,/zero counted visit time/);assert.match(html,/not a realistic zero-minute visit/);assert.match(html,/type="checkbox" required=""/);
});
test('nested contact panel does not duplicate name address rating hours maps or Google branding',()=>{
 const venue={id:'fixture',providerPlaceId:'fixture',name:'Fixture cafe',address:'123 Fixture Street',mapsUrl:'https://www.google.com/maps/search/?api=1&query=Fixture',rating:4.7,ratingCount:88} as DisplayVenue;
 const html=renderToStaticMarkup(createElement(VenueDetails,{venue,primaryMaps:true,session:new VenueDetailsSession()}));
 assert.doesNotMatch(html,/123 Fixture Street|4\.7|88|View location on Google Maps|google-attribution|Opening hours/);
 assert.equal((html.match(/Contact the venue to arrange your visit/g)??[]).length,1);
 assert.match(html,/No reservation or ticket is confirmed/);
});
test('provider credits are deduplicated within their authorized display',()=>{
 const html=renderToStaticMarkup(createElement(GoogleCredits,{credits:[{provider:'Fixture credit',uri:'https://example.com'},{provider:'Fixture credit',uri:'https://example.com'}]}));
 assert.equal((html.match(/Fixture credit/g)??[]).length,1);assert.equal((html.match(/google-attribution/g)??[]).length,1);
});

test('a draft applied with nearby clarification keeps both answers for model-free replay',()=>{
 const next=rememberAdvancedEdit([],{searchNearOrigin:true,edits:{dwell:[{occurrence:0,minutes:20}]}});
 assert.equal(next[0].searchNearOrigin,true);
 const changed=rememberAdvancedEdit(next,{edits:{dwell:[{occurrence:0,minutes:10}]}});
 assert.equal(changed[0].searchNearOrigin,true);assert.deepEqual((changed[1].edits as {dwell:unknown[]}).dwell,[{occurrence:0,minutes:10}]);
});
