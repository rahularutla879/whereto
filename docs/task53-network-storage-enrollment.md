# Next private hosting actions — network and storage

**Demo-first update:** [minimum-cost compatibility findings](task53-demo-storage-compatibility.md) now qualify Free/directIPv6 rather than automatically purchasing Pro/Small. Existing IPv4-only N1, all consumed batches, source manifests and approvals remain unchanged; poolers are still refused. The older purchasing recommendations below remain historical selected-topology proposals.

## November 23 authenticated account findings — no purchase

N1 is complete, recorded in commit `fef21670ab0bb3dbe085c81e42f33bd0c6ccc031`; never rerun it. [Sanitized read-only account observation](../deployment/cloud-run/storage-account-observation-v1.json) supersedes the older signed-out/unknown-price observations below. This was dashboard inspection, not a database connection or hosted capacity test.

| Item | Actual account observation | Decision before enrollment |
|---|---|---|
| Existing `whereto` / `Where To` Supabase | Free/Nano, AWS North Virginia `us-east-1`; initially coming up/unhealthy, later **Healthy**, **7/60** connections. Database28.1MB; Nano≤0.5GB shared RAM. Current cost$0. | Reuse the project, preserve saved-plan schema/RLS; upgrade is required by this architecture's IPv4 direct-connection and backup requirements. Micro is the smallest eligible compute trial; **Small is the recommended operational starting candidate**, still subject to CPU/deadline tests. |
| Direct PostgreSQL | Port5432 endpoint observed; IPv6 default. IPv4 disabled; account offers **$4/month/database**, Pro-only. No actual SQL connection attempted. | Pro offered **$25/month**; explicitly resize compute (Nano is not automatically resized when organization becomes paid). Micro **$.01344/hour**, Small **$.0206/hour**, both observed. Verify-full TLS, restricted roles and current source/epoch contracts remain mandatory. |
| Database security/backups | SSL enforcement **off**, all IPs allowed; **Free excludes backups**, no backups listed, PITR off. Offered Pro daily retention7days. | Separately authorize SSL enforcement and narrow NAT/operator allowlists only after reviewing impacts on existing saved-plan clients. No change was made. |
| Redis quote | **GCP us-east4, Essentials RAM-only250MB, no HA, no persistence: $6/month; $.008/hour displayed**, beforetax,100GB network,256connections,4CIDR rules,1000ops/sec. Version8.8 offered. No databases exist; quote cancelled. | Actual TLS/custom ACLs/noeviction/backup settings cannot be verified as enabled before authorized creation. Named Users/Roles/RedisACL tabs exist, with no users defined. Configure separate publisher/reader, TLS/CA, default-user refusal, noeviction, no snapshot/export, actual NAT `/32`; then test exact Lua/CAS/expiry/client commands. |
| Redis default trap | Same250MB with single-zone HA+AOF: **$10/month**, only125MBdataset+125MBreplica. NoHA+AOF: **$7/month**. | Default HA dataset is smaller than current128MiB evidence ceiling before overhead. No-HA gives250MBdataset but loses evidence on restart; existing recovery must refuse safely. No risk acceptance or runtime setting was made. |
| Independent witness | No independently controlled target/administrator selected. | Separate organization/project under a **different administrator and backup/restore controller**, not another project under the operational owner. Smallest eligible starting plan: **Pro+explicitMicro+IPv4+7-day backups**, capacity-gated; Small if required by unchanged deadlines. Reserve22clients including revision overlap/operators, plus platform headroom. |

Public-rate744-hour worksheet, assuming a separate eligible$10compute credit per Pro organization and no tax/overages: Pro/Micro/IPv4 **$29.10**, Pro/Small/IPv4 **$34.42** (each rounded upward). OperationalSmall+witnessMicro+nominalRedis6 = **$69.52** for these storage items only; bothSmall+Redis6 = **$74.84**. These are arithmetic projections, not current invoices or full-hosting totals. Actual invoices, tax, credit eligibility, Redis hourly proration, CPU adequacy and witness ownership remain unverified. The proposed$180 infrastructure ceiling is still unapproved. No private credential, SQL/ACL mutation, payment, N2, secret version, grant or provider request occurred.

**Next owner decisions:** select/authorize the existing operational project's Pro/compute/IPv4 upgrade; name the independent witness owner; separately approve an empty, quarantined Redis database at the observed $6 quote, then verify its actual security settings before enrolling credentials or data. Payment details must be entered by the owner, not copied into repository/chat. Subsequent N2, SQL/Redis role/allowlist and secret enrollment require their own scopes. Earlier proposal text below is preserved as historical preparation, not a runnable authorization.


Prepared from `61de32e04845a995ce5c09d91ed347496a39d611`, November21,2026 UTC. **No creation or purchase is authorized.** Foundation and publication are complete; never rerun their batches. This is an offline projection of the existing compiler, not a new deployment architecture.

## First owner decision: N1 only, expected incremental fixed cost $0

Authorize exactly two commands in `deployment/cloud-run/network-N1-PROPOSED-v1.sh`: create custom VPC `whereto-staging` and its `us-east4` subnet `10.92.0.0/26` with Private Google Access. No firewall, default-network change, NAT/IP, API, IAM, database, secret value, provider or service deployment. Codex can execute after explicit authorization and fresh read-only conflict/permission checks. Stop on error or unexpected automatic changes; no creation retry.

The November21 read-only inventory found only the preserved default VPC/42subnets/four firewalls, zero routers/reserved addresses/VPN tunnels/peerings/Run services, and no observed subnet/route overlap. Confirm this CIDR is not reserved for an external/future VPN network; those ranges were unavailable. The six immutable SA subjects and exact published amd64 manifests are now populated in `network-storage-staging-PROPOSED-v1.json`. All runtime approvals, endpoints, secret versions and epoch remain unset. No public project/repository binding was observed. Existing empty-secret state is from the completed foundation verification; this checkpoint listed containers, not their versions.

```sh
cd /Users/rahularutla/Documents/whereto
# OFFLINE only: public owner proof, original source pins and six OCI receipts; no private key/API key.
backend/.venv/bin/python -m deployment.network_storage \
  "$HOME/.whereto-production-frontend-v1/state" --check
# ONLY after separate N1 authorization and fresh cloud checks:
sh deployment/cloud-run/network-N1-PROPOSED-v1.sh
```

Both shells recheck the committed preparation hashes and existing owner artifact proof. These are source/receipt checks, **not** current-cloud-state checks or a new signed hosting approval. Fresh authenticated preflight is mandatory. An artifact-only signature cannot approve runtime risk or storage purchases.

## N2 — separately approve when storage is ready for an allowlist

`network-N2-PROPOSED-v1.sh` contains exactly three existing compiler commands, in order: reserve `whereto-staging-egress` regional IPv4; create router `whereto-staging`; create manual-address Public NAT `whereto-staging` using that one IP. N1 must already match exactly. No connector, VM, extra IP allocation, firewall, service or public ingress is added. Do not run N1 again. Read back the actual address after creation; use only that observed `/32` for database/Redis allowlists, never a guessed IP or `0.0.0.0/0`.

With **no deployed workloads**, one reserved-unused IPv4 costs at most **$7.44 per744-hour month** before tax; NAT assignment/data usage is zero in that empty configuration. A separate proposed N2-only limit could be $10 for30 days, conditional on actual account charges, with no workloads or paid traffic authorized. It is not approved here. Delay N2 to avoid idle charges. Once services run, NAT and egress require the later hosting envelope below; this is not an unlimited $10 runtime authorization.

## Account actions required before buying or enrolling storage

Both dashboards were inspected with owner permission and are currently **signed out**. No login, credential read, subscription or account change occurred. Owner: sign into the existing [Supabase dashboard](https://supabase.com/dashboard) and [Redis Cloud console](https://cloud.redis.io/); then Codex can complete the already-authorized read-only inspection. Do not send passwords, keys or connection strings in chat.

| Target | Minimum exact review / owner action | What Codex can do after scoped authorization |
|---|---|---|
| Operational PostgreSQL | Select existing Where To? Supabase project; verify project reference/region, current organization plan, compute, free connection headroom, direct IPv4 add-on, CA, network restrictions and backup owner. Preserve saved-plan `whereto` schema/RLS. Reuse if sufficient; do not buy a duplicate. | Inspect nonsecret settings, then separately authorized direct TLS catalog/capacity probe; prepare target-specific restricted-role/schema enrollment from existing real SQL. No DB credentials or DDL authorized now. |
| Independent witness | Name a **different administrator and backup/restore owner**, in an independently controlled organization/project. Conditional SKU: Supabase Pro, Small compute, direct IPv4, daily backups. A second project under the same restore owner is insufficient. Confirm region near us-east4 (exact available region from dashboard), retention and restore procedure. | Prepare exact reviewed witness SQL and restricted logins once actual target/administrator is known. No restore, grant, migration or purchase now. |
| Redis | Obtain actual **GCP us-east4, Essentials, RAM-only250MB** quote, billing interval/tax, TLS support, two custom ACL identities, and no-eviction setting. Do not substitute Flex/SSD, Free, Pro or Memorystore Basic. Exact regional price remains unknown; confirm the managed Redis version/vendor patch status before purchase. | Verify settings read-only; after a separate purchase/config authorization, enroll TLS/CA and narrow publisher/reader ACLs with actual NAT `/32`. No purchase or password generation now. |

PostgreSQL requires **direct port5432** with `sslmode=verify-full`; current hosted adapter rejects pooler hosts and6543. Historical saved-plan evidence used `aws-0-us-east-1.pooler.supabase.com:5432` and an older Free plan snapshot: that does **not** establish current real-runtime compatibility. No private `.env.database` was read. Supabase direct connections default toIPv6; paid IPv4 supports the selected existing IPv4 NAT design. [Direct connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres), [IPv4 terms/pricing](https://supabase.com/docs/guides/platform/manage-your-usage/ipv4).

Select pool maximum2 for each of **four operational logins** (factory runtime+issuer, counter, dispatcher delivery) and **five witness logins** (backend nonce, factory, counter, dispatcher, recovery). Revision overlap plus two operator connections reserves **18 operational /22 witness**, in addition to existing app/platform headroom. No admin/owner credential enters a worker. Existing port verifies session_user/current_user, restricted privileges, exact contract/policy/build/epoch, and bounded pool lifecycle. `deployment/sql/hosted-capacity-readonly-v1.sql` is an inert read-only catalog probe: no data inspection, grant or installation. Operator can later run it through a separately approved existing secure **direct** connection; no speculative DSN/credential path is supplied.

Capacity acceptance must exercise actual concurrent real-profile SQL and witness checks, revision overlap, contention, restart and backup quarantine. Prior SQLSTATE57014 CPU-throttling remains relevant: **do not increase1500ms statement /250ms lock deadlines**. Small has2GB/sharedCPU and90 direct connections; it satisfies the proposed connection arithmetic only, not proven CPU latency. A failed capacity trial blocks deployment or needs a separately priced larger plan. [Compute specifications](https://supabase.com/docs/guides/platform/compute-and-disk).

The existing source-pinned `private_runtime.real_finance.profile.scripts()` / `contracts()` provide real operational/witness DDL projections; do not execute Docker fixture bootstrap or raw synthetic parent SQL. Installation needs actual managed-admin privilege review, exact restricted logins, schema ownership/ACLs and independent post-install contract measurements. No application financial policy/grant is inserted until separately approved. Pro daily backup retention is7days; PITR is a separately priced option, not selected. Restores must preserve/quarantine exposure against independent witness evidence and operator epoch; never restore both authorities together or reset spending. [Backup behavior](https://supabase.com/docs/guides/platform/backups).

Redis acceptance: TLS+AUTH+hostname/CA verification, default user disabled, separate publisher/reader, existing Lua atomicCAS, absolute PXAT/PEXPIREAT deadlines, **no eviction**, maximum application evidence128MiB. Exact key prefix derives from runtime `52-encrypted-shared-evidence-local-v1` plus enrolled epoch; do not copy the older fixture prefix. Publisher needs existing narrow GET/SET/EVAL/TIME and hash/sorted-set commands; reader onlyPING/GET/TIME. Verify these exact commands on the purchased plan, including client handshake, before enrollment. NoCONFIG/ACL/FLUSH authority in app users. Select persistence **None**, no backup/export of source evidence, and confirm provider retention treatment; Redis loss refuses continuation, never renews financial authority or automatically repeats provider calls. Google content remains request-local except separately permitted Place IDs.

Official documentation listsGCPus-east4 Essentials and paid TLS, named data-access identities, Lua support subject to command restrictions, no-eviction selection and persistenceNone. The250MB tier lists256connections, fourCIDR rules,100GBmonthly transfer and1000ops/sec; these are limits, not a reserved throughput guarantee. Account-specific two-user availability and price must still be verified. [Regions](https://redis.io/docs/latest/operate/rc/supported-regions/), [plan limits](https://redis.io/docs/latest/operate/rc/subscriptions/view-essentials-subscription/essentials-plan-details/), [TLS](https://redis.io/docs/latest/operate/rc/security/database-security/tls-ssl/), [ACLs](https://redis.io/docs/latest/operate/rc/security/access-control/data-access-control/), [Cloud EVAL compatibility](https://redis.io/docs/latest/commands/eval/), [eviction](https://redis.io/docs/latest/operate/rc/databases/configuration/data-eviction-policies/), [persistence](https://redis.io/docs/latest/operate/rc/databases/configuration/data-persistence/).

## Exact public-rate arithmetic; account total still unquotable

USD,744 hours, before tax/discounts/realAI/Maps. No new setup fee was established for the selected resource types; hourly setup/transfer usage and a subscription's first invoice still cost money. The prior **$180/month infrastructure +$10metered setup proposal remains unapproved**, is not a provider-enforced hard cap, and cannot be confirmed all-in until actual Redis/account/tax/capacity evidence exists.

| Item | Current public basis |744-hour arithmetic |
|---|---|---:|
| Each conditional Supabase Pro/Small/directIPv4 organization |25/month +.0206/hour compute +.0055/hour IPv4 |44.4184 before any eligible10compute credit;34.4184 if available |
| Two separately controlled such organizations |Do not double-count base/credit if existing operational org is reused |88.8368 without credits;68.8368 with two eligible credits |
| Redis250MBus-east4 |Pricing advertises Essentials **from**.007/hour, not this regional RAM SKU quote |**R unknown**, not assumed$5; worksheet conditional allowanceR≤15 |
| NAT gateway |.0014/assignedVM-hour capped.044/hour |0empty; maximum32.736 gateway charge; actual assignment count is not six roles |
| Egress IPv4 |.005/hour used by NAT; .01/hour reserved-unused |3.72 used or7.44 unused, not both |
| NAT data processing |.045/GiB inbound+outbound |50GiB=2.25; internet/destination egress additional |
| Existing registry,≤5GiB |.000136986/GiB-hour before free allowance |≤.50958792 |
| Later18active secret versions /100k accesses |.000082192/version-hour; .03/10k accesses, before free allowances |1.100715264 +.30; currently zero versions |
| Later request-billed Run usage illustration |10vCPUh,8.5GiBh,10krequests at.000024/CPU-s,.0000025/GiB-s,.40/million |0.9445; use9.40 planning allowance, not fixed subscription |

[Supabase prices](https://supabase.com/docs/guides/platform/compute-and-disk), [Redis starting prices](https://redis.io/pricing/), [NAT](https://cloud.google.com/nat/pricing), [IP](https://cloud.google.com/vpc/network-pricing), [Run](https://cloud.google.com/run/pricing), [secrets](https://cloud.google.com/secret-manager/pricing), [registry](https://cloud.google.com/artifact-registry/pricing). Regional/account terms govern. No free GCP allowance assumed.

Conservative **planning illustration $167.58/month**, rounded upward: twoSmall organizations88.8368 (no compute credits), conditionalRedis15, NAT maximum32.736, IPv4 maximum7.44, registry.50958792, secrets1.100715264+.30, Run9.40,50GiBNAT2.25, logging5 andother-egress5. Log/egress allowances are usage assumptions, not fixed price guarantees. Small CPU adequacy unproven. No quote or authorized$180 envelope is asserted. IfR/tax/capacity/egress exceeds the remaining headroom, stop and reprice; no automatic plan upgrade. RealAI/Maps budgets remain entirely separate.

## Execution order, with separate approval at each spending/change boundary

1. Owner confirmsCIDR and authorizes **N1 two commands only**. Codex preflights/executes/verifies; preserve default network and completed foundation.
2. Owner signs into both dashboards; Codex completes read-only reuse/quote check. Owner names independent witness administrator/restore owner. No purchase yet.
3. Owner approves exact database/Redis subscriptions, current invoice terms and finite setup/monthly scope; administrators perform their purchases. Do not buy until exact regional quote/capacity/independence is acceptable.
4. Separately authorize **N2 three commands** when ready to bind actual static IP. Then separately authorize network allowlists, restricted SQL/ACL enrollment and unchanged-deadline capacity/recovery tests. No secretvalues inGit; secret-version enrollment needs its own authorization.
5. Only after runtime vulnerability disposition, qualifiedapplicationLLM, real credentials/rates/countpolicy/financialgrants, Googlecontent obligations, epoch, IAP/testers and exactsignedsource enrollment: compile the existing six-service deployment commands. No synthetic fallback; no public access or provider call is implicit in infrastructure approval.

**Next smallest decision:** authorizeN1 only, expectednewfixed$0, confirming10.92.0.0/26. Both authenticated storage inspections remain blocked on owner sign-in, not on another architecture implementation.

## Verification actually performed

Final focused suite: **39passed,0failed/errors/skipped** (13new network/storage checks +26existing owner-proof/publication/real-source checks). Genuine public owner proof and all six published OCI receipt bytes passed; real financial SQL/profile source pins unchanged; dependency check, shell syntax, preparation hashes, diff whitespace and changed-file secret patterns passed. Chapter18 updated; all20chapters preserved. Initial development test had11passes/1error because it invoked the frozen pre-owner raw frontend pins; those correctly refused. The test now independently asserts the finite existing network commands; no historical pin was changed.

Authorized read-only GCP checks passed; both authenticated storage inventories stopped at sign-in pages. **Not run:** capacity SQL on any database, hosted migrations/ACL probes/load/recovery tests, application/browser regression suites, image builds/scans, provider calls or fresh324-file private inventory. No application/runtime/dependency/image source changed, so those suites were not claimed. Historical journal/evidence were not accessed; original recorded10attempts/$0.047366625/324files, frozen payloads/consumed scopes/halt remain untouched. [Machine-readable exact results](../deployment/cloud-run/network-storage-verification-v1.json).
