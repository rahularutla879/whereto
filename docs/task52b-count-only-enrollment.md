# Task52B — observed permission and supervised count enrollment preparation

Baseline `4d9280582ec23e31df921d36dccddbcb06f5de27`, November17,2026. [New source build](task52b-count-only-build-v2.json), [sanitized dashboard binding](task52b-count-only-dashboard-binding-v1.json), [exact verification](task52b-count-only-enrollment-verification-v1.json).

**Preparation passed. No live send authorization or scope was created or consumed.**

## Permission evidence actually observed

A read-only inspection of the owner's actual signed-in OpenAI API-key dashboard showed project **WhereTo Model Evaluation**, the exact project ID `proj_E4EfEvC5uQYN4nqFaYZoo3I4` in its Settings link, Personal organization, and the existing active **WhereTo Task52B Evaluation** key. Its visible tracking ID matches both the existing private credential enrollment and historical metadata; expiry is December15,2026. The existing key was inspected, not recreated.

The Restricted edit dialog showed **List models: Read**, **Responses: Write**, all unrelated model capabilities and top-level groups **None**. Save was disabled; the dialog was canceled without saving and the temporary tab closed. No permission, credential, expiry, billing or other account setting was changed. The secret was masked, never revealed or read. This inspection used the explicitly authorized dashboard, not a Models/Responses API probe.

Two new owner-only files alongside the existing readiness records hold the actual observation transcript and its separate permission receipt: `52b-count-only-owner-3ec6b68-v1.dashboard-observation-v1.json` and `.permission-evidence.json`, under ignored `backend/.local/task52b-readiness/`. Files are0600, parent0700, regular/single-link/no-symlink, written with the existing O_EXCL/O_NOFOLLOW/fsync primitive. The timestamp records the observation attestation after inspection. No screenshot, secret, raw API response or private transcript entered Git. Only identity/hash bindings are committed.

`verified_permission` now verifies the transcript, receipt and pinned binding, including exact project, active key name/tracking/expiry, credential enrollment hash and permission values. Old Read metadata is preserved byte-for-byte as historical evidence; it is not represented as current permissions. The transcript is an independently observed local record, **not a provider-signed receipt or verification that server permission propagation has completed**. Same-user filesystem/administrator compromise remains outside this operator trust boundary. Any future401/403 is terminal; never modify permissions or retry automatically.

## Exact prepared runner and deadline

Proposed scope remains `52b-count-only-owner-3ec6b68-v1`: exactly one POST `/v1/responses/input_tokens`, model `gpt-6-luna`, exact count SHA256 `70939877e0df3fca79fb68cab25d5449ae2533ec31892ed91b762ddbd2c8e6d1`. GET/inference/retry maxima remain zero. No alternate credential, endpoint, model or inference option was added.

The original validated model GET remains bound to the unchanged thirteen-file consumed scope and old source/runtime manifest. Its hard expiry is **November18,2026,00:00UTC = November17,2026,7:00PM EST**. The same-UTC-day/24-hour rule is unchanged. Both read-only preparation and actual worker/dispatch checks refuse at expiry; a new check after TLS handshake prevents HTTP transmission if freshness lapses while connecting. No evidence deadline is extended, and no GET is automatically added. A model alias is not an immutable model revision.

`scripts/task52b_run_count_once.py` prepares the existing spawn-supervisor pattern for this fixed POST. It pins a new versioned build, normalized bootstrap, Python executable and CA bundle; disables core dumps; verifies permission/source/freshness and explicit authorization before claiming anything; claims the launcher exclusively; spawns one worker; and kills an over-deadline worker without replacement. Worker parent/PID and loaded wire-code identities are checked. The existing runner consumes once and writes durable INTENT before the approved key loader can read the OpenAI line. The fixed TLS transport still has one dial, no redirects/proxies/netrc/retries,20s request deadline,10s dial timeout and65536-byte response bound. Incomplete or uncertain sends remain consumed.

The new v2 preparation manifest supersedes v1 for the updated runner; v1 and all original evaluator/readiness manifests remain unchanged as historical source identities, reproducible at their original commits. This is not repinning old model evidence. No application startup, SQL grants, provider pricing, prompt, schema or frozen request changed.

## Exact offline verification

**85current-source tests passed,0failures/errors/skips (26.824s)**: new observation/supervisor tests plus existing count-only, enrolled readiness, request validation and provider-response cohorts. **15frozen-compatible selected tests passed,0failures/errors/skips**. An earlier27-test development run passed before the added TLS-expiry case. No failed tests or interrupted runs in this checkpoint. These are selected cohorts, not a full backend/B2 suite.

Fictional journals and credentials cover observed-receipt tampering/substitution/modes, absent authorization, incorrect CLI purpose, expired evidence, successful one-count delivery, terminal400/401/403, malformed/oversized/incomplete responses, actual independently spawned supervisors/workers, competing supervisors, deaths before/after INTENT and response persistence, and replacement/replay refusal. Real TLS code is exercised only against loopback responders. The two process/supervision substitutions in fixture tests do not prove hosted identity or real provider acceptance.

Read-only historical checks, all original38source pins, the five payload pairs, original13consumed files, dependency consistency, diff checks and secret-pattern scans passed. Ten attempts(OpenAI7/Google2/Anthropic1),$0.047366625 accounted,$11.952633375 remaining,324private files and persistent halt are unchanged. Actual credential values were not read; value-comparison scanning was not run because it would require reading them. Full backend/B2/SQL/Redis, frontend/build/browser/application/images/cloud tests were not rerun; no affected application/dependency/image files changed. Handbook17 updated,14/15 reviewed unchanged, all20chapters preserved.

## Stop: exact remaining authorization

Permission evidence is valid as an observed dashboard record and prior GET was fresh at final verification. **The only remaining owner decision for this readiness operation is explicit authorization of one count POST under this exact scope/key/project/model/payload, accepting the stated Support$0 fee basis, with zero GETs/inference/retries.** Then, and only then, enroll the actual owner-only authorization and scope bound to this source build, permission receipt, prior GET bundle and existing credential. This checkpoint creates neither. Recheck all evidence and source identities at execution time; expired GET means stop for a separately scoped owner decision, not an automatic renewal. No inference/model qualification, grant, cloud provisioning, deployment or Task53 is approved by this preparation.
