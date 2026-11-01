import test from 'node:test';
import assert from 'node:assert/strict';
import * as React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {planningMessage,restoreContinuation,continuationNotice} from './continuation';
import {savedLaunchToken} from './saved-navigation';
import {GoogleCredits} from '../components/venue-details';
import {AlternativeActions} from '../components/alternative-actions';
import {SavedPlans} from '../components/saved-plans';
import demoPlans from '../data/demo-plans.json';
import type {PlannerResult} from './planner';

test('exhaustion contractions and repeated API messages render once while distinct constraints remain',()=>{
 const first="We've shown the available combinations from the places checked so far. Explore farther to discover more.";
 assert.equal(planningMessage(first,[{message:'We have shown the available combinations from the places checked so far. Explore farther to discover more.'},{message:first}]),first);
 assert.equal(planningMessage('No options.',[{message:'Strict travel limit remains.'}]),'No options. Strict travel limit remains.');
 const empty={...structuredClone(demoPlans),plans:[],canExpand:false,canDiscover:false,continuationStatus:{kind:'search_exhausted',message:first}} as PlannerResult;
 assert.equal(continuationNotice(empty),'');assert.equal(continuationNotice(empty,'Explicit continuation failure'),'Explicit continuation failure');
});
test('normal launch never consumes remembered availability; explicit fragment and explicit tab refresh do',()=>{
 const key='A'.repeat(43);
 assert.equal(savedLaunchToken('',false,key),undefined);
 assert.equal(savedLaunchToken('#saved='+key,false,null),key);
 assert.equal(savedLaunchToken('',true,key),key);
 assert.equal(savedLaunchToken('#saved=broken',true,key),undefined);
 assert.equal(savedLaunchToken('',false,null),undefined);
});
test('page restoration retains current backend action availability without changing itinerary identity',()=>{
 const page=structuredClone(demoPlans) as PlannerResult;const latest={...page,canExpand:false,canDiscover:false,continuationStatus:{kind:'search_exhausted',message:'Final bounded search status'}};
 const restored=restoreContinuation({...page,canExpand:true,canDiscover:true},latest);
 assert.equal(restored.plans,page.plans);assert.equal(restored.canExpand,false);assert.equal(restored.canDiscover,false);assert.deepEqual(restored.continuationStatus,latest.continuationStatus);
});
test('continuation control flags cover known combinations, discovery, exhausted, paused and pending routes',()=>{
 for(const [combine,explore] of [[true,false],[false,true],[false,false],[true,true]]){
  const html=renderToStaticMarkup(React.createElement(AlternativeActions,{real:true,canCombine:combine,canExplore:explore,busy:false,disabled:false,notice:'One status',onAction(){},onAdjust(){}}));
  assert.equal((html.match(/One status/g)??[]).length,1);
  assert.equal((html.match(/disabled=""/g)??[]).length,Number(!combine)+Number(!explore));
 }
});
test('one card-level Google attribution can deduplicate required third-party credits',()=>{
 const credits=[{provider:'Synthetic credit',uri:'https://example.com'},{provider:'Synthetic credit',uri:'https://example.com'}];
 const html=renderToStaticMarkup(React.createElement(GoogleCredits,{credits}));
 assert.equal((html.match(/>Google Maps</g)??[]).length,1);assert.equal((html.match(/>Synthetic credit</g)??[]).length,1);
 const supplemental=renderToStaticMarkup(React.createElement(GoogleCredits,{credits,showGoogle:false}));
 assert.doesNotMatch(supplemental,/>Google Maps</);assert.match(supplemental,/Synthetic credit/);
});
test('saved management starts collapsed with no primary saved document',()=>{
 const html=renderToStaticMarkup(React.createElement(SavedPlans,{active:false,onOpen(){},contextKey:'normal'}));
 assert.match(html,/<details><summary>Saved plans/);assert.doesNotMatch(html,/Saved itineraries|<details open/);
});
