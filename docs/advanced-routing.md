Current Task 50E supersedes historical traffic-unaware notes below: every Driving leg requests `TRAFFIC_AWARE`; Walking has no routingPreference. Current request-time semantics, nanosecond limits, fallback provenance, five-minute cache compatibility and Pro accounting are shared by ordinary/advanced paths. Origin/inter-stop/return/final legs remain directional; changed modes, origins or selected identities cannot borrow incompatible evidence. Bounded discovery is unchanged; convenience/novelty order only already eligible combinations. [Current policy and verification](task50e-consolidated.md).

> Current Task 50E: approved local website and version 2 saving integration is implemented. Initial milestone descriptions below are historical; see [current flow, gates and limits](advanced-integration.md).

# Task 50C — advanced route construction

Backend development/test contract only. Ordinary advanced requests still show the
Task 50B explanation; they produce no advanced cards or saved advanced documents.
Task 50D timing is implemented separately; Task 50E integration/persistence remains unstarted.

## Audit and minimum extensions

| Existing interface | Reuse / extension |
| --- | --- |
| `StopResolver`, `ResolvedJourney/Stop/Candidate` | New `routing_snapshot()` returns a revalidated copy of the current server-owned result, under the existing development switch and ten-minute expiry. No client-resolved DTO is accepted. |
| `Journey`, `RequestedStop`, `InterpretationContext` | Original source occurrences, required/optional identities, durations, precedence, endpoint, whole-trip budget/deadline, destination calendar, mode and scoped preferences survive. The context gains the existing legacy per-leg/total-between caps and exclusivity from the same source grammar/manual override, closing a previously missing handoff field. No Qwen or discovery call in routing. |
| `AuthorizedStart`, `RoutePoint.from_venue` | Same explicit manual/device-origin boundary and verified Google identity bridge. Origin remains independent of destination; no origin/home inference or geocoding. |
| `GoogleRouteCalculator` | New bounded `DirectedRouteRequest` / `calculate_directed()` feeds the same batching, normalization and dispatch implementation. The linear API and ordinary planner retain their behavior. |
| `plan_matrices`, exact pair batching | Extracted `batch_pairs` accepts the selective directed union. Rectangles add no unwanted cells; identical provider-waypoint aliases reuse evidence. Equal coordinates alone do not establish the same venue. |
| `RouteLeg`, `parse_matrix` | Exact nanosecond durations, distances, Google provenance, local same-place evidence, missing cells, per-element status and sanitized errors retained. No raw Google response returned. |
| `ProviderBudget`, transport, cost dispatch | Same shared outing/process/minute/day/concurrency/attempt and persistent ledger admission. Whole selected plan admitted before I/O. Conservative reservations survive failure; no dispatched request retry. |
| `location_policy.exceeds/first_measure/effective_max` | Existing exact time/distance, exclusive Strict boundary and inclusive doubled Flexible maximum. No new interpretation/scoring weights in the ordinary planner. |
| `routing_shortlist`, `spatial_beam`, diversification audit | Existing linear beam expects fixed activity groups and ordinary itinerary DTOs. Advanced topology needs a small precedence-aware beam; it follows the same geographic pruning, known-evidence-first, venue-quality tie-break and deterministic diversity principles without changing that planner. |
| `planning_hours.venue_hours`, canonical `VenueFacts` | Carry current/regular periods, timezone, observation timestamps and credits. Reuse only conservative current whole-date closure exclusion; never create visit times. |

## Trusted input and output

`AdvancedRouter(resolver).plan(origin=authorized_start)` consumes the active
backend resolver object and its **same outing budget**. Existing
`WHERETO_STOP_RESOLUTION_DEV=1` is required; actual Matrix dispatch also requires
the existing Routes/local-real authorization. No new flag, public endpoint, field
mask, paid service, production capability, table or migration is introduced.
Do not enable live switches merely to exercise this contract.

The router object owns one active computation. An unchanged repeat returns a deep
copy, with no provider call. Changed inputs or resolver choices require a separate
computation and the unchanged cumulative outing budget. Expiry/gate is rechecked
on every read; provider evidence is transient, not a cross-session/disk cache.

`AdvancedRoutingResult` contains at most three `AdvancedRouteCandidate` objects,
fixed statuses/reasons, matrix reservations, bounded coverage counts, calendar
metadata and any typed `HoursExclusion` evidence. The full interpretation context
is retained internally and excluded from serialization/repr: private origin text
and home answers never enter diagnostics or a public DTO. Origin output contains
only confirmation/source/precision, with the opaque routing alias `advanced_origin`.
No origin coordinates, private Place ID, label or address are returned. Public
establishment facts and original requested phrases remain transient and traceable.
Never log or persist these internal objects.

Each candidate contains:

- Unchanged `Journey`, indexed visits with selected Google identity, original
  `RequestedStop`, kind, requirement, dwell relation, actual order and explicit
  optional-inclusion boolean; separately indexed optional omissions and reasons.
- Distinct confirmed-origin metadata and ending role: last activity, origin, or
  verified named destination. The endpoint is not an optional activity.
- Ordered origin-to-first, inter-activity and final-return/destination legs, their
  occurrence roles, mode and normalized provider evidence/status.
- Exact scoped travel checks with preferred/maximum values, actual directional
  measures and deviations, plus a separately typed total-between check.
  Original preferences are never relaxed.
- Known travel-only seconds/meters, missing-leg indexes and a nullable complete
  travel total. A partial known subtotal of zero is allowed; an unknown complete
  total is **null**, never zero.
- `route_status`: verified, unverified or beyond_limit. This is routing status,
  **not whole-journey feasibility**. `temporal_status=not_evaluated` and
  `execution=unavailable` always remain explicit.

Pydantic rejects occurrence loss, required omissions, identity/optionality changes,
repeated physical identities, missing topology, precedence/cross-mode violations,
inconsistent totals/status and travel checks that disagree with their evidence.
Resolution authority still comes from the server resolver, not schema validity.

## Ordering and optionality

One to four stops are supported; larger Task 50A/50B interpretations return an
explicit unsupported result before routing. Each occurrence keeps its own index,
even for repeated coffee labels. Named places require one resolved identity;
ambiguous/missing required places stop execution rather than causing substitution.
Brands/activities may select only approved resolver candidates. Repeated venue IDs
within a journey are prohibited; an endpoint may equal the origin or a visited
venue, because it has a distinct role and verified same-location handling.

Unspecified order retains source order without inventing optimization intent.
Fixed/partial edges use transitive predecessor closure, including paths through
an omitted optional stop. Only available topological successors may extend a beam;
cycles/conflicting modes/clarifications are rejected. Explicit flexible ordering
considers independent next occurrences. Each subset of at most four optional stops
is bounded; no required stop is omitted to fill option slots.

Candidate pools are pruned to at most four (or the smaller configured candidate
ceiling), beam width 24, at most 24 shortlisted complete distinct physical orders.
Geographic distances only prune promising assignments; they never become travel
estimates. Identical physical venue/order combinations collapse deterministically,
even if interchangeable activity occurrences could produce multiple assignments.
A greedy union admits only whole candidate topologies within **27 directed pairs**;
therefore it never spends its allowance on prefixes with an omitted required return.
This conservative ceiling also counts same-location pairs; actual billable cells
can be lower. It does not request all discovered places against every other place.

Every admitted directed pair is requested once per mode/computation. DRIVE retains
TRAFFIC_UNAWARE; WALK omits driving preferences. Outbound evidence never proves a
reverse journey. Missing origin is a separate unresolved state before provider
I/O. Home requires explicit origin confirmation plus an actual confirmed origin;
a syntactic separate home answer remains unresolved under the current resolver.
A separately verified named final location is routed exactly, without an extra
return. Ambiguous/generic endpoints remain unresolved; no new geocoder is added.

## Travel checks, ranking and uncertainty

First-stop limits apply only to the verified origin-to-first leg. Between-stop
preferences apply only to inter-activity legs, not the first/final return or the
whole trip. Legacy per-leg maxima and the separate sum-of-between-legs cap are
also enforced with exact duration evidence; unknown sums cannot pass, while a
known lower bound may already prove a violation. Manual total-travel overrides
retain ordinary precedence. Unsupported distance scopes stay unresolved.
Strict limits and Flexible effective maxima filter before option
selection. Explicit backend `allow_beyond_limit=True` returns accurately labeled
exceptions while preserving the original preference; it grants no extra budget.
Unknown legs remain unverified and cannot pass hard limits.

Rank complete verified routes first, then evidence completeness and original
Flexible preference matching, then measured complete travel seconds. Available
venue ratings break ties; missing ratings are not invented. Comparable options
within a one-minute travel band prefer less shared venue identity. Identical routes
never fill extra slots. Known missing metrics are not scored as zero; totals are
null, with a separate known subtotal for later evaluation. Optional visits can be
included or omitted according to this route cost/applicability ranking; omission
reasons explicitly avoid claiming sufficient/insufficient whole-trip time.

Application admission errors remain `application_limit`, separate from Cloud
`quota` and transport/service failures. Matrix partial responses preserve every
valid cell; missing/unreachable/error legs have null metrics. The common adapter
stops later batches after a service/quota/authentication failure without retrying;
reserved request/element counts are conservative, not receipts of successful sends.

No arrival/departure, assumed 10 AM start, dwell-time arithmetic, deadline score,
appointment, ticket, inventory or opening-at-visit claim is made. Fresh current hours
that prove closure throughout an explicitly dated outing exclude that candidate
and retain its canonical evidence. Typical/operational status alone cannot do so.
Other timing evidence remains for Task 50D.

## Offline cost and performance evidence

All provider responses are invented; real HTTP sends are refused. Existing gross
application estimate is $0.005/Matrix element, before free allowances/credits;
these reuse documented assumptions, not newly verified prices or posted billing.
Resolution costs remain separately accounted under Task 50B. Actual Google cost
for all checks is **$0**, with zero live calls, Details or additional AI calls.

| Fixture (one eligible venue per occurrence unless stated) | Reserved elements | Reserved requests | Gross Matrix estimate |
| --- | ---: | ---: | ---: |
| College → coffee | 1 | 1 | $0.005 |
| Origin → college → coffee → origin | 3 | 3 | $0.015 |
| Origin → grocery → ATM → origin | 3 | 3 | $0.015 |
| Single-store round trip | 2 | 2 | $0.010 |
| Pharmacy before bank; grocery anywhere, all three valid orders | 5 | 3 | $0.025 |
| Bank/grocery either order | 2 | 2 | $0.010 |
| Origin → bank → named station | 2 | 2 | $0.010 |
| Required grocery / optional coffee, included and omitted options | 1 | 1 | $0.005 |
| Repeated coffee, two distinct candidate cafes | 2 | 2 | $0.010 |
| Driving or Walking two-stop fixture, each computed separately | 1 each | 1 each | $0.005 each |
| Dense four activities × ten candidates; flexible round trip | 20 | 5 | $0.100 |
| Unresolved/ambiguous identity, home, origin or conflicting order | 0 | 0 | $0 |
| Application matrix admission rejection | 0 | 0 | $0 |
| Timeout on three-leg fixture (only first batch sent) | 3 reserved | 3 reserved | ≤$0.015 reserved |
| Technical worst-case ceiling | ≤27 | ≤27 | ≤$0.135 |

Forty-seven focused tests cover the requested identity/order/endpoint/mode/travel,
partial/error/admission, evidence/privacy/gate/uniqueness and bounded-work scenarios.
The ordinary planner and frontend gating also retain their full existing suites.
Twenty fresh fixture-backed round-trip routing computations measure Python routing
only, excluding resolution and Qwen. The final full-suite run measured median **0.654ms**, max
**0.982ms**; the runner prints measurements for reproduction. These numbers are
not live Google latency, a controlled CPU benchmark or end-to-end performance.
The dense fixture considers and admits 24 paths, 20 elements in five batches.
No Qwen model/schema/context/memory setting changed; Task 50A's prior warm-latency
qualification remains. No Cloud quotas, billing, credentials or ledger were changed.

Run from `/Users/rahularutla/Documents/whereto`:

```sh
backend/.venv/bin/python -m unittest backend.test_advanced_routing backend.test_routes backend.test_stop_resolution backend.test_journey -v
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

Final suite counts, actual desktop/mobile checks and scope qualifications are in
HANDOVER.md. No hosted checks are needed: persistence and its input DTOs are
unchanged. No migration, owner-plan write, RLS/TLS/runtime identity change occurred.
Task 50D now evaluates travel plus dwell, actual temporal anchors, whole-duration
and deadlines (see the update below). Task 50E must integrate verified advanced
results, clarification, edits and saving. Task 50E and Task 51 remain unstarted.


## Task 50D update — independent temporal evaluation

`AdvancedRouter.timing_snapshot()` exposes only the active server-owned computation
after rechecking resolver authorization, expiry and unchanged resolution. No route
request is repeated. Task 50D consumes its exact directional legs, all selected
occurrences/omissions, scoped checks and hours facts without reranking or reordering.
The original Task 50C snapshot retains `temporal_status=not_evaluated`; a separate
`TimedCandidate` carries Task 50D's component/overall verdicts and projections.
Travel verification alone remains insufficient. [Timing contract](advanced-timing.md).
Task 50E website execution/persistence and Task 51 remain unstarted.


## Task 50E — advanced application integration

Task 50E now invokes this router through the approved local advanced flow and displays actual ordered/return/final legs. It preserves the existing bounded work, directional evidence, required stops and Strict/Flexible checks. [Contracts, limits and verification](advanced-integration.md). Earlier task-pending statements above are historical. Task 51 remains unstarted.


## November 3 — Task 50E acceptance repair

The owner-reported ordinary interpretation and advanced UI regressions are repaired. Both paths share the original form/card/history/save controls; advanced actions now support bounded combinations, same-area discovery and explicit scoped travel exceptions. Required identities, ordering, returns, whole-trip timing, original budgets and private persistence protections remain enforced. No migration, profile/Cloud/billing/model change or Task 51 work. [Root causes, parity, bounds, evidence and remaining limits](task50e-repair.md). Earlier one-page limitations describe the original checkpoint.


## Task 50E follow-up: presentation, nearby origins and coverage

The follow-up repair removes repeated advanced card diagnostics, labels dwell answers
in minutes with explicit exact/bounded/approximate meaning, distinguishes nearby
consent from route origin and real expiry, preserves destination-local clocks,
clarifies traffic-unaware estimates and balances bounded discovery/routing across
all stop occurrences. Numeric development stage/coverage diagnostics remain private.
[Causes, measurements, safeguards and acceptance evidence](task50e-followup.md).
Task 51 remains unstarted.


## November 4 — final Task 50E acceptance repair

Shared readable duration formatting, named closed-visit recovery with explicit stop-specific permission, balanced optional-stop recommendations and editable missing coffee dwell continue Task 50E. Exact enforcement, other venues’ hours, source constraints, selected private saving and approved provider accounting are preserved. No migration, Cloud/profile/model/dependency change or Task 51 work. [Diagnosis, measured counts, trust/lifecycle contracts and verification](task50e-final-acceptance.md).


## Task 50E leg actions and optional continuation

Every actual origin/intermediate/final/return leg now has the shared directions row. Public legs use exact selected Place IDs and mode; private origin/return URLs omit that endpoint, with visible Maps picker/input instructions. No private alias, coordinates or saved route URL. Optional opportunities are checked in bounded existing-inventory continuation before repeatedly serving omission alternatives; explicit discovery prioritizes optional activities and preserves geography, required stops and return. Traffic-aware five-minute evidence, exact limits, quotas and no retries are unchanged. [Diagnosis, counts and official URL support](task50e-final-acceptance.md#november-4-continuation-from-798a3fc-return-wording-leg-links-and-optional-exploration). Task 51 is unstarted.

## Initial recommendation fill

After local timing evaluation, one or two supported initial options can trigger one selective routing stage using only remaining room in the existing 27-element initial allowance. No new Places search, recursive fill or retry follows a failed transport. Three supported checked options need no fill. Genuine sparse inventories stay sparse. Coverage remains finite; server flags separate combinations and discovery.
