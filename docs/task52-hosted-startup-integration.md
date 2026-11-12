# Task 52 — server identity port and guarded application boundary

Baseline `92bc3263a5a6e2006c90d03111776ae28081d35c`. Identity: **52-next-server-identity-port-local-v1**. Source-manifest SHA256: `283f026a044df840564ede56d132b09cc04e7f8e8a1d24a70cef9ac5a3cae9cd`. [Source manifest](../experiments/hosted_startup/build.json), [verification](task52-hosted-startup-verification.json), [route matrix](task52-staging/route-integration-v1.json), [startup contract](../deployment/private-startup-v1.json).

**Bounded result: server identity acquisition/forwarding and authenticated liveness are implemented. Full private hosted application startup remains blocked.** No cloud resource, real Google token, JWKS/metadata call, financial grant, inference, Maps request or owner database write is performed. This is not a functional cloud deployment, model qualification, or public-launch approval.

## Audit and the exact stopping boundary

The ordinary public `/api/interpret` returns `InterpretationResult`; a complete ordinary result has no durable source-ticket field. `/api/plans/generate` accepts `PlannerInput`, a typed planning DTO plus starting controls, not the native factory's owned source ticket/revision. Pending, advanced, options, Details and selected receipts have different existing tokens, several tied to process-local registries. The native factory instead accepts `{request, execution, requestId}` and returns a source-owned route; continuation consumes `{route, method, arguments}`. These representations are not interchangeable.

Treating a browser's validated-looking request/card as retained original interpretation would bypass source/optional-order ownership, revisions and financial roots. Pairing by the latest outing for an IAP user would confuse concurrent tabs and outings. Inventing a route from a native internal token would bypass factory scope. None is implemented. Existing manual-form planning also needs an explicit, reviewed source/action purpose distinct from an AI-source continuation.

Completing this bridge needs a separately reviewed public ownership contract: an opaque, server-issued outing handle carried through ordinary interpretation/pending/generate, or an equally explicit tab/outing-safe session mechanism. Any new field/cookie semantics need owner review under this checkpoint's prohibition on unapproved public-contract changes. It must preserve manual edits, source invalidation, pending answers, native ticket revisions, selected receipt reuse and saved bearer/RLS access. No new permanent account model is proposed.

`backend.main` still refuses production, known hosting and `NODE_ENV=production` at import and lifespan. `deployment/private_startup.py` deliberately exits78 even when supplied readiness-looking environment booleans. It has no activation, local-model fallback or provider-dispatch branch. A configuration file is not authenticated evidence that real SQL/Redis/grants/epoch/inference are ready.

## Actual route integration

Every existing Next proxy entry point now checks `privateRoute` before its old behavior. With no trusted bootstrap installation, it returns null and the existing path runs unchanged. No HTTP/header/query/environment selector installs a profile. A branded status-only object can be installed once by reviewed server code; a caller-supplied object cannot substitute for it.

| Route | Existing limit / timeout | Selected private profile | Remaining binding |
|---|---|---|---|
| GET `/api/health` |3 seconds | Node IAP + metadata verification, method/body-bound scope; authenticated FastAPI liveness | Not financial/application readiness |
| GET `/api/planning-mode` |30 seconds |503, no normal-mode fallback | Do not advertise enabled planning before integration |
| POST `/api/interpret` |backend65,536 bytes /70 seconds |503 before parsing/provider work | Public ordinary source handle and issuer-owned request identity |
| POST `/api/plans/generate` |backend65,536 /115 seconds |503 | Exact source/manual purpose, edits, native revision/root/outing |
| POST `/api/plans/advanced` |4,096 /45 seconds |503 | Public advanced token to owner-bound native continuation |
| POST `/api/plans/options` |backend65,536 /115 seconds |503 | Durable membership/history, pagination and exploration scope |
| POST `/api/starting-areas` |backend65,536 /115 seconds |503 | Native pre-source area path remains unsupported |
| POST `/api/starting-places` |backend65,536 /30 seconds |503 | Source-owned reference, origin confirmation and original budget |
| POST `/api/venues/details` |backend65,536 /30 seconds |503 | Allowed venue/attempt mapping; preserve600/1800-second scope distinction |
| POST `/api/plans/save` |4,096 /45 seconds |503 | Reusable selected receipt mapping plus existing RLS/persistence |
| POST `/api/plans/reopen` |4,096 /45 seconds |503 | Existing anonymous bearer/RLS/expiry; do not invent source evidence |
| POST `/api/plans/refresh` |4,096 /45 seconds |503 | Owner-approved purpose-specific access/membership/replay, independent of IAP account ownership |
| GET `/api/development-diagnostics` |local-only /5 seconds |404 | Never enroll in private hosted exposure |

Business refusals do not read raw graphs, call AI, issue capabilities, reserve spending, renew expiry or forward to the old local backend. This is explicit unavailability, not disabling AI to claim successful functional deployment. Default mode retains its previous response DTOs, privacy controls and local-only persistence guards. Health GET overloads preserve existing no-argument test callers while satisfying this installed Next version's route types.

## Server-side identity port

`lib/server-identity.ts` implements the former interface using exact-pinned **jose6.2.17**, verified against official npm metadata/integrity. No other package version is upgraded. Production `createGoogleIdentityPort` fixes metadata to the assigned service identity endpoint with exact encoded backend audience, `Metadata-Flavor: Google`, `format=full`, no redirects/retries and a2-second acquisition bound. It fixes the two Google JWKS origins; no browser URL/key/issuer or service-account JSON key is accepted. This factory was not used against real endpoints.

Signatures, exact issuer/audience, service-account subject/email/verified flag, IAP tester subject, integer issue/expiry and lifetime bounds precede cache/proof use. Duplicate JSON keys, unsupported JWT headers/algorithms, malformed identities and invalid private signing-key sizes refuse. Default Google verification rejects fixture key IDs. Test roots are supplied only by explicit server-side fixture composition, excluded from production artifacts; no environment flag enrolls them in Google trust.

One in-flight metadata acquisition serves concurrent waiters. Only a verified token with more than30 seconds remaining is reused; near expiry refreshes once. Failed acquisition has a5-second cooldown, no stale fallback or automatic retry. Cancelling one caller refuses that caller promptly without cancelling another waiter's shared, independently bounded acquisition. Cancellation is checked again before returning dispatch headers. Google JWKS cache is bounded to60 seconds, unknown-key refresh cooldown60 seconds, with bounded100KB responses and positive Cache-Control lifetime of at least60 seconds; shorter/absent cache policy refuses. Real rotation/availability compatibility remains unverified.

The public HTTP proof uses **new namespaces** `urn:whereto:http-request-proof:v1` and `urn:whereto:http-iap-forward:v1`, binding actual GET/POST method, exact final bytes, path, audience, IAP/token hashes, nonce, build/environment/epoch and expiry. It does not relabel the old native POST-only proof. No post-seal JSON parsing/reserialization is allowed. Source proof never repairs a model graph. New source and schema/model authority are still required before any future spending action.

The read-only frontend retains the3-second health deadline, bounded4KB response, cancellation, no cache, no redirects/retries, constant browser response and no upstream credential/cookie headers. Browser Authorization/custom identity headers refuse; unsigned IAP user/email headers are ignored/dropped, never trusted. The signed assertion is independently verified at Next and at the downstream FastAPI boundary. Email is not a user account identifier.

## Local process composition and what it proves

The local harness reuses the unchanged disposable SQL/Redis/witness/grant and authenticated service foundations. It adds two non-root, read-only FastAPI status processes with **nonce/epoch-only witness credentials**, never factory/issuer/counter/dispatcher/recovery or Redis secrets. Root is used only in a networkless, capped source-copy helper before runtime starts; it has no database credentials. A separate immutable code snapshot avoids modifying the frozen services' running snapshot. Exact task volumes are removed; no prune.

The actual Next frontend is started programmatically from the production build, with trusted code installing the status profile before requests. Fake metadata and public fixture JWKS remain server-side; temporary files are0700/0600 and deleted. A loopback-only, secret fixture ingress gate protects this test driver. It is not real Google IAP. A Docker-exec test transport carries the exact signed request into real TLS/HTTP FastAPI processes in the disposable network; it is not the future Cloud Run HTTPS transport. Default `BACKEND_URL` is an unreachable loopback port so a missing seam cannot touch the owner's backend.

The FastAPI fixture wraps the actual `backend.main:app` with a health-only authenticated boundary and runs its lifespan under ordinary **development** environment. Only AI preparation is replaced by a fake; neither `validate_environment` call is patched. Requests and provider network operations are blocked. This is development compatibility evidence, **not production backend startup**. The Next custom-server warning about standalone output is retained: the local driver is not a deployment recipe and is not copied into images.

Eight actual cases cover both backend processes, signed IAP/header refusal, all public business-route refusals, raw HTTP replay/wrong audience/unsigned forwarding, process restart, operational SQL/Redis loss, witness outage and independently authenticated synthetic operator epoch rotation. SQL confirms zero provider operations. Existing native/financial/evidence regression suites separately cover source ownership, other-user ticket theft, ordinary/advanced continuation, optional/flexible/return constraints, receipts, refresh, crashes and uncertainty. Combining these results does not establish that those workflows run through the new Next hosted facade.

## Deployment/package and remaining gates

The normal non-root Docker recipes, pinned Linux amd64 bases and backend payload remain intact. The frontend dependency lock now includes jose and the real API entry seams compile in the ordinary image. A fixed build-stage transpiler packages `/app/private-runtime/server-identity.mjs` plus its JSON validator and nonlaunchable contract, with exact jose runtime files. The shipped identity module exposes only `createGoogleIdentityPort`; the fixture-injection constructor is not exported. No fixture, key, test runner or new hosted activation is added. The packaged identity-port implementation is not an activated standalone bootstrap. A reviewed production composition must explicitly trace/package it, acquire real service identity and enroll dependencies; do not deploy the local custom driver or synthetic schema/reset scripts.

Remaining: public-token/native ownership contract and facade; real authenticated service transports/readiness; actual IAP/IAM all-ingress/Invoker/subjects/audiences; proof-key rotation/revocation and nonce maintenance; Supabase/Redis capacity/roles/privacy/migration; independently administered witness/backup/epoch reconciliation; qualified hosted LLM and real tokenization/pricing; canonical paid transports and explicit grant; image security acceptance and private end-to-end quality, latency, cost and rollback. Proposed spending figures remain unapproved. No public launch or Task53.

Next bounded checkpoint: review the ordinary source-handle/session contract and retained native expiry/SQL reliability evidence, then implement only ordinary interpretation→pending→planning public/native mapping with synthetic authority, keeping unsupported paths refused. Do not automatically begin it.

## Verification provenance

Final selected cohorts: **757 passed /16 opt-in skips**, with no final failures; this is not full backend discovery. Exact per-cohort counts, development failures, skips, warnings and unexecuted conditions are in the machine record. The first unchanged hosted cohort had one unexpected403 and passed20 on quiet rerun. Native attempts recorded an exact one-millisecond earlier-expiry mismatch and a separate `database_protocol` refusal during advanced inference cleanup; the full third selection passed all17 native cases with fail-fast disabled, retaining both earlier failures. No parent source, assertion, SQL timeout or pin was changed. These are reliability evidence, not permissions to ignore a refusal.

The final frontend cohort passed298, packaging/startup/artifact/resource tests passed15, and the new actual Next/FastAPI cohort passed8. TypeScript, ESLint, native production build, both Linux amd64 image builds and existing container smoke passed. The unchanged smoke uses its explicit synthetic test environment; that does not establish hosted production startup. Seven moderate npm tooling matches remain, with no high/critical npm matches. A fresh full image vulnerability scan and browser/hosted quality checks were not run; existing container security residuals remain open.  Historical ten attempts, $0.047366625 accounted, $11.952633375 remaining,324 private files and persistent halt are verified read-only before/after. No historical source pin, scorer, prompt, model or result is changed.

Primary references: [Cloud Run assigned-service metadata authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service), [jose official project](https://github.com/panva/jose); installed Next guides `node_modules/next/dist/docs/01-app/01-getting-started/15-route-handlers.md` and `02-guides/custom-server.md` were read before code. Only public documentation/package metadata were retrieved, never Google identity endpoints.
