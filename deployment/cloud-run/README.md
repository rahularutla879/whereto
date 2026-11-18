# Private Cloud Run configuration — preparation, not deployment

Target: `where-to-512422` (observed project number `895186533714`), `us-east4`. Task 52/52B remain unfinished. The owner now authorizes **Task 53 preparation in parallel**, not acceptance, provisioning or provider execution.

## What can run now

From `/Users/rahularutla/Documents/whereto`:

```sh
PYTHONPATH=. backend/.venv/bin/python -m deployment.cloud_run deployment/cloud-run/staging.example.json
PYTHONPATH=. backend/.venv/bin/python -m unittest deployment.test_cloud_run -v
```

The first command only prints an offline JSON plan. There is no apply command, subprocess execution, credential lookup, provider send, financial grant or migration executor. Unknown resource IDs, endpoints, tester subjects, secret versions, storage targets and approvals remain `null`. Keep filled local inputs outside Git; never place secrets in these inputs. Source pins verify both this compiler and the existing candidate cohort. Handwritten approval hashes cannot activate a runtime.

The plan contains explicit argv for API/service-identity enrollment, a regional immutable-tag registry, six dedicated workload accounts, publication, VPC/private Google access/static NAT, own-role Secret Manager containers, IAM/IAP, six Cloud Run deployments and exact-revision rollback. Incomplete deployment argv remain absent. **Commands are review material, not authorization.** No resources were created by this checkpoint.

## Important release stop

The existing six Debian 13 candidates are source-pinned **synthetic-only**. `private_runtime/private_service.py` rejects real transport, its counter uses fictional byte counting/SQL policies, its dispatcher calls the simulation responder, and the frontend startup purpose is synthetic-only. Inactive real adapters exist but are not selected by these images. Fixture-related modules also remain in the cohort; see generated `imageContentReview`. Their historical credential-exclusion check is not a claim that the images are fixture-free or safe for real API credentials.

Consequently the compiler always reports `releaseEligible=false`. Even completed enrollment fields cannot make these images a genuine demonstration. A reviewed real-provider source cohort must connect the existing adapters and qualified counter/rates/SQL authority, remove fixture-only dispatch from its runtime, satisfy Google content handling and retain closed enrollment. This is a concrete existing-runtime integration gate, not a request for another architecture. No real-mode flag, synthetic production response, local Ollama or evaluation API key can substitute.

## Six-role deployment contract

| Role | CPU / memory | HTTP concurrency | Allowed Run callers | SQL purposes |
|---|---|---:|---|---|
| frontend | 1 / 512 MiB | 1 | IAP service agent only | none |
| backend | 1 / 1 GiB | 1 | frontend | witness nonce |
| factory/issuer | 1 / 1 GiB | **8** | backend, dispatcher | runtime, issuer, witness-factory |
| counter | 1 / 512 MiB | 1 | factory | counter, witness-counter |
| dispatcher | 1 / 1 GiB | 1 | factory | delivery, witness-delivery |
| recovery | 1 / 512 MiB | 1 | factory probe; separately enrolled recovery operator | recovery witness |

Each has its own service account and immutable numeric subject, gen2, request-based CPU, min zero/max one at service and revision levels, port8080 and 120-second HTTP timeout. These settings do **not** relax protected SQL1500ms/lock250ms deadlines. Prior PostgreSQL57014 CPU-throttling evidence requires realistic hosted capacity/concurrency verification before tester admission. A TCP startup probe is liveness, not functional/provider readiness.

Factory concurrency8 accommodates the existing four-action/four-callback semaphores: an ordinary request waits for dispatcher-to-factory callback, so concurrency1/max1 would deadlock. This does not increase native action admission or spending. Cold starts, overlapping revisions, exact callback-owner routing and constrained resources still need hosted verification; max1 is not a guarantee that an old factory owns every callback.

Backend and privileged ingress are internal, with invoker IAM enforced. Direct VPC all-traffic plus Private Google Access is proposed for internal Run calls and stable NAT egress to public TLS storage/provider endpoints; no additional service or Serverless VPC connector. Frontend ingress is reachable for IAP, never anonymously invokable. Workload audiences are **observed canonical HTTPS service URLs**, not guessed URLs, revision tags or IAP audiences. The separate signed IAP audience is `/projects/895186533714/locations/us-east4/services/whereto-frontend`; the backend/factory still independently verify scoped user ownership, body proofs, nonces and native authority.

Named testers (maximum five) get only IAP access after functional/security verification. Email alone never establishes application ownership. Direct IAP may need actual account/OAuth consent bootstrap, especially without an organization; that state is unknown. No users or broad Owner/Editor grants are invented.

`--no-traffic` is a revision-safety request, **not a guarantee that a first service revision receives no traffic**. Do not admit testers until the complete private graph is verified. Establishing exact service URLs without public/dummy/synthetic product bootstrap is an explicit enrollment step; no fake URL or permissive first revision is supplied here.

## Storage, secrets and provider enrollment

- Reuse `private_runtime/connections.py` and `redis_port.py`; this compiler validates nonsecret enrollment constraints, not live connectivity. Direct/session-affine PostgreSQL5432 only, verified hostname/CA, exact schema contract, distinct restricted session/current-user roles, pool maximum2 and operator/overlap connection budgets at least18 operational/22 witness. No admin credentials, transaction pooler or migrations in application startup. PostgreSQL capacity and actual Supabase plan/host remain unverified.
- Witness must have different administrative and backup/restore ownership from operational storage, plus its own restricted credentials and current independently protected epoch. Proposed minimum: separately controlled Supabase Pro organization/Micro project, direct IPv4. An independently controlled operator identity is required; a second password under the same restore owner is insufficient. No witness administrator has been designated.
- Redis proposal remains paid Redis Cloud Essentials250MB in GCPus-east4, TLS with named separate publisher/reader ACL identities, Lua CAS, absolute expiry, `noeviction`,128MiB evidence bound and static-NAT allowlist. Exact regional availability, network terms and **price quote are missing**. Public TLS is not private-IP networking. Memorystore Basic is not substituted. Test the actual ACL/TLS/noeviction service before enrollment.
- Cloud Run forbids mounting different secrets in one directory. Preserve existing `/run/secrets` paths using **one role-owned Secret Manager container with a distinct pinned numeric version for each file** (18 versions total). Each workload can read only its own container. This is packaging for the existing loader, not a new credential system. Contents/versions must be enrolled by the trusted operator; no `latest`, credential values or version creation in the plan. Gen2 volumes are root-owned/read-only; verify actual mounts and rotation on deployment.
- Frontend receives only sealed frontend configuration/enrollment. No API key enters its bundle. Backend receives no issuer, provider or recovery credentials. Dispatcher alone may receive a separately approved application OpenAI secret; **do not reuse the historical evaluation credential**. Google uses dispatcher-assigned short-lived workload OAuth plus project-local `serviceUsageConsumer`, only after separate approval. No JSON service-account keys, Mac ADC, local filesystems or Docker socket.
- Provider endpoints remain fixed Responses, Places Text Search and Compute Route Matrix. No Details/Enterprise, photos, automatic retry, alternate model or fallback. Price/count/model/purpose/grant/source/epoch checks must precede every provider send. The experimental5,704count/$0.0025proposal is not an application financial policy or qualified model.
- Google place IDs may be allowed by the existing typed contract; venue/route facts remain request-local while the exact content-use contract is unapproved. Do not retain snapshots in Redis/SQL/logs/backups or refill missing evidence through paid requests. Required recovery evidence missing means refusal. Advanced, pagination, saved-provider persistence, standalone discovery, provider Details and automatic refresh stay closed.

## Safe publication and revision replacement

Keep the six local image config digests, original Bookworm images and existing rollback references intact. A local OCI config digest is **not** a registry manifest digest. Publication must capture raw manifest and config bytes; `publication_receipt()` verifies both hashes, Linux/amd64 and the exact reviewed image config. An index requires explicit platform selection. No unverified tag/digest may be enrolled.

Before changing traffic, stop new actions, drain exact factory ownership (existing8-second drain/5-second permits), invalidate incompatible native builds/fences and preserve current financial/replay/epoch history. Rollback accepts an observed exact compatible service revision, never `LATEST`; do not restore databases or Redis to roll back software. Any uncertain send remains charged/non-retryable. Hosted worker replacement and callback-owner overlap are still mandatory staging tests.

## Read-only account observations, November18

[Sanitized metadata](account-observation-v1.json): project ACTIVE, billing enabled; Places/Routes and relevant IAM/monitoring APIs enabled. Run/registry/IAP/SecretManager/Compute/scanning were not in the enabled list. Run inventory failed `SERVICE_DISABLED`; repository listing failed an SDK `HttpException` reporting error. Neither establishes that resources do not exist. Six runtime identities were not observed. Plan/trial/credits/quotas, tester identities, OAuth state, storage contracts and registry URLs remain unknown. Six control-plane metadata commands were run; no provider data-plane request or secret read.

## Costs and first owner decision

[Public rates and exact assumptions](prices-2026-11-18.json), checked November18, are **not an account quote or approved budget**. USD,730hours, no assumed GCP free credits:

| Case | Infrastructure / month |
|---|---:|
| Proposed fixed charges even with zero users | **$63.26 + R** |
| Low use:10 aggregate vCPU-hours,8.5GiB-hours,10k requests,8 NAT assignments,1GiB processed | **$75.46 + R** |
| Planning case:100vCPU-hours,85GiB-hours,100k requests,12 NAT assignments,10GiB processed | **$95.72 + R** |

`R` is the **missing paid Redis regional quote**; no exact full total can honestly be quoted yet. Fixed amount budgets two separate $25 Supabase Pro organizations/Micro credits, two IPv4 add-ons, one static NAT IP,18 active secret versions and5GiB registry. Existing operational plan may lower incremental cost only after account verification. Low-use/planning figures include separate logging/egress allowances; they are not hard billing caps. Provider, tax, security review and account-specific premium/scan costs are separate. Supabase direct IPv4 and NAT incur costs when idle.

For100outings, conditional canonical limits of4SearchPro +27MatrixPro elements give **up to$39.80 gross Maps**, before account-price validation; add **100×L**, where the qualified application LLM bound `L` is unknown. No Maps/AI grant is proposed for activation now. No inference or counting request is authorized.

**Smallest approval request — batch A1, not application deployment:** authorize enabling the listed Run/ArtifactRegistry/IAM/IAP/SecretManager/Compute APIs and managed Run/IAP identities; create one private immutable-tag Artifact Registry repository inus-east4 and six dedicated service accounts; publish at most six existing reviewed candidates (at most5GiB total) for private artifact/security review only. Proposed ceiling **$5 one-time metered setup/scans and $1/month registry storage**. Public gross storage estimate is$0.50/month; six initial vulnerability scans, if account-enabled at the published rate, are$1.56. Stop if account terms exceed these ceilings. No billing attachment/change, Cloud Run service, database, Redis subscription, NAT, secret value, tester access, grant or provider operation in A1. Do not enable paid scanning automatically. This batch does not produce a working URL.

Before approving the full real demo: obtain `R`, operational capacity, independent witness owner and actual terms, independent residual container-risk disposition (or an available verified fix), exact application model/count/rate/financial approvals and a genuine real-provider source cohort. Then authorize a finite resource and provider envelope; metadata alone is not that authorization. The shortest functional acceptance remains a private IAP URL → real qualified interpretation/clarification → genuine Places/Routes → ordinary cards/View Plan, Mac off, with financial/replay/restart checks. No claim of that acceptance is made here.

## Verification limits

[Machine-readable results](../../docs/task53-private-cloud-configuration-verification.json):48focused tests pass; frontend324/325pass with one unchanged expired-date fixture failure; TypeScript/ESLint pass. No actual browser, new image build/scan, full backend, managed SQL/Redis connection or hosted IAM/IAP/restart test was run in this configuration-only checkpoint. Existing critical/high findings remain visible (0critical/71high per Python role;0/66 frontend in the earlier inventory), not independently accepted or rescanned away.

Official references: [Cloud Run/IAP](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run), [signed IAP audience](https://docs.cloud.google.com/iap/docs/signed-headers-howto), [Direct VPC](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc), [secret volumes](https://docs.cloud.google.com/run/docs/configuring/services/secrets), [Run pricing](https://cloud.google.com/run/pricing), [NAT](https://cloud.google.com/nat/pricing), [registry](https://cloud.google.com/artifact-registry/pricing), [scans](https://cloud.google.com/artifact-analysis/pricing), [secrets](https://cloud.google.com/secret-manager/pricing), [Supabase](https://supabase.com/pricing), [IPv4](https://supabase.com/docs/guides/platform/manage-your-usage/ipv4), [Redis](https://redis.io/pricing/), [Maps](https://developers.google.com/maps/billing-and-pricing/pricing).
