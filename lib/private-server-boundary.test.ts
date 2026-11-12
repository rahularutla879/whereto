import {test} from 'node:test';import assert from 'node:assert/strict';
import {privateRoute,createStatusOnlyProfile,installPrivateProfile} from './private-server-boundary';
import {POST as interpret} from '../app/api/interpret/route';
import {POST as generate} from '../app/api/plans/generate/route';
import {GET as health} from '../app/api/health/route';
import {GET as mode} from '../app/api/planning-mode/route';
import {GET as diagnostics} from '../app/api/development-diagnostics/route';
import {persistenceProxy} from './persistence-proxy';import {providerProxy} from './provider-proxy';
test('actual route entry points select only server-owned status composition; all business routes refuse without fallback',async()=>{
 assert.equal(privateRoute('/health'),null);let count=0;const r=()=>new Request('https://frontend.invalid/api/health',{headers:{'x-goog-iap-jwt-assertion':'verified-at-port'}});
 const profile=createStatusOnlyProfile('https://frontend.invalid','https://backend.invalid',{async verifyAndSeal(i){assert.equal(i.method,'GET');assert.equal(i.assertion,'verified-at-port');return{workloadToken:'server-owned',context:'server-owned'};}},async(_url,init)=>{count++;assert.equal(new Headers(init?.headers).get('authorization'),'Bearer server-owned');assert.equal(init?.redirect,'manual');return Response.json({status:'ok'},{headers:{'set-cookie':'do-not-forward'}});});
 assert.throws(()=>installPrivateProfile({handle:async()=>Response.json({})}));installPrivateProfile(profile);assert.throws(()=>installPrivateProfile(profile));
 assert.equal((await health(r())).status,200);assert.equal((await health()).status,403);assert.equal((await health(new Request(r(),{headers:{authorization:'forged'}}))).status,403);
 const body=()=>new Request('https://frontend.invalid/api/interpret',{method:'POST',body:'{}'});
 for(const v of [interpret(body()),generate(body()),mode(r()),...(['/api/plans/save','/api/plans/reopen','/api/plans/refresh','/api/plans/advanced'] as const).map(p=>persistenceProxy(p,body())),...(['/api/plans/options','/api/starting-areas','/api/starting-places','/api/venues/details'] as const).map(p=>providerProxy(p,body()))]){const response=await v;assert.equal(response.status,503);assert.equal((await response.json()).code,'hosted_route_unavailable');}
 assert.equal((await diagnostics(r())).status,404);assert.equal(count,1);
});
