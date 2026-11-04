import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {resultsSummary,consumerMessage} from './results-presentation';
import {continuationNotice} from './continuation';
import type {PlannerResult} from './planner';
import {classifiedFailure,failureText} from './failure-diagnostics';

test('partial pages explain structured remaining work without implying a total city count',()=>{
 assert.equal(resultsSummary(2,{canExpand:true,canDiscover:true}), 'Found 2 options so far. More combinations may be available. You can also look for more nearby places.');
 assert.equal(resultsSummary(2,{canExpand:false,canDiscover:false}), 'Found 2 options so far.');
 assert.match(resultsSummary(3,{canExpand:true},8),/Found 8 options so far. Showing 3 on this page/);
 const page={plans:[{}],canExpand:false,canDiscover:true,continuationStatus:{kind:'checked_pool_exhausted'}} as PlannerResult;
 assert.equal(continuationNotice(page),'No more matching combinations found among the places checked so far. You can look for more nearby places.');
 assert.match(consumerMessage('This outing session expired.'),/still available to view. Regenerate/);
});
test('consumer errors retain distinct recovery without developer details or opaque references',()=>{
 for(const code of ['llm_timeout','llm_unavailable','llm_invalid_response','ai_unavailable']){
  const value={code,message:code==='llm_invalid_response'?"We couldn't finish understanding that request. Please try again or edit the wording.":"We're having trouble planning your outing right now. Please try again.",correlationId:'0123456789abcdef'};
  const rendered=renderToStaticMarkup(React.createElement('p',null,failureText(value,'fallback')));
  assert.doesNotMatch(rendered,/Ollama|Qwen|Python|JSON|0123456789abcdef/);
  assert.equal(classifiedFailure(value)?.correlationId,value.correlationId);
 }
 assert.doesNotMatch(consumerMessage('Check Ollama and retry.'),/Ollama/);
 assert.match(consumerMessage('Google Routes quota reached'),/Google.*limit/);
});
