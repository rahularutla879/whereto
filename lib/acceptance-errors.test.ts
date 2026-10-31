import test from "node:test";
import assert from "node:assert/strict";
import { developmentOriginHeaders } from "./development-origin";
import { classifiedFailure, failureText } from "./failure-diagnostics";
import { consumerMessage } from "./results-presentation";
import { adaptRanking } from "./planning-client";
import { execFileSync } from "node:child_process";

test("mapped loopback stays local for real development planning",()=>{
  const headers=developmentOriginHeaders(new Request("http://localhost/api/plans/generate",{headers:{host:"127.0.0.1:3000","x-forwarded-for":"::ffff:127.0.0.1","x-forwarded-host":"127.0.0.1:3000"}}));
  assert.equal(headers["X-WhereTo-Proxied"],"0");
  assert.equal(developmentOriginHeaders(new Request("http://localhost",{headers:{"x-forwarded-for":"203.0.113.1"}}))["X-WhereTo-Proxied"],"1");
});
test("classified internal/database/provider failures survive consumer presentation",()=>{
  for(const code of ["database_not_configured","database_authentication_failed","save_transaction_failed","provider_quota_rejected","internal_application_error","llm_interpretation_failed"]){
    const value={code,message:"Check the operation; your itinerary is kept.",correlationId:"0123456789abcdef"};
    const text=failureText(value,"fallback");assert.match(text,/0123456789abcdef/);assert.equal(consumerMessage(text),text);
  }
  assert.equal(classifiedFailure({code:"unknown",message:"SQL password SECRET"}),undefined);
  assert.equal(failureText({code:"unknown",message:"SQL SECRET"},"Safe fallback"),"Safe fallback");
});
test("actual one-stop Hyderabad backend shape renders three cinema cards",()=>{
  const code=`import os,json
from unittest.mock import patch
from backend.test_real_planning import ENV
from backend.acceptance_fixtures import search_fixture,matrix_fixture
from backend.real_planning import PlannerInput,real_plans
from backend.provider_budget import ProviderBudget
with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('Live forbidden')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
 r=real_plans(PlannerInput(activities=['movie'],location='Hyderabad',date='2026-11-14',calendarTimezone='Asia/Kolkata',locationFirst=True,startingLocation={'point':{'id':'test-origin','coordinates':{'latitude':17.44,'longitude':78.36}},'source':'manual','explicitly_authorized':True}),ProviderBudget())
 print(r.model_dump_json())`;
  const raw=JSON.parse(execFileSync('backend/.venv/bin/python',['-c',code],{encoding:'utf8'}));
  const result=adaptRanking(raw);assert.equal(result.plans.length,3);
  assert.ok(result.plans.every(p=>p.stops.length===1 && p.legs.length===0 && p.firstLeg?.minutes!==null));
  assert.deepEqual(result.activities,["movie"]);
});
