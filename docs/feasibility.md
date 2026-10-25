# Task 44 — provider evidence feasibility

`backend/feasibility.py` is a pure evaluator, separate from discovery, authentication,
transport, candidate generation, ranking and rendering. It performs no I/O and has
no public endpoint. The website continues using its existing fictional planner.
No new dependency, provider request, field mask, pricing tier, quota, credential,
billing setting or live-access default changes.

## Interface and scope

Construct a `FeasibilityInput` with a candidate ID, one to four ordered
`EvidenceStop`s containing Task 41 `VenueFacts`, explicit aware arrival/departure
instants (or both absent), requested `drive`/`walk` mode, Task 43 `RouteLeg`s and
an explicit `evaluated_at` clock. Optional decimal-minute limits are
`max_leg_minutes`, `max_total_minutes` (inter-stop only), and
`max_first_leg_minutes`. Zero is a real limit; absent means no cap.

`evaluate_feasibility(input)` returns the candidate ID, overall state,
`travel_state`, `hours_state`, and individual checks. Every check carries a kind,
state, concise reason code, stop index and input-path evidence reference. No raw
payload or precise starting coordinates are copied into results. Results remain
transient; there is no logging or persistence. References describe supplied input,
not an independent audit of provider authenticity.

`filter_feasible_candidates(inputs)` partitions results into `feasible`,
`infeasible` and `unverified`, preserving input order within each group. Keep the
original candidates by their IDs. There is no score, top-three selection, activity
reordering or relaxation of hard limits.

- **feasible**: all evaluated travel/hours checks fit the supplied applicable
  evidence. This is scoped feasibility, never a guarantee of overall availability.
- **infeasible**: at least one demonstrated conflict. This always takes precedence
  over other unknown checks and cannot be overridden by preferences.
- **unverified**: no proven conflict, but required evidence is unavailable or
  uncertain. Preserve these provisional candidates for later verification.

Budgets, capacity, booking availability, prices and recommendation scores are
outside this evaluator. It checks a supplied schedule; it does not generate one.
Existing Task 27 rules were inspected but not reused: their fictional quotes,
integer minute windows and same-day cutoff do not represent these provider facts.
The existing hard-violation-over-unknown policy is retained. Existing shared
contracts, event-category definitions and normalized evidence are reused instead.

## Travel

Each required leg is matched by **origin ID, destination ID and actual mode**.
Reverse directions never substitute. Missing/mismatched modes, duplicate matching
legs, `unknown`, and `error` evidence remain unverified; no unknown becomes zero.
A Google `unreachable` result rejects the candidate. Google success must have the
appropriate driving/walking estimate type. Provider venue evidence must be
`google_places` / `provider_supplied`; fictional records cannot silently enter this
path. Synthetic tests deliberately model provider-supplied facts and are not live
verification.

Compare duration seconds directly with `Decimal(limit_minutes) * 60`, inclusively.
The matrix parser now additionally retains the protobuf duration as exact integer
`duration_nanoseconds`; hard comparisons prefer this value. Existing seconds,
minutes and distances remain compatible. For older supplied legs without nanos,
use their supplied seconds precision, never rounded display minutes. For example,
600 seconds passes a 10-minute cap; 600.000000001 seconds fails. Distance is never
converted into duration. Negative/invalid/nonfinite limits are rejected.

Sum only known inter-stop seconds. A known subtotal already exceeding the total
cap proves a violation even if another leg is missing. An incomplete sum never
becomes fully verified. Available transfer time is the absolute UTC difference
between consecutive departure/arrival instants, preserving microseconds; a route
that cannot fit rejects the schedule. Explicit overlapping stops reject even when
their route is unknown. Missing schedule times remain unverified.

An explicitly supplied `AuthorizedStart` adds exactly start → first stop. Its
separate cap applies there; this trip is excluded from the inter-stop total and
per-leg cap. Missing/failed/unreachable first-leg evidence follows the same rules.
Without an authorized start there is no first-leg obligation, even if a first-leg
cap was provided. No user position, city center, return journey or proximity claim
is invented. There is no location-permission UI.

A supplied local same-location leg is accepted only with identical IDs, zero
seconds/meters and the Task 43 local-identity status/provider/estimate type. No
zero leg is manufactured. Caller aliases with different IDs require explicit
canonical identity resolution before evaluation; otherwise local alias evidence
stays unverified.

## Opening hours and dates

The evaluator consumes only already supplied optional hours; it never buys them.
Current discovery does not request these Enterprise fields, so its ordinary
minimal records will generally remain unverified for hours.

Reliable current-hours evaluation requires all of:

1. Google provider-supplied facts and a valid IANA `timeZone`.
2. A non-null `currentOpeningHours.periods` snapshot, with its specific
   `observedAt['currentOpeningHours.periods']` receipt timestamp.
3. `EvidenceStop.hours_request_date`: the trusted original request date in that
   venue's timezone. The existing normalizer records receipt, not request time.
   A future caller must carry this context alongside that same snapshot; do not
   infer it from receipt, `openNow`, a later partial update or the outing date.
4. The receipt is no later than evaluation and on its venue-local calendar date;
   its local date is the request day or the following day. This conservative
   freshness policy deliberately leaves older snapshots unknown.
5. The complete activity falls after evaluation and inside the seven local days
   starting at request-day midnight. Outside that window is unknown, not closed.

Google documents current hours as seven days including the request day, with
exceptions incorporated and cutoffs potentially truncated. See the official
[Place/currentOpeningHours and Period reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places).
Local receipt alone cannot establish the exact request day across midnight.
Absent trustworthy context therefore remains unverified. This Task adds no
transport/enrichment adapter to acquire it automatically.

Every ordinary current period must have both exact endpoint dates, complete clock
values and untruncated endpoints, all within the covered window. Undated,
truncated, open-ended (except Google's unique Sunday 00:00 always-open sentinel),
invalid or ambiguous periods leave the entire snapshot unverified. Explicit empty
periods mean closed within a proven applicable window; absent periods mean unknown.
Localized weekday text, UTC offset alone, next-open/close values and `openNow`
never supply a missing executable schedule.

Opening intervals are merged in UTC. The whole arrival-through-departure interval
must be covered without a gap; departure exactly at closing is allowed. Closing
during the activity, arriving before opening or crossing a closed gap rejects the
candidate. Multiple touching intervals can cover one activity. Overnight periods
retain their actual endpoint dates, including weekend and month boundaries.

IANA timezone conversion applies the offset for each date. All elapsed-time and
coverage comparisons use UTC, including spring-forward and fall-back changes.
Aware stop instants can specify either repeated-hour occurrence explicitly. An
opening-hours boundary in a repeated or nonexistent local hour remains unknown
rather than guessing a DST fold or repairing the time. UTC offset alone cannot
replace a timezone. A seven-day coverage boundary that is itself ambiguous also
remains unknown.

Regular weekly hours are preserved as `regular_hours_only` evidence, always
unverified for a dated outing. They cannot rule out holiday or exceptional hours,
so this evaluator does not reject or confirm future plans based on them. Applicable
complete current hours take precedence over regular hours, including special-day
closures. Incomplete current hours do not fall back to regular hours to manufacture
certainty. This conservative policy may retain a normally closed venue provisionally.

Opening a building does not prove a movie screening, game, concert, theater session,
ticket or reservation. Movie and existing event categories always add
`session_not_verified`; no sessions or start times are invented. Integrating actual
session evidence is future work. Even a fully hours-verified event venue remains
overall unverified, unless a separate known violation already rejects it.

## Validation and boundaries

`backend/test_feasibility.py` uses invented normalized responses and Task 43 matrix
fixtures, forbidding sockets, route calculation, provider transport and token access.
It covers both modes/directions, nanosecond boundaries, caps, failure/missing evidence,
starts, transfers/overlaps, current/regular/missing hours, closures and gaps,
overnights, date coverage, DST, session uncertainty, source isolation, precedence,
stable filtering and serialization. Existing backend tests include exact fictional
catalog/planner-output fingerprints. No existing planner helper or behavior changed.

Task 45 will implement accurate source labeling and distinguish verified evidence,
estimates and unknown availability. Task 46 will integrate real venue/route data
with the planner while retaining mock mode. Neither is implemented here.


## Task 45 display boundary

Task 45 is now complete. `feasibility_labels` translates this evaluator's supplied results into fixed, safe human-readable messages, preserving every check state and stop index without rerunning decisions. The original result retains exact backend reason/evidence references; public labels exclude them. A violated constraint stays rejected alongside unknowns, and satisfied checks do not verify prices, reservations or availability. [Evidence contract and Task 46 guidance](evidence-labeling.md). Task 46 remains unstarted.
