import assert from "node:assert/strict";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import demo from "../data/demo-plans.json";
import type { Plan } from "./planner";
import { ResultsInformation } from "../components/results-information";
import { consumerMessage, DEMO_DISCLOSURE, estimateNotes, failureMessage, OPENING_HOURS_ISSUE, planWarnings, resultsSummary } from "./results-presentation";

const plan = (): Plan => ({ ...(structuredClone(demo.plans[0]) as Plan), feasibility: "provisional", issues: [OPENING_HOURS_ISSUE] });

test("results have one plain-language count, including singular and empty results", () => {
  assert.equal(resultsSummary(3), "Found 3 possible plans.");
  assert.equal(resultsSummary(1), "Found 1 possible plan.");
  assert.equal(resultsSummary(0), "Found 0 possible plans.");
  assert.equal(consumerMessage("0 confirmed mock recommendations; 3 provisional alternatives."), "");
});

test("common notices are consolidated while user-relevant notes are retained", () => {
  const notes = estimateNotes([
    "AI interpretation; itinerary calculations use the Python planner and fictional catalog.",
    "All shared-catalog venues, prices, schedules, capacity and travel are fictional.",
    "Costs exclude transport, tax, tips, booking fees and extras; shopping excludes purchases and free picnic requires your own food.",
    "Travel excludes the first/last trip; the default simulation ignores transport mode.",
    "Confirmed means constraints checked against supplied data, never a real booking or real availability.",
    "Manual people overrides the text interpretation.", "Stated preferences: quiet.", "Stated preferences: quiet.",
  ]);
  assert.deepEqual(notes, ["Using the group size you selected.", "Stated preferences: quiet."]);
});

test("routine hours disclosure stays secondary, but conflicts and specific unknowns stay by the plan", () => {
  const p = plan();
  assert.deepEqual(planWarnings(p), []);
  p.issues.push("Earlier stops and travel cannot reach the fixed event start; change order or activities.", "Obtain group capacity before confirming this stop.", "availability cannot be checked; obtain structured windows for the requested day.");
  const warnings = planWarnings(p);
  assert.equal(warnings.length, 3);
  assert.match(warnings.join(" "), /cannot reach.*accommodate your group.*Availability/);
  assert.equal(p.issues.length, 4, "presentation does not mutate engine issues");
});

test("missing price, travel, timing and group capacity remain prominent even without issue text", () => {
  const p = plan();
  p.price = null; p.travel = null; p.stops[0].start = null; p.venues[0].capacity = null;
  const warnings = planWarnings(p).join(" ");
  assert.match(warnings, /prices are unknown/);
  assert.match(warnings, /Travel time is unknown/);
  assert.match(warnings, /timings are unknown/);
  assert.match(warnings, /group-size limits are unknown/);
});

test("failed plans retain the actionable violation without technical count or service names", () => {
  const message = consumerMessage("0 confirmed mock recommendations; 0 provisional alternatives. No candidate satisfies all known limits. Review rejection reasons and adjust the relevant constraint. Known activity costs exceed budget; increase the cap or choose cheaper activities.");
  assert.match(message, /No plan fits all your current preferences/);
  assert.match(message, /exceed your per-person budget/);
  assert.doesNotMatch(message, /confirmed mock|provisional alternatives|candidate/);
  for (const failure of [
    "Python planner unavailable. Start the backend and try again. No plan was generated.",
    "AI interpretation unavailable or timed out. Start the Python backend and local AI service, then retry. No plan was generated.",
    "AI interpretation or Python planner unavailable, timed out, or returned an invalid response. Check both services and retry. No plan was generated.",
  ]) {
    const text = consumerMessage(failure);
    assert.doesNotMatch(text, /Python|backend|services|AI interpretation/);
    assert.match(text, /could not/);
    assert.match(text, /No plan was generated/);
  }
  const budgetFailure = failureMessage(`Known activity costs exceed budget; increase the cap. ${OPENING_HOURS_ISSUE}`);
  assert.match(budgetFailure, /exceed your per-person budget/);
  assert.doesNotMatch(budgetFailure, /Opening hours/);
  assert.match(failureMessage("0 confirmed mock recommendations; 0 provisional alternatives."), /could not find a plan/);
  assert.match(consumerMessage("Skydiving is unsupported. No partial plan was created."), /Skydiving is unsupported/);
});

test("estimates disclosure is collapsed, accessible and includes all secondary explanations", () => {
  const html = renderToStaticMarkup(React.createElement(ResultsInformation, { notes: [], needsChecking: true }));
  assert.match(html, /aria-label="About these sample results"/);
  assert.match(html, /<summary>About these estimates<\/summary>/);
  assert.doesNotMatch(html, /<details[^>]*\bopen\b/);
  assert.equal(html.split(DEMO_DISCLOSURE).length - 1, 1);
  for (const text of ["Opening hours", "availability", "taxes", "Transport fares", "first stop", "returning home", "chosen transport"]) assert.ok(html.includes(text), text);
  assert.doesNotMatch(html, /Python|shared catalog|confirmed mock/);
});
