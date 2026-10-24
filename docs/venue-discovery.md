# Task 40 venue discovery

Task 40 adds isolated backend discovery, not real-data itineraries. The website still uses the fictional catalog. No new FastAPI route or frontend/geolocation control was added. Task 41 adds offline normalization below; Task 42 adds candidate quality checks. Tasks 43–46 remain unstarted.

## Development use

Normal startup needs no change. `VENUE_DATA_MODE` stays absent or `mock`; other values still fail validation. The generic live provider/Routes gate remains locked. A separate `WHERETO_PLACES_DEV=1` switch permits only the new local Places development adapter. It does not connect the website or enable routing.

The Task 40 authorization for two live requests has been fully used. The following is a command reference for a **separately authorized future test**, not an instruction to run another request now. From `/Users/rahularutla/Documents/whereto`:

```sh
WHERETO_PLACES_DEV=1 backend/.venv/bin/python -m backend.discover_places --activity bowling --destination 'Baltimore, MD'
```

The setting applies to that one command and ends when it exits. Do not export it in a shell profile or save it in an environment file. To turn off a previously exported switch, run `unset WHERETO_PLACES_DEV`. Running the command without the switch refuses access before authentication/network. Normal `npm run dev:backend` and `npm run dev` keep the fictional planner.

The diagnostic command prints only provider/counts/notices, not venue content, addresses, precise user coordinates or credentials. Backend code can inspect `DiscoveryResult.candidates` in memory. No persistent Google content cache, request log or token file is created. Do not dump request models or raw transport/authentication exceptions into logs.

The official `google-auth` library loads the protected existing local ADC file and requires its `impersonated_service_account` type, exact dedicated target account and restrictive file permissions. It rejects broad user ADC and service-account private keys. It requests short-lived `cloud-platform` tokens using the already configured impersonation flow; no new identity, permission, key or account is created. Every Places request explicitly attributes quota/billing to `where-to-512422`. Missing/expired credentials get a safe error. Authentication uses only the existing OAuth and IAM Credentials endpoints, bounded timeouts and no repeated endpoint attempts. See [authentication setup](billing-safeguards.md).

## Backend interface and locations

`PlacesDiscovery(outing_budget).discover(DiscoveryRequest(...))` returns up to the existing candidate ceiling (three, or a lower configured ceiling). Create one `ProviderBudget` per development process and reuse one `.outing()` across all activities in that outing. Do not construct a fresh budget for each activity. The development command deliberately makes one search; multiple command runs/restarts reset process counters and require deliberate usage review.

```python
from backend.places import DiscoveryRequest, PlacesDiscovery
from backend.provider_budget import ProviderBudget

session = ProviderBudget()
outing = session.outing()
request = DiscoveryRequest(
    activity="coffee",
    destination={"name": "Fells Point, Baltimore, MD"},
    starting_location={"address": "An optional user-provided starting address"},
    travel_constraints={"max_first_leg_minutes": 15, "max_between_activities_minutes": 10},
)
# Calling PlacesDiscovery(outing).discover(request) requires the development switch
# AND authorization for the external request. This example makes no request.
```

There are three separate concepts:

- `destination`: optional `SearchArea`, containing a name, coordinates, or both, plus optional `radius_m`.
- `current_location`: optional user-authorized coordinates with an optional radius. Used for discovery only if destination is absent. It never overrides an explicit destination.
- `starting_location` and `travel_constraints`: optional inputs reserved for later routing/feasibility. They are not sent to Google, converted to a city center, used as the discovery location, or evaluated here. No maximum travel time is invented.

A name-only destination generates an explicit geographic query, for example `bowling alleys in Baltimore, MD`. To avoid Google's default server-IP bias, it also supplies a nonlocal 180-degree-wide rectangle bias. Google's documented explicit-location precedence overrides this bias; it is not a destination restriction or assumed user position. Results must independently match all comma-separated destination parts against geographic address components (short or long forms, ignoring case, punctuation and accents). Venue names and street-name matches do not establish location. Prefer `Washington, DC` or `Fells Point, Baltimore, MD` over ambiguous/unstructured names. No Baltimore fallback or geocoder is used.

Matching is deliberately conservative: Google may omit a neighborhood, use an alternative name or return nearby suburbs. Those unverified matches are excluded and counted, so an empty collection can mean no geographically verifiable results. Address components are not administrative boundary polygons; this is geographic evidence checking, not proof of a venue's availability/relevance or comprehensive coverage. Task 42 now adds conservative activity relevance and entity deduplication below.

Coordinate-only searches use Text Search `locationBias.circle` with an activity query. Valid latitude: −90 to 90; longitude: −180 to 180. Nonfinite numbers, booleans and numeric strings are rejected. A supplied radius must be greater than 0 and at most 50,000 meters, with an explicitly provided coordinate center. A radius with only a city name is rejected rather than silently inventing a center. A destination can include its own explicitly supplied center/radius; unrelated current-location coordinates/radius are ignored when a destination is set.

Google's circle is a bias, so the backend checks each returned coordinate using great-circle distance and excludes candidates outside a supplied radius. That distance is only geographic radius validation, not driving/walking distance or travel time. Without a radius, Google's documented zero-radius point-bias mode is used; there is no hard distance limit and no invented default search radius. No starting location is inferred from the city, the IP address or the search point.

## Queries, methods, fields and costs

All 29 existing activity IDs map to concise provider queries. Examples: `food` → restaurants, `drinks` → bars, `movie` → movie theaters, `coffee` → cafes, `arcade` → video arcades. Scheduled activities search venue types (concert venues, stadiums, theaters), not events/showtimes. Discovery never asserts that a performance or game is scheduled.

Only `POST https://places.googleapis.com/v1/places:searchText` is implemented. Text Search supports named destinations and coordinate bias, so Nearby Search would add no necessary Task 40 capability. There are no Details, Nearby, Routes, pagination or retry requests. `pageSize` is at most three; unexpected larger responses are rejected. A next-page token is neither requested nor followed. Fewer valid candidates are acceptable; no extra search fills the collection.

Fixed explicit field mask:

```text
places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions
```

| Field | Text Search SKU tier | Purpose |
| --- | --- | --- |
| `places.id` | Essentials IDs Only | Preserve the original stable provider ID |
| `places.displayName` | Pro | Identify the venue |
| `places.formattedAddress` | Pro | Inspect its address |
| `places.location` | Pro | Coordinates for geographic checks and later clustering |
| `places.addressComponents` | Pro | Verify city/neighborhood/region independently of venue names |
| `places.attributions` | Essentials IDs Only | Retain any provider-supplied third-party attributions |

Highest tier: **Text Search Pro**. Official global pricing checked October 23, 2026: 5,000 free events/month for this SKU; first paid tier **$32 per 1,000 requests ($0.032 each)**, subject to account-wide usage, applicable terms and changing prices. Two successful chargeable requests would have a $0.064 list-price estimate before free allowance/credits. This is not a measured charge; one of our two attempts returned HTTP 400, and billing treatment/posted cost was not independently measured. Results per page do not change the requested field tier. No Enterprise ratings/hours/websites/prices/reviews are requested.

Each candidate contains `provider="google_places"`, untouched `provider_id`, display name, address, validated coordinates and any attributions. It is a discovery-only contract, not a normalized planner `Venue` or a feasible itinerary. There is no invented hours/availability/showtime/capacity/price/route/travel evidence. Task 41 now adds a separate offline canonical conversion with deliberate handling of optional details, unknowns and field costs; see the section below.

Official references: [Text Search guide](https://developers.google.com/maps/documentation/places/web-service/text-search), [method reference and rectangle limit](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchText), [field tiers](https://developers.google.com/maps/documentation/places/web-service/data-fields), [field masks](https://developers.google.com/maps/documentation/places/web-service/choose-fields), [current pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [OAuth scopes](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchText#authorization-scopes).

## Safeguards and provider policies

The existing budget reserves atomically before authentication/Places I/O. Failed authentication and data requests retain the reservation; an authentication failure before the Places POST is not reported as a live Places attempt. Exact requests are hashed in memory for duplicate prevention; no precise coordinates are stored in those identities. Changed starting/travel inputs do not cause duplicate discovery queries. The outing/session request ceilings, four-search ceiling, concurrency one, candidate ceiling three and zero retries remain unchanged. Automatic OAuth recovery never resends a Places POST; HTTP redirects are refused. Empty results stay empty; provider/authentication/permission/quota/timeout/invalid-response failures return safe errors without fictional fallback or raw sensitive internals.

Google's error guidance suggests retries for some failures; this project's stricter zero-retry rule takes precedence. [Error guidance](https://developers.google.com/maps/documentation/places/web-service/web-services-best-practices).

Keep provider content in transient memory for inspection; do not build a persistent venue cache or save raw responses/fixtures from live searches. Google restricts storage/caching, with specific exceptions including place IDs. Before future public frontend integration, comply with Google's Terms/Privacy Policy requirements, Google Maps attribution/logo for results shown without a map, Google-map requirements for map displays, and supplied third-party attributions. This backend-only development work introduces no public Places display. The candidate contract retains attributions for that later display work; a provider string alone is not sufficient public attribution. [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies).

## Verification on October 23, 2026

Exactly **two live Places Text Search attempts**, including failures, with existing ADC/service-account impersonation and project `where-to-512422`:

1. Bowling in `Baltimore, MD`, with explicit destination taking precedence over separate public Washington, DC reference coordinates: **HTTP 400**. The first implementation used an invalid 360-degree-wide bias rectangle. The generic viewport guide allows world bounds, but the method-specific reference imposes a 180-degree maximum. No automatic retry occurred.
2. Same activity/destination using the corrected 180-degree rectangle: **HTTP 200**, **three candidates**, all three accepted against returned Baltimore/MD geographic components, zero excluded. This verifies actual local OAuth access to Places, not just token issuance.

Both used the fixed field mask above, no pagination, no expensive optional fields, no Details/Nearby/Routes, and existing/lowered verification budgets. No Places quota/billing errors occurred. The originally planned Washington coordinate search was **not sent**, preserving the two-attempt maximum; coordinate/radius behavior is verified offline only. Development switches existed only in isolated verification processes, were removed in `finally`, and the disabled command was verified afterward. No further live requests are authorized by Task 40.

Preflight reverified all 36 quota values, including the 17 prior reductions, and both enabled APIs through read-only Service Usage administration. Console reverified the existing Free Trial ($300/90 days displayed), $50 account-wide monthly budget, actual alerts at $25/$45/$50, excluded credits and billing-admin/user recipients. An optional Cloud Billing administration API inspection returned **403 SERVICE_DISABLED**; it was left disabled and Console supplied the verification instead. That administration failure is separate from Places access and is not evidence of an unlinked billing account. No upgrade, quota increase, new role, new project, new key or financial terms action occurred. Alert delivery and posted charges were not tested.

Offline tests cover query mappings, geographic evidence, city/neighborhood/coordinates/radius, destination precedence, independent start/travel fields, parsing/empty/malformed results, provider errors, missing/expired/wrong-identity ADC, timeouts, disabled gates, exact masks, no redirects/retries, budgets and mock isolation. All fixtures are synthetic. Full backend and frontend regression results are recorded in HANDOVER.md. No browser planner/geolocation journey, actual Ollama smoke or frontend visual checks were performed for this backend-only task.

## Task 41 canonical venue facts — October 24, 2026

Task 41 is an **offline normalization layer**, separate from field selection and network access. `backend/venue_models.py` defines `VenueFacts`; `backend/venue_normalization.py` converts Google Place objects into it. The website/planner continues using the shared fictional catalog. No live Google request, new field mask, enrichment transport, quota change, database or cache was introduced. Tasks 42–46 are unstarted.

### Model boundaries and mapping

The existing `Venue`/`ScheduledEvent` contract describes planner stops: USD/person cost, duration, capacity, fictional routing zone, and (for event categories) a dated session with a start. Google's Place describes a **physical building/business**, including stadiums and theaters; its hours do not establish a game, showtime, reservation, ticket inventory or bookable session. Converting it directly into `ScheduledEvent` would require inventing those facts. `VenueFacts` is the canonical physical-place contract for future real discovery, not a second planner or an alternative session schema. Both reuse the small `VenueIdentity` base (`id`, `name`, existing `ActivityType`); coordinate validation is also shared with Task 40. Existing mock record values and public planner payloads are preserved.

| Google input | Canonical `VenueFacts` field | Behavior |
| --- | --- | --- |
| `id` | `id` | Original provider ID, never generated, truncated or trimmed; whitespace-invalid IDs rejected. Identity is scoped by `provider`. |
| Source adapter | `provider`, `evidence` | `google_places`, `provider_supplied`; means supplied by the provider, not independently verified. Test responses are synthetic. |
| Caller activity | `activity` | Existing 29-category enum; derived search context, **not** provider-confirmed relevance. No type matching/ranking here. |
| `displayName.text` | `name` | Nonblank human-readable name. `name` resource path is never used as a fallback. |
| `name` | `resourceName` | Optional `places/<id>` resource path; must agree with `id`. |
| `formattedAddress`, `location` | `address`, `coordinates` | Nullable address and finite latitude/longitude; valid ranges −90…90 and −180…180. No inferred location. |
| `types`, `primaryType` | `providerTypes`, `primaryType` | Nullable supplied type strings (list and optional primary), including unfamiliar future types; no invented classifications. |
| `rating`, `userRatingCount` | `rating`, `ratingCount` | Nullable rating 1…5 and nonnegative integer count. No mapping to the mock `experience` tier. |
| `regularOpeningHours` | `regularOpeningHours` | Typical venue hours, structured periods and optional localized descriptions. |
| `currentOpeningHours` | `currentOpeningHours` | Separate current/exceptional hours snapshot, including dated periods and special dates when supplied. |
| `websiteUri`, `googleMapsUri` | `websiteUrl`, `mapsUrl` | Nullable HTTP(S) URLs. Credentials in URLs and other schemes are rejected; links are not fetched. |
| `priceLevel` | `priceLevel` | Nullable free/inexpensive/moderate/expensive/very_expensive indicator; unspecified becomes null. |
| `priceRange.startPrice`, `.endPrice` | `priceRange.start`, `.end` | Nullable exact decimal amounts and source currencies. End may be absent; supplied bounds must be ordered and share a currency. This is **not** a per-person quote or ticket price. |
| `timeZone.id`, `.version` | `timeZone` | Supplied IANA zone (validated with the installed timezone database) and optional provider version. Unknown zones reject safely. No inferred Baltimore zone. |
| `utcOffsetMinutes` | `utcOffsetMinutes` | Separate nullable offset −840…840, including zero. An offset alone is not an IANA zone or future DST rule. |
| `attributions[].provider`, `.providerUri` | `attributions[].provider`, `.uri` | Required supplied credit information, with HTTP(S) URI validation. No attribution is invented. |
| Local receipt clock | `observedAt` | Timezone-aware timestamps by supplied scalar/list path. Derived ingestion metadata, not Google's update time, licensing permission or proof of freshness. |

`addressComponents` remains Task 40's geographic-check input; the validated formatted address is the canonical address. Raw geographic component payloads, reviews, photos, AI summaries and unknown provider extensions are not copied into canonical records. No unsupported details are requested to populate the schema.

A new canonical record requires an original ID, readable name and valid caller category. Other facts are optional and remain **null** if missing or explicitly null. Empty arrays retain their supplied meaning; no missing rating/price becomes zero and no absent hours mean open. A zero **rating count** is valid; zero is not a valid supplied rating. Booleans, numeric strings and nonfinite values are rejected for ordinary numeric fields. Google Money's documented int64 string encoding is parsed explicitly, with exact nanos and protobuf zero semantics only for a missing component of an otherwise supplied amount; a missing entire price/amount is never free. Normalized schemas forbid unknown canonical fields. Google extension fields are ignored by the provider adapter.

Structured hours retain Sunday-based weekday numbers, local hour/minute, optional exact dates, truncated flags, open-ended periods, localized descriptions, explicit `openNow`, special dates and timezone-aware next-open/close timestamps. Date/weekday disagreements, invalid dates/clock values, reversed dated periods and malformed structures reject safely. Missing required point components are rejected conservatively rather than repaired. Overnight/week-boundary periods and Google's open-only 24-hour representation are preserved; **no scheduling evaluation** occurs. `periods: null` is unknown; explicitly returned `periods: []` is an empty provider schedule, not unknown. `openNow` is an observation at response time, never future availability. Localized text does not become executable windows.

### Pure conversion and later partial enrichment

- `normalize_google_place(raw, activity, observed_at=...)` validates one raw Google Place object. Malformed supported fields reject the entire record with a fixed `NormalizationError` that excludes raw input/credentials.
- `normalize_google_places(records, activity, observed_at=...)` isolates invalid entries in an already bounded collection, returning `(valid_records, rejected_count)` in input order. It does not deduplicate, rank, refill or issue requests. Task 40's transport/geographic parser retains its existing fail-closed behavior for malformed discovery responses.
- `normalize_discovery_candidates(result, activity, observed_at=...)` bridges Task 40's minimal six-field in-memory DTO into the same canonical model. Because the DTO contains only those fields, optional Enterprise facts remain null. Task 42 now uses this bridge in discovery and adds development reason counts.
- `normalize_google_place(partial_raw, activity, existing=facts, observed_at=...)` accepts a later partial response containing the **same Google ID** without requiring the name again. It revalidates all fields/instances, refuses a different provider/ID/category/evidence, retains missing/null/unspecified existing facts, and ignores older field observations. Nested missing/null values also retain existing facts. Supplied lists (including complete hours-period lists) replace whole snapshots; individual period lists are never stitched together. Nested scalar/list paths retain separate observation times, so a new `openNow` does not make retained periods or next-open timestamps fresh. A future evaluator must check the relevant observations before using a composite record. Credits accumulate without dropping previous supplied attributions. Inputs remain unchanged. These are pure in-memory merge mechanics, **not** a cache or a live enrichment pipeline.

A future optional Details adapter, if separately authorized, should accept one stable ID plus an explicit reviewed field allowlist and the existing shared outing budget. It must check disabled-by-default live authorization **before authentication**, reserve `details` before any attempt, use existing backend-only impersonated authentication/quota attribution, enforce candidate/session/concurrency limits, and keep zero retries. It should return a partial Place for the pure function above, never call Details automatically for every candidate. No Details transport/stub, enabling setting or speculative new limit was added in Task 41.

### Current field costs

Reviewed the official [field-tier matrix](https://developers.google.com/maps/documentation/places/web-service/data-fields), [Text Search field masks](https://developers.google.com/maps/documentation/places/web-service/text-search), [Place representation](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [field-mask guidance](https://developers.google.com/maps/documentation/places/web-service/choose-fields) and [global pricing](https://developers.google.com/maps/billing-and-pricing/pricing) on October 24, 2026. The current six-field mask shown above is **unchanged**. Support in a parser does not request or enable a field.

| Fields | Text Search tier | Place Details tier if used later | Requested today? |
| --- | --- | --- | --- |
| `id`, resource `name`, `attributions` | Essentials IDs Only | Essentials IDs Only | `id`, `attributions` only |
| `formattedAddress`, `location`, `addressComponents`, `types` | Pro | Essentials | First three only |
| `displayName`, `googleMapsUri`, `timeZone`, `utcOffsetMinutes` | Pro | Pro | `displayName` only |
| `rating`, `userRatingCount`, `regularOpeningHours`, `currentOpeningHours`, `websiteUri`, `priceLevel`, `priceRange` | Enterprise | Enterprise | **No**; synthetic-response tests only |

Billing follows the highest requested SKU tier, not how many returned values are populated. The currently used Text Search Pro list rate remains **$32/1,000** with **5,000** free monthly events; Text Search Enterprise is **$35/1,000** with **1,000** free events. Future Details Enterprise is a separate **$20/1,000** SKU with **1,000** free events. These are global first paid-tier list rates, before allowances/credits and subject to account terms and changes; no posted charges were measured. Enterprise is a field-triggered billing category, not a schema subscription to enable. No reviews, photos, atmosphere fields or summaries are needed. Existing alerts are not hard caps; all quotas/application ceilings/authentication/live locks remain unchanged.

### Storage, display and refresh rules

Reviewed the official [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies), [non-EEA service-specific terms §14](https://cloud.google.com/maps-platform/terms/maps-service-terms) and [Place ID guidance](https://developers.google.com/maps/documentation/places/web-service/place-id) on October 24, 2026. Account-specific agreements and billing location govern; EEA terms differ. This implementation takes the conservative transient-memory approach and introduces **no persistent storage**.

- Place IDs are exempt from the content caching restriction and may be retained indefinitely. Google recommends refreshing IDs older than 12 months; IDs can change/become obsolete. No refresh requests were added.
- The non-EEA Places terms specifically permit caching latitude/longitude for **up to 30 consecutive calendar days**, then require deleting them. This exception is not permission to cache the entire record for 30 days. We do not implement even that coordinate cache here.
- Names, addresses, types, ratings/counts, hours, websites, Maps links and price indicators remain restricted Places content. Do not persist raw or normalized content, logs, snapshots, production fixtures or future saved itineraries containing it without a separately reviewed applicable permission. Renaming fields into a provider-neutral model does not remove Google's restrictions. Keep attribution attached during permitted transient use; no general retention exception is assumed for attribution payloads.
- Places content may be displayed without a map with the required **Google Maps** attribution/logo under the current guidelines. On a map, it must use a Google map; do not mix it with a non-Google map. Supplied third-party credits must also accompany their content. Provider identity text alone is insufficient. Public Terms of Use and Privacy Policy obligations also apply before frontend integration. Task 41 adds no public provider display or Task 45 labeling system.
- A receipt timestamp does not authorize retention or promise validity. Recheck applicable terms and permitted refresh behavior before future persistence/public display. Hours/ratings/prices can change; never reuse them indefinitely or treat cached `openNow` as a future booking. Any refresh/enrichment must remain optional, separately authorized and budgeted; no automatic refresh exists.

Task 41 uses only invented Google-shaped fixtures in automated tests. No new live Google Places/Routes calls occurred. Backend/frontend regression results and limitations are recorded in HANDOVER.md. Task 42 will add venue deduplication and relevance checks; none were implemented here.

## Task 42 deduplication and relevance — October 24, 2026

The development discovery path now runs geographic validation → Task 41 normalization → pure `backend/venue_quality.py` checks → distinct candidates. `backend/venue_geography.py` shares the existing great-circle calculation and geographic evidence checks; it has no transport or authentication. No route, public endpoint, UI, planner integration, ranking engine, extra query, dependency or persistent cache was added.

`discover(request)` keeps the existing single-search interface. `discover_many(requests)` explicitly accepts up to the unchanged outing search ceiling, shares the same outing budget, requires the same effective area for every request and combines their results. Every actual search still reserves its exact request hash before authentication/transport. Repeated identical requests are refused by the existing budget, not retried. No hidden query expansion, paging or refill takes place. Use one call with the requested activities to deduplicate across them; separate calls do not retain a result cache. A future planner must use the combined associations when deciding whether activities share one physical stop.

`DiscoveryResult.candidates` retains the minimal Task 40 DTO. In-memory `result.venues` supplies canonical merged facts, original source observations, supported requested `activities` and a relevance verdict for each association. `facts.activity` is a deterministic representative (alphabetically first retained category), not the complete activity list. `venues` and `diagnostics` are excluded from normal result serialization. Nothing adds them to public planner responses. The development-only command prints counts and reason codes, never names, IDs, payloads, coordinates or credentials.

### Identity and safe merging

- Exact `(provider, original Place ID)` is primary identity across queries/categories. IDs remain case-sensitive and untouched; whitespace-invalid discovery IDs are rejected instead of silently trimmed.
- Different IDs merge only with **all** of: identical normalized full name of at least two words; identical full address containing a number, including unit/screen distinctions; returned coordinates within **10 meters**; the identical website URL with a non-root, non-generic venue path; no conflicting supplied primary types; and overlapping specific provider types if both records supply them. Case, accents and punctuation normalize for comparison; brand prefixes, address abbreviations and unit numbers are not stripped. A shared brand/building/address/point alone is insufficient. No website is fetched.
- Today's six-field mask does **not** supply websites. Different IDs with only name/address/point corroboration therefore remain separate. This intentionally tolerates possible duplicates to protect same-brand concessions, cinemas and businesses inside complexes. Richer alias tests use invented optional-field responses only; no details call buys missing evidence. Even a matching venue URL is corroboration, not an absolute guarantee; conflicting names, units, primary types or distance retain separate records.
- Alias groups require pairwise corroboration against every member. A chain of near neighbors cannot collapse distant endpoints. Sorting identities before grouping makes grouping independent of input order. Output groups follow the first occurrence in provider/query order; this deliberately preserves meaningful search order, rather than sorting recommendations by ID.
- Merge canonical facts **before** evaluating requested activity associations, so a duplicate response can supply missing relevance evidence. Missing/null values never overwrite known facts. Newer per-field receipt times win; equal-time conflicts use a deterministic serialized-record tie break. Missing nested facts can complement one another, but incompatible nested bounds/currencies cannot create an invalid price range. Opening-period lists stay atomic snapshots. Credits and provider types accumulate; their union uses the oldest contributing receipt time, or an unknown time if any contribution lacks one, so older evidence is not made fresh. All original IDs, source observations, conflicting facts, evidence and timestamps remain in `sources`; the representative ID is the lexicographically first original ID, never an invented ID. Resource names remain paired with that representative ID.
- One physical venue can retain several requested activities, each with its own evidence assessment. This prepares later stop identity checks; no itinerary scheduling or optimization is implemented.

### Activity evidence and uncertainty

Rules cover every existing category; they do not claim performances, games or bookable sessions exist. Provider types and optional primary type are parsed when already legitimately supplied to the canonical normalizer. Both are absent under the unchanged current mask. Unknown future types are preserved and do not count as negative evidence. See Google's [official type definitions](https://developers.google.com/maps/documentation/places/web-service/place-types), consulted for these rules.

| Categories | Useful evidence and limitations |
| --- | --- |
| food, drinks, coffee | Restaurant subtypes/food courts, bars/pubs, cafes/coffee shops respectively; activity-specific name phrases provide weaker support. A cafe's existence does not establish prices or a dinner menu. |
| movie, bowling, arcade | Movie theater, bowling alley and video arcade types. Names alone remain uncertain; cinemas are not assumed to offer bowling. Multi-purpose venues with multiple matching types retain each association. |
| museum, art | Museum types versus art galleries/art museums. Generic museum evidence does not prove an art gallery. |
| outdoors, hiking, picnic | Park/garden types support outdoors; hiking areas and picnic/barbecue grounds support their narrower activities. A generic park does not prove a trail or picnic facility. |
| karaoke, escape, miniGolf, skating | Karaoke, miniature golf and ice-skating types where available; specific names such as escape rooms and roller rinks offer weaker evidence. Generic amusement centers do not prove a particular facility. |
| shopping, zoo | Malls/department stores/markets and zoo/wildlife-park types respectively. A shared complex or address does not identify a tenant. |
| baseball, basketball, football, soccer, hockey, sports | General stadium/arena/sports-complex types support sports only. Named sport evidence stays uncertain; a stadium alone does not establish which sport or any scheduled game. |
| concert, theater, musical, ballet, opera, comedy | Specific concert/live-music, performing-arts, opera-house and comedy-club types help. Broad theaters do not prove musicals/ballet. Names are weaker evidence; no showtimes or ticket availability are inferred. |

Verdicts are `strong` (matching specific provider type), `uncertain` (name support, insufficient evidence, or mixed business-name/type evidence), or `mismatch`. Clear unrelated business types/service names, and selected narrow incompatible venue types/names, remove the corresponding activity association. Examples include a dental clinic for bowling, an insurance business matching “escape,” theater equipment suppliers, coffee supply stores and Bowling Green parks. Word boundaries avoid interpreting “barber” as a bar. A matching legitimate activity type can keep a conflicting business name uncertain. Multi-purpose businesses are not excluded merely for also having other types. If every requested association is a mismatch, the venue is excluded. A missing type never causes rejection by itself, and a name match alone never becomes strong verification.

This is conservative evidence screening, not exhaustive business understanding. Unsupported aliases, opaque brand names and broad facility types can remain uncertain. Such candidates are not promises of facilities, hours, prices, sessions or availability. No AI/model call or provider-detail lookup resolves them. Empty/small results remain empty/small; real results never contain fictional replacements.

### Geography, diagnostics and safeguards

Named destinations still require all comma-separated geographic parts in provider address components, independently of business/street names. City/neighborhood checks now disallow county-only evidence with the same name (for example, Baltimore County cannot establish Baltimore city). Missing neighborhood evidence is excluded rather than broadening to another neighborhood. Punctuation, accent and short/long component spellings remain supported. No geocoder or verified boundary polygon dataset is available here: these are structured provider geographic evidence checks, **not polygon containment proof**; ambiguous names/omitted components can yield fewer results. No invented boundary, city-center radius or arbitrary city travel cap substitutes for missing geographic information.

Explicit validated coordinate/radius inputs enforce actual returned great-circle distances, including antimeridian cases. Coordinate-only inputs without a radius remain a bias. Destination takes precedence over unrelated current location/radius. Starting location and future travel constraints remain separate, unsent and unevaluated; straight-line distance never becomes driving time. Canonical coordinates and source context remain in memory for later use.

Development reason counts: `area_unverified`, `outside_radius`, `invalid_normalized_venue`, `duplicate_place_id`, `corroborated_alias`, `matching_provider_type`, `name_support_only`, `insufficient_activity_evidence`, `conflicting_business_name`, `unrelated_business_type`, `incompatible_venue_type`, `incompatible_venue_name`. Activity counts describe merged-identity evidence for source observations; duplicate counts describe collapsed observations. They may overlap and must not be summed as independent exclusions. `excluded_count` is returned observations minus final distinct venues, including geographic exclusions. Per-venue association verdicts are available in memory; no raw-input logging is needed to inspect decisions.

The optional canonical `primaryType` mapping adds no requested field. Existing field mask, backend-only OAuth, quotas, application limits, zero retries, default mock mode and development gate are unchanged. **Zero live Places/Routes requests** were made for Task 42. No Place Details transport or billable enrichment exists. The fictional planner remains isolated. Task 43 (actual driving/walking route calculation) has not started.

## Task 43 routing boundary

The separate [backend route calculator](route-calculator.md) can consume Task 41 canonical Google venue IDs or validated venue coordinates after Task 42 candidate checks. It does not invoke discovery, buy missing details or expand candidate pools. Multiple activity associations can share a locally labeled same-venue transition. Destination area, optional explicitly authorized start, venue candidates and separate first-leg/inter-stop travel constraints retain their distinct meanings. Discovery behavior, field mask and live gate are unchanged. No new Places request occurred. Full feasibility is Task 44; public source labeling is Task 45 and real-data planner integration is Task 46.
