# Task 40 venue discovery

Task 40 adds isolated backend discovery, not real-data itineraries. The website still uses the fictional catalog. No new FastAPI route or frontend/geolocation control was added. Tasks 41–46 remain unstarted.

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

Matching is deliberately conservative: Google may omit a neighborhood, use an alternative name or return nearby suburbs. Those unverified matches are excluded and counted, so an empty collection can mean no geographically verifiable results. Address components are not administrative boundary polygons; this is geographic evidence checking, not proof of a venue's availability/relevance or comprehensive coverage. Broader relevance, entity deduplication and aliases belong to Task 42.

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

Each candidate contains `provider="google_places"`, untouched `provider_id`, display name, address, validated coordinates and any attributions. It is a discovery-only contract, not a normalized planner `Venue` or a feasible itinerary. There is no invented hours/availability/showtime/capacity/price/route/travel evidence. Task 41 will add the normalized venue contract and deliberate handling of supported optional details, unknowns and field costs.

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
