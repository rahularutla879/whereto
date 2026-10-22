import assert from "node:assert/strict";
import test from "node:test";
import { PlanningSession } from "./planning-session";
import { generateOuting, type PendingOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";

const saved: PendingOuting = { pending: { text: "coffee", interpretation: { activities: ["coffee"] },
  answers: {}, referenceTime: "2026-10-21T15:00:00Z" }, questions: [
    { field: "location", question: "Which city?", kind: "essential" },
    { field: "people", question: "How many people?", kind: "essential" },
  ] };

test("incomplete requests return retained state without a planning call", async () => {
  let state: PendingOuting | null = null;
  let calls = 0;
  const result = await generateOuting("coffee", EMPTY_PREFERENCES, { onClarification: value => { state = value; } }, async () => {
    calls++;
    return Response.json({ ...saved, request: null, issues: ["Location and group unknown"], notes: [] });
  });
  assert.equal(calls, 1);
  assert.deepEqual(state, saved);
  assert.equal(result.plans.length, 0);
});

test("follow-up sends the unchanged original and interpretation separately from answers and manual preferences", async () => {
  const manual = { ...EMPTY_PREFERENCES, people: "3", budget: "0", costExplicit: true };
  let next: PendingOuting | null = null;
  await generateOuting("coffee", manual, { continuation: saved, answers: { location: "Baltimore", people: "many" },
    onClarification: value => { next = value; } }, async (url, init) => {
    assert.equal(url, "/api/interpret");
    assert.deepEqual(JSON.parse(init!.body as string), { text: "coffee", preferences: manual,
      pending: saved.pending, answers: { location: "Baltimore", people: "many" } });
    return Response.json({ ...saved, issues: ["Enter a whole number"], notes: [], request: null });
  });
  assert.deepEqual(next, saved);
});

test("backend or model failure leaves retained state and answers available for retry", async () => {
  for (const status of [422, 503]) {
    let updates = 0;
    const result = await generateOuting("coffee", EMPTY_PREFERENCES, { continuation: saved, answers: { people: "2" },
      onClarification: () => { updates++; }, onComplete: () => { updates++; } },
    async () => Response.json({ message: "Service unavailable" }, { status }));
    assert.equal(updates, 0);
    assert.match(result.message, /unavailable/);
    assert.equal(saved.pending.text, "coffee");
  }
});

test("duplicate submissions are blocked; cancellation and replacement discard late results", () => {
  const session = new PlanningSession();
  const first = session.begin()!;
  assert.equal(session.begin(), null);
  session.cancel();
  assert.equal(first.signal.aborted, true);
  assert.equal(session.current(first), false);
  const replacement = session.begin()!;
  assert.equal(session.finish(first), false);
  assert.equal(session.current(replacement), true);
  assert.equal(session.finish(replacement), true);
  assert.ok(session.begin());
});

test("cancel during interpretation prevents any subsequent planning request", async () => {
  const controller = new AbortController();
  let calls = 0;
  const result = await generateOuting("coffee", EMPTY_PREFERENCES, { signal: controller.signal }, async () => {
    calls++;
    controller.abort();
    return Response.json({ issues: [], notes: [], request: { location: "Baltimore", people: 2, date: null,
      budget: null, travel: null, cost: "balanced" } });
  });
  assert.equal(calls, 1);
  assert.equal(result.plans.length, 0);
});

test("malformed backend output does not discard an existing clarification", async () => {
  let updates = 0;
  await generateOuting("coffee", EMPTY_PREFERENCES, { continuation: saved,
    onClarification: () => { updates++; } }, async () => Response.json({ issues: [], notes: [], request: {} }));
  assert.equal(updates, 0);
});

test("contextual date reasons and year-only answers pass through the existing continuation", async () => {
  const question = { field: "date" as const, kind: "ambiguous" as const, reason: "missing_year",
    question: "March 11 has already passed this year. Which year would you like to plan for?",
    helpText: "Enter a four-digit year, for example 2027." };
  let current: PendingOuting | null = null;
  let calls = 0;
  await generateOuting(saved.pending.text, EMPTY_PREFERENCES, { continuation: saved,
    answers: { date: "2027" }, onClarification: value => { current = value; } }, async (url, init) => {
    calls++;
    assert.equal(url, "/api/interpret");
    assert.equal(JSON.parse(init!.body as string).answers.date, "2027");
    return Response.json({ interpretation: {}, ...saved, questions: [question], request: null,
      issues: [question.question], notes: [] });
  });
  assert.equal(calls, 1); // An unresolved answer must never reach planning.
  assert.deepEqual((current as PendingOuting | null)?.questions, [question]);
});
