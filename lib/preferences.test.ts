import assert from "node:assert/strict";
import test from "node:test";
import { EMPTY_PREFERENCES } from "./planner";
import { displayInterpretedPreferences, editPreference, emptyPreferenceState, interpretedPreferences, manualPreferences } from "./preferences";
import { generateOuting } from "./planning-client";

const request = { activities: ["coffee"], location: "Baltimore", people: 6, date: "2026-10-22",
  budget: 100, travel: 30, cost: "experience" };

test("untouched controls submit no overrides; structured interpretation fills every existing control", () => {
  const initial = emptyPreferenceState();
  assert.deepEqual(manualPreferences(initial), EMPTY_PREFERENCES);
  const shown = displayInterpretedPreferences(initial, interpretedPreferences(request));
  assert.deepEqual(shown.values, { location: "Baltimore", date: "2026-10-22", people: "", budget: "100", travel: "30", cost: "experience", costExplicit: false });
  assert.deepEqual(manualPreferences(shown), EMPTY_PREFERENCES);
});

test("subsequent text replaces auto-populated values, clears unspecified caps/date, and leaves no override", () => {
  const first = displayInterpretedPreferences(emptyPreferenceState(), interpretedPreferences(request));
  const next = displayInterpretedPreferences(first, interpretedPreferences({ ...request, people: 2, date: null, budget: null, travel: null, cost: "balanced" }));
  assert.deepEqual(next.values, { ...EMPTY_PREFERENCES, location: "Baltimore", people: "", costExplicit: false });
  assert.deepEqual(manualPreferences(next), EMPTY_PREFERENCES);
});

test("manual edits win independently, including zero caps and deliberately selected Balanced", () => {
  let state = displayInterpretedPreferences(emptyPreferenceState(), interpretedPreferences(request));
  for (const [field, value] of [["people", "3"], ["date", "2026-11-07"], ["budget", "0"], ["travel", "0"], ["cost", "balanced"]] as const) {
    state = editPreference(state, field, value);
  }
  assert.deepEqual(manualPreferences(state), { ...EMPTY_PREFERENCES, people: "3", date: "2026-11-07", budget: "0", travel: "0", costExplicit: true });
  const next = displayInterpretedPreferences(state, interpretedPreferences({ ...request, people: 8, budget: 50 }));
  assert.equal(next.values.people, "3"); assert.equal(next.values.budget, "0");
  assert.equal(next.values.cost, "balanced"); assert.equal(next.values.costExplicit, true);
  state = editPreference(next, "people", "");
  assert.equal(state.values.people, ""); assert.equal(manualPreferences(state).people, "");
  assert.equal(displayInterpretedPreferences(state, interpretedPreferences(request)).values.people, "");
  assert.deepEqual(manualPreferences(emptyPreferenceState()), EMPTY_PREFERENCES);
});

test("an edit made while interpretation is pending survives the automatic display update", () => {
  const pending = editPreference(emptyPreferenceState(), "budget", "0");
  assert.equal(displayInterpretedPreferences(pending, interpretedPreferences(request)).values.budget, "0");
});

test("invalid structured preference fields cannot become displayed facts", () => {
  for (const changed of [{ date: "tomorrow" }, { budget: undefined }, { travel: -1 }, { cost: "luxury" }, { location: null }]) {
    assert.throws(() => interpretedPreferences({ ...request, ...changed }));
  }
});

test("one interpretation call displays values before planning; later text submits only deliberate overrides", async () => {
  let state = emptyPreferenceState();
  let current = request;
  const paths: string[] = [];
  const send: typeof fetch = async (url, init) => {
    paths.push(String(url));
    const body = JSON.parse(String(init?.body));
    if (url === "/api/interpret") {
      assert.deepEqual(body.preferences, EMPTY_PREFERENCES);
      return Response.json({ interpretation: {}, request: current, issues: [], notes: [] });
    }
    assert.deepEqual(body, current);
    assert.equal(state.values.people, "");
    // Planning failure must stay an error, while successful interpretation can
    // still be inspected; it must never call the model or legacy engine again.
    return Response.json({ message: "Unavailable" }, { status: 503 });
  };
  const run = () => generateOuting("Coffee for 6 people in Baltimore tomorrow", manualPreferences(state), {
    onInterpreted: values => { state = displayInterpretedPreferences(state, values); },
  }, send);
  assert.equal((await run()).plans.length, 0);
  assert.equal(state.values.date, "2026-10-22");
  current = { ...request, people: 2, budget: 20, cost: "budget" };
  await run();
  assert.equal(state.values.people, ""); assert.equal(state.values.budget, "20");
  assert.deepEqual(paths, ["/api/interpret", "/api/plans/generate", "/api/interpret", "/api/plans/generate"]);
});

test("missing essential information and AI failures never populate guessed controls or call planning", async () => {
  for (const response of [
    { interpretation: {}, request: null, issues: ["Group size is unknown. How many people are going?"], notes: [] },
    { message: "AI unavailable" },
  ]) {
    let calls = 0; let displayed = false;
    const send: typeof fetch = async () => { calls++; return Response.json(response, { status: "message" in response ? 503 : 200 }); };
    const result = await generateOuting("Coffee", EMPTY_PREFERENCES, { onInterpreted: () => { displayed = true; } }, send);
    assert.equal(displayed, false); assert.equal(calls, 1); assert.equal(result.plans.length, 0);
    assert.match(result.message, /Group size|AI unavailable/);
  }
});

test("validation failure during a pending answer preserves manual, automatic and follow-up state", async () => {
  const state = editPreference(displayInterpretedPreferences(emptyPreferenceState(), interpretedPreferences(request)), "budget", "50");
  const before = structuredClone(state);
  const pending = { pending: { text: "coffee", interpretation: { activities: ["coffee"] },
    answers: {}, referenceTime: "2026-10-21T12:00:00Z" },
    questions: [{ field: "date" as const, question: "What day?", kind: "essential" as const }] };
  let changes = 0;
  const paths: string[] = [];
  const failed = await generateOuting("coffee", manualPreferences(state), {
    continuation: pending, answers: { date: "tomorrow" },
    onInterpreted: () => { changes++; }, onClarification: () => { changes++; }, onComplete: () => { changes++; },
  }, async (url, init) => {
    paths.push(String(url));
    const sent = JSON.parse(String(init?.body));
    assert.deepEqual(sent.pending, pending.pending);
    assert.equal(sent.preferences.budget, "50");
    return Response.json({ message: "Please check your request and try again." }, { status: 422 });
  });
  assert.equal(failed.plans.length, 0);
  assert.deepEqual(paths, ["/api/interpret"]);
  assert.equal(changes, 0);
  assert.deepEqual(state, before);
  assert.equal(pending.questions[0].field, "date");
});
