# Task 46 — real-data outings

The existing homepage, local Ollama interpretation, deterministic clarification/date handling, manual overrides, outing summary and result cards now support a deliberately enabled **local real-data mode**. Mock is still the default. Neither mode silently falls back to the other. This milestone supplies actual multi-stop venue suggestions and route estimates, not confirmed reservations or a fully timed/financially verified outing.

## Flow and boundaries

1. The browser submits text to the existing Next.js `/api/interpret` proxy. Python validates the AI extraction, original wording, user overrides and exact calendar date. Saved clarification continues without another AI call.
2. `/api/plans/generate` uses the process's backend mode; a request cannot change it. Real mode requires `VENUE_DATA_MODE=real` and `WHERETO_REAL_DEV=1` in development. Production/known hosting environments refuse it. Normal startup does not enable Google requests.
3. One shared outing budget covers distinct activity searches, routing and later contact lookups. Repeated activity categories reuse one search; explicit dinner context uses a dinner-specific restaurant query. Places Text Search uses the unchanged six-field Pro mask, up to three candidates/category and four searches/outing, without pagination, refill queries or retries.
4. Existing geographic checks, Task 41 normalization and Task 42 deduplication/relevance checks produce canonical Google physical places. Every original source/Place ID and credit remains available in evidence labels. All 29 categories have queries; event-category searches locate buildings, never performances.
5. Task 26's existing ordered product traversal generates combinations. The small explicit `providerPlaceId` bridge permits an event-category physical venue without fabricating a `ScheduledEvent`. One physical venue cannot become two visits in a real outing, including multi-activity matches. Explicit real revisits remain unsupported; request order and repeated categories are preserved with distinct venues.
6. Task 43 calculates only adjacent-group directed pairs and an explicitly supplied start. It deduplicates waypoints/pairs and admits the full matrix plan before I/O. No candidate truncation is used to evade the 27-element ceiling.
7. Task 27 evaluates unknown prices, capacity, durations and scheduling with real route quotes; fictional price/travel adapters are never used for real data. Task 44 separately checks exact provider seconds/nanoseconds against per-leg, total inter-stop and first-stop limits. Rounded-up display minutes do not decide these limits. Missing/unreachable/invalid routes remain unknown/infeasible as appropriate. Task 45 provides venue, route and scoped feasibility labels.
8. Existing normalized scoring ranks eligible combinations, favoring convenient travel when price/quality are unknown. Existing diversity selection prefers different stop identities. It normally requires half of the stops to change, reduced to the number of positions that actually have alternatives when the eligible pool is small. Shared venues across options are allowed; full ordered duplicates are rejected. It returns up to three visible options, plus at most two additional batches of three pre-evaluated options for Show different options. The same distinctness threshold applies against earlier batches; no full itinerary reappears. Nothing is added to fill a batch. This is a bounded heuristic, not global route optimization.
9. Existing cards display actual names/addresses, ordered activities, route direction/mode, Google Maps/third-party credits, source links, uncertainty and a compact contact panel. No interactive map, booking, payments, dragging, database or Task 47 feature is added.

## Location and calendar

Destination, search center, optional authorized start, first-stop travel and inter-stop travel are separate. An explicit Washington, DC request wins over unrelated device coordinates. A named city never supplies an origin. A radius needs a coordinate search center; the app refuses to apply the current position's radius to an unrelated named destination.

The optional starting-location disclosure contains **Use my current location**. Only that button calls browser geolocation, with a bounded timeout and no high-accuracy request. Opening the page/disclosure never requests permission. Localhost and HTTPS are supported secure contexts. Denied/unavailable/unsupported location gives a manual city/neighborhood alternative through existing preferences; the normal interface instead accepts a place, address, neighborhood or ZIP. Resolution of that text is not enabled yet; it cannot be used as an origin until resolved and confirmed. No device coordinates are written to application diagnostics, returned in planner responses, or saved to disk/database. The page holds them until removal/reload/close; Google receives them only as needed for an explicitly requested search/route.

“Near me” without a supplied point cannot trigger discovery. Missing city/date/group continues through the existing clarification. With permission, near-me searches use the supplied search point. Explicit source-grounded forms such as “within 10 minutes of me” retain a separate first-leg cap; unsupported/unclear AI scope is refused rather than silently relaxed. The location disclosure also has validated first-stop minute and near-me radius controls. Complex location/radius wording can need manual controls or rephrasing.

Baltimore and explicitly qualified Washington, DC use America/New_York for date interpretation/publication checks. Other destinations retain the existing explicit UTC fallback notice when their timezone is unknown. The minimal discovery mask does not retrieve venue timezones. No exact real visit times are published while activity durations/session times are unknown. This avoids inventing a venue-local schedule; broader timezone/location resolution is future work.

## Evidence limitations

Current searches retrieve identities, names, addresses, coordinates, geographic components and credits. They do **not** retrieve ratings, prices, opening hours, business status, activity duration, capacity, ticket/session inventory or reservations. Search context is not verified activity availability. Conservative geographic filtering can reject valid suburbs or neighborhoods with incomplete provider components.

Real options remain **provisional**. Unknown prices are null, never free, and never reused from the fictional catalog. A supplied hard per-person/group budget stays on the request and is explicitly **not passed/not verified** while costs are unknown. Missing optional prices/hours do not remove all useful options. Movie showtimes, performances and restaurant reservations remain independently unverified. Applicable known evidence continues to use Task 44; the current permitted search mask supplies no hours or visit durations from which an actual hour-by-hour schedule could be verified. No hours enrichment is performed here. Dinner/date constraints remain in the effective request; unknown visit times cannot promise dinner timing.

Driving estimates exclude live traffic. Walking is supported but remains offline-tested; Google's beta walking caution is displayed. Transport defaults visibly to driving for real mode; unsupported cycling/transit requests explain the limitation. First-stop travel is shown separately; return-home travel is excluded.

## On-demand venue contact details

Every real venue has **View details** inside its itinerary. The compact, closable panel shows the known name/address, Google Maps location link, and available phone/official website. Contacting a business does not confirm a ticket or reservation.

`POST /api/venues/details` requires a transient random outing capability and an original returned Google Place ID. It cannot look up arbitrary fictional or unrelated IDs. Backend session entries retain only IDs, attempted-ID markers and the original budget for at most 30 minutes/50 active entries. All provider attempts share the existing process session (50 requests), outing (20 requests), concurrency (one), and zero-retry controls. An additional **six Details attempts per outing** ceiling is a reduction within those existing ceilings. Invalid/expired sessions and missing/failed/quota-limited details produce safe messages.

The separate `WHERETO_CONTACT_DETAILS_DEV=1` gate is off by default. The fixed GET field mask is:

```text
id,nationalPhoneNumber,internationalPhoneNumber,websiteUri,attributions
```

Phone numbers and websites trigger **Place Details Enterprise**. Google global pricing checked October 25, 2026: 1,000 free events/month for that SKU, then $20/1,000 ($0.02/request) in the first paid tier. Search remains Text Search Pro: 5,000 free/month, then $32/1,000. Matrix Essentials remains 10,000 free elements/month, then $5/1,000. Allowances aggregate at billing-account/SKU level; estimates are not billing receipts. Six contact requests would be $0.12 before allowances/credits. No Enterprise search fields, Atmosphere fields, photos, reviews or booking inventory are requested.

Numbers are bounded/validated before `tel:` links; websites must be HTTPS without embedded credentials. Unsafe/missing information displays **Phone number unavailable** / **Website unavailable**. External links use `noopener noreferrer`. Credits remain attached. Reopening a mounted panel reuses its active displayed response; repeated cards for the same ID share one in-flight/display promise. Responses are `no-store`; there is no browser storage, service worker, persistent Google cache or server contact-content cache. Regeneration/page replacement clears the active display session; errors do not retry automatically. This active-view reuse is not permission to retain Google content for later/offline use.

Task 46 live authorization explicitly excludes Place Details. All contact-detail verification uses invented responses. A live contact check needs separate authorization.

Official references: [global pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [Details field tiers](https://developers.google.com/maps/documentation/places/web-service/place-details), [Places display/storage policies](https://developers.google.com/maps/documentation/places/web-service/policies), [Maps service terms](https://cloud.google.com/maps-platform/terms/maps-service-terms), [Routes policies](https://developers.google.com/maps/documentation/routes/policies). Compact cards/panels use the permitted space-limited Google Maps text attribution and retain all supplied credits. `/privacy` and `/terms` explain this local prototype and link Google's policies. Public deployment still requires its own review; it is outside Task 46.

## Limits and diagnostics

No Cloud quota, budget, billing account, IAM permission, credential, candidate ceiling or matrix ceiling was increased. The $40–$50 development target, existing $50 alerts and Free Trial remain. Billing alerts do not stop usage. Process counters reset after restart and are not account-wide accounting.

Three candidates yield nine elements for two different activities, 18 for three, and 27 for four. An added three-element first-stop group can make a four-activity outing require 30, which is refused before any routing call. Repeated groups can reuse pairs; there is no all-pairs city matrix. Missing candidates may reduce options; fewer than three is legitimate. These limits materially restrict coverage/diversity. A future proposal could raise candidates to four for two-stop requests (16 elements, or 20 including a start), and separately allow 30 elements for four-stop requests with a start. Neither change is approved or applied; broader candidate work should follow measured feedback.

Development responses report Places search/detail attempts, total attempts, conservatively reserved matrix elements, matrix request count, exclusions, provider latency and usage categories. No raw payload, token or precise user position is logged. Provider failures return curated explanations, including disabled mode, authentication, permission/billing, quota, timeout, application budget and invalid data. No automatic retry, real/mock mixture or fictional fallback occurs.

## Verification

Offline automated suites use invented Google responses and fail on unintended network sends. `backend/real_fixture_server.py` is a deliberately launched test-only server; the ordinary app never imports it or enables it through configuration. It replaces AI and provider boundaries, enabling the actual Next.js proxies/client and browser to exercise the complete pipeline without Google. No persistent fixture contains live Google content.

See the final Task 46 checkpoint in HANDOVER.md for exact suites, browser checks and the bounded live ledger. Do not rerun the live verification as an ordinary regression command.


## Bounded live verification ledger — October 25, 2026

| Run | Places Text Search | Route Matrix requests | Billable matrix elements requested | Live Details | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Initial browser outing, bowling → dinner in Baltimore, November 7 | 2 | 1 | 9 | 0 | All HTTP 200; three provisional options |
| Corrected dinner-specific query and mode-aware summary | 2 | 1 | 9 | 0 | All HTTP 200; three provisional options |
| **Total** | **4** | **2** | **18** | **0** | **Within the authorized 4 searches / 27 elements** |

Zero retries, Enterprise search fields, Places Details or other billable Google methods. Each request used the unchanged permitted field masks and existing keyless impersonated ADC. Auth/permission/quota/billing did not cause a runtime failure. Source attribution, original Google venue IDs, actual addresses and positive directional driving estimates reached the browser. Numerical provider metrics/IDs and raw payloads were used transiently and were not copied into committed fixtures or this ledger. At the reviewed first paid tiers, usage corresponds to **$0.218 before free allowances/trial credits**, an estimate rather than a posted charge. Pre-test Console spend was $0.00 and can lag. Billing plan, quotas, alerts, IAM and ADC file were unchanged.

The initial run exposed legacy simulated-travel wording in Your outing; the final browser run verified its correction. A dinner-specific query was also added and offline-tested, but the second live search **still returned a daytime café**. Search wording cannot establish dinner service. The final cards explicitly flag dinner service/hours as unverified; confirmed meal suitability/opening hours require future evidence acquisition. This is a material recommendation-quality limitation, not proof of a feasible dinner booking.

The allowance is now closed. The guarded processes were stopped, local real switches were absent afterward, and the ordinary backend was restarted in mock mode. No further live Task 46 requests are authorized. Contact-success/missing/failure/reopen tests remain mocked; browser geolocation success is mocked, while the browser's actual unavailable/timeout fallback was exercised. Walking is offline-tested only. Broader timezone coverage and real service-hours/prices/session evidence remain future work.


## Post-integration stabilization — October 25, 2026

This is a focused Task 46 follow-up, not Task 47 or a new roadmap item. Zero live Google API calls were made. All existing Cloud/application limits, disabled-default gates, credentials and the prior live ledger above are unchanged.

### Date root cause and correction

The exact prompt “Plan bowling followed by dinner in Baltimore on Saturday, November 7, 2026, for 4 people.” reproduced `date_conflict` through the actual interpretation/clarification service even with correct AI extraction. The deterministic scanner extracted `Saturday` and `November 7, 2026` separately, resolving the first to the next upcoming Saturday rather than treating it as the weekday of the stated date. Manual overrides and frontend follow-up state were not the root cause.

The calendar scanner now recognizes a weekday-qualified named/ISO date as one phrase, validates that its weekday agrees, and ignores redundant AI fragments from that same phrase. Independent dates, mismatched weekdays, invalid days, missing-year/past-date policy and explicit manual priority remain checked. Year-only follow-ups retain qualified date context. The exact prompt now passes both deterministic fixtures through real HTTP/Next proxies and the local Ollama interpretation service without a date question.

### Ranking, shared venues and presentation

Real card titles use the actual ordered venue names. Descriptions explain known estimated inter-stop minutes and venue variety, explicitly stating that unavailable prices/ratings did not determine ranking. The existing score still uses travel convenience when price/quality evidence is absent; tied estimates use diversity and stable ordering, not a hidden venue-quality judgment. First-stop travel is checked separately and does not contribute to this existing inter-stop ranking. No cheapest/highest-rated/open/budget-compliant claim is introduced.

Diversity prefers different whole venue visits, allows shared stops across separate options, and never duplicates a complete ordered itinerary. When only one requested activity has alternatives, useful combinations sharing the fixed stops are retained. This is still a heuristic over provider IDs; it does not prove two businesses offer different experiences. Different options may have the same travel estimate.

Unknown prominent prices now say Price not available and group totals Cost not verified, without a tilde or per-person numeric heading. Hard budgets and their unverified state are retained. Real headers show ordered stop names and existing locally installed Lucide activity symbols in the existing three color themes; they explicitly say illustrations are not venue photos. No new image, photo API, dependency or asset license is introduced.

### Bounded other options

The backend evaluates the same bounded candidate pool once and returns at most six extra eligible options in two batches. The frontend consumes those batches from active-page memory, never resubmitting interpretation, discovery or routing for the action. All options preserve the original request, route/uncertainty evidence and hard constraints. The existing contact capability includes their original Place IDs and retains the same six-contact/overall limits. Edits/new generation clear these options and the contact display session. Regeneration may make a new search; Show different options does not.

The fixture bowling/dinner pool provides nine unique combinations in three pages using the same two synthetic searches/nine matrix elements; a one-combination pool gives no extra button action. Exhaustion is explicit, with no automatic refill or cycling. More genuinely new businesses would require another user-initiated search and potentially more provider budget. The earlier four-candidate/30-element proposals remain proposals only; no increases are needed for this bounded action.

### Manual starting-place resolution: implemented versus deferred

Implemented: ordinary text input for a place/address/neighborhood/ZIP, no latitude/longitude controls, separate destination, explicit geolocation button, clear unavailable/manual fallback messages, transient excluded request field, and a backend refusal before any provider I/O when manual text is unresolved. Text entry never silently becomes a city-center/device position and never silently disables a first-stop cap. Removing the unresolved entry permits destination-only planning when no first-stop requirement remains. No address/coordinate logging or persistence is added.

Deferred: actual text-to-coordinate lookup and confirmation. Google's [Geocoding API](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding) is suited to addresses/ZIPs and reports `location_type` and `partial_match`; an area result must be labeled approximate and explicitly selected as a reference point, not the user's exact location. Named businesses/landmarks could use the existing Places Text Search API, but another request consumes a search slot and needs shared resolution/planning budget accounting plus ambiguity handling. Existing venue discovery must not be reused to pretend a neighborhood is an exact starting address.

Recommended separately approved follow-up: enable/verify Geocoding API only after confirming supported keyless authentication/least privilege; set a proposed 10/day, 5/minute Cloud quota; add at most one explicit resolution attempt per outing within the existing 20/50 total attempts, no retries/autocomplete/pagination; display up to three candidates with provider address/precision and require selection. Require explicit consent to route from an approximate reference point; describe limits as applying from that reference, not verified from the user's position. Do not add a new credential or expand access silently. [Current global pricing](https://developers.google.com/maps/billing-and-pricing/pricing) lists 10,000 monthly free Geocoding events then $5/1,000 ($0.005/request) in the first paid tier; account-wide usage and actual billing may differ. These are documented proposals only: no Cloud API enablement, IAM/authentication/quota change or live method was performed. Manual lookup remains unavailable until that work is authorized and verified.

### Verification

Full backend and frontend suites, lint, TypeScript, production build and dependency consistency passed (exact totals and practical browser checks are in HANDOVER.md). New regressions cover the exact prompt/continuation/manual priority, weekday conflicts, preserved year answers, shared venue pools, unique bounded batches, hard-cap rejection across all alternatives, unknown cost rendering, unresolved manual starts with zero provider calls, and option changes with unchanged request counters. Desktop/mobile browser checks use only the fail-on-network fixture server; successful local Ollama date interpretation is separately verified. No live recommendation-quality/Geocoding/Details verification is claimed for this pass.


### Headline refinement within Task 46 stabilization

`lib/real-headlines.ts` builds titles only from the selected venue records. Two-stop options use “Venue A & Venue B”; three/four-stop options use ordered name highlights, shortening individual names beyond 28 Unicode characters. Ordinary four-stop titles stay within 121 characters. If shortening would give two options the same title, full names are retained instead; same-named businesses can use their supplied addresses to distinguish them. No source names, endorsements or venue facts are invented. Full names remain in the heading tooltip and existing itinerary details.

Eyebrows now read “OPTION 1 · BOWLING + DINNER”, using the actual ordered categories and validated dinner-stop indices. Food is not relabeled dinner without request evidence. The provisional status stays in the separate existing visual badge/result disclosure; it is removed from the eyebrow/headline text. Mock recommendation copy is unchanged. Real headings wrap anywhere when necessary and have a three-line display limit with equal reserved height, preserving card alignment on desktop/mobile. Shortening is presentation only and never changes venue IDs, order, constraints, sources or the available option pool.

Five focused tests cover two-, three-, four-stop and long/colliding/same-named venue titles, ordered/repeated activities, evidence-based dinner labels and absence of invented claims. The full mocked HTTP pipeline also asserts the exact two-stop title and eyebrow. The explicit offline fixture server has a synthetic long-name scenario for browser layout checks; normal startup never enables it. No new asset/dependency/license or Google call is introduced. Exact final test/browser results are in HANDOVER.md; Task 47 remains unstarted.
