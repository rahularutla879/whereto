# Task 52A — paid cloud architecture evaluation

Research date: November 5, 2026. Baseline: `0337f4d031c2384dfcc28b0e88435aabc30ba42b`, clean `main`. **Recommendation only; Task 52 remains in progress.** No account, deployment, quota, billing, credential, database or model change is authorized by this document. Tasks 53–55 remain unstarted.

## Owner decision in plain language

Recommend Google Cloud Run for both the Next.js website and FastAPI backend, with Google’s managed HTTPS load balancer/CDN and Cloud Armor in front of the website. Keep the backend private. Evaluate **OpenAI GPT-4.1 mini** as the first cloud extraction candidate; **Gemini 3.8 Flash on Google's managed model platform (Vertex AI documentation now redirects to Gemini Enterprise Agent Platform)** is the credible alternative. Neither has been tested on this app. Pin an available model version only after accuracy, lifecycle, latency and privacy review.

Use **Memorystore for Redis Standard Tier** for short-lived planning state and **regional HA Cloud SQL PostgreSQL** for the authoritative operational reservation/dispatch ledger and fencing. Keep saved plans in the existing **Supabase PostgreSQL us-east-1** project, upgrading to paid Pro before real beta. A second PostgreSQL service is justified by durable provider safety and regional latency, not by moving existing owner data. It adds cost and operations; the simpler Supabase-only ledger alternative is evaluated below.

This separates temporary planning evidence, durable spending authority, and existing private saves. Redis failover must never restore spent Google/AI capacity. A successful next request can reach any backend replica without losing its valid session. Five-second recommendations remain a release target, not an established capability.

Acceptance for 52A: trace current ownership and blockers; compare official provider evidence; construct a reusable scenario corpus; rerun relevant offline safeguards; quantify assumptions/capacity/cost; prepare a testable 52B sequence and an explicit owner decision. Acceptance does not include deploying or proving cloud performance.

## What runs today: inspected request lifecycle

1. Browser uses `lib/planning-client.ts` / `lib/planning-timing.ts`; Next route handlers proxy to `BACKEND_URL`, default `127.0.0.1:8000`. The UI is the existing shared ordinary/advanced form, cards, preferences, history and save controls.
2. `app/api/interpret/route.ts` → FastAPI `backend/main.py` → `interpretation.py` → `ai.create_provider()` → `ai/ollama.py` → locally installed `qwen3:4b` at port 11434. Only Ollama is implemented. Parsing rejects duplicate keys/unknown fields; source/journey/travel/calendar validators establish a trusted partial or effective request. Missing data yields clarification, never a guessed provider search.
3. Ordinary generation: `app/api/plans/generate/route.ts` → `main.generate_plan()` → `real_planning.py`. Starting-location confirmation, destination/area, mode and geography are checked before `PlacesDiscovery`, normalization/relevance/hours filtering, selective directional `routes.py` evidence, feasibility/ranking and receipts. Location-first/sequential discovery and Surprise Me have their own confirmed-anchor paths; not every outing is the same Cartesian pipeline. Mock uses `ranking.py` and fictional fixtures.
4. Advanced generation: interpretation creates a `Session` in `advanced_planning.py`; `/api/plans/advanced` applies explicit answers/preferences under its lock, `stop_resolution.py` verifies named/brand/activity identities, `advanced_routing.py` selects bounded directed pairs, `advanced_timing.py` enforces dwell/return/whole-journey limits and `advanced_planning.py` selects cards. Closed-visit exceptions are scoped to verified occurrence/schedule/evidence. No global permission to ignore hours.
5. Different options can consume checked unseen combinations or selective route work. Explicit nearby discovery can add up to two supported searches plus missing route evidence. Previous/Next is browser history and makes no model/Google request. Compatible field-only edits and clarification reuse trusted interpretation/evidence, with no inference. Changed geography/mode/time may invalidate evidence and require new admitted work.
6. `saved_plans.py` receipts authorize only server-generated membership/selection. Next persistence proxy → restricted-role TLS PostgreSQL transaction. Existing five-table atomic inserts, capability-scoped advisory lock, immutable fingerprint/idempotency, forced RLS and uncertain-commit reconciliation remain. Version 2 saves only the selected advanced option; no precise origin or Google venue/route snapshot is retained. Reopening retrieves identifiers/app-owned constraints; selected Pro Details refresh is separately gated and replay-guarded. Optional contacts/manual hours remain Enterprise and explicit.

### Blocker, implementation owner and required regression evidence

| Current fact / blocker | Phase 52B owner and replacement | Required proof before activation |
| --- | --- | --- |
| Next/Python/Ollama run on owner Mac; no deployed target or container configuration | New reviewed infrastructure/container definitions; Node and Python Cloud Run services; local launchers untouched | Production image on staging works with Mac off; same ordinary/advanced browser acceptance |
| Only `AI_PROVIDER=ollama`; loopback URL, 60s synchronous adapter, one process-local inference lease | `backend/ai/__init__.py`, new cloud adapter; keep Ollama development branch | Same parse/source validation; timeouts/refusals/truncation; one send, no fallback/retry; cross-instance AI capacity |
| `ai_readiness.py` local optional warmup; `performance.py` Ollama timing fields; local smoke/evaluation scripts and `.env.example` assume Ollama | Separate cloud health/metrics path, no paid startup generation; preserve local tools/options/installation | Startup sends zero model/Google calls; readiness reports dependency capability rather than claiming a generated result |
| `admission.py` 16 readers/work owners, 240 reads/10s; process-random HMAC; identical independent bodies collide | Shared anonymous-context + operation identity; durable fenced leases, Redis admission accelerator | Same-body independent users proceed; simultaneous same operation executes once across replicas; saturation/release/cancellation/races |
| `advanced_planning.Session` owns source, clarification, answers, preferences, origin, resolver/router, inventories, seen/ranked sets, closure offers, receipts, ten-minute expiry and lock | Versioned shared DTO plus encrypted volatile evidence; no serialization of Python locks/budget objects | Initial request on A, answer/edit/Different/save on B; strict source/order/return/hours/privacy invariants; expiry and fencing |
| `option_sessions.py` ordinary context, 50 entries, timers/locks/600s | Same shared session abstraction | Ordinary options/discovery on another replica; no lost inventory or repeated dispatch |
| `starting_areas.py` reference confirmations; Details membership in `venue_details.py` (50, 30 min); mock Surprise Me option context | Shared reference/contact membership with original expiry and request binding | Reference substitution, changed origin/mode and contact membership rejected across instances |
| `saved_plans.Receipts` (100, 10 min); `saved_refresh.RefreshSessions` (512 replay metadata entries, 30 min) | Hashed capability membership/receipt DTO, atomic replay claims and durable dispatch IDs | Cross-instance selected-only save; forged receipt/token/ID rejected; concurrent refresh one owner; no response cache |
| `provider_budget.py` process/session/outing counters, concurrency one, in-memory seen/windows; `development_cost.py` fcntl/fsync local ledger | Existing reservation boundary gains one production SQL authority; local implementation stays for development | Cross-machine reservation races, mixed SKU minute/day limits, duplicate/uncertain dispatch, restart and outage fail closed |
| Supabase saves use one fresh connection/action, process `BoundedSemaphore(4)`; no application pool | `saved_plans.py` explicit fleet allocation plus small bounded Psycopg pool; separate operational SQL role/pool | Real restricted-role/TLS/RLS tests; same-token concurrent/uncertain commit; no connection held over Google/model I/O |
| `persistence-proxy.ts`, `development-origin.ts`, backend local middleware and persistence boundaries reject remote/forwarded requests | Explicit production trusted-origin/service-identity policy; retain development loopback branch | Forged Host/Origin/Forwarded/invoker rejected; authorized same-origin save works; raw backend inaccessible |
| Developer diagnostics and Server-Timing protected/local; memory-only aggregate metrics; no active alert collector | Private metrics/ops collector with seven-day safe application logs | No public debug routes; body/location/capability redaction; fleet metrics without identity labels |
| Ignored private files, local ADC impersonation/CA paths, local ledger path | Secret Manager mounts, attached workload identities, verified CA; environment-specific manifests | No credential copied from Mac/image/browser; invalid role/secret/TLS fails readiness |
| `admission.validate_environment()` refuses import and lifespan on hosted/prod environments; additional provider/advanced/persistence development gates | Verified dependency bundle and explicit production policies in each boundary, not a bypass flag | Missing admission/ledger/session/AI config, incompatible schema or unhealthy safety store prevents readiness/dispatch |
| Cancel reaches cooperative work Event but synchronous sends can outlive browser; body/worker ownership retained | Deadline propagation plus fenced dispatch ownership; conservative uncertain outcome | Kill worker after commit/before send, during send and after response; no automatic billable replay/refund |

The exact local startup commands remain `npm run dev:backend` and `npm run dev` from this repository. Production is not implemented by setting development flags. Historical Task 39 limits (e.g. 60 Matrix EPM) and later Task 51 notes (150 shared EPM) differ; the file ledger currently enforces **150 EPM**, search10/min, Details10/min. These are application limits, not a fresh authenticated quota verification. Latest recorded Cloud settings and current remaining use must be rechecked privately before any activation. No console quota was reread in 52A.

## Hosting comparison

All web research below uses official public pages checked November 5. List prices are USD, region/tier dependent, tax/discounts excluded. No account-specific capacity, remaining credits or signed SLA was verified. Service credits do not guarantee successful itineraries or end-to-end latency.

### Frontend

| Candidate | Latency, compatibility, scale | Reliability, privacy, recovery and operations | Commercial/cost finding and decision |
| --- | --- | --- | --- |
| Vercel Pro; Enterprise for contractual needs | Native Next deployment, edge assets; place Node proxy compute near API; API still traverses to Google Cloud | Easy previews/rollback; another processor and cross-cloud trust path. Do not make FastAPI public just for convenience; short-lived workload federation/invoker verification needs integration proof | Pro listed $20/month plus metered use; Enterprise custom with advertised 99.99% SLA. Strong alternative if preview workflow outweighs extra networking. [Pricing](https://vercel.com/pricing), [plans](https://vercel.com/docs/plans) |
| Cloudflare Workers Paid + OpenNext (Pages only for a truly static site) | Global assets; workerd/OpenNext compatibility differs from Node; existing API proxies preclude plain static export | Excellent edge controls, versions/rollback; private Google invoker federation needs proof; avoid another distant shared-state store | $5/month base; 10m requests and 30m CPU-ms included, then $0.30/m requests and $0.02/m CPU-ms on cited schedule. WAF/support/SLA products may add cost. Lower base price does not justify adapter/security migration now. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Next guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/) |
| **Google Cloud Run Node + external Application Load Balancer, Cloud CDN, Cloud Armor** | Same region as Python; full Node runtime, static hashed assets cacheable; dynamic planning/save routes always no-store | IAM service identity, common network/secret/log controls; revisions/traffic splits. More initial infra than Vercel; managed runtime does not maintain our app | Usage-based compute, ingress/CDN/Armor separately charged; minimum warm instances prevent routine scale-to-zero cold starts. Recommended for private backend integration. [Cloud Run pricing](https://cloud.google.com/run/pricing), [invoker auth](https://cloud.google.com/run/docs/authenticating/service-to-service) |
| Firebase App Hosting paid Blaze | Managed Next builds, Cloud Run/CDN integration; supported framework version must be verified | Less container control; defaults/logging/ingress still need review | Pay-as-you-go underlying services; not a fixed all-inclusive hosting subscription. Valid Google-compatible alternative; prefer direct Cloud Run for explicit network/identity control. [Costs](https://firebase.google.com/docs/app-hosting/costs) |

Installed Next deployment/self-hosting guides were read. Node/Docker supports the needed server features; static export does not. Cache only public immutable assets; do not cache request bodies, capabilities, private cards or provider evidence in CDN/Next caches. Multi-instance deployment identifiers, encryption keys if Server Actions are introduced, and cache invalidation need review; there is no reason to introduce new Server Actions here.

### Python backend

| Candidate configuration | Latency, scaling and recovery | Security/complexity/reliability | Cost and selection |
| --- | --- | --- | --- |
| **Cloud Run, us-east4, 1 vCPU/1 GiB, min 2/max 4 initially, concurrency 8, one Uvicorn worker/container** | Warm I/O workers, managed ingress, CPU/request-concurrency autoscaling; image revisions/gradual traffic rollback | Private IAM invoker; VPC access for SQL/Redis. Managed non-GPU SLA 99.95% subject to terms. Separate fleet provider admission remains mandatory | Instance-based illustration $0.000018/vCPU-s + $0.000002/GiB-s in published regional table; confirm us-east4 calculator before order. 730h at 1+1 ≈$52.56/instance before allowances. Chosen for coherent Google network/IAM. [Pricing](https://cloud.google.com/run/pricing), [concurrency](https://docs.cloud.google.com/run/docs/about-concurrency), [autoscaling](https://docs.cloud.google.com/run/docs/about-instance-autoscaling), [SLA](https://cloud.google.com/run/sla) |
| ECS/Fargate Linux x86, us-east-1, two 1vCPU/2GiB tasks across AZs + ALB | Predictable warm tasks; CPU/memory/custom scaling; deployment health/circuit breaking; good proximity to Supabase | Mature VPC/IAM; more ALB/NAT/task/rollout configuration. ECS/Fargate multi-AZ SLA conditions differ from single task | CPU+RAM seconds plus ALB/LCU/NAT/egress/logs. Public example rates yield roughly $36/task-month at 1vCPU/2GiB, excluding network; validate regional quote. Credible backend alternative, larger owner operations burden. [Pricing](https://aws.amazon.com/fargate/pricing/), [autoscaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html), [SLA](https://aws.amazon.com/ecs/sla/) |
| Render paid Pro workspace + two paid 1CPU-class services, East US region | Managed deploy/private services, manual/CPU-memory autoscale; documented ordinary paid service max 100 instances (larger types max 5), contact for more | Simple operations; cross-cloud Google/Redis if mixed with proposed stack; choose colocated Render state if selected. Contractual SLA/support must be quoted | Per-instance compute plus workspace, bandwidth and state. Current pricing page did not expose a complete machine rate table in retrieval; **exact paid machine/workspace price and SLA unresolved**, request quote instead of recycling older $25 Standard claims. Not first choice. [Pricing](https://render.com/pricing), [scale/limits](https://render.com/docs/scaling) |

Neither more replicas nor a 1,000-request Cloud Run concurrency ceiling creates AI tokens/minute or Google Matrix EPM. Start concurrency 8 because current code has blocking work and process-local assumptions; benchmark thread limits/event-loop responsiveness before increasing. The platform's default is not the application capacity plan.

## Shared state, durable authority and database

| Option | Latency/atomicity/recovery/privacy | Costs/operations | Decision |
| --- | --- | --- | --- |
| **Regional Memorystore Redis Standard** | Low regional RTT; atomic primary mutations; automatic failover, but acknowledged writes may be lost with asynchronous replication. No safety claim based solely on Redis locks | Provisioned GiB-hours; published M1 Standard reference $0.064/GiB-hour ≈$46.72/GiB-month; verify actual us-east4 quote. HA, TLS/private access; disable snapshots/exports for volatile evidence | Chosen for short sessions/admission acceleration, SQL fencing remains authoritative. [Pricing](https://cloud.google.com/memorystore/docs/redis/pricing), [HA](https://cloud.google.com/memorystore/docs/redis/high-availability), [SLA](https://cloud.google.com/memorystore/sla) |
| Upstash Redis regional/fixed/enterprise | Convenient serverless access; global/eventual consistency unsuitable as an assumed globally linearizable quota ledger. Primary scripting and failover contract require proof | PAYG/fixed plans/enterprise; HTTP commands and multi-region latency add costs; application data traverses another processor | Not authoritative safety store. [Pricing](https://upstash.com/pricing/redis), [consistency](https://upstash.com/docs/redis/features/consistency) |
| Redis Cloud managed subscription | Regional HA/cluster options, TLS and commercial support; exact consistency/durability depends purchased configuration | Quote memory, throughput, cloud/region and failover guarantees; plan-dependent Standard/Multi-AZ/Active-Active SLA offerings differ. [Pricing](https://redis.io/pricing/), [SLA](https://redis.io/legal/redis-cloud-service-level-agreement/); do not infer safety from Redis compatibility | Viable substitute if Memorystore volatile-data controls or capacity inadequate; no verified quote in 52A |
| Existing Supabase PostgreSQL for sessions AND accounting | Strong transactions/unique constraints/CAS, but cross-cloud RTT, hot minute counters and saved-plan contention; backups would retain session evidence | Lowest additional fixed services; needs separate schema/role and capacity. No production writes authorized | Credible simplified ledger alternative for staging, **never put Google/private ephemeral payloads in backed-up SQL**. Test RTT and lock contention before choosing |
| **Regional HA Cloud SQL PostgreSQL for operational metadata** | Regional transactions, durable ownership, reservation/outcome journal, failover. No location/Google response data in journal/backups | Additional database/pools/backup/monitoring, HA compute/storage pricing; planning allowance $150–350/month small regional configuration pending exact quote | Chosen to isolate regional safety traffic and avoid forcing owner-data migration. [Pricing](https://cloud.google.com/sql/docs/postgres/pricing) |
| Firestore transactions / Durable Objects | Firestore transactional documents possible; TTL cleanup is not an immediate authorization expiry. Hot global counters contend. Durable Objects serialize per object but place authority on another platform | Operation/storage charges; extra transaction/reconciliation implementation | Do not add these alongside SQL/Redis now. Future partitioned coordinator possible after profiling. [Firestore prices](https://cloud.google.com/firestore/pricing) |

Supabase is currently recorded as **Free, us-east-1**, not production Pro. Keep region/schema/data; Pro base $25/month includes compute credit, paid project compute and add-ons billed separately; daily backups and seven-day retention on published Pro offering. Recommend initially Small compute (published roughly $15 compute/month before the included $10 credit → about $30 total with $25 plan), subject to dashboard quote. Pro is not automatically an enterprise HA/SLA arrangement. Before public growth, decide required RPO/RTO, PITR and contractual availability; obtain Team/Enterprise/support quote if required. Do not promise HA by merely paying $25. [Pricing](https://supabase.com/pricing), [compute](https://supabase.com/docs/guides/platform/manage-your-usage/compute).

Keep session pooler/5432 initially because present role validation, TLS and transaction/advisory-lock behavior are tested there. Add pool max 2/backend replica for saved operations; four beta replicas →8 application clients, reserve maintenance headroom. Independent operational SQL pool max 2/replica →8 clients. Verify **both** project pooler client capacity and server connection allocation; neither is known from source. Pooler counts are not PostgreSQL `max_connections`. For larger fleet use transaction pooling only after proving SET LOCAL/RLS/advisory transaction locks/prepared-statement compatibility and resetting state on checkout. Runtime must never become administrator to simplify pooling. [Connection choices](https://supabase.com/docs/guides/database/connecting-to-postgres), [connection allocation](https://supabase.com/docs/guides/database/connection-management).

## Production shared-session contract (design, not implemented)

All stores use schema-versioned bounded JSON DTOs, never pickle/live Python objects. Absolute server timestamps replace process monotonic values in shared DTOs. Original source journey plus explicit accepted edits remain separate. Hold application-owned version/expiry/owner hashes in durable metadata where fencing is required; Google evidence and precise origins are confined to the encrypted volatile plane.

| State | Proposed contents / expiry / atomic transition |
| --- | --- |
| Anonymous request context | Server-issued random cookie, Secure/HttpOnly/SameSite; HMAC at rest. Not a login/account feature. Signed expiry and short-window abuse admission; no daily itinerary allowance |
| Advanced/ordinary/clarification sessions | Source extraction, accepted answers/preferences, bounded inventories, checked/unseen combinations and current page membership; ten-minute absolute expiry preserved, not extended on every edit |
| Transient evidence | Minimum source-bound provider facts/route observations/precise authorized origin needed for the same active computation, encrypted in volatile Redis with no snapshots/export/backup. Route evidence still expires at five minutes where current rules require; session TTL does not make stale traffic valid |
| Closed-venue permission | Occurrence + verified identity + schedule/configuration/evidence digest + opaque offer hash, explicit accepted override; any affected change invalidates it |
| Budget ownership | Session references immutable operation/reservation IDs. Never rehydrate an independent fresh `ProviderBudget` with replenished balances |
| Selection receipt | Minimized app-owned safe document and exact candidate membership, access verifier, ten-minute expiry; capability secrets never logged. Selection/idempotency rules unchanged |
| Contact/reference membership | Same confirmed IDs/request binding and existing 30-minute Details window or source-specific reference expiry; no cross-outing evidence cache |
| Refresh replay | Hash(context/capability/action/selection), 30-minute metadata expiry, atomic first-owner claim; no provider body retained |
| Continuation lock | SQL CAS owner + monotonically increasing fence/version + deadline; suggested renewable30s lease with 5s heartbeat, bounded by request deadline. Every commit checks fence and version |
| Admission/deduplication | Atomic claim keyed by context+server operation ID; bounded fleet capacity, inference units, burst windows; Redis can accelerate but no unsafe fallback or unlocked mutation |

SQL safety transaction claims continuation owner and fence; Redis CAS verifies payload generation/version; worker loads required data, computes, then publishes only with current SQL fence and matching Redis version. A lost payload, mismatched version or uncertain write refuses continuation without resetting balances. Crash between stores can reduce availability but cannot grant a second dispatch. No distributed transaction is pretended. Payload publication pointers/version sequence and compensation require explicit fault-injection tests in 52B.

**Important privacy blocker:** A short TTL is not permission to cache Google content. Review [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies), Routes terms and the actual agreement for distributed same-session processing. Place IDs can have different retention treatment from names/hours/routes. If remote volatile processing is not permitted or the service cannot exclude snapshots/retained evidence, activation is blocked until an approved design exists. Do not copy whole Google responses into Redis/SQL/logs, or secretly re-fetch on each replica hop. Redis must use a non-evicting policy for active session state, explicit memory admission and encryption keys with bounded lifetime; expiry deletion plus key destruction covers expired sensitive payloads. Backups contain only permitted app-owned identifiers/metadata. Location data must never appear in key names, metrics or journals.

Replica changes preserve sessions; region/store failure can still invalidate volatile sessions safely. That is disclosed recovery, not uninterrupted disaster recovery. Receipts issued before a failure are not silently recreated with more provider authority. Saved links survive independently in Supabase.

## One distributed Google accounting authority

Replace production file-ledger operations behind `ProviderBudget`/`OutingBudget` with SQL transactions, keeping the development ledger untouched. All production callers, including searches, manual starts, advanced resolution, routes, contact/hours and saved refresh, use **one** journal/limits authority. AI accounting uses a separate provider namespace in the same coordinator, not Google counters.

1. Reservation transaction checks project/method rolling-minute units, configured daily project accounting, SKU field-mask/transport tier, session/outing limits, fleet concurrency and duplicate operation ID. Serialize a project/method window row or use serializable transactions with bounded conflict handling **before any external dispatch**. Reserve the entire required batch or refuse; provider I/O never occurs under a database lock.
2. Commit immutable reservation ID, unit count, integer micro-USD rate version, quota timezone/reset boundary, expiry and owner fence. Explicitly mark local historical day basis separately; production project daily reset must follow the verified provider quota boundary (not host timezone). No daily per-person cap.
3. Before socket send, atomically mark dispatch intent under the same owner/fence and uniqueness constraint; transport verifies it. The mark means “may have been sent”, not confirmed billing. Crash after mark/before send retains conservative charge. A stale worker cannot obtain dispatch permission after ownership loss. An already dispatched uncertain operation is never assigned a new sender.
4. Record outcome or uncertain-send classification; retain reservation even on timeout, cancellation, malformed response, partial Matrix stream, worker death or unsent remainder of an admitted batch, preserving current conservative semantics. **No automatic billable retries.** Metadata-only DB retry before any dispatch may be separately bounded; uncertain reservation commit must be read by the same ID before proceeding.
5. SQL durable leases/fences own dispatch; Redis counters are advisory mirrors. On Redis loss rebuild from SQL or stop, never zero budgets. On SQL outage stop all new paid dispatch. Restoring SQL from backup requires a new disabled epoch, reconciliation of uncertain/out-of-backup dispatch and explicit operator resume, not an empty-ledger restart.
6. Keep reserved/dispatched/provider-billed figures distinct; reconcile aggregate billing asynchronously without pretending an estimate is an invoice. No raw credential, user prompt, origin or Google content in journal. Retain minimal reconciliation records for an approved bounded period (proposal 90 days); operational logs7 days. Owner must approve this metadata policy; it is not a raw location history.

Routes DRIVE+TRAFFIC_AWARE → Pro; WALK → Essentials. Details minimal saved mask → Pro; hours/contacts → Enterprise. Places highest requested field decides tier. Separate SKU costs, shared method windows. [Fields](https://developers.google.com/maps/documentation/places/web-service/data-fields), [Routes limits](https://developers.google.com/maps/documentation/routes/usage-and-billing), [Places limits](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing).

Current local concurrency 1 and small development limits are not a production capacity policy. 52B must replace production values with separately approved, verified fleet capacity; preserve local values. No second ledger, project proliferation or credential sharding to evade Google limits. Partition internal session/ledger storage by tenant/project/time only when authorized projects/contracts justify it. Google capacity increases or multi-project agreements require official approval, not rotating keys to multiply a quota.

## Capacity forecast and incremental load plan

Definitions: registered users = total accounts if accounts are later implemented (none today); MAU/DAU = distinct active users/month/day; connected browsers = tabs/network clients, mostly idle; active generators = in-flight interpretation/planning operations; RPS = admitted operations/second. None is interchangeable. One million registered users could mean modest RPS; one million simultaneous generators is entirely untested.

Illustrative **assumed** outing distribution, used for capacity and costs (not measured production traffic):

| Type | Share | Enterprise search calls | Pro Details | Matrix elements | Commentary |
| --- | ---: | ---: | ---: | ---: | --- |
| Ordinary two activities | 60% | 2 | 0 | 36 | Current width6 adjacent pools; origin6 extra excluded from this base example |
| Advanced initial + some explicit continuation | 30% | 3 | 0 | 27 | Initial27 allowance; some outings need less (recorded college17), later actions can add batches |
| More exploratory session | 10% | 5 | 0 | 54 | Assumed initial3 + explicit discovery2, two selective27 batches |
| Saved reopen demand (additional) | — | 0 | average0.4/outing | 0 | Assumed20% open a two-stop link with automatic Pro refresh approved |

Weighted means **2.6 searches, 35.1 Matrix elements, 0.4 Details/outing**. Assume80% driving/20% walking → gross routing $0.009/element. Search $0.035 and Details $0.017 → Google **$0.4137/outing** before free tiers/volume discounts. Add origin6 Drive elements = $0.06 when required; named mall relationships may need extra searches; four selected Details = $0.068 Pro or $0.08 Enterprise. Text Search pagination costs another search; Matrix rectangular cells count even if some are unused. Continuation counts are not fixed maximum total session bills.

Published Google Matrix default 3,000 EPM is only about **85.5 outings/minute ≈1.42 RPS** at 35.1 elements/outing, before safety headroom/other consumers. Current local 150 EPM is ≈4.27 outings/minute. Search10/min is ≈3.85 outings/minute. Neither supports a public product without an explicitly approved operational capacity change. Last documented daily development ceilings also obstruct sustained beta; remaining configured quotas unknown. Rate-limit headroom, provider concurrency, Matrix request bounds and verified per-project quotas all matter.

Assuming steady five-second service and **no think time** (a deliberately demanding load), concurrency C implies C/5 RPS. A realistic model with 20 seconds of think time gives C/25 RPS; test both, using open arrival rate as well as closed users to avoid coordinated omission.

| Active planning users C | Demanding RPS | Search QPM at 2.6/outing | Matrix EPM at 35.1/outing | Initial backend sizing hypothesis at 8 in-flight/replica |
| --- | ---: | ---: | ---: | --- |
| 10 | 2 | 312 | 4,212 | 2 replicas; already above published default Matrix capacity |
| 50 | 10 | 1,560 | 21,060 | 7+ replicas; AI quotas and Google approval first |
| 100 | 20 | 3,120 | 42,120 | 13+ replicas; SQL hot rows/pools and Redis bytes profile |
| 500 | 100 | 15,600 | 210,600 | 63+; negotiated provider capacity, partition coordinator safely |
| 1,000 | 200 | 31,200 | 421,200 | 125+; substantial contracts, load evidence and budget required |

These are arithmetic requirements, not capacity promises. Replica figures exclude headroom, mixed request types and CPU saturation. Initial beta max 4 does not authorize these fleets. For each rung run no-egress synthetic I/O first (10min warmup +30min steady +burst/cancellation/failure); verify fairness, p50/p90/p95/max, success rate, backlog, event loop, per-stage calls, payload bytes, SQL locks/connections, Redis memory and ledger invariants. Then request a separate tightly bounded live canary allowance; do not run a30-minute paid stress test implicitly. Progress only if previous rung passes and contracted quotas/budgets cover it. Larger rungs require a new reviewed plan.

Session memory assumption for sizing only: mean 256KiB serialized encrypted session, cap 1MiB, no measured current histogram. 1,000 sessions≈250MiB payload, budget 3× for keys/replication/allocator≈750MiB; 10,000≈7.5GiB provisioned. Differentiate active requests from ten-minute retained sessions: Little's Law at 2 session starts/s ×600s≈1,200 retained sessions. Measure actual DTO distribution before choosing capacity; new sessions may be temporarily refused when memory full, not evict valid accepted sessions. Response target p95≤100KiB, hard≤512KiB proposed, to be checked against existing card/receipt shapes before enforcement. No arbitrary payload truncation.

Bottlenecks: model RPM/TPM and tail latency first; Google EPM/QPM/cost next; blocking Python/thread and CPU work; SQL global-window contention and connections; Redis serialization/memory; cross-cloud Supabase RTT on saves; mobile response transfer. Scale through approved model throughput, bounded parallel independent searches, selective routing, more workers/replicas, larger Redis, SQL partitioned windows/range reservations with no over-allocation, and pool/compute upgrades. No change may relax correctness or add hidden provider searches.

## Cost scenarios: illustrative budgets, not quotes

30-day month for activity,730h for always-on compute. One AI extraction/new outing; clarifications/compatible edits remain model-free. AI token allowance8,000 input +1,200 output (assumption, not tokenizer measurement) at GPT-4.1 mini $0.40/$1.60 per million → **$0.00512/outing**. No cache discounts assumed. Google distribution above; gross first-tier rates intentionally ignore volume discounts/free allowances. B/C need negotiated quote; these are conservative list-rate planning envelopes, not precise bills.

| Activity assumption | A: private staging/early beta | B: growing public product | C: high growth |
| --- | ---: | ---: | ---: |
| DAU; outings/user/day | 50;1 | 5,000;1 | 100,000;1 |
| New outings/month | 1,500 | 150,000 | 3,000,000 |
| Mean outing RPS over 24h | 0.017 | 1.74 | 34.72 |
| Assumed10× peak RPS | 0.17 | 17.4 | 347.2 |
| Searches/month | 3,900 | 390,000 | 7,800,000 |
| Matrix elements/month | 52,650 | 5,265,000 | 105,300,000 |
| Pro Details/month | 600 | 60,000 | 1,200,000 |

A's throughput trial should begin lower than 10 continuously generating users until quotas verified. B's mean alone exceeds default Matrix capacity, C's peak exceeds the1,000-active-user table. Daily users are not concurrent users. Real peaks and think times are unknown.

| Monthly component | A USD | B USD | C USD | Fixed vs usage / basis |
| --- | ---: | ---: | ---: | --- |
| Frontend Cloud Run | 55–110 | 150–600 | 1,000–5,000 | Warm minimum plus scale; measured CPU absent |
| Python Cloud Run | 105–210 | 300–1,500 | 2,000–12,000 | Two warm 1vCPU/1GiB baseline; usage/headroom grows |
| LB/CDN/Armor | 40–120 | 100–500 | 500–4,000 | Rules/policies/requests/forwarding/data, calculator pending |
| AI | 7.68 | 768 | 15,360 | Usage; no retries; tokens assumed |
| Redis Standard | 47–140 | 200–700 | 1,000–5,000 | Provisioned fixed capacity, region-dependent |
| Operational HA PostgreSQL | 150–350 | 350–1,500 | 2,000–10,000 | Fixed compute + storage/backup; exact configuration quote pending |
| Supabase saved plans | 30–100 | 100–600 | 1,000–5,000 | Paid plan/compute, PITR/SLA/support extra as quoted |
| Places Search | 136.50 | 13,650 | 273,000 | Gross2.6 Enterprise/outing; volume/free not applied |
| Places Details | 10.20 | 1,020 | 20,400 | Gross0.4 Pro/outing; explicit Enterprise extra |
| Routes | 473.85 | 47,385 | 947,700 | Gross35.1 × blended$0.009/outing |
| Logging/monitoring | 10–50 | 50–300 | 300–2,000 | Ingest/metrics/alerts and seven-day storage, not unlimited |
| Network transfer/NAT/DNS/secrets/build/artifact storage | 20–80 | 100–600 | 500–5,000 | Separate from compute/CDN; estimate traffic before order |
| **Total infrastructure/provider envelope** | **1,100–1,800** | **64,200–69,200** | **1.265m–1.305m** | Rounded arithmetic; no tax/support/labor/contracts |
| Operator time (assumed) | 4–8h/month | 16–40h | 80–160h | Budget separately; at assumed$100/h add$400–800/$1,600–4,000/$8,000–16,000 |

Fixed infrastructure before AI/Google is roughly$457–1,160 A, $1,350–6,300 B, $8,300–48,000 C. Hosting is not the dominant high-volume bill in this distribution. Contracted volume pricing could materially lower Google spend, while origin/detail/exploration usage could raise it. Reconcile provider usage before treating any envelope as an approved spend ceiling. Alerts are not hard caps. Do not promise unlimited throughput or free usage based on monthly allowances.

## Security, privacy and operations

Frontend: managed TLS at load balancer, exact production host/origin allowlist, CSRF/same-site controls and body/read limits. Edge strips caller-supplied forwarding/service metadata; only trusted proxy hops reconstruct scheme/host. Cloud Armor risk/burst controls, bounded anonymous contexts and per-context simultaneous work limit (proposal one active costly generation/context) protect capacity without counting daily outings. Shared NAT/campus IP is a risk signal, not user identity or daily quota. DDoS mitigation is layered; optional challenge only for suspicious traffic and never a hidden requirement to create an account.

Backend: no unauthenticated invoker, no direct public API bypass. Use attached Next service identity and short-lived audience-bound ID token, internal ingress plus configured VPC path. Firewall/egress restrict SQL/Redis; only Python gets Google/AI secrets. Attached backend identity gets only approved Google service-use permissions; do not copy local ADC source refresh credentials to cloud. Separate staging/prod projects, service accounts, stores, quotas and secrets. Runtime identities have no migration/billing/admin rights; CI deployer uses short-lived federation and approval for infrastructure changes.

Saved links keep fragment tokens, body-only POST, SHA-256 verifier, no-store/no-referrer and30-day expiry, restricted runtime role, verified TLS, forced RLS and selected-only retention. No Google content/precise origin migrates to permanent saves. Browser capabilities remain bearer access; accounts/revocation are not silently introduced in Task 52.

Logs: create a dedicated seven-day application operational bucket; exclude request bodies, arbitrary URLs/query strings, IP/user-agent and capability/Place ID/location data from application/access/tracing sinks. Verify platform-generated LB/Run access logs and error collectors too; redaction in Python alone is insufficient. Where platform security/audit records have mandatory longer retention, document them separately and keep them free of user payloads; do not falsely promise every provider deletes all records in seven days. Metrics use fixed operation/status/SKU labels and aggregate histograms. No prompt recording for debugging; dropped logs alarm. [Logging configuration](https://cloud.google.com/logging/docs/buckets).

Cloud inference changes the current local-only processing disclosure: outing text can contain exact venues, dates, home addresses and sensitive errands. Before use name subprocessors, purpose, regions, retention/training exceptions and deletion/access process; obtain owner acceptance of DPA and processing region. Send only text needed for extraction, no capability, DB secret, precise device coordinate or provider response. Text can itself include an address; do not claim redaction removes all private data without a proven semantics-preserving method. No private owner request was sent in 52A.

Recovery targets proposed, not guarantees: saved-plan RPO≤24h on daily backups, improve to≤5min with approved PITR; RTO≤4h after restore drill. Operational ledger HA target no loss of acknowledged reservations on ordinary failover; regional disaster must reconcile uncertain sends before resume, regardless of backup age. Session cache may be lost on disaster; retain browser cards and explicit regeneration without invented restored evidence. Canary1%→10%→50%→100%, two compatible DTO versions during rollout, rollback to last compatible image/config and additive SQL schema. Rehearse restore privately, never on owner data. No automatic multi-region active-active spending ledger at launch.

## Weighted decision matrix

Scores1–5 are engineering judgments, **not measured model rankings**. Weights sum 100; weighted total=sum(weight×score)/5. Correctness/privacy are hard gates regardless of total. AI score 3 for every untested candidate avoids inventing accuracy differences.

| Criterion / weight | Google runtime + OpenAI + Redis/SQL + Supabase | Same stack + managed Gemini | Vercel + ECS + OpenAI + AWS state + Supabase | Cloudflare + Render + open model + managed state |
| --- | ---: | ---: | ---: | ---: |
| Correctness /25 | 3 | 3 | 3 | 3 |
| Latency potential /20 | 4 | 4 | 3 | 3 |
| Scale /15 | 5 | 5 | 5 | 4 |
| Reliability /10 | 4 | 4 | 4 | 3 |
| Security/privacy /10 | 4 | 5 | 4 | 3 |
| Operating simplicity /8 | 4 | 4 | 2 | 3 |
| Migration /7 | 4 | 3 | 3 | 2 |
| Cost /5 | 3 | 3 | 3 | 4 |
| **Weighted total /100** | **77.0** | **77.6** | **68.4** | **62.6** |

Gemini's slight judgment lead reflects integrated IAM/privacy controls, not proven extraction superiority or regional availability. Recommendation is **Google hosting/state**, with OpenAI as first baseline-compatible model experiment and Gemini as an equal serious challenger. Do not treat a 0.6-point subjective difference as a procurement decision. Select the final model only on matched semantic/latency/privacy evidence; if Gemini meets gates and regional capacity is confirmed it can replace OpenAI without changing planner logic. Vercel+ECS is credible but adds orchestration/trust hops; Cloudflare/Render add adapter/provider migration without evidence of a faster complete itinerary. Dedicated GPU remains a later option for demonstrated sustained throughput needs, not an assumed route to five seconds.

## Owner checkpoint

Review the [AI evidence/proposal](task52-ai-performance-evaluation.md) and [implementation sequence/approval packages](task52-production-implementation-plan.md). Approve or revise hosting/state/database approach, AI benchmark data terms/allowance, region, private-staging recurring envelope and provider quotas separately. No billable order or Phase 52B implementation has occurred. Remaining uncertainties: real model accuracy/tail latency, model version/lifecycle/region availability, account throughput, ephemeral Google-data terms, actual session sizes, exact regional infrastructure quote, Supabase connection allocation/HA requirements and current Google quotas. Task 52 cannot be complete until these are resolved and the owner approves52B.
