# Private hosting — exact next batch, not authorization

Baseline aa6d48cb24bde3340b139de45689010996b55675. November20,2026. Publication is complete; do not rerun it or recreate the registry. The new offline projection reuses the existing compiler, owner public signature and actual manifest/config receipts. It changes no pinned runtime/compiler/trust source and creates no cloud resources.

## One proposed owner decision

**Authorize the attached 22-command foundation batch only** in where-to-512422/us-east4: enable only Run/IAP/SecretManager APIs (Compute is deferred until the paid networking batch); initialize the two Google-managed service agents; create six dedicated workload service accounts and six empty role-owned regional secret containers; grant each workload access only to its own container and the Run service agent reader access only to the existing image repository. Expected new recurring/setup charges $0 for this empty foundation; existing approved registry storage continues. No Run services, networks, addresses, subscriptions, secret values, testers, provider IAM, financial grants or risk acceptance. Pre-execution read-only inventory must confirm target names/state; stop on conflicts/errors and review partial progress before any rerun.

For the subsequent paid hosting phase, propose **at most $180/month total infrastructure, plus $10 once for metered setup**, conditional on actual account terms, taxes and the exact Redis quote fitting those limits. This is a proposed purchasing/operational stop threshold, not an installed provider billing hard cap. No subscriptions, billing upgrade or paid resource creation is authorized yet. No AI/Maps expenditure is included or authorized. If the owner requires an absolute provider-enforced all-in hard cap, the present metered services cannot establish it; do not promise one.

Maximum scope: six existing images/services (1vCPU each, min0/max1; memory and concurrency from existing compiler), one custom VPC/subnet, one router/NAT/static IPv4, six empty secret containers/later18 pinned file versions, existing registry≤5GiB, one operational and one independently administered witness PostgreSQL project, and one Redis Cloud database. No load balancer, VM, connector, extra service, Enterprise Maps API, paid cloud scanning or new model. No automated dependency enlargement. Reuse an adequate existing operational subscription rather than purchasing a duplicate after verifying its capacity/terms.

## Exact commands now ready for review

Working folder `/Users/rahularutla/Documents/whereto`. The checked-in shell is executable by `sh` **only after the above separate approval**:

```sh
cd /Users/rahularutla/Documents/whereto
# Offline verification only; safe before approval, no cloud/key access:
PYTHONPATH=. backend/.venv/bin/python -m deployment.hosting_batch \
  "$HOME/.whereto-production-frontend-v1/state" --check
# DO NOT RUN until exact foundation authorization:
sh deployment/cloud-run/private-hosting-foundation-PROPOSED-v1.sh
```

It rechecks owner signature/source/OCI receipts before any gcloud command; no key is opened. The shell is review material, not an authorization bypass. All gcloud commands bind the project explicitly. Existing deployment compiler and genuine signed startup enrollment retain their authority checks.

After foundation creation, record observed SA numeric subjects, inventory existing network ranges and agree a nonoverlapping private /26 or larger. Independently supply the missing storage and enrollment inputs below. Copy `deployment/cloud-run/published-staging-v1.json` outside Git and fill only verified nonsecret fields. Six exact amd64 leaf digests are already filled; never substitute local config/index IDs. Compile the final six-service command review using the existing tool:

```sh
PYTHONPATH=. backend/.venv/bin/python -m deployment.publication_batch \
  "$HOME/.whereto-production-frontend-v1/state" /tmp/whereto-enrolled-run-review.json \
  --cloud-plan /absolute/path/to/owner-only-filled-staging.json \
  --registry-receipts deployment/candidates/registry-publication-v1
```

Choose a new output path if it exists. This only renders. With current null values **all six deployment commands are absent**; no genuinely executable full-service batch can honestly be produced until numeric secret versions and storage/runtime authority exist. Do not execute the historical bootstrap/publication sections of the older compiler: registry creation/uploads are completed. The new foundation projection removes them. No guessed resource/secret IDs, subjects or approval hashes were inserted.

## Published images, unchanged

Prefix `us-east4-docker.pkg.dev/where-to-512422/whereto-private/whereto-ROLE@sha256:`. These are actual Linux/amd64 manifest hashes, not local image/config or top-level provenance-index hashes.

| Role | Manifest SHA256 |
|---|---|
| frontend | `ccb7ae14347dce29a5a183cabd8e7bac3eac47f68103e537c0275e54841e81a6` |
| backend | `ddd0d355cf8027cd75c052a832c62483bd11c5ef53e9363b75ecfc88f73702ae` |
| factory | `b0e0f96111dd735d2df4c0f04cc89569fe45557376202c39fdf2f0ec745e4d95` |
| counter | `2398c26fcf4ec54e9ca03828a364d1ba16fc5225cbc37a56e4fe6e1b7b8fc84b` |
| dispatcher | `2a56fbc05b0c2fbb340f0f2385d16086a534d9f8ff1c3f87fea72710baab904a` |
| recovery | `8408d80c00e2bdbaa151772f01f5b98711b5e0f2c1967945487acd4a0ea5cec8` |

All source/config bindings remain in the existing [actual publication receipts](../deployment/candidates/registry-publication-v1/images.json). Existing0critical/77high per Python image and0critical/72high frontend findings remain unaccepted for runtime; storage-only approval does not accept them. No new build/scan was warranted by this deployment-only change.

## Current gross infrastructure estimate

Public rates checked November20; USD,744-hour upper-length month. No GCP free tier assumed. Supabase's advertised per-Pro-organization $10compute credit is shown separately, not assumed account eligibility. These are public rates, not current account invoices or a Redis regional quote.

| Item | Proposed exact scope and gross estimate |
|---|---|
| PostgreSQL | Two independently administered Supabase Pro organizations, one Small2GB/shared project each, direct IPv4. $25/org + $0.0206/compute-hour + $0.0055/IPv4-hour = **$88.84/month total before credits**, **$68.84** if both $10credits apply. No PITR add-on; included standard backup terms require owner confirmation. Existing account capacity may reduce incremental cost. |
| Redis | Paid Essentials250MB RAM-only in GCPus-east4; public offer starts $5/month, **exact regional quote R unknown**. Purchase only if all ACL/TLS/Lua/noeviction requirements hold and R≤$15/month including compulsory fees; otherwise stop. Do not select discounted RAM/SSD Flex or Pro($200minimum) silently. |
| Run | Request-based Tier1 CPU$0.000024/vCPU-second, RAM$0.0000025/GiB-second, requests$0.40/million. Min0 fixed compute$0;100aggregatevCPUh +80GiBh +100krequests ≈**$9.40**. Cold starts/overlap count toward metering. |
| NAT / static IP | Gateway$0.0014/assignedVM-hour, published gateway cap$0.044/hour =**$32.74/month**. Attached IP$3.72/month; reserved-unused IP can cost**$7.44/month**. Use the larger IP allowance, not both simultaneously. 50GiB processed adds$2.25; egress additional. Cloud Run NAT assignment count must be measured; six roles do not prove six billed assignments. |
| Secrets / registry | 18active regional file versions≈**$1.10/month**,100kaccesses$0.30gross; empty containers/management free. Existing5GiB registry envelope≈$0.51/month at published hourly rate, same-region pulls free. Automatic scans remain disabled. |
| Logs / transfer | Allocate$5each/month, ordinary logs$0.50/GiB with30-day retention. Egress is a spending allocation pending actual destinations/volume, not a fabricated universal rate. No raw user/provider/secret content; no paid custom metrics/log exports proposed. |

Conservative planning subtotal with no Supabase credits, R=$15, maximum gateway/IP allowance and the above usage allocations: **about$167.57/month before tax/premiums**, within proposed$180 only if actual mandatory extras fit. Low-use example with both credits, R=$5, six billed NAT assignments,10CPUh/8.5GiBh/10krequests,1GiB NAT processing and$2combined logs/transfer allowance: **about$88.44/month**. Neither is a guaranteed bill. Idle subscriptions/versions/IP/registry still incur charges even with zero users (about$82.89 with both credits/R=$5/reserved-unusedIP, before assigned-NAT charges). No vendor setup fee identified; $10setup is proposed metered allowance, not an invoice.

Sources: [Run](https://cloud.google.com/run/pricing), [NAT](https://cloud.google.com/nat/pricing), [IP/network](https://cloud.google.com/vpc/network-pricing), [Supabase compute](https://supabase.com/docs/guides/platform/compute-and-disk), [direct IPv4 example](https://supabase.com/docs/guides/platform/manage-your-usage/ipv4), [Redis pricing](https://redis.io/pricing/), [Redis us-east4 availability](https://redis.io/docs/latest/operate/rc/supported-regions/), [secrets](https://cloud.google.com/secret-manager/pricing), [registry](https://cloud.google.com/artifact-registry/pricing), [logs](https://cloud.google.com/products/observability/pricing).

## Inputs needed before services start / users enter

1. **Storage and witness owners:** actual operational Supabase plan/region/direct5432host/CA/roles; independently controlled witness project, administrator, restore/backup owner and recovery operator subject. A second password under the same restore administrator is insufficient. Small is a purchase candidate, not capacity proof: ≥18operational/22witness connection allowance plus platform headroom, per-role pools≤2, realistic CPU/concurrency test with unchanged1500msSQL/250mslock deadlines. Prior57014CPU-throttling and hosted restart/owner-overlap remain explicit tests. Confirm region availability and close-to-us-east4 placement with the database provider before purchase; no resource ID is invented.
2. **Redis quote/enrollment:** owner-observed Essentials250MB RAM-only GCPus-east4 regional quote, two named publisher/reader users, TLS hostname/CA, Lua/CAS, absolute expiry, noeviction,128MiBapplication bound and NAT allowlist; backup/restore and deletion terms. No default user or local-memory fallback. Paid availability is documented; actual account feature/price/endpoint remains unverified.
3. **IAM/IAP and secrets:** observed six SA subjects; private internal Run ingress and exact service audiences; only frontend public network ingress protected by IAP/IAM, never anonymous access. This no-organization project may require owner Cloud Console setup/custom OAuth client for first IAP enablement; supply consent/tester settings, maximum5named tester emails/verified subjects. Google documents no-organization support but warns initial OAuth bootstrap cannot be created programmatically: [direct IAP instructions](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run). Do not replace it with a public service or new login system. Numeric secret versions, sealed per-role configs, actual URLs/status confirmation, current source/epoch and genuine owner-signed frontend configuration are still missing. Selected owner trust key is already embedded; no new key/rebuild required.
4. **Real providers and runtime risk:** actual application-qualified model (human semantic review deferred), separately approved application OpenAI credential, current full-payload count/rate/fee policy, fixed endpoint/transport enrollment, finite owner-approved SQL/witness grants and current independent epoch. No reuse of historical5704count/evaluation key/$0.0025diagnostic as app authority. Approve Google content/credits/request-local continuation contract and dispatcher workload OAuth separately. Existing Google APIs do not authorize calls. Explicit residual container-risk disposition remains required; no artifact-storage signature supplies it.

**Order after separate approvals:** foundation → reviewed subnet/NAT and approved SQL/witness/Redis enrollment → operator schema/rate/epoch enrollment and sealed secret versions (no saved-plan migration) → compile/verify exact services/identities → recovery/counter then factory/dispatcher then backend/frontend as one verified graph, before testers → independently authorized real-provider financial enrollment and bounded first ordinary outing → desktop/mobile, expiry/replay/outage/worker replacement checks with Mac off → named IAP tester admission. Bootstrap must not depend on a synthetic/public/dummy application revision. `--no-traffic` alone does not guarantee no access on a first revision. Startup cannot pass until genuine provider/financial/identity dependencies are enrolled. No user traffic is a substitute for readiness.

Stop/shutdown: deny new tester actions first, drain exact factory callbacks, retain financial/uncertain-send/epoch history and audit evidence. Stop compute traffic; review removing NAT/static IP and subscriptions separately (idle bills continue). Never restore financial databases or Redis to roll back software. Rollback only to an observed compatible approved revision; no automatic old-build ownership transfer.

Verification and development attempts are in [the machine record](task53-private-hosting-batch-verification.json). No cloud account/secret/provider request, resource creation, image rebuild, new scan, migration or grant was performed.
