import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import Home from "../app/page";
import { OutingDateField } from "../components/outing-date-field";
import { OutingSummary } from "../components/outing-summary";
import { generateOuting, type ValidatedOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";

const value: ValidatedOuting = {
  request: { location: "Baltimore", date: "2026-11-07", people: 4, activities: ["coffee", "museum", "coffee"],
    budget: null, travel: null, cost: "balanced", startTime: 600, endTime: 1440, groupBudget: null, maxLegTravel: null, transport: null, dinnerStops: [] },
  continuation: { pending: { text: "Coffee, museum, coffee in Baltimore for four on November 7, 2026", interpretation: {}, answers: {}, referenceTime: "2026-10-22T12:00:00Z" }, questions: [] },
  explicitCost: false, explicitTime: false,
};

test("homepage starts with preferences collapsed and an accessible toggle", () => {
  const html = renderToStaticMarkup(createElement(Home));
  assert.match(html, /aria-expanded="false" aria-controls="preferences"/);
  assert.match(html, /id="preferences" hidden=""/);
  assert.doesNotMatch(html, /id="outing-summary-title"/);
});

test("compact summary has effective core details and edit action without unspecified optional rows", () => {
  const html = renderToStaticMarkup(createElement(OutingSummary, { value, dirty: false, onEdit() {} }));
  for (const text of ["Baltimore", "November 7, 2026", "4 people", "Coffee → Museum → Coffee", "Edit details", 'aria-controls="preferences"']) assert.ok(html.includes(text));
  for (const text of ["Not specified", "Balanced", "<dt>Budget</dt>", "<dt>Travel</dt>", "<dt>Experience</dt>"]) assert.ok(!html.includes(text));
});

test("native date input preserves ISO value and explains the same selected calendar date", () => {
  const html = renderToStaticMarkup(createElement(OutingDateField, { value: value.request.date, onChange() {} }));
  assert.match(html, /type="date"[^>]*value="2026-11-07"/);
  assert.match(html, /aria-describedby="outing-date-help"/);
  assert.match(html, /id="outing-date-help">Selected: November 7, 2026/);
  const empty = renderToStaticMarkup(createElement(OutingDateField, { value: "", onChange() {} }));
  assert.match(empty, /Date format follows your browser/);
});

test("completion hook used to collapse preferences runs only after a validated planning response", async () => {
  for (const outcome of ["success", "invalid", "clarification", "plannerFailure"] as const) {
    let completed = 0;
    let calls = 0;
    await generateOuting(value.continuation.pending.text, EMPTY_PREFERENCES, {
      continuation: value.continuation, onComplete: () => { completed++; },
    }, async (url, init) => {
      calls++;
      if (url === "/api/interpret") {
        if (outcome === "invalid") return Response.json({ interpretation: {}, request: null, issues: ["Invalid budget"], notes: [] });
        if (outcome === "clarification") return Response.json({ interpretation: {}, request: null, issues: ["Which date?"], notes: [], pending: value.continuation.pending, questions: [{ field: "date", question: "Which date?", kind: "essential" }] });
        return Response.json({ interpretation: {}, request: value.request, issues: [], notes: [], pending: value.continuation.pending, questions: [] });
      }
      assert.equal(JSON.parse(init!.body as string).date, "2026-11-07");
      if (outcome === "plannerFailure") return Response.json({ message: "Unavailable" }, { status: 503 });
      return Response.json({ request: value.request, plans: [], provisionalPlans: [], message: "No options fit", notes: [], errors: [] });
    });
    assert.equal(completed, outcome === "success" ? 1 : 0, outcome);
    assert.equal(calls, outcome === "invalid" || outcome === "clarification" ? 1 : 2);
  }
});
