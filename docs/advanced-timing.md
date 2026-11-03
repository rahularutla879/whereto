> Current Task 50E: approved local website and version 2 saving integration is implemented. Initial milestone descriptions below are historical; see [current flow, gates and limits](advanced-integration.md).

# Task 50D — whole-journey timing

Backend development/test evaluation only. Task 50E website integration and advanced
saving, and Task 51, remain unstarted. Ordinary plans and saved-plan contracts retain
their existing behavior. This does not release advanced cards or claim reservations.

## Audit and reuse

| Existing component | Timing use |
| --- | --- |
| `Journey`, `Duration`, `Deadline`, indexed `RequestedStop` | Preserve source text, relations, occurrences, required/optional status, ordering and endpoint without reinterpretation. |
| `InterpretationContext`, deterministic calendar clock parser | Add explicit departure minute/source and timezone basis to the advanced handoff. Default 10 AM, day parts and earliest-start windows never supply a departure. No Qwen schema/model/output/context-window change. |
| `AdvancedRouter`, `AdvancedRoutingResult`, validated route topology | Read the active backend computation through `timing_snapshot()`. Recheck resolver gate, expiry and unchanged resolution before every evaluation. No routing or resolution repeats. |
| `RouteLeg.duration_nanoseconds`, provider/mode/status | Use exact Decimal seconds, original directional evidence and every first/inter-stop/final leg. Driving and Walking evidence remain separate. |
| Scoped Task 50C travel checks | Retain Strict/Flexible, exclusivity, preferred/effective maxima and total-between scope separately from total elapsed duration. |
| `feasibility._local_instant`, `_hours`, `EvidenceStop` | Reuse unique local-wall-clock validation, fresh dated periods, seven-day coverage, date-specific/special/overnight/24-hour handling and conservative missing-hours behavior. |
| `planning_hours.venue_hours` | Existing Task 50C whole-date closure exclusion remains in force. No additional hours retrieval, field mask, tier or Details call. |

The prior evaluator required already supplied arrival/departure pairs and addressed
travel/hours rather than whole journeys. The new layer supplies justified schedules
from route and dwell evidence; it does not change that ordinary evaluator or planner.

## Trusted typed contract

```python
from datetime import datetime, timezone
from backend.advanced_timing import evaluate_advanced_timing

# router is the existing server-owned AdvancedRouter after router.plan(...).
result = evaluate_advanced_timing(router, evaluated_at=datetime.now(timezone.utc))
```

Do not enable live flags to exercise this function. Tests use invented Places/Matrix
responses and refuse real HTTP sends. There is no HTTP timing endpoint or client
route-evidence input. A serialized route or timing DTO is never an authority.

`AdvancedTimingResult` retains the routing status/reasons, destination calendar,
timezone basis, aware evaluation clock, up to three `TimedCandidate` results and
explicit zero incremental requests/cost. Each candidate has its original candidate
index and full validated Task 50C route snapshot: selected IDs/facts/provenance,
source journey, actual ordered visits/legs, scoped checks, missing leg indexes,
required/optional status, original omissions/reasons, origin confirmation and ending.
The route snapshot's `temporal_status=not_evaluated` describes the original Task 50C
snapshot; the sibling typed timing fields contain Task 50D's verdicts. It remains
`execution=unavailable` throughout.

`DurationRange` represents nonnegative Decimal-second lower and nullable upper
bounds, with explicit upper exclusivity. Decimal values serialize as strings to
retain precision. A null upper bound is unknown, never zero. `TimedVisit` associates
the original dwell constraint/bounds, arrival/departure `Projection`, hours verdict,
reason, periods observation timestamp, venue timezone and special-day evidence with
the unchanged occurrence/Place ID. Candidate output separates travel, dwell and
elapsed ranges, start evidence, deadline, final-arrival projection, routing,
travel-preference, hours, duration, deadline and overall verdicts. Reasons have
machine codes, states, occurrence references and plain explanations.

Validation rejects empty/reversed/nonfinite ranges, changed occurrences/dwell,
inconsistent sums/projections, impossible chronology and contradictory component or
overall verdicts. Task 50C still rejects missing/duplicated topology, cross-mode
legs, omissions of required stops and violated precedence. Reads return independent
copies. Provider content remains transient; the private interpretation context is
excluded, and returned origin metadata contains no coordinates, address or private
Place ID. Public venue coordinates/facts in the inherited internal route snapshot
are not private origin evidence. Never log or persist these objects.

## Duration policy

| Explicit dwell relation | Hard bounds in seconds | Meaning |
| --- | --- | --- |
| exact N minutes | [60N, 60N] | Fixed user-specified duration, not a provider reservation. |
| minimum N | [60N, unknown] | A proven lower bound; not an exact visit. |
| maximum N | [0, 60N] | A user-specified upper bound, not a guaranteed actual duration. |
| under N | [0, 60N) | Strict upper bound. Under zero is contradictory and rejected. |
| approximate N | [0, unknown] | Retained soft estimate, never a hard numeric bound. |
| unspecified / quick coffee | [0, unknown] | No invented numeric duration or activity default. |

Zero lower bounds are mathematical nonnegativity only. They never establish that
an unspecified visit takes zero time or that an optional visit fits. Explicit upper
bounds can establish compliance when the entire bounded schedule fits; minimum-only
or unspecified dwell cannot establish a finite completion upper bound. No positive
minimum, waiting, buffer, automatic truncation or venue-specific duration is added.

Complete travel sums every selected verified directional leg exactly once, including
required returns or named-endpoint arrival. Missing/error legs retain the known
subtotal as a lower bound and null complete upper. A provider-verified unreachable
leg is a proven routing failure. Outbound durations never stand in for return legs.
Surprise-style routes with no confirmed-origin obligation begin at the first activity;
no origin-to-first leg is invented. Final endpoints are arrival obligations with no
invented activity dwell. Named-endpoint service/visit-hours compatibility remains
unverified because an endpoint visit duration/service requirement is unspecified.

Elapsed bounds equal travel plus every included dwell. No ranking, reordering,
replacement, optional dropping or rerouting occurs. Omission reasons remain Task
50C's identity/closure/routing-applicability reasons, never invented time pressure.
Included optional stops can cause proven infeasibility or uncertainty; Task 50E may
later choose an independently evaluated route that omits the optional stop.

A hard inclusive maximum passes only if the complete upper bound is at or below it;
an exclusive maximum passes only below it (an equal exclusive upper bound also fits).
A lower bound above an inclusive maximum, or at/above an exclusive maximum, proves
failure. An overlapping or unbounded range is unverified. Whole-trip exact/minimum
relations are checked in both directions as appropriate. Approximate whole-trip
budgets are soft preferences, retained separately without becoming violations.

Examples with a 45-minute maximum:

- 2 minutes travel + exactly 43 minutes dwell = 45: duration feasible; under 45 fails.
- 2 minutes travel + minimum 45 minutes dwell: infeasible, even with missing hours.
- 32 minutes travel + exactly 5 at ATM + unknown grocery dwell: lower bound 37;
  at most 8 minutes remain, but completion stays unverified.
- 2 minutes travel + maximum 50 minutes dwell: unverified, rather than assuming
  either a 0-minute or a 50-minute actual visit.

Overall `feasible` requires all applicable hard timing components to be established.
`infeasible` wins when any mandatory component is proven violated, despite other
unknown evidence. Otherwise the result is `unverified`. Component `feasible` for an
absent/soft-only duration or deadline means no applicable hard constraint; it does
not by itself establish overall feasibility. A fresh-hours, explicitly anchored,
exact 17-minute trip is feasible under these conditional estimate semantics;
missing hours keeps the same duration-feasible route overall unverified.

## Clocks, deadlines and precision

Only explicit `start [at]`, `starting [at]`, `leave [at]` or `depart [at]` clock wording
with an unambiguous existing clock parse qualifies as a departure. Conflicting clocks,
`after`, a general `from ... to ...` availability window, defaults and day parts do
not. The advanced interpretation handoff retains the numeric minute and matching
clock-only source. This is a conservative grammar; unsupported departure wording
needs clarification in future integration. Existing source grounding and calendar
issues still apply; no extra model call is made.

A valid destination-calendar timezone basis is required. Browser-reported nearby
calendars and unknown-location UTC fallback remain explicitly distinguished and do
not establish a destination clock anchor. Trusted backend callers must supply this
basis deliberately. Repeated or nonexistent DST wall times yield no anchor; no fold
is guessed. Elapsed additions use UTC instants, then convert back to destination
local time, preserving midnight and DST transitions.

Deadline clocks apply to the entire journey finish, including the final leg. `by`
is inclusive; `before` is exclusive. Without a valid start, deadline status is
unverified. A same-date deadline clock preceding departure asks for overnight-date
clarification rather than rolling forward. Explicit ISO dates or explicit next/
following-day wording in the preserved deadline source can identify a different
deadline date; unsupported date wording remains unverified. An explicitly dated
past deadline is infeasible. No original date/clock/source constraint is rewritten.
The ordinary single-day planner's overnight limitations are unchanged.

Projections retain exact Decimal offsets as their authoritative evidence. Earliest/
latest aware clocks enclose those offsets with outward microsecond rounding; an
exact nanosecond offset may therefore have a one-microsecond clock envelope. Hard
comparisons always use Decimal offsets, never rounded clocks. Bounded dwell produces
ranges; unknown unbounded dwell removes all later latest clocks. Later earliest
clocks are labeled lower bounds, not exact arrivals. Without an anchor, all clocks
are null. A final-return/final-destination finish is distinct from the last activity's
departure. Every projection is explicitly an estimate from routes/user constraints.

## Hours and uncertainty

Evaluate visits in each venue's actual provider timezone using the existing `_hours`
policy: provider provenance, original periods timestamps, freshness, applicable dated
seven-day coverage, nontruncated periods, special days, 24-hour sentinel and overnight
periods. Typical weekly hours and OPERATIONAL status never prove visit compatibility.
Missing, stale, truncated, out-of-coverage, ambiguous-DST or absent-timezone evidence
stays unverified, not closed or provider failure. No booking/session/inventory claim.

If fresh opening periods cover the entire arrival-to-departure envelope, all bounded
visits fit. An exact visit conflicting with current hours is infeasible. For ranges,
a conflict in the nonempty mandatory core (latest arrival to earliest departure)
proves failure; an envelope failure alone remains unverified. Zero-duration visits
receive no invented positive minimum or automatic hours pass. Unknown unbounded
visits cannot establish complete hours compatibility; an explicit minimum can
still prove an hours conflict through its mandatory core. Existing current-date closure
filtering in Task 50C remains intact.

## Verification and reproduction

Working folder: `/Users/rahularutla/Documents/whereto`.

```sh
backend/.venv/bin/python -m unittest backend.test_advanced_timing -v
npm run test:backend
npm test
npm run typecheck
npm run lint
npm run build
backend/.venv/bin/python -m pip check
npm ls --depth=0
npm audit --omit=dev
python3 scripts/security-scan.py
```

The focused suite uses 51 test methods with numeric subcases covering the requested
60 scenarios: exact/inclusive/exclusive totals; all dwell relations/unknown visits;
all leg roles, modes, missing/unreachable legs and malformed topology; fixed/partial/
flexible ordering; optional inclusion/omission/failure; explicit/absent/ambiguous
anchors and deadline equality/overnight/DST; current/special/24-hour/overnight/
stale/truncated/missing/out-of-window hours; bounds, precision, source preservation,
no default durations/timestamps, unverified evidence, gates, copy isolation and no
network/model/storage during evaluation. Existing suites cover ordinary planner,
clarification, public API and saved contracts. Actual browser evidence and final
suite counts/performance are recorded in HANDOVER.md.

Timing evaluation makes **zero incremental Google requests**, has **$0 incremental
estimated Google cost**, and reruns neither Qwen, resolution nor Matrix calculation.
No live provider request, SQL test/write, migration, persisted provider data, new
service, field mask, quota/billing/security/private-profile change is introduced.
Benchmarks print 100 local evaluations for a two-stop round trip and a four-stop,
three-candidate result, including trusted snapshot validation. They exclude prior
routing/resolution/Qwen and are not live/end-to-end or controlled CPU measurements.
No model memory settings change.

Task 50E still owns complete website execution, final option selection/filtering,
clarification/edits, safe advanced saving/reopening and end-to-end integration. In
particular it must gather missing dwell/anchors, verify nearby destination timezones,
resolve unsupported deadline dates and endpoint service semantics, preserve unknown
availability and honor every timing component. This task makes no new interpretation
accuracy claim and does not begin Task 50E or Task 51.

Final acceptance: backend 851 reported (817 passed, 34 opt-in skips), frontend 239/239,
focused 194/194; JSON midnight/DST round trips 3/3. Typecheck/lint/build/dependency/
audit/secret/diff checks pass. Timing overhead for 100 evaluations each: two-stop
median 0.590 ms/max 1.772 ms; four-stop/three-candidate median 2.512 ms/max 33.912 ms.
Desktop 1280/mobile 390 functional and responsive checks passed; ordinary saved UI
used an in-memory repository harness, not hosted SQL. No complete accessibility
audit or live provider verification is claimed. See HANDOVER.md for precise scope.


## Task 50E — advanced application integration

Task 50E displays these verdicts, filters infeasible options and accepts occurrence-specific missing-duration/explicit-departure answers. Reevaluation reads trusted route snapshots with no new Matrix/Qwen calls; approximate answers do not establish hard feasibility. [Contracts, limits and verification](advanced-integration.md). Earlier task-pending statements above are historical. Task 51 remains unstarted.


## November 3 — Task 50E acceptance repair

The owner-reported ordinary interpretation and advanced UI regressions are repaired. Both paths share the original form/card/history/save controls; advanced actions now support bounded combinations, same-area discovery and explicit scoped travel exceptions. Required identities, ordering, returns, whole-trip timing, original budgets and private persistence protections remain enforced. No migration, profile/Cloud/billing/model change or Task 51 work. [Root causes, parity, bounds, evidence and remaining limits](task50e-repair.md). Earlier one-page limitations describe the original checkpoint.
