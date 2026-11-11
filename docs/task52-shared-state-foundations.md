# Task 52 shared-state foundations — inactive local reference

Identity: `52-shared-authority-local-pg-v1`. Baseline: `ce4f3194d66083efedcf457f941547f4191ead89`. No application startup imports this implementation. No hosted adapter, migration, provider transport, public receipt or activation switch was added. Existing production refusal, legacy interpretation, Qwen, V5.1 development boundary, saved-plan schema/RLS and financial limits are unchanged.

## Current ownership and restart risks

| Actual component | Current state/lifetime | Shared-state requirement |
|---|---|---|
| `interpretation.PendingClarification` | Browser-carried effective interpretation, answers and reference clock; revalidated | Server-owned source/revision binding before authority; never relabel as raw model evidence |
| `advanced_planning.Sessions` | 50 process entries, 600s; source/Journey, contexts, resolver/router, candidates, history and receipts | Expiring private evidence plus durable revision/fence; callbacks, locks and live resolver objects cannot simply be serialized |
| `option_sessions.OptionSessions` | 50 entries, 600s; venues/routes, seen IDs, beam and outing counters | Shared expiring evidence; durable operation ownership and counters; preserve pagination history |
| `starting_areas.References` | 20 entries, 600s; suggestions/private geography, ownership uses Python session identity | Shared session-bound identifiers, not object identity; retain explicit reference selection |
| `starting_places._calendars` | Private coordinate/calendar cache, 600s | Volatile bounded cache; missing evidence must not invent timezone |
| `venue_details.DetailsSessions` | 50 entries, 1800s; allowed IDs, attempted IDs, original outing budget | Expiring session evidence and durable admitted-operation consumption |
| Advanced/ordinary route evidence | Context-held private venue/route evidence; live route lifetime 300s | Preserve original freshness; storage must not authorize stale route reuse |
| `saved_plans.Receipts` | 100 entries, 600s; minimized options and hashed access capability | Server-held selected-option membership; do not impose single-use semantics on every reusable selection receipt |
| Saved documents | Existing restricted PostgreSQL role/RLS, capability digests and expiry | Already durable; pure viewing does not need a new semantic receipt |
| `saved_refresh.RefreshSessions` | 512 process entries, 1800s; access digest + refresh ID; reopen/RLS/expiry rechecked | Durable replay/consumption across instances, preserve bounded outing accounting and existing pre-admission behavior |
| `planning_admission.AdmissionRegistry` | Explicit internal/test-only process registry, 50 entries/600s; random process HMAC, revisions, consumed handles | Only complete validation may issue future shared authority; advanced handoff and effective pending snapshots cannot issue fresh planning permission |
| `admission`, `provider_budget` | Process request/inference slots, dedupe, burst controls and outing/session/provider counters | Atomic fleet-wide limits; retain per-outing scope and original unit/window limits |
| `development_cost.DevelopmentCost` | fsync + local filesystem lock; local-calendar daily exposure, minute window and reserved/dispatched units | Durable transactionally serialized accounting; ephemeral instance files and local locks are insufficient |
| Signing/capabilities | Random process tokens/HMAC; saved links use hashed bearer capability | Approved stable key distribution/rotation plus durable consumption; a signature alone does not prevent replay |

A restart loses process evidence and replay sets. Overlapping workers can each believe a request or budget is unused. Revisions must invalidate old authority; fencing must reject old-worker completion after a new claim. Unknown sends must retain their entire charge and never become retryable merely because a process disappeared.

## Minimum architecture decision

Recommend **option A conditionally**: a separately isolated operational schema and least-privilege role in the existing Supabase PostgreSQL, plus approved volatile shared storage for private expiring evidence (Redis remains the existing proposed choice). Do not use the saved-plan role or anonymous/Data API grants. This recommendation does not approve a live schema, service or account change.

Both A and B (separate Cloud SQL + Redis) can support the same SQL row-lock, unique capability/operation, revision/fence and append-only accounting invariants. A is acceptable only after connection headroom, isolation, privacy, restore behavior and availability are reviewed. B separates operational load and failure scope but adds another database and cost. Redis eviction/loss may block an outing; it must never erase SQL reservations, consumption or uncertainty. Private text/location/provider payloads must not casually enter durable SQL backups. The local UNLOGGED evidence table is a **synthetic substitute**, not an approved Redis or real-data privacy implementation.

Published [Supabase pricing](https://supabase.com/pricing) lists Pro from $25/month; Free has a 500MB database and inactivity pausing. Current owner plan, usage and spare capacity are **unknown**. Published [compute limits](https://supabase.com/docs/guides/platform/compute-and-disk) for Nano/Micro include 60 database connections, 200 pool clients and default pool size 15; these are ceilings, not measured available connections. [Connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres) distinguish session pooling from transaction pooling and its prepared-statement limitations. Future hosted connections require approved TLS verification and pool sizing; neither is established here.

Earlier architecture estimates were about $150–350/month for regional HA Cloud SQL and about $47/month for Redis. The previously used Redis pricing URL now returns 404, so $47 is an **unrefreshed reference**, not a current quote. Using those assumptions only: A is roughly $72/month including a $25 Supabase floor; B roughly $222–422 including existing saved storage. Actual incremental A cost may differ if Pro already exists. These exclude application compute, traffic, secrets, monitoring, backups and taxes. [Cloud SQL pricing](https://cloud.google.com/sql/pricing) depends on region, CPU/RAM, HA, storage and network; no account estimate or provisioning occurred. Lower cost does not justify weaker authorization or accounting.

## Implemented boundary

`experiments/shared_state/contracts.py` reuses actual Pydantic DTOs for ordinary planner input, advanced handoff/results, pending effective state, ranked options and selected saved document. Canonical encoding includes private/excluded fields for integrity, stays within 64KiB, and never uses pickle. HMACs separate session, capability and evidence domains. Kind/version and all effective DTO fields bind each revision. A stored typed DTO is not proof of source correctness. There is no raw-model evidence kind, semantic issuer or substitute for the existing admission registry. Every reservation reports `planning_authorized=False`.

`postgres.py` explicitly accepts only the fictional loopback database/role and synthetic provider names. It has no environment selector, credential discovery or schema initializer. The harness injects temporary fictional credentials. All authority operations lock the same SQL gate, explicitly use READ COMMITTED, verify policy/key/limits and validate operation facts. READ COMMITTED ensures a worker that waited for the gate sees committed competing reservations in subsequent statements. [PostgreSQL row locking](https://www.postgresql.org/docs/17/explicit-locking.html) is the transaction primitive; there is no optimistic in-memory fallback.

Session expiry uses database time and remains fixed across revision changes. Claims advance fences; execution leases also belong to the issuing store instance/process. A restarted worker must claim again; stale worker objects cannot resume reservations. Revision changes/revocation invalidate prior capabilities. Evidence must still exist and pass integrity checks. Missing, expired, revoked or altered state refuses.

A reservation atomically consumes a unique capability and inserts a full integer charge plus RESERVED fact before returning. INTENT and terminal SUCCEEDED/FAILED/UNCERTAIN facts append; SQL uniqueness rejects replay and multiple terminal results. Failed and uncertain charges are retained. Claiming abandoned work marks it uncertain. Uncertainty blocks new operations at the configured concurrency limit; no automatic refund, resend, lease timeout reclaim or manual reconciliation tool exists. Missing facts fail closed. No transport is invoked by this module.

The local limits enforce fictional lifetime aggregate/provider charges and attempts, plus concurrency. They are **not** a completed mapping of existing minute/day/outing/provider-unit controls, calendar accounting or real financial authorization. Existing application budget checks remain unchanged. No new dollar ceiling was selected.

The schema rejects mutation/deletion of operation/fact/capability/policy anchors; the test worker cannot truncate them or create schema. The SQL principal remains trusted server code with INSERT privileges: arbitrary SQL under that principal could bypass protocol checks. Production requires reviewed execution-only stored procedures or equivalent constrained writer authority. This prototype is not a sandbox against malicious code running as the same OS/database principal.

## Verification and application compatibility

Run from the repository root, with the already approved dedicated Colima profile running:

```sh
backend/.venv/bin/python experiments/shared_state/run_local.py
```

The harness uses a digest-pinned PostgreSQL 17 image and the already verified Linux amd64 backend image. It creates only new synthetic database/container/volume resources, with no host ports or mounts and no external container networking. It copies authored test helpers into the temporary client, never changes an image or connects to owner storage, and removes its resources afterward. No new host dependencies or VM resource increase.

18 local PostgreSQL tests passed. They include two actual competing worker processes, cap races, financial limits, revisions, expiry/revocation, evidence tampering, wrong policy/key/host, immutable anchors, lock failure, missing facts, and process exits before commit/after reservation/intent/outcome. Actual PostgreSQL SIGKILL and worker restart retained logged INTENT/charge. UNLOGGED evidence disappeared, and the store refused continuation rather than reconstructing or resending. Database outage refused without fallback. Cold DTO imports were moved before the SQL lock after a real lock-timeout failure; timeout bounds were not relaxed.

Application compatibility tests use the **actual legacy interpreter** with fake inference, pending date clarification with no extra inference, ordinary planner/ranked options, advanced planner with synthetic Places/Routes, existing selected receipt and saved DTO. Source, optionality, named identity, date and destination tampering refuse. Advanced handoff/pending/browsing cannot reserve provider work, and preparation objects cannot act as existing admission receipts. These are typed roundtrip and existing planner tests, **not** hosted HTTP/session integration or a replacement serialization of live `Session` objects. No browser test or actual Supabase save/reopen was performed in this checkpoint.

Existing focused backend: 89 run, **73 passed / 16 opt-in skips**, zero failures. Frontend: **289 passed**. TypeScript, lint and all seven existing packaging checks passed. The first packaging run could not bind a loopback fake server under the sandbox; the unchanged tests passed with local-network permission. Full backend discovery, browser smoke and production build were not rerun because production/shared application sources and dependencies did not change. See [machine evidence](task52-shared-state-verification.json). Existing container vulnerability blockers are not resolved by this task.

## Remaining gates and stopping point

1. Owner chooses the operational backend after connection/load, privacy/retention, region, HA/RPO and cost review; no services or schemas provisioned here.
2. Review real issuer/consumer integration, session DTO decomposition and all ordinary/advanced/pending/options/refresh paths. Preserve the existing validation and selected-save ownership contracts; do not accept client DTOs as authority.
3. Approve volatile evidence storage, encryption/key lifecycle and retention; expiry alone is not deletion from SQL backups. Implement bounded cleanup without deleting replay/financial history prematurely.
4. Review constrained SQL writer permissions, pooling/TLS, complete budget-policy mapping, stable scope/epoch identities and authenticated issuer boundaries. No process-local random key may silently become fleet authority.
5. Specify conservative operator reconciliation for uncertainty and database backup restore. A restored database can lose recent consumption; remain disabled in a new epoch until reconciliation. Prototype tests do not establish backup-restore replay safety.
6. Test real hosted isolation, failover, network partitions and multi-instance application behavior separately. The global gate and history sums are a correctness reference, not a throughput claim; connection-per-operation is not a reviewed fleet pool.

SIGKILL/process tests prove local PostgreSQL crash recovery under this filesystem configuration, not power-loss, replicated failover or distributed exactly-once HTTP delivery. All new behavior stays inactive. Task 52 remains in progress; Task 53 has not begun.
