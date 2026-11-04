import assert from "node:assert/strict";
import test from "node:test";
import { generateOuting } from "./planning-client";
import { EMPTY_PREFERENCES, formatDuration, formatTime, resolveOuting } from "./planner";

const context = { today: "2026-11-01" };

test("historical interpreter regression preserves manual precedence, inference, date resolution and zero limits", () => {
  const inferred = resolveOuting("Dinner and karaoke for 2 people $25 per person tomorrow", EMPTY_PREFERENCES, context);
  assert.deepEqual(inferred.payload, { activities: ["food", "karaoke"], location: "Baltimore", people: 2,
    budget: 25, travel: null, date: "2026-11-02", cost: "balanced", dinner: true });
  const manual = resolveOuting("Concert in Boston for 2 people $25 per person on 2026-11-08", {
    ...EMPTY_PREFERENCES, location: "Baltimore", people: "8", budget: "0", travel: "0", date: "2026-11-07", cost: "experience",
  }, context);
  assert.deepEqual(manual.payload, { activities: ["concert"], location: "Baltimore", people: 8,
    budget: 0, travel: 0, date: "2026-11-07", cost: "experience", dinner: false });
  assert.equal(formatTime(null), "Unknown");
  assert.equal(formatDuration(null), "Unknown");
});

test("AI issues stop planning and raw text/manual controls reach the interpretation endpoint", async () => {
  let calls = 0;
  const send: typeof fetch = async (url, init) => {
    calls++;
    assert.equal(url, "/api/interpret");
    const body = JSON.parse(init!.body as string);
    assert.equal(body.text, "Something competitive tomorrow");
    assert.equal(body.preferences.costExplicit, true);
    return Response.json({ interpretation: {}, request: null, notes: ["Suggestions only"], issues: ["Choose exact activities and date."] });
  };
  const r = await generateOuting("Something competitive tomorrow", { ...EMPTY_PREFERENCES, costExplicit: true }, context, send);
  assert.equal(calls, 1);
  assert.equal(r.plans.length, 0);
  assert.match(r.message, /exact activities/);
  assert.deepEqual(r.notes, ["Suggestions only"]);
});

test("AI failures and invalid output produce clear errors without planning fallback", async () => {
  for (const send of [
    async () => Response.json({ message: "Local model timed out" }, { status: 503 }),
    async () => Response.json({}),
    async () => { throw new TypeError("Network failed"); },
  ] as typeof fetch[]) {
    const r = await generateOuting("Coffee", EMPTY_PREFERENCES, context, send);
    assert.equal(r.plans.length, 0);
    assert.match(r.message, /trouble planning.*try again/i);
  }
});

test("clock labels distinguish noon, midnight and the allowed end-of-day boundary", () => {
  assert.equal(formatTime(0), "12:00 AM");
  assert.equal(formatTime(720), "12:00 PM");
  assert.equal(formatTime(1380), "11:00 PM");
  assert.equal(formatTime(1439), "11:59 PM");
  assert.equal(formatTime(1440), "12:00 AM");
});

test("advanced requirements stop before origin lookup/planning and preserve request/preferences for revision", async () => {
  for (const text of ["Go to SUNY College of Optometry.", "Go to the pharmacy first, then the supermarket.", "Get groceries and return home within 45 minutes."]) {
    const limitation = "This outing includes specific stops or timing requirements that we can't plan together yet. You can simplify the request for now.";
    let calls = 0;
    const send: typeof fetch = async (url, init) => {
      calls++;
      assert.equal(url, "/api/interpret");
      const payload = JSON.parse(init!.body as string);
      assert.equal(payload.text, text);
      assert.equal(payload.preferences.transport, "walking");
      return Response.json({ interpretation: { journey: { stops: [] } }, request: null, issues: [limitation], unsupported: [limitation], notes: [] });
    };
    const r = await generateOuting(text, {...EMPTY_PREFERENCES, transport: "walking"}, {prepareOrigin:async()=>{throw new Error("Must not prepare a route");}},send);
    assert.equal(calls,1);assert.equal(r.plans.length,0);assert.equal(r.message,limitation);assert.equal(r.requestFailed,false);
  }
});

test("unsupported response cannot be bypassed by a stale resolved request", async () => {
  let calls = 0;
  const send: typeof fetch = async () => {
    calls++;
    return Response.json({ request: {activities:["coffee"]}, issues: [], unsupported:["Please simplify this outing."], notes:[] });
  };
  const r = await generateOuting("Coffee then return to the origin",EMPTY_PREFERENCES,undefined,send);
  assert.equal(calls,1);assert.equal(r.plans.length,0);assert.equal(r.message,"Please simplify this outing.");
});
