# 15 — Testing Mocks Debugging and Error Handling

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## A test is a controlled claim

A **test** runs code under declared conditions and compares actual behavior with expected behavior. A **unit test** targets a small piece; an **integration test** exercises connected pieces; an **end-to-end test** follows a larger user journey. A **mock** replaces a dependency; a **fixture** supplies known data. Developers use them to reproduce failures without relying on changing external services. Where To? particularly needs invented venue/routes/model responses so verification does not spend money or expose owner data.

A green test with fake Google data establishes behavior for that fixture, not accuracy of real Google data. A test file that starts the actual FastAPI app with fake providers can establish HTTP integration, but is not automatically a browser check. Full hosted database and POSIX PTY lifecycle tests are opt-in. PTY means **pseudoterminal**, a simulated terminal used to test process ownership and shutdown.

## Read an existing deterministic-clock example

From [backend/TESTING.md](../../backend/TESTING.md):

```python
request = OutingRequest(activities=["coffee"], location="New York", date="2026-11-07")
problem = outing_problem(request, now=datetime(2030, 1, 1, tzinfo=timezone.utc))
self.assertEqual(problem[0], 'outing_date_expired')
```

Line 1 constructs a request with a declared historical date. Line 2 supplies a later aware instant explicitly; an **aware datetime** carries timezone information. Line 3 asserts that the calendar rejects it as expired. Inputs are a request and clock, output is a calendar problem, and a wrong result fails the test. No AI, Maps or SQL is needed. The surrounding example uses `calendar_clock` for scenario defaults; explicit `now` still takes precedence.

**Assertions** express expected facts. A failing assertion is evidence to investigate, not permission to loosen the rule. Calendar, route-evidence, monotonic session and accounting clocks have different meanings. Historical November 7 fixtures failed after real dates advanced; the repair introduced isolated scenario clocks rather than weakening production expiry. `route_evidence_clock` controls freshness separately, and `fixture_api --factory` explicitly controls child-server test calendars.

## Find the right test family

| Change or question | Existing starting point |
|---|---|
| Candidate identity/product | `backend/test_planner.py` |
| Scheduling/scoring | `backend/test_ranking.py`, `test_feasibility.py` |
| Source/calendar validation | `test_interpretation.py`, `test_journey.py`, `test_date_resolution.py` |
| Partial order/return/timing | `test_advanced_routing.py`, `test_advanced_timing.py` |
| Geographic incident | `test_hitec_geography.py` |
| Worker/rate/privacy | `test_request_management.py`, `test_planning_admission.py` |
| Saving/security | `test_saved_plans.py`, `test_database_security.py` |
| Browser-facing adapters | `lib/planning-client.test.ts`, `lib/request-management.test.ts` |
| HTTP proxies | `app/api/interpret/route.test.ts`, `app/api/plans/generate/route.test.ts` |
| Frozen cloud research | `backend/test_task52_q1.py` through `test_task52_q4c.py` and ordering suites |
| Default-OFF V5.1 interpretation to synthetic planning | `backend/test_v51_ordering_preservation.py` |

These are repository-relative paths; [the file map](PROJECT_FILE_MAP.md) links every indexed source/test. Normally enabled tests use fixtures; do not enable hosted resource or lifecycle flags as a study shortcut.

## Debug by locating the first wrong boundary

**Debugging** is finding why observed behavior differs from intended behavior. Start with the visible message, HTTP status and safe code/correlation ID. In browser Developer Tools, the Network panel can distinguish `/api/interpret` failure from `/api/plans/generate` or `/api/plans/advanced`. Do not export raw requests, tokens or origin payloads into shared reports.

A failed frontend fetch could mean a dead proxy/backend, a validation refusal, malformed upstream JSON or a provider failure. [failure-diagnostics.ts](../../lib/failure-diagnostics.ts), [proxy-failures.ts](../../lib/proxy-failures.ts) and [backend/failures.py](../../backend/failures.py) preserve categories. A **stack trace** shows function calls around an exception; a sanitized production message deliberately hides sensitive internals. Review private local traces carefully rather than logging whole bodies.

The launcher inherits terminal output; there is no guaranteed application log file containing every prior request. Operational counters and sanitized events cannot recover all original response fields. The Hitech incident's missing original response demonstrates why uncertainty should be reported instead of filled with a plausible cause.

For the explicit V5.1 development path, run `backend/.venv/bin/python -m unittest backend.test_v51_ordering_preservation -v`. Compare the raw graph, legacy snapshot and final result in the fixture before investigating routes. A missing edge in the raw snapshot is an extraction problem. A proved edge present only in the raw snapshot identifies the legacy deletion branch. A proved handoff followed by a missing route is a planning-evidence problem. Keep snapshot text local. [Development tests](../../backend/test_v51_ordering_preservation.py)

## Commands and honest reporting

`npm test` runs the declared TypeScript tests. `npm run test:backend` runs unittest discovery through the existing virtual environment. `npm run lint` checks code style/errors; `npm run build` compiles a production frontend bundle; `npm run typecheck` checks types. Build replaces generated `.next/types`, so run typecheck after the build completes. Compilation is not behavior verification, and a successful build does not mean backend production activation is allowed.

For this documentation-only delivery, link/organization/source checks are appropriate. Running paid services or all opt-in tests would not validate prose and would exceed scope. See [VERIFICATION.md](VERIFICATION.md) for exactly what was checked now. See [DEBUGGING_PLAYBOOK.md](DEBUGGING_PLAYBOOK.md) for symptoms and bounded read-only investigation.

## Native packaging smoke versus real containers

`deployment/test_packaging.py` tests manifest assembly, safe launch refusal, real temporary Uvicorn/Node startup, proxy health, a loopback fake unavailable AI service, missing-SQL refusal, receipt loss after restart and clean shutdown. It requires standalone output from `npm run build`. These are native-process tests, not Docker verification. `sh deployment/container-smoke.sh` is the separate Linux image test; it exits 78 when a local Docker engine is missing rather than claiming success. The script publishes no ports, uses no external network at runtime and never deploys or pushes an image.

## Actual container smoke acceptance

The approved named Colima context is selected per command: `DOCKER_CONTEXT=colima-whereto-task52 sh deployment/container-smoke.sh`. Native tests remain separate. The container check now verifies mock planning, absent-SQL refusal, frontend/backend diagnostic protection, no published ports, non-privileged/read-only/capability-dropped execution, graceful stop and stale-receipt rejection after restart. Next deliberately exits 143 after its awaited SIGTERM cleanup; this is accepted alongside zero, while SIGKILL 137 and OOM are rejected. Backend shutdown-complete logging is required. Only a fictional receipt is streamed from tmpfs with `docker exec`; it is never printed or treated as real authority. [Actual results and limitations](../task52-local-container-verification.md).

## Testing a bounded dependency patch

The backend builder now performs `pip check` after installing the Linux hash lock. Runtime images still contain no pip/npm installer. Packaging tests compare every historical requirement, permit only the exact reviewed pyasn1 0.6.5 exception and check its wheel hash; they also assert the old requirements-file SHA. The historical local venv is not overwritten. Backend regressions can be exercised using an isolated verified universal wheel, while actual image imports and existing container smoke prove the deployed dependency is loaded. Comparing old and patched images under the same advisory database separates a fix from scanner-database drift. [Tests and exact evidence](../task52-container-security-verification.json).

## Five key takeaways

1. Tests establish behavior under specific conditions.
2. Mocks prevent external cost but do not verify real availability.
3. Separate clocks make time-dependent tests meaningful.
4. Compile, test, browser and live evidence are distinct.
5. Investigate the first failed boundary rather than guessing a provider cause.

## Local application-boundary V5.1 checks

Run `backend/.venv/bin/python -m unittest backend.test_v51_application_fixture -v` for fixture isolation, API optional-stop omission, unreachable-route refusal and whole-trip timing. Run `node --import tsx --test lib/v51-application.test.ts` for the actual Next interpretation proxy, FastAPI advanced sessions, frontend card adaptation and selected save/reopen. The Node suite launches disposable loopback backends with minimal environments; each independent scenario owns its normal fresh process allowance. It never increases a running session's budget.

The fixture blocks external HTTP, outbound sockets, real database connections and model factories. The browser smoke uses only synthetic public names and local requests. A provisional card with unknown visit duration is not a verified feasible whole-trip schedule. Cards retain the existing “Real venues” presentation for provider-shaped fixtures; all fixture venue names are explicitly Synthetic and have no verified live availability. Do not follow their Maps links.

For debugging, compare source → supplied raw graph → validated handoff → session answers → option occurrence order → saved selected graph. The generalized helper remains fresh-only; the fixture bridge below handles bounded manual controls. Included optional stops lack an active-card optional badge in the current UI; the saved view preserves typed optional metadata. Do not fix that presentation by changing the extraction. [Scope, browser results and exact incomplete historical IDs](../task52-v51-local-application-integration.md).

## Manual/pending compatibility checks

Run `backend/.venv/bin/python -m unittest backend.test_v51_manual_pending -v` for source edits, tampered/expired pending state, raw-identity changes, deterministic overlays and expired planning/save capabilities. `node --import tsx --test lib/v51-application.test.ts` additionally crosses the actual Next proxies, FastAPI session boundary, planner and selected save/reopen service. The four tests include fresh source edits and pending reuse; fake-provider acquisition counts stay unchanged for a valid pending answer.

The application fixture owns a fresh default provider-budget object per fixture lifetime and restores the prior object on exit. This isolates test contexts without increasing limits or resetting a running session. Calendar freshness and advanced answers share the frozen timezone-aware reference; monotonic capability expiry and provider accounting clocks remain independent. If a changed source is refused, inspect the new source proof before considering any old graph. Never turn an effective pending snapshot into raw evidence to make a test pass. [Exact verification](../task52-v51-manual-pending-verification.json).

## Check your understanding

15.Q1. What is a fixture?
15.Q2. What does an assertion do?
15.Q3. Why not move every expired fixture date forward?
15.Q4. Does a build prove planning behavior?
15.Q5. Can sanitized aggregate logs recover every original response?

## Code-reading exercise — 15.R

Read one test in test_hitec_geography.py and identify invented inputs, replaced dependencies and the assertion.

## Inactive shared-state and financial authority

The synthetic PostgreSQL harness runs core security tests followed by V3 financial tests and a real SIGKILL/restart of the disposable database. The financial fixture installs all grants in one transaction. Tests bypass the Python wrapper to attempt price, unit, provider, scope and clock manipulation; the restricted SQL principal must refuse them. Two spawned workers compete at outing/session/day/minute/admission boundaries. A protected fixture clock tests exact 60-second and 10-second rollover, local midnight and DST without waiting in real time; runtime cannot set that clock. Existing interpreter/planner/save tests and native refresh tests still use fake evidence. Passing these tests does not demonstrate real API pricing, hosted failover, browser integration or production performance.

[Financial policy audit, tests and limitations](../task52-financial-authority.md)

## Practical exercise — 15.P

After inspecting backend/TESTING.md, run only backend/.venv/bin/python -m unittest backend.test_planner -v in a disposable learning checkout if desired. Record actual output, not expected totals.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-15).

[Previous chapter](14-security-rate-limits-accounting-and-reliability.md) · [Contents](README.md) · [Next chapter](16-git-github-and-the-development-workflow.md)


## Testing the inactive action bridge

Run `backend/.venv/bin/python experiments/shared_state/run_local.py` from the repository root with the approved dedicated Colima profile. It creates/removes only its own synthetic PostgreSQL volume/containers, exposes no host port, copies reviewed runtime files and injects authored responses. `test_bridge.py` calls actual ordinary/advanced planning, pending answers, options, lookup, contact, refresh and selected receipt selection. Its crash test kills a worker after committed intent/dispatch. `test_action_identity.py` separately compares seven stored OpenAI legacy result hashes and 27 Qwen ordering results under the current build; it does not bypass an old evaluator. Old B2/Q1–Q4 checks intentionally refuse changed source identities: report those refusals, never silently repin them. These tests are not browser or hosted verification.

See [Task 52 action bridge](../task52-provider-action-bridge.md) for exact boundaries and verification.


## Disposable Redis and PostgreSQL evidence tests

Run `PYTHONPATH=. backend/.venv/bin/python -m experiments.shared_state.run_evidence` after downloading the isolated hash-pinned Linux test wheels. The harness uses the approved local Colima context, no host mounts/ports and loopback-only container networking. It exercises existing SQL/financial/bridge tests, new encryption/CAS/role tests, synthetic TLS certificates, Redis loss and an actual older synthetic SQL snapshot restore. Every created container/volume is removed. This does not test hosted Memorystore, real user data or Google accuracy. See the report for exact commands and failures; do not point the fixture at Supabase.

See [implemented evidence boundary and limitations](../task52-shared-evidence.md). Production behavior is unchanged.


## Two-database grant and restore tests

Run `PYTHONPATH=. backend/.venv/bin/python -m experiments.shared_state.run_grants` from the repository root with the existing approved Colima profile running and the hash-verified evidence wheels cached. This harness creates disposable operational PostgreSQL, separate witness PostgreSQL, Redis and an isolated client, all with synthetic accounts. It removes its own containers/volumes in `finally`; it never copies the real evaluation journal. Keep the existing VM resource limits.

The test profile composes actual legacy interpretation/planning and saved-refresh contracts with fake providers, rather than inventing a second planner. Tests distinguish gross reserved exposure from reported token usage. Restore drills export only newly authored synthetic schemas, restore one component at a time, and require full-grant quarantine. Process/database kills test committed-state recovery, not power-loss or multi-region durability. Existing frozen tests are run separately without changing their source pins. See [exact verification](../task52-application-financial-verification.json).

## Testing native restart continuation

Run the inactive profile with `python3 -m experiments.shared_state.run_native` from the repository root, using only the already approved disposable Colima environment and hash-checked local test wheels. It reuses the grant harness; it is not a hosted runner or evaluation grant. Fresh `spawn` processes reconstruct ordinary pending/options and advanced resolver/history state from SQL/Redis, using their own fake dependencies. JSON-only test IPC carries internal ticket scalars, not pickled application objects. An actual child exits after durable BEGIN to prove it cannot be automatically retried.

Distinguish stale revision/fence, missing Redis, expired route, incompatible build/key and BUSY-turn refusals. Do not reset SQL/witness history or call providers to make reconstruction succeed. Source edits require new validation. A separate selection-only ticket can remain viewable while active routing has expired. Actual PostgreSQL snapshot and SIGKILL/restart drills differ from ordinary unit mocks; none proves power-loss or hosted regional recovery. Exact commands and outcomes: [verification](../task52-native-session-verification.json).

## Authenticated service-process tests

The [local runner](../../experiments/service_isolation/run_local.py) uses disposable stores plus separate factory, counter, dispatcher, recovery and ordinary-worker containers. Tests invoke fresh worker processes through TLS, not privileged objects handed to a worker. Private bootstrap credentials remain in the test controller. The code volume is read-only; root filesystem is read-only; capabilities are dropped and there is no Docker socket, host mount or external network interface.

The normal cohort covers pending/advanced continuation, cross-owner and stale revision refusal, reusable selected receipts, refresh replay, bad signatures/audiences/roles/epochs/builds, durable nonce replay, restricted SQL, restart/outage and restored history. Explicitly synthetic failure cohorts pause delivery after reservation and terminate processes or revoke admission, checking committed exposure is retained. This is process-crash evidence, not proof of power-loss/hosted failover durability. Sanitized service errors contain only reason/stage/SQLSTATE/frame names; never log source bodies or credentials. See the [exact verification record](../task52-service-isolation-verification.json) for results and limitations.

## Offline Google-shaped identity tests

`python3 -m experiments.hosted_identity.run_local` uses the frozen local harness with new offline identities and authentication-only roles. The trusted controller alone holds synthetic RSA/EC issuer keys; services receive public fixture JWKS and only their own preissued workload tokens/proof keys. Separate frontend/backend/factory processes verify scoped user ownership through actual native planners. Pure token tests, Node forwarding tests and PostgreSQL/Redis process tests prove different things; none is a real Google/IAP/browser or hosted-readiness test. [Exact results and untested conditions](../task52-hosted-identity-verification.json).

## Test the real seam without claiming hosted planning

`experiments.hosted_startup.run_local` uses actual Next HTTP handlers and two actual FastAPI status processes, signed synthetic identities, fake metadata and fresh SQL/Redis/witness resources. Its Docker-exec transport and custom Next driver are test infrastructure, excluded from production images. Backend environment remains ordinary development; AI preparation alone is faked. Neither production admission check is patched. Business requests refuse and SQL confirms zero provider operations. Parent native/financial tests are separate evidence, not proof those flows traverse the new public facade.

A restart test must wait for bounded non-billable socket readiness rather than assume Python is ready after one second. Preserve failed cohorts and immutable source pins; do not weaken tests to obtain a green total. Distinguish SDK unit tests, actual HTTP process tests, native container smoke, browser checks and hosted acceptance. [Exact results](../task52-hosted-startup-verification.json) list what was not run.


## Ordinary HTTP acceptance and clock-pair regression

`experiments.ordinary_hosted.run_local` exercises actual Next/FastAPI requests and the existing `generateOuting` client using disposable PostgreSQL/Redis and offline identities. That client driver is not a browser UI test or real IAM/provider verification. `test_reliability.py` reproduces a one-millisecond loss in the original native `Session.state` clock-pair conversion and checks the new exact-integer adapter. The earlier redacted SQL refusal remains unattributed; sanitized reason/category/SQLSTATE/stack locations help future diagnosis. Never log raw queries, credentials or source bodies, or repin frozen tests to hide failures. See [Task 52 ordinary integration](../task52-ordinary-hosted-integration.md).


## Inactive ordinary private browser checkpoint

Separate real desktop/mobile browser observations from HTTP, unit and container results. The new controller tests cover late responses, expiry, no retries, no browser raw evidence, normal404 and non-entitling readiness. Controlled missing evidence yields SQLSTATE P0001; lock contention yields55P03 under unchanged deadlines. Neither proves the cause of an older unattributed refusal. See the [UI/recovery report](../task52-ordinary-private-ui.md).
