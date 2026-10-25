> Task 46 now connects these components to the existing local planner. Mock remains default; real mode and contact lookups require deliberate switches. [Current flow, safeguards and closed live ledger](real-planning.md). Sections below preserve earlier task checkpoints.

# Task 43 — backend route calculator

Implemented October 24, 2026. This is an isolated Python integration prepared for later feasibility work. The website still uses fictional venues/travel. **The initial implementation used no live requests.** A subsequent separately authorized driving verification succeeded with one live request and four elements; see the ledger below. Walking remains mock-tested only.

## Interface and data

`backend/routes.py` defines the provider-independent `RouteCalculator.calculate(RouteRequest) -> RouteResult` protocol and the Google implementation. Supply one to four **ordered activity candidate groups**, each with one to three validated `RoutePoint`s, and `mode="drive"` or `"walk"`. Groups may repeat venues or activities. A point retains a stable caller identifier and exactly one of validated latitude/longitude or a syntactically supported original Google Place ID (not a `places/…` resource name, address or arbitrary text). Input validation cannot establish that a Place ID still exists; Google can reject stale IDs. No geocoding, extra search or candidate refill occurs.

`RoutePoint.from_venue(VenueFacts)` reuses existing canonical Google IDs and refuses fictional/non-Google evidence. Alternatively, construct a point with already validated venue coordinates and the same stable venue identifier. Route requests revalidate supplied models, reject conflicting locations under one ID, unknown fields, empty candidate groups and unsupported modes. Validation failures are Pydantic input errors; budget/gate failures are safe `RouteError(code, message)` exceptions.

Each returned `RouteLeg` contains `origin_id`, `destination_id`, `mode`, `duration_seconds`, `duration_minutes` (seconds / 60 without rounding), `distance_meters`, `status`, `provider`, `estimate_type`, `error_code` and optional numeric `provider_status_code`. Task 44 additionally retains exact protobuf `duration_nanoseconds` on parsed successful provider legs for hard comparisons, without changing existing metrics. The array contains one result per distinct directed required pair, in first-needed order; callers can index by the two IDs and reuse it across combinations. A-to-B and B-to-A remain independent. Failed/unknown routes have null metrics, including distance, and never become zero-minute routes.

Task 44's separate pure [feasibility evaluator](feasibility.md) consumes these legs and already supplied venue hours; it performs no provider calls and does not activate real-data planning.

| Status | Meaning |
| --- | --- |
| `ok` | Google supplied a successful route, valid duration and distance under the documented response encoding. An estimate, not confirmed future travel. |
| `same_location` | Same stable venue ID or identical supplied Google Place ID: local zero **between venues**; no Google request, `provider=local_identity`. Does not estimate movement inside a building. Equal coordinates alone do not prove venue identity. |
| `unreachable` | Google explicitly returned `ROUTE_NOT_FOUND`; metrics remain null. |
| `error` | Per-element provider failure or whole-request failure; safe code preserved, metrics null. |
| `unknown` | Missing/duplicate element, malformed status/condition/metrics; metrics null. |

All data stays in memory. No cache, logging, raw error payload, credential output or persistence is added. Task 45's complete public source-labeling system is not implemented.

## Exact pair selection and budget admission

`plan_matrices(request)` is pure and makes no requests. It takes only the union of the directed pairs between **consecutive** activity groups, plus an optional authorized start → first-group transition. Repeated identical pairs and identical provider-waypoint pairs under caller aliases reuse metrics while retaining caller IDs; same-venue transitions are removed from Google work. It groups origins having identical needed destination sets into rectangular matrices. Every cell is a required pair, so no full all-to-all matrix or unneeded cross-group cells are purchased. This favors small deterministic batches over combinatorial itinerary calls, without a complex matrix optimization engine.

For each planned request, elements = **number of origins × number of destinations**. Sum the products across the whole plan before authentication or network access. Three transitions of 3 × 3 candidates use **27 elements**, even though they use only three HTTP requests. Adding a start → three first venues would require 30, so the complete routing plan is refused before any request. No silent candidate truncation, omitted required transition, automatic search expansion or matrix splitting to evade limits occurs.

`OutingBudget.reserve_matrices()` atomically checks and reserves the complete batch before I/O, sharing the existing session/outing budget with Places. It checks remaining candidate, request, matrix and concurrency allowances and prevents repeat request hashes. All planned reservations remain charged locally even if the first request fails and later matrices are not sent. Result `matrix_elements` and `matrix_requests` describe these **conservative reservations**, not posted Google charges or counts of successful routes. Return/reuse this single outing result; repeat calculation calls are not a response cache or permission to retry.

Unchanged maxima: 3 candidates/activity, 27 elements/outing, 20 requests/outing, 50 requests/session, 300 elements/session, **1 concurrent external request and 0 automatic retries**. Added admission check mirrors the project's **60 matrix elements per rolling minute** across outings in this process. Google also enforces the existing **300/day** and **60/minute** cloud quotas. Each actual matrix is checked against Google's standard 625-element and 50 total address/Place-ID waypoint request limits. No quota or setting was increased.

These are local process controls, not a distributed billing ledger. Restarting/reloading or multiple workers reset/separate counters; external use can consume Google quota too. The session ceiling is at most the known daily cloud ceiling, but cannot know account-wide remaining daily usage. Google's 429 remains authoritative; no quota-inspection API is called per outing. The $50 budget alerts remain notifications, not a hard cost cap.

## Google request and pricing

Fixed endpoint: `POST https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix`.

Explicit minimal mask: `originIndex,destinationIndex,status,condition,distanceMeters,duration`.

Driving sends `travelMode=DRIVE`, `routingPreference=TRAFFIC_UNAWARE`. Walking sends `travelMode=WALK` and **omits** `routingPreference`, which is not supported for walking. No departure/arrival time, traffic model, route modifiers, optimization, toll calculation, polylines or premium extras are sent. The transport refuses unsupported top-level options and route modifiers.

These basic requests qualify for **Routes: Compute Route Matrix Essentials**. Google's global first paid tier is currently **$5/1,000 elements**, with a **10,000-element monthly free allowance**, subject to account terms/aggregation and future changes. A reserved 27-element outing is at most **$0.135 at that list rate**, before allowances/trial credit; this is an estimate, not measured charges. Free Trial is subject to remaining credit and expiry; no billing plan change or quota increase occurred.

Durations are ordinary route-network estimates. They are not straight-line-distance calculations, live traffic predictions or guaranteed arrival times. Walking routes are beta and may omit sidewalks/pedestrian paths; future display must include Google's required warning. Before displaying matrix content, also follow Google's copyright/attribution requirements (currently `Powered by Google, ©<YEAR> Google`) and applicable Maps terms. No frontend display, map or general content-retention permission is introduced here.

Official documentation reviewed October 24, 2026:

- [Compute Route Matrix guide and request limits](https://developers.google.com/maps/documentation/routes/compute_route_matrix)
- [REST schemas, modes, statuses and duration encoding](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix)
- [Response association and attribution](https://developers.google.com/maps/documentation/routes/understand-rm-response)
- [Field masks and omitted default scalar values](https://developers.google.com/maps/documentation/routes/choose_fields)
- [Walking mode and required warning](https://developers.google.com/maps/documentation/routes/reference/rest/v2/RouteTravelMode)
- [Usage, SKU triggers and limits](https://developers.google.com/maps/documentation/routes/usage-and-billing), [Essentials SKU](https://developers.google.com/maps/billing-and-pricing/sku-details#compute-route-matrix-essentials), [global price table](https://developers.google.com/maps/billing-and-pricing/pricing)

## Starting point and future constraints

A destination such as **Baltimore** describes where venues are sought. It never becomes downtown coordinates or the user's origin. Venue candidates describe activity stops. Travel between consecutive stops is separate from travel to the first stop and from any return journey.

Optional `AuthorizedStart(point=RoutePoint(...), explicitly_authorized=True)` must be explicitly supplied by a future trusted caller based on the user's actual permission/input. A boolean declaration is a caller contract, not a browser-consent audit system. This task adds no browser geolocation prompt or UI. Starting addresses/city names are not accepted for routing: supply authorized coordinates or a supported Place ID. An unknown starting location remains unknown; no first-leg request is made.

Discovery's existing `TravelConstraints.max_first_leg_minutes` and `max_between_activities_minutes` remain separate and unevaluated. “Within 10 minutes of me” will need the actual authorized start and the appropriate route in Task 44. Task 43 calculates evidence only, with no full feasibility enforcement, opening-hour filtering, scheduling, source-confidence labeling, ranking change or real-data planner integration. Keep starting points transient; do not log or persist them in future callers without a separately justified need.

## Failures, authentication and live lock

Elements are associated by their returned zero-based indices, regardless of order. Per documented proto3 JSON semantics, omitted scalar indices decode as zero and omitted `distanceMeters` as zero **only inside an otherwise successful route element**; missing whole elements and missing/invalid durations never acquire defaults. Missing/null status is unknown; an explicit empty status object is Google's OK status. Invalid/out-of-range indices invalidate the affected matrix; duplicate cells are unknown, never last-write-wins verification. Valid siblings survive per-element errors and missing cells. A whole-request/structural failure stops further matrices, marking their pairs `not_requested`; no automatic retry or fallback is attempted.

Safe codes distinguish disabled operation, application limits, invalid requests, authentication, permission, quota, timeout, provider failures, invalid responses, per-element status and incomplete metrics. Raw provider status messages/details, response bodies and external request payloads are not exposed. HTTP 401 never refreshes and resends a billable request; HTTP 429 never triggers a retry. Plain `requests.Session` has zero adapter retries, redirects disabled, and connection/read timeouts of 5/15 seconds.

`backend/routes_transport.py` reuses Task 40's existing protected ADC impersonation/token helper: expected dedicated account, ADC permission/type checks, short-lived in-memory token, fixed quota project `where-to-512422`, bounded OAuth/IAM authentication hosts and no fallback to broad user credentials or permanent keys. No new dependency, key, IAM grant or credential-file edit.

**Live access is disabled by default**, checked in calculator and transport before authentication. `WHERETO_ROUTES_DEV=1` is a separate local-development gate for a future explicitly authorized verification only; it is not set in startup, environment examples or this task's running environment. `VENUE_DATA_MODE` remains mock-only, and the generic live-provider lock stays unconditional. Places' development gate does not activate routing. No public route endpoint or live-test command was added. Authorization for Task 40's old two requests does not extend to Routes.

Offline verification: run `backend/.venv/bin/python -m unittest backend.test_routes backend.test_provider_budget -v` from `/Users/rahularutla/Documents/whereto`. Tests use invented responses, scoped flags and patched transports/authentication; sockets are forbidden in route tests. Full regression evidence and browser/live limitations are in HANDOVER.md. The authorized driving check below has now been performed. Its one-request allowance is exhausted; further live requests require separate authorization.


## Authorized live verification — October 24, 2026

**Result: successful. Exactly ONE live Compute Route Matrix request, FOUR requested/returned matrix elements, HTTP 200. Zero Places calls, retries or additional routing requests. The allowance is exhausted.** This follows the owner's updated explicit one-request/four-element authorization; the earlier two-element proposal made no live request.

Public reference locations: **A = Fort McHenry National Monument and Historic Shrine**, with coordinates from [Recreation.gov](https://www.recreation.gov/gateways/2695); **B = Washington Monument in Baltimore's Mount Vernon neighborhood**, with published degree/minute/second coordinates from the [National Gallery of Art](https://heald.nga.gov/mediawiki/index.php/Washington_Monument_%28Baltimore%2C_MD%29), converted arithmetically to decimal degrees. These are landmark reference points, not user locations, verified entrances, opening-hours checks or accessibility guarantees. No Places/geocoding request obtained the inputs.

The temporary verification process used existing `matrix_body([A,B], [A,B], "drive")`, the existing shared `OutingBudget.reserve("matrix", ..., origins=2, destinations=2)`, `routes_transport.compute_matrix` and `parse_matrix`. It deliberately included all four cells as authorized. Normal `GoogleRouteCalculator` behavior still removes self-pairs and purchases only needed transitions; no code was changed to force this verification shape into normal planning. Test-only settings lowered both process and outing ceilings to **one request/four elements**, beneath all unchanged project/application limits. A send guard allowed only the fixed Routes endpoint once and the existing OAuth/IAM authentication hosts, rejecting Places or any second Routes send. An exclusive local run marker prevented accidental repeat execution.

| Pair | Validation outcome |
| --- | --- |
| A → B | Successful provider status/ROUTE_EXISTS; positive, sensible distance and duration; seconds/minutes consistent. |
| B → A | Successful provider status/ROUTE_EXISTS; positive, sensible distance and duration; independently mapped and different from A → B. |
| A → A and B → B | Successful provider status/ROUTE_EXISTS; zero distance and duration, appropriately accepted as self-pairs. |


No provider, authentication, permission, quota, timeout, incomplete-element or mapping errors occurred. Existing local impersonated ADC successfully authenticated the actual Routes request. Its file hash remained unchanged, and the local permission/type/target checks passed. The fixed field mask remained `originIndex,destinationIndex,status,condition,distanceMeters,duration`; DRIVE/TRAFFIC_UNAWARE, no traffic model/tolls/premium options, zero redirects/retries. These are ordinary driving estimates, not live traffic predictions or guaranteed times. This check does not live-verify walking or Task 44 feasibility.

The route gate was enabled only inside the single verification process and removed in `finally` immediately after the transport operation, before response validation. Both route/Places development switches were absent afterward; the disabled-route guard was exercised successfully. No environment/profile/config file, credential, IAM, quota, alert, billing-plan or account change. No persistent cache or raw provider request/response/credential was stored in the repository; the table records operational validation outcomes only. Numerical route metrics were used transiently for validation/reporting and were not copied into Git fixtures or documentation. [Routes content policies](https://developers.google.com/maps/documentation/routes/policies).

Safeguard review used local code/settings/ADC metadata and the existing verified billing records: Free Trial originally $300, recorded expiry January 21, 2027; existing $50 account-wide alerts at $25/$45/$50; matrix cloud quotas 300/day and 60/minute. Those settings were not changed. Current remaining credit, aggregate usage and posted charges were **not freshly measured**. At the previously documented Essentials first-tier rate, four elements correspond to **$0.02 before allowances/trial credit**, an estimate rather than a receipt. No cloud administration API was enabled or queried as part of this check.

Post-test focused offline route/budget checks: **33/33 passed**. No repository application code changed, so full frontend/build/browser/Ollama suites were not rerun. The initial Task 43 implementation's full regression results remain in HANDOVER.md. The fictional planner is unchanged; Task 44 remains unstarted.


## Task 45 display boundary

`route_labels` adds duration/distance estimate labels and Google Maps attribution requirements without changing `RouteLeg`, direction, mode, precision or provider metadata. Traffic-unaware driving and beta walking limitations remain explicit; failures/missing routes never become zero travel. Local identity transitions have local provenance. Pair with `feasibility_labels` over Task 44 results for scoped constraint messages. [Evidence and attribution contract](evidence-labeling.md). No new calls, mask/feature/cost/limit changes or Task 46 integration.


## Task 46 — planner connection

The existing route calculator now serves deliberately enabled local real planning. Its exact adjacent-group batching, direction/mode/source metadata, unknown/failure states, unchanged 27-element ceiling and full-plan admission are preserved. Optional authorized first-stop routing stays separate. Task 44 exact seconds decide hard limits; the shared minute scheduler uses floor minutes only as a conservative lower bound for time-window rejection, while result quotes round up for display. Real visit times remain unknown when durations/sessions are absent. No automatic retries or alternate fictional travel exist. [Integration and combined Task 46 live ledger](real-planning.md). The Task 43 allowance above remains exhausted and is separate from the owner's Task 46 allowance.
