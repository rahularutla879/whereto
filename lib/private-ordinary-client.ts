// Memory-only private-profile controller. Display DTOs and handles are never authority.
import {privateOuting,type PrivateOuting} from './private-outing';
import {adaptRanking,type ValidatedOuting,type ClarificationAnswers} from './planning-client';
import {EMPTY_PREFERENCES,type Preferences,type PlannerResult} from './planner';
export const UI_VERSION='52-private-ordinary-ui-v1';
export type OrdinaryView={phase:'empty'|'pending'|'ready'|'finished'|'blocked';message:string;questions:{field:keyof ClarificationAnswers;question:string}[];summary?:Pick<ValidatedOuting,'request'|'explicitCost'|'explicitTime'>;result?:PlannerResult;expiresMs?:number};
export class PrivateOrdinaryClient {
 private handle?:PrivateOuting;private input?:{text:string;preferences:Preferences};private request?:ValidatedOuting['request'];private busy=false;private generation=0;
 view:OrdinaryView={phase:'empty',message:'Private synthetic ordinary planning only. Nothing resumes automatically after refresh.',questions:[]};
 constructor(private send:typeof fetch=(input,init)=>fetch(input,init)){}
 clear(message='This page does not restore outings or repeat provider requests. Start a new outing explicitly.') {this.generation++;this.busy=false;this.handle=undefined;this.input=undefined;this.request=undefined;this.view={phase:'empty',message,questions:[]};}
 expire(){if(this.handle&&this.handle.expiresMs<=Date.now()){this.handle=undefined;this.view={...this.view,phase:'blocked',questions:[],message:'This outing expired. Displayed cards are snapshots only. Start a new outing; no work was retried.'};}}
 private async post(path:string,value:unknown,signal?:AbortSignal){
  const generation=this.generation;const response=await this.send(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value),cache:'no-store',redirect:'manual',signal:AbortSignal.any([...(signal?[signal]:[]),AbortSignal.timeout(path.endsWith('generate')?120000:75000)])});
  if(!response.ok)throw Error('This outing could not continue safely. It may be expired, stale or interrupted. No automatic retry was made. Start a new outing explicitly.');
  const data=await response.json();if(generation!==this.generation)throw Error('Discarded page action.');return data;
 }
 private async turn(work:()=>Promise<void>){
  this.expire();if(this.busy)throw Error('An outing action is already in progress.');this.busy=true;const generation=this.generation;
  try{await work();}catch(error){if(generation!==this.generation)return;this.handle=undefined;this.view={...this.view,phase:'blocked',questions:[],message:error instanceof Error?error.message:'This outing stopped. Start a new outing explicitly.'};}finally{if(generation===this.generation)this.busy=false;}
 }
 private accept(data:Record<string,unknown>){
  this.handle=privateOuting(data.privateOuting);if(!this.handle)throw Error('Owned outing missing. No planning was attempted.');
  const questions=data.questions as OrdinaryView['questions'];if(!Array.isArray(questions)||!questions.every(q=>q&&['date','location','people','activities','time','endpoint'].includes(q.field)&&typeof q.question==='string'))throw Error('Invalid clarification.');
  const base={questions,expiresMs:this.handle.expiresMs};
  if(data.advancedToken||data.executionStatus==='advanced_unavailable'||(!data.request&&!questions.length)){this.request=undefined;this.view={...base,phase:'blocked',questions:[],message:'This request needs advanced or unsupported planning. Optional, flexible and return requirements have not been simplified. Edit the request or start a new outing.'};return;}
  if(questions.length){this.view={...base,phase:'pending',message:'Answer the requested clarification. Original source and expiry are retained; no new inference is needed.'};return;}
  if(!data.request||!Array.isArray(data.issues)||(data.issues as unknown[]).length)throw Error('Requirements could not be validated. Start a new outing.');
  const facts=data.interpretation as {cost?:unknown;time_expressions?:unknown}|undefined,answers=(data.pending as {answers?:{time?:unknown}}|undefined)?.answers;
  this.request=data.request as ValidatedOuting['request'];this.view={...base,phase:'ready',summary:{request:this.request,explicitCost:!!this.input?.preferences.costExplicit||facts?.cost!=null,explicitTime:!!(Array.isArray(facts?.time_expressions)&&facts.time_expressions.length||answers?.time)},message:'Requirements validated. Confirm execution controls, then generate once. No provider work is authorized by this display.'};
 }
 async interpret(text:string,preferences:Preferences=EMPTY_PREFERENCES,signal?:AbortSignal){
  if(this.view.phase!=='empty')throw Error('Discard the previous outing before starting another.');
  return this.turn(async()=>{this.input={text,preferences:structuredClone(preferences)};this.accept(await this.post('/api/interpret',this.input,signal));});
 }
 async answer(answers:ClarificationAnswers,signal?:AbortSignal){
  return this.turn(async()=>{if(this.view.phase!=='pending'||!this.handle||!this.input)throw Error('No current pending outing. Start a new outing.');this.accept(await this.post('/api/interpret',{...this.input,privateOuting:this.handle,answers},signal));});
 }
 async generate(latitude:number,longitude:number,radius?:number,signal?:AbortSignal){
  return this.turn(async()=>{
   if(this.view.phase!=='ready'||!this.handle||!this.request)throw Error('No current executable outing. Start a new outing.');
   if(!Number.isFinite(latitude)||latitude< -90||latitude>90||!Number.isFinite(longitude)||longitude< -180||longitude>180||radius!==undefined&&(!Number.isFinite(radius)||radius<=0||radius>50000))throw Error('Confirm valid coordinates and a search radius up to 50000 metres.');
   const result=adaptRanking(await this.post('/api/plans/generate',{...this.request,privateOuting:this.handle,startingLocation:{point:{id:'authorized-start',coordinates:{latitude,longitude}},explicitly_authorized:true,source:'manual',precision:'address_or_place'},...(radius===undefined?{}:{searchRadius:radius})},signal));
   this.handle=undefined;this.view={...this.view,phase:'finished',questions:[],result,message:'Synthetic itinerary snapshots. Generation is consumed; cards cannot authorize another request. Saving, discovery and provider Details are unavailable.'};
  });
 }
 async discard(signal?:AbortSignal){return this.turn(async()=>{const handle=this.handle;this.handle=undefined;if(handle)await this.post('/api/private-ordinary/revoke',{privateOuting:handle},signal);this.clear('Previous authority discarded. Edit the source/preferences, then explicitly start a new interpretation.');});}
}
