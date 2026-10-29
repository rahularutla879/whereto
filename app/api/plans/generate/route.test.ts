import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { POST } from "./route";
import { adaptRanking } from "../../../../lib/planning-client";
import { EMPTY_PREFERENCES, formatTime, resolveOuting } from "../../../../lib/planner";

const MOCK_START={point:{id:"Mock_origin_0",coordinates:{latitude:0,longitude:0}},source:"mock",explicitly_authorized:true};
const context = { today: "2026-11-01" };
// Preserve Task 28 contract regression independently of the new AI boundary.
const generateOuting = async (text: string, prefs: Parameters<typeof resolveOuting>[1], ctx: { today: string }, send: typeof fetch) => {
  const resolved = resolveOuting(text, prefs, ctx);
  if (resolved.error) return resolved.error;
  const response = await send("/api/plans/generate", { method: "POST", body: JSON.stringify({...resolved.payload,startingLocation:MOCK_START}) });
  if (!response.ok) return { plans: [], message: (await response.json()).message, location: "", activities: [], notes: [] };
  return adaptRanking(await response.json());
};
const send: typeof fetch = async (_url, init) => POST(new Request("http://localhost/api/plans/generate", init));

test("historical resolved request → Next.js proxy → real Python planner → display cards", async () => {
  // Keep the test alive while Node fetch retries a closed pooled connection.
  const keepAlive = setInterval(() => {}, 1000);
  const reservation = createServer();
  reservation.listen(0, "127.0.0.1");
  await once(reservation, "listening");
  const address = reservation.address();
  assert.ok(address && typeof address === "object");
  await new Promise<void>(resolve => reservation.close(() => resolve()));
  const previous = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${address.port}`;
  const backend = spawn("backend/.venv/bin/python", ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", String(address.port), "--log-level", "warning"]);
  try {
    let ready = false;
    for (let i = 0; i < 100; i++) {
      try { ready = (await fetch(`${process.env.BACKEND_URL}/health`)).ok; } catch { /* starting */ }
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    assert.ok(ready, "Python server became ready");
    const run = (text: string, prefs = {}) => generateOuting(text, { ...EMPTY_PREFERENCES, ...prefs }, context, send);
    // normal request preserves returned Python IDs, order, totals, times and quality
    {
      const r = await run("Bowling, drinks and a movie in Baltimore on 2026-11-07");
      assert.equal(r.plans.length, 3);
      const p = r.plans[0];
      assert.match(p.id, /^candidate-/);
      assert.deepEqual(p.venues.map(v => v.activity), ["bowling", "drinks", "movie"]);
      assert.equal(p.price, p.prices.reduce((n, q) => n + q.amount!, 0));
      assert.equal(p.groupCost, null);
      assert.equal(p.travel, p.legs.reduce((n, q) => n + q.minutes!, 0));
      assert.equal(p.stops[0].start, 600);
      assert.equal(p.feasibility, "provisional");
      assert.match(p.issues.join(" "), /Opening hours/);
      assert.equal(p.venues[0].dataQuality?.price, "fictional");
      const raw = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: JSON.stringify({...resolveOuting("Bowling, drinks and a movie in Baltimore on 2026-11-07", EMPTY_PREFERENCES, context).payload,startingLocation:MOCK_START}) }));
      assert.equal(raw.headers.get("cache-control"), "no-store");
      assert.deepEqual(adaptRanking(await raw.json()).plans, r.plans);
    }
    // different activities and all three preferences affect Python results
    {
      const ids = [];
      for (const cost of ["budget", "balanced", "experience"]) ids.push((await run("Coffee on 2026-11-07", { cost })).plans[0].venues[0].id);
      assert.deepEqual(ids, ["coffee-0", "coffee-1", "coffee-2"]);
      assert.equal((await run("Museum on 2026-11-07")).plans[0].venues[0].activity, "museum");
    }
    // manual overrides, hard budget, travel, capacity and infeasible messages
    {
      const r = await run("Dinner and karaoke for 2 people on 2026-11-07", { budget: "25", travel: "5", people: "4" });
      assert.ok(r.plans.length);
      assert.ok(r.plans.every(p => p.price! <= 25 && p.travel! <= 5 && p.stops[0].start! >= 1020));
      for (const prefs of [{ budget: "0" }, { travel: "0" }]) {
        const empty = await run("Dinner and karaoke on 2026-11-07", prefs);
        assert.equal(empty.plans.length, 0);
        assert.match(empty.message, /No candidate|cannot|exceed/);
      }
    }
    // matching events confirmed only against fiction; missing dates never substituted
    {
      const r = await run("Baseball and concert on 2026-11-07");
      assert.ok(r.plans.length);
      assert.ok(r.plans.every(p => p.feasibility === "confirmed" && p.date === "2026-11-07"));
      assert.match(r.plans[0].description, /Best fit for Balanced/);
      const missing = await run("Concert on 2026-11-08");
      assert.equal(missing.plans.length, 0);
      assert.match(missing.message, /No mock records/);
      assert.ok((await run("Concert on 2026-11-08", { date: "2026-11-07" })).plans.length);
    }
    // Descriptions reuse real Python scores and distinguish tied café orders.
    {
      const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: JSON.stringify({
        activities: ["coffee", "museum", "coffee"], location: "Baltimore", people: 6,
        budget: 100, travel: 30, cost: "experience", date: "2026-11-07", startingLocation: MOCK_START,
      }) }));
      const raw = await response.json();
      const before = structuredClone(raw);
      const plans = adaptRanking(raw).plans;
      assert.deepEqual(raw, before, "describing options must not mutate Python results");
      assert.deepEqual(plans.map(p => p.price).sort(), [31, 41, 41]);
      assert.match(plans[0].label, /JOINT TOP MATCH/);
      assert.match(plans[0].description, /Best Experience.*highest sample venue quality/);
      const reordered=plans.find(p=>p.label.includes("DIFFERENT STOP ORDER"))!;
      const cheaper=plans.find(p=>p.label.includes("LOWEST COST"))!;
      assert.ok(reordered);assert.ok(cheaper);
      assert.match(reordered.description, /Same cost, travel and sample quality.*Paper Cup Studio/);
      assert.match(cheaper.label, /LOWEST COST/);
      assert.match(cheaper.description, /\$31\.00.*Harbor Discovery Hall/);
      assert.equal(new Set(plans.map(p => p.description)).size, 3);
      assert.deepEqual(plans.map(p => p.title).sort(), ["Joint Best Match", "Same Places, New Order", "Lowest Cost per Person"].sort());
    }
    // Real fixture route finishes exactly at midnight; display must not say noon.
    {
      const r = await run("Comedy, drinks, coffee and art on 2026-11-07");
      assert.equal(r.plans.length, 3);
      assert.equal(new Set(r.plans.map(p => p.id)).size, r.plans.length);
      for (const p of r.plans) {
        assert.deepEqual(p.venues.map(v => v.activity), ["comedy", "drinks", "coffee", "art"]);
        assert.equal(p.stops.at(-1)!.end, 1440);
        assert.equal(formatTime(p.stops.at(-1)!.end), "12:00 AM");
        assert.equal(p.duration, 240);
        assert.equal(p.travel, 15);
      }
    }
    // invalid and unsupported requests have clear messages
    {
      for (const text of ["Dinner and skydiving", "Concert", "Coffee on 2026-02-30"]) {
        const r = await run(text);
        assert.equal(r.plans.length, 0);
        assert.ok(r.message.length > 20);
      }
      const invalid = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: '{"activities":["skydiving"]}' }));
      assert.equal(invalid.status, 422);
      assert.equal((await invalid.json()).code, "unsupported_request");
      assert.equal((await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: "bad" }))).status, 400);
    }
    // unknown price, times and travel remain unknown in the card adapter
    {
      const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: JSON.stringify({activities:["coffee"],date:"2026-11-07",startingLocation:MOCK_START}) }));
      const raw = await response.json();
      const p = raw.provisionalPlans[0];
      p.costPerPerson = p.groupCost = p.elapsedDuration = null;
      p.prices[0].amount = null;
      p.stops[0].end = p.stops[0].venue.price = null;
      p.issues.push({ message: "Price is unknown; confirm costs before planning." });
      const display = adaptRanking(raw).plans[0];
      assert.equal(display.price, null);
      assert.equal(display.groupCost, null);
      assert.equal(display.stops[0].end, null);
      assert.match(display.issues.join(" "), /Price is unknown/);
      for (const undated of [null, "Any day", ""]) {
        raw.provisionalPlans[0].candidate.date = undated;
        assert.throws(() => adaptRanking(raw), /Invalid itinerary response/);
      }
    }
    backend.kill();
    await once(backend, "exit");
    // stopped Python produces an explicit error and no legacy fallback
    {
      const r = await run("Coffee on 2026-11-07");
      assert.equal(r.plans.length, 0);
      assert.match(r.message, /Python planner unavailable/);
    }
  } finally {
    clearInterval(keepAlive);
    if (backend.exitCode === null && backend.signalCode === null) { backend.kill(); await once(backend, "exit"); }
    if (previous === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = previous;
  }
});

test("proxy rejects failed, malformed and stalled upstream responses", async () => {
  let status = 500;
  let body = '{}';
  let stall = false;
  const server = createServer((_req, res) => {
    if (stall) return;
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(body);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.ok(address && typeof address === "object");
  const previous = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${address.port}`;
  try {
    for (const [nextStatus, nextBody] of [[500, '{}'], [200, 'not json'], [200, '{}'], [422, '{}']] as const) {
      status = nextStatus; body = nextBody;
      const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: '{"activities":["coffee"],"date":"2026-11-07"}' }));
      assert.equal(response.status, 503);
      assert.equal((await response.json()).code, "backend_unavailable");
    }
    stall = true;
    const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: '{}' }));
    assert.equal(response.status, 503);
  } finally {
    server.close(); server.closeAllConnections();
    if (previous === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = previous;
  }
});
