# Task 52 — actual local container verification

Later checkpoint: [bounded security remediation](task52-container-security-remediation.md) patches pyasn1 in a separately identified deployment profile. Original findings and measurements below remain historical evidence, not current results for that new profile.

Date: November 11, 2026. Repository baseline: clean `62f8e6efb26dcfec6c19d45e788c8d5faf0f3c31`. This follows the owner's explicit installation/Rosetta-license/VM approval. This is local packaging evidence, not cloud deployment, hosted AI qualification or production activation. Earlier [packaging evidence](task52-cloud-deployment-verification.json) remains unchanged as the pre-engine checkpoint.

## Installed environment and isolation

Verified macOS 27.0.1, Apple Silicon arm64, 16 GiB physical RAM, hardware virtualization, Homebrew and approximately 238 GiB available host disk. Swap was already approximately 8 GiB used before installation. Installed Colima 0.10.3, Docker CLI 29.9.3, Buildx 0.38.2 and dependency Lima 2.3.0; Apple Rosetta installation completed successfully. The Buildx symlink destination was checked first and was absent; nothing was overwritten. No Docker Desktop, subscription, login service or cloud resource was created.

Dedicated profile `whereto-task52`: **2 CPUs, 4 GiB memory, 40 GiB container data disk**, native arm64 Linux VZ VM with Rosetta. Colima additionally supplies its standard 20 GiB sparse root disk; the approved `--disk 40` controls the container data disk, not that standard root filesystem. No allocation was increased. Host mounts are `null`, SSH agent forwarding and SSH-config modification are disabled, and auto-activation is false. Personal SSH/ADC/configuration and protected evaluation evidence are not mounted into the VM. Docker build sends only the filtered context.

The exact original pinned Python base executed `Linux x86_64` with `--platform linux/amd64 --network none`. Both application images report `linux/amd64`; actual frontend and backend processes ran under Rosetta. No architecture fallback or dependency replacement was used. The initial builder listing advertised only native platforms, so actual execution/build was checked rather than treating that listing as proof of amd64 failure. The default host Docker context was not changed: commands explicitly use `colima-whereto-task52`.

## Actual builds and runtime checks

Both existing Dockerfiles built successfully. The backend installed the reviewed Linux amd64 CPython 3.12 wheel hash lock with `--require-hashes`. Frontend `npm ci` and the full production Next build/TypeScript/static generation succeeded inside the pinned Linux image. Base digests, package lock, backend dependency lock and application sources were not modified. Following scan evidence, only inherited package installers were removed from the final runtime stages; build-stage installation remains unchanged. Local tags only; no registry publication.

The original smoke passed first. The strengthened `deployment/container-smoke.sh` then verified:

- Non-root users (`app` backend, `node` frontend), non-privileged execution, read-only root filesystems, dropped capabilities and no published host ports.
- Expected backend production-startup refusal and frontend missing-configuration refusal, both exit 78. No guard bypass.
- Existing test-mode backend startup and real standalone frontend startup, health and frontend-to-backend HTTP over an isolated shared network namespace. Separate actual Docker HEALTHCHECK probes reached `healthy` for each final image; runtime identities were `10001 Linux x86_64` and `1000 linux x64`. These are process checks, not proof of AI/SQL/shared-state readiness.
- Unavailable loopback AI returns safe HTTP 503; container networking is `none`, with no credentials or provider access.
- Synthetic ordinary planning produces options; SQL is unconfigured and saving returns 503 without a database connection.
- Backend diagnostic API and frontend diagnostic page/API remain unavailable.
- Both processes stop within the eight-second Docker deadline without SIGKILL or OOM. Backend shutdown-complete logging is required. Frontend observed exit 143, backend observed exit 0.
- After restarting both processes, proxy health recovers and the old fictional save receipt returns 409. Lost authority is safely rejected, not reconstructed or called durable recovery.

The frontend is stopped before the backend, then restarted after it to rejoin the backend's new isolated network namespace. This is a network-free smoke arrangement, not a proposed Cloud Run topology. Temporary synthetic save data is cleaned up; no real saved itinerary or owner database is touched. All task-owned smoke containers are removed on exit.

## Demonstrated harness defects and focused changes

Both original image builds worked. Security inspection found unnecessary inherited package installers; these were removed from final runtime stages without changing application dependency versions. Stronger checks also exposed two test-harness assumptions:

1. `docker cp` could not retrieve the receipt from this runtime's tmpfs. The harness now streams only the fictional receipt with `docker exec`, into a mode-0600 temporary host file and back into the restarted container. Nothing is mounted from the host.
2. Requiring zero as the only clean exit wrongly rejected Next.js. Installed `next/dist/server/lib/start-server.js` awaits connection/server cleanup and deliberately exits 143 for SIGTERM. Uvicorn also permits signal termination after cleanup. The harness accepts 0/143, rejects 137/other codes and OOM, and checks backend shutdown completion. It does not change either framework's signal handling.

Every `docker run` now explicitly requests the reviewed amd64 platform, removing platform-mismatch warnings without changing the target. There is no grammar, parser, normalizer, prompt, model, frontend UI, persistence, admission or provider-accounting change.

## Security evidence and dependency limitations

Actual saved runtime-image layers were scanned locally for configured secret values and forbidden private/evaluation/fixture paths. Final backend: 7,835 layer files; final frontend: 7,961. Zero configured-secret matches and zero forbidden files; no ESLint/typescript-eslint runtime tooling found. Runtime declaration exposes only 8080/tcp; smoke publishes no ports. These checks do not prove absence of every possible unknown secret.

The initial merged runtime contained pip (backend) and npm/yarn (frontend). Six frontend high matches were under the base npm installer, not the standalone app. Final runtime stages now remove inherited npm/npx/yarn/corepack and both system/venv pip. Actual running-container checks prove those installers are unavailable, and complete smoke still passes. Immutable lower base layers still contain their original public bytes; this is runtime attack-surface removal, not erasure of lower layers or a smaller-base claim. The final vulnerability scan uses the merged runtime; the separate secret scan still examines all saved layers.

Public npm audit again reports seven moderate findings in the development lint chain (minimatch amplification, GHSA-g3hv-75wg-m249), zero high/critical. The affected paths are dev-only according to the unchanged package lock and were absent from runtime image inspection. They affect the build/lint toolchain and still merit a separately tested compatible update. They are not seven distinct remotely exploitable application-runtime flaws, nor proof that the images are vulnerability-free.

A separate digest-pinned official Grype container examines local Docker archives. It has no host mounts, socket, credentials or access to protected evidence. Public vulnerability-database downloads are allowed; images are not uploaded. Non-root scanner temporary-directory permissions needed an isolated writable work directory; application images were unaffected. Exact scanner/database identity, results and any retrieval limits are recorded in the [verification JSON](task52-local-container-verification.json). Security findings must remain separate from functional smoke success; no vulnerable package is silently repinned.

## Security triage and next bounded remediation

The initial scanner reported backend 301 package/advisory matches (3 critical, 78 high) and frontend 228 (2 critical, 55 high). These are **matches**, not unique remotely exploitable vulnerabilities. Final counts after installer removal: backend **289 matches (3 critical, 78 high)**; frontend **209 matches (2 critical, 49 high)**. Backend removal eliminated 12 pip-related medium/low matches; frontend removal eliminated 19 npm-related matches including all six non-OS highs. See [retained high/critical advisory inventory](task52-local-container-security.json). High/critical OS and application-dependency findings remain unresolved. Functional smoke passes; hosted security approval does not.

- The critical glibc matches are `libc-bin` and `libc6` at `2.36-9+deb12u14`, both for [CVE-2026-5450](https://security-tracker.debian.org/tracker/CVE-2026-5450). Debian lists Bookworm vulnerable with a minor/no-DSA assessment; the scanner labels them critical. Preserve both observations rather than suppressing the matches or claiming application exploitability.
- Backend `libsqlite3-0` at `3.40.1-2+deb12u2` matches [CVE-2025-7458](https://security-tracker.debian.org/tracker/CVE-2025-7458), also Bookworm minor/no-DSA. The advisory concerns crafted SQL execution, not proof that this app accepts arbitrary SQL. The local evaluation journal is absent from images and was never exercised in containers.
- Backend `pyasn1 0.6.4` has four high matches; scanner fixes indicate `0.6.5`, including [constructed-string decoding denial of service](https://github.com/advisories/GHSA-9m75-vc3g-4x39). This is a real retained dependency finding, distinct from the removed pip installer. No exploitability or safe-risk acceptance is claimed.
- The seven moderate repository npm findings remain dev-only, [minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249). Fixing that chain still needs a compatible lint-toolchain update and tests. `npm audit fix --force` was not used.

Next security work should be one reviewed base/application-dependency and build-toolchain remediation checkpoint: select supported fixed base digests, review the pyasn1 and other retained findings, bind changed runtime/dependency identities without rewriting historical evaluation pins, rebuild, rescan and rerun regressions. Do not switch distributions, versions or suppressions incidentally here. No cloud purchase or provider readiness request is needed to review these local findings.

## Reproduction and remaining gates

From `/Users/rahularutla/Documents/whereto`, with the already-approved profile:

```sh
colima start whereto-task52
DOCKER_CONTEXT=colima-whereto-task52 sh deployment/container-smoke.sh
npm run build
backend/.venv/bin/python -m unittest deployment.test_packaging -v
```

Do not mount the home/repository/journal or enable real-provider development flags. Stop this task's VM with `colima stop whereto-task52` when finished; images/configuration stay local and are not committed. The smoke contains no deployment or push command. Public build dependencies/base downloads differ from forbidden AI/Maps/account requests.

Hosted staging remains blocked by the unchanged production guard, local-only Ollama dependency, process-local sessions/replay/receipts and file financial ledger, missing shared durable authority, workload identity/private backend invocation, trusted hosted-origin policy, SQL secrets/CA/fleet connection review, independent model qualification, security remediation and explicit provisioning/spend approval. Container success resolves the prior missing-engine/build uncertainty only. Existing [architecture and cost assessment](task52-cloud-deployment-preparation.md) remains a proposal; no cost redesign, migration, activation or Task 53 work was done.
