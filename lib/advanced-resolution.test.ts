import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import {ClarificationField} from '../components/clarification-field';
import {PlanningFeedback} from '../components/planning-feedback';
import {generateOuting, type PendingOuting} from './planning-client';

test('advanced status is honest and cannot generate cards or call the planner',async()=>{
  let calls=0;
  const result=await generateOuting('Go to SUNY College of Optometry then coffee today.',undefined,undefined,async()=>{
    calls++;return Response.json({issues:['Advanced planning is still being added.'],notes:[],unsupported:['Advanced planning is still being added.'],executionStatus:'advanced_unavailable',request:{activities:['coffee']}});
  });
  assert.equal(calls,1);assert.equal(result.advancedUnavailable,true);assert.deepEqual(result.plans,[]);
  const html=renderToStaticMarkup(createElement(PlanningFeedback,{loading:false,needsClarification:false,failed:false,advancedUnavailable:true,message:result.message,onRetry(){},onEdit(){}}));
  assert.match(html,/Your request is understood/);assert.doesNotMatch(html,/Let’s tweak|simplify/);
});

test('home field offers a keyboard accessible explicit return option',()=>{
  const html=renderToStaticMarkup(createElement(ClarificationField,{question:{field:'endpoint',kind:'essential',question:'Where should the outing end?'},value:'',onChange(){}}));
  assert.match(html,/Address or named destination/);assert.match(html,/<button type="button"[^>]*>Return to my starting point/);
  assert.doesNotMatch(html,/supported-activities/);
});

test('field-only endpoint continuation retains original text and preference payload',async()=>{
  const text='Go grocery shopping, then return home within 45 minutes today.';
  const pending:PendingOuting={pending:{text,interpretation:{journey:{endpoint:{kind:'home',source:'return home'},total_duration:{minutes:45}}},answers:{},referenceTime:'2026-11-02T15:00:00Z'},questions:[{field:'endpoint',kind:'essential',question:'Where should the outing end?'}]};
  let question:PendingOuting|null=null;
  const send:typeof fetch=async(_url,init)=>{
    const input=JSON.parse(String(init?.body));assert.equal(input.text,text);assert.equal(input.preferences.transport,'walking');
    if(input.pending){assert.deepEqual(input.pending,pending.pending);assert.equal(input.answers.endpoint,'Return to my starting point');return Response.json({issues:['Advanced route planning is still being added.'],unsupported:['Advanced route planning is still being added.'],executionStatus:'advanced_unavailable',notes:[],request:null,pending:{...pending.pending,answers:input.answers},questions:[]});}
    return Response.json({issues:['Where should the outing end?'],notes:[],pending:pending.pending,questions:pending.questions,request:null});
  };
  const preferences={location:'Baltimore',date:'2026-11-07',people:'',budget:'',travel:'',cost:'balanced' as const,transport:'walking' as const};
  await generateOuting(text,preferences,{onClarification:value=>{question=value;}},send);
  assert.deepEqual(question,pending);
  const result=await generateOuting(text,preferences,{continuation:pending,answers:{endpoint:'Return to my starting point'},onClarification:value=>{question=value;}},send);
  assert.equal(result.advancedUnavailable,true);assert.deepEqual(result.plans,[]);
  assert.deepEqual((question as PendingOuting | null)?.pending.answers,{endpoint:'Return to my starting point'});
});
