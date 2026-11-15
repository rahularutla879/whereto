# Task 52B — original-evidence replay and inactive execution boundary

Baseline `17430785faee36c88ac6d65972061944488b6f9f`. This is bounded offline preparation, not permission to access provider accounts or execute the five requests. [Build](task52b-execution-boundary-build-v1.json) · [Verification](task52b-execution-boundary-verification-v1.json) · [Unactivated purpose proposal](task52b-diagnostic-purpose-amendment-PROPOSED-v1.json).

## Original-evidence dependency and resolution

The matching source environment remains `e7937e4ab1c2734a6576137dd4233fdaca8966c5`, B2 root `eeaec6d0fcc502cb1df2388f9ab808f013cbf711b7f84c91d21e7132ff3d4b8b`, original lock SHA `7fde3bb3c81a32f5149f56a3258a8dc9afc563c040a50337c85ea69f483b8404`. The modern development checkout remains incompatible with that frozen identity and is not repinned.

The four earlier errors were precise location dependencies:

1. Q1 seven-response replay needs the exact 324-file private hash set, original journal bytes and ten immutable row hashes before decoding the seven OpenAI records.
2. Q2 provider-error assessment needs the original ten journal records, configuration/error evidence and IP-restriction evidence files.
3. Q2 source-gate test calls Q1 replay and therefore needs the same original evidence, while requiring the old paid corpus gate to continue refusing B2.
4. V5.1 replay traverses the V5/Q4B chain, requiring the original private set, permissions, corrections, lock inode and fixed read-only journal snapshot before comparing original V4 and proposed V5.1 results.

`scripts/task52b_evidence_access.py` supplies a separately versioned, trusted **in-process I/O port**, not a filesystem clone or OS sandbox. Frozen code and ROOT values are unchanged. Only I/O requests under the frozen private-evidence prefix are routed to the existing original absolute path. Actual opens use that original path/inodes: no copy, symlink, mount, recreated response or synthetic replacement. The source checkout remains clean.

Before access the port verifies B2, all324 original file hashes and the pinned set/journal hash, owner-only directory/journal modes, absence of symlinks/side journals and real device/inode identities. Files open read-only with `O_NOFOLLOW`; descriptor identity is checked. SQLite evidence access accepts only the exact original URI, refusing encoded/normalized/authority aliases, and opens it with `mode=ro&immutable=1`, query-only and a restrictive authorizer. The existing original lock inode is retained; each connection owns a shared lease until close. Network sends are blocked. Evidence hashes and source identity are rechecked after the run. Missing, altered, linked or incompatible evidence refuses.

For Q1 replay the port holds the shared lock throughout. Q4B already owns its shared lock and deliberately tests an exclusive lock; its suite uses the explicit `frozen_q4b` mode, with pre/post locking and connection leases, so the added port does not mask that unchanged exclusion test. No frozen test was edited or excluded. An earlier full-context trial produced one adapter-induced lock-test error; the record is retained.

All37 unchanged frozen Q1/Q2/V5.1/version tests pass with original evidence through the port. This restores the full **recorded-evidence behavioral replay**, rather than merely locating matching source files. It does not reproduce the original paid environment, run an inference, certify model accuracy, or make the I/O adapter part of the historical build. The new source-composition manifest separately binds the adapter/launcher/tests and preserves every historical hash.

## Append-only writer and single-send kernel

`52b-append-single-send-execution-boundary-v1` in `scripts/task52b_execution_boundary.py` reuses Q4C's existing transition code under fixed V5.1 diagnostic dependencies and the existing real-integration SQL guard. It does not introduce another ledger, scorer, signature algorithm or planner.

The production-intended transition path is exercised only with registered, newly created fictional exact-DDL journals. The new adapter narrows INSERT to the exact latest immutable START, expected slot, fixed2,500,000-nanodollar reservation and existing operation record. SQL remains PID/thread/current-lock guarded, with fixed SELECT/BEGIN/INSERT only; no UPDATE/DELETE/REPLACE/metadata/schema modification. Original root/ten-row prefix, halt, unique slots/nonces, global/provider/child caps and max(reservation, liability) accounting remain checked by frozen code. Synthetic prefix records are freshly authored fictional money/records using public slot identifiers; no private financial rows are copied.

Before dispatch: verify the adapter manifest, matching B2 source, existing signed synthetic purpose/action/readiness/operation evidence, exact prepared request bytes/provider/model/method, and current progression gates. Full source verification occurs before each operation; existing frozen artifact/signature/fact checks continue at each transition. Repeated full historical-evidence scans on every SQL accessor were removed from the new draft; setup and the read-only port still verify original evidence and retain its locks. No security deadline, accounting check or frozen validator was changed.

The unchanged kernel durably records START, commits the conservative reservation with FULL synchronous SQLite, then fsyncs INTENT before one closed send. The responder independently observes the committed reservation and INTENT, and exclusively creates a durable dispatch-consumption fact before simulated delivery. A second send cannot recreate that fact. Both before-send and possible-send timeout simulations retain the full reservation and block continuation; no retry, refund or slot replacement is inferred.

Raw response bytes are base64-preserved verbatim with SHA-256, followed by a distinct decoded envelope/content/usage/status record. Existing raw mechanical checks, legacy normalization, independent V5.1 guarded assessment and conditional diagnostic eligibility remain separate inside the immutable OUTCOME/grade evidence. Capture/decoding/grade files are revalidated against the outcome; missing or changed evidence refuses. A crash between stages remains incomplete/uncertain, never permission to repair the raw output or resend. Planning stays false and independent correctness remains null.

The factory still accepts **only fictional storage**. It cannot open the original journal writable. `live_dispatch` remains unconditional refusal. Real-path storage enrollment, operational-purpose signatures/role provenance, readiness and a real single-send HTTP implementation remain unavailable pending separate review/authorization. Parent signatures used by the tests are explicitly synthetic and do not approve this new adapter build operationally. The source-pinned kernel and its boundaries are prepared; no active real writer or transport is claimed.

## Review and readiness boundary

Owner review deferral remains unchanged:120 source judgments, six historical questions and four normalizer questions are incomplete. Temporary synthetic test signatures are not reviewer answers, owner signatures or financial permission.

The purpose proposal is deliberately minimal: only the first exact slot could be considered as an unreviewed technical observation after explicit governance/owner/security and financial approval. It would stop after that response/error; genuine independent response review remains necessary before any next slot. It is **not activated** and is not accepted by the frozen envelope verifier. The exact journey-06 exception and its genuine-review/system-incompatible/planning-false restrictions are untouched.

The [separately gated account procedure](task52b-openai-readiness-gates-v1.md) remains: owner-controlled key/project/model/access/quota/credits/auto-recharge/terms/pricing evidence, at most one model GET and five exact full-payload count requests only after separate permission, no inference or retries. All actual counts are still null. The unchanged five-operation proposed ceiling is $0.0125, conditional on verified current counts/prices; nothing here authorizes that amount or increases it. Each actual operation would also need exact new purpose/build/journal and single-operation permission while preserving the old halt.

## Running and trust limits

Run the committed launcher by absolute path **from the clean matching B2 checkout**, using the existing development Python executable with `PYTHONPATH=.` and `CI=1 WHERETO_AI_WARMUP_DEV=0 PYTHONDONTWRITEBYTECODE=1`. Select `--suite replay`, `--suite boundary` or `--suite historical`. The launcher explicitly loads only the new pinned ports/tests; ordinary frozen application imports remain in the B2 checkout. Wrong working source refuses, without fallback. New boundary tests are explicit opt-in and cannot run their original-evidence checks under normal backend discovery.

These local tests trust reviewed Python and same-UID operator code. The I/O hooks are process-global offline tooling, not a production web-worker adapter. A fresh interpreter without the test storage enrollment refuses; crash drills do not claim operational grant reenrollment. They do not resist a malicious administrator, coherent rollback of all journal/audit state, OS compromise or an attacker who can replace the verifier itself. No independent human approval is inferred from passing tests. Crash drills show process termination, durable local reservation/INTENT and no resend; they are not proof of physical power-loss durability. The old original halt is preserved. Account pricing, real provider behavior and production transport remain untested.

The original ten attempts, $0.047366625 accounted, $11.952633375 remaining,324 files/corrections and persistent halt remain unchanged. No provider, account, token-count, financial grant, cloud, application or Task53 action follows automatically. Full-backend/frontend/container suites were not claimed. Exact results, development errors and interrupted runs are in the machine verification record.


## Final verification totals

| Executed suite | Passed | Failures/errors/skips |
| --- | ---: | --- |
| Frozen Q1/Q2/V5.1/version replay | 37 | 0/0/0 |
| Frozen Q4B journal | 12 | 0/0/0 |
| Frozen Q4C signed protocol | 22 | 0/0/0 |
| Frozen Q4D strict continuation | 11 | 0/0/0 |
| Frozen real-integration synthetic tests | 7 | 0/0/0 |
| New boundary, two isolated partitions | 17 | 0/0/0 |
| Existing prepared-payload regression | 13 | 0/0/0 |
| **Total selected** | **119** | **0/0/0** |

Normal discovery separately skips all17 privileged lab cases without importing their frozen profiles; unittest reports0 executed/17 skipped and exit5, not a passing executed suite. Wrong-source launch deliberately returns VersionError before evidence access. `pip check`, configured-secret scans (two ordinary plus three evaluation values), full manifest/payload/link/syntax checks and before/after original-journal/private-file/halt comparison pass. All20 chapters remain, with15/17 updated and18 unchanged. No full backend/frontend/browser/build/container or authenticated-provider checks were run. Test timings in the record are local verification timings, not provider latency.
