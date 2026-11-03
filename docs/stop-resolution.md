> Current Task 50E: approved local website and version 2 saving integration is implemented. Initial milestone descriptions below are historical; see [current flow, gates and limits](advanced-integration.md).

# Task 50B — verified stop resolution

This layer resolves venue identities and discovers candidates. It does not create
advanced itineraries, optimize order, check return routes, establish arrival times,
or prove deadline, hours, reservation, inventory or event availability.

## Audit and reuse

| Existing component | Task 50B use or extension |
| --- | --- |
| `places.PlacesDiscovery`, Text Search New | Add `resolve_named`; same adapter and transport, finite single page, at most ten results, lower candidate ceilings honored. |
| `search_body`, `SearchArea`, `venue_geography` | Existing coordinate bias, rectangle restriction, named-component evidence, exclusions and fixed boundaries. Named identities are exempt from an ordinary nearby discovery radius, never from explicit hard boundaries. |
| `starting_places` | Reuse its architectural approach (explicit Text Search, no Geocoding); no origin lookup or origin identity is inferred by the new layer. |
| `places_transport`, `search_fields` | Same OAuth identity, mask allowlist, optional preauthorized hours/ratings, no redirects/retries or Details fan-out. |
| `venue_normalization`, `VenueFacts` | Canonical provider-scoped ID, address, coordinates, types, attributions, current/regular hours, timezone and observation timestamps. |
| `venue_quality`, `retail` | Existing activity relevance/deduplication, arbitrary brands, flexible formats and mandatory outlet evidence; malls require directed containment plus independently verified mall facts. |
| `provider_budget`, `development_cost`, `provider_errors` | Same outing/process/concurrency/minute/day admission, conservative failed-attempt accounting, tier estimates and provider-vs-local error categories. |
| Task 50A `Journey`, interpreter/follow-ups | Reuse validated extraction; no expanded Qwen schema or extra Qwen resolution call. Ordinary generation remains separate. |

Task 50B extends identity checks and adds a backend-owned ambiguity context. It
adds no provider integration, public endpoint, database table or storage format.
`parse_response(identity_lookup=True)` preserves a soft named-area bias without
turning it into a hard geographic filter. Ordinary discovery parsing is unchanged.

## Contract and identity rules

`backend.stop_resolution.StopResolver` requires the default-off
`WHERETO_STOP_RESOLUTION_DEV=1` switch. Existing provider authorization is still
required at dispatch. It is a backend development/test API, deliberately absent
from ordinary `/interpret` and `/plans/generate` execution. No flag is added to
the owner's local profile, tests' general defaults or production configuration.
The current frontend cannot enforce the advanced route/time requirements safely.

`resolve(validated_journey, area, context=validated_interpretation_context)` returns
`ResolvedJourney`: the unchanged Journey, geography/context, source-order indexed
stops, separately indexed endpoint, unresolved relationships and fixed
`execution='unavailable'`. Each `ResolvedStop` retains the entire original
`RequestedStop` (phrase, kind, requirement, evidence, duration). Its status is
resolved, candidates, ambiguous, unresolved or provider_failure. Lists are bounded
at 32 occurrences and ten candidates/occurrence. Canonical facts remain internal;
they are not an ordinary frontend or saved-plan DTO.

Each `ResolvedCandidate` requires a syntactically valid original Google Place ID,
matching canonical identity/provider, address, coordinates and actual provider
types. Facts and observation provenance are provider-supplied; eligibility is an
application assessment, not a Google guarantee. Exact normalized name identity,
relevant type evidence and all explicit qualifiers must agree. Similar names,
annexes, other colleges, other streets and different branches are excluded.
Address spelling variants are bounded (St/Street, Rd/Road, Ave/Avenue, Rte/Route).
No name-to-coordinate database, fabricated ID or Qwen assertion establishes a venue.
Conservative matching may leave genuine aliases unresolved.

`named_place` means one mandatory identity, even if distant. Multiple plausible
identities require a choice. `brand` means multiple eligible branches; nearest
wording guides discovery but does not prove nearest routed travel. Existing brand
identity and retail types remain hard requirements. Outlet/regular/flagship are
flexible unless explicitly restricted. `activity` uses existing normalization,
search, relevance and deduplication. Repeated phrases reuse a search while retaining
separate occurrences. A failed named stop is never replaced by generic discovery.
With no explicit discovery area, a uniquely resolved preceding place can supply a
coordinate bias for following activities. An ambiguous place cannot supply one.

Named retailer-at-mall requests verify the parent through the same adapter and
join its ID to provider `containingPlaces`; address proximity is insufficient.
Shared-mall requirements retain only common directed parent IDs verified as malls.
Missing containment or uncertain parent identity remains unresolved. Identity
resolution never establishes accessible facilities, services, sessions or availability.
Task 50C consumers must continue enforcing all retained requirements.

## Ambiguity and security

The server-owned resolver object retains one active result, a private random
context token and a ten-minute choice expiry. `choices()` exposes only the
ambiguous occurrence, question, provider-backed names/addresses/credits and IDs.
No origin/home, raw response or internal provider model is included. These are
public establishment suggestions, not private address-history suggestions.
`choose(context, occurrence, place_id)` accepts only membership in that context's
still-ambiguous stop, reuses its validated candidate and preserves all other
stops/constraints. Foreign IDs, contexts, indexes, expired choices and replays are
rejected without Qwen or provider I/O. A future public boundary must retain the
object server-side; accepting a client-serialized resolved object is forbidden.
No new public selection API or cross-user registry is introduced here.

## Implemented clarification UI

Valid advanced requests now show **Your request is understood** and “We understand
your stops and requirements, but advanced route planning for this kind of trip is
still being added.” This is separate from genuine ambiguity/failure feedback.
No advanced cards are generated and no resolution search occurs to display it.
Manual origin preparation follows interpretation, so unsupported advanced requests
do not first perform a manual-origin lookup.

Unresolved home endpoints show an address/named-location input and a native
**Return to my starting point** button. The button fills an explicit answer; the
user submits Continue planning. Invalid/uninformative answers retain the question.
Validated field-only continuations reuse the existing extraction, original text,
calendar reference, preferences, order, required stops and timing constraints.
A return-to-start answer confirms the intended relationship, not starting coordinates; future routing must still require a confirmed origin. The original source-grounded home clause is preserved; separate transient context
records origin confirmation or a location needing provider verification. A supplied
address is only syntactically accepted, never represented as verified or routed.
Accepted home answers also remain in transient continuation state for subsequent checks of the same text. Editing the original text or reloading clears that state. No GPS-to-home inference, permanent address storage, SQL or Google lookup occurs.

Named-place ambiguity selection is implemented and tested in the gated backend
contract, **not surfaced in the ordinary planner**. The ordinary UI therefore
shows an honest advanced limitation for Penn Station rather than issuing paid
searches or guessing a match. Connecting verified named-place choices, endpoint
geocoding and this contract to an executable plan remains future integration.
Existing ordinary activity/date/location follow-ups remain in place.

## Costs, hours and performance

One unqualified exact place: one Text Search. A named mall-qualified retailer:
at most two (parent + retailer). Repeated exact requests reuse successful or failed
lookups within the active resolver. Each distinct discoverable activity uses the
existing bounded pipeline, including its already implemented retail fallback and
relationship searches. Two separate brands sharing a mall: three fixture searches
(two stores + one mall). Every attempt uses the shared budget; large requests can
exhaust it and preserve provider_failure states. There are no matrix, Details,
retry, speculative pagination or per-candidate operations in this layer.

Using the project's existing gross estimates, one Pro search is $0.032; two are
$0.064; three are $0.096. With already authorized Enterprise fields enabled these
are $0.035/$0.070/$0.105. These are list-price estimates, not posted billing or a
new pricing verification. All tests and browser checks incur **zero live Google
requests and $0 actual provider cost**. Cloud quotas, billing/IAM/credentials and
private local configuration remain unchanged.

Existing search hours/current and regular periods/timezone/observation times stay
transient in canonical facts. Missing hours stay unknown. There is no arrival-time
evaluation before routing and no extra Details call to fill missing evidence.

The interpreter schema, model, settings and warmup are unchanged. Task 50A's last
matched warm median remains 9.325s (previously 3.911s); actual Qwen was not rerun in
50B because no model prompt/schema/settings changed. Twenty offline single-exact
resolution iterations measured about 0.3ms median (fixture transport only). This
measures Python overhead, **not live Google or end-to-end latency**. Real resolution
would add one or two sequential provider round trips; live latency is unmeasured.
Ordinary and unsupported UI flows add zero resolution calls. Endpoint continuations
make zero Qwen/provider calls.

## Verification

From `/Users/rahularutla/Documents/whereto`:

```sh
backend/.venv/bin/python -m unittest backend.test_stop_resolution backend.test_journey -v
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

Invented provider-shaped tests cover exact college/street/Apple identities,
Penn Station/Starbucks ambiguity and scoped selection, nearest Target, groceries,
coffee, Zara branch/brand/formats, verified shared malls versus proximity, required
and optional combinations, repeats, hard/preferred geography, far exact places,
missing/wrong/duplicate/invalid identities, quota/service/local limits, hours,
request accounting, source/order/return/deadline preservation and safe gating.
Frontend tests cover honest status, accessible home control, preserved original
payload/preferences and no planner dispatch/cards. Existing full suites cover
ordinary two-stop planning, clarifications and provider/persistence boundaries.
Final counts and actual browser evidence are recorded in HANDOVER.md.

No migration or hosted check is needed: the resolver/endpoint answer is absent
from persistence DTOs, database access and schema. Tasks 50C–50E and 51 remain
unstarted. Saved advanced plans and route feasibility remain unavailable.

Final acceptance (November 2, 2026): backend 753 reported run, 719 passed and 34
opt-in skips; frontend 239/239; focused resolution/Journey 68/68. TypeScript,
ESLint, production build, dependency/audit and credential scans pass. Desktop 1280
and mobile 390 fixture checks pass within the explicitly stated scope above and
in HANDOVER.md. The final 20-iteration overhead median was 0.299ms, maximum 0.412ms.
Hosted checks: zero; no persistence/schema path changed. No live Google or SQL.


## Task 50C update — backend routing contract

`StopResolver.routing_snapshot()` provides a revalidated active server-owned result
under the existing gate/expiry. `AdvancedRouter` consumes that resolver and its same
outing budget, never client-provided resolved places. Missing/ambiguous required
identities or unverified home/final endpoints cannot become compliant routes.
Ordinary named choices and advanced execution remain backend-only. [Route contract,
privacy, evidence and tests](advanced-routing.md). Tasks 50D–50E and 51 remain unstarted.


## Task 50D update — timing consumes routing, never resolves again

The local evaluator takes the active Task 50C router, rechecking this resolver's
gate/expiry and unchanged context before reading its route evidence. It preserves
selected identity, occurrences, optionality, original timing/source constraints and
all endpoint roles. No new place choice/search, AI call, Details request or persistent
provider cache. Destination/browser/unknown timezone basis and explicit departure
evidence are additive transient context fields. [Timing semantics](advanced-timing.md).
Advanced execution/saving remain Task 50E; Task 51 remains unstarted.


## Task 50E — advanced application integration

Task 50E surfaces server-scoped named-place choices in the website and passes the same resolver/outing budget to routing. Choosing an existing candidate adds no search or model call. Separate home addresses still need verified identity and remain unsupported here. [Contracts, limits and verification](advanced-integration.md). Earlier task-pending statements above are historical. Task 51 remains unstarted.
