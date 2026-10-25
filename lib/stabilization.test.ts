import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PlanCost } from "../components/plan-cost";
import { nextOptions } from "./option-batches";
import type { PlannerResult } from "./planner";

test("unknown cost headings are plain language without numeric estimates or per-person suffix", () => {
  const price = renderToStaticMarkup(createElement(PlanCost, { amount: null }));
  assert.equal(price, "<strong>Price not available</strong>");
  assert.equal(renderToStaticMarkup(createElement(PlanCost, { amount: null, group: true })), "<strong>Cost not verified</strong>");
  assert.match(renderToStaticMarkup(createElement(PlanCost, { amount: 0 })), /~\$0/);
});

test("different options does nothing on exhausted or mock results", () => {
  const result: PlannerResult = { plans: [], message: "", notes: [], activities: [], location: "Baltimore", dataMode: "mock" };
  assert.equal(nextOptions(result), result);
});
