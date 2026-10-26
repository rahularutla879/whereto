import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { activityEditText, outingDetails, OutingSummary } from "../components/outing-summary";
import { generateOuting, type ValidatedOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";

const value: ValidatedOuting = {
  request: { location: "Baltimore", date: "2026-11-07", people: 4, activities: ["coffee", "museum", "coffee"],
    budget: null, travel: null, cost: "balanced", startTime: 600, endTime: 1440, groupBudget: 80, maxLegTravel: 20, transport: null, dinnerStops: [] },
  continuation: { pending: { text: "Coffee, museum, coffee tomorrow for four in Baltimore", interpretation: {}, answers: {}, referenceTime: "2026-11-06T12:00:00Z" }, questions: [] },
  explicitCost: false, explicitTime: false,
};
test("summary displays resolved effective values and repeats without inventing optional choices", () => {
  const fields = Object.fromEntries(outingDetails(value));
  assert.equal(fields.Date, "November 7, 2026");
  assert.equal(fields.Activities, "Coffee → Museum → Coffee");
  assert.equal(fields.Budget, undefined);
  assert.equal(fields.Experience, undefined);
  assert.equal(fields["Time window"], undefined);
  assert.equal(fields["Group budget"], "$80 maximum total");
  assert.equal(activityEditText(value.request), "coffee, museum, coffee");
  assert.equal(activityEditText({ ...value.request, activities: ["miniGolf", "escape", "sports"] }), "mini golf, escape room, sports event");
  const edited = { ...value, explicitCost: true, request: { ...value.request, budget: 0, travel: 0 } };
  assert.equal(Object.fromEntries(outingDetails(edited)).Budget, "$0 maximum / person");
  assert.equal(Object.fromEntries(outingDetails(edited)).Experience, "Balanced");
});
test("dirty summary clearly withholds previous constraints until revalidation", () => {
  const html = renderToStaticMarkup(createElement(OutingSummary, { value, dirty: true, onEdit() {} }));
  assert.match(html, /Previous recommendations are hidden/);
  assert.doesNotMatch(html, /November 7/);
  const loading = renderToStaticMarkup(createElement(OutingSummary, { value, dirty: true, loading: true, onEdit() {} }));
  assert.match(loading, /Checking your updated details/);
  assert.doesNotMatch(loading, /Regenerate|Previous recommendations/);
});
test("structured regeneration sends continuation and explicit edits to validation, then the exact validated request to planner", async () => {
  const corrected = { ...value.request, location: "Baltimore", date: "2026-11-14", people: 2, budget: 40, activities: ["museum", "coffee", "coffee"] };
  const calls: string[] = [];
  let seen: ValidatedOuting | undefined;
  await generateOuting(value.continuation.pending.text, { ...EMPTY_PREFERENCES, budget: "40", people: "2", date: "2026-11-14" }, {
    continuation: value.continuation, answers: { activities: "museum, coffee, coffee" }, onValidated: v => { seen = v; },
  }, async (url, init) => {
    calls.push(String(url));
    const body = JSON.parse(init!.body as string);
    if (calls.length === 1) {
      assert.deepEqual(body.pending, value.continuation.pending);
      assert.equal(body.answers.activities, "museum, coffee, coffee");
      return Response.json({ request: corrected, interpretation: {}, pending: value.continuation.pending, questions: [], notes: [], issues: [] });
    }
    assert.deepEqual(body, corrected);
    return Response.json({ message: "Planner unavailable" }, { status: 503 });
  });
  assert.deepEqual(seen?.request, corrected);
  assert.deepEqual(calls, ["/api/interpret", "/api/plans/generate"]);
});

test("rejected structured edits cannot publish a summary or invoke planning", async () => {
  let calls = 0;
  let published = false;
  const result = await generateOuting(value.continuation.pending.text, { ...EMPTY_PREFERENCES, budget: "-1" }, {
    continuation: value.continuation, onValidated: () => { published = true; },
  }, async () => {
    calls++;
    return Response.json({ interpretation: {}, request: null, issues: ["Enter a valid budget."], notes: [] });
  });
  assert.equal(calls, 1);
  assert.equal(published, false);
  assert.equal(result.plans.length, 0);
  assert.match(result.message, /valid budget/);
});

test("dinner occurrence and explicit time window survive summary and editable sequence", () => {
  const dinner = { ...value, explicitTime: true, request: { ...value.request, activities: ["coffee", "food", "coffee"] as ValidatedOuting["request"]["activities"], dinnerStops: [1], startTime: 1020, endTime: 1320 } };
  assert.equal(activityEditText(dinner.request), "coffee, dinner, coffee");
  assert.equal(Object.fromEntries(outingDetails(dinner)).Activities, "Coffee → Dinner → Coffee");
  assert.equal(Object.fromEntries(outingDetails(dinner))["Time window"], "5:00 PM–10:00 PM (Baltimore time)");
});


test("real outing summary labels provider routes and avoids a fictional timezone claim", () => {
  const real = { ...value, explicitTime: true, request: { ...value.request, location: "Washington, DC", transport: "driving" } };
  const details = Object.fromEntries(outingDetails(real, true));
  assert.equal(details.Transport, "driving (Google Maps estimates)");
  assert.doesNotMatch(details["Time window"], /Baltimore/);
  assert.match(Object.fromEntries(outingDetails(real)).Transport, /simulated/);
});
