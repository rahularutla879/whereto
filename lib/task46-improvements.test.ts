import assert from "node:assert/strict";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { OutingDateField } from "../components/outing-date-field";
import { RealVenueFacts, VenueRating } from "../components/real-venue-facts";
import { planWarnings } from "./results-presentation";
import { StartingPlaceSession } from "./starting-places";
import type { Plan } from "./planner";
import demo from "../data/demo-plans.json";

const plan = (): Plan => ({ ...structuredClone(demo.plans[0]) as Plan, dataMode: "real", hardBudget: false, issues: [], constraintIssues: [], venues: [{ ...demo.plans[0].venues[0], address: "Synthetic Street", price: null, capacity: null, duration: null }] as Plan["venues"], travel: 5 });

test("ordinary real results omit unknown cost/capacity/duration while preserving useful facts and ratings", () => {
  const p = plan();
  const html = renderToStaticMarkup(React.createElement(RealVenueFacts, { venue: p.venues[0] }));
  assert.match(html, /Synthetic Street/);
  assert.doesNotMatch(html, /Unknown|Price not available|Cost not verified|capacity/i);
  assert.deepEqual(planWarnings(p), []);
  const rated = { ...p.venues[0], rating: 4.5, ratingCount: 320 };
  assert.match(renderToStaticMarkup(React.createElement(VenueRating, { venue: rated })), /4.5 ★ · 320 Google ratings/);
  for (const rating of [null, 0, NaN, 6]) assert.equal(renderToStaticMarkup(React.createElement(VenueRating, { venue: { ...rated, rating } })), "");
});

test("hard budgets, unknown travel, event sessions, dinner and future hard violations remain visible", () => {
  const p = plan(); p.hardBudget = true; p.travel = null;
  p.venues[0].activity = "movie";
  p.issues = ["Dinner service needs checking"];
  p.constraintIssues = [{ code: "future_hard_failure", field: "schedule", status: "violation", message: "Known closure conflicts with the requested time." }, { code: "unknown_duration", field: "duration", status: "unknown", message: "Unknown duration" }];
  const warnings = planWarnings(p).join(" ");
  assert.match(warnings, /hard budget cannot be verified/);
  assert.match(warnings, /Known closure/); assert.match(warnings, /showtimes/); assert.match(warnings, /Dinner service/); assert.match(warnings, /Travel time is missing/);
  assert.doesNotMatch(warnings, /Unknown duration/);
});

test("manual starting lookup is explicit, coalesced in active memory and preserves precision", async () => {
  const session = new StartingPlaceSession(); let calls = 0;
  const send: typeof fetch = async (_url, init) => {
    calls++; assert.deepEqual(JSON.parse(init!.body as string), { query: "Synthetic ZIP" });
    return Response.json({ matches: [{ placeId: "Fixture_area", name: "Synthetic ZIP", address: "Synthetic address", coordinates: { latitude: 39, longitude: -76 }, precision: "postal_area", attributions: [] }] });
  };
  assert.equal(calls,0);
  const matches = await session.get("Synthetic ZIP",send);
  assert.equal(matches[0].precision,"postal_area");
  assert.equal(await session.get(" synthetic zip ",send),matches); assert.equal(calls,1);
  session.clear(); await session.get("Synthetic ZIP",send); assert.equal(calls,2);
});

test("starting lookup errors are retained without retries and invalid provider coordinates are rejected", async () => {
  const session = new StartingPlaceSession();let calls=0;
  const send: typeof fetch = async () => {calls++;return Response.json({message:"Quota reached"},{status:422});};
  await assert.rejects(session.get("Synthetic area",send),/Quota reached/);
  await assert.rejects(session.get("Synthetic area",send),/Quota reached/);assert.equal(calls,1);
  await assert.rejects(new StartingPlaceSession().get("Synthetic area",async () => Response.json({matches:[{placeId:"fixture",name:"Fixture",address:"Fixture",coordinates:{latitude:999,longitude:1},precision:"city"}]})),/could not be verified/);
});

test("real date help distinguishes venue dates from confirmed sessions without fictional-data copy", () => {
  const html = renderToStaticMarkup(React.createElement(OutingDateField, { real: true, value: "2026-11-07", onChange: () => {} }));
  assert.match(html, /do not confirm event sessions/);
  assert.doesNotMatch(html, /fictional/);
});
