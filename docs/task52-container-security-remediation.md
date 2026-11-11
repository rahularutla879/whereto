# Task 52 — bounded container security remediation

November 11, 2026; clean baseline `ce0ec0f7f2e686c390709c680a385fd70f084265`. Local containers only. No cloud deployment, registry publication, real providers, financial authority, database migration or Task 53.

## Verified baseline and current evidence

The original saved reports match their recorded SHA256 values in [prior security evidence](task52-local-container-security.json): backend **289 matches / 3 critical / 78 high**, frontend **209 / 2 / 49**. These are package/advisory matches, not confirmed exploits. Original scanner: official Grype `v0.121.3`, digest `sha256:13113eeceab017260370cf540e1d25442c59665fd07d1b09b66d63bb0c282887`; database built `2026-11-10T06:21:20Z`.

The same versioned official scanner digest was reverified. All three new scans used the same valid database, built `2026-11-11T06:21:32Z`, in bounded non-root ephemeral containers without Docker socket, credentials or host binds. Only the public advisory database was downloaded; local application images were not uploaded. A control scan of the original backend separates database changes from remediation:

| Image/cohort | Total matches | Critical | High | Medium | Low | Negligible | Unknown |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original backend, November 10 DB | 289 | 3 | 78 | 104 | 18 | 86 | 0 |
| Same original backend, November 11 DB | 351 | 3 | 86 | 124 | 18 | 86 | 34 |
| Patched backend, November 11 DB | 347 | 3 | 82 | 124 | 18 | 86 | 34 |
| Original frontend, November 10 DB | 209 | 2 | 49 | 78 | 16 | 64 | 0 |
| Unchanged frontend, November 11 DB | 209 | 2 | 49 | 78 | 16 | 64 | 0 |

The backend database delta adds two Kerberos high advisories across four binary packages (8 matches), five medium advisories across those packages (20), and unknown-severity Kerberos/OpenSSL records (34). **Unknown is not benign or suppressed.** These packages did not change. The controlled old/new backend comparison removes exactly four high pyasn1 advisory IDs and adds zero package/advisory identities. [Exact comparisons and identities](task52-container-security-verification.json).

## Complete high/critical triage

[Machine-readable triage](task52-container-security-triage.json) maps all **132 original high/critical matches plus eight fresh-database high matches** to **35 individually assessed advisories**. Each finding names the image, installed package/version, runtime presence, source package, scanner fix availability, current Debian release status and exposure assessment. Shared CVEs across libc/libkrb5/util-linux binary packages are linked rather than represented as independent exploit mechanisms. All findings were in the merged baseline runtime; none is dismissed as build-only. pyasn1 has a new patched runtime version; other affected package versions remain.

Source review covers the actual image file manifest, FastAPI/typed requests, SQL connection contract and Google transports, plus owned frontend code. This is a bounded source/feature assessment, not an exhaustive native call graph or independent exploitability certification. No exploit was attempted. Application text enters JSON/runtime parsers, so unknown transitive native paths remain explicitly unknown.

| Family | Actual exposure and decision |
|---|---|
| glibc | Both images load libc. No owned scanf `%mc`, deprecated DNS printer, strfmon or wide-stream interface was found; those exact native paths remain unproven. HTTP inputs cannot set locale environment or install gettext catalogs. `CVE-2026-5450` remains open for Bookworm; [Debian](https://security-tracker.debian.org/tracker/CVE-2026-5450) lists a fixed newer-release package, not a compatible Bookworm patch. Some description ranges conflict with installed versions; these are unresolved applicability questions, not waivers. |
| SQLite | Backend actually has SQLite 3.40.1, FTS5 and session features enabled. Owned runtime code does not import sqlite, accept arbitrary SQL or upload/open user database files. The historical journal is absent from images. The critical [ORDER BY issue](https://security-tracker.debian.org/tracker/CVE-2025-7458) and FTS5/changeset highs remain vulnerable-library findings, not disabled-feature fixes. |
| Kerberos | Libraries are present with native SQL dependencies, but no KDC/kadmind/GSS acceptor or GSS-RPC client endpoint is implemented. SQL is restricted password/TLS, OAuth is HTTP. Client linkage does not prove reachability of the newly disclosed GSS-RPC client issue; native uncertainty remains. No fixed Bookworm package is listed. |
| util-linux / ACL | The app does not mount, probe disks, process fstab or modify ACLs. Setuid mount helpers **are still present**. Observed non-root, no-new-privileges, no capabilities, read-only root and no host/device binds constrain the local privileged-path prerequisites; they do not patch the packages. Any future runtime must retain these controls and separately review remaining helpers. |
| GCC/libstdc++ | Native Node/Python dependencies can use allocation/C++ libraries. No owned heap priority-queue `erase_if` operation was found, but native reachability is not proven absent. Large-allocation input limits help but are not a library fix. |
| gzip / ncurses / Perl | No owned gzip CLI/archive processing, terminal analysis or Perl formatting path. `infocmp` is installed. Standard inspected Perl paths lack Pod::Text/Archive::Tar modules; retain source-package matches with that limited feature evidence, not a patched claim. |
| libtasn1 / zlib | libtasn1 is distinct from Python pyasn1. No direct owned call to its expansion function or zlib gz-file-write APIs. HTTP compression can use zlib, which is not proof of the particular write-error path. Native reachability/version-range discrepancies remain unresolved. |
| pyasn1 | Indirect auth/ASN.1 dependency may consume certificate/key material in authorized authentication flows. No direct ASN.1 endpoint is required to justify patching; do not dismiss it because providers are currently gated. Official patch implemented below. |

Every retained OS advisory is still **open in current Bookworm tracker data**, including those labeled no-DSA/won't-fix. Those labels are scheduling/status information, not proof of safety. Both official Bookworm image tags still resolve to the exact existing digests. There is no evidenced compatible updated base/package set to select here. Pulling newer-release libraries into Bookworm or silently switching to Trixie would broaden the OS/ABI change and is not done.

## Implemented compatible patch and dependency identity

New deployment dependency identity: **`52-container-security-dependencies-v1`**. Base identities remain:

- Node: `node:24-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9`.
- Python: `python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df`.

Only deployment `pyasn1 0.6.4 → 0.6.5` changed. The official PyPI universal wheel hash is `4017b0fce125096b8573b39c989fdb1a4b19cf761e683398184550fea0e66587`; downloaded bytes matched. It supports Python >=3.8, including pinned 3.12. Complete installed chain:

- `google-auth 2.41.1` requires `pyasn1-modules>=0.2.1` and `rsa>=3.1.4,<5`.
- `pyasn1_modules 0.4.2` requires `pyasn1>=0.6.1,<0.7.0`.
- `rsa 4.9.1` requires `pyasn1>=0.1.3`.

The patch satisfies all constraints. Builder now executes **`pip check`**, which passed. Actual non-root final-image imports and a constructed BER string regression passed; isolated patched-wheel host tests also passed BER/DER roundtrip and the existing application/transport regressions. The [upstream 0.6.5 release](https://github.com/pyasn1/pyasn1/releases/tag/v0.6.5) explicitly fixes all four reviewed quadratic-decoding advisories. The fresh same-DB image comparison confirms exactly those four are removed; this is evidence of a versioned upstream patch, not merely fewer scanner matches.

`backend/requirements.txt`, B1/B2 manifests and paid-evaluator source pins remain byte-for-byte unchanged. That file describes historical/local evidence, not this new deployment dependency profile. The Linux deployment lock carries the exact single security override; its test checks the historical file SHA, every other version and the new wheel hash. No generic override/fallback was introduced. Existing local venv and frozen historical environments are **not** claimed patched or retroactively requalified. New source/lock/build hashes are recorded separately in verification; the new deployment profile grants no planning or paid-dispatch authority.

## npm moderate advisory decision

The seven findings are one minimatch denial-of-service chain through the development lint tools, absent from merged runtime images. Developer-controlled globs/repository input still matter; this is not automatically harmless. Upstream [advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249) requires minimatch >=11.0.1. A bounded typescript-eslint 8.72.0→8.72.2 trial still required `minimatch ^10.2.2`; it did not resolve the advisory and was restored completely. Final package.json/package-lock are unchanged.

No forced audit fix, whole-tree update or major transitive override was retained. Owner decision: separately approve a scoped minimatch10→11 override and API/behavior compatibility review, or use a future upstream lint cohort supporting the fixed range. This is a build-toolchain decision, not a framework/model upgrade. Seven moderate findings remain recorded.

## Functional, privacy and historical verification

Both actual Linux amd64 images rebuilt and the existing full container smoke passed: non-root, read-only root, dropped capabilities, no published ports/host binds, expected production refusal, frontend/backend health/proxy, unavailable AI503, missing SQL503, denied diagnostics, graceful shutdown and old-receipt409 after restart. Scheduled Docker HEALTHCHECKs also reached healthy. No installer/build tools were added back to runtime. Existing Qwen/legacy interpretation and V5.1 default-OFF behavior are unchanged.

Completed: 7 packaging tests; 121 backend passes /16 opt-in skips across 137 tests under the isolated patched universal wheel; 289 frontend tests; TypeScript, ESLint and the Linux production build (unchanged cached frontend build stage) passed. No full backend discovery or browser test claim. Original source requirements were not installed over or modified. Mocked transport diagnostics named `provider_dispatched` are synthetic test counters, not real Google sends.

Image layers were rechecked for configured secrets and forbidden private/evaluation/fixture files; zero matches. This is not proof about unknown secrets. Original read-only journal inspection before/after matched: OpenAI7/Google2/Anthropic1, ten attempts, $0.047366625 retained/$11.952633375 remaining, original SHA256/corrections/324 private files/persistent halt unchanged. No real database/provider operations or authorization changes occurred.

The approved Colima profile remains 2 CPUs/4 GiB/40 GiB data with no host mounts or SSH forwarding; no resource increase. Task containers were removed and VM stopped after verification, with only local images retained. Nothing was published.

## Next exact owner decisions

1. Review the retained findings, native reachability uncertainty, unknown-severity OpenSSL/Kerberos records and runtime privilege requirements. No waiver is issued here.
2. If broader OS remediation is wanted, separately approve an explicit Debian-release/base proposal while retaining Node24/Python3.12 unless independently justified. Review ABI/native wheel compatibility, glibc/SQLite fixes, rebuild, scan and run regressions; do not mix distribution packages or compile ad-hoc patched system libraries here.
3. Decide whether to approve the scoped minimatch major override or await an upstream compatible lint update. Preserve frozen evaluation identities in either case.

Hosted inference qualification, shared session/replay/financial authority, workload/private-backend authentication, trusted origins and explicit provisioning/spend permission remain additional hosting blockers. No architecture redesign or Task 53 work is included.
