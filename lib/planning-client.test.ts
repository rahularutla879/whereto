import assert from "node:assert/strict";
import test from "node:test";
import { generateOuting } from "./planning-client";
import { EMPTY_PREFERENCES, formatDuration, formatTime, resolveOuting } from "./planner";

const context = { today: "2026-11-01" };

test("active interpreter preserves manual precedence, inference, date resolution and zero limits", () => {
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

test("invalid and unsupported text or preferences never send a partial request", async () => {
  const unexpected: typeof fetch = async () => { throw new Error("Unexpected network request"); };
  for (const [text, prefs] of [
    ["Dinner and skydiving", {}], ["Concert", {}], ["Coffee", { people: "0" }],
    ["Coffee", { budget: "-1" }], ["Coffee", { travel: "1.5" }], ["Coffee in Boston", {}],
    ["Concert on 2026-02-30", {}], ["Concert or theater on 2026-11-07", {}],
  ] as const) {
    const result = await generateOuting(text, { ...EMPTY_PREFERENCES, ...prefs }, context, unexpected);
    assert.equal(result.plans.length, 0);
    assert.doesNotMatch(result.message, /unavailable/);
  }
});

test("client reports invalid API input and network errors clearly", async () => {
  const invalid: typeof fetch = async () => Response.json({ message: "Invalid request: correct the date." }, { status: 422 });
  assert.match((await generateOuting("Coffee", EMPTY_PREFERENCES, context, invalid)).message, /correct the date/);
  const offline: typeof fetch = async () => { throw new TypeError("Network failed"); };
  const result = await generateOuting("Coffee", EMPTY_PREFERENCES, context, offline);
  assert.equal(result.plans.length, 0);
  assert.match(result.message, /Python planner unavailable/);
});
