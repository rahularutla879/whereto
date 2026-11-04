import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {execFileSync} from 'node:child_process';
import {mapsDirections} from './maps-directions';
import {adaptAdvanced,type AdvancedData} from './advanced-planning';
import {PlanCard} from '../components/plan-card';
import {RouteDirections} from '../components/route-directions';
import {VenueDetailsSession} from './venue-details';
const raw=JSON.parse(execFileSync('backend/.venv/bin/python',['-c',`
from backend.test_advanced_planning import IntegrationTests
from backend.test_advanced_routing import start
h=IntegrationTests('test_named_roundtrip_dto_and_receipt');h.setUp()
try:
 s=h.session([{'source':'grocery shopping'},{'source':'pharmacy'},{'source':'coffee'}],endpoint={'kind':'origin','source':'return to starting point'})
 print(h.run_session(s,startingLocation=start()).model_dump_json())
finally:h.doCleanups()
`],{encoding:'utf8'})) as AdvancedData;
const plan=adaptAdvanced(raw,{}).plans[0];
const render=()=>renderToStaticMarkup(createElement(PlanCard,{plan,index:0,detailsSession:new VenueDetailsSession()}));
test('every actual advanced leg has a separately blocked safe Maps action',()=>{
 const html=render();assert.equal((html.match(/View this leg on Google Maps/g)??[]).length,4);
 assert.equal((html.match(/class="route-directions"/g)??[]).length,4);
 assert.match(html,/Travel from previous stop:.*<\/span><div class="route-directions">/);
 assert.doesNotMatch(html,/<span>[^<]*Travel from previous stop:[\s\S]*?estimate\)\.\s*<a/);
 assert.match(html,/Enter your original starting point in Google Maps/);
 assert.match(html,/Google Maps uses your current location/);
 assert.doesNotMatch(html,/advanced_origin|private_start|latitude|longitude/);
});
test('outbound/intermediate/return links retain exact public direction and selected mode',()=>{
 for(const [index,leg] of raw.options[0].legs.entries()){
  const url=new URL(leg.mapsUrl!);assert.equal(url.pathname,'/maps/dir/');assert.equal(url.searchParams.get('api'),'1');assert.equal(url.searchParams.get('travelmode'),'driving');
  if(index===0){assert.equal(url.searchParams.get('origin'),null);assert.equal(url.searchParams.get('destination_place_id'),raw.options[0].stops[0].placeId);}
  else {assert.equal(url.searchParams.get('origin_place_id'),raw.options[0].stops[index-1].placeId);assert.equal(url.searchParams.get('destination_place_id'),raw.options[0].stops[index]?.placeId??null);}
 }
});
test('ordinary real legs use same link row without inventing a Surprise Me origin',()=>{
 const ordinary={...plan,advanced:undefined,firstLeg:undefined,planningMode:'surprise' as const};
 const html=renderToStaticMarkup(createElement(PlanCard,{plan:ordinary,index:0,detailsSession:new VenueDetailsSession()}));
 assert.equal((html.match(/View this leg on Google Maps/g)??[]).length,2);assert.doesNotMatch(html,/current location if available|original starting point in Google Maps/);
});
test('supported Maps defaults never fabricate private identity; same-place skips travel',()=>{
 assert.equal(mapsDirections(null,null,'drive'),null);assert.equal(mapsDirections('A','A','walk'),null);
 assert.equal(new URL(mapsDirections(null,'PublicCafe','walking')!).searchParams.get('travelmode'),'walking');
 assert.equal(new URL(mapsDirections('PublicCafe',null,'drive')!).searchParams.has('destination'),false);
});
test('unsafe directions links are not rendered and external action is keyboard-safe',()=>{
 assert.equal(renderToStaticMarkup(createElement(RouteDirections,{url:'javascript:alert(1)'})),'');
 const html=renderToStaticMarkup(createElement(RouteDirections,{url:mapsDirections('PublicA','PublicB','drive')}));
 assert.match(html,/target="_blank" rel="noopener noreferrer"/);assert.match(html,/href="https:\/\/www.google.com\/maps\/dir\//);
});
test('later selected venue identities produce later option links',()=>{
 const next=structuredClone(raw);next.options[0].stops[1].placeId='LaterPublicPharmacy';
 next.options[0].legs[1].mapsUrl=mapsDirections(next.options[0].stops[0].placeId,'LaterPublicPharmacy','walk');
 const html=renderToStaticMarkup(createElement(PlanCard,{plan:adaptAdvanced(next,{}).plans[0],index:1,detailsSession:new VenueDetailsSession()}));
 assert.match(html,/destination_place_id=LaterPublicPharmacy/);assert.match(html,/travelmode=walking/);
});
test('structured continuation reason survives adaptation and viewed history',async()=>{
 const {restoreContinuation}=await import('./continuation');
 const next=adaptAdvanced({...raw,options:[],canExpand:true,canDiscover:true,exploration:{combination:'unchecked_combinations',discovery:'available',message:'More combinations may fit.'}},{});
 const restored=restoreContinuation(adaptAdvanced(raw,{}),next);
 assert.equal(restored.plans[0].id,plan.id);assert.equal(restored.canExpand,true);assert.equal(restored.continuationStatus?.message,'More combinations may fit.');
});
