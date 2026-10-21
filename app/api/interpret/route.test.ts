import assert from "node:assert/strict";
import test from "node:test";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { POST } from "./route";
import { POST as planPOST } from "../plans/generate/route";
import { generateOuting } from "../../../lib/planning-client";
import { EMPTY_PREFERENCES } from "../../../lib/planner";

test("raw text → interpretation proxy → Python provider → validated request → Python engine → cards", async () => {
  let modelCalls = 0;
  let requestText = "coffee, museum, then coffee in Baltimore for 2 people under $30 each";
  let modelStatus = 200;
  let modelContent = JSON.stringify({ activities: ["coffee", "museum", "coffee"], people: 2,
    location: "Baltimore", date: null, budget_per_person: 30, currency: "USD", preferences: [] });
  const model = createServer(async (req, res) => {
    let body = "";
    for await (const chunk of req) body += chunk;
    assert.equal(JSON.parse(body).messages.at(-1).content, requestText);
    modelCalls++;
    res.writeHead(modelStatus, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ done: true, message: { content: modelContent } }));
  });
  model.listen(0, "127.0.0.1");
  await once(model, "listening");
  const ma = model.address(); assert.ok(ma && typeof ma === "object");
  const reservation = createServer(); reservation.listen(0, "127.0.0.1");
  await once(reservation, "listening");
  const ba = reservation.address(); assert.ok(ba && typeof ba === "object");
  await new Promise<void>(r => reservation.close(() => r()));
  const previous = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${ba.port}`;
  const python = spawn("backend/.venv/bin/python", ["-m", "uvicorn", "backend.main:app", "--port", String(ba.port), "--host", "127.0.0.1", "--log-level", "warning"],
    { env: { ...process.env, AI_BASE_URL: `http://127.0.0.1:${ma.port}` } });
  const paths: string[] = [];
  const send: typeof fetch = async (url, init) => {
    paths.push(String(url));
    return (url === "/api/interpret" ? POST : planPOST)(new Request(`http://localhost${url}`, init));
  };
  const run = (preferences = EMPTY_PREFERENCES) => generateOuting(requestText, preferences, undefined, send);
  try {
    let ready = false;
    for (let i = 0; i < 100; i++) {
      try { ready = (await fetch(`${process.env.BACKEND_URL}/health`)).ok; } catch { /* startup */ }
      if (ready) break;
      await new Promise(r => setTimeout(r, 50));
    }
    assert.ok(ready);
    const result = await run();
    assert.equal(result.plans.length, 3);
    assert.deepEqual(paths, ["/api/interpret", "/api/plans/generate"]);
    assert.equal(modelCalls, 1);
    assert.deepEqual(result.plans[0].venues.map(v => v.activity), ["coffee", "museum", "coffee"]);
    assert.match(result.plans[0].id, /^candidate-/);
    assert.equal(result.plans[0].people, 2);
    assert.ok(result.plans.every(p => p.price! <= 30));
    // Model deliberately omits tomorrow: the source guard and deterministic
    // resolver must carry the local calendar date through real HTTP to cards.
    modelContent = JSON.stringify({ activities: ["coffee"], people: 2,
      location: "Baltimore", date: null, budget_per_person: null, preferences: [] });
    requestText = "coffee in Baltimore for 2 people tomorrow";
    const localDate = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
    const tomorrow = new Date(Date.parse(`${localDate}T00:00:00Z`) + 86400000).toISOString().slice(0, 10);
    paths.length = 0;
    const relative = await run();
    assert.equal(relative.plans.length, 3);
    assert.ok(relative.plans.every(p => p.date === tomorrow));
    assert.deepEqual(paths, ["/api/interpret", "/api/plans/generate"]);
    requestText += " between 6 and 9 PM";
    const window = await run();
    assert.ok(window.plans.length > 0);
    assert.ok(window.plans.every(p => p.stops.every(stop => stop.start! >= 1080 && stop.end! <= 1260)));
    const override = await run({ ...EMPTY_PREFERENCES, date: "2099-01-01" });
    assert.ok(override.plans.every(p => p.date === "2099-01-01"));
    requestText = "coffee in Baltimore for 2 people tomorrow from 10 PM to 1 AM";
    paths.length = 0;
    const overnight = await run();
    assert.equal(overnight.plans.length, 0);
    assert.match(overnight.message, /Overnight/);
    assert.deepEqual(paths, ["/api/interpret"]);
    modelContent = "{}";
    paths.length = 0;
    assert.match((await run()).message, /AI interpretation unavailable/);
    assert.deepEqual(paths, ["/api/interpret"]);
    modelStatus = 500;
    assert.equal((await run()).plans.length, 0);
    assert.equal((await POST(new Request("http://localhost/api/interpret", { method: "POST", body: "bad" }))).status, 400);
  } finally {
    python.kill(); await once(python, "exit");
    model.close(); model.closeAllConnections();
    if (previous === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = previous;
  }
});

test("interpretation proxy rejects malformed upstream and preserves safe errors", async () => {
  let status = 200; let body = '{}';
  const server = createServer((_req, res) => { res.writeHead(status); res.end(body); });
  server.listen(0, "127.0.0.1"); await once(server, "listening");
  const address = server.address(); assert.ok(address && typeof address === "object");
  const previous = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${address.port}`;
  try {
    for (const [nextStatus, nextBody, expected] of [[200, '{}', 503], [200, 'bad', 503], [422, '{"message":"Invalid input"}', 422], [503, '{"message":"AI unavailable"}', 503]] as const) {
      status = nextStatus; body = nextBody;
      const r = await POST(new Request("http://localhost/api/interpret", { method: "POST", body: '{}' }));
      assert.equal(r.status, expected); assert.equal(r.headers.get("cache-control"), "no-store");
    }
  } finally {
    server.close(); server.closeAllConnections();
    if (previous === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = previous;
  }
});
