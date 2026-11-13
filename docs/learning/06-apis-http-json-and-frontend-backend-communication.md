# 06 — APIs HTTP JSON and Frontend Backend Communication

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## An API is a contract, not a magic connection

An API specifies an address, method, allowed input, output and failure behavior. HTTP has a **method** such as GET (retrieve metadata) or POST (submit work), **headers** carrying metadata, an optional **body**, and a **status code** in the response. Where To? uses JSON bodies so TypeScript and Python can exchange structured values without sharing memory.

A small interpretation request can be written as:

```json
{"text":"Dinner and drinks in Sydney today.","preferences":{}}
```

This is an illustrative request body, not a captured successful run. The first property supplies the owner's words; the second leaves manual fields at their defaults. JSON uses double-quoted names and strings. An empty object is not the same as `null`; a missing property is not always equivalent to either. Dates in JSON are strings; the receiving model validates them. Comments and trailing commas are not standard JSON.

## Follow the client's real HTTP call

The existing call in [lib/planning-client.ts](../../lib/planning-client.ts), excerpted without optional context fields:

```typescript
const interpreted = await send("/api/interpret", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text, preferences }), cache: "no-store"
});
```

Line 1 submits to the same-origin API and waits; `send` normally delegates to fetch and can be replaced in tests. Line 2 selects POST and declares JSON. Line 3 serializes the input object and prevents caching. Line 4 ends the options object. The full source also supplies cancellation/timeouts and, where relevant, pending clarification, answers and location/calendar context. The output `interpreted` is a Response; `await interpreted.json()` decodes it. The client checks `ok`, required arrays and pending question shapes before choosing the next path.

The same browser path is forwarded by [app/api/interpret/route.ts](../../app/api/interpret/route.ts) to FastAPI's `interpret_endpoint`. A relative path means the browser does not need the backend's host or private Google credentials. The proxy's `BACKEND_URL` stays server-side.

## Status is not domain outcome

| HTTP result | Meaning in this repository |
|---|---|
| 200 | Handler returned normally; interpretation may still contain questions, or advanced status may be clarification/no_results |
| 400 | Next.js could not parse request JSON on relevant proxy routes |
| 403 | Local/private-origin boundary refuses the caller |
| 408 / 413 | Managed body read timed out / exceeded its bound |
| 409 | Duplicate in-flight request or a scoped conflict/expiry, depending on code |
| 422 | Invalid input or an explicit validation refusal |
| 429 | Burst/provider quota classification where applicable |
| 500 / 503 | Internal failure, service unavailable, or a classified dependency/admission failure |

Use the response `code` and `message` with the status. Do not turn every 503 into “Google quota exceeded” or every empty response into “no venues exist.” The exact mapping lives in [failures.py](../../backend/failures.py), [provider_errors.py](../../backend/provider_errors.py), the endpoint handlers and client adapters.

## Serialization, transport and validation are separate

**Serialization** converts a value to transferable text. **Parsing** reconstructs structure. **Validation** determines whether that structure is allowed. A syntactically valid model response can still invent an ordering edge. A correctly parsed venue can still be outside the destination. A complete 200 response can still ask a necessary question. Keep these steps distinct while debugging.

`Cache-Control: no-store` tells intermediaries/browsers not to retain API responses as an HTTP cache. This does not erase JavaScript state or prevent intentional saved-plan storage. `AbortSignal` carries cancellation. A canceled browser fetch does not establish that a backend worker or billable provider request never started; worker ownership and reservations remain important.

The reference lists every current public proxy and backend route, request fields and response families. Do not experiment with POSTs merely to learn API syntax: an apparently harmless generation, origin lookup, detail refresh or continuation can perform real provider work on the owner's configured profile. Start with source inspection and health GETs.

## Packaged service networking

`deployment/frontend-entry.mjs` requires an explicit server-only `BACKEND_URL`. HTTPS origins are accepted; plain HTTP is limited to loopback for isolated native/container smoke. It imports Next’s standalone `server.js` in the same process so termination reaches the server. The current proxy does not attach Cloud Run IAM identity tokens, so private hosted invocation remains a blocker. `/api/health` verifies backend reachability; backend `/health` does not certify AI or database readiness. No paid inference is used as a health probe.

## Five key takeaways

1. An endpoint includes method, path and contract.
2. JSON parsing is distinct from validation.
3. HTTP 200 can contain clarification.
4. The same path passes through two server layers.
5. Canceled transport does not refund provider work.

## Check your understanding

06.Q1. What does Content-Type describe?
06.Q2. Why call JSON.stringify?
06.Q3. Can a 200 reply contain no plan?
06.Q4. Which variable selects the proxy backend?
06.Q5. Is a failed network response proof nothing was billed?

## Code-reading exercise — 06.R

Read both interpret route handlers and find where malformed JSON, invalid shape and unavailable AI receive different treatment.

## Practical exercise — 06.P

Write a JSON interpretation body in a scratch note, then identify each property in InterpretationInput without sending it.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-06).

[Previous chapter](05-backend-python-fastapi-and-pydantic.md) · [Contents](README.md) · [Next chapter](07-complete-end-to-end-outing-request-lifecycle.md)

## Private experimental RPC is not a public application API

The inactive [service fixture](../../experiments/service_isolation/server.py) exposes fixed POST methods only on its disposable loopback network. TLS verifies the service certificate; a separate synthetic workload signature binds exact caller role, audience, path, body, build, epoch, expiry and a durable single-use nonce in the independent witness database. Typed application validation and SQL financial permission are still required afterward. Request bodies are capped at200KB and responses at1MiB to fit the existing plan DTO; no public DTO changes. Normal Next proxies and FastAPI routes do not select this mechanism. Hosted Google identity verification and independently verified user forwarding are still absent.

## Request identity and user forwarding are different proofs

The inactive [Node forwarding contract](../../experiments/hosted_identity/proxy.server.ts) lists fixed paths and original timeout/body limits. It drops browser Authorization, cookies and unsigned identity headers, never follows redirects/retries and never copies credential response headers. Its server-owned `ServerIdentityPort` must independently verify IAP and obtain/seal the service identity; that production composition is not wired. Tests of this helper are distinct from the Python TLS multi-process fixture and from browser verification.

`HostedAuth` uses Google-only keys; `Auth` explicitly uses isolated offline keys. A separate frontend signature binds the IAP assertion to the exact action body/path/build/epoch, while each hop has its own Google identity and single-use request proof. An IAP user assertion cannot replace a workload token, nor can a workload choose a user through a header. Real Cloud Run IAM and all-ingress IAP configuration still require independent deployment tests.

## Server-owned credentials at actual proxy entry points

`lib/server-identity.ts` implements `ServerIdentityPort.verifyAndSeal`. It verifies a Google-shaped workload identity and an independent IAP assertion, then signs exact method/path/body/token hashes with the frontend's own proof key. Production construction fixes metadata/JWKS origins; tests explicitly inject synthetic sources. A verified token is cached only with more than30 seconds left. Concurrent calls share one bounded acquisition; a cancelled waiter cannot dispatch or cancel another waiter's acquisition.

`privateRoute` is checked at every actual proxy entry, before old parsing/local guards. A branded profile can be installed once by trusted server code; no header or environment flag installs it. Current private business routes return503, diagnostics404, and only health forwards a freshly sealed request. This is a source-level integration seam, not a live deployment. The new method-aware HTTP proof namespaces differ from frozen native POST RPC; GET must never be signed as POST. See [route matrix](../task52-staging/route-integration-v1.json).


## Optional private outing ownership

Only the selected private profile returns `privateOuting` with `version`, opaque `handle`, protected `revision` and fixed `expiresMs`. `lib/private-outing.ts` validates this optional extension; `generateOuting` carries it in tab-local continuation and generation requests. Without it, normal request bodies remain unchanged. Private answers do not submit browser pending interpretations as evidence. Exact original bytes are signed before forwarding; duplicate-aware public JSON parsing permits whitespace without relaxing canonical financial/evidence records. See [Task 52 ordinary integration](../task52-ordinary-hosted-integration.md).


## Inactive ordinary private browser checkpoint

Only the selected UI profile adds authenticated GET `/api/planning-mode` and POST `/api/private-ordinary/revoke` alongside ordinary routes. Readiness returns `enabled:false` with a separately scoped synthetic-dependency flag, never financial or production permission. Normal revoke is404. Public/service proofs retain separate build identities; exact method/body and IAP ownership remain mandatory. See the [UI/recovery report](../task52-ordinary-private-ui.md).
