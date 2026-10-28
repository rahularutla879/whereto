import test from "node:test";
import assert from "node:assert/strict";
import { ItineraryPages, beyondPage } from "./itinerary-pages";
import demo from "../data/demo-plans.json";
import type { PlannerResult } from "./planner";
const demoPlans=demo as PlannerResult;

test("saved pages navigate without I/O, deduplicate, preserve snapshots and reset", () => {
  const history=new ItineraryPages();
  const first=structuredClone(demoPlans);
  assert.equal(history.append(first),true);
  assert.equal(history.append(first),false);
  const second=structuredClone(first);
  second.plans=second.plans.map(p=>({...p,id:p.id+"new",venues:p.venues.map(v=>({...v,id:v.id+"new"}))}));
  assert.equal(history.append(second),true);
  second.plans[0].title="mutated";
  assert.notEqual(history.pages[1].plans[0].title,"mutated");
  assert.equal(history.index,1);
  assert.equal(history.navigate(1),undefined);
  assert.equal(history.navigate(-1)?.plans[0].title,first.plans[0].title);
  assert.equal(history.navigate(-1),undefined);
  assert.equal(history.pages.length,2);
  assert.equal(history.navigate(1)?.plans.length,3);
  history.reset();assert.equal(history.pages.length,0);
});
test("beyond pages preserve classification while no-result actions preserve position",()=>{
  const history=new ItineraryPages();
  const result=structuredClone(demoPlans);
  result.plans[0].travelClassification="beyond_limit";
  result.plans[0].travelDeviations=["First journey: 16 minutes exceeds 10 minutes."];
  assert.equal(beyondPage(result),true);
  history.append(result);
  assert.equal(history.append({...result,plans:[]}),false);
  assert.equal(history.index,0);
  assert.equal(history.pages[0].plans[0].travelClassification,"beyond_limit");
});

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ItineraryPagination } from "../components/itinerary-pagination";
test("page navigation has labeled native buttons, live indicator and disabled boundaries",()=>{
  const first=renderToStaticMarkup(createElement(ItineraryPagination,{index:0,count:3,busy:false,onNavigate:()=>{throw Error("render cannot navigate");}}));
  assert.match(first,/Previous itinerary page" disabled/);
  assert.match(first,/Page 1 of 3/);
  assert.match(first,/aria-live="polite"/);
  const last=renderToStaticMarkup(createElement(ItineraryPagination,{index:2,count:3,busy:false,onNavigate:()=>{}}));
  assert.match(last,/Next itinerary page" disabled/);
  const pending=renderToStaticMarkup(createElement(ItineraryPagination,{index:1,count:3,busy:true,onNavigate:()=>{}}));
  assert.equal((pending.match(/disabled=""/g)??[]).length,2);
});
