# Task 52 — inactive protected financial authority

Identity `52-financial-authority-local-pg-v3`; reused core identity `52-shared-authority-financial-core-v3`. Baseline `22267d124afab69ed271fc19e9428812c787d540`. New local synthetic PostgreSQL only. No application startup import, hosted adapter, live dispatch, provider credential discovery, real database migration or provisioning. All planning authorization remains false. [Machine/source/policy evidence](task52-financial-authority-verification.json).

## Audit: actual application policy, not a new allowance

Here, provider outing/session budgets are separate from the user’s activity-price or trip-time constraints; neither product constraint is changed.

The sources are `backend/admission.py`, `provider_budget.py`, `development_cost.py`, `provider_work.py`, `request_middleware.py`, `places.py`, `places_transport.py`, `starting_places.py`, `starting_areas.py`, `routes.py`, `routes_transport.py`, `search_fields.py`, `venue_details.py`, `saved_refresh.py`, `real_planning.py`, `advanced_planning.py`, `option_sessions.py` and `ai/ollama.py`/`ai/__init__.py`. Source hashes are recorded separately from historical evaluation identities.

**Important existing distinction:** ordinary bounded `ProviderBudget` has no `DevelopmentCost` object. Exploration constructs `DevelopmentCost(enforce_limit=False)`. It retains the durable usage ledger and shared minute limits, but **does not enforce a dollar ceiling**. `DevelopmentCost()` itself defaults to a $10/day hard limit and $10 warning, configurable independently to positive USD amounts with at most six decimals. That standalone enforcement must not be silently represented as active in normal or exploration planning. Existing exploration tests deliberately exceed $10. This checkpoint preserves all three configurations; it does not select one for hosting.

| Existing control | Scope / units / reset | Local SQL mapping |
|---|---|---|
| Requests per outing | 30 attempted HTTP requests, including failed/auth-unsent reservations; no time reset within outing | Immutable line count by issuer-bound outing |
| Search per outing | 10; includes starting-place/area lookup | Count search + lookup lines by outing |
| Contact/detail per outing | 6 Details attempts; remains bounded in exploration | Count details lines by outing |
| Matrix per outing | 300 full origin × destination elements | Sum approved matrix units by outing |
| Requests per provider session | 50; `ProviderBudget` is normally the process-global object, not a browser user | Persistent issuer-provisioned logical budget root; no reset on worker/session-object replacement |
| Matrix per provider session | 1,500 elements | Sum by budget root across all outings/evidence sessions |
| Lookup per provider session | 10; also consumes search and request counts | Lookup count by root |
| Provider concurrency | 1 active reservation/batch per ProviderBudget | Active/uncertain operations per root; no TTL refund or automatic release |
| Search / Details minute | 10 each, rolling 60 seconds per ProviderBudget | Per-root rolling sums; exact age 60 is excluded |
| Matrix minute | Default 150, configurable downward; rolling 60 seconds per ProviderBudget | Per-root unit sum with protected setting |
| Durable shared ledger minute | 10 searches, 10 Details, 150 elements across ledger users, regardless of session; only ledger-enabled paths | Additional all-root rolling sums for exploration/standalone ledger profiles |
| Daily estimated gross / warning | Host-local calendar date; USD millionths; gross includes all reserved work, not merely successful sends | Database-time date in an explicitly protected IANA timezone; nullable hard ceiling preserves disabled enforcement; warning only ledger profiles |
| Request dedupe | `(operation,request_id)` within original outing; rejected admission does not consume it | Unique `(outing,kind,request_digest)` on immutable admitted lines; capability and operation uniqueness also retained |
| Batch routing admission | All matrix requests/elements reserve atomically before auth/I/O; unsent batch suffix stays charged | Entire approved plan priced/checked/inserted in one transaction; partial failure retains every line |
| HTTP capacity/burst | `LocalAdmission`: 16 active reader/worker-owned requests; 240 admissions per rolling 10s | Separate SQL HTTP leases, persistent admitted-at timestamps and active references |
| Inference capacity/burst | 1 active local inference; independent 240/10s domain | Separate SQL inference admission domain; no AI money rate or model invocation |
| Bind/retain/release | Reader fingerprint replaced atomically; worker retains lease after HTTP completion/disconnect | SQL fingerprint uniqueness, same-worker ownership and references; release never refunds provider charges |
| Retries | Zero provider automatic retries; explicit pre-dispatch capacity wait may last up to 15s | No retry/resend/refund API; uncertainty persists. Existing wait/cancellation/transport behavior remains in application, not SQL |
| Exploration exceptions | Uncaps outing searches/requests/elements, session requests/elements/lookups and candidates; keeps Details/minute/concurrency constraints | Explicit immutable exploration profile skips only those corresponding quantity limits; no runtime toggle |
| Lower configurable limits | Pydantic allows lower quantities; env maps searches, requests, candidates, matrix outing/session/minute | Bootstrap validates source settings; SQL independently validates their exact keys/types/ranges; workers cannot change them |
| Candidate/route topology | 100 candidates/activity ordinarily; route frontier 20/group, ≤4 groups; matrix body ≤625 elements and ≤50 place-ID waypoints | Still application/issuer structural validation, not inferred from aggregate ledger units. SQL bounds plan cardinality to 64; unsupported plans refuse |
| Timeouts/body/privacy/RLS | 4,000 text chars; middleware 4KiB protected action / 64KiB other body, 5s body read; provider bounded timeouts; source/session/save ownership and expiry | Existing application remains authoritative. Financial SQL is not an alternate parser, body reader, route validator or saved-link authority |
| Cloud quotas/account billing | External quota/errors are distinct from local estimates | Unknown, not queried or claimed enforced by these estimates |
| Monthly/lifetime application dollars | No approved application-wide monthly/lifetime dollar ceiling found | None invented. The inherited core numeric test envelope is not an application allowance |
| Paid AI experiment | Separate immutable $12/594/198 and token limits with persistent halt | Deliberately excluded from application financial ledger; no journal clone, import, new allowance or dispatch |

The SQL profiles are `bounded` (quantity limits, no dollar hard cap/shared ledger minute), `exploration` (source exceptions, shared ledger minute, warning, no dollar hard cap), and `ledger_enforced` (bounded quantity controls combined with the existing standalone hard-cost guard). The last is a component-composition test profile, **not a claim that current startup enables it**. Tests use both the existing $10 default and an explicitly fictional $0.02 configuration accepted by the existing `daily_limit` parser. No new real ceiling or grant.

## Protected pricing and request ownership

The six checked-in `development_cost.RATES` values are copied exactly, in integer USD millionths:

| SKU | Per-unit micro-USD |
|---|---:|
| `search_pro` | 32,000 |
| `search_enterprise` | 35,000 |
| `details` | 20,000 |
| `details_pro` | 17,000 |
| `matrix_element` | 5,000 |
| `matrix_pro_element` | 10,000 |

Rate identity is `development_cost.RATES-2026-11-03-v1`. These are **the application's historical gross first-paid-tier estimates**, not newly verified Google prices, actual billing, net credit costs or purchasing advice. A later real staging readiness review must verify pricing/terms explicitly; this task sends no provider requests.

The runtime API is now `FinancialPostgres.reserve(lease, capability, operation_id)`. It accepts **no charge, provider, rate, units, outing, root, date or rate-version override**. Raw SQL with extra fields also refuses. A protected request plan must exist first:

1. Bootstrap installs immutable policy under a separate NOLOGIN owner.
2. A separate NOLOGIN issuer, unavailable to runtime, enrolls a server-owned evidence session into a persistent budget root and outing. Existing binding cannot be moved or reset. Revisions keep the binding.
3. The issuer approves a bounded, exact plan for a capability: request digest, operation, matrix dimensions and supported variant. It cannot supply prices. SQL derives lookup Pro, search Pro/Enterprise, Details Essentials/Pro, Walking Essentials/Driving Pro, and full matrix products. Unknown variants/providers refuse. `route/none` is the existing zero-charge accounting placeholder, **not authorization for a live free Routes call**.
4. At reservation, the database checks the plan against current source/evidence revision, capability and fence; prices every line from its protected policy; checks all relevant outing/root/window/day/concurrency limits; then calls the private core for atomic capability consumption and financial anchors.
5. Immutable lines bind operation ID, provider (`synthetic_maps`), request digest, root/outing, SKU, units, rate, rate version, policy version, accounting identity (`synthetic-local-project-v1`), currency, reserved time, timezone and calendar day. Integer/numeric intermediate bounds prevent multiplication/aggregation overflow before conversion to bigint.
6. INTENT precedes a single-use per-line dispatch fact. The approved ordinal cannot be skipped/repeated or sent after terminal failure. Full-success completion requires all planned dispatch facts. FAILED/UNCERTAIN may stop early; their entire reserved charge remains. No raw response, plan graph or journal is changed.

The issuer must ultimately be joined to existing validated server requests and the **exact canonical provider payload/field mask**. SQL cannot infer a real payload from a digest. A future transport must verify the payload digest/operation/SKU before I/O. A compromised issuer could approve the wrong category; SQL is not semantic certification or independent provider billing telemetry. No live issuer, egress bridge or provider permission is supplied here.

## Reused security and state boundaries

`financial_protocol` is the worker's **only** executable protected routine in the V3 fixture. The old core `protocol` and all helpers are private to the non-login owner; a raw call attempting the old arbitrary-charge path is permission-denied. No table, sequence, DDL, policy mutation, TEMP or owner/issuer membership is granted to runtime. Issuer can execute only enroll/approve routines, not change policy or financial history. Fixed search paths and qualified names remain; no runtime dynamic SQL. Schema/core/policy/front-door grants install in one atomic synthetic bootstrap transaction, with no temporary runtime access to the old core.

The core's gate, READ COMMITTED requirement, HMAC/DTO checks, protected evidence digest, expiry/revision/fence, capability uniqueness and append-only outcome logic are reused. No second planner or AI evaluator. Core source identity changed for a private database-clock dependency; old V2 artifacts/hashes/results remain preserved in Git and their reports, not relabeled as V3 evidence. The old 25 security tests run separately before the new profile. Their fixture does not grant access to any V3 database.

The new tables hold protected financial policy; roots/outings/bindings; request plans; immutable financial lines/dispatch facts; admission leases and a monotonic last-seen finance time. SQL uses a database clock, not a worker time/window argument or the connection's timezone. Backwards clock movement refuses. A private synthetic clock table supports deterministic rollover/DST tests; only bootstrap/admin can set it. Its NULL default uses real database time. No environment/HTTP clock override or production activation exists.

A reservation's day is fixed even if dispatch occurs after midnight. Day rollover never deletes history or lifts an unresolved operation's concurrency hold. New worker/evidence sessions cannot mint a new budget root, change an outing or reset per-root exposure. The test issuer deliberately provisions new scopes for legitimate synthetic actions; it is not a real operator or authority enrollment.

## Compatibility and limitations requiring decisions

- **Billing timezone:** current file ledger uses host-local time; no hosted project billing timezone was approved. The test policy explicitly uses `America/New_York`, including DST, without selecting a staging timezone. A hosted policy without a reviewed timezone/profile/root identity has no ready adapter or live execution path.
- **Budget session:** current ProviderBudget is process-global. A restartable fleet needs an approved persistent logical root and a controlled procedure for beginning a genuinely new reviewed session. Runtime cannot mint/reset roots here. No automatic per-user/day/root replacement was invented.
- **No hard dollars by default:** choosing a finite hosted allowance instead of the current standard/exploration behavior is an owner policy decision. The SQL can enforce the existing hard-cost component, but this checkpoint does not activate it for the app or borrow the AI experiment's budget.
- **Application issuers:** ordinary DTOs, actual interpretation/pending answers/options/selection, advanced synthetic planner/result/handoff, existing refresh/privacy/RLS tests and source-budget parity are exercised. No application-session integration was added. Advanced handoff/results and saved viewing remain non-provider authority; their proper provider-action issuers and refresh replay bridge still need implementation/review. Unsupported paths stay blocked in this reference.
- **Admission-to-work binding:** HTTP/inference leases and financial reservations are separate protected primitives. A financial reservation alone does not certify HTTP admission or authorize network work. The next server-owned bridge must bind the correct request/inference domain, retained lease and canonical payload to the provider operation; no transport can use this reference independently.
- **Untranslated controls:** candidate eligibility/topology, source-grounding, routing feasibility, cancellation, auth-before-send, response status classification, cookie/session ownership, saved-refresh registry (512 actions/1,800s), details/option/advanced retention and selected-save membership remain existing application controls. SQL financial enrollment cannot substitute for them; there is no transport path that bypasses them.
- **Existing numeric envelope:** the private reused core is initialized at its existing 10^12 integer ceiling and 16-operation envelope in the financial fixture. These are technical synthetic safety bounds, not a new USD grant or real aggregate spending policy. Real policies use the mapped line counts/cost/window limits; unusually large/custom operations beyond supported bounds refuse. No monthly cap was invented.
- **Recovery:** uncertainty blocks the original budget root, and crash-retained HTTP/inference leases remain active until a separately reviewed reconciliation procedure exists. SQL cannot prove whether an HTTP send occurred or whether a worker's reported success is true. Bootstrap/owner and fixture administrator remain privileged; a test process with synthetic admin credentials is not an OS isolation proof.
- **Hosted gaps:** no live migrations, PostgreSQL pool/TLS/role mapping, shared private evidence service, key lifecycle, restore-epoch/replay reconciliation, workload identity, hosted inference, or production security remediation. Local SIGKILL tests do not establish replicated failover, power-loss or backup-restore correctness. Gate/history scans are not a fleet latency benchmark.

## Verification and next concrete checkpoint

Use `backend/.venv/bin/python experiments/shared_state/run_local.py` from the repository root with the approved dedicated Colima profile. It runs existing core tests, the financial suite and actual database outage/SIGKILL recovery using new databases, synthetic issuer identities, fake request plans and no external networking/host mounts. Final results: **25 core + 31 financial PostgreSQL tests passed**, with zero failed/skipped/incomplete in those suites. Existing backend: **165 run, 149 passed / 16 opt-in hosted skips**, zero failures. Frontend: **289 passed**. Packaging: **7 passed**. TypeScript and lint passed. Detailed identities are in the machine report. No hosted test was enabled and no historical test excluded. Full backend discovery, production build and browser verification are not claimed for these experimental-only changes.

The broader existing backend regressions include actual ordinary/advanced interpretation/planning, provider budgets, persistent local cost guards, cancellation/admission, options, refresh, selected-save and privacy checks with fake services. An initial command named a nonexistent `backend.test_saved_refresh`; this was corrected to the actual existing suites and rerun, not treated as a passing test. Initial SQL CASE syntax errors were corrected before acceptance. Final diff review also found a NULL-command fall-through; an explicit command/object guard and malformed-input regression probes were added before the final rerun. All reservations still require approved plans and budget checks.

**Recommended next bounded checkpoint:** implement the server-owned issuer bridge for actual ordinary/advanced/options/refresh actions, linking existing validation, request revisions, outing lifetime and canonical provider payloads to these protected budget scopes and plans. Keep fake transports, actual shared-session evidence contracts and production refusal while verifying the same application workflows. This is a concrete prerequisite to private staging, not another general architecture redesign. Then perform the gated private-staging resource/security/capacity/pricing preflight before provisioning; any paid/recurring service still needs explicit cost approval. Public launch remains a separate owner approval after staging quality/security/reliability/latency/cost evidence. Do not start the next checkpoint automatically. Task 52 remains in progress; no Task 53.
