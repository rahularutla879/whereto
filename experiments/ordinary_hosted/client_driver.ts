// Actual application browser-client contract, driven over local HTTP; not a browser UI test.
import {readFileSync} from 'node:fs';import assert from 'node:assert/strict';
import {generateOuting,type PendingOuting} from '../../lib/planning-client';
async function main(){
 const c=JSON.parse(readFileSync(process.argv[2],'utf8')),base=process.argv[3];let pending:PendingOuting|null=null;
 const send:typeof fetch=(url,init)=>fetch(base+String(url),{...init,headers:{...init?.headers,Origin:'https://frontend-task52-offline.run.app','X-Task52-Local-Ingress':c.ingress,'X-Goog-IAP-JWT-Assertion':c.user},redirect:'manual'});
 const origin={startingLocation:{point:{id:'authorized-start',coordinates:{latitude:39.29,longitude:-76.61}},explicitly_authorized:true as const,source:'manual' as const,precision:'address_or_place' as const}};
 const first=await generateOuting('Coffee and museum in Baltimore',undefined,{onClarification:p=>{pending=p;},locationContext:origin},send);assert.equal(first.plans.length,0);assert.ok(pending);
 const next=await generateOuting('Coffee and museum in Baltimore',undefined,{continuation:pending,answers:{date:'2026-11-07'},locationContext:origin},send);assert.ok(next.plans.length>0,next.message);assert.deepEqual(next.activities,['coffee','museum']);console.log('Actual generateOuting pending-to-plan HTTP contract passed.');
}
void main().catch(()=>{console.error('Application client contract refused');process.exitCode=1;});
