import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { POST } from "./route";
import { generateOuting, adaptRanking } from "../../../../lib/planning-client";
import { EMPTY_PREFERENCES, resolveOuting } from "../../../../lib/planner";

const context = { today: "2026-11-01" };
const send: typeof fetch = async (_url, init) => POST(new Request("http://localhost/api/plans/generate", init));

test("frontend interpreter → Next.js proxy → real Python planner → display cards", async () => {
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
      const r = await run("Bowling, drinks and a movie in Baltimore");
      assert.equal(r.plans.length, 3);
      const p = r.plans[0];
      assert.match(p.id, /^candidate-/);
      assert.deepEqual(p.venues.map(v => v.activity), ["bowling", "drinks", "movie"]);
      assert.equal(p.price, p.prices.reduce((n, q) => n + q.amount!, 0));
      assert.equal(p.groupCost, p.price! * p.people);
      assert.equal(p.travel, p.legs.reduce((n, q) => n + q.minutes!, 0));
      assert.equal(p.stops[0].start, 600);
      assert.equal(p.feasibility, "provisional");
      assert.match(p.issues.join(" "), /Opening hours/);
      assert.equal(p.venues[0].dataQuality?.price, "fictional");
      const raw = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: JSON.stringify(resolveOuting("Bowling, drinks and a movie in Baltimore", EMPTY_PREFERENCES, context).payload) }));
      assert.equal(raw.headers.get("cache-control"), "no-store");
      assert.deepEqual(adaptRanking(await raw.json()).plans, r.plans);
    }
    // different activities and all three preferences affect Python results
    {
      const ids = [];
      for (const cost of ["budget", "balanced", "experience"]) ids.push((await run("Coffee", { cost })).plans[0].venues[0].id);
      assert.deepEqual(ids, ["coffee-0", "coffee-1", "coffee-2"]);
      assert.equal((await run("Museum")).plans[0].venues[0].activity, "museum");
    }
    // manual overrides, hard budget, travel, capacity and infeasible messages
    {
      const r = await run("Dinner and karaoke for 2 people", { budget: "25", travel: "5", people: "4" });
      assert.ok(r.plans.length);
      assert.ok(r.plans.every(p => p.price! <= 25 && p.travel! <= 5 && p.people === 4 && p.stops[0].start! >= 1020));
      for (const prefs of [{ budget: "0" }, { travel: "0" }, { people: "21" }]) {
        const empty = await run("Dinner and karaoke", prefs);
        assert.equal(empty.plans.length, 0);
        assert.match(empty.message, /No candidate|cannot|exceed/);
      }
    }
    // matching events confirmed only against fiction; missing dates never substituted
    {
      const r = await run("Baseball and concert on 2026-11-07");
      assert.ok(r.plans.length);
      assert.ok(r.plans.every(p => p.feasibility === "confirmed" && p.date === "2026-11-07"));
      assert.match(r.plans[0].description, /fictional/);
      const missing = await run("Concert on 2026-11-08");
      assert.equal(missing.plans.length, 0);
      assert.match(missing.message, /No mock records/);
      assert.ok((await run("Concert on 2026-11-08", { date: "2026-11-07" })).plans.length);
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
      const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: '{"activities":["coffee"]}' }));
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
    }
    backend.kill();
    await once(backend, "exit");
    // stopped Python produces an explicit error and no legacy fallback
    {
      const r = await run("Coffee");
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
      const response = await POST(new Request("http://localhost/api/plans/generate", { method: "POST", body: '{"activities":["coffee"]}' }));
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
