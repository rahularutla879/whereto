import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {createHash} from 'node:crypto';
import logo from '../data/google-attribution.json';
import {GoogleCredits} from '../components/venue-details';
import {PlanCard} from '../components/plan-card';
import {VenueDetailsSession} from './venue-details';
import type {Plan} from './planner';

test('official unmodified local Google logo and safe deduplicated provider credit',()=>{
 assert.equal(createHash('sha256').update(Buffer.from(logo.dataUrl.split(',')[1],'base64')).digest('hex'),logo.sha256);
 const html=renderToStaticMarkup(createElement(GoogleCredits,{credits:[{provider:'Authored credit',uri:'https://example.com'},{provider:'Authored credit',uri:'https://example.com'}]}));
 assert.match(html,/alt="Google Maps"/);assert.match(html,/height="18"/);assert.equal((html.match(/Authored credit/g)||[]).length,1);assert.doesNotMatch(html,/https:\/\/developers.google.com/);
});

test('card attribution remains outside hidden View Plan and provider Details',()=>{
 const venue={id:'Authored_A',providerPlaceId:'Authored_A',name:'Authored venue',activity:'coffee',duration:30,evidenceLabels:{attribution:{third_party:[{provider:'Authored source',uri:'https://example.com'}]}}};
 const plan={id:'authored',issues:[],theme:'warm',label:'Authored',title:'Authored outing',description:'Authored fixture',date:'2026-12-01',dataMode:'real',duration:null,travel:null,stops:[{venue,start:600,end:630}],venues:[venue],legs:[],prices:[]} as unknown as Plan;
 const html=renderToStaticMarkup(createElement(PlanCard,{plan,index:0,detailsSession:new VenueDetailsSession()}));
 assert.ok(html.indexOf('alt="Google Maps"')<html.indexOf('class="plan-details"'));
 assert.ok(html.indexOf('Authored source')<html.indexOf('class="plan-details"'));
 assert.equal((html.match(/alt="Google Maps"/g)||[]).length,1);
});
