# Task 51 — request management and operations

November 5, 2026. Baseline: clean `main` at `5ea9ffd`. Scope: implement the local safety foundation and the cloud activation contract for original roadmap Task 51. Task 52 and later tasks remain unstarted. Paid hosting, managed shared state and cloud inference are required for launch, but none is selected, provisioned or deployed here. No daily legitimate-user itinerary allowance was added.

## Acceptance and audit

Acceptance requires bounded outstanding work and duplicate suppression; local inference backpressure; preserved provider reservation/dispatch semantics; sanitized errors and operational events; fail-closed production activation; unchanged cards, hard constraints and explicit recovery; offline concurrent tests, hosted persistence compatibility and rendered desktop/mobile checks. Actual distributed activation is explicitly outside this task.

| Lifecycle / owner | Existing control retained | Storage / limitation | Task 51 change |
| --- | --- | --- | --- |
| Browser submission | `PlanningSession`, AbortController, generation identity and stale-response rejection | One page; multiple tabs need backend protection | Server duplicate detection across tabs; interpretation proxy now forwards cancellation |
| Next.js proxy | Fixed upstream paths, no-store, server-only credentials, bounded upstream timeouts | Stateless; persistence/advanced bodies already bounded to 4096 bytes | New admission/error statuses survive proxy classification |
| Interpretation | Source validation, duplicate/unknown-field rejection, one unchanged Qwen extraction, 60-second default adapter timeout | Local Ollama; browser/proxy deadlines 75/70 seconds | One active inference, no waiting queue, safe busy rejection; 16 admitted HTTP readers/work owners leave capacity for health and other workers |
| Field clarifications / regeneration | Retained validated interpretation and explicit answers | No model call; current ordinary pending contract unchanged | Same request boundary and measurements; no repeated inference introduced |
| Ordinary initial planning | Shared `ProviderBudget`/`OutingBudget`, bounded discovery/shortlists, exact routing/timing | Process counters plus authorized exploration ledger | Bounded request readers/work and concurrent exact-body suppression before endpoint work |
| Named places / origin / nearby suggestions | Existing gated Text Search, manual confirmation, shared search admission | Private origin stays transient | Shared request control and safe error mapping |
| Advanced options / Different / discovery / beyond / mode edits | Server-owned opaque capability, nonblocking session lock, ten-minute expiry, same outing budget; finite assignment/pair/action bounds | 50 process-local sessions; restart or another worker loses continuation | Existing lock-busy codes map to temporary overload; current cards/history retained |
| Places discovery / contacts / saved hours | Shared search/details minute counters, minimal approved masks, no retries | Durable local ledger coordinates cooperating exploration processes on one filesystem; provider dispatch slot remains process-local | Add `details_pro`; Enterprise contacts/hours retain legacy `details` key |
| Matrix / travel mode | Atomic full-plan reservation, directed-pair deduplication, five-minute compatible route evidence, exact Drive/WALK policy | Full origins × destinations; Pro/Essentials share element window | Preserve both accounting keys; emit SKU-specific reservation and dispatch measurements |
| Save / reopen | Server receipt membership; independent capability; hashed 30-day RLS access; atomic five-table write; advisory-lock idempotency; four nonblocking DB connections; verified TLS | PostgreSQL durable; receipts (100 / ten minutes), refresh replay (512 / 30 minutes), connection semaphore and contact promises are local | Apply request admission; no SQL, RLS, grant, stored document or migration change |
| Diagnostics | Fixed error categories, opaque correlations, protected local diagnostics | Development-only; no public metrics endpoint | Allowlisted structured events, bounded metrics, admission/inference gauges |

Existing controls are layered, not interchangeable: reader/work admission protects backend resources; session locks protect continuation correctness; provider reservations protect shared usage; Cloud quotas remain external ceilings; PostgreSQL controls protect durable writes. None is a daily plan allowance. The authorized exploration daily cost warning remains nonblocking; no local provider ceiling or owner profile was reduced or raised.

## Admission and duplicate policy

`AdmissionStore` and `Lease` describe atomic request ownership, including reader-to-operation binding behind the lease interface rather than exposing local locks to middleware. The current `LocalAdmission` is explicitly process-local. The backend admits at most 16 outstanding readers/work owners and 240 accepted reads in a rolling ten-second interval, across protected operations, with no waiting queue. These are local operational defaults, not production sizing or per-person quotas. The existing single external-provider dispatch slot remains separate and unchanged. An initial inference occupies only one worker; saturated inference is rejected promptly rather than filling a model queue.

Bodies must arrive within five seconds; advanced/persistence bodies remain 4096 bytes, others are at most 65536 bytes. Streaming bounds apply regardless of Content-Length. Health and planning-mode reads do not enter this expensive-work allowance. An incomplete body cannot accumulate unlimited waiting jobs. Requests/metrics never use IP addresses, forwarded headers, account identifiers or caller-supplied session identities as trusted admission evidence.

A process-random HMAC key fingerprints path plus canonical JSON for concurrent duplicate suppression. Neither the body nor digest enters logs, metrics or disk. A digest is retained only while the operation owns a lease; body-reading slots initially use random keys. There is no response cache or successful-response replay containing capabilities. Two independent requests with exactly the same body can therefore collide intentionally as concurrent duplicates, even from independent people. After completion a fresh identical request is permitted. This tradeoff is appropriate for the local prototype; production should bind idempotency to a server-issued, authenticated anonymous context and operation identity under the shared atomic store. Do not trust a freely replaceable client key as an abuse boundary.

The final response byte releases HTTP ownership before delivery, avoiding a reproduced race with a legitimate immediate next action. A worker retains independent ownership until it actually finishes, including when its browser disconnects. Existing session work locks reject incompatible concurrent continuations even when their request bodies differ. Saved writes keep their independent durable idempotency: an uncertain write is reconciled using the same capability/selection, never an automatically minted replacement.

This is immediate admission, not a fair distributed scheduler or bot detector. Independent sessions can use free slots; a sustained distributed attacker can still exhaust a local process. Public ingress needs shared burst protection, request-size/read deadlines at the proxy/edge, nonidentifying risk signals, controlled authenticated anonymous contexts, and measured fairness/load tests in Task 52. Do not identify a household/campus as one user based on its IP.

## Cancellation and uncertainty

`run_work` propagates cancellation through a cooperative Event, retains the worker lease and retrieves eventual exceptions. The interpreter checks cancellation before transport and before creating an advanced session. Provider reservations and transport dispatch already check the same cancellation state. Cancellation before dispatch prevents further sends; cancellation after dispatch never refunds or automatically repeats reserved work. A synchronous HTTP call may finish after disconnect, bounded by its existing timeout. Its result is discarded or fails the next cooperative check; it does not authorize follow-on work. This does not prove that Ollama instantly stops internal computation, or that Google did not process an uncertain send.

Provider timeouts and lost responses remain conservatively accounted attempts. An in-progress duplicate receives 409; it is not confirmation that the earlier operation failed. Concurrent saves remain atomic/idempotent in PostgreSQL even after an uncertain commit. Browser Previous/Next uses tab history only. Explicit regeneration after expiry can reuse retained interpretation/answers as already supported; no automatic AI/billable retry was added.

## Google coordination and prices

Only the established `development_cost.py` ledger is used. Its owner-only locking, initialization, fsync-before-I/O, conservative reservations, immutable historical usage, shared rolling minute checks, and dispatch tracking remain authoritative. It is local durable accounting, not a deployment-wide cloud service or a second quota ledger. No Cloud quota, billing, credential, alert amount, API, field mask, identity or paid provider was changed.

Global first paid-tier estimates, independently checked November 5 against the [official price list](https://developers.google.com/maps/billing-and-pricing/pricing): Text Search Pro $0.032/search, Enterprise $0.035/search; Details Pro $0.017/request, Enterprise $0.020/request; Matrix Essentials $0.005/element, Pro $0.010/element. These gross estimates exclude allowance/volume/region/tax effects and are not verified posted billing or remaining free capacity.

Driving remains DRIVE + TRAFFIC_AWARE / Pro; Walking remains WALK / Essentials. No OPTIMAL, verification pass or extra Cartesian cells. Google documents [3,000 Matrix elements/minute and normal 625-element request bounds](https://developers.google.com/maps/documentation/routes/usage-and-billing); these published defaults are not this project's verified configured quotas. [Places quotas are per method/project and billing follows the highest selected field tier](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing). Existing documented development project settings (including 150 shared Matrix elements/minute and 10 search/details requests/minute) stay unchanged; this task did not reread or edit the Cloud console.

The audit found saved Pro refreshes were conservatively charged at the Enterprise rate. New Pro-only refreshes now reserve/dispatch `details_pro`; manual hours/contacts keep `details`. Old `details` entries are not relabeled or refunded. The additive key stays in ledger version 1, with the same integrity validation. Rolling Details capacity sums both tiers, and Matrix capacity sums both routing tiers. An older binary that does not recognize `details_pro` will fail ledger validation: preserve the ledger and include this reader compatibility on rollback; never delete/reset it to regain capacity.

Capacity planning: two ordinary activity searches at Enterprise plus 36 Drive elements estimate $0.43 gross before an origin/extra discovery/details. The current two-stop initial shortlist may add six origin elements; advanced initial work stays within its 27-pair allowance, with bounded selective continuation batches. Existing college coverage fixture uses 17 elements. A typical explicit discovery action adds at most two Places calls plus selected missing routes. Forecast aggregate EPM = outings/minute × measured mean elements/outing + exploration + saved-refresh demand. At 100 such 36-element outings/minute, 3,600 elements/minute already exceeds Google's published default; a quota increase is an explicit future operational decision, never an app promise. Coordinate all replicas and all credential users before enabling greater concurrency. Alerts and quotas do not guarantee a monthly spending ceiling.

## Events, metrics and privacy

The application emits JSON events for request start/end, admission/rejection, stage duration, provider reservation/dispatch, cancellation and classified failure. Failure paths cover interpretation, Places/Routes/quota, validation/session expiration, persistence, unavailable links and unexpected internal exceptions. Existing protected failure diagnostics additionally retain exception **type**, never its message/body. A generated 16-hex correlation ID flows through the request context, worker, failure body and X-Correlation-ID; inbound correlation headers are ignored. Proxies retain the opaque field in classified DTOs. Browser messages omit it.

Fields are event, fixed operation, fixed reason, optional random requestId, status, durationMs and SKU unit counts. Unknown reason strings collapse to `other`; unknown operation/event names are refused. Labels never contain raw request text, origins/coordinates/address, user contacts, provider payloads/bodies, SQL/exception messages, keys/passwords, capabilities, Place IDs, fingerprints or arbitrary URLs. No IP is collected. Request IDs are log correlation only, never metric labels or user identity.

Counters, fixed SKU totals and at most 1024 latency samples per operation remain in memory. Protected `/api/development-diagnostics` adds operation snapshots and current request/inference capacity, queued=0. Sample percentiles p50/p90/p95/p99 are nearest rank over the bounded recent sample, not fleet-wide service-level statistics. Existing provider timings, AI timings and active advanced-session diagnostics remain. Reservation and dispatch totals are distinct; derive gross estimates with the existing rate table/ledger, never treat counters as a posted invoice.

A bounded 1024-event asynchronous log queue prevents a slow stderr sink from blocking the planner or growing memory indefinitely. Saturation drops operational output and increments `droppedLogEvents`; counters still advance. Abrupt shutdown can lose queued events. The durable provider ledger remains the usage authority. The app does not create log files or a persistent location-history store. Local terminal capture is operator-owned: remove diagnostic captures within seven days. The required future hosted policy is seven-day operational-log retention, restricted staff access, no request/response/body/query/capability capture, and anonymized aggregate metrics only beyond that period. Task 52 must enforce this policy in the selected logging service; retention is not falsely claimed active on an unselected host.

| Signal | Implemented local evidence | Cloud alert / dependency |
| --- | --- | --- |
| Availability / error rate | Health; request outcomes by status/operation; failures by safe reason | Unhealthy instance >1 minute; >5% 5xx over 5 minutes with ≥20 requests; separate dependency outage from invalid input |
| Performance | Request, inference, admission and provider stage percentiles; existing advanced calculation timers | Set actual normal-flow SLO after cloud measurements; warn p95 budget exceeded for 5 minutes; inspect interpretation/search/Matrix/DB stages |
| Capacity | Active request/inference, rejects, queued=0; existing advanced session count, four-slot DB admission | >80% sustained worker/admission/session capacity; repeated busy responses; aggregate DB connections across replicas below pooler plan capacity |
| Shared state | Production startup refusal while dependencies absent | Alert immediately on shared state unavailability; no local fallback or unsafe replay |
| Cost / provider | SKU reserved/dispatched units + durable gross ledger; quota vs local admission | Warn at 70% and 90% verified minute capacity, any persistent quota refusal, or >2× recent normal unit rate; reconcile provider billing/alerts |
| Logging | Queue bound and dropped-event count | Any sustained dropped events; investigate sink without enabling body dumps |

These are actionable alert contracts, not provisioned external alerts. No paid observability platform, public metrics endpoint, collector or background polling job was added. Fleet RPS, healthy instance count, database connection utilization, fleet session count and stage SLOs need an authenticated infrastructure collector. An inference adapter can reuse the provider-independent gate/events and add bounded future AI usage units; no token/cost estimate is invented for the local model.

## Error and recovery contract

| Category | HTTP | Consumer behavior |
| --- | --- | --- |
| Concurrent duplicate | 409 | Already processing; wait, retain input/current page; no automatic replay |
| Short-window burst / local provider rate / actual provider quota | 429 | Brief temporary capacity explanation; existing preferences/cards kept; separate stable internal codes |
| Worker / inference / continuation capacity | 503 | Busy, explicit later Retry; no model/provider names |
| AI unavailable / timeout / invalid response | 503 | Existing distinct safe categories; request/preferences kept; explicit Retry/Edit |
| Provider service/authentication/invalid provider response | 503 | Service could not complete; no credentials or provider body |
| Body timeout / size | 408 / 413 | Short fixed input explanation; endpoint work not started |
| Input/unsupported/session answer problems | 422 | Specific supported field/expiry recovery, no hard constraint relaxed |
| Private link unavailable | 404 | Invalid/expired/unavailable together; no existence oracle |
| Database unavailable / uncertain transaction | 503 | Preserve itinerary; same selection for retry; no success claim or duplicate new write |
| Unexpected application failure | 500 | Fixed safe explanation and protected correlation |

Valid empty/partial results, missing visit evidence, known closure/Proceed anyway, impossible timing and unsupported requirements retain their established typed planning/clarification DTOs. They are not reclassified as overload. Existing role=status/live feedback, keyboard buttons, focus management, and per-page errors remain; no extra quota box or repeated card warning is introduced. Local operational admission is distinct from Google's real quota even though both have concise consumer copy.

## Production configuration and Task 52 activation

Current local startup commands and ignored owner profile are unchanged. Fresh clones stay mock, no startup Google traffic, no new dependency or environment secret. `WHERETO_ENV` accepts development/test/production; unknown values fail. At backend import **and** lifespan startup, production, NODE_ENV=production or recognized hosting environments refuse activation while the mandatory shared dependency bundle is unimplemented. There is no `shared_ready=true` flag that bypasses verification. Turning off lifespan cannot bypass the import guard.

Task 52 must supply and test:

1. A selected paid backend/AI platform independent of the owner's Mac, and production-only secret injection. Set WHERETO_ENV=production explicitly; host-name detection is an additional safeguard, not discovery of every possible host.
2. An atomic shared admission adapter with bounded leases, fencing/renewal/reconciliation, server-issued contexts, abuse resistance and fail-closed outage behavior. The current `AdmissionStore` is the interface; no shared implementation is active.
3. A shared provider reservation/dispatch/concurrency implementation behind the existing provider-budget ownership boundary. Reuse/migrate the established accounting semantics without a second uncoordinated ledger. The local filesystem ledger is insufficient across machines.
4. Shared expiring sessions/receipts/replay ownership, minimum necessary transient provider/private-origin data, encryption/TLS, access controls and automatic TTL deletion. Current session/receipt/contact stores cannot route across instances. A restart safely requires regeneration; committed PostgreSQL links survive.
5. Managed AI adapter behind existing AIProvider/source validation, shared bounded capacity, request deadlines and measured throughput. Preserve no-fabrication, model-free edits and zero automatic inference retries; evaluate accuracy/latency before switching.
6. Trusted reverse-proxy configuration and private backend ingress; strip caller forwarding metadata at the edge, authorize only known proxies and preserve CORS/private saved-link protections. Do not remove existing local-only endpoints just to make deployment work.
7. Database connection allocation per replica with fleet maximum below Supabase pooler capacity, runtime role/TLS/RLS verification, recovery/uncertain-commit tests, and alerts. No new pool or schema is needed locally.
8. Authenticated metrics collection, seven-day safe logs, quota/cost forecasting, load tests at gradually increased concurrency, and an explicitly approved quota change only if justified.

Target architecture: frontend CDN → managed load balancer → independently scaled FastAPI → shared ephemeral sessions/admission → managed inference + existing Google APIs → managed PostgreSQL. Frontend assets/proxies and pure calculations can scale independently; provider dispatch, model capacity and database connections have separate shared ceilings. Sessions and receipts need shared atomic mutation; saved documents need durable SQL. A failed shared dependency refuses work before billable dispatch. Sticky routing alone does not supply durable accounting or safe failover. Neither million-user concurrency nor five-second planning is established here.

## Verification record

Verification totals, timings, browser evidence, exact cleanup and remaining limitations are finalized in HANDOVER.md. All automated/browser Google evidence uses invented provider-shaped fixtures with actual sends blocked. Actual Google cost is zero. Hosted SQL and the explicitly identified installed-Qwen timing are real. No owner plan, release tag, Cloud profile or private development configuration is changed.

Reproduce from `/Users/rahularutla/Documents/whereto`:

```sh
npm run test:backend
npm test
npm run typecheck
npm run lint
npm run build
backend/.venv/bin/python -m pip check
npm audit --omit=dev
backend/.venv/bin/python -m unittest backend.test_request_management -v
backend/.venv/bin/python -m scripts.benchmark51
python3 scripts/security-scan.py
```

Hosted commands remain in database-security.md; use only the authorized development database and exact disposable cleanup. Benchmark51 uses invented fixtures and an in-memory log sink, excludes networking, and is not a production throughput or browser-latency benchmark.

### November 5 measured acceptance

- Final full backend: **973 reported / 936 passed / 37 opt-in skips**, **172.914 s**. The 37 include hosted and unchanged development-lifecycle opt-ins; hosted tests were exercised separately. Final frontend: **283/283**, **116.487 s**. Hosted selected schema/persistence/security/advanced suite: **71/71**, **35.045 s**. No full suite is counted as passing before its failures were fixed and rerun.
- Earlier runs exposed sandbox loopback restrictions, the immediate-next-request lease race, expected price/status/message changes and no other retained regression. Socket-constrained attempts are not successful HTTP verification. The response race is covered by the actual multi-request interpretation pipeline; concurrent ASGI and adapter tests prove single execution/ownership. Two historical cost assertions now expect 20 Pro Details = $0.34 instead of $0.40, and that plus ten Pro searches = $0.66 instead of $0.72. Local provider rate rejections now assert 429.
- Offline serial benchmark (one process, authored fixtures, no model/provider/SQL sends): 1,000 admission+HMAC samples p50 **0.0189 ms**, p95 **0.0209 ms**; 1,000 structured formatting/in-memory-sink samples **0.0070 / 0.0080 ms**; 1,000 process-local provider-admission samples **0.0369 / 0.0408 ms**. Thirty ordinary calculation samples **1.4613 / 2.1158 ms**, thirty model-free field clarifications **0.1810 / 0.2422 ms**, thirty advanced complete fixture computations **2.9172 / 3.1432 ms**. These measure local components, not total live planning latency or a controlled before/after speedup. Real disk fsync, network latency, host log collectors and multi-instance contention are excluded.
- Forty compatible advanced edit measurements: twenty duration edits p50 **1.4455 ms**, p95 **1.750 ms**; twenty scope edits p50 **1.452 ms**, p95 **1.739 ms**. No incremental model/search/Matrix calls. Local concurrency tests exercise a 16-way same-request race (one lease), independent free capacity, saturation, rolling recovery, and an occupied actual adapter gate; no uncontrolled load is sent to installed Qwen. One actual unchanged installed-model request took **28,447.593 ms** and preserved the authored ordinary activities/destination. One sample cannot establish an inference percentile, cold/warm comparison or five-second performance.
- Actual production-build browser checks: ordinary exact dinner/bowling request, synthetic busy → explicit Retry with original text → Surprise Me cards, details and Different; provider quota rejection during discovery preserves the same three cards/page. Advanced exact college → return clarification → confirmed synthetic public start → three college/coffee/return cards; 20/10-minute model-free visits yield **36 minutes** under the original inclusive **180-minute** cap. Different/discovery progress to three pages and nine distinct options. Previous/Next and expanding route details leave counters exactly **AI3 / searches9 / elements141 / details0** before/after history-only browsing (cumulative browser run, including busy attempts, ordinary work and manual lookup). All three leg links remain; no private start is transferred.
- Desktop **1280px** and mobile **390px** document widths match viewport widths. Browser checks verify clean consoles, role=status recovery, busy-state clearance, error focus, and Enter-operated plan details. Session expiry keeps all three viewed cards and requests regeneration. Exact later **option 2 / café 7** saves once, reopens in a fresh tab as one two-stop selection with return/180-minute cap/20+10 overrides, clears fragment capability, and loads two synthetic Pro details. Invalid invented capability has safe unavailable feedback and clears its fragment. Hosted tests separately cover legacy v1/v2 and idempotent/concurrent writes.
- The one browser-generated SQL record is verified by its exact generated hash and exact stored college/café 7 identities; only that record is deleted. Independent committed absence passes. Hosted suites similarly clean their generated disposable records. No owner records are mutated.
- Proof: `task51-ordinary-desktop.jpg` and `task51-saved-mobile.jpg` in `/Users/rahularutla/.codex/visualizations/2026/11/05/01a1aca1-9036-7a41-83f4-8280642aeb1d/`. The browser's viewport setting is per active test tab; final dimensions above were read from each rendered document, not assumed from an override call.

### Scenario coverage and explicit limits

The new `backend.test_request_management` tests cover concurrent ownership, independent admission, capacity, rolling bursts/resumption, 1,000 successive legitimate intervals, fingerprints, production refusal, actual adapter concurrency, conservative mixed-tier accounting, redacted logs/labels, streamed body bounds, concurrent tabs, caller cancellation and existing session-lock busy mapping. `lib/request-management.test.ts` verifies duplicate/busy/burst/provider statuses across interpretation/options/advanced proxies and cancellation with exactly one upstream attempt.

Existing full regressions supply normal/ordinary/advanced exploration, directional Matrix deduplication, cross-process durable reservations and restarts, provider minute/rate/quota errors, transport timeout/invalid response/no retries, model-free field edits/browsing, all hard timing/travel/return/closure examples, selected receipt membership, save idempotency, connection/uncertain-commit recovery, private links and v1/v2 compatibility. Browser evidence above distinguishes rendered verification from source inspection. No active shared store exists to test a real multi-machine outage or cross-instance session survival; the implemented acceptance is fail-closed production startup plus the adapter/activation contract. No fleet load, DDoS defense, public reverse-proxy configuration, live Google throughput/cost or managed AI performance is claimed. Previously accepted work may finish when its session expires; subsequent continuation admission refuses the expired capability. Shared TTL/fencing and restart reconciliation must be verified in Task 52.

Final proxy recovery regression also verifies that classified local-minute errors retain their recoverable continuation flags, while true quota errors retain stopped-search flags. The rebuilt 1280px/390px browser rerun preserved all three cards and disabled unavailable discovery after the quota error, with a role=status notice and clean console. The test-only environment typing issue caught by the build was corrected before the final successful build. Test tabs and owned 8050/3051 servers are closed; owner 8000/3000 services are untouched.

Final delivery checks pass: TypeScript, ESLint, production build, Python dependency consistency, zero-vulnerability production npm audit, complete tracked/new-file diff review, and the configured-secret scan across 1,425 current files/assets plus 2,411 historical objects (two configured sensitive values; zero current/historical matches). These checks do not prove absence of unknown retired credentials or third-party log exposure. The existing GitHub repository was independently reverified private; no release tag or visibility was changed.
