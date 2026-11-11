# Task 52 — cloud staging packaging checkpoint

Later checkpoint: [actual local container verification](task52-local-container-verification.md) now resolves the engine/build uncertainty recorded below. Original packaging measurements and cost assumptions remain historical evidence; unresolved security and hosted-activation gates remain open.

Baseline: clean `e7937e4ab1c2734a6576137dd4233fdaca8966c5`. This checkpoint prepares build artifacts and tests their assembled payloads. It does **not** deploy a working cloud application. Task 52 remains open; Task 53 is unstarted. No provider calls, purchases, provisioning, migrations or changes to the paid experiment are authorized.

## Implemented artifacts

`next.config.ts` now emits Next.js standalone output. `deployment/Dockerfile.frontend` uses `npm ci`, the existing lockfile and the standalone server/static files. `deployment/Dockerfile.backend` uses CPython 3.12, a Linux amd64 wheel hash lock preserving the existing requirements, and an explicit application import-file manifest. Both use digest-pinned official base images and non-root runtime users. The checked-in public image metadata identities are in `deployment/base-images.json`; refreshing them is a separate reviewed dependency change. These are repeatable build inputs, not proof of byte-identical builds: Next generates build identities. Build once and promote the resulting immutable image digest.

The default-deny `.dockerignore` excludes Git, environment files, credentials, private evidence, scripts and handbook. Backend assembly copies only reviewed runtime files and mock venue data; evaluation runners, V5.1 local fixtures, test clocks, database administration/migration tools and model weights are absent. Existing runtime shadow wrapper code remains present because interpretation imports it; its observer stays OFF and its offline scripts are not packaged. The active parser, prompt, legacy normalizer, source-grounding, HITEC correction, schemas and planner are unchanged.

The launchers validate ports and configuration without echoing values, reject development integrations, and do not load credentials or create a cloud/model fallback. Backend defaults to production and therefore **refuses startup** under the existing `admission.validate_environment` guard. That is intentional, including when Cloud Run supplies `K_SERVICE`. Setting the environment to test cannot bypass a hosted indicator. Local isolated tests alone use test mode and a loopback fake unavailable AI service. See [environment and secret contract](../deployment/environment-contract.md).

Cloud Run YAML files are incomplete review templates with placeholder identifiers, private ingress, min instances zero, max one and concurrency one. They grant no IAM access and cannot make this backend deployable. Required identity-token networking, state services, secret/CA mounts and inference remain absent. Never render/apply them as a shortcut around the startup refusal.

## Existing components and actual blockers

| Component | Verified current implementation | Requirement before functional staging |
|---|---|---|
| Frontend | Production build, standalone Node server, server-side API proxies | Authenticated private backend invocation; proxies currently have no Cloud Run IAM ID-token handling |
| Backend | FastAPI/Uvicorn, one worker, `/health`, bounded requests | Hosted startup intentionally refused until shared authority, state and hosted inference are verified |
| AI | Ollama `qwen3:4b` on local loopback | Mac service/model weights are not in images. No approved hosted model adapter or qualified replacement; no silent fallback |
| Google | Existing local impersonation and local-only real-provider admission | Reviewed workload identity and shared durable reservations; no local ADC files in image |
| Saved plans | Restricted Supabase PostgreSQL session-pooler connection, TLS verify-full and capability-based access | Inject restricted role password and reviewed CA; verify staging-origin policy, connection limits and outage behavior without admin credentials |
| Sessions and replay | Process-local sessions, options, evidence tokens, receipts, refresh replay and HMAC authority | Shared expiring private evidence plus durable replay/revision/consumption authority |
| Financial admission | Process admission and inference leases; fsync-protected local cost file | Shared durable reservations, fencing and uncertain-send recovery across restart/overlap |
| Private save/advanced admission | Current loopback-origin restrictions | Separately reviewed trusted staging-origin/authentication contract; do not globally relax it |
| Local Docker verification | No Docker, Podman, Colima or Docker desktop engine available | Owner supplies a working local engine; run `sh deployment/container-smoke.sh` and review failures before publishing an image |

Max instances one and concurrency one limit capacity, **not** replay or financial risk. A rollout can overlap old and new instances, process restart loses authority, and each isolated limiter can admit independently. Receipts issued by one process are invalid in another; regenerating signing secrets is not session migration. File locking on ephemeral Cloud Run disk is not a cross-instance lock. Do not reduce these controls to local counters to save money.

## Minimal staging architecture and state ownership

Retain the [reviewed hosting proposal](task52-cloud-architecture-evaluation.md) as the starting point: one frontend service and one private backend service in proposed `us-east4`, plus existing Supabase saved-plan infrastructure (historically Free, `us-east-1`; current account state not checked). No new resource exists from this checkpoint.

Private ephemeral source/session/provider evidence belongs in the proposed non-persistent encrypted Redis service with bounded TTLs, no raw-text logs/backups and fail-closed loss handling. Durable SQL holds minimal financial reservations, operation intents/outcomes, consumed capabilities, revision fences and replay authority. Regional HA Cloud SQL is the existing proposed operational authority, separate from Supabase's saved-plan purpose. Redis replication alone cannot guarantee financial single use after failover. Do not remove either role without a reviewed equivalent implementation and crash model.

Reusing Supabase for operational tables could reduce fixed costs but is not implemented or approved: it requires a separately reviewed restricted role/schema, atomic transactions/fencing, connection budget, availability, privacy/retention and migration decision. Existing saved-plan tables/RLS are not an operational ledger. No database migration is included here. Secrets belong in pinned Secret Manager versions available only to the necessary workload identity; frontend receives no database/model/Google credentials. Existing local `.env.persistence`, personal SSH and ADC files must never be mounted.

Min zero/max one/concurrency one is a proposed private staging capacity limit, not a performance claim or distributed-safety implementation. Cold starts include image/runtime startup and later qualified inference dependency availability. No production p95 or five-second claim is established. Future pools must fit the entire replica and rollout connection budget. Private staging access also needs an explicit owner-approved authenticated access path; templates do not supply a public endpoint or load balancer.

## Local verification and limits

[Machine-readable results](task52-cloud-deployment-verification.json) distinguish native execution from containers. Native smoke assembles the exact backend file set and built Next standalone output in temporary folders. It starts real Uvicorn and Node processes, checks frontend-to-backend health, safe AI-unavailable response using a loopback HTTP 503 fake, mock ordinary planning, missing-database save refusal, backend outage propagation, restart receipt invalidation, privacy-safe logs and graceful shutdown. No real provider or persistent owner data is used. Independent limiters demonstrate why shared admission is necessary. Existing database-security tests separately simulate connect/query/uncertain-commit errors and prove no retry and admission-slot release.

The Linux amd64 CPython 3.12 wheel set was downloaded publicly and re-resolved offline with `--require-hashes`: 25 packages, unchanged original pins plus the existing binary extra's dependency. Actual Docker builds, non-root Linux execution, read-only filesystem behavior, image vulnerability scanning and Cloud Run probes remain **unverified** because no local engine exists. The container smoke command exits 78 with an explicit blocker. Native success is not container success. No browser-layout test was needed or claimed; UI source is unchanged. Public npm audit reported seven moderate findings in the development lint dependency chain (minimatch glob-parts amplification, GHSA-g3hv-75wg-m249), zero high/critical. No automatic update was applied; review/update that toolchain separately before publishing builds. Python/base-image vulnerability scans are not established.

Missing SQL settings were exercised; authenticated TLS connectivity and an actual remote database outage were not. Health is process reachability, not AI/database/shared-state readiness. Backend `/health` remains non-billable. SIGTERM tests establish process cleanup under native execution, not distributed crash or power-loss durability. Startup/liveness settings follow the [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract) but have not run on Cloud Run.

## Cost envelope — estimates, not purchase authorization

Public pricing reviewed at this checkpoint; no authenticated pricing/account checks. Region, currency, free-tier sharing and current quotes must be confirmed before approval. Existing credits/free tiers are not a durable operating-cost strategy.

| Category | Concrete planning basis / uncertainty |
|---|---|
| Cloud Run, request-based | Published reference rates: $0.000024/vCPU-second, $0.0000025/GiB-second and $0.40/million requests, before eligible aggregate free tier. At 10,000 outings/month with assumed 10 backend seconds at 1 CPU/1 GiB plus 5 frontend seconds at 1 CPU/0.5 GiB, and 100,000 total requests: roughly **$3.95/month gross**. Startup, other calls, retries (not authorized), networking and real measured usage excluded. [Official pricing](https://cloud.google.com/run/pricing) |
| Minimum instances | Proposed zero avoids fixed idle instance allocation but accepts cold starts. Two continuously allocated services at reference instance-based CPU/memory rates with those sizes would be about **$102.49/730 hours**, before other costs/free tier. This is an alternative illustration, not the min-zero quote. |
| Shared Redis | Prior Standard M1 1-GiB reference $0.064/GiB-hour ≈ **$46.72/730 hours**. The English price URL failed retrieval; [official localized reference](https://cloud.google.com/memorystore/docs/redis/pricing?hl=pt-BR) is not a verified current us-east4 quote. Regional minimum size/network/availability must be checked. |
| Durable operational PostgreSQL | Existing architecture's **$150–350/month** regional HA planning allowance, not a fresh SKU quote. CPU, RAM, HA, storage, backups and network vary; [official SQL pricing](https://cloud.google.com/sql/pricing). No instance selected or approved. |
| Existing Supabase | Historical Free tier; availability/connection capacity not account-verified. Public Pro starts **$25/month**, with usage extras; Free inactivity pausing can affect staging. [Official plans](https://supabase.com/pricing). No upgrade approved. |
| Secrets | Published free allowance six active versions and 10,000 access operations; beyond it approximately $0.06/version-month and $0.03/10,000 accesses. [Official pricing](https://cloud.google.com/secret-manager/pricing). No secret created. |
| Additional categories | Artifact Registry storage/builds, logs/metrics retention, private networking/VPC, inter-region Supabase transfer, egress, authenticated ingress/load balancer/Armor if selected, domain and backups need exact usage/quotes. AI and Maps remain separate metered costs with no new authorization. |

Illustratively Redis + prior SQL allowance + Supabase Pro + the request-based example is roughly **$226–426/month before unquoted services/usage**. This is deliberately not a minimum bill or current all-in quote. The original architecture's fixed shared-state costs dominate small staging compute; the owner must decide whether that design/cost is acceptable or separately approve an equivalent smaller shared-state design. No reliable complete operating total is established yet.

## Finite owner gates and rollback

1. Supply a working local container engine, build both Linux amd64 images, run the checked-in smoke, image scan and exclusion inspection; fix actual failures before publishing.
2. Review the shared ephemeral/durable state design, private-data retention/regions, operational database ownership and exact fixed-cost quote. Separately authorize implementation/migrations; no implicit new spend.
3. Separately finish hosted model qualification and approve an inference adapter. Local Qwen remains authoritative; model unavailability blocks interpretation.
4. Implement and security-review workload identity, trusted staging origins, private authenticated service networking, distributed session/replay/financial fencing, restricted SQL secrets/CA and fleet connection budgets. Preserve admission invariants in restart/overlap tests before changing the hosted refusal.
5. Review exact image digests, least-privilege identities, dependencies/advisories, current service quotes and resource limits. Obtain explicit provisioning/deployment/budget permission before any cloud creation.
6. Deploy privately only after those gates; functional hosted acceptance and phone testing remain Task 52 work. Task 53's original load-testing scope is not started by packaging.

Rollback promotes a previously reviewed image/config digest only if it still meets current source/schema/authority requirements. Do not roll back to independent local budgets or reuse lost/revoked capabilities. Until shared invariants exist, rollback is **refuse hosted startup**, not publish an unsafe legacy deployment. No active data/schema transition is made here.
