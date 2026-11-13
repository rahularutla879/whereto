# Task 52 — private ordinary application integration

Baseline: `e831346c096222a63eb08470985e62e92d71a59e`. Profile: `52-private-ordinary-hosted-local-v1`. This is a local, explicitly installed composition with synthetic identities/providers and disposable SQL/Redis. Normal startup remains unchanged. No cloud resource, real grant, inference/token-count/Maps/identity request, owner database write, public traffic or Task 53 is authorized.

## Contract and acceptance boundary

Only `POST /api/interpret`, `POST /api/plans/generate` and authenticated `GET /api/health` are eligible. Pending answers use the interpretation route. Advanced planning, options, Details, origin lookup, saving/reopening/refresh, manual-only planning and diagnostics remain unavailable. An ordinary source that needs the advanced planner must block; optional/flexible/return semantics must never be flattened into ordinary required visits to obtain a result. This checkpoint does not enable V5.1 or change its grammar, Qwen, prompts, saved-plan RLS or any historical evaluator.

Acceptance requires actual Next/FastAPI requests through separate authenticated factory/counter/dispatcher/recovery processes, retained pending evidence without inference, owned/tab-safe current handles, protected SQL reservations before fake dispatch, negative/refusal coverage and unchanged normal application tests. Exact results, trials and unexecuted conditions are in [verification](task52-ordinary-hosted-verification.json). [Route matrix](task52-staging/ordinary-routes-v1.json) · [Handle contract](task52-staging/ordinary-outing-v1.json) · [Source manifest](../experiments/ordinary_hosted/build.json) · [Remaining gates](task52-staging/ordinary-next-gates.md).

## Ownership extension

`privateOuting` is optional in the browser client and emitted only by the selected profile. Its version is `52-private-ordinary-outing-v1`; fields are `version`, `handle`, `revision`, `expiresMs`. The handle is the existing factory's cryptographically unpredictable 256-bit URL-safe locator, not a graph, price, entitlement or bearer spending grant. SQL retains only its keyed hash and protected owner/revision/session association; its native ticket locator is AES-GCM encrypted in Redis. Native evidence retains original source, interpretation, reference clock, outing/root, financial inference identity and planning history.

The owner association derives from verified IAP issuer/audience/subject, additionally namespaced by this public adapter build. Existing SQL service/epoch checks and authenticated ciphertext bind the rest. Another tester, incompatible build, expired/revoked session, altered expiry or stale revision cannot borrow a locator. No latest-session-per-user cache or shared browser cookie pairs outings; each tab/request carries its own handle. IAP testers are not permanent Where To? accounts. Saved anonymous capabilities retain their independent rules and are not exposed here.

Continuation atomically consumes the existing protected route revision before reconstruction. A successful answer republishes the same handle at a newer revision; absolute expiry never renews. A lost response/interrupted turn remains consumed: no automatic retry, replay, reconstruction fallback or grant refund. Explicitly starting a new request is a new action under the same original protected root/grant limits, not a retry permission. Initial issuance uses an existing server-generated, durably consumed request ID; no proxy retry is implemented.

## Actual application flow

The actual Next route seams use `createOrdinaryProfile` only when trusted server code explicitly installs it. They verify IAP through `ServerIdentityPort`, acquire the frontend's own workload identity and seal exact original method/path/body bytes. Browser credentials are rejected/stripped, origin is checked, reads are bounded to 64 KiB/five seconds, original 70/115-second deadlines apply, and redirects/retries/fallbacks are forbidden. Health retains three seconds and is only liveness. No environment/header/query enables this composition. Final review also found and reproduced a partial-body timeout bug: reader cancellation could look like EOF after valid-looking JSON. The proxy now checks the separate five-second read signal before sealing; the regression requires zero identity seals and zero sends after timeout.

The local FastAPI facade wraps the actual application/lifespan and existing `RequestManagement`, with original production refusal untouched. Ordinary routes independently verify workload identity, frontend scope/IAP and witness nonces. The backend's own authenticated service identity forwards an envelope containing the unchanged public bytes/proofs to one fixed factory method. The factory independently rechecks the public proof/IAP in its own nonce namespace before using the existing typed validators and native broker. Backend workers possess nonce/epoch authority only, never issuer/counter/dispatch/recovery or operational Redis credentials.

Public HTTP JSON permits ordinary whitespace/key order, while rejecting duplicate keys, nonfinite values, excessive nesting and unknown typed fields. Parsing happens after byte-proof verification. Canonical evidence/financial JSON remains unchanged and strict. Neither request nor raw AI output is repaired to fit a gold answer.

Fresh interpretation uses existing `InterpretationInput`, native inference admission, protected synthetic token counting/max-charge reservation, independent delivery intent and fake model responder. It then captures the source with the native session/evidence factory. Pending answers use retained server evidence, the original fixed reference clock and existing `ClarificationAnswers`/legacy validator; browser pending interpretations are not accepted as evidence. No additional model action is needed for deterministic answers.

Generation validates `PlannerInput` against the retained effective request. Only existing typed execution controls (confirmed origin/current area and supported origin-reference/search controls) may be supplied at that boundary; changes to activities, date, destination, transport, budgets or timing meaning refuse. Execution controls are deterministically revalidated through the existing admission registry using the retained raw extraction, never a new model call or an admission bypass. The original outing/root/inference identity remains. The existing ordinary planner then constructs exact canonical search/matrix requests; restricted SQL derives price/units and conservatively reserves before single-use synthetic dispatcher calls. Provider errors/uncertainty retain exposure.

An explicit source/preferences edit under a handle revokes the previous native source and requires a new interpretation. A fresh request without an old handle is a separate outing; the service cannot infer that it is an edit to some other tab. Manual-only planning is blocked. One planning action per source revision remains consumed; revalidation is not a fresh planning grant. Unreviewed receipt/options/Details fields are nulled and corresponding exploration flags disabled, rather than exposing unsupported capabilities. Synthetic evidence is labelled in notes; `dataMode=real` reflects the exercised native adapter contract, not verified Google facts.

## Reliability investigation

The expiry discrepancy is reproducible in the original `Session.state` path: it resamples a database wall clock and a later monotonic clock when translating `source.created` back to milliseconds. A one-millisecond clock-pair skew changes the persisted integer by one millisecond. This includes quantization/round-trip effects; it is not evidence that simply increasing a timeout fixes anything.

The separately versioned `stable_session.Session` adapter retains the first protected integer creation time and restores that exact value from authenticated evidence. It does not round upward or change the original SQL/anchor deadline. Three deterministic tests reproduce the old result and check stable republication/restoration. The original native suite also runs unchanged, including its exact-deadline assertion; passing that invocation does not erase the deterministically reproduced old defect. The original native source/tests/manifests remain frozen; no retrospective pin or result changes.

The earlier unexplained `database_protocol` refusal cannot be attributed from its retained redacted trace alone. Its transaction wrapper intentionally suppressed the underlying protected SQL error. No state was retained that could establish a unique historical cause. New local refusal diagnostics retain only safe reason/category, SQLSTATE and filename/function/line, never queries, values, tokens or credentials. SQL failures still deny; no timeout increase, memory authority, refund or automatic retry is introduced. This remains a staging reliability investigation requirement.

## Final verification

Exact source-manifest SHA256: `7b9b2998e68c2396c519e909c8988aeefd4d793ddda5dcc3cc2e15638161d21d`. Frozen hosted-identity and service-isolation parent identities are retained in the manifest and verification record.

| Selected cohort | Passed | Skipped |
|---|---:|---:|
| Actual Next/FastAPI ordinary HTTP workflows | 13 | 0 |
| Deterministic timestamp reproduction/adapter | 3 | 0 |
| Current backend contracts/API/admission and recorded replays | 263 | 16 opt-in |
| Frontend, including four new ownership/proxy/client tests | 302 | 0 |
| Public JSON / frozen Node proxy / packaging | 20 | 0 |
| Hosted identity / native cross-worker / grants | 67 | 0 |
| SQL/financial/bridge/encrypted evidence | 112 | 0 |
| Service isolation / five separate interruption runs | 17 | 0 |
| **Total selected checks** | **797** | **16** |

Final selected cohorts had zero failures, timeouts or interruptions. Development failures are retained separately; this is not a full-backend-suite claim. TypeScript, ESLint, production build, Python compile/dependency consistency, new/parent identity checks and configured-secret scans passed. npm audit reports seven unchanged moderate tooling advisories and no high/critical matches. No fresh OS/image vulnerability database rescan or real browser UI run was performed.

Both actual pinned Linux amd64 images built and passed normal container smoke checks, including production refusal, controlled mock startup, proxy/health, unavailable AI/database refusal, non-root/read-only/dropped-capability operation, shutdown and restart/stale receipt refusal. The frontend image exposes only the closed Google identity artifact and retains a nonlaunchable startup contract; experiments, owner environment files and npm are absent. This verifies normal packaging, not hosted startup or real identity/provider readiness. Exact local image IDs are in the machine record; no registry publication occurred.

The original journal was verified read-only before/after: OpenAI7/Google2/Anthropic1, ten of594 attempts, $0.047366625 accounted, $11.952633375 remaining, original rows/corrections/root/hash and all324 private files unchanged, persistent halt active. No real grant or provider request was created. Disposable containers/named volumes were removed, unrelated anonymous volumes preserved and the dedicated VM stopped with its approved resources unchanged. Reviewed chapters3/6/7/12–15/18/20; updated3/6/7/12–15/18 and supporting handbook references. All20 original chapter contents are retained,12 unaffected chapters byte-identical.

## Development and privacy findings

Earlier failed fixture runs are retained in the machine record. They identified public JSON being incorrectly parsed as canonical evidence, a test-only transport deadline, correct native admission refusal after origin changes, and correct local provider-gate refusal. Fixes are confined to the new adapter or disposable test configuration; original validators, protected SQL and production guards remain unchanged. A container-command diagnostic exposed a temporary synthetic Redis password in local tool output. It was never an owner credential, the disposable cohort was removed, and the listing is not committed. Subsequent diagnostics print only sanitized service events.

## Verification limits and next checkpoint

The custom Next driver and fake metadata/JWKS/ingress, development-mode FastAPI preparation and Docker-exec TLS bridge are local test infrastructure, excluded from deployment images. They are not real Cloud Run IAP/IAM or a production bootstrap. The existing production startup gate remains nonlaunchable; the [new inert review record](../deployment/private-ordinary-startup-v1.json) does not change it. `/api/planning-mode` stays blocked, so full interactive private UI readiness is not claimed by API/client-driver success. Real hosted inference/tokenization, canonical transports, enrollment, grants, provider-content retention, independently operated restore authority, image security acceptance and managed-service failure/latency tests remain missing.

Public/native mapping for advanced/options/Details/origin/save/refresh, supported execution-control edits beyond this narrow set, browser UI acceptance and measured private-staging quality are separate gates. Current automatic source revalidation does not certify model accuracy, real routes or the five-second latency objective. Public launch requires separate owner approval. Proposed staging dollar figures remain unapproved.

Next bounded checkpoint: review ordinary edit/revalidation and UI recovery against this ownership contract, investigate remaining SQL reliability evidence, then integrate one specifically reviewed additional native/public workflow. Do not provision, enable paid calls or begin it automatically.
