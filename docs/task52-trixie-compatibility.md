# Task 52 — isolated Debian 13 and Next.js compatibility candidate

Run: November 16–17, 2026. Baseline clean main: `6c2c5d0ed49a9e8fc66ece45531628b267067475`.
[Exact image identities and runtime versions](../deployment/candidates/trixie-v1/images.json) · [source cohort](../deployment/candidates/trixie-v1/cohort.json) · [full verification, per-advisory/package comparison and vendor status](task52-trixie-compatibility-verification.json).

## Decision

**Local technical compatibility passed; no promotion or security acceptance.** The existing six responsibilities run using supported official Debian 13 bases, preserving Python 3.12 and Node 24. All application code, original Bookworm images/manifests, root application/Python locks, financial SQL and historical source pins remain intact. No provider, cloud, grant, credential or public-traffic activation occurred.

Trixie removes all scanned critical matches but introduces unresolved high findings. It is ready for a separately scoped security/promotion decision, not an unqualified deployment recommendation. Normal builds/startup continue using the original inputs.

## Exact isolated build

Official Docker Hub metadata and pulled amd64 runtimes were checked:

| Runtime | Pinned multi-platform reference digest | amd64 digest | Actual version |
| --- | --- | --- | --- |
| python:3.12-slim-trixie | `5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b` | `05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177` | Python 3.12.16, Debian 13.7, glibc 2.41, OpenSSL 3.5.7, SQLite 3.46.1 |
| node:24-trixie-slim | `af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0` | `60587baa7c895cf438d44f691e4ac8248b36c13b26be77332f874bebb3a64201` | Node 24.22.3, Debian 13.7 |

[Official Python metadata](https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim-trixie), [official Node metadata](https://hub.docker.com/v2/repositories/library/node/tags/24-trixie-slim). No unsupported custom Python runtime, OS package purge, compiler installation, source-built replacement libc or major language/framework upgrade.

`prepare_trixie_candidate.py` wraps the existing role and closed-frontend projectors. It refuses an existing/in-repository target, changed parent cohort, non-pinned base, enabled promotion/provider flag or unrelated Next lock update. It derives a separate cohort `8e94732c63d46df3ebc550e13a7daa4018a8ff67ab8150c036264f7e5824a479` from unchanged application output bytes. Normal `private-role-cohort-v1.json` stays `53c8a313…`; none of the candidate artifacts is selected by ordinary startup. [Reproduction instructions](../deployment/candidates/trixie-v1/README.md).

Built five Python roles and three frontend controls/candidates:

| Role/variant | Local image digest |
| --- | --- |
| Backend | `37f670a2a4e75260033dfeb86615c34a90b422ea3d0c7fa408852d3dc5334252` |
| Factory/issuer | `1bb4343140ac88e00c9a798b1766a63e75e1b7dde8e5ca159fcae6746ebdd588` |
| Counter | `e34061d8247d51d303a06a6cdfcca7a792152877c147bf1cbbd5a9cdf91b2b86` |
| Dispatcher | `5d431643ea4df3ec163c0565fc2453b3472b83a6b57d544689e857d53a56e77f` |
| Recovery | `5a8da13cd12af12095d3b4fc8cf6aa051ee6157adb43b0377b3b1a4ff9b8ff38` |
| Frontend: Trixie + Next 16.4.5, combined candidate | `70e45bfde6826e137c9fc99599dd6aa54bedcb0324bc40cdb9b74ada4e715570` |
| Frontend: Trixie + unchanged Next 16.4.2 | `43be74f68e6b89429c6f39dce65d5c6c78a581e6f90afe0f29f4d6385740e8be` |
| Frontend: Bookworm + Next 16.4.5 only | `124b456d07d2cdc15b302a7ed5d3e11338985c43aa737d0b363b470e44f3fc74` |

All IDs use `sha256:`; tags and exact source/lock hashes are in the candidate inventory. A ninth, separately tagged `LOCAL_FIXTURE=true` frontend was built solely for offline browser testing and is explicitly ineligible for promotion. It contains no signer or operator credentials. Production-candidate frontend artifacts have `FIXTURE=false` and exclude the fixture module.

## Same-database security result

Fourteen scans used Grype 0.121.3 pinned at `13113eeceab017260370cf540e1d25442c59665fd07d1b09b66d63bb0c282887`. One DB was downloaded once, then network/update disabled for every subsequent scan; schema v6.1.10, built `2026-11-16T06:30:54Z`. Exact archive/checksum and raw output hashes are recorded. All scans exited 0; no suppression or exclusion.

| Final runtime | Bookworm critical/high | Candidate critical/high |
| --- | --- | --- |
| Each of five Python roles | 3 /86 | **0 /61** |
| Frontend Trixie, either Next version | 2 /53 | **0 /60** |
| Frontend Bookworm, Next-only patch | 2 /53 | **2 /53**, unchanged |

The Python change removes 59 binary/advisory associations and introduces 31, leaving 61; frontend removes 29 and introduces 34, leaving 60. These comparisons intentionally separate package version transitions, binary/package renames and advisory identities. Python's 16 disappeared C/H advisory IDs are **not 16 independently proven vulnerability fixes**. Three new advisory IDs appear: **CVE-2026-76642, CVE-2026-78408 and CVE-2026-78409**, all util-linux. They create 27 source-package matches across nine utility/library package records. Current Debian Trixie 2.41.5-0+deb13u1 remains vulnerable. Other added associations reflect additional package records, not new CVE identities.

Confirmed important vendor fixes in installed packages:

- glibc `2.41-12+deb13u4`: CVE-2026-5450 fixed; removes both critical libc associations. CVE-2026-5928 also has fixed Trixie status.
- SQLite `3.46.1-7+deb13u2`: CVE-2025-7458 fixed; removes Python's third critical match. CVE-2026-11824 has fixed Trixie status; other SQLite high findings remain.
- PAM `1.7.0-5`: CVE-2025-6020 fixed. Gzip and older util-linux advisories also have fixed Trixie release rows; exact installed packages and vendor evidence are in the record.

[Debian glibc advisory](https://security-tracker.debian.org/tracker/CVE-2026-5450), [SQLite advisory](https://security-tracker.debian.org/tracker/CVE-2025-7458), [new util-linux advisory](https://security-tracker.debian.org/tracker/CVE-2026-76642). Thirty-five current official pages were fetched and hashed.

Some findings disappear because the official base no longer includes distro libtasn1/Kerberos packages. That is not an installed vendor patch. **Psycopg-binary 3.3.3 still bundles identical Kerberos/OpenSSL/LDAP library bytes on both bases**; libpq reports 18.0. No new wheel was substituted. Their component/version-to-advisory mapping remains unresolved, so zero scanned critical matches is not proof every native dependency is fixed. Current Grype also continues associating CVE-2026-76844 with zlib while Debian describes webpack-dev-middleware; that conflict is retained, not suppressed.

The 61 consolidated candidate package/advisory rows cover 19 CVE IDs and eight source-package families: glibc, SQLite, zlib, Perl, ncurses, ACL, GCC 14 runtime and util-linux. Per-row version, affected role, vendor status, required-use assessment and uncertainty are recorded. libc/native ABI libraries are required. Perl/terminal/mount utilities have no identified application business flow, but belong to the supported upstream base/dependency set; no arbitrary essential-package removal was attempted. Metadata-only/source-package associations do not establish affected function execution.

New util-linux risks involve privileged mount hooks, nsenter cgroup descriptors and subdirectory mount/symlink behavior. Local runs verified non-root, read-only root/application files, CapEff 0, CapBnd 0 and NoNewPrivs 1. These constrain prerequisites but are **not independent unreachability findings or accepted exceptions**. Hosted kernel/platform enforcement is unverified. The frontend's higher high-count is an explicit tradeoff requiring disposition, not hidden by the critical-count reduction.

## Separate Next.js patch

The [vendor advisory](https://github.com/vercel/next.js/security/advisories/GHSA-mfr8-8qww-v76h) fixes GHSA-mfr8-8qww-v76h in 16.4.5. The isolated lock changes only 11 Next/env/SWC records from 16.4.2. Normal root package files remain unchanged. A clean Linux npm proposal also reorganized unrelated optional-WASM metadata; those changes were rejected, the exact Next entries reviewed/merged into the original lock, and actual npm ci/production builds validated the result.

Patched-tree npm audit: **seven moderate development-tooling matches**, zero high/critical, versus eight moderate before. The Next advisory no longer appears. No force update or broad dependency upgrade. Grype C/H counts are unchanged between Next controls because these retained C/H findings are distro package records.

## Functional evidence and limitations

- Three new overlay tests pass: exact patch/disabled state, byte-identical projected application code/new identity and refusal of unrelated updates. Twelve packaging/artifact/overlay tests pass in total.
- Focused provider/planner/admission/dispatch/projection cohort: 175 passed on host, then the same 175 passed in the actual Trixie factory venv with a read-only external source-test volume and no network. This test-process environment is separate from application startup; no testing override was used to claim production startup readiness.
- Eight production candidates/controls passed actual version/native import/crypto/SQLite, amd64, source inclusion, non-root/read-only/capability checks. All refuse missing enrollment with exit78. Every Python build's selected hash lock/pip check passed. No extra compiler, package manager or fixture bootstrap was added to runtime.
- Eleven existing hosted-connection cases passed, covering TLS/hostname validation, exact restricted SQL roles, transaction reset/pool reuse, permission denial, Redis TLS/AUTH/CAS/expiry and revocation. Four identity-port cases passed. The bootstrap client is the old controlled fixture; actual Trixie processes independently used these TLS ports during the application flow.
- Immutable multi-process flow passed on two candidate backends, two candidate factories, counter, dispatcher and recovery, plus the candidate-based test-only standalone Next frontend. It exercised two outings, cross-user refusal, cross-replica deterministic clarification with no added inference, generation, duplicate/unsupported-route/forged-workload refusal and encrypted evidence/financial reservation/dispatch.
- Actual desktop 1280×900/mobile 390×844 browser: interpretation→pending date→confirmed authored origin→three provisional cards→View Plan/local details/credits. No mobile horizontal overflow; all three official logos loaded. Discard/refresh left operation count 9→9. These are fictional providers/identities, not model or Google quality evidence. Two separately authenticated human browser users and exhaustive browser outage permutations were not exercised.
- Immutable post-browser interruption/restart passed: 6,845 synthetic units, one INTENT, zero deliveries; old action refused after factory restart. The loaded assertion/source manifest stayed unchanged. This passing run does not retroactively explain older unattributed observations.
- Next 16.4.5 frontend suite: 324 passed, **one unchanged expired-date fixture failure**, zero skips. No historical test/source pin was changed. TypeScript, ESLint and dependency consistency passed.

Retained development errors: host npm lock layout rejected; duplicate null npm config rejected; copied-file permissions refused; unrelated WASM changes rejected; a direct docker-cp into readonly test container refused before tests (resolved using the existing readonly-volume pattern); one diagnostic import-order error and empty upstream metadata handling corrected. None required application, SQL, deadline, attestation or security-guard changes.

No full-backend/full direct 30-case grant suite/frozen evaluator replay is claimed. SQL code did not change; actual protected dispatch/replay/crash was exercised. Live provider/model/count/account calls, hosted IAM/IAP/capacity, backup ownership and cross-version active-session migration remain untested. Source-version changes must not reset financial exposure or silently migrate old tickets.

## Remaining deployment decision

Technical compatibility supports **separate review of these exact candidates**, not automatic promotion. Resolve/dispose the 19 remaining scanned advisory IDs, the three new util-linux issues, scanner conflict and unchanged bundled-library mapping before accepting real-credential/data exposure. A supported vendor patch or a separately reviewed minimal runtime may reduce these further; do not purge packages or accept a score-only exception. Any promotion must explicitly update selected digests/Next lock/new cohort enrollment while retaining financial scope/history and rejecting incompatible old sessions.

Final read-only checks preserved all ten attempts (OpenAI 7/Google 2/Anthropic 1), $0.047366625 accounted, $11.952633375 remaining, 324 private files and persistent halt. Configured-secret scan found 0 matches. All original image IDs and exactly 126 pre-existing volumes remain; no task containers remain, and the dedicated 2CPU/4GiB/40GiB VM was stopped. Root Dockerfiles, selected manifests, application/Python locks, protected SQL and frozen sources were reviewed unchanged. All 20 handbook chapters remain; 4/14/15/18 updated, 11 reviewed unchanged because Google handling did not change.

Real deployment still separately requires qualified cloud inference and verified costs/counts, scoped provider/secret enrollment, explicit financial grants, permitted Google content recovery/attribution and approved infrastructure. No new architecture, Google retention permission, model decision, grant, cloud resource or Task53 work was introduced here.
