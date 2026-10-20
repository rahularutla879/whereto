import assert from "node:assert/strict";
import { createServer } from "node:http";
import { once } from "node:events";
import test from "node:test";
import { GET } from "./route";

test("Next.js health handler communicates over HTTP and handles backend failures", async () => {
  let body = '{"status":"ok"}';
  let status = 200;
  let stall = false;
  let requestedPath = "";
  const server = createServer((request, response) => {
    requestedPath = request.url ?? "";
    if (stall) return;
    response.writeHead(status, { "Content-Type": "application/json" });
    response.end(body);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.ok(address && typeof address === "object");
  const previousUrl = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${address.port}/`;

  async function expectUnavailable() {
    const response = await GET();
    assert.equal(response.status, 503);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.deepEqual(await response.json(), { status: "error", backend: "unavailable" });
  }

  try {
    const response = await GET();
    assert.equal(response.status, 200);
    assert.equal(requestedPath, "/health");
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.deepEqual(await response.json(), { status: "ok", backend: "ok" });

    status = 500;
    await expectUnavailable();
    status = 200;

    for (body of ['invalid json', 'null', '{}', '{"status":"error"}']) {
      await expectUnavailable();
    }

    stall = true;
    await expectUnavailable();

    const closed = once(server, "close");
    server.close();
    server.closeAllConnections();
    await closed;
    await expectUnavailable();
  } finally {
    server.close();
    server.closeAllConnections();
    if (previousUrl === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = previousUrl;
  }
});
