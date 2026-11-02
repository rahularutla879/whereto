import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { AlternativeActions } from "../components/alternative-actions";
import { ResultsInformation } from "../components/results-information";
import { ItineraryPages } from "./itinerary-pages";
import type { PlannerResult, Plan } from "./planner";

test("nearby and beyond-limit actions are explicit, distinct and keyboard-native",()=>{
 const html=renderToStaticMarkup(createElement(AlternativeActions,{real:true,canCombine:true,canExplore:true,canShowBeyond:true,nearby:true,busy:false,disabled:false,notice:"",onAction(){},onAdjust(){},onBeyond(){}}));
 assert.match(html,/alternative-row.*Show different options<\/button><p>Try new combinations/);
 assert.match(html,/Search more nearby places/);assert.match(html,/Show options beyond my limit/);
 assert.match(html,/keeping your current travel limits/);
 const back=renderToStaticMarkup(createElement(AlternativeActions,{real:true,canCombine:true,canExplore:true,busy:false,disabled:false,notice:"",showingBeyond:true,onAction(){},onAdjust(){},onCompliant(){}}));
 assert.match(back,/Return to within-limit options/);
});

test("ordinary page has no numeric budget, spending modes or development banner",()=>{
 const page=readFileSync("app/page.tsx","utf8");
 for(const text of ["<ExplorationNotice","Maximum budget","cost-field","Number of people"])assert.ok(!page.includes(text),text);
 const html=renderToStaticMarkup(createElement(ResultsInformation,{real:true,needsChecking:true,notes:["Development usage — searches 3; estimated gross $0.20","Venue hours need confirmation."]}));
 assert.doesNotMatch(html,/Developer diagnostics|Development usage/);
 assert.doesNotMatch(html,/<details[^>]*open/);
 assert.match(html,/Check venue hours/);
});

test("explicit beyond page remains separate and earlier compliant snapshot is immutable",()=>{
 const pages=new ItineraryPages();
 const plan=(id:string,classification:Plan['travelClassification'])=>({venues:[{id,providerPlaceId:id,activity:"food"}],travelClassification:classification} as Plan);
 const matching={plans:[plan("near","matching")]} as PlannerResult;
 pages.append(matching);pages.append({plans:[plan("far","beyond_limit")]} as PlannerResult);
 assert.equal(pages.pages.length,2);assert.equal(pages.navigate(-1)?.plans[0].travelClassification,"matching");
 assert.equal(pages.navigate(1)?.plans[0].travelClassification,"beyond_limit");
 assert.deepEqual(matching.plans.map(p=>p.venues[0].id),["near"]);
});
