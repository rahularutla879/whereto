# Task 50E final acceptance repair — November 4, 2026

Continuation of `141a265`; no new roadmap task. Task 51 remains unstarted.

## Durations and shared cards

The old formatter used a floating-point minute remainder (`minutes % 60`) directly in text; other ordinary travel and recommendation strings also interpolated raw minutes. Fractional provider seconds therefore produced strings such as `~2h 0.1666666666666714m`. `lib/duration-format.ts` now owns numeric UI duration presentation, including the legacy export, first leg, ordinary/advanced route totals, recommendations and saved fictional travel. The backend's small `display_duration.seconds_text` adapter follows the same policy for server-generated explanations, with a cross-language test.

Nonnegative known estimates round to the nearest second, with carry into minutes/hours (`10 sec`, `1 min`, `59 min 19 sec`, `1 hr 59 min`, `2 hr 10 sec`). Displayed lower bounds round down and upper bounds up; unknown upper bounds stay unknown. Exact, at-most, minimum, under and approximate user relations are retained. No formatted value participates in enforcement: Decimal/nanosecond directional route evidence, inclusive/exclusive travel limits, dwell bounds and deadlines are unchanged. Fractional first-leg display no longer silently rounds up to a whole minute. Clock text also avoids fractional minute artifacts.

Both paths retain the original PlanCard artwork, typography, actions, compact ordered details and underlined Maps/contact links. Unknown hours without any useful current/typical evidence are explained once in the existing shared disclosure instead of repeated at each stop. Actual closed hours, dated periods, typical/special-day information and stop-specific exceptions remain visible. Compact contact panels retain contact/booking notices without repeating venue names, addresses or ratings.

## College-now diagnosis and recovery

One actual installed local Qwen call for each exact owner request used the unchanged original prompt/schema/options/model policy, with Google sends blocked. College extraction took **12,200.783 ms**: exact college identity, required coffee, college-before-coffee order, and `departureNow=true` survived. The initial destination/timezone remained unresolved until verified named-place resolution, as intended. Grocery/pharmacy/optional-coffee extraction took **17,391.687 ms** and correctly retained coffee optionality, return to origin and the inclusive 90-minute maximum. Recorded raw outputs are regression fixtures; neither is a live Google venue/hours/traffic verification. These two measurements are not a latency improvement claim.

The old pipeline had two rejection paths: whole-date closures could discard a mandatory named candidate before routing; projected-arrival/visit closures became generic “all options infeasible” copy. The original manual failure's provider periods, confirmed origin, projected arrival and evaluation instant were not retained. **Its historical closure verdict cannot be independently certified or called a proven timing bug.** Fresh synthetic tests establish valid rejections for closed arrival/required visit core, while stale/missing/incomplete hours remain unverified. Existing holiday, overnight, 24-hour and DST evaluation remains in force; OPERATIONAL never proves access or service.

Verified mandatory named identities now survive whole-date pruning so their projected visit can be evaluated. A failed current-hours check names the affected venue and offers two main-form actions:

- **Choose another time or date** opens preferences and focuses Date. A structured date/departure edit preserves the source request, exact named identity, origin, other activities, order and limits, then checks timing again. Compatible route evidence and resolved venues are reused. Explicit manual-date provenance also prevents “now” from overwriting an edited future date during model-free session renewal. Future access is never guaranteed.
- **Proceed anyway** accepts only an opaque token offered by the active trusted backend session. The token binds occurrence, verified Place identity, destination calendar/date, departure intent, the affected visit’s effective dwell, confirmed routing configuration, projected offsets and the current hours observation. No browser Place ID, hours claim or arbitrary route is accepted as authority. Only that failed mandatory named-visit hours component becomes an explicit unverified exception; its raw failed verdict is retained. The card says: “Closed at the planned visit time. Included at your request; access is not confirmed.”

Other cafés still obey their own hours checks. Required stops/order/return, all directional traffic-aware or walking evidence, scoped Strict/Flexible maxima, total duration and deadlines remain independent. Active permission is visible/removable in Set preferences. Compatible regeneration/exploration retains it; changed date, departure, affected visit dwell/schedule, identity, route offsets, hours observation or routing assumptions clears/requires reconfirmation. Expired sessions cannot replay an old offer token as authority.

Saving adds only defaulted app-owned `closedVisitOccurrences` to v2 requirements, validated against selected required named occurrences. Existing selected stop references bind the historical choice; the exception stores no Google periods, observations, venue facts, route metrics or private origin. Reopening says it was a choice for the original visit, not that today's venue is open/closed. v1 and older v2 remain compatible; selected-only hashed 30-day links, restricted login, forced RLS and verified TLS are unchanged. No migration.

## Optional coffee: measured diagnosis and selection

A disposable interpreter loaded the committed baseline routing/timing/session code to compare the same invented ten-venue-per-activity fixture. Google HTTP was blocked; saving was stubbed only for this ranking comparison. These are reproducible synthetic counts, not inferred owner-session statistics.

| Same dense grocery/pharmacy/coffee fixture | Baseline `141a265` | Repaired |
| --- | ---: | ---: |
| Retained venues per activity | 10 / 10 / 10 | 10 / 10 / 10 |
| Complete assignments checked initially | 15 | 18 |
| Checked coffee-inclusive assignments | 4 | 10 |
| Initial coffee-inclusive recommendations | 0 | 3 |
| Missing coffee-duration question | absent | present |
| Text Searches | 3 | 3 |
| Matrix billable elements | 27 | 27 |
| Matrix HTTP batches | 10 | 7 |

Baseline coffee was discovered and routed, not proven impossible. The four inclusive routes had unknown coffee dwell and unverified duration, while no-coffee duration checks fit; all overall states were unverified because hours/clock evidence was incomplete. Shortest-first ranking selected 360-second no-coffee routes over 480-second coffee routes. Missing dwell questions were collected only from displayed routes, so coffee's missing time never surfaced. The geographic beam also favored shorter inclusion patterns before Matrix admission.

The bounded beam now balances occurrence-inclusion patterns before repeatedly using one pattern/venue. Recommendation ranking keeps hard eligibility, verified feasibility and scoped preference classes first, then considers optional satisfaction, with shortest verified route travel within comparable classes and existing diversity. It does not reserve an arbitrary card quota. No-coffee alternatives remain reachable; no required stop is dropped and no deadline is relaxed. Unknown optional dwell in any eligible checked route is asked in the existing main-form controls, even if that route is not selected. Unknown is never treated as zero or as a proven fit.

With exact grocery 20 + pharmacy 20 + coffee 10, the fractional browser fixture returned a complete round trip of about **57 min 57 sec**, including about **7 min 57 sec** travel. Coffee 20 produced about **1 hr 7 min 57 sec**; editing back to 10 restored the shorter duration and cleared stale cards/history. Coffee 80 made inclusive routes exceed the unchanged 90-minute maximum; recommendations retained groceries, pharmacy and return, with a checked-pool-specific time-budget omission explanation. Other eligible no-coffee alternatives can be offered even when coffee fits. Closed flexible cafés are excluded normally; missing hours remain unknown.

Show different options and Search more nearby places retain optionality, exact mandatory requirements, source geography, return, mode, Strict/Flexible semantics, timing inputs and page history. Additional discovery reevaluates inclusive assignments. Flexible affects its existing scoped travel maximum only; it cannot waive 90 minutes. Bounded coverage is reported honestly and does not prove that all other venues/routes are impossible.

Structured edits use no model. The browser's 10 → 20 → 10-minute sequence added **0 AI, 0 Text Search, 0 Matrix elements and 0 contact calls**. The dense ten-edit backend benchmark and final suite measurements are recorded in HANDOVER.md; these are local fixture evaluations, not promised live latency.

## Verification and cost boundaries

All automated Google transports are replaced with invented provider-shaped responses and real sends blocked. The only actual AI use was the two explicitly identified local Qwen calls above; browser extraction uses recorded fixtures. Actual hosted PostgreSQL is separately exercised for restricted selected-only saving, restart reads, legacy compatibility and exact disposable cleanup. No live Google opening-hours, traffic or consumer Maps comparison is claimed.

The existing TRAFFIC_AWARE Driving / Walking separation, Pro element accounting, masks, quotas, concurrency, no-retry policy and bounded Matrix/search limits remain unchanged. Pattern balancing can change which assignments and HTTP batches fit within those limits; in the measured dense fixture billed search/element counts were identical. A mandatory named venue previously rejected before routing may now use bounded authorized Matrix evidence to establish arrival and offer a visit exception. That is not a new API/tier or quota increase. Compatible Proceed anyway and timing edits add zero provider calls in the tests. No Cloud billing, quotas, IAM, credentials, owner profile, provider, model download or dependency version was changed.

Desktop 1280px and mobile 390px browser checks cover closure naming/actions, exact college plus café, permission removal, date focus/recovery, optional coffee fit/unknown/no-fit/edit/exploration, ordinary dinner/bowling and compact details, and selected advanced saving/new-tab reopening. Actual document widths were checked; screenshots and final suite totals are in HANDOVER.md. Native browser date/time fields needed real arrow-key events to commit automation edits; a fill-only transient DOM value was not counted as a working edit. Earlier stale-copy assertions were updated, and failed intermediate test runs are not counted as passing.

Known limits: historical live SUNY closure evidence is unavailable; current hours do not prove appointments/public entry; finite candidate/Matrix coverage is not exhaustive; current route estimates cannot guarantee future arrivals; Qwen latency remains an earlier open acceptance limitation. Task 51 remains unstarted.

Final checks: backend **939 reported (902 passed, 37 opt-in skips)**; frontend **271/271**; focused backend **160 reported (142 passed, 18 hosted skips)**; authorized hosted suite **59/59**, with exact committed cleanup. The eight opt-in startup lifecycle checks were not rerun; startup code is unchanged. TypeScript, ESLint, production build, pip consistency, zero-vulnerability npm production audit, configured-secret scan and full diff/new-file review passed. The baseline optional WASI dependency-tree mismatch remains documented; no packages changed. One ten-edit local fixture run measured median **12.915 ms**, maximum **33.533 ms**, with zero incremental model/Google calls. Final browser expiry recovery cleared old closure authority, requested fresh consent without another Qwen interpretation, and retained accepted permission during a later coffee-only dwell edit.
