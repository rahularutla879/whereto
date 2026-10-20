# Current architecture

Source baseline: October 20, 2026. A single-page Next.js App Router application with a client component and local planning modules, plus a minimal FastAPI backend. Next.js serves/renders the page; user-facing itinerary generation runs synchronously in the client. Python also has standalone candidate generation (Task 26) and constraint evaluation/ranking (Task 27). The backend only exposes health status; no backend planning endpoint or external service is implemented.

```text
Root layout + global styles
          |
Homepage: request text + optional preferences (React state)
          |
makePlans -> parse activities/location + resolve date
          |
Validate input -> fictional catalog -> capacity/date filtering
          |
Enumerate venue combinations in requested activity order
          |
Budget/travel filtering -> schedule stops -> rank/deduplicate
          |
Up to 3 cards + expandable details, or explanatory empty state
```

## Backend health boundary (Task 23)

`Browser or HTTP client -> Next.js GET /api/health -> FastAPI GET /health`

FastAPI runs locally through Uvicorn on `127.0.0.1:8000`. Next.js calls it server-side using `BACKEND_URL`, defaulting to that address; the variable is never sent to browser code. The homepage does not call the health endpoint or depend on backend availability. No CORS middleware is needed for this server-to-server call.

The Next.js route disables fetch/response caching, validates the expected status, and enforces a three-second timeout. Success returns `{"status":"ok","backend":"ok"}`; connection failures, timeouts, invalid JSON/status, and upstream HTTP errors return HTTP 503 `{"status":"error","backend":"unavailable"}` without exposing internal errors. Tests use local HTTP servers; Python's standard test library avoids extra backend test packages.

## Input to itinerary

1. app/page.tsx handles form submission and calls makePlans. Preferences override corresponding parsed values; blank fields use recognized text or defaults (Baltimore, four people, no budget/travel cap, balanced ranking).
2. lib/request.ts recognizes catalog keywords, preserves first-mentioned activity order, and reports unmatched text. Dates use Baltimore's calendar; an explicit reference day supports repeatable tests.
3. lib/planner.ts rejects unsupported cities/wording, invalid limits, and more than four distinct activities. Events require an exact matching fixture date. Candidate pools must have adequate mock capacity.
4. It enumerates venue combinations without reordering activities. Mock travel per leg is `5 + abs(zone difference) * 8` minutes. Total activity cost and total inter-stop travel must fit hard limits.
5. Scheduling starts ordinary stops at 10 AM, delays food to at least 5 PM when the request says dinner, and respects fixed event starts, travel, and a midnight finish. Duration includes waiting between stops.
6. Budget, balanced, and experience scores each select a best candidate; the selected preference comes first and duplicate winners are omitted. Cards show mock per-person cost, group total, travel, and scheduled stops. No result is persisted.

## Key files

| File | Responsibility |
| --- | --- |
| backend/models.py | Pydantic request, venue/event, final-plan and candidate contracts, scalar types, and integrity validation |
| backend/planner.py | Deterministic ordered Python candidate generation and lazy traversal (Task 26) |
| backend/ranking.py | Candidate evaluation, schedules, cost/travel adapters, normalized scores and distinct selection (Task 27) |
| backend/test_ranking.py | Hard limits, uncertainty, scheduling, scoring, distinct selection and generator integration |
| backend/test_planner.py | Generator completeness, identity, event timing, uncertainty, validation and lazy traversal tests |
| backend/test_models.py | Request/schedule/result tests, live TypeScript contract comparison, and FastAPI schema compatibility |
| backend/main.py | FastAPI application and health endpoint |
| backend/requirements.txt | Pinned essential backend dependencies and required transitive packages |
| backend/test_health.py | Uvicorn HTTP health test |
| app/api/health/route.ts | Server-side health communication with timeout and failure response |
| app/api/health/route.test.ts | HTTP communication and failure tests |
| .env.example | Optional server-only backend address |
| app/layout.tsx | Root HTML, metadata, global stylesheet import |
| app/page.tsx | Homepage, request/preferences state, submit behavior, result/empty states, PlanCard expansion |
| app/globals.css | Tailwind import, colors, typography, responsive layout, reduced-motion styles |
| components/artwork.tsx | Original inline SVG hero/card illustrations |
| lib/request.ts | Activity/location parsing and calendar-date helpers |
| data/mock-venues.json | Shared fictional catalog values, three tier definitions, two event dates |
| lib/mock-data.ts | Typed catalog adapter, keyword patterns, existing frontend record expansion |
| backend/mock_data.py | Validated shared fixture loading and category/kind/date/ID retrieval |
| backend/test_mock_data.py | Fixture/lookup/provenance tests, frontend parity, pre-migration output fingerprints |
| lib/planner.ts | Validation, combinations, mock travel, scheduling, ranking, display helpers |
| lib/planner.test.ts | Automated planner and parser behavior tests |
| package.json | Dependencies and development/check commands |
| next.config.ts, tsconfig.json, eslint.config.mjs, postcss.config.mjs | Framework, TypeScript, lint, and stylesheet tooling |

React state holds requests, preferences, results, and expanded cards in memory. There is no database, browser persistence, account system, or cross-session history. Icons use lucide-react; illustrations and fonts need no external media service.

## Backend data contract (Task 24)

`backend/models.py` is the single Python definition module. It uses the Pydantic dependency already pinned for FastAPI; no new dependencies or runtime routes were added. Models can be imported by future FastAPI endpoints. An isolated OpenAPI test verifies request/response schema generation without adding a planning route to the application.

- `ActivityType` carries the exact 29 TypeScript activity IDs, including `miniGolf`. `CostPreference` uses `budget`, `balanced`, and `experience` for the existing Budget-friendly, Balanced, and Best experience controls.
- `OutingRequest` represents **resolved** inputs: ordered `activities` (one to four; repeated entries permitted since Task 26), `location` (default Baltimore), `people` (default four), optional `date`, `budget`, `travel`, `transport`, `cost` (default balanced), and `dinner` (default false), plus `allowRevisits` (default false, Task 26). A future boundary must resolve text/defaults/UI overrides before constructing this model; this task does not port the parser or the UI's string-valued `Preferences` object.
- Group size, location, calendar dates, money, start/end times, duration, capacity, and travel limits use reusable validated scalar types rather than wrapper objects or duplicate definitions. Groups accept whole numbers 1–100, budgets accept finite USD/person values 0–100,000, and travel accepts whole minutes 0–1440, matching existing form/planner limits. No limit is inferred from the fictional catalog's maximum capacity of 20.
- `activities`, resolved `location`/`people`, an explicitly supplied date, budget, and travel cap are mandatory constraints. `cost` only ranks feasible options. `transport` is an optional preference with walking/cycling/driving/transit values for future use; null is intentional because today's mock formula has no transport mode. It does not implement routing. `dinner` records the parsed dinner timing requirement for future scheduling; the models do not generate a schedule.
- Null budget/travel means **no cap**; zero means a real hard limit. Null request date means a flexible day for regular venues; scheduled activity categories require an exact valid `YYYY-MM-DD` date. No schema restriction to fixture dates or Baltimore is imposed: supported location, fixture availability, and feasibility remain planner decisions. Task 25 loads the shared fixture separately; no catalog values are embedded in the models.
- `Venue` and `ScheduledEvent` form a discriminated union using `kind`. Scheduled categories require event records with `eventDate` and fixed `start`. Other venue fields retain TypeScript names: `id`, `name`, `activity`, `neighborhood`, `price`, `duration`, `zone`, `experience`, `capacity`. Unknown optional information is null; it must never be interpreted as zero cost, unlimited capacity, or verified availability. Optional `source`, `openingHours`, and `availability` preserve missing information honestly; they do not perform any lookup.
- `ItineraryStop` preserves `{venue, start, end}`. `Itinerary` preserves every existing Plan field, including `venues`, `stops`, per-person `price`, total inter-stop `travel`, elapsed `duration`, `people`, card copy/theme, and ISO `date` or the legacy `"Any day"` label. Start times are whole minutes 0–1439; end may be 1440 (midnight). All times are Baltimore local time, `America/New_York`, matching the current single-day planner. No UTC conversion or timezone inference is performed.
- Response integrity checks enforce positive stop duration, known venue duration, fixed event starts and dates, non-overlap, known capacity, matching venue/stop order, distinct activity categories, elapsed itinerary duration, room for travel within schedule gaps, and consistent known per-person costs. These checks validate supplied schedules; they do not select venues, calculate mock routes, or generate itineraries. Request-to-result hard-limit enforcement and dinner scheduling remain responsibilities of the future planner.
- `PlanningResult` retains `{plans, message, location, activities, notes}` and adds optional structured `errors` (`PlanningError`: code/message/optional field). At most three distinct plans are allowed, every plan preserves all activities in order, and errors cannot accompany partial plans. Legacy empty results with only the explanatory message remain valid.
- `DataStatus` and `DataQuality` distinguish unknown, fictional, estimated, and verified identity/price/capacity/duration/schedule/travel/experience values. Venue and itinerary `dataQuality` default to unknown, never verified. Producers must explicitly label fixture values fictional; existing legacy payloads lack this metadata, so parsing them does not automatically identify their source. Mixed statuses are possible, and null values always remain unknown. Metadata is descriptive, not independent verification. Costs exclude transport, tax, tips, fees, and extras; travel excludes getting to the first stop and returning home. Elapsed duration includes waiting.

Example resolved request (not a new endpoint):

```json
{"activities":["food","concert"],"location":"Baltimore","people":4,"date":"2026-11-07","budget":60,"travel":30,"cost":"balanced","dinner":true}
```

Models reject unknown field names and invalid numeric values, including boolean quantities and non-finite costs. JSON dates serialize to ISO strings and enum values to the existing frontend IDs. `model_dump(mode="json", exclude_unset=True)` round-trips current TypeScript result payloads without injecting optional metadata. Default serialization includes optional fields/defaults for a future richer contract. Unknown venue information will require deliberate frontend rendering before a future endpoint sends nulls to today's UI; no such integration is implemented here.

`backend/test_models.py` executes the unchanged TypeScript planner for all 29 categories and representative multi-stop, event, capacity, zero-limit, and failure cases, then validates and round-trips its actual results. This one contract test needs the already-installed frontend Node dependencies; the other model tests use Python plus existing backend dependencies. The frontend and Python definitions remain separate because they serve different runtimes; this check detects drift without copying the catalog.

## Shared fictional dataset (Task 25)

`data/mock-venues.json -> lib/mock-data.ts` (browser) and `backend/mock_data.py` (Python).

The JSON contains the 29 activity definitions, three fictional tiers, and two unchanged event dates. Both runtimes expand these small definitions in the same category/tier/date order into 51 ordinary venue records and 72 event occurrences. This avoids storing expanded duplicates or independently editable catalogs. TypeScript keeps its regular expressions and the existing public exports; no build tool, dependency, endpoint, or backend connection was added. The fictional zone inputs are shared; Task 27 also implements the same deterministic travel convention in Python. Opening hours and actual availability were never supplied and remain unknown.

`load_mock_venues()` resolves the fixture relative to the module, validates its schema and all expanded records with the Task 24 `VenueInformation` union, and returns fresh models. An optional fixture path supports tests; invalid data raises errors instead of returning a partial catalog. Python adds a source reference and explicit `fictional` data-quality statuses to supplied values; events have fictional schedules, while ordinary venue schedules stay unknown. No existing contract field or model changed. All money is USD/person and event clock values remain minutes after midnight in America/New_York.

`SUPPORTED_ACTIVITIES` comes from the 29-value `ActivityType` enum. `available_activities()` reports only categories present in the records; currently all 29 have samples. `get_mock_venues(activity, event_date=..., kind=...)` retrieves matching records in fixture order. With no date it returns all event occurrences; with a date it keeps only exact event matches plus ordinary venues (without asserting opening hours). Supported categories with no records return `[]`; unsupported IDs, invalid dates and invalid kinds raise errors. `get_mock_venue(id)` returns the exact record or `None`. No capacity/budget feasibility, travel calculation, ranking or itinerary generation is implemented.

`backend/test_mock_data.py` compares every record with the actual frontend exports and checks fixed fingerprints of pre-migration frontend records and 33 representative planner results. Those fingerprints guard legacy values/results without maintaining a second editable dataset. Deliberate future catalog or result changes require explicitly updating the baseline. Missing-sample tests remove a category from a temporary fixture and prove support remains without fabricating replacement venues.

## Python candidate generation (Task 26)

`OutingRequest -> validated shared fixture -> activity/date pools -> depth-first ordered combinations -> CandidateItinerary`

`backend/planner.py` offers `generate_candidates(request)` for a serializable `CandidateGenerationResult` and `iter_itinerary_candidates(request)` for lazy consumption. Both preserve every requested activity occurrence and fixture order. They use the existing loader/retrieval functions; there is no copied dataset. Missing records return structured `no_availability` errors in the collected result, unsupported locations return `unsupported_location`, and identity/fixed-time incompatibility returns `infeasible`. Invalid activity IDs and missing required event dates remain request validation errors. The iterator yields nothing for unavailable requests; use the collected result when explanations are needed.

Traversal retains only the current route and candidate pools, prunes duplicate IDs (unless `allowRevisits=True`) and fixed-time conflicts early, and yields each candidate independently. There is no truncation, sorting, optimization, or top-three selection. The collected API materializes all results, at most 81 for the current fixture/request limits; callers working with larger catalogs can stream via the iterator. Stable candidate IDs hash canonical request JSON and ordered venue IDs. IDs express source record identity, not independently verified physical venue identity; the fixture supplies no separate building/event-alias identifiers.

Candidate contracts reuse `OutingRequest`, `VenueInformation`, `PlanningError`, and validated scalar types. `CandidateStop` retains venue/start/end with nullable times; `CandidateItinerary` retains ID, ordered venues/stops, people, date, and revisit permission. `CandidateGenerationResult` carries the resolved request, candidates, errors, and explanation, validating request/order consistency. They intentionally omit final-plan display copy, price/travel/duration totals and ranking. Existing `Itinerary`/`PlanningResult` contracts remain strict final outputs; candidate objects are not payloads for today's frontend. Conversion to final plans and handling repeats in final plans belong to later work.

Ordinary stop times stay null. Scheduled stops copy the event's exact date/start and compute an end only from its supplied duration. Events on other dates never enter the pools. Fixed events must follow the requested order without overlap and must allow known intervening activity durations; unknown durations contribute only the positive lower bound implied by the model, without assigning a time. Revisit permission cannot override conflicting event times. No travel, opening-hour, capacity, budget, dinner-time, or complete-day feasibility is evaluated here. These candidates must pass Task 27 before being presented as feasible plans. Full original venue/event records retain fictional labels, sources, stable IDs and unknown fields. No route, endpoint, frontend call, third-party API or dependency was added.

Example backend use (not an API endpoint):

```python
from backend.models import OutingRequest
from backend.planner import generate_candidates, iter_itinerary_candidates

request = OutingRequest(activities=["coffee", "museum", "coffee"])
result = generate_candidates(request)  # 18 distinct-identity ordered candidates
# Stream candidates instead of collecting them for larger future catalogs:
for candidate in iter_itinerary_candidates(request):
    pass  # Future feasibility stage consumes these; no frontend connection yet.
```

## Python filtering and ranking (Task 27)

`recommend_plans(OutingRequest) -> generate_candidates -> evaluate_candidate -> score_candidates -> distinct selection -> RankingResult`

The standalone `backend/ranking.py` consumes Task 26 candidates and the same Task 24/25 records. `rank_candidates(request, iterable)` also accepts an existing candidate stream. No planning endpoint, text parser, frontend integration or dependency was added. The existing TypeScript planner is untouched; its exact catalog/output parity tests still pass. Its order, capacity, dinner-at-17:00, fixed events, midnight cutoff and zone simulation conventions carry over. Python uses normalized weighted scores instead of TypeScript's differently scaled strategy formulas, and considers alternate candidates when strategy winners would coincide.

Request additions are optional and backend-only: `groupBudget` (USD group activity cap), `maxLegTravel` (minutes per leg), `startTime` (earliest start, default 600), `endTime` (latest finish, default 1440), and `requireAvailability` (default false). Existing `budget` remains per person and `travel` remains total inter-stop travel. Both budget caps apply simultaneously when supplied; zero is a real cap. Start/end use the existing local minute types. Events still need an exact date. Transport is retained, but the simulation has no mode-specific routing.

`TimeWindow` adds structured daily or date-specific local `[start,end]` windows to venue `openingWindows` and `availabilityWindows`. A null list means unknown; `[]` explicitly means closed/unavailable. Supplied schedules, capacities and durations with unknown data-quality status remain provisional, as do quotes with unknown status. Dates must match; date-specific windows cannot establish feasibility for an unspecified day. Windows cannot span midnight. Free-form `openingHours`/`availability` text is preserved, but cannot establish a machine-checkable schedule. No hours or availability were fabricated in the shared fixture. Known event schedules establish the event's mock time window without a separate ordinary opening schedule; supplied event hours and availability are also honored. Explicitly required availability always needs structured evidence. This is not a reservation or inventory system.

Evaluation checks supported location and preserves all activity occurrences, order, people, date and revisit permission. Known capacity, per-person/group budget, total/per-leg travel, opening/availability windows, dinner timing, exact event starts/dates/durations, earliest start, latest end and midnight are hard constraints. Earliest-finish scheduling intersects windows and permits waiting; stop durations must fit one continuous window. Starting later cannot improve feasibility for these ordered, single-day constraints. Unknown durations/travel propagate unknown times; only positive duration/zero travel lower bounds are used to detect definite conflicts, never to invent an exact schedule. A later fixed event can anchor subsequent times again.

`RankedItinerary` retains the complete candidate and supplied metadata, planned stops with nullable start/end/duration, individual `PriceQuote`/`TravelQuote` provenance, known cost subtotals per person/group, complete cost totals when calculable, leg/total travel, activity duration, elapsed duration (including waiting), typed constraint issues, score components and structured recommendation reasons. Incomplete totals stay null. Decimal arithmetic enforces inclusive monetary caps without float boundary errors. Violated routes that exceed one day have no day-bounded total/timing value emitted.

Feasibility has three explicit states:

- `confirmed`: all evaluated hard constraints can be checked against supplied data. Fictional or estimated evidence retains its status; this never means verified real-world feasibility.
- `provisional`: no known violation, but evidence is missing. These alternatives appear only in `provisionalPlans`, with specific missing fields/actions; they are not confirmed recommendations.
- `violated`: at least one known hard violation. These are excluded from both selections, even if other fields are unknown.

`RankingResult.plans` contains confirmed recommendations only. `plans` plus `provisionalPlans` total at most three. Confirmed plans take priority. Today's ordinary venues have unknown hours, so ordinary/mixed outings produce provisional alternatives and an `insufficient_data` error when no confirmed plan exists. Event-only outings can pass against the fictional schedule/capacity data; `requireAvailability=True` keeps them provisional until availability evidence exists. No alternatives are returned merely to fill three slots. Empty results retain actionable errors and deterministic reason counts (one count per code per evaluated candidate). Missing pools/unsupported locations preserve the generator's errors.

Scoring runs only after known violations are removed. Affordability (complete per-person price, lower is better), quality (mean supplied experience tier, higher is better), and convenience (total travel, lower is better) use min/max normalization over the full eligible pool to `[0,1]`. A constant known component earns 1; an unknown component earns 0 and is never treated as free/instant/average quality. Scores are relative to this request's candidate pool, not comparable across different requests. Weights are:

| Mode | Affordability | Quality | Convenience |
| --- | --- | --- | --- |
| Budget-friendly (`budget`) | 0.75 | 0.10 | 0.15 |
| Balanced (`balanced`) | 0.35 | 0.40 | 0.25 |
| Best Experience (`experience`) | 0.10 | 0.75 | 0.15 |

Mandatory budgets are unchanged by mode. Ties use ordered record IDs, then candidate ID. Select the highest score first; subsequent choices prefer more changed stop identities among candidates within 0.15 of the best remaining score, then score and stable IDs. This provides variety without admitting a known violation or a large score drop for diversity. Exact ordered venue duplicates are removed. Record identity is the available measure of distinctness; the fixture has no physical-building aliases or real review scores.

Price and travel providers are injectable callables returning validated quote models. The default price provider reads the existing per-person field/status/source; the default travel provider uses exactly `5 + abs(zone difference) * 8` with explicit fictional provenance. Missing zones yield unknown travel. Providers receive the request (including people and transport), allowing future sourced estimates without rewriting scheduling/scoring. Provider failures are not silently converted into success or fabricated values. Current costs exclude transport, taxes, tips, fees and extras; travel excludes the first/last trip. No real routing is called.

Backend example (not a new API or frontend flow):

```python
from backend.models import OutingRequest
from backend.ranking import recommend_plans

result = recommend_plans(OutingRequest(
    activities=["baseball", "concert"], date="2026-11-07",
    budget=100, groupBudget=400, maxLegTravel=25, travel=30,
    cost="balanced",
))
# result.plans: only confirmed against supplied mock evidence
# result.provisionalPlans: separate alternatives requiring more information
```

Legacy `Itinerary`/`PlanningResult` validation remains unchanged for TypeScript compatibility. The richer Task 27 contracts support nullable calculations, repeated categories and explicit provisional alternatives instead of forcing incomplete evidence into a fully scheduled legacy card. Task 28 must deliberately handle this distinction before any frontend connection.

## Future architecture — not implemented

Stages 1–3 in [TASKS.md](TASKS.md) need real venue/event lookup and route information, richer constraints and optimization, then a map, editing, conversation, saved versions, and sharing. Server-side credential handling will be needed if selected providers require secrets. API boundaries, providers, AI model, map library, storage, authentication, and hosting remain undecided; this is not a committed design.
