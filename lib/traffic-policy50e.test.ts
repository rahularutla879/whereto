import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {ResultsInformation} from '../components/results-information';
test('one current-traffic notice qualifies future driving without promising Maps parity',()=>{
 const html=renderToStaticMarkup(createElement(ResultsInformation,{real:true,walking:false,notes:[],needsChecking:true}));
 const sentence='Travel times are based on current Google traffic estimates. Actual travel times may change, especially for future outings.';
 assert.equal(html.split(sentence).length-1,1);assert.doesNotMatch(html,/exclude live traffic|without live traffic|identical to Google Maps/);
});
test('walking disclosure never implies traffic-aware walking',()=>{
 const html=renderToStaticMarkup(createElement(ResultsInformation,{real:true,walking:true,notes:[],needsChecking:true}));
 assert.match(html,/Walking times use current Google route estimates/);assert.match(html,/Walking routes are in beta/);assert.doesNotMatch(html,/current Google traffic/);
});
