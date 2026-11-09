# Task52B backend regression and date-fixture repair

The normally enabled backend suite is reproducibly green: **two consecutive runs of 1,134 tests, 1,097 passed and 37 unchanged opt-in skips each**. Frontend 285/285, TypeScript, lint and production build pass. All existing expiry/accounting/security assertions remain intact. **No production application behavior, ordering enforcement, model settings, prompts, corpus, provider configuration or paid state changed.**

Baseline clean `7a4fa1ce35fee6e817c42ea3c467eb8a8318a0e9`. [Exact 41 failing methods and sanitized original stack traces](task52-backend-date-baseline.json), [machine-readable run history, hashes and checks](task52-backend-regression-results.json), [clock and test guidance](../backend/TESTING.md).

## Verified original failures

The documented `npm run test:backend` reproduced 1,126 tests, 15 failure entries, 30 errors and 37 skips in 145.209s, with 41 distinct failing methods. The previous checkpoint reported 1,125 before the final added shadow test; no test was removed. Subtests create multiple failure entries, so baseline pass totals are not inferred by subtraction. Complete original method names/traces are preserved in the separate baseline artifact; historical V4 failed reports and model measurements were not overwritten.

| Root cause | Distinct methods | Evidence and repair |
|---|---:|---|
| Expired synthetic calendar fixtures |31|Nov7 events were genuinely past at the uncontrolled real freshness boundary, including a direct API-parent case. Scope calendar time to Nov1 UTC in those scenario fixtures.|
| Spawned HTTP server's uncontrolled clock |6|Parent patches do not cross a Python subprocess. Use the same real app through an explicit test-only factory with a lifespan-scoped calendar clock.|
| Monotonic/calendar clock mismatch |3|Regeneration tests advanced quota time but left calendar freshness live. Keep independent explicit quota and calendar clocks.|
| Downstream wrong response type |1|A saved-plan fixture expected RankingResult, but the valid expiry rejection was JSONResponse; `.plans` then raised AttributeError. This was not a persistence/authorization defect.|

All 41 methods passed their **unchanged assertions** after clock repair (114.521s). The following table identifies their fixture classes; the linked JSON lists every individual method and stack trace.

| Fixture class | Failing methods |
|---|---:|
| `test_acceptance46.OptionsAcceptance` | 7 |
| `test_acceptance_regeneration49.Regeneration` | 3 |
| `test_api.PlanningApiTests` | 7 |
| `test_discovery100.PipelineAlternatives` | 2 |
| `test_expanded_limits46.ExpandedLimits` | 6 |
| `test_exploration.ExplorationTests` | 2 |
| `test_location_acceptance.Pipeline` | 1 |
| `test_location_first.LocationFirst` | 2 |
| `test_location_lifecycle.GeographyLifecycle` | 1 |
| `test_open_exploration.OpenExploration` | 1 |
| `test_real_planning.RealPlanningTests` | 3 |
| `test_saved_plans.OfflinePersistenceTests` | 1 |
| `test_surprise.Pipeline` | 2 |
| `test_task46_improvements.ImprovementTests` | 2 |
| `test_travel_mode49.PlannerModes` | 1 |

No substantive production defect was found in these 41 failures. Date expiry was working correctly and took precedence over the quota/routing assertions that stale scenarios intended to reach. No production threshold, grace period, validation priority or source-grounding rule was changed.

## Test-only changes

`backend.testing_clock.calendar_clock()` targets only the calendar freshness lookup. Its default is aware UTC **2026-11-01T12:00:00Z**, keeping the original Nov7 Saturday venue/event fixtures intact. Each affected TestCase enters its own context; cleanup restores the original datetime even on nested contexts or test failure. The location-acceptance fixture inherits its existing LocationFirst setup and receives the same scoped clock without duplicated changes.

The HTTP tests explicitly select `backend.testing_clock:fixture_api --factory`, which returns the unchanged real application/routes and scopes the calendar clock to the child process lifespan. Normal dev/start still uses `backend.main:app`. No production clock/environment flag, suite-wide clock, test exclusion or new skip was introduced.

Eight added boundary tests cover aware-clock validation/restoration, explicit-now precedence, current/future/past dates, exact expired start/end boundaries, relative days, Saturday identity, Hyderabad/New York midnight differences, DST folds and nonexistent times, ten-minute capability TTL and route-evidence freshness. Quota monotonic clocks and daily/monthly billing clocks are not frozen or reset by these fixtures. Session validity at 599.999s passes and at 600s fails. Route evidence at 0/299.999s passes; future evidence and age 300/301s fail.

## Repeat-run investigation: cache reuse clock

The first date-only full run passed 1,133 tests with 37 skips (251.052s). Its repeat found **one failure** (1,133 tests, 37 skips, 300.145s): a cache-reuse test reserved 150 matrix elements instead of its exact expected 110. That red run is preserved in the new execution history.

Investigation retained the 110 assertion. Three isolated hash-seed runs passed with fresh evidence and no invalid cache entries, arguing against set ordering or leaked cache state. A controlled 301-second route-evidence clock advance after the tenth continuation reproduced the **exact 150-versus-110 mismatch**: the unchanged five-minute policy legitimately required fresh routes. Reservation stages were 42+64+4 normally; expiry added 40, without resetting accounting.

The reuse scenario now explicitly enters `route_evidence_clock()` so creation and reuse share a fixed test instant. Only this test opts into that helper; production `current_evidence` still enforces 0 ≤ age < 300s and rejects future timestamps. A new boundary test verifies those exact rules. No quota/billing allowance or provider retry was increased, and no real request occurred.

## Separate environment/cleanup defect

An initial frontend verification inherited `CI=1`. The fake exploration server exited because the unchanged production guard rejects exploration outside explicitly local development. Its parent then awaited an exit event already emitted and hung teardown. The owned stuck test processes were stopped; the failed attempt was not called green.

The frontend test now copies its child environment and removes **only CI from that fake-only child**; parent settings and production admission remain unchanged. The fixture server still refuses real provider sends and disables model warmup. A negative CLI probe with CI=1 still raises `Exploration requires explicitly local real development mode`, confirming that guard was preserved. Startup detects early child exit rather than polling until teardown. Cleanup handles an already-exited child and registers a listener before signalling a running child. Two event-driven regression tests cover both states; no retries, sleeps or larger timeouts were added.

## Final verification

| Check | Result |
|---|---|
| Complete backend final run A |1,134 run;1,097 passed;37 skipped;0 errors/failures;240.084s|
| Complete backend final run B |1,134 run;1,097 passed;37 skipped;0 errors/failures;239.188s|
| Frontend |285/285 passed, including 2 new worker-cleanup tests|
| TypeScript / lint / production build |All passed; typecheck sequenced after build-generated types|
| Date/quota/order/shadow targeted group |121 passed before the final added cache-boundary case; both final suites include the complete set|
| Calendar/cache fixture boundary tests |8/8 passed|
| Actual loopback HTTP API |Future fixtures succeed; explicit 2000 expiry, unsupported inputs and security cases retain their original assertions|
| Shadow OFF/ON |Existing full-body/status, interpretation/questions, invocation, session/capability, graph/admission and exception/timeout/mutation comparisons pass|

There is no new browser UI change or production request-code change; real loopback HTTP tests and ASGI/proxy integration provide the relevant API smoke. Shadow remains OFF by default and never authorizes a plan. Saved effective snapshots remain skipped rather than called raw evidence. **The known active legacy start/finish normalization loss remains unfixed by authorization; passing tests do not activate V4 enforcement.**

The37 unchanged skips are 29 hosted PostgreSQL checks (private DB/resource opt-in) and 8 POSIX PTY lifecycle checks (explicit flag and both development ports stopped). They were not enabled because this task authorizes neither hosted resources nor taking over owner development processes. No skip was added to conceal a failure.

## Security, paid state and next step

Full tracked/new diff and configured-secret scans are reviewed before delivery. Production expiry, route TTL, provider accounting, token/session security, main interpretation and shadow implementation source hashes match baseline; the report records them. All 324 private evaluation files and the SQLite journal/root/ten rows/corrections remain byte-identical, with integrity OK and actual persistent-halt recovery refused. Journal SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`. Credentials/journal remain ignored and mode 600; configured-secret scans found no values in current files or Git history.

Paid totals remain OpenAI 7 / Google 2 / Anthropic 1=10/594, 584 remaining. Conservatively accounted $0.047366625; authorized remaining $11.952633375. Original $12/594/198, 12k input/2k output, concurrency 1, retries 0 remain unchanged. No inference, counting, Maps, payment/billing/quotas, provider key/schema/endpoint, production model, infrastructure, migration or Task 53 action occurred. Gemini 400/IP and Anthropic grammar-compilation blockers remain independent.

The regression blocker is closed. The codebase is ready for a **separate ordering-enforcement design/review**, not activation. That review still needs to retire overlapping legacy normalization under an approved version, preserve raw/user-answer provenance and clarify pending-snapshot handling. This task does not resume the paid evaluation or select a production cloud model.
