import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StartingConfirmation } from "./starting-confirmation";
import { StartingPlaceSession } from "./starting-places";
import type { LocationContext } from "./planning-client";
import { PlanningFeedback } from "../components/planning-feedback";
import { LocationControls } from "../components/location-controls";
import { outingDetails } from "../components/outing-summary";
import type { ValidatedOuting } from "./planning-client";

const origin: LocationContext = { startingLocation: { point: { id: "authorized-start", coordinates: { latitude: 0, longitude: 0 } }, precision: "neighborhood", explicitly_authorized: true }, maxFirstLegTravel: 15 };
test("pending outing waits for explicit starting selection and continues once with its original limits", async () => {
  const choice = new StartingConfirmation(); let planned = 0;
  const text = "union station, washington dc";
  const lookup = new StartingPlaceSession(); let searches = 0;
  const send: typeof fetch = async () => { searches++; return Response.json({ matches: [{ placeId: "Synthetic_place", name: "Synthetic station", address: "Synthetic DC", precision: "neighborhood", coordinates: { latitude: 0, longitude: 0 }, attributions: [] }] }); };
  const submitted = choice.wait().then(value => { if (value) { planned++; assert.deepEqual(value, origin); } });
  await lookup.get(text, send); await lookup.get(text, send);
  assert.equal(searches, 1); assert.equal(planned, 0);
  assert.equal(choice.confirm(origin), true); await submitted;
  assert.equal(planned, 1); assert.equal(text, "union station, washington dc");
  assert.equal(choice.confirm(origin), false);
});
test("editing, removal, failure or unmount cancels a pending outing and prevents stale resume", async () => {
  const choice = new StartingConfirmation();
  const old = choice.wait(); choice.cancel(); assert.equal(await old, null);
  assert.equal(choice.confirm(origin), false);
  const first = choice.wait(), next = choice.wait(); assert.equal(await first, null);
  choice.cancel(); assert.equal(await next, null);
});
test("lookup failure and quota information stay actionable without duplicate automatic requests", async () => {
  const session = new StartingPlaceSession(); let calls = 0;
  const send: typeof fetch = async () => { calls++; return Response.json({ message: "Starting-place quota reached. Stop and review usage." }, { status: 422 }); };
  await assert.rejects(session.get("Synthetic Station", send), /quota reached/);
  await assert.rejects(session.get("Synthetic Station", send), /quota reached/);
  assert.equal(calls, 1);
});
test("starting-location stages are distinct from itinerary generation and preserve normal feedback", () => {
  for (const stage of ["Searching for starting place", "Choose your starting place", "Generating itinerary"]) {
    const html = renderToStaticMarkup(createElement(PlanningFeedback, { loading: true, stage, failed: false, needsClarification: false, message: "old error", onRetry() {}, onEdit() {} }));
    assert.match(html, new RegExp(stage === "Generating itinerary" ? "Planning your outing" : stage));
    assert.doesNotMatch(html, /old error|Retry|couldn’t complete/);
  }
  const html = renderToStaticMarkup(createElement(LocationControls, { lookupEnabled: false, onChange() {} }));
  assert.match(html, /Optional starting location/); assert.doesNotMatch(html, /latitude|longitude/);
});
test("summary distinguishes strict travel scopes without changing inclusive wording", () => {
  const value = { request: { activities: ["bowling", "food"], date: "2026-11-07", location: "Baltimore", people: 2, budget: null, travel: 20, maxLegTravel: 5, maxFirstLegTravel: 15, travelExclusive: true, maxLegTravelExclusive: true, transport: "driving", dinnerStops: [1] } } as ValidatedOuting;
  const details = Object.fromEntries(outingDetails(value, true));
  assert.equal(details["Each journey"], "Under 5 min between stops");
  assert.equal(details.Travel, "Under 20 min total between stops");
  assert.equal(details["First journey"], "15 min maximum from your shared start");
});

test("early discovery expansion preserves queued checked options instead of losing variety", async () => {
  const { expandedOptions, nextOptions } = await import("./option-batches");
  const base = { plans: [], message: "", location: "", activities: [], notes: [] } as import("./planner").PlannerResult;
  const plan = (id: string) => ({ id }) as import("./planner").Plan;
  const merged = expandedOptions({ ...base, alternativeBatches: [[plan("old-unviewed")]] }, { ...base, plans: [plan("new")], alternativeBatches: [[plan("new-unviewed")]] });
  assert.equal(nextOptions(merged).plans[0].id, "old-unviewed");
  assert.equal(nextOptions(nextOptions(merged)).plans[0].id, "new-unviewed");
});
