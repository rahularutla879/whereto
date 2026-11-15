# Task 52 — private synthetic staging purchase decision

Baseline `6c8c388d91b0aadc9b476013ebbd261e13dc779a`. **Proposal only; do not provision yet.** Local engineering checks do not constitute independent security acceptance. [Verification, arithmetic and exact identities](task52-staging-purchase-verification-v1.json) · [Retained security findings](task52-staging-purchase-security-v1.json).

## Recommended purchase

Reuse the existing six-role Cloud Run application, **paid Redis Cloud Essentials RAM-only250MB**, and **Supabase Pro/Micro**. The witness must occupy a **separate Supabase organization/project with a separately named restore administrator**. No additional application service or financial framework. Proposed first review period: 30 days, two named testers, 100 ordinary outings; synthetic providers only. Real AI/Maps, grants, public traffic and automatic renewal are excluded.

| Service | Exact proposed configuration |
|---|---|
| Frontend | Existing closed Next image; GCP `us-east4`,1vCPU/512MiB; IAP tester allowlist. |
| Backend | Existing FastAPI role;1vCPU/1GiB; frontend invoker only. Witness nonce role, no issuer authority. |
| Factory/issuer | Existing factory;1vCPU/1GiB; one enrolled revision-owner slot; backend ordinary actions and dispatcher callbacks only. |
| Counter | Existing fictional byte counter;1vCPU/512MiB; factory only. Not actual provider tokenization. |
| Dispatcher | Existing non-network synthetic responder;1vCPU/1GiB; factory only; exact single-use payload/owner checks. |
| Recovery | Existing recovery role;1vCPU/512MiB; separately authenticated operator; factory can only probe readiness. |
| Operational SQL | Existing Supabase project, Pro/Micro assumption + dedicated IPv4. Retain existing region; confirm account capacity/backups. Direct5432, verified TLS, restricted roles; no saved-schema/RLS changes. |
| Witness SQL | **Separate organization Pro, one Micro project, AWS `us-east-1` North Virginia, dedicated IPv4**; separate restore custodian and role secrets. Direct5432, verified TLS; daily7-day backups. |
| Redis | **Paid Essentials RAM-only250MB, nonreplicated, GCP `us-east4`**, verified TLS, named publisher/reader ACL users, `noeviction`, persistence/backups off. |
| Network/secrets | One VPC/subnet, Direct VPC all-traffic/PGA, one NAT/router/static IPv4, one regional registry, one private DNS zone if needed; per-workload Secret Manager versions. |

All six Run services: request billing, concurrency1, min0/max1,120s request timeout. Exact Google OIDC audiences and caller-specific `roles/run.invoker`; no `allUsers`, broad Editor/Owner or JSON service-account keys. Backend/authority ingress stays private. Factory revision routing/draining must be verified: an instance maximum alone does not establish process ownership during rollout. Missing ownership refuses; callbacks never transfer/retry. SQL pools maximum2 per role/target require separate operational/witness capacity budgets including rollout overlap. Existing SQL1500ms statement/250ms lock deadlines remain unchanged.

Redis Essentials requires **restricted public TLS**, not private IP: default-deny CIDR permits only the dedicated NAT `/32`; default Redis user disabled. Publisher receives only the namespace and commands used by the existing Lua CAS; reader GET plus necessary handshake/PING. Existing128MiB/350-record encrypted evidence cap, absolute expiry and no financial authority remain.250MB plan documentation lists256connections/100GB monthly transfer/1000ops per second; hosted performance is untested. Nonreplicated evidence can disappear: continuation then refuses, never reconstructs paid work.

Paid Essentials supports these features and the proposed region; the exact regional checkout price remains unverified. Free Essentials lacks TLS. Redis Cloud Pro is the compatible private-connectivity alternative, **published minimum$200/month**, requiring a separate quote. Memorystore Basic lacks ACLs; Redis Cluster's cluster routing is not a verified drop-in for this non-cluster client. Do not silently weaken identities or substitute providers. Sources: [plans](https://redis.io/docs/latest/operate/rc/subscriptions/), [regions](https://redis.io/docs/latest/operate/rc/supported-regions/), [ACLs](https://redis.io/docs/latest/operate/rc/security/access-control/data-access-control/role-based-access-control/), [TLS](https://redis.io/docs/latest/operate/rc/security/database-security/tls-ssl/), [CIDR](https://redis.io/docs/latest/operate/rc/security/cidr-whitelist/), [eviction](https://redis.io/docs/latest/operate/rc/databases/configuration/data-eviction-policies/), [Lua](https://redis.io/docs/latest/commands/eval/).

## Witness independence and price

The operational administrator must have **no witness organization membership, broad management token or restore permission**. A different schema, a shared backup or another project under the same administrator is insufficient. Name the separate recovery custodian before purchase. Shared provider/root compromise, collusion and correlated provider failure remain outside this separation. A restore remains stopped until explicit reconciliation/new epoch; no refund or authority resurrection.

Selected witness price: Pro$25 includes one Micro compute credit; IPv4$0.0055/hour → **$29.015 per730hours**, before tax/overages. Daily7-day backups included; no PITR add-on. Select exact `us-east-1`, not a general region. [Plan](https://supabase.com/pricing), [compute](https://supabase.com/docs/guides/platform/manage-your-usage/compute), [IPv4](https://supabase.com/docs/guides/platform/manage-your-usage/ipv4), [regions](https://supabase.com/docs/guides/platform/regions).

Alternative: independently administered Cloud SQL Enterprise PostgreSQL17 `db-g1-small`,10GiB SSD, zonal Iowa `us-central1`: reference$25.55compute+$1.70storage+$0.80/10GiB backups≈**$28.05/month before networking**. No shared-core SLA; separate-project private connectivity/shared-CA hostname verification adds unquoted configuration/cost. Therefore not selected over the simpler direct-TLS witness. A same-organization additional Supabase Micro is cheaper but fails the intended administrative separation. [SQL pricing](https://cloud.google.com/sql/pricing), [limitations](https://docs.cloud.google.com/sql/docs/postgres/instance-settings), [TLS](https://docs.cloud.google.com/sql/docs/postgres/configure-ssl-instance).

## Finite bill of materials

USD,730hours, no credits/free discounts assumed, before taxes. `R` is the **actual Redis regional quote**, unknown. Public [Redis pricing](https://redis.io/pricing/) advertises from$0.007/hour/$5monthly; **$5.11 for730hours is illustrative, not a verified regional checkout price**.

| Component | Low-use estimate | Planning case |
|---|---:|---:|
| Six Run services combined |$0.9445|$9.445|
| Operational Pro/Micro + IPv4 |$29.015|$29.015|
| Independent witness Pro/Micro + IPv4 |$29.015|$29.015|
| Redis |R|R|
| NAT + static IPv4 + processing |$11.871|$16.364|
| Secrets |$1.83|$2.10|
| Artifacts |$0.50|$1.00|
| Logs/built-in monitoring |$1.00|$5.00|
| DNS |$0.24|$0.28|
| Build |$0.06|$0.36|
| Other transfer contingency |$1.00|$5.00|
| **Total** |**$75.4755 + R**|**$97.579 + R**|

At illustrative R=$5.11: **$80.59 expected / $102.69 planning**. Proposed review envelope **$110/month, unapproved**, not a billing hard stop. Actual quote/account changes must return for approval. The previous$200 proposal is not accepted. Existing operational subscription is counted in full; subtract already-paid capacity when calculating incremental purchase costs.

Low/planning assumptions:10/100 aggregate CPU-hours,8.5/85GiB-hours,10k/100k service requests;8/12 NAT-assigned instance equivalents including overlap/hold time,1/10GiB processed;30 secret versions and10k/100k accesses;5/10GiB artifacts;2/10GiB logs;100k/200k DNS queries;10/60 build minutes. Transfer reserves are estimates, not destination-specific quotes. Rates/arithmetic: [Run](https://cloud.google.com/run/pricing), [NAT](https://cloud.google.com/nat/pricing), [secrets](https://cloud.google.com/secret-manager/pricing), [registry](https://cloud.google.com/artifact-registry/pricing), [logs](https://cloud.google.com/products/observability/pricing), [DNS](https://cloud.google.com/dns/pricing), [Build](https://cloud.google.com/build/pricing).

Zero users still cost approximately **$64.18+R/month** for retained subscriptions/IPv4, NAT IP, secrets, artifacts and DNS, plus actual background/assignment usage. No fixed provider setup fee found in the reviewed public pricing; propose a separately approved **$5 one-time metered setup allowance**. Reviewer fees unknown/excluded. Account billing/trial status, regional quote and operational plan remain unchecked; no implicit upgrade. Save through scale-to-zero, spare approved operational capacity and bounded logs/images—not shared witness administration or ACLs. No extra HA, PITR, custom domain/load balancer, paid scans/support or custom monitoring is included.

## Security disposition: still blocked

Seven fresh final-image scans used pinned Grype `sha256:13113eeceab017260370cf540e1d25442c59665fd07d1b09b66d63bb0c282887` and **one November15 database**. Python roles: **3critical/86high each**. Frontend baseline/candidate: **2critical/53high**.32 unique critical/high advisory IDs/89 package-version rows retained. Four added high PAM package matches all reference `CVE-2025-6020`: database evolution, not new installed code. No suppression or acceptance.

Official Python3.12 Bookworm digest and eligible installed package candidates are unchanged. Debian still marks [glibc](https://security-tracker.debian.org/tracker/CVE-2026-5450), [SQLite](https://security-tracker.debian.org/tracker/CVE-2025-7458) and [PAM](https://security-tracker.debian.org/tracker/CVE-2025-6020) vulnerable. No fixed-available high/critical match in this cohort. Newer Node24.22.3 versus24.22.2 built/passed image checks but removed **zero** advisory matches; **not promoted**. Seven moderate npm tooling findings remain; no broad dependency/distro update.

Independent reviewer must inspect each retained digest/advisory/package, native TLS/libpq/parser reachability and local privilege prerequisites; approve remediation or an explicit expiring private-synthetic-only residual-risk disposition with controls/owner/revocation triggers. Non-root/read-only/capability controls and absence of a direct vulnerable call are not fixes or proof of unreachability. No AI-generated exception. If unacceptable, separately approve a broader pinned-base/backport cohort.

## Enrollment, rollback and owner decision

Exact six baseline image digests and nonpromoted candidate are in the security JSON; common role cohort `2db736f5c65fd029aa20ac142de03331bd4b446a9b05409532fb95c3e57daeee`. Approval must name independently disposed final digests. Required secrets: each workload's own proof/configuration seal, exact restricted SQL credentials/CA/schema fingerprint, factory publisher/dispatcher reader credentials and AES key ID, independent epoch/recovery authority. No test signer, fake IdP, Docker controller, owner mount, provider credential or historical evidence. [Existing role matrix](../deployment/private-network-v1.json).

Migration scope: new isolated operational/witness objects and restricted routines with operator-only bootstrap and fictional synthetic state. No saved schema/RLS/user migration, real dollar grant or journal change. `launchable:false` and normal startup refusal remain until exact enrollment passes.

**Mandatory gates:** independent vulnerability disposition; named separate restore custodian; Redis regional quote and restricted-public-TLS approval; operational capacity/backup/direct-host confirmation; exact IAM/IAP testers, secrets, migration and resource-cost approval. After separately authorized provisioning, verify real IAM/network/ACL/CAS, cold starts, revision ownership, outages and Mac-off ordinary browser use before tester admission. Current model/Maps accuracy is not established. Advanced/options/Details/origin/save/refresh remain blocked; public beta enhancements can wait. Historical SQL/assertion uncertainty and the unchanged expired-date test failure remain disclosed.

Shutdown: close tester admission, stop new factory actions, bounded drain, revoke stale invocation/enrollment and retain all SQL/witness facts. No resend/refund. Roll back only compatible code with current epoch/replay history; database restoration stays stopped until separate reconciliation. Redis loss refuses continuation. Scaling Run to zero does not stop database/Redis/IP/storage charges. Subscriptions continue until an operator cancels them; the 30-day review does not expire billing automatically. Retained state can continue charging. Delete only named pilot resources after approved retention/backup handoff—never financial history as cleanup.

## Verification completed

Selected backend tests: **92 passed**; locked-image metadata tests: **4 passed**; native packaging: **7 passed**. Frontend: **322 passed / 1 failed / 0 skipped**, with the fixed November14 date reproduced as `outing_date_expired`; no test was changed. A duplicate sequential attempt was interrupted after206 passing judgments and has no final suite result. TypeScript, ESLint, candidate production build, dependency consistency and closed-image/non-root/read-only/preload refusal checks passed. Seven fresh scans completed, preserving all advisory findings. npm audit completed with7moderate advisories (exit1, not a clean audit). Initial sandbox/host-dependency errors are retained in machine evidence. Full backend, fresh browser and complete SQL/Redis/recovery suites were not rerun; no hosted acceptance is claimed. Handbook14/18 updated; other18 chapters preserved.

**Next actual boundary:** obtain independent security disposition, confirm the regional Redis quote and separate witness custodian, then request explicit owner approval of this fixed purchase scope/final price. No resource creation is authorized here.
