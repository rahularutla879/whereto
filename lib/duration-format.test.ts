import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {formatDuration,formatSeconds} from './duration-format';
import {AdvancedDetails} from '../components/advanced-plan';
import type {AdvancedOption} from './advanced-planning';
test('shared seconds policy handles boundaries without float artifacts or negative zero',()=>{
 for(const [input,expected] of [[10,'10 sec'],[59.999,'1 min'],[60,'1 min'],[119*60,'1 hr 59 min'],[7210,'2 hr 10 sec'],[-0,'0 sec']] as const)assert.equal(formatSeconds(input),expected);
 assert.equal(formatDuration(59.3166666667),'59 min 19 sec');
 assert.equal(formatSeconds(59.999999999,'lower'),'59 sec');
 assert.equal(formatSeconds(60.000000001,'upper'),'1 min 1 sec');
 assert.equal(formatSeconds(59.999,'lower'),'59 sec');assert.equal(formatSeconds(59.001,'upper'),'1 min');
 assert.equal(formatDuration(null),'Unknown');assert.equal(formatSeconds(Infinity),'Unknown');
});
test('rendered bounded and unknown advanced durations remain readable and qualified',()=>{
 const base={knownTravelSeconds:3559,ending:'origin',totalConstraint:{minutes:45,relation:'under',source:'under 45 minutes'},durationState:'unverified',budgetScope:'outing',elapsedLowerSeconds:7210,elapsedUpperSeconds:null,state:'unverified',omitted:[]} as unknown as AdvancedOption;
 let html=renderToStaticMarkup(createElement(AdvancedDetails,{option:base}));
 assert.match(html,/59 min 19 sec/);assert.match(html,/at least 2 hr 10 sec/);assert.match(html,/Under 45 min/);assert.match(html,/visit timing needs confirmation/);assert.doesNotMatch(html,/\d\.\d{5}/);
 html=renderToStaticMarkup(createElement(AdvancedDetails,{option:{...base,elapsedLowerSeconds:60,elapsedUpperSeconds:90.001,upperExclusive:true}}));
 assert.match(html,/1 min to under 1 min 31 sec/);
 html=renderToStaticMarkup(createElement(AdvancedDetails,{option:{...base,elapsedLowerSeconds:119.9,elapsedUpperSeconds:119.9}}));
 assert.match(html,/Whole journey: 2 min/);
});

test('backend explanation formatter follows the same seconds presentation policy',async()=>{
 const {execFileSync}=await import('node:child_process');
 const values=[10,59.999,60,3559,7140,7210,2700];
 const output=JSON.parse(execFileSync('backend/.venv/bin/python',['-c',`import json;from backend.display_duration import seconds_text;print(json.dumps([seconds_text(x) for x in ${JSON.stringify(values)}]))`],{encoding:'utf8'}));
 assert.deepEqual(output,values.map(v=>formatSeconds(v)));
});
