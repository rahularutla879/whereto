> Follow-up: [closed frontend / immutable continuation](task52-closed-frontend-verification.md) records the latest bounded local result. All earlier observations and failures below are retained, including the unattributed assertion.

# Task 52 — authenticated network transport and private packaging

Baseline: `2c5bfcc651521639cb654b6e3940697b3cd880aa`. Implementation identity: `52-ordinary-authenticated-network-v1`; manifest SHA-256: `5640cd4c898f1f87c0e5ae04e03d77934d09a3e86be2b85a58d7befbec160f7d`. This report records local synthetic evidence, not hosted IAM, qualified AI, real provider accuracy or deployment approval. [Machine evidence](task52-production-service-packaging-verification.json).

## Outcome and acceptance boundary

Actual standalone Next.js → two FastAPI workers → native factory/issuer → counter/dispatcher/recovery now uses HTTPS clients rather than a frontend Docker-exec driver. The existing ordinary UI and planner are reused. The frontend has no Docker executable/socket, SQL/Redis login, issuer/recovery key, IAP signing key or test-controller ingress credential. Original ordinary source handles, deterministic pending clarification, original expiry/revision, confirmed execution controls and single-use generation remain unchanged.

**The complete privately deployable startup objective is not satisfied.** The reusable clients and frontend artifact are implemented and locally exercised. The full protected authority still has deliberate synthetic-only constructors, fake provider/counter/rate profiles and a process-local dispatch callback. No safe hosted factory can be assembled simply by changing URLs. The inert startup contract explicitly says `launchable:false`; no bypass, environment-ready flag or unsafe privileged image was added. This is a bounded partial implementation with a concrete source-level blocker, not a claim that the application can now be deployed privately. Conditional commit/push requires the full checkpoint acceptance decision; uncommitted status is disclosed below.

## Existing architecture audit

| Layer | Before this change / retained constraint | New result / remaining boundary |
|---|---|---|
| Browser | Existing private UI, memory-only handles, no raw-evidence authority | Unchanged components served by actual standalone Next image; no browser storage or provider permission added |
| Next server | `experiments/ordinary_ui/node_client.mjs` drove backend calls through test-controller Docker access | Test preload composes the existing identity port with `lib/server-https.ts`; actual requests use verified HTTPS; no Docker/controller secret in frontend |
| FastAPI replicas | Existing real request management and ordinary facade; old loopback client | New `ServiceClient` sends original signed bodies to exact configured URLs; no SQL/Redis/issuer privileges |
| Native factory/issuer | Actual source validator, reconstruction, SQL grants, encrypted evidence and planner; synthetic local connection factories | Same algorithms, new network client; native hosted connection/lifespan factories still missing |
| Counter | Separately authenticated role; fictional UTF-8 byte accounting and fictional pricing | Remains fictional; cannot authorize real hosted inference |
| Dispatcher | Checks canonical payload/reservation/epoch and calls factory admission callback | HTTPS retained, fake replies only; callback currently lives in factory process memory |
| Recovery | Separate witness database, role-specific epoch/nonce permissions | Preserved locally; hosted independent ownership and reconciliation not enrolled |
| Test control plane | Docker bootstrap/admin creates disposable resources | Still required to run local tests only; not an application transport or hosted image |

The local core keeps its frozen networkless/loopback security boundary. A test-only opaque TCP/Unix-socket conduit passes TLS bytes to it; it cannot read credentials, terminate TLS or mint authority. This adapter is not the proposed Cloud Run service mesh. Edge containers use a bridge with masquerading disabled and ports published only to host loopback. The frontend has a read-only synthetic config volume; there are no host bind mounts. No claim of owner-Mac independence is made by this local fixture.

## Implemented authenticated clients

- `private_runtime/https.py`: `Endpoint` permits reviewed HTTPS root origins only. `HTTPS` validates certificate and hostname with a TLS1.2 minimum, caps concurrency at four without an unbounded queue, enforces body/response bounds and an absolute transport deadline, and refuses redirects, non-JSON/non-200/truncated responses. There is no proxy, retry, alternate endpoint or plaintext fallback. Synchronous operating-system DNS may delay a caller beyond its deadline; no request is sent after a late connection completes. Hosted DNS behavior remains unverified. Connection slots/cache limits are per client instance, not fleet admission: hosted factories must retain reviewed long-lived clients and bound inbound concurrency; constructing a new client for every call is not a process-wide connection cap. The current fixture still reuses the old per-call client lifecycle, another reason not to claim a completed hosted lifespan.
- `private_runtime/service_client.py`: uses existing canonical JSON, exact original body bytes, signed audience/path/token/body proof, scoped IAP forwarding and downstream durable nonce checks. Only configured target/path pairs can be called. Workload identity does not replace native source/session/admission/grant/payload/dispatch/epoch checks.
- `private_runtime/google_identity.py`: dormant assigned-workload metadata adapter, fixed Google metadata path, exact audience, independently verified Google signature/issuer/subject/email/expiry, bounded cache and failure cooldown. It refuses fixture signing roots/tokens. No real metadata/JWKS requests were executed. Its positive fake-metadata unit test uses a trusted verifier stub; genuine Google-shaped signature/role failures are exercised by the existing downstream offline verifier, not claimed as real Google enrollment.
- `lib/server-https.ts`: server-only exact audience→endpoint map, five paths, manual redirect policy, 64KiB request bound, response bounds, four simultaneous requests and existing cancellation/deadline behavior. An actual oversized-response rejection exposed a socket error handling defect during development; explicit promise rejection plus clean socket destruction fixes it. No response-size assertion was removed.

The request flow remains: independently verified IAP user → frontend-owned workload token and signed bytes → independently verifying FastAPI → authenticated factory source ownership → current SQL/Redis/witness/admission → protected reservation → canonical single-use fake dispatch. Frontend→factory and backend→counter/dispatcher attempts are denied before accounting changes. Secret ownership remains separated as specified in [the inert role contract](../deployment/private-network-v1.json). Native callbacks/financial validators are not replaced by a network digest.

## Actual route matrix

| Frontend route | Behavior in the local selected profile |
|---|---|
| `GET /api/health` | Process liveness only; no provider call |
| `GET /api/planning-mode` | Authenticated bounded, non-billable dependency readiness; not full hosted readiness |
| `POST /api/interpret` | Actual ordinary source action and deterministic pending answers; owner-bound opaque handle |
| `POST /api/plans/generate` | Current owned source/control validation and existing ordinary planner through protected fake providers |
| `POST /api/private-ordinary/revoke` | Explicit source discard; no new provider operation |
| Advanced/options/pagination/origin discovery/provider Details/save/reopen/refresh/manual-only | Explicitly blocked, not made available by networking |

Cards' **local** View Plan / View details expand only existing synthetic snapshots. External Maps/credit links were not followed. Original Qwen flow, public DTOs, ordering, saved-plan schema/RLS and normal startup remain unchanged.

## Packaging and runtime identities

`deployment/prepare_network_context.py` projects explicit app sources/configuration into a fresh isolated build directory. It does not broaden the frozen root `.dockerignore`. Tests, experiments, private evaluation evidence, environment files, Git and fixture keys are excluded. `Dockerfile.frontend-network` retains the reviewed pinned Node base/dependencies/non-root user and builds actual standalone Next. The extra artifact exposes only closed `createGoogleIdentityPort` and `createHTTPSChannel` constructors, plus hashed files and an inert dependency contract. The fixture-only generic constructor/preload is not in the image.

Built Linux amd64 frontend image: `sha256:30b62fc51e8b4fa283dff2cddc13274d7b2355c29aa9ea198eb934bb61d6f586` (local tag `whereto-frontend:network-task52-v1`, 104746153 bytes). Actual test frontend runs as1000:1000, read-only, all capabilities dropped, no-new-privileges, 512MiB/1CPU, bounded tmpfs; authority roles retain existing smaller limits within the approved VM. The image's default command remains the existing refusing/normal startup entry, not a new hosted launch switch. No privileged production-role image was falsely manufactured around synthetic test constructors. Dependency locks and base digests are unchanged.

## Browser and network evidence

The final pinned cohort exercised actual independent services and the standalone container, not merely helper calls. Browser checks completed the original authored Coffee/museum request, pending date answer, explicit origin confirmation, generation of three provisional cards, correct order/date/area/mode, View Plan and local details, explicit discard and refresh to empty source/cards. The responsive viewport was independently measured at1280×900 and390×844; card layout was visually checked at both. No inference/provider accuracy is inferred from fixture success. Browser did not separately exercise all outages, other users, expiry, tab races or load-balanced trusted factory replicas; authenticated HTTP covers the listed refusal cases separately.

The unchanged thirteen HTTP cases cover owner/revision/build/expiry and payload refusals, deterministic pending flow, source/control edits, duplicate generation, financial exhaustion, SQL/Redis/witness failure and unsupported paths. Four new network cases check frontend privilege exclusion, full flow with no extra inference for a pending answer, forbidden role calls and loss of factory/dispatcher connectivity in non-billable readiness. TLS unit tests additionally reject wrong hostname/root, redirects, malformed endpoints, oversize and truncated responses, cancellation/deadline/capacity errors. No response is automatically retried.

## Measured local latency

The final measured three-request synthetic flow took **53849.354ms** controller-inclusive, including fictional tester setup and read-only count queries. It created four new fake operations, one inference; the date answer did not increase inference count. This is a single flow in an emulated amd64 VM with2CPU/4GiB, not cloud latency or an SLO pass. Inclusive nested spans overlap and must not be added.

| Stage | Samples | Median ms | p95 ms |
|---|---:|---:|---:|
| Frontend identity |3|2.200|2.586|
| Frontend TLS connect |3|9.145|181.942|
| Frontend HTTPS total |3|10755.134|31395.365|
| Workload token verification |40|0.391|1.219|
| Service authentication including nonce |14|15.764|19.918|
| Public forwarding authentication |6|26.000|34.059|
| Session lookup |2|30.082|30.420|
| Redis read / write |32 /9|0.281 /0.638|1.756 /2.027|
| SQL statement |2052|0.241|80.453|
| Independent witness protocol |71|1.878|21.215|
| Admission |3|1.109|7319.384|
| Reservation |4|1371.566|1440.014|
| Provider dispatch inclusive |5|1792.942|2216.636|
| Fake responder only |5|0.200|22.126|

No same-workload causal before/after baseline was established. Repeated protected database connections/checks and serialized orchestration need investigation before staging performance acceptance; do not remove checks or extend deadlines to obtain better scores.

## Reliability, resource and security findings

The inherited controlled SQL reliability cases are rerun unchanged: protected lock contention/invalid SQL produces expected sanitized `P0001`/`55P03` refusal and preserves conservative accounting. No recurrence in the measured2052 SQL statements. That does **not** identify or fix the earlier unexplained `database_protocol` incident. Existing deadlines were not raised; no refund/retry/fallback was added.

Source inspection found another concrete hosted blocker: `experiments/service_isolation/runtime.py` stores `PENDING` dispatch permits with a live `check_current` callback in one factory process. A dispatcher callback to a different factory replica or a restarted process will refuse. Network transport alone cannot make this durable. A reviewed exact-owner routing/draining or durable revalidation design is needed before Cloud Run overlap/scaling. Do not serialize callbacks, reconstruct admission from a digest, bypass `/dispatch-check`, or mark this locally single-factory result a multi-replica authority pass.

Resource creation is inventoried before each new cohort. Cleanup removes only exact created container/network IDs and proved-new mount names; no broad prune. The initial task baseline had116 unattributed anonymous volumes. A first failed development fixture left one additional anonymous volume without captured mount provenance; it was deliberately retained rather than guessed away. Subsequent cohorts start with117 and remove their proved-new Redis volume. An unattributed failed-constructor network is also retained if ownership cannot be proved. This resource leakage is disclosed, not counted as complete cleanup. No user data or original volume is deleted.

Actual image content and runtime checks exclude Docker/socket/owner paths, test credentials, private evidence and excessive privilege. No package/base update was made; existing unresolved image advisories are not suppressed or claimed fixed. The new frontend was rescanned with pinned Grype0.121.3 and a valid database built2026-11-12T06:20:58Z:213 matches (2 critical,49 high,80 medium,18 low,64 negligible). Compared with the retained209-match frontend report using the November11 database, the high/critical package/advisory set is unchanged and no match was removed. Added matches are glibc CVE-2026-100290(low) and CVE-2026-115819(medium), each across libc-bin/libc6 at unchanged2.36-9+deb12u14. This is consistent with the database update; it is not a same-database control rescan or exploitability certification. The prior security triage remains open and no patch is claimed. Backend OS scanning was not rerun because backend dependencies/image inputs are unchanged. The first scan correctly refused an unreadable0600 archive; only the disposable secret-free archive copy was made readable for the same non-root scanner. No scanner privilege/resource increase. Full comparison is in machine evidence. The exact dependency audit and configured-value scan results are in machine evidence. No real identity/provider/owner database call, financial grant, cloud resource or activation occurred. Historical ten attempts,324 files, corrections, source pins, accounting and halt are checked read-only before/after.

## Remaining deployment work and concrete next checkpoint

1. **Next source-level checkpoint:** implement/review separately versioned hosted native connection/lifecycle ports for actual restricted TLS PostgreSQL roles, Redis TLS/AUTH and independent witness without synthetic constructors or test clocks; include a finite dispatch-callback ownership/draining contract. Preserve frozen local algorithms/evidence and fail closed on missing admission. Test genuine independent service processes and overlapping factory revisions with fake providers. This is not provisioning or a reason to weaken guards.
2. Produce restricted authority/counter/dispatcher/recovery production-role image projections only after those ports pass; no fixture bootstrap, root role, fake signer or arbitrary Python module selection in hosted images.
3. Review real data privacy/retention, independent recovery/restore ownership, IAM/IAP/Secret Manager enrollment and finite grants/root/timezone, then qualify a cloud LLM and its real complete-payload token/pricing policy. Proposed staging financial amounts remain unapproved.
4. Only after separate account/security/cost approvals: actual private resources, migration and native ordinary rollout; verify Mac-off, private IAM/IAP, failures, performance, cost and quality before any public launch recommendation.

Task52 remains in progress. Task53 is not started. This report does not authorize subsequent work automatically.

## Local reproduction (not a deployment command)

From `/Users/rahularutla/Documents/whereto`, with the already approved dedicated Colima profile running, create a fresh temporary build context and use only a local image tag:

```sh
context_parent=$(mktemp -d /tmp/whereto-network-build.XXXXXX)
python3 deployment/prepare_network_context.py . "$context_parent/context" > "$context_parent/sources.json"
docker --context colima-whereto-task52 build --platform linux/amd64 -f "$context_parent/context/deployment/Dockerfile.frontend-network" -t whereto-frontend:network-task52-v1 "$context_parent/context"
```

The test runner deliberately requires an inspected exact image identity rather than assuming the tag. This read-only projection writes no credentials:

```sh
python3 - <<'PY'
import json, subprocess
from pathlib import Path
image=json.loads(subprocess.check_output(['docker','--context','colima-whereto-task52','image','inspect','whereto-frontend:network-task52-v1']))[0]
assert image['Architecture']=='amd64' and image['Os']=='linux' and image['Config']['User']=='node'
Path('/tmp/network-image-identities.json').write_text(json.dumps({'frontend':{'id':image['Id'],'architecture':'amd64','os':'linux','user':'node','size':image['Size']}}))
PY
PYTHONPATH=. backend/.venv/bin/python -m experiments.ordinary_network.run_local
```

`--browser` additionally pauses the local runner for a bounded manual review and writes only a loopback URL to `/tmp/whereto-network-ready.json`; create `/tmp/whereto-network-browser-done` when finished. Never use these test entry points, offline identities, bootstrap routines or synthetic volume mounts as a hosted startup command. Review the exact source manifest first. The source verifier refuses changed frozen parents; do not repin them to make a test run.


## Acceptance disposition

| Criterion | Local evidence / disposition |
|---|---|
| Ordinary Next/FastAPI through authenticated network clients | Passed with synthetic dependencies and actual standalone container |
| No Docker-administrator access in frontend/worker request path | Passed; Docker remains test-control-plane only |
| Safe source-pinned private startup composition | **Incomplete**: inert refusal contract and frontend component only; hosted native authority factories/role images/dispatch-callback portability missing |
| Financial/evidence/ownership/replay/recovery preservation | Existing protected path exercised; no changed accounting algorithm or claim of all parent failure drills rerun |
| Network failures/restarts | Tested bounded TLS/client failures, readiness disconnection, backend/factory restart and storage/witness outages; hosted factory-replica overlap remains blocked |
| Ordinary UI and blocked unsupported routes | Passed actual pending/generation/cards/discard/refresh; no new product semantics |
| Image privacy/privilege | New frontend image checked; full privileged hosted role cohort not built |
| Complete hosted verification | Not established; IAM/IAP/private networking/qualified model/real grants remain unavailable |

Because complete startup acceptance is unmet, no commit or push is represented as checkpoint completion. Verified source, tests, documentation and exact evidence remain in the working tree for review. HEAD remains the supplied baseline. This is not a clean-tree/completed-deployment claim. No permission is inferred to provision or start the next checkpoint automatically.

## Exact completed verification

| Suite | Passed | Skipped | Scope |
|---|---:|---:|---|
| New Python HTTPS process tests |7|0|CA/hostname, exact bytes, truncation, bounds, deadline/capacity |
| Selected current backend modules |263|16|279 discovered in17 named modules; interpretation, admission, budgets, ordinary/advanced, privacy/saved contracts and recorded27 Qwen/seven OpenAI replays |
| Frontend suite |315|0|Includes two new actual Node HTTPS process tests |
| Existing packaging/startup/artifact/resource tests |15|0|Normal existing refusal boundaries |
| Existing TypeScript identity proxy |3|0|Server-only forwarding, cancellation and no fallback |
| Existing public JSON validation |2|0|Duplicate/nonfinite/deep/malformed input refusal |
| Final pinned network application cohort |30|0|4 metadata protocol stub units +3 clock +6 UI authority/SQL +4 network +13 unchanged ordinary HTTP |
| Unchanged signed hosted-identity cohort |20|0|10 token/JWKS units +10 actual process ownership/role/replay/restart/store/epoch cases |
| **Unique automated cases** |**655**|**16**|No full-backend claim; duplicate development reruns not added |

TypeScript, ESLint, native production build, Python dependency consistency, source manifests and configured credential scans pass. Initial lint/import/IPC/fixture failures and one intentionally interrupted pre-final API cohort remain documented in machine evidence. The removed three dummy startup tests are excluded from totals. Full backend discovery/33 immutable historical headings and standalone parent112 authority/evidence,30 grant,17 native and12 service-isolation cohorts were not rerun; their paths are exercised by the current selected application cohorts without claiming every parent drill completed.

Actual normal Linux amd64 images rebuilt and `deployment/container-smoke.sh` passed. The frontend terminates143 after SIGTERM cleanup; backend terminates0, neither OOM nor SIGKILL. Existing receipt replay refuses after process-state loss. This smoke's inherited isolated test-mode mock is not a production-hosted startup test. The new network component image's own default startup exits78 without configuration. Its non-root source/artifact/excluded-path audit passes. All image tags remain local.

The public npm audit completed with **seven moderate development-tooling matches, zero high/critical**, exit1 as expected for advisories; it is not a vulnerability-free dependency result. They are the existing minimatch `GHSA-g3hv-75wg-m249` advisory and dependent TypeScript ESLint tooling matches. No dependency changes or forced audit fix. The first sandbox DNS audit attempt failed; the later authorized public advisory query succeeded. Configured application values(2) and evaluation values(3) have zero current/history matches. Before/after real journal/file digests match exactly, including $0.047366625 accounted, $11.952633375 remaining and active halt.

Final resource state: zero running containers; all proved-owned cohort containers/volumes removed.117 original/unattributed volumes and one unattributed bridge were retained. The dedicated `whereto-task52` VM was stopped after verification; its2CPU/4GiB/40GiB configuration was not increased. Journal/private-file digests were rechecked after cleanup and remain identical. Full diff, new source/artifacts, handbook preservation, file links, JSON and known-credential scans were reviewed; no unrelated tracked implementation, dependency, frozen source or historical record changed.

## Preserved-work continuation

The additional hosted connection, exact-owner routing and role-image candidate is documented in [the continuation report](task52-private-role-continuation.md) and its separate verification. Earlier results and source identities above are historical cohorts, not authorization for the derived images. Combined acceptance remains open; no commit/push or deployment readiness is implied.


## Subsequent closed-entry / immutable verification continuation

The preceding results and open gates are retained as historical development evidence. See [the closed frontend continuation](task52-closed-frontend-verification.md) and its machine-readable record for final artifact identities, exact browser/crash checks and remaining hosted blockers. The original assertion remains unattributed; no frozen financial/evaluation record is reclassified.
