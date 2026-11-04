import assert from "node:assert/strict";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { FirstLegTravel } from "../components/first-leg-travel";
import { OutingSummary } from "../components/outing-summary";
import { realHeadlines } from "./real-headlines";
import { consumerMessage } from "./results-presentation";
import { AlternativeActions } from "../components/alternative-actions";
import { interpretedPreferences } from "./preferences";
import type { Plan } from "./planner";
import type { ValidatedOuting } from "./planning-client";

test("current first-leg copy uses actual evidence, mode and no private origin label", () => {
  const plan = { dataMode: "real", firstLeg: { source: "device", mode: "walk", originLabel: "PRIVATE_INTERNAL_LABEL", minutes: 8, miles: 1.11 } } as Plan;
  const html = renderToStaticMarkup(React.createElement(FirstLegTravel, { plan }));
  assert.match(html, /Travel from your current location/);
  assert.match(html, /About 8 min walking \(1.11 miles\) to the first stop/);
  assert.match(html, /Walking route estimate/);
  assert.doesNotMatch(html, /PRIVATE|permission-authorized|latitude|longitude/);
  for (const source of ["manual", "suggested"] as const) {
    const text = renderToStaticMarkup(React.createElement(FirstLegTravel, { plan: { ...plan, firstLeg: { ...plan.firstLeg!, source, minutes: null } } }));
    assert.match(text, /not verified/);
    assert.doesNotMatch(text, /About null|current location/);
  }
});

test("legacy group counts never become controls or visible outing metadata", () => {
  for (const people of [undefined, null, 2, 3, 6]) {
    const request = { activities: ["custom:pottery class", "food"], location: "Manhattan", date: "2026-11-14", people, budget: null, travel: null, cost: "balanced" };
    assert.equal(interpretedPreferences(request).people, "");
    const html = renderToStaticMarkup(React.createElement(OutingSummary, { value: { request } as ValidatedOuting, dirty: false, onEdit() {} }));
    assert.match(html, /Pottery class/);
    assert.doesNotMatch(html, /<dt>Group|people|persons|custom:/);
  }
});

test("new activity labels and provider failures remain understandable", () => {
  assert.match(realHeadlines([[{ name: "Synthetic pottery studio", activity: "custom:pottery class" }, { name: "Synthetic cafe", activity: "coffee" }]])[0].label, /POTTERY CLASS \+ COFFEE/);
  for (const text of ["Local route matrix minute quota reached.", "The local rolling-minute routing allowance is temporarily full."]) {
    assert.match(consumerMessage(text), /temporary routing limit/);
    assert.doesNotMatch(consumerMessage(text), /adjust|scarcity|no venues/i);
  }
  assert.match(consumerMessage("Routes per-minute element limit was reached."), /Google's current search or routing limit/);
  const limited = renderToStaticMarkup(React.createElement(AlternativeActions, { real: true, canCombine: true, canExplore: true, busy: false, disabled: false, notice: consumerMessage("Local route matrix minute quota reached."), onAction() {}, onAdjust() {} }));
  assert.doesNotMatch(limited, /Adjust travel preference/);
});
