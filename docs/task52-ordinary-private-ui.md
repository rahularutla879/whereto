# Task 52 — inactive ordinary private UI and recovery

Baseline `da7b99acd4217ec4d669140a8512d72b95b06e9b`. New profile `52-private-ordinary-ui-local-v1`; public UI contract `52-private-ordinary-ui-v1`. This is a synthetic local checkpoint, not a hosted deployment or public launch. Normal startup, Qwen, prompts, ordering policies, saved schema/RLS, financial policies and frozen evaluation artifacts remain unchanged. No real identity/model/Maps call, grant, real account enrollment, owner database write, migration or provisioning is authorized. Exact final results are in [verification](task52-ordinary-private-ui-verification.json).

## Browser audit and integration

The existing `Home` uses React memory for request/preferences, `PendingOuting`, `ValidatedOuting`, candidate pages and cancellation. It submits the browser pending interpretation and manual overrides in the normal legacy path, and offers retry/regenerate. That is not distributed source authority: a private source turn is durably consumed and may have incurred costs even if no response arrived. Repeating it or guessing the user's latest outing would violate the protected contract.

Only trusted server code can install `createOrdinaryUIProfile`. Its authenticated `/api/planning-mode` response includes a new explicitly scoped private marker. `Home` selects `PrivateOrdinaryExperience` for that marker; normal responses and normal rendering remain unchanged. The private component reuses existing typography/layout styles, `HeroArtwork`, `OutingDateField`, `OutingSummary`, `PlanCard`, itinerary stops and `adaptRanking`. It does not implement a planner, recommendation algorithm or new ordering parser. `PlanCard`'s optional synthetic label defaults off; synthetic cards are not labelled verified real venues.

The private flow explicitly separates interpretation, requested answers, confirmation of execution controls and one generation. It exposes no advanced, pagination, discovery, standalone origin lookup, provider Details, save/reopen/refresh or manual-only path. Advanced/optional/flexible/return requirements are retained and blocked, never flattened. Existing card expansion reads only returned venue/route/timing information; it makes no Details request without an issued token.

## Ownership, edits and recovery

`PrivateOrdinaryClient` keeps only the original request input/preferences, opaque `52-private-ordinary-outing-v1` handle, current revision/deadline and necessary public display DTOs in memory. It discards the raw interpretation/pending graph instead of retaining it as evidence. Only the server factory reads original evidence from encrypted Redis with current SQL ownership/revision/fence and independent epoch. No browser value selects a financial root, model, price or provider permission. Multiple tabs have independent controllers/handles; there is no latest-session lookup or shared outing storage.

| Action | Private behavior |
|---|---|
| Initial source/preferences | Existing text, location, date and transport controls feed a new typed interpretation request; no manual-only bypass. |
| Pending answer | Only the server-requested fields are sent alongside the identical original input and current handle. No browser raw graph or new inference. |
| Source meaning/date/destination/mode/activity/budget edit | Existing controls are locked after interpretation. Explicit **Discard outing and edit** revokes the owned native source before beginning a new action. No silent reinterpretation or regeneration. |
| Execution controls before generation | User confirms numeric origin coordinates; radius editing remains unavailable without a separately authorized search point. Existing typed native validators and admission revalidation apply. No geolocation permission, lookup or invented origin is silently supplied. Other native controls are not advertised as UI-supported. |
| Generation | Current owned handle/request plus reviewed controls; all existing identity/source/evidence/admission/grant/reservation/payload/dispatch/epoch checks. One generation, no retry. |
| Failure/response loss | Clear local authority, show explicit stopped/uncertain instructions, retain conservative SQL exposure. No automatic resend or financial refund. |
| Refresh/back navigation | No browser storage or automatic resumption. `pagehide`/persisted `pageshow` clear source, handle, cards, preferences and coordinates. A generation counter prevents late responses from reviving discarded authority. |
| Expiry | Absolute deadline is not renewed. Local expiry removes the handle; the server independently rejects stale/expired/revoked authority. Cards, if present, are snapshots only. |
| New outing after completion | An explicit user action, never an automatic retry. Existing aggregate/root/day/outing limits still apply. |

No raw source, model evidence, graph, outing handle, candidate result or bearer saved capability is persisted to localStorage/sessionStorage/indexedDB. This intentionally does not implement refresh recovery of in-progress work. There is no new read-only session-status operation because safely discarding on reload requires none. Lost initial responses cannot be recovered by guessing a source. Safe reconstruction from server records remains a separate reviewed future UI contract.

### Authenticated discard

New `POST /api/private-ordinary/revoke` is available only under the explicitly installed UI profile; normal startup returns404. It accepts exactly the versioned handle, independently verifies frontend/workload/IAP ownership, consumes the protected route turn, checks original expiry, reconstructs authenticated native state and invokes existing `Session.revoke`. It grants no provider work and changes no financial exposure. Wrong-user/stale/altered/replayed requests refuse. If a source was already consumed/uncertain, the client never recovers it to retry.

## Non-billable readiness

Liveness stays `/api/health`. The UI profile's authenticated `GET /api/planning-mode` deliberately returns `enabled:false`, `mode:unavailable`, no starting lookup, `productionReady:false` and `financialAuthorization:false`. Its separately versioned private marker reports only dependency availability for the synthetic ordinary path. It is not broad app readiness, financial entitlement, a quote or an approved cloud startup.

Dedicated, owner-controlled `SECURITY DEFINER` read routines run inside SQL READ ONLY transactions. Both use fully qualified objects and fixed search paths, revoke PUBLIC access and are owned by the existing NOLOGIN owner. Only the existing issuer/factory witness roles receive execution; ordinary runtime cannot call them. They check protected configuration/epoch/expiry/accounting/global exhaustion, compare the complete operational/witness committed history, and reject pending/quarantined/disagreeing authority. Redis PING proves service availability, not that a particular outing record exists; missing source evidence still refuses at continuation without reconstruction. Fixed authenticated counter/dispatcher/recovery probes verify dependency availability. Probes never count tokens, mint capabilities, reserve spending, dispatch, update a user session, extend TTL or reconcile a restore. Authentication nonces are still consumed; these are separate security facts, not financial or session transitions.

Snapshots are conservative point-in-time availability only. Concurrent financial work can make readiness temporarily unavailable, and a new operation must still pass every current permission and scope/rate window. Per-action/per-outing feasibility cannot be promised by a session-free probe. All refusals return bounded generic booleans, not credentials, topology, prices or detailed errors. No service-identity check substitutes for user/source authority.

## Local fixture and trust boundaries

`experiments/ordinary_ui/` is a separately pinned adapter over the unchanged ordinary/native/financial/service foundations. The original ordinary artifact and its Python implementation remain frozen. Because reviewed frontend files change, the old complete-source verifier properly refuses the new checkout; it is not repinned or claimed to authorize this profile. The new verifier checks the frozen parent artifact/unchanged ordinary algorithms, parent hosted/service identity and all current adapter/frontend sources. New public proofs/owner namespaces use the new UI build, while private service calls retain their separate service build.

The custom loopback Next fixture simulates IAP ingress using a temporary HttpOnly/SameSite cookie mapped server-side to one fictional tester. Its random cookie value is separate from the private test-harness ingress credential. It verifies exact loopback Origin before translating to the canonical offline frontend origin, rejects browser identity headers, and injects the signed fixture assertion only server-side. An isolated fake IdP retains only temporary synthetic IAP key material in the bootstrap controller overlay, not workers, the frontend, source volume or Git. It issues fixed enrolled fictional testers at the unchanged600s assertion lifetime. Fresh identity assertions do not renew native session expiry, budgets or consumed operations. Direct HTTP tests refresh their trusted fixture credentials, and the unchanged client-driver case receives a current assertion before execution; verifiers still reject expired input and fixture roots remain forbidden in production. There is no real Google signing key, enrollment or general HTTP signing endpoint.

It stores no outing in that cookie and never claims real IAP authentication. Offline keys, ingress mapping and Docker-exec TLS transport are excluded from deployment images. The fixture rejects hosted indicators and binds loopback; authority services require disposable Docker/loopback isolation. Nothing in normal startup enrolls those roots or installs this profile. Anonymous saved capabilities and permanent account semantics are unchanged.

## SQL reliability investigation

Controlled missing owned evidence reproduces `database_protocol` with SQLSTATE `P0001`; protected lock contention produces `55P03` and an unavailable refusal under the original250ms lock/1500ms statement deadlines. After releasing the synthetic lock, a fresh non-billable read works; no provider retry is performed. Concurrent requests, worker handoff, restart, Redis loss and witness outage are separate application/process tests. Sanitized instrumentation records fixed reason/category, SQLSTATE and filename/function/line only, never SQL parameters, raw errors, credentials or user text.

These expected controlled refusals do **not** establish the cause of the earlier unexplained historical refusal. Its trace is insufficient to distinguish missing/expired evidence from another protected condition. It remains an operational risk requiring load/staging investigation. No timeout increase, fallback, pin change, refund or automatic retry hides it.

## Verification and remaining gates

Final browser versus direct HTTP results, failed development trials, exact suite counts, local image IDs, dependency/security residuals and checks not run are recorded separately in the verification record. A synthetic extraction does not prove model accuracy or real venue/route quality. Local authenticated process tests are not Google IAM/IAP enrollment or independent hosted recovery validation.

The next concrete checkpoint is to complete reviewed production-compatible packaging/bootstrap for this narrow ordinary profile and its private identity/dependency wiring using fake services, while retaining all unsupported routes closed. Real enrollment/migration, provider-content retention, independent recovery operation, hosted LLM qualification/tokenization, exact prices and finite owner-approved grants, image-security acceptance, private quality/latency/restore tests and public-launch approval remain blockers. No automatic next task, provisioning, paid usage or Task53.

### Browser failure trial: unknown fake input

An independent browser tab submitted `Coffee, maybe museum, dinner in Baltimore tomorrow` while another tab was generating. That exact text is absent from the fixed synthetic responder's allowlist: this is a fake-provider input failure, not evidence that a model misinterpreted it. The existing dispatcher refused; inference uncertainty conservatively stopped the synthetic grant. The other generation received `grant_stopped`, both pages displayed a stopped/no-retry message, and the manual dependency check became unavailable. This does not establish a defect in SQL accounting or the cause of the older `database_protocol` finding. The halted disposable cohort was preserved as failed trial evidence and then cleaned; no grant was reset, retried or refunded. Success-path tests use separate new fictional databases, unchanged policies and supported fake inputs. This exercise does not prove two concurrent billable workflows will both succeed.

### Actual browser coverage and limits

The in-app browser exercised the actual loopback Next production build and independent FastAPI replicas at1280px: ordinary pending date, backend restart, deterministic answer, confirmed origin, three provisional itinerary cards, View Plan, local returned detail expansion, source discard/unlock, separate tabs, walking preference retention, refresh, unknown fake-provider refusal, scoped readiness, and Redis readiness outage/recovery. Pending answer preserved the synthetic inference count2 and charge13710; refresh preserved count6/charge204555/inference3; readiness outage/recovery preserved count2/charge13720/inference2 in a separate fictional cohort. Units are synthetic integer financial units, not actual provider dollars. The known groceries/optional-coffee fixture showed the accurate advanced/unsupported message and no generation control.

Different-user access, expiration, forged identities, financial exhaustion, stale revisions, protected payloads and all three store/witness outages are direct authenticated HTTP/process checks, not browser coverage. The local viewport capability accepted390×844 but existing/new tabs still reported1280px DOM width; mobile responsiveness is **not verified**. Waiting600s for UI expiry, full back/forward-cache behavior and successful simultaneous billable browser workflows were not verified. Controller tests cover expiry/late responses; recovery intentionally discards, never resumes. No source, handle, graph or cards are stored in browser storage. Temporary viewport overrides were reset. Desktop screenshots are local test evidence, not hosted staging results.

Dependency/base pins are unchanged. The current npm audit retains seven moderate development-tooling advisories, zero high/critical; no forced dependency upgrade or suppression was applied. Existing runtime-image findings and acceptance requirements in the [container security report](task52-container-security-remediation.md) remain applicable. Rebuilt-image smoke/content checks do not replace a fresh vulnerability-database scan or resolve prior residual advisories. No claim of clean hosted security is made.

The host-side Next test driver deliberately uses the local Docker daemon to reach isolated services and the fixed fake IdP. Docker control is administrative power over this disposable VM; the harness is **not** evidence of a least-privilege hosted frontend process. Role-specific application/service credentials and protocol denials are tested, but a malicious host administrator or compromised Docker-capable test driver remains outside the local isolation claim. A real frontend must use authenticated network clients and workload identity without Docker access or bootstrap-controller access. Do not deploy this driver.

Cleanup removed all disposable containers and task-named SQL/code volumes. Anonymous Docker volumes were preserved: aggregate inventory rose from97 to116, consistent with inherited Redis image `/data` volumes and the frozen parent's `rm -f` cleanup. There is no pre-task per-volume ID inventory proving which anonymous IDs are safe to delete; no broad prune was used. Redis tests disable persistence, but that is not a content inspection of unattributed volumes. A later local harness-cleanup change should inventory resources before creation and remove only proved task-owned anonymous volumes. This is not a cloud or application-data migration.

## Final verification

Exact new source manifest SHA256: `c48e7b24d950ea3c28f767f8b49e724238c2299b60b3c2b597e42a6fcfc8f3d5`.

| Final suite | Passed | Skipped |
|---|---:|---:|
| Ordinary clock / new UI authority / actual Next–FastAPI HTTP | 3 / 6 / 13 | 0 |
| Selected current backend modules, including recorded27 Qwen/seven OpenAI replays | 263 | 16 opt-in |
| Frontend, including11 new controller/presentation cases | 313 | 0 |
| Packaging / frozen proxy / strict public JSON | 15 / 3 / 2 | 0 |
| Hosted identity | 20 | 0 |
| Native reconstruction | 17 | 0 |
| Application grants | 30 | 0 |
| SQL / financial / action / encrypted evidence | 112 | 0 |
| Service isolation | 12 | 0 |
| Five independently spawned crash/admission-loss cohorts | 5 | 0 |
| **Total final automated cases** | **814** | **16** |

Final suites: zero failures, timeouts or interruptions. Earlier failed/incomplete development trials are retained separately in the machine record, not hidden or included as final passes. Native/grant SQL/witness snapshot-restore and restart drills also passed. TypeScript, ESLint, production build, Python compilation, pip consistency, source identities, local links, handbook preservation and diff checks passed. The existing bridge fork test emitted a Python3.12 multithreaded-fork deprecation warning; this is not a power-loss or hosted-distributed durability proof.

Both actual pinned amd64 images built and passed normal startup-refusal, health/proxy/mock-planning, unavailable-AI/missing-SQL, non-root/read-only/capability, diagnostics, shutdown/restart and stale-receipt smoke checks. The frontend's actual compiled identity artifact exports only `createGoogleIdentityPort`, pins jose6.2.17, has `launchable:false` and contains no experimental fixture directory. Images remain local; private production startup is not enabled.

The full backend discovery and33 historical source-identity headings were not rerun or repinned; no full-backend pass is claimed. Sixteen opt-in owner-database tests remain skipped. Mobile layout, real IAM/IAP/metadata/JWKS, hosted failover, real LLM/tokenization/Maps quality, fresh OS vulnerability-database rescan and Mac-off deployment acceptance remain unverified.

Read-only before/after verification preserved journal SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`, all ten rows/corrections and324 private files, original six pins, persistent halt, OpenAI7/Google2/Anthropic1, accounted$0.047366625 and remaining$11.952633375. Configured-secret scanning found zero current/assets/history matches. Handbook chapters3/4/6/7/12–15/18 and supporting references were updated; all20 originals and11 unaffected chapter files were preserved.
