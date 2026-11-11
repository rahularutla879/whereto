# Task 52B generalized V5.1 ordering preservation

The [original repair](task52-v51-ordering-preservation-dev.md) showed that legacy validation can erase a supplied, source-forward graph when the text has no recognized temporal cue. That behavior still exists in the production interpreter. The generalized development adapter removes the five-request lookup and the fixed case clock. It applies the same evidence checks to any fresh request in its supported grammar.

## Development flow

1. `interpret_for_development(value, extraction=..., now=..., preserve_order=True)` uses a supplied extraction and an in-memory provider. The default remains false. There is no request field, environment switch, model factory or call from normal startup.
2. `validate_for_development` retains the original typed extraction and the complete legacy result as separate in-memory snapshots. It matches each stop to a unique, unchanged original span and checks the frozen V5.1 proof for the original edge quotations, directions, required reachability and optionality. A narrow context-suffix fallback uses the original prefix with the same offsets and quotations. Quotes that need rewriting to fit that prefix fail.
3. The development boundary independently checks complete clause coverage and context. Calendar and mode reuse the existing deterministic validators. The full legacy result must be compatible. A difference is allowed only for the legacy deletion of the entire proved graph and its ordering mode, apart from the independently checked date-expression and explicit mode normalization. The adapter copies the original graph and leaves the supplied extraction untouched. It never fills in missing edges.
4. A proved result can be passed to the existing advanced contracts in a local development test. The adapter creates no session, receipt or planning authority. Using the advanced handoff keeps flexible placement and repeated occurrences explicit when legacy would have used the linear planner. Existing resolver, timing, routing, save and admission checks still apply.

## Supported boundary

- Two to four source-owned visits. Generic labels use the existing activity vocabulary. An exact named venue needs an explicit visit cue. Provider identity verification remains a later step.
- Complete comma or conjunction lists, explicit `then` and reviewed arrows, and whole-word Roman-script Hindi `aur` between owned visits. Optional items retain their place when selected. The leading optional form requires an explicit connector such as `then`.
- Scoped `before` or `after`, a separately delimited required third visit with `whenever convenient`, and the frozen list grammar's independently flexible and explicit unordered forms. Contradictions and ambiguous interactions between explicit connectors and flexibility are blocked.
- Bounded terminal clauses for an exact destination phrase, a single date in a known calendar, explicit driving or walking, a named final destination, or return to the confirmed origin. A `within` cap attached to an explicit origin return is a maximum for the entire outing. A missing date or search area can be requested by the advanced session.
- Unknown language, unconsumed clauses, pending snapshots, manual overrides, ambiguous names, financial budgets, unsupported transport, visit-duration and clock-window forms outside the supported grammar remain blocked. The original extraction is still available to the caller. Unsupported constraints are never removed to obtain a handoff.

Accepted fixtures include “Arcade, bowling, dinner, movie,” “Maybe skating, then lunch,” “Museum, maybe bowling, dinner,” “Bookstore and maybe tea,” “Pharmacy before bank, tea whenever convenient,” and “Arcade aur bowling in Hyderabad.” Refused fixtures include “Tea as well as bowling,” “Tea aurora bowling,” a forward edge on an explicit any-order request, competing directions, and a partial graph that omits a proved visit relationship. The five original cases keep their original expected results.

## Planning and evidence

The synthetic advanced sessions exercise a complete graph, optional selection, flexible placement, repeated visits, named venue identity, confirmed-origin and terminal constraints, unreachable required routes, and the existing selected-itinerary save and reopen mapping. The router computes transitive predecessors before it filters optional visits. Omitting the middle visit preserves the required order on both sides. For a new walking outing, missing dwell left the whole-trip verdict unverified, explicit dwell exactly met the inclusive 45-minute cap, and increasing dwell by one minute refused the route. A separate source-named library stayed a final destination and produced the corresponding final leg. These tests use no external venue, route, model or database service.

The development result is a statement about supported source meaning and compatibility with the existing handoff. Venue identity, route reachability, whole-trip timing, and plan publication require their own evidence and gates. Same-venue repeats still face the existing unique venue assignment constraint. Pending/manual workflows, broader wording and constraints, and a production entry point remain outside this checkpoint.

## Reproduce the focused checks

```sh
WHERETO_AI_WARMUP_DEV=0 backend/.venv/bin/python -m unittest backend.test_v51_ordering_preservation -v
```

The production interpreter, frozen V5.1 policy, reviewed prompt, historical evaluator and paid halt remain unchanged. The frozen paid evaluator still enforces its original source pins.

## Verification results

- All 12 repair tests passed, including the five original cases and new source and planner fixtures. The focused backend run passed 276 of 292 tests with 16 opt-in skips.
- Bounded backend discovery attempted the complete inventory of 1,459 tests in two passes with 330- and 210-second limits. It finished 1,336, with 1,299 passes, 37 opt-in skips and zero failures or errors. The first attempt at the bounded runner discarded custom fixture suites and was replaced before counting results. The final 123 incomplete tests belong to six historical synthetic suites. Their exact IDs and the interrupted test are recorded in the [verification inventory](task52-v51-ordering-generalization-verification.json).
- All 285 frontend tests, lint, TypeScript, build, handbook link and code-reference checks, and the credential scan passed.
- Read-only verification before and after matched journal SHA-256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`. The ten attempts, $0.047366625 accounting, corrections, persistent halt and all 324 private files remain intact.
