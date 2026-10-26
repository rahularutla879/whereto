import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PlanningFeedback } from "../components/planning-feedback";
import { generateOuting, type ValidatedOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";

const text = "Coffee in Baltimore on 2026-11-07 for 2 people";
const request = { activities: ["coffee"], location: "Baltimore", people: 2, date: "2026-11-07", budget: null, travel: null, cost: "balanced", startTime: 600, endTime: 1440, groupBudget: null, maxLegTravel: null, transport: null, dinnerStops: [] };
const pending = { text, interpretation: { activities: ["coffee"] }, answers: {}, referenceTime: "2026-10-25T12:00:00Z" };
const extraction = () => Response.json({ pending, questions: [], request, interpretation: {}, issues: [], notes: [] });
const success = () => Response.json({ request, plans: [], provisionalPlans: [], errors: [], notes: [], message: "No matching sample venues" });
function feedback(loading: boolean, failed = false, needsClarification = false, message = "") {
  return renderToStaticMarkup(createElement(PlanningFeedback, { loading, failed, needsClarification, message, onRetry() {}, onEdit() {} }));
}

test("normal submission never publishes an empty retry panel while planning is pending", async () => {
  let release!: (value: Response) => void;
  const held = new Promise<Response>(resolve => { release = resolve; });
  let validated!: () => void;
  const ready = new Promise<void>(resolve => { validated = resolve; });
  let questions = 0, completed = 0;
  const work = generateOuting(text, EMPTY_PREFERENCES, { onClarification: () => { questions++; }, onValidated: () => validated(), onComplete: () => { completed++; } }, async path => path === "/api/interpret" ? extraction() : held);
  await ready;
  assert.equal(questions, 0);
  assert.equal(completed, 0);
  const html = feedback(true);
  assert.match(html, /Planning your outing/);
  assert.doesNotMatch(html, /retry|failure|tweak|Edit your request|little more detail/i);
  release(success());
  const result = await work;
  assert.equal(completed, 1);
  assert.notEqual(result.requestFailed, true);
});

test("actual failed planning retains validated constraints and retry recovers without showing questions", async () => {
  let saved: ValidatedOuting | undefined;
  let questionUpdates = 0;
  const failed = await generateOuting(text, EMPTY_PREFERENCES, { onValidated: value => { saved = value; }, onClarification: () => { questionUpdates++; } }, async path => path === "/api/interpret" ? extraction() : Response.json({ message: "Synthetic failure" }, { status: 503 }));
  assert.equal(failed.requestFailed, true);
  assert.ok(saved);
  assert.equal(questionUpdates, 0);
  assert.match(feedback(false, true, false, failed.message), /Retry/);
  let release!: (value: Response) => void;
  const held = new Promise<Response>(resolve => { release = resolve; });
  let validated!: () => void;
  const ready = new Promise<void>(resolve => { validated = resolve; });
  const recovery = generateOuting(text, EMPTY_PREFERENCES, { continuation: saved.continuation, onValidated: () => validated(), onClarification: () => { questionUpdates++; } }, async (path, init) => {
    if (path === "/api/interpret") {
      assert.deepEqual(JSON.parse(init!.body as string).pending, pending);
      return extraction();
    }
    return held;
  });
  await ready;
  assert.doesNotMatch(feedback(true, true, true, failed.message), /Retry|Synthetic failure|could not|little more detail/i);
  release(success());
  const recovered = await recovery;
  assert.notEqual(recovered.requestFailed, true);
  assert.equal(questionUpdates, 0);
  assert.doesNotMatch(feedback(false, false, false, recovered.message), /Retry/);
});

test("old clarification and failure copy is suppressed in loading and actual questions still work", async () => {
  const question = { field: "date", question: "Which date?", kind: "essential" };
  let received: unknown;
  let calls = 0;
  const result = await generateOuting(text, EMPTY_PREFERENCES, { onClarification: value => { received = value; } }, async () => {
    calls++;
    return Response.json({ pending, questions: [question], request: null, issues: [question.question], notes: [] });
  });
  assert.deepEqual(received, { pending, questions: [question] });
  assert.equal(calls, 1);
  assert.equal(result.requestFailed, false);
  assert.match(feedback(false, false, true), /Just a little more detail/);
  assert.doesNotMatch(feedback(true, true, true, "Which date? Please retry."), /Which date|retry|Just a little/i);
});

test("interpretation failure offers useful retry but a new successful attempt has no stale failure", async () => {
  const failure = await generateOuting(text, EMPTY_PREFERENCES, {}, async () => Response.json({ message: "Local interpretation service temporarily unavailable" }, { status: 503 }));
  assert.equal(failure.requestFailed, true);
  assert.match(feedback(false, true, false, failure.message), /Local interpretation service temporarily unavailable/);
  assert.match(feedback(false, true, false, failure.message), /Retry/);
  assert.doesNotMatch(feedback(true, true, false, failure.message), /temporarily unavailable|Retry/);
  const recovered = await generateOuting(text, EMPTY_PREFERENCES, {}, async path => path === "/api/interpret" ? extraction() : success());
  assert.notEqual(recovered.requestFailed, true);
  assert.doesNotMatch(feedback(false, false, false, recovered.message), /Retry|temporarily unavailable/);
});
