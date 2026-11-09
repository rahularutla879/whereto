import { test } from "node:test";
import { developmentOriginHeaders } from "./development-origin";
import { once } from "node:events";
import { spawn, type ChildProcess } from "node:child_process";
import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ExplorationNotice, explorationStage } from "../components/exploration-notice";
import { ResultsInformation } from "../components/results-information";

async function stopFixture(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const exited = once(child, "exit"); // Listen before sending the signal.
  child.kill("SIGTERM");
  await exited;
}

test("fixture cleanup handles an exit that already happened", async () => {
  const child = spawn(process.execPath, ["-e", "process.exit(7)"]);
  await once(child, "exit");
  await stopFixture(child);
  assert.equal(child.exitCode, 7);
});

test("fixture cleanup terminates and reaps a running child without sleeps", async () => {
  const child = spawn(process.execPath, ["-e", "process.send('ready'); setInterval(() => {}, 1000)"],
    { stdio: ["ignore", "ignore", "ignore", "ipc"] });
  try {
    await once(child, "message");
    await stopFixture(child);
    assert.equal(child.signalCode, "SIGTERM");
  } finally {
    await stopFixture(child);
  }
});

test("development exploration notice is explicit and disappears when disabled", () => {
  assert.equal(renderToStaticMarkup(React.createElement(ExplorationNotice, { active: false })), "");
  assert.match(renderToStaticMarkup(React.createElement(ExplorationNotice, { active: true })), /role="status".*DEVELOPMENT EXPLORATION.*estimated usage recorded/);
});
test("continuation distinguishes place discovery from route checking without a retry flash", () => {
  assert.match(explorationStage(true), /finding more places/);
  assert.match(explorationStage(false), /Checking routes/);
  assert.doesNotMatch(explorationStage(true), /retry|failed/i);
});
test("developer usage is excluded from the normal recommendation disclosure", () => {
  const html=renderToStaticMarkup(React.createElement(ResultsInformation, { real: true, needsChecking: true, notes: ["Development usage — estimated gross $0.25; Cloud billing not verified."] }));
  assert.match(html, /<details[^>]*><summary>About these recommendations<\/summary>/);
  assert.doesNotMatch(html,/Development usage|estimated gross|Cloud billing/);
  assert.doesNotMatch(html, /<details[^>]*open/);
});

test("offline exploration HTTP boundaries and contacts share persistent nonblocking usage accounting", async () => {
  const { createServer } = await import("node:http");
  const { mkdtemp, rm } = await import("node:fs/promises");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");
  const dir=await mkdtemp(join(tmpdir(),"whereto-exploration-test-"));
  const listener=createServer(); listener.listen(0,"127.0.0.1");await once(listener,"listening");
  const address=listener.address();assert.ok(address && typeof address==="object");
  await new Promise<void>(r=>listener.close(()=>r()));
  const base=`http://127.0.0.1:${address.port}`;
  // This explicit fake-only server forbids real sends. Do not let the parent
  // runner's CI flag select production real-provider admission in the child.
  const fixtureEnvironment: NodeJS.ProcessEnv = { ...process.env, WHERETO_DEV_DAILY_USD: "0.29", WHERETO_DEV_WARN_USD: "0.29" };
  delete fixtureEnvironment.CI;
  const child=spawn("backend/.venv/bin/python",["-m","backend.real_fixture_server","--port",String(address.port),"--reference-time","2026-11-05T15:00:00+00:00","--exploration-ledger",join(dir,"usage.json")],{env:fixtureEnvironment});
  const post=(path:string,body:unknown)=>fetch(`${base}${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  try {
    for(let i=0;i<600;i++){if(child.exitCode!==null||child.signalCode!==null)throw new Error("Synthetic fixture server exited before readiness");try{if((await fetch(`${base}/health`)).ok)break;}catch{ /* Wait only for the local fixture server. */ }await new Promise(r=>setTimeout(r,50));}
    const mode=await (await fetch(`${base}/api/planning-mode`)).json();
    assert.equal(mode.explorationEnabled,true);
    assert.equal((await fetch(`${base}/health`,{headers:{Origin:"https://example.com"}})).status,403);
    assert.equal((await fetch(`${base}/health`,{headers:{"X-Forwarded-For":"127.0.0.1"}})).status,403);
    assert.equal((await fetch(`${base}/health`,{headers:developmentOriginHeaders(new Request("https://public.example/test"))})).status,403);
    const response=await post("/api/plans/generate",{activities:["bowling","food"],location:"Baltimore",people:2,date:"2026-11-07",startingLocation:{point:{id:"authorized-start",place_id:"Fixture_origin_0"},source:"manual",explicitly_authorized:true}});
    assert.equal(response.status,200);
    const result=await response.json();assert.equal(result.provisionalPlans.length,3);
    assert.equal(result.diagnostics.explorationMode,true);
    assert.equal(result.diagnostics.estimatedDayGrossUsd,.49);
    assert.equal(result.diagnostics.dispatched.matrixElements,42);
    const before=await(await fetch(`${base}/__test/counts`)).json();
    const detail=await post("/api/venues/details",{token:result.detailsToken,placeId:result.provisionalPlans[0].candidate.venues[0].id});
    assert.equal(detail.status,200);const contact=await detail.json();assert.equal(contact.diagnostics.estimatedUsageWarning,true);assert.equal(contact.diagnostics.costAdmissionEnforced,false);
    assert.equal((await(await fetch(`${base}/__test/counts`)).json()).details,before.details+1);
    assert.ok(result.provisionalPlans.every((p:{candidate:{venues:{providerPlaceId:string}[]}})=>p.candidate.venues.every(v=>v.providerPlaceId)));
  } finally {await stopFixture(child);await rm(dir,{recursive:true,force:true});}
});

test("proxies retain public host, origin and forwarded-request evidence for exploration admission",()=>{
 const request=new Request("https://public.example/api/plans/options",{headers:{Origin:"https://public.example","X-Forwarded-For":"192.0.2.1"}});
 assert.deepEqual(developmentOriginHeaders(request),{"X-WhereTo-Client-Host":"public.example","X-WhereTo-Client-Origin":"https://public.example","X-WhereTo-Proxied":"1"});
});
