> Current Task 49: explicit private saved plans now use a separate restricted Python/PostgreSQL connection, atomic writes and capability-scoped RLS. Browser refresh reopens the last saved plan; Google content remains transient. [Current architecture and limits](docs/saved-plans.md). Earlier sections retain historical checkpoints.

> Task 46 bowling diagnosis: `backend/planning_diagnostics.py` combines per-activity discovery audits with current routing/ranking coverage, emitting only aggregate counts and fixed reason codes in diagnostics and the existing About these estimates disclosure. The explicit bowling refinement permits evidence-backed mixed venues without widening geography; primary shortage can trigger the existing bounded route expansion. [Findings, definitions and live unknowns](docs/real-planning.md#task-46-diagnosis--repeated-bowling-venues).

> Current Task 46 application expansion: up to 20 retained candidates/activity, ten searches and 300 route elements under 30 attempts/outing; initial ten-result discovery and 6/4/4 shortlists remain. `backend/routing_expansion.py` selects bounded unsent directed evidence within original counters, with a recoverable preflight minute pause. Discovery response cursors live only in expiring continuations. [Current flow and boundaries](docs/real-planning.md#effective-budgets-and-local-operation). Older checkpoints below are historical.

> Earlier October 26 consolidated Task 46 checkpoint: 10-candidate discovery with type evidence and separately gated Enterprise ratings; whole-sequence geographic shortlists; the existing exact directed route/evidence/ranking flow; primary-venue diversity; budget-preserving options; explicit manual-origin Text Search and confirmation. See the current section below and [real planning](docs/real-planning.md). Earlier sections are historical snapshots.

> Task 46 current state: the existing pipeline now supports deliberately enabled local real Google venues/routes and on-demand contacts, with mock default. See the final Task 46 section and [complete flow](docs/real-planning.md). Earlier task sections retain their historical checkpoints.

> Current execution path (Task 31): homepage → Next.js/FastAPI POST /api/interpret → replaceable local AI provider → validated request/manual merge → POST /api/plans/generate → Task 26 generator → Task 27 ranking. Earlier task sections below describe historical checkpoints. TypeScript no longer interprets submitted text or executes planning in the app.

# Current architecture

Task 45 adds `backend/evidence.py`, pure adapters over existing Task 40–44 data.
`Source`, `Claim`, `EvidenceLabels` and `DisplayAttribution` separate original
provider identities/links/credits from field-level certainty and receipt times.
`venue_labels` covers canonical fields (including missing nested values);
`distinct_venue_labels` preserves Task 42 merged contributors; `route_labels`
labels estimates paired with the unchanged directional route contract;
`feasibility_labels` translates Task 44 outcomes without evaluating constraints.
Fictional-fixture and user-detail adapters preserve source distinctions. Existing
models, provider masks, endpoints and mock planner/UI are unchanged. Labels and
provider content stay in memory; no storage, new requests or Task 46 integration.
See [evidence labeling](docs/evidence-labeling.md) for states, attribution and
consumption rules. The following baseline and historical sections remain valid.

Source baseline: October 20, 2026. Next.js serves the existing React homepage, proxies raw text/manual controls, and displays results. FastAPI interprets requests through the Task 30 AI provider, validates/merges them in the Task 31 service, then generates and ranks itineraries using Tasks 26–27 and the shared fictional dataset.

```text
Homepage text + manual preferences
          |
Browser POST /api/interpret -> Next.js proxy -> FastAPI AI extraction
          |
Validated supported activities/constraints + manual overrides (or issues)
          |
Browser POST /api/plans/generate
          |
Next.js server proxy -> FastAPI validated OutingRequest
          |
Task 26 candidates -> Task 27 constraints, scheduling, ranking
          |
RankingResult -> display adapter -> existing cards or clear error
```

## Backend health boundary (Task 23)

`Browser or HTTP client -> Next.js GET /api/health -> FastAPI GET /health`

FastAPI runs locally through Uvicorn on `127.0.0.1:8000`. Next.js calls it server-side using `BACKEND_URL`, defaulting to that address; the variable is never sent to browser code. The homepage does not call the health endpoint; its planning POST does require backend availability. No CORS middleware is needed for this server-to-server call.

The Next.js route disables fetch/response caching, validates the expected status, and enforces a three-second timeout. Success returns `{"status":"ok","backend":"ok"}`; connection failures, timeouts, invalid JSON/status, and upstream HTTP errors return HTTP 503 `{"status":"error","backend":"unavailable"}` without exposing internal errors. Tests use local HTTP servers; Python's standard test library avoids extra backend test packages.

## Input to itinerary

1. `app/page.tsx` calls asynchronous `generateOuting`; an in-flight guard and disabled button prevent duplicate submissions.
2. `lib/planner.ts` resolves text/manual preferences with the unchanged `lib/request.ts` keyword/date parser. Unsupported wording or invalid values receive the existing explanations. Blank fields use recognized text or defaults: Baltimore, four people, unlimited budget/travel, balanced mode.
3. The Next.js proxy forwards structured JSON to FastAPI. `OutingRequest` validates the API input; Tasks 26–27 enforce exact event dates, capacity, ordered activities, budgets, simulated travel and scheduling.
4. Python preserves 10 AM ordinary starts, dinner no earlier than 5 PM, fixed events, travel and midnight finish. Missing hours remain unknown; ordinary suggestions are provisional. Costs and schedules are fictional.
5. Python ranks under the selected mode and returns at most three distinct confirmed/provisional options. The adapter preserves that order and all calculated fields; unknown values show “Unknown”. Failures show messages without a TypeScript fallback.

## Key files

| File | Responsibility |
| --- | --- |
| backend/ai/__init__.py | Vendor-independent interpretation contract, provider protocol, environment settings and factory |
| backend/ai/ollama.py | Ollama HTTP adapter, extraction prompt/examples, schema validation and safe errors |
| backend/ai/smoke.py | Opt-in real local model communication check; never run by ordinary tests |
| backend/test_ai.py | Mocked AI responses, configuration, failure handling and provider substitution |
| backend/models.py | Pydantic request, venue/event, final-plan and candidate contracts, scalar types, and integrity validation |
| backend/planner.py | Deterministic ordered Python candidate generation and lazy traversal (Task 26) |
| backend/ranking.py | Candidate evaluation, schedules, cost/travel adapters, normalized scores and distinct selection (Task 27) |
| backend/test_ranking.py | Hard limits, uncertainty, scheduling, scoring, distinct selection and generator integration |
| backend/test_planner.py | Generator completeness, identity, event timing, uncertainty, validation and lazy traversal tests |
| backend/test_models.py | Request/schedule/result tests, live TypeScript contract comparison, and FastAPI schema compatibility |
| backend/main.py | FastAPI health and validated planning POST |
| backend/test_api.py | Real HTTP API behavior, validation and unknown-data tests |
| app/api/plans/generate/route.ts | Uncached server-side planning proxy and failure handling |
| app/api/plans/generate/route.test.ts | Real Python/proxy/client integration and upstream failure tests |
| lib/planning-client.ts | Async planning request and ranking-to-card adapter |
| lib/planning-client.test.ts | Active interpretation, overrides, unknown formatting and client errors |
| lib/legacy/planner.ts | Retired engine for historical regression tests only |
| data/demo-plans.json | Fixed initial inspiration cards; never a fallback |
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
| lib/planner.ts | Input resolution/validation, request/card types and display formatting |
| lib/planner.test.ts | Historical TypeScript planner and parser regression tests |
| package.json | Dependencies and development/check commands |
| next.config.ts, tsconfig.json, eslint.config.mjs, postcss.config.mjs | Framework, TypeScript, lint, and stylesheet tooling |

React state holds requests, preferences, results, and expanded cards in memory. There is no runtime database persistence, browser persistence, account system, or cross-session history. Task 48 later adds an isolated hosted schema; see the current database section below. Icons use lucide-react; illustrations and fonts need no external media service.

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


## Task 28 — live Python planning boundary

`lib/planner.ts` retains the original parser orchestration, Baltimore calendar, exact-date handling, inferred people/budget, dinner flag, manual override precedence and input validation. `lib/request.ts` is unchanged. `resolveOuting` produces an `OutingPayload`; blank limits become JSON null, while zero stays zero. Requests use the existing Pydantic camelCase fields (`activities`, `location`, `people`, `date`, `budget`, `travel`, `cost`, `dinner`). Other Task 27 constraints retain their backend defaults and are not exposed as new controls.

The client POSTs resolved JSON to `/api/plans/generate`. Its Next.js route forwards that payload to the same FastAPI path using server-only `BACKEND_URL`, uncached, with a 10-second timeout. The browser uses a 15-second timeout. The existing health proxy is unchanged. No CORS or public backend URL is needed. FastAPI validates `OutingRequest`, calls `recommend_plans`, and validates its returned `RankingResult`; it adds no algorithm or fixture. The sync route lets FastAPI execute CPU work outside its async event loop.

HTTP 200 contains the unmodified ranking contract, including empty/infeasible outcomes and separate `plans` / `provisionalPlans`. Validation uses 422 (`invalid_request` or `unsupported_request`, message and field issues). Malformed JSON at Next.js returns 400; transport/upstream failure, timeout or malformed success returns 503. The browser clears generated cards on errors and never calls the legacy engine. An in-flight ref and disabled submit button prevent duplicate submissions and announce loading.

`adaptRanking` validates consumed response fields, combines confirmed then provisional options without re-ranking, and supplies presentation titles/themes. It maps `candidate.id` → card `id`, `stops[].venue` → card `venues`, `costPerPerson` → `price`, `groupCost` → group total, `totalTravel` → `travel`, `elapsedDuration` → `duration`, null date → “Any day”. Prices and per-leg travel use returned quotes, not UI calculations. Stops/venue provenance stay attached; null prices, durations, capacities, travel and times show “Unknown”. Constraint issue text is displayed, with `openingHours` humanized as “Opening hours”. Confirmed means only fits supplied fictional evidence; unknown hours produce provisional alternatives, not confirmed recommendations.

Python’s weighted ranking/diversity differs deliberately from the retired algorithm: all options follow the selected mode, rather than one pick per mode. Balanced can favor premium tiers. Confirmed options precede provisional ones. These Task 27 differences are exposed rather than replaced with legacy results. No hard constraint is relaxed.

`lib/legacy/planner.ts` is a regression reference imported only by historical tests; no application import exists. Its retained tests and cross-runtime fixture fingerprints do not test live execution; the new HTTP and real-Python frontend integration tests do. `data/demo-plans.json` contains fixed pre-submission inspiration cards to preserve the initial design; it is never a fallback for a submitted request. CSS, artwork and responsive layout remain unchanged. No dependencies were added.

## Standalone local AI boundary (Task 30)

`Python caller -> create_provider() -> AIProvider.interpret(text) -> Interpretation`

This path is not imported by FastAPI, the parser, candidate generator, ranker or frontend. No new endpoint exists. Ollama is the first and only implemented provider; a future provider implements the same one-method `Protocol` and is selected in the factory. No provider framework or extra dependency is needed. Model-specific HTTP messages, schema format, prompt/examples, context/output limits and generation options stay in `backend/ai/ollama.py`. Existing `backend/models.py` remains vendor-independent and unchanged.

`Interpretation` is a partial extraction with ordered activity phrases, nullable people, nullable numeric per-person budget, nullable exact date/location and stated preferences. All fields are required in the response; unspecified scalar values must be null. Activities are phrases, not resolved catalog IDs. It reuses existing vendor-independent scalar validation. The schema rejects extra fields, negative budgets, invalid dates and invalid group sizes. Pydantic verifies structure and ranges, not truthfulness or completeness.

Task 31 must resolve ambiguity, normalize supported activities, preserve negation/order, apply reference dates/defaults/manual overrides, and check semantic accuracy before constructing an `OutingRequest`. Task 30 supplies no conversion into the planning engine. Hosted providers can later use the same `Interpretation` contract without frontend or itinerary-optimization changes; none is implemented now.

`AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL` and `AI_TIMEOUT_SECONDS` are read when creating the provider. Settings are exported process environment values; Python does not auto-load Next.js `.env.local`. Calls use standard-library HTTP with a configurable socket timeout, non-streaming JSON schema output and local Pydantic validation. No automatic retries or model downloads occur. Requests bypass system HTTP proxies. Missing model/API (404), other HTTP failures, unavailable service, timeouts, malformed JSON, truncated/incomplete and schema-invalid replies raise `AIError` with a safe actionable message rather than accepting partial results. Real smoke commands are documented in README; ordinary tests mock the transport and can substitute another provider without a running model.

The selected default is `qwen3:4b` (tested `359d7dd4bcda`, Q4_K_M). Ollama owns downloaded weights outside the repository; Git stores only code/configuration examples and documentation. The adapter requests `think: false` (verified without thinking content), temperature 0, 4096 context, 512 output tokens and five-minute keep-alive. It keeps no conversation history between requests. Approximately 2.5 GB on disk / 3.2 GB loaded was observed on the M2 Mac. No model is pulled by the module or smoke command. Tests use `AISettings` overrides and a fake provider to verify replacement without machine-specific paths or model files.


## Task 31 — active AI interpretation pipeline (supersedes historical parser path above)

`Homepage raw text + manual strings → POST /api/interpret (Next.js) → POST /api/interpret (FastAPI) → AIProvider.interpret → Interpretation → grounding/normalization/manual merge → OutingRequest → POST /api/plans/generate proxy → existing Python generator/evaluator/ranker → existing cards`.

The interpretation endpoint returns `{interpretation, request, notes, issues}`. HTTP 200 can carry `request: null` with actionable issues, preserving partial extraction for later tasks without planning it. Invalid inputs return 422; unavailable/invalid/timed-out AI returns safe 503. The sync endpoint runs provider I/O outside the event loop. No keyword fallback or retry exists. Browser and proxy AI timeouts are 75/70 seconds around the provider's default 60; planning timeouts remain 15/10 seconds. BACKEND_URL stays server-only.

`backend/interpretation.py` accepts a replaceable provider, validates its output, translates exact activity aliases, grounds phrases in source order, checks known explicit occurrences/multiplicity for omission, and preserves common raw date expressions independently of the model. It rejects unsupported phrases as a whole and does not choose suggestions. Grounding core location/group values prevents model defaults becoming facts. Numeric/currency and time/date guards are deliberately conservative; finite checks cannot prove arbitrary-language completeness. Ambiguity/exclusions/alternatives are surfaced as issues rather than silently choosing. Unknown location/group requires text or manual values, avoiding OutingRequest's legacy defaults. Null budget/travel stays uncapped; zero stays zero. No relative-date resolver is called.

Task 30's one-method protocol remains unchanged. Interpretation adds nullable group budget/currency/travel caps/transport/cost/start/end and raw date/time expressions, suggested category IDs and uncertainties. Required original nullable fields remain intact. Additive fields have defaults for older provider implementations; that does not guarantee they support richer constraints. Vendor messages and options stay inside Ollama. The same Qwen3 4B model uses 8192 context and 1024 output tokens with thinking disabled to fit the expanded extraction/examples.

Manual nonblank fields override corresponding text fields. `costExplicit` tracks actual selection so initial Balanced does not erase text affordability/experience; clicking Balanced deliberately does. Reset clears explicitness. Manual per-person budget and text group budget remain independent caps. No activity override/confirmation UI is added. Preferences/suggestions/uncertainty remain distinct; venue tastes are unverified notes, not new ranking signals. Transport reaches the existing request, with an explicit note that mock routing is mode-independent.

Only one small planner extension is needed: optional `OutingRequest.dinnerStops` indexes scope the existing 5 PM dinner rule to the requested dinner occurrence. Omitted indexes retain legacy `dinner` behavior for existing callers. Repeated categories already work in Tasks 26–27 and require distinct record IDs unless revisits are explicit; no generator, scoring or selection algorithm was rewritten. The fixture, styles, artwork and card structure are preserved. The initial example omits a relative weekday so it remains actionable without implementing Task 32.

Tests cover the service, provider errors, manual precedence, repeated stops and meal timing, missing/unsupported/ambiguous requests and real HTTP wiring through a fake Ollama server into actual Python planning. Historical parser tests remain explicitly regression-only. `backend.ai.smoke_interpretation` is a separate opt-in eight-case actual Qwen test. A production browser check with actual Qwen verifies button submission, ordered cards, details and relative-date/manual behavior. See HANDOVER.md for evidence and limits.


## Focused results presentation correction after Task 31

`lib/results-presentation.ts` translates existing result text only at rendering time. A single live status announces a plain-language plan count. `ResultsInformation` consolidates the fictional-data disclosure and native, keyboard-operable About these estimates disclosure. Routine missing opening hours is secondary; all other plan issues and unknown price/travel/timing/capacity remain visible by the affected card, even with itinerary details closed. Failure reasons remain in the main empty state. Raw response messages, issues, provenance and all calculations remain unchanged. No backend, API contract or interpreter changes; Task 32 remains unstarted.


## Focused recommendation-card explanations after Task 31

`adaptRanking` reuses existing Python `score` and `components.quality`, plus returned costs/travel and venue identities, to feed `lib/recommendation-copy.ts`. It only writes card titles, labels and descriptions; no score, calculation, selection, order or API payload changes. Superlatives compare the displayed options, require known comparison values, and acknowledge ties. An all-equal cost/travel/quality pair is described by its actual venue or ordering difference; a single option or insufficient evidence gets factual neutral wording. The quality claim also requires supplied venue experience values, so the engine's zero placeholder for unknown quality does not become a factual quality comparison. No AI call or parsing of technical explanation prose is added. Sample-data disclosures and material warnings remain separate from these short choice explanations.


The final headline refinement uses the same evidence-backed explanation classification for short titles, replacing position-based slogans in generated results. Joint winners stay explicitly tied; different venue orders receive Same Places, New Order, and tied matches with different prices/travel can state those actual differences. Detailed descriptions, badges and all calculations are unchanged. Comparisons remain limited to the displayed plans; incomplete evidence receives neutral wording.

## Task 32 — deterministic outing calendar resolution

The active Task 31 pipeline now calls `backend/date_resolution.py` after choosing the effective location/manual Date and before constructing `OutingRequest`. This supersedes earlier unresolved-date descriptions. The AI provider interface and partial Pydantic schema stay compatible: Qwen is instructed to leave `date`, `start_time` and `end_time` null and copy original date/time phrases. Legacy providers' calculated fields are never used for arithmetic. The response's `interpretation` retains extraction/phrases; `request.date/startTime/endTime` are the separate resolved values. Source guards preserve supported phrases even when the model omits them. No AI activity fallback is introduced.

`resolve_datetime` uses only standard-library `datetime`, `timedelta`, regex and `zoneinfo`, plus the planner's existing Baltimore coverage check. It accepts an aware injected reference clock for deterministic tests; production reads the current UTC instant and converts it to outing-local time. Baltimore, Baltimore MD/Maryland aliases resolve to `America/New_York` (system IANA daylight-saving rules). Other/unknown locations use **UTC as a disclosed fallback reference**, never a claim about that location's timezone. Unknown location/group still requires clarification and the catalog still rejects unsupported cities. No browser/device timezone, geocoding service, or invented precise timezone is used. Explicit timezone abbreviations/offsets require rephrasing in outing-local time.

Calendar semantics:

- Today/tonight use the local reference date; tomorrow adds one calendar day, independent of 23/25-hour DST days. Tomorrow evening and weekday evening/night preserve that day.
- Bare/“this” weekday means the next occurrence **including today**. “Next” weekday means that weekday in the **next Monday–Sunday calendar week**. On Friday, this Friday is today and next Friday is seven days later; on Saturday, this Friday and next Friday both refer to the coming Friday. All seven weekday names use this rule.
- This/next weekend is recognized but needs Saturday, Sunday or a manual exact Date. No silent single-day choice. Saturday night means the upcoming Saturday, including today, with the evening default below; an explicit overnight window is refused.
- Full ISO dates and all English full month names/standard abbreviations (including Sep/Sept and optional periods) work in month-first or day-first order, including ordinal suffixes and “7 of November 2026”. For a yearless named month/day, use the reference date’s local calendar year only when that valid date is today or later. A passed month/day asks for a year; February 29 in a non-leap year asks for a leap year. Invalid dates and conflicting expressions need correction. Explicit years are respected and past dates rejected, never rolled forward or replaced by fixture dates. A nonblank manual Date wins over natural-language date ambiguity/conflicts, while independent time constraints remain in force.

Clock semantics (planner resolution is whole minutes):

- `6 PM`, `18:00`, noon = 720, midnight as a start = 0. Midnight as an end = 1440, the end of the selected day. `between 6 and 9 PM` inherits PM for the bare first hour; `from 18:00 to 21:00`, dash ranges, `at`, `start(s)/starting`, `end(s)/ending`, `until` and `by` are supported. Unqualified hours such as `at 7` need AM/PM. Explicit 24-hour clocks retain their values.
- `after 6 PM` means earliest 18:01 and `before 10 PM` means latest 21:59, strict bounds at minute precision. `at`, `between`, `from/to`, `until` and `by` are inclusive planner boundaries. Multiple bounds intersect without discarding constraints; incompatible starts/windows need clarification. These are overall outing bounds, not individual-stop appointments.
- Without explicit starts, evening/night/tonight defaults to 18:00 through midnight, disclosed in notes. Explicit starts take precedence over the day-part default. Ordinary no-time requests retain 10:00–24:00; an end-only window earlier than 10:00 permits a midnight earliest start. Today without an explicit/day-part start uses no earlier than the current local minute (rounded up), disclosed. A requested start already past today, past date, expired window, or past evening default returns clarification; nothing moves automatically to tomorrow.
- 22:00–01:00 is identified as overnight and refused with a single-day explanation. Other reversed/empty windows report contradictory constraints. Explicit following-day/overnight wording is refused. The planner's midnight cutoff and all feasibility/ranking rules are unchanged.
- On a resolved date, local times that do not exist or occur twice at DST changes require an unambiguous time. Windows crossing an offset change require a window wholly before/after it because the existing planner computes wall-clock durations. No artificial fold or elapsed-time equivalence is invented.

Unsupported wording (including morning/afternoon without supported explicit treatment and broader relative phrases) can require an exact Date and overall clock window. Stop-specific time wording in multi-stop requests requires clarification. Finite phrase guards and AI extraction do not guarantee arbitrary-language completeness. Clarification uses the existing issues/empty-state path; there is no new UI flow, session state, parser framework, dependency or infrastructure.

Fixed-clock tests cover local/UTC boundaries, month/year/leap transitions, all weekday semantics, weekend boundaries, conflicting/past/overnight windows, noon/midnight and DST folds/gaps/crossing windows. Interpreter-to-engine tests and actual HTTP proxy/client tests exercise source omission of tomorrow, dates/time windows and manual precedence. `backend.ai.smoke_dates` separately checks original Qwen phrase fidelity and deterministic/planner outcomes; it never downloads a model.

## Natural-language-only correction after Task 32

The reproduced live failure was a stale FastAPI runtime on port 8000: both the Next.js proxy and direct backend returned the old Task 31 “relative dates are not resolved yet” issue, while a fresh process importing the current checkout resolved the identical full request to October 22, 2026 with location/group/budget/travel/cost intact. The old process was stopped and the current backend restarted using the existing reload-enabled development command. No resolver or AI arithmetic workaround was added.

The separate frontend display gap is fixed in `lib/preferences.ts` and `app/page.tsx`. State holds displayed `values` and per-field `manual` markers. `manualPreferences` submits only deliberate nonblank edits (including zero), plus deliberately selected cost/`costExplicit`; auto-populated values never become manual input. Clear releases a field; reset clears all markers/values. Functional state updates preserve edits made while a request is pending.

`generateOuting` now accepts an optional client-only `onInterpreted` callback in its existing context argument. After a successful interpretation with no issues, it validates/maps the existing effective `request` fields to controls and invokes the callback before the unchanged planning POST. No API request/response schema, provider protocol or planner contract changes. Date display uses Python’s resolved calendar value; null optional caps/date remain blank, with the existing Balanced UI default. There is one model interpretation per submit, none per keystroke or preference display. Issues/provider failures do not populate guessed values and never call a fallback. Successful interpretation may remain visible even if the subsequent planner call fails; it is explicitly labeled as values from the last interpreted request.

Tests cover state transitions, zero/Balanced overrides, release/reset, pending edits, failure boundaries, actual HTTP interpretation-to-engine/card data and fixed-clock complete requests. Live development and clean production browser checks additionally verify untouched-panel text submission, repeated stops, tomorrow, auto display, replacement by new text, deliberate overrides, genuinely missing essentials and backend failure/recovery. Styles, recommendation design, fixture and ranking are unchanged.

## Task 33 — temporary clarification state

The existing `/api/interpret` input gains optional `pending` and `answers` fields. Python’s `PendingClarification` contains the unchanged original text, grounded `Interpretation`, separate typed answers and an aware reference clock. The response adds `questions` (field, natural question, essential/ambiguous kind), `pending` and `unsupported` explanations; existing `issues`, notes and resolved request remain compatible. All state is Pydantic-validated on every submission. There is no server session store, database, authentication, new endpoint or conversation framework.

The homepage holds this envelope in React memory. A new request calls the existing AI provider once. A continuation copies and revalidates the saved extraction, applies simple answers deterministically, and uses the existing Task 32 date resolver and `OutingRequest` validation. The initial clock anchors relative-date meaning across follow-ups; the current clock rechecks past dates/starts before planning. Answered locations recompute local calendar interpretation from that original reference. Date corrections replace only date wording, preserving independent clock bounds; overall time corrections require an explicit user answer. An unclear activity occurrence is replaced in its original position while known stops/repeats remain. Alternative/no-activity requests ask for an explicit ordered stop list.

Required location/group drive catalog matching, capacity and group cost. Exact dates are required for every finalized outing, and ambiguous supplied date/time/activity constraints need clarification. Missing budget, travel caps and optional preferences do not. Original unsupported requirements produce explanations rather than clarification loops. Invalid answers retain the original state for correction; valid-but-infeasible requests proceed to the unchanged ranking explanation and clear clarification state.

Precedence remains deliberate nonblank manual setting → explicit follow-up correction → original interpretation. Answers stay separate from `ManualPreferences`; displayed inferred values still use Task 32’s manual markers. All explicit original money/travel/experience fields remain in the extraction and continue through existing grounding/validation. The UI sends only genuine manual controls on each continuation.

`PlanningSession` provides a single active AbortController and identity guard: duplicate submits are ignored; cancellation, editing text and Try an example abort and invalidate old results. The client checks cancellation before sending a plan. A valid extraction is retained through planner failure, allowing a model-free retry. Successful planning (including honest infeasibility) clears pending state. Provider/network failures keep the original text; failures during continuation keep saved state and answers. No automatic retry occurs. Reload/close intentionally discards temporary state. The small follow-up panel reuses existing preference/button styles; cards, artwork, fixture and scheduling/ranking engines are unchanged.

The answer grammar is deliberately bounded: simple cities, numeric/one–twenty group sizes, catalog activity aliases and Task 32 dates/clock windows. Complex corrections and unsupported requirements can require editing the original text. This is not a general chat interface or guarantee of arbitrary-language understanding.

Task 33 location wording correction: missing/uncertain-location prompts and empty location placeholders are city-neutral. Clarification accepts a supplied city directly and passes it unchanged to the existing planner; catalog coverage is checked there rather than asking users to replace their city during clarification. The fictional catalog still covers Baltimore only, so other cities receive the existing unsupported-location result. Missing locations remain unknown; no city/device-location default is introduced.

## Task 33 follow-up — dated finalization and measured latency

The current product policy supersedes earlier flexible-day publication descriptions. `PlanningRequest(OutingRequest)` requires a valid non-null calendar date at the public planning endpoint and in successful interpretation results. The original candidate-analysis `OutingRequest` remains compatible with historical/internal tests; it cannot publish undated options. `recommend_plans` checks for a missing date before generating candidates; `rank_candidates` checks before evaluating candidates; `RankingResult` rejects selected options without a request date. The card adapter rejects null/empty/“Any day” candidate dates rather than fabricating a display value. Preview demo cards remain clearly separate from generated itineraries.

A missing date asks “What day are you planning to go?” for ordinary venues and events alike. Existing Task 32 resolution handles original/manual dates and date answers, preserving timezone, this/next semantics, day-parts, past/invalid/DST checks and independent time constraints. No date is guessed; overall start time remains optional with existing disclosed defaults. The existing pending-state flow collects all missing essentials together, keeps manual precedence and avoids reinterpreting answers or generating candidates during clarification.

Temporary measurement wrappers around real Ollama, Python and production Next.js confirmed that AI prompt/decode work dominates. The adapter now supplies property definitions/types in Ollama’s existing structured `format` field, rather than repeating it in the system message. Examples/instructions retain nullable core/scalar fields and every stated value; absent optional phrase arrays and unused AI clock fields may be omitted and restored by existing Pydantic defaults. Explicit budget-currency and total/per-leg guidance remains. Normalized provider output, context/output limits, timeouts, temperature/thinking settings and replaceable provider interface are unchanged. The Ollama format requires every scalar planning-constraint field to be emitted (nullable when absent); only empty optional phrase arrays and unused AI clocks can be omitted. This ensures both group/per-person caps, currency, travel, mode and priority are visited, without turning optional user constraints into questions. After numeric grounding, an unqualified explicit $ amount can deterministically restore missing USD under the existing documented dollar policy; explicitly different currencies are never converted. No cache, heuristic parser, candidate pruning change, background model process, persistent telemetry or timing middleware was introduced into the product.

Sequential local measurements use one model-unloaded and two warm runs per initial scenario; exact final timings and evidence are recorded in HANDOVER.md and the delivered performance report. Date/validation, candidate generation and ranking remain milliseconds, and follow-ups use no AI. Cold residency and generation still impose visible latency; no arbitrary early timeout or semantic AI bypass was added. These are finite measurements on this computer, not guarantees of speed or language accuracy. The date requirement does not establish real catalog availability.

## Task 34 — interpretation trust boundary

The authoritative conversion remains `interpret_request`: provider-independent `Interpretation` → existing source/date/clarification checks → one effective `PlanningRequest`. Providers do not participate in feasibility calculations. No second interpreter, validation service or fallback parser was added.

Inspection before implementation found these existing guarantees:

| Layer | Existing guarantee | Task 34 addition |
| --- | --- | --- |
| Pydantic extraction/planner contracts | Unknown fields forbidden; numeric bounds/types, finite values, enums, dates, ordered stop lists | Strict bounded phrase arrays/strings, revalidation of provider instances, duplicate JSON-key rejection |
| Interpretation service | Ground activity order/repeats, reject unsupported phrases, missing group/location, currency checks, manual precedence | Check independent budget scope/amount, total/per-leg travel evidence/units, minimum spending, group/location conflicts, invented/omitted explicit modes |
| Task 32 resolver | Source date/time recovery, deterministic relative dates, intersections, past/invalid/ambiguous dates, DST/overnight checks | Reuse unchanged; public planning endpoint also checks that date/start/window have not expired |
| Task 33 clarification | Separate original extraction/answers/reference clock; targeted essentials; no second AI call | Preserve pending extraction/answers when semantic validation still blocks a continuation |
| Frontend | Only successful effective requests synchronize preferences; automatic values never become manual overrides; failures do not call planner | Additional HTTP integration and pending-failure regressions; no UI changes |
| Python feasibility engine | Capacity, cost, travel, order, schedules and ranking against supplied fictional evidence | Unchanged |

The old loose budget check (any matching number anywhere in the request) is replaced, rather than retained alongside the new budget evidence check. Evidence guards compare common explicit money amounts and per-person/group scope, and numeric minutes/hours with total/per-leg scope. Multiple maximum caps of the same scope require the tightest cap; independent group/per-person and total/per-leg caps remain independent. Zero is never missing. Manual per-person/total-travel overrides do not erase text group/per-leg caps. Explicit non-USD evidence cannot be labelled USD. Unsupported travel distance/units, minimum spending and common mandatory accessibility/dietary requirements block with an explanation rather than a fabricated conversion or feasibility claim.

Malformed/unknown structured fields and provider failures use the existing safe 503 response, without raw JSON or schema exceptions. Valid structure with uncertain essentials uses existing questions; conflicting/unsupported numeric requirements explain how to edit the original request or use existing controls. No retry or additional AI call was introduced. Unrecognized wording is not exhaustively validated: source guards cover bounded forms, aliases and common units; unusual valid wording can need rephrasing. Optional venue qualities remain explicitly unverified. These checks do not establish real hours, tickets, accessibility, diets, availability or routes, or infer missing event showtimes.

`backend.ai.smoke_validation` is opt-in actual-model acceptance plus 100 deterministic validation samples per request. Ordinary automated suites use fake model outputs and real local HTTP boundaries, without requiring Ollama.

Task 34's Ollama schema projection excludes unused AI clock keys (the shared contract still accepts them for other providers and saved sessions). Python defaults restore nulls; only Task 32 calculates clocks. Compact example serialization reduces prompt work while retaining every scalar constraint. Exact grounded labels such as “best experience” can clear a provider's bare duplicate uncertainty only when the extracted mode matches; actual questions/conflicts continue to block. Missing-optional uncertainty suppression now requires absence wording, preventing a cost conflict mentioning “budget” from being discarded as a missing optional numeric cap.

Provider uncertainty prose is classified internally but never displayed verbatim: the website receives curated messages for date, time, group, city, activities, money/preferences, travel or an unknown requirement. Structured extraction/pending state retains the original bounded evidence for revalidation.


## Task 35 — editable effective outing summary

`generateOuting` exposes `onValidated` with the same `extraction.request` sent to `/api/plans/generate`, plus the existing pending envelope and display-only explicit-time/cost metadata. The homepage retains this validated snapshot for summary and deterministic continuation after successful planning. It is not a second preference store: summary fields cannot be independently edited; editable scalar values/manual markers remain exclusively in `PreferenceState`, and activity corrections reuse `ClarificationAnswers.activities`.

`OutingSummary` renders a definition list, resolved dates, supported hard caps and original dinner occurrences. Unspecified optional caps and implicit experience preferences are omitted from the compact summary; inferred scheduling defaults are not shown as user-selected times. Edit details opens and focuses the existing preferences panel. The ordered comma-separated activity field uses validated activities/dinner indices for display until deliberately edited; exact repeated occurrences are retained. A blank sequence is submitted as an explicit empty-list correction for server rejection, since the existing continuation protocol treats blank answers as unanswered.

Regeneration sends only deliberate scalar overrides plus the original extraction/answers/reference clock to the existing interpretation endpoint. Task 33 deterministic continuation applies corrections, Task 34 revalidates source/constraints, Task 32 resolves/rechecks dates, and the existing planning endpoint rechecks publication dates before ranking. No extra AI call, endpoint or dependency is introduced. Successful responses replace the validated snapshot and synchronize controls without changing manual markers. Failures keep correction/retry context. Displaying/editing fields has no network side effect.

Any edit cancels the active `PlanningSession` and clears cards immediately. Late responses remain guarded by submission identity. New text clears completed context, activity answers and automatic display values while preserving deliberate manual settings. Reset clears manual settings and completed context; pending clarification keeps its original details. Recommendations remain absent after invalid edits, stale work or service failure. The summary hides its previous detail list while dirty and asks for regeneration. Existing fictional-data cards/disclosures, engines, dataset and one-click initial flow remain intact.

Trailing spelled-out party counts such as “for two.” are accepted only as grounding evidence matching a provider-supplied count; conflicting counts still use existing clarification. This narrow acceptance correction does not infer missing group sizes or introduce a fallback parser. See HANDOVER.md for automated/browser evidence and viewport limits.


Task 35 UI refinement: the existing `preferencesOpen` flag still starts false. Only the identity-guarded `onComplete` callback (after a valid planning response, including honest infeasibility) now collapses it. Interpretation/validation failures, service failures, pending questions and ordinary edits never close it. Edit details uses the existing expand-and-focus action; clarification remains a separate visible panel. No extra editor or preference state was added. Summary spacing is tighter and absent optional fields are omitted, while explicit zero caps, deliberate Balanced and supplied additional hard constraints remain visible.

`OutingDateField` preserves the native date input and ISO `YYYY-MM-DD` value. Numeric day/month presentation is controlled by browser locale; the observed `07/11/2026` corresponds to the same November 7 value used by Python. A readable selected-date description uses the same formatter as the summary and is linked with `aria-describedby`; empty dates explain browser formatting. Date parsing, timezone resolution, API payloads and validation are unchanged.


## Task 36 — focused reliability corrections

Party-size grounding and conflict detection share `GROUP_EVIDENCE`, including numeric/spelled “for four” before common location/date/constraint clauses and punctuation. This validates a model-supplied count only; it does not infer missing counts or treat duration/money numbers as people. Conflicting source counts remain clarification cases.

Recognized minimum spending remains unsupported and blocking. Its concrete explanation supersedes competing model budget uncertainties and amount/scope diagnostics; it never selects a budget interpretation. Maximum-only validation and independent constraints are unchanged. Ungrounded model activity strings receive fixed user-facing errors/questions instead of echoed provider text. Genuine source activity phrases remain readable. The provider prompt, public contracts, continuation state, manual provenance, date resolver, planning engines and dependencies are unchanged.

`backend.ai.smoke_reliability` adds an opt-in bounded actual-Qwen acceptance/timing matrix; normal tests remain deterministic. Temporary request-count/timing wrappers used during verification live outside the repository. See HANDOVER for test results, cold/warm methodology, browser verification and retained fictional-data limitations.


## Focused date correction after Task 36

The existing resolver emits typed `CalendarIssue` reasons alongside compatible issue messages. `ClarificationQuestion` adds optional `reason`/`helpText`; the existing field component displays that curated guidance with an accessible description and a year/weekend-specific placeholder. Missing day, passed yearless month/day, explicit past date, invalid calendar date, weekend ambiguity and time problems each produce their own question. Interpretation no longer classifies resolver failures by matching English error text. Calendar-source resolution, rather than model uncertainty about a missing year, determines whether a supported date is clear; other semantic/source validation remains active.

A four-digit date answer can replace the year of one unambiguous named month/day from the previous date answer or original request. It is expanded inside the existing separate clarification answers, preserving original text/extraction, calendar reference and independent constraints. Several different dates or a year without month/day context cannot be resolved this way. Every continuation is revalidated and still needs a valid future/today date before publication. Manual ISO dates retain priority, and expiry/timezone/DST checks remain in force. No extra AI call, parser dependency, endpoint, preference store, planner or ranking change is added.


## Task 39 — prepared external provider budget (no live integration)

`backend/provider_budget.py` provides immutable strict `ProviderSettings`, a thread-safe process `ProviderBudget`, per-outing reservations and safe `ProviderLimitError` explanations. FastAPI constructs one process budget at import/startup; only the explicit `VENUE_DATA_MODE=mock` (also default) is valid. `require_live_provider()` always refuses live use. No Google client, external provider factory or frontend switch exists.

Future adapters must check the live gate, use this shared session and one outing budget across search/details/routing, check candidates before routing and reserve every exact attempt before I/O. Failed attempts retain counts/identity; duplicates cannot retry for free. The lock atomically enforces process concurrency/session totals and outing request/search/matrix totals, releasing concurrency in `finally`. No automatic retries or persistent cache. Reset/reload/multi-worker limitations and exact ceilings are documented in [billing safeguards](docs/billing-safeguards.md).

Mock `_pools()` still loads shared fictional fixtures and enumerates all combinations unchanged. Future search belongs before that combination stage; routes should be bounded/reused adjacent-candidate matrices before ranking, never network calls inside evaluation for every itinerary. This is a future integration requirement, not Task 40 implementation. No new dependency or service.

## Task 40 — isolated development venue discovery

`backend.discover_places` (explicit local command) → `backend.places` request/query/geographic checks → existing `OutingBudget.reserve("search", exact_request_hash)` → `backend.places_transport` protected local impersonated ADC → one Places Text Search POST → bounded `DiscoveryResult`. The fixed mask requests IDs, names, addresses, coordinates, geographic address components and attributions (Text Search Pro). No new FastAPI route or frontend call; the existing `main.provider_budget`, mock loader/planner/ranking and normal startup remain unchanged. The command owns its own process budget; reuse one session/outing when calling the adapter for multiple activities.

`DiscoveryRequest` deliberately does not inherit Baltimore-defaulted `OutingRequest`. Destination is explicit and overrides optional current coordinates. `SearchArea` supports names, coordinates and bounded supplied radii; no location yields validation failure. Name-only queries use a valid nonlocal bias overridden by Google's explicit geographic query handling, avoiding default server-IP bias; results must match geographic address components. Coordinate bias is checked against returned coordinates when a radius is supplied. Optional start/address and independent travel inputs are interface-only and never sent as search coordinates or evaluated for feasibility. Candidate coordinates remain available for later clustering without any routing or ranking implementation.

`WHERETO_PLACES_DEV=1` gates only discovery, with checks in the adapter and transport. `VENUE_DATA_MODE` still accepts only mock, and the generic live/route lock remains unconditional. The official authentication library and plain requests transport use backend-only short-lived tokens, fixed quota attribution to `where-to-512422`, zero Places retries/redirects and safe errors. Existing accounting/candidate/concurrency ceilings remain unchanged; authentication/data failures consume reservations. No result cache/persistent content or automatic refill/pagination.

Full location semantics, conservative matching limits, fixed mask/SKU, privacy/provider display obligations, exact live-request ledger and development command are in [docs/venue-discovery.md](docs/venue-discovery.md). Task 41 normalization and Tasks 42–46 relevance/routes/feasibility/labeling/full planner integration are deferred.

## Task 41 — canonical physical venue facts

`Google Place JSON / Task 40 DiscoveryResult → pure venue_normalization functions → VenueFacts` (in memory only). The normalizer is independent of field masks, budget/authentication/transport and the planner. It never performs I/O. `normalize_google_place` also accepts a partial response plus an existing same-ID Google record for optional later enrichment; it validates both, preserves unknown/missing values, keeps field receipt times/credits, and ignores older updates. The batch helper isolates invalid records, retaining input order and duplicates. No new real-data endpoint, Details adapter, cache, routing, ranking, deduplication or scheduling logic.

`backend/venue_models.py` defines provider-neutral `VenueFacts`, typed attributions, coordinates, separate regular/current opening hours with dated/weekly/truncated points, IANA timezone/version plus independent UTC offset, and nullable ratings/counts/HTTP links/price indicators. Both it and existing planner `Venue` share `VenueIdentity` in `models.py`; Task 40 also reuses the coordinate model. `VenueFacts.id` is the untouched provider ID, scoped by `provider`; `name` is human-readable. Existing `Venue`/`ScheduledEvent` are planner/session contracts, not alternate physical-place schemas. Google buildings cannot satisfy dated event records without a separate actual session source. No mock `experience`, USD/person cost, duration, opening windows or availability is inferred from Google ratings/hours/prices.

The Task 40 DTO/field mask is unchanged; `normalize_discovery_candidates` deliberately bridges that minimal transport shape into the canonical record. Optional Enterprise fields use synthetic tests through the raw Place normalizer only. Future integration must explicitly handle unknowns and source licensing; nothing activates real discovery in the website. Full field mapping, validation decisions, partial-update observation semantics, pricing tiers, future bounded Details interface and storage/display restrictions are in [venue discovery](docs/venue-discovery.md#task-41-canonical-venue-facts--october-24-2026). Tasks 42–46 remain deferred.

## Task 42 — offline candidate quality in development discovery

`PlacesDiscovery.discover / discover_many` → unchanged budgeted transport → `parse_response` with shared pure `venue_geography.geographic_reason` → Task 41 canonical normalization → pure `venue_quality.assess_candidates` → distinct minimal discovery DTOs plus in-memory `DistinctVenue` groups. `discover_many` requires one effective destination area and explicitly supplied bounded searches, with one existing outing budget; no hidden lookups, query expansion or retained cache. Single-search behavior uses the same path. No planner/API/frontend/routing integration.

`DistinctVenue` holds merged `VenueFacts`, all original source facts/IDs, a sorted requested-activity list and per-association strong/uncertain/mismatch evidence decisions (mismatching associations are removed). The canonical representative activity is the first retained category; consumers must use the full association list. Group by original provider/Place ID first; different IDs need pairwise exact name/address/close-coordinate/venue-URL corroboration. Merge known optional fields/credits deterministically before evaluating activity evidence. Preserve first source occurrence order, rather than adding ranking. Safe reason counts and groups are excluded from normal result serialization; the explicit development CLI shows only counts/reason codes. No provider payload or precise-user-coordinate logging.

Shared geometry preserves supplied radius checks and destination precedence, with county-only evidence no longer accepted as proof of a same-named city. Components are evidence, not polygon boundaries. Optional `primaryType` is now supported by normalization when supplied offline; no API field is added. The six-field mask, auth, limits and disabled defaults are unchanged. All 29 category rules, ambiguity protections, merge policy, diagnostic semantics and limitations are in [venue discovery](docs/venue-discovery.md#task-42-deduplication-and-relevance--october-24-2026). Task 43 routes remain unimplemented.

## Task 43 — isolated backend route calculation

`RouteCalculator` protocol / `RouteRequest` → pure directed adjacent-group pair union (`plan_matrices`) → minimal rectangular matrices → shared `OutingBudget.reserve_matrices` whole-plan admission → `routes_transport.compute_matrix` → protected existing ADC impersonation → fixed Compute Route Matrix POST → index-associated `RouteLeg`s. There is no connection to the existing planner, ranker, API endpoints or frontend.

`backend/routes.py` owns validated provider-independent inputs/results and the Google adapter. Each point has one stable ID plus coordinates or an original Place ID; the canonical Google-facts bridge preserves original IDs and rejects fictional evidence. Groups retain requested activity order. Optional `AuthorizedStart` must be explicitly supplied/authorized and has no destination-area fallback. Request limits/time constraints remain outside this calculator; full feasibility is Task 44.

Only needed consecutive-group pairs are computed, with optional start → first venues, no return-home request. Repeated pairs and identical provider waypoints reuse calculated metrics while preserving every caller ID. Same stable venue/Place ID is a locally labeled zero transition, distinct from Google success; equal coordinates alone do not establish venue identity. Origins sharing identical needed destination sets form matrices without unneeded cells. `RouteResult` contains one leg per distinct logical directed pair plus conservative reserved element/request counts. See [full contracts, default-scalar handling and failure semantics](docs/route-calculator.md).

`backend/provider_budget.py` now supports atomic batch reservation before authentication/I/O, retaining all planned counts/identities if a failure stops work early. Existing single-request callers delegate to the same accounting path. A session-wide rolling 60-elements/minute check mirrors the existing cloud rate quota; all previous configured ceilings remain unchanged. Reservation holds the existing single external-request slot for the sequential batch. A rejected batch reserves nothing. No queue, automatic retry, refill, candidate relaxation, persistent budget/cache or distributed quota ledger.

`backend/routes_transport.py` uses the existing protected ADC helper with fixed quota project, rebuilt strict basic-only request payload, zero adapter retries, no redirects and bounded timeouts. Both adapter and transport require the separate disabled-by-default `WHERETO_ROUTES_DEV=1` local gate before authentication. `VENUE_DATA_MODE` remains mock-only. Driving explicitly uses TRAFFIC_UNAWARE, walking omits routingPreference. The six-field response mask is `originIndex,destinationIndex,status,condition,distanceMeters,duration`; no traffic, tolls, premium features or polylines. No new dependency or endpoint. [Usage, Essentials pricing, privacy, errors and live-verification limitations](docs/route-calculator.md). The isolated Task 44 evaluator is described below.

## Task 44 — pure feasibility evaluation

Caller-supplied canonical `VenueFacts` + ordered aware stop intervals + `RouteLeg` evidence + explicit limits/clock → `backend.feasibility.evaluate_feasibility(FeasibilityInput)` → structured `FeasibilityResult`. `filter_feasible_candidates` stably partitions by feasible/infeasible/unverified state and retains provisional results. No transport/authentication call, planner/API/UI integration, ranking or persistence exists. Current Task 27 mock generation/evaluation remains untouched; its fictional quotes and single-day windows are unsuitable for provider dates/timezones. Shared canonical contracts and event categories are reused.

Directed/mode-specific legs enforce exact seconds/nanos against decimal minute caps, unreachable routes, total known inter-stop lower bounds and available UTC transfer gaps. The route parser retains optional exact `duration_nanoseconds` alongside compatible prior metrics. An optional `AuthorizedStart` adds only start → first stop, with its own cap; absent start creates no requirement and no inferred location.

Complete dated current-hours snapshots use their specific receipt timestamp, trusted venue-local `hours_request_date` supplied alongside the snapshot, seven-day applicability and IANA timezone. All coverage comparisons are in UTC. Overnight intervals are supported; ambiguous/nonexistent DST boundaries, truncated/undated hours, stale/missing receipt/request context, absent timezone and regular-only hours remain unverified. Regular weekly hours cannot establish holiday exceptions. Movie/event buildings always retain unknown session availability. Known conflicts dominate all unknowns. The result checks only travel/hours/session uncertainty, not every possible planning constraint. [Contracts, exact thresholds, applicability policy, supported evidence and limits](docs/feasibility.md). Tasks 45–46 remain unimplemented.


## Task 46 — real-data planner integration (current)

The existing Next.js → interpretation → validated Python request → candidate/evaluation/ranking → card pipeline now has a backend-owned local real mode. `backend/real_planning.py` orchestrates Tasks 40–45 and reuses `planner._walk`, `ranking.evaluate_candidate`, `score_candidates` and `_select`. The provider physical-place bridge carries original IDs, addresses, Task 45 evidence/credits and documented Maps links without fabricating event sessions. Dinner requests use a dinner-specific restaurant query; repeated categories reuse their search. No fictional price or travel adapter runs in real mode.

`PlannerInput` adds excluded/transient current/start coordinates, optional coordinate radius and a separate first-stop cap. Destination wins over current location. `maxFirstLegTravel` also survives interpretation as a grounded request constraint; mock mode refuses unsupported origin/radius limits instead of discarding them. Real explicit revisits are refused, while repeated categories remain ordered distinct stops. First-leg evidence is separate from inter-stop totals. Task 44 enforces exact route seconds; the shared minute scheduler uses conservative lower bounds for early impossibility checks and displayed route minutes round upward. Unknown durations leave all real visit times null.

The process owns one `ProviderBudget`; later Details calls share the original outing's reservation budget. `GET /api/planning-mode` exposes safe mode metadata. `POST /api/venues/details` requires a short-lived random outing capability plus one of its original Google IDs; the backend retains only IDs/budget/attempt markers, never a provider-content cache. Six on-demand Enterprise Details attempts/outing fit inside the unchanged 20-attempt outing and 50-attempt process ceilings. Browser session promises coalesce duplicate active-display lookups, with no persistent storage. Both proxies are no-store.

The website keeps its cards, preferences, summary/edit and clarification controls. It adds one optional location disclosure and compact per-venue contact panels, safe links, Google Maps/third-party attribution and mode-aware disclosures. Real responses are provisional while prices, hours, duration/capacity, sessions and reservations remain unknown. Backend mode and a separate local-only opt-in are required; production/known hosting environments refuse real mode. Mock is the unchanged safe default; no fallback crosses modes. Public deployment is outside this task.

[Complete flow, calendar/location limits, contact protocol, pricing, request limits and verification](docs/real-planning.md). Historical sections above describe their task checkpoints.

### Task 46 stabilization

The calendar resolver treats weekday-qualified explicit dates as single evidence phrases and validates weekday agreement, including redundant AI-fragment handling and existing year/manual correction rules. `RankingResult.alternativeBatches` contains at most two batches of three additional real provisional options, validated against the same request and global full-itinerary uniqueness. They are selected from the already evaluated/routed pool; active-page consumption uses no new backend request. Contact capabilities include these displayed alternatives under unchanged budgets. Diversity adapts to the number of positions with eligible alternatives, retaining shared fixed stops in small pools.

`PlannerInput.manualStartingPlace` is transient, excluded from public serialization and refused before provider I/O until resolution is implemented. The normal interface accepts natural starting-place text instead of coordinates. Geocoding API enablement/authentication/quota checks and a precision-aware confirmation flow are deferred proposals, not an enabled transport. Real cards describe the available travel/venue-variety evidence and use local activity icons with explicit illustration labeling. See docs/real-planning.md.


### Submission feedback correction after Task 46

Complete interpretation continuations are retained via `onValidated` for model-free regeneration/retry; `onClarification` publishes actual questions only. Browser loading has presentation priority over retained questions/errors. A client-created `PlannerResult.requestFailed` flag distinguishes failed requests from clarification and valid empty results; it is not a new FastAPI/provider contract or a feasibility status. `PlanningFeedback` provides clean loading/real-error/manual-Retry states, while existing `PlanningSession` guards still own cancellation and stale-response protection. No automatic retries or provider changes.

## October 26 — consolidated Task 46 interfaces

- `backend/routing_shortlist.py` ranks candidates by strong relevance and forward/backward geographic path cost across the full sequence. `routes.RouteRequest.required_pairs` restricts the existing exact rectangular matrix planner to missing directed pairs. Pairs must belong to selected adjacent transitions/authorized first legs. Geography never supplies travel minutes.
- `real_planning.py` still bridges canonical places to `_walk`, `evaluate_candidate`, Task 44/45 evidence and `score_candidates`/`_select`. No second ranking engine. Ratings/counts are nullable source facts; only provider venues use confidence-aware rating quality. Mock scoring/fingerprints remain.
- POST `/api/plans/options` uses a random active-computation capability in `option_sessions.py`: at most 20 continuations, per-entry lock, ten-minute automatic expiry, original request/OutingBudget, discovered facts, directed routes and returned-combination/primary-venue sets. It accepts no replacement constraints and never refills budgets. One bounded shortlist expansion is allowed; provider failures stop expansion. No persistence/cross-outing provider cache.
- POST `/api/starting-places` validates a 3–200-character query, calls existing OAuth Text Search Pro once behind a local gate, and returns at most three matches with type-based precision and credits. Explicit browser confirmation supplies the existing AuthorizedStart with additive precision metadata. Areas require representative-point consent. No Geocoding service/key/permission is added.
- Fixed-path Next server proxies cover both POSTs. React retains page-only lookup/contact promises, origin precision and consumed option batches. A new submission clears stale results/errors/capabilities; failed expansion preserves useful cards. No browser storage. Privacy text discloses separate ten-minute backend continuation expiry.
- `real-venue-facts.tsx` and structured `constraintIssues` separate presentation from evidence: missing optional rows disappear, critical warnings remain. Google/third-party credits, original IDs, long-name titles and fictional card presentation survive.

Settings, effective Cloud values, pricing, gates and verification are in [real planning](docs/real-planning.md) and [billing safeguards](docs/billing-safeguards.md). No Task 47/database work.

## Task 46 manual acceptance follow-up

- `travel_constraints.py` supplies bounded scope/operator source evidence to the existing interpretation validator. Additive exclusive flags travel through PlanningRequest, mock evaluation and exact Task 44 feasibility independently for leg/total/first-leg caps. It is validation/normalization, not a replacement AI or itinerary engine.
- Active option contexts retain the original search area and whether the single explicit discovery refinement was used. `/api/plans/options` accepts only a continuation plus an additive expandDiscovery flag; refinement reuses that outing/session budget, retained candidates, seen combinations and directed route cache. Initial empty discovery can expose this capability. Per-category inventory remains ten; contacts extend original capability IDs without resetting budget/age. Discovery/quality and planning diagnostics expose aggregate stage/rejection counts.
- `StartingConfirmation` owns the pending browser-only match-selection promise. LocationControls exposes preparation/cancellation to the existing submission flow; confirmation resumes the same request, while edits/unmount/failure cancel it. No keystroke lookup, automatic geolocation permission, browser storage or new geocoding provider.

## Task 46 development exploration

`ProviderSettings.exploration` centrally validates the local-only flag and supplies effective ceilings while preserving original safe settings. Existing real orchestration retains discovery/cursor/identity/route/seen-plan state in the expiring option capability; finite computational frontiers and existing route-stage selection avoid exhaustive city matrices. Next proxies carry original host/origin/nonlocal-forwarding evidence; backend exploration middleware rejects public callers even when proxied through localhost.

`backend/development_cost.py` is a local-only, private, versioned counter ledger. It contains no provider content or request identity. OS file locking serializes cooperating processes, conservative gross reservations are fsynced before provider work, and transport dispatch counters distinguish measured sends from reserved work. One stable ledger shares the daily estimate and rolling-minute admission across outings and backend restarts. Storage corruption/unavailability refuses work. Normal mode does not use the new ledger; Google content still has no disk persistence. No database or Task 47 integration.

## Task 46 location-first extension

The active real website uses additive `PlannerInput.locationFirst`; direct legacy clients can retain city-wide discovery. `location_policy.py` owns validated first-leg minutes/miles, deterministic source phrases/geography and finite flexible bands. The existing interpreter/calendar/clarification and Task 44 exact-evidence evaluator remain authoritative. `starting_areas.py` compares provider-supported public references with first-venue route/second-activity proximity evidence and returns expiring confirmation capabilities. Next proxies `/api/starting-areas` through the same loopback/trusted-origin boundary; no browser provider credentials or automatic geolocation.

`sequential_discovery.py` stores positional candidates, anchor searches, strategy/page cursors and flexible-band state in existing transient option sessions. `discovery_inventory.py` merges accepted associations and all credits without resurrecting rejected matches. Multiple previous-stop anchors feed later search regions. Existing computational frontiers and staged directed routing feed `spatial_beam.py` (96 partial paths, first-venue coverage, distinct identities, known transitions), then existing scheduler/feasibility/ranking/diversity. First-leg routes stay separate from inter-stop/total travel. No database, optimizer dependency, new provider tier or Task 47 component. [Detailed bounds and limitations](docs/real-planning.md#location-first-planning).

## Task 46 mandatory-origin acceptance

Publication now requires an explicit origin in real and mock modes; old origin-free continuations are rejected. `FirstPreference` in the client hydrates validated first travel and owns explicit-edit precedence. `effective_max` in the backend owns the inclusive 2× Flexible rule; staged-band/widening state is removed. `starting_scoring.py` evaluates provider-backed regional public references using actual first/onward routes, original-range preference and coverage overlap; verified preflight onward venues/edges feed the same positional discovery/beam engine. Normal discovery leaves search headroom for remaining stops. `mock_origin.py` provides explicitly fictional mock first-leg fixtures, without Google calls or claims about actual coordinates.

`provider_errors.py` allowlists service/quota evidence and attaches safe request accounting; unknown boundaries remain unknown. HTTP and per-element quota/auth/permission errors stop unsent matrices. The developer disclosure admits fixed labels/numeric counters only. Existing option cards survive exploration failure; changing origin explicitly invalidates prior recommendations. Google Places daily override is now 200 after read-back; all minute/Routes/Details quotas and the persistent $10/day exploration estimate guard remain. No Task 47 storage.

## Task 46 Surprise Me acceptance

OutingRequest.planningMode distinguishes origin (default, still confirmed) from surprise (first activity is the beginning). PlannerInput rejects origin/first-leg fields for Surprise Me, requires a named destination and forces the same sequential-discovery path. The former suggested-reference endpoint remains isolated for compatibility but has no active UI call path. No placeholder origin or first-leg matrix row is created.

between_policy owns narrowly grounded consecutive-leg minutes/miles intent; the existing FirstTravel shape and exact Task 44 evaluator enforce strict or deliberately doubled Flexible constraints. Independent client editors preserve source/manual precedence and inactive first preferences. Explicit first-scope removal is bound to submitted text; other hard scopes survive. SurpriseHistory keeps only 120 first IDs for 10 minutes in page memory.

surprise.py adds system-random weighted sampling over relevance/feasibility/quality-qualified shared-planner results. Active contexts retain seen complete signatures, primary/activity IDs and coarse venue-region coverage. Sequential anchors and balanced following frontiers preserve several first-stop regions before the existing 96-path beam. User-triggered continuations keep the original inventory/routes/budgets; mocked Surprise continuation reuses the shared fictional generator/evaluator/ranker. Existing mode gates, ledger, source attribution and quota/error handling remain. No storage/database/dependency or Task 47 component added.


## Task 46 comprehensive discovery acceptance

Cost reservations no longer hold a file lock across provider I/O; dispatch metrics re-read/update the original day under short locks. Details reads usage after reservation exit, and only pre-admission failures allow explicit unsent recovery. No ledger schema reset or provider-content persistence.

Real ranking uses absolute confidence-weighted rating and smooth travel scales; shared spatial frontiers preserve several first paths. Initial diversity can demand one finite additional discovery batch, while the 96-path beam and two routing stages stay bounded. Only published cards enter seen history. Combination-only continuation and explicit regional exploration are separate. Sequential jobs retain private geometry hashes, page/query IDs and finite ring progress; public diagnostics expose aggregate funnel/first-route/beam/shortage counters only. Existing provider gates, exact feasibility, cumulative costs and ten-minute context locks remain authoritative.

## Task 46 — independent inventories and browsable classification

Current acceptance supersedes historical 20-candidate/reject-all-travel-violations checkpoints. sequential_discovery rotates finite page/strategy/region jobs per distinct activity; discovery_inventory preserves accepted associations toward 100/activity. Finite frontiers and spatial_beam bound computation independently. travel_classification keeps original evaluator evidence and exact deviations, and selects all-stop novelty within a quality band. RankingResult.explorationPlans is a real-only explicit travel-violation channel; provisionalPlans remains violation-free. Nullable wheelchair evidence does not trigger new field requests.

provider_work adds cooperative disconnect cancellation and short pre-dispatch admission waiting. provider_budget consults process and persistent development_cost minute capacity; atomic reservations remain authoritative. No background provider queue or retries.

lib/itinerary-pages keeps immutable in-tab result snapshots and ordered signatures. Latest continuation metadata stays separate from the viewed page. ItineraryPagination invokes only navigation callbacks; successful generation appends, empty/error actions preserve pages. Edits/reload reset history. Existing cards and contact sessions remain. Task 47 is pending.

## Task 46 — location/calendar provenance

backend/location_context.py defines destination intent/resolution metadata, validated IANA zones, compatible approximate anchor evidence and pure outing-validity checks. The planner keeps private search geometry and AuthorizedStart separate; sequential discovery uses currentArea for nearby destination searches even when routing starts elsewhere. Interpretation records explicit clock provenance; continuation reads the saved calendar instead of serializing defaults as new user times. Session lifetime remains owned by option_sessions. lib/destination-context.ts mirrors intent/recovery contracts; submission-only permission preflight and the existing StartingConfirmation coordinate fallback without a new location panel or provider. Publication surfaces only safe codes/aggregate diagnostics. No durable provider-content store is introduced.

> Current Task 46 acceptance: source-grounded open activity intents share the existing normalization, independent inventory pools, sequential discovery, beam, Routes evidence and ranking. Optional legacy party-size fields no longer drive planning. `DevelopmentCost` remains durable across exploration outings/restarts, with a nonblocking configurable warning instead of a daily estimated-cost admission cap; integrity and verified project minute protection remain. See [limits audit](docs/exploration-limits.md). Task 47 is untouched; historical sections retain prior checkpoints.

## Task 46 — explicit travel-alternative visibility and evaluation

`OptionsRequest.showBeyond` is a continuation visibility choice checked under the existing outing lock; `RankingResult.canShowBeyond` advertises withheld checked alternatives. History records only actually displayed combinations. Nearby discovery geometry remains separate from confirmed route origin and exact travel classification; beam/frontier heuristics preserve multiple candidate paths. Developer notes are separated from ordinary result copy. `backend/evaluation` is an explicit localhost-only model benchmark with authored inputs; it neither imports venue transports nor runs in ordinary tests/startup. Provider/model research documents describe future interfaces only. No new runtime service, database, dependency or Task 47 component.

## Planned Stage 1 extension — Tasks 48 and 50A–50E (not implemented)

Current Stage 1 functionality is AI-assisted leisure venue discovery and sequential itinerary recommendations, with transient page/continuation history. It is not a general fixed-destination errand planner or durable saved-plan database.

The owner-approved [Stage 1E roadmap](TASKS.md#1e-save-plans-and-launch-our-first-mvp) plans structured mandatory/flexible stops, named destinations, precedence/reorder permissions, origin/end-point/return topology, stop-duration evidence and complete-journey deadlines. Task 48 should leave straightforward schema extension points for those concepts and provider/constraint metadata without speculative tables or advanced planning implementation. Tasks 50A–50D will extend the existing interpreter, discovery and planner; 50E will integrate persistence and basic edits. Unknown durations must remain unknown, not invented deadline compliance. Rich Stage 2 optimization and Stage 3 editing remain later work. This note changes no current API, schema, implementation, provider gates or task status; Task 47 is unstarted.


## Task 47 — isolated PostgreSQL readiness check (historical completion checkpoint)

`backend/database_check.py` is a CLI-only boundary using pinned Psycopg 3 binary distribution in the existing virtual environment. It is not imported by FastAPI, the planner, Next.js or health endpoints. `backend/.env.example` defines `WHERETO_DB_HOST`, `WHERETO_DB_PORT`, `WHERETO_DB_NAME`, `WHERETO_DB_USER`, `WHERETO_DB_PASSWORD` and `WHERETO_DB_SSLROOTCERT`; only an explicitly sourced ignored backend file supplies them. Normal startup stays database-independent and mock by default.

The local choice is Supabase shared session pooler on port 5432 for IPv4 compatibility, `sslmode=verify-full` with an explicit CA, read-only transaction, bounded connect/query timeouts and deterministic credential-free CLI output. No ORM, migration infrastructure, persistent pool, tables, Data API client or save endpoint exists. A successful check proves client-to-pooler TLS and authenticated PostgreSQL queries, not the pooler's internal transport properties. Project `whereto` / organization `Where To` (Free), region `us-east-1`, and Healthy dashboard status are confirmed. Ignored local configuration and the dashboard-linked public CA are installed; DNS and pre-authentication TLS 1.3 hostname/CA verification passed. Actual authenticated hosted verification passed on October 30, 2026: constant SELECT succeeded inside a read-only transaction with verified client-to-pooler TLS, rollback and clean closure. Future production direct IPv6 versus session pooler depends on FastAPI hosting; transaction mode is reserved for a possible transient/serverless architecture. [Setup, limitations and Task 48 handoff](docs/database-setup.md).


## Task 48 — private PostgreSQL foundation (complete)

The additive `backend/migrations/0001_initial_planning.sql` creates `whereto.plans`, `plan_constraints`, `generated_itineraries`, `itinerary_stops`, `source_metadata` and the administrative `schema_migrations` ledger. UUID ownership chains cascade from plans to options to ordered stops to permitted source references; constraints have a one-to-one plan key. Current requests/activities/travel/accessibility map to typed columns; stop identity and nullable user/fictional timing permit later additive journey migrations without implementing 50A–50E.

`backend/database_migrate.py` reuses existing Psycopg and verified TLS in a separately invoked administrative CLI. Numbered checksummed SQL, advisory transaction locking, rollback rehearsal and atomic apply replace an unnecessary ORM. A separate read-only verification checks the actual hosted ledger, tables, ownership, ACLs and forced RLS. Private schema/table grants deny PUBLIC and Supabase API roles; no runtime identity/policies or database startup dependency is added. Data API remains disabled.

Google Place IDs and app-owned provenance are retained; venue facts, route metrics, provider-derived text/snapshots, precise origins and continuation capabilities are excluded. Task 49 must implement allowlisted transactional save/retrieve behavior, completeness validation, explicit access/refresh/failure contracts and safe timestamp updates; Task 50 must complete runtime least privilege, authentication/authorization and public write protection. Five application tables are actually applied and empty in the confirmed hosted development project. [Detailed relationships, field mapping, security, provider terms, commands and extension boundaries](docs/database-schema.md). Tasks 49, 50 and 50A–50E remain unstarted.


## Task 49 — private plan persistence

Explicit Save Plan is a separate Python-controlled SQL flow; generation remains
DB-independent. `backend/saved_plans.py` issues bounded ten-minute server receipts,
allowlists the trusted generated selection, and atomically writes all five tables
with Psycopg parameters. Additive migration 0002 retains selection, hashed private
access, expiry, missing legacy preferences and fictional-only snapshots. Next's
fixed `/api/plans/save` and `/api/plans/reopen` proxies keep SQL credentials on
Python; `lib/saved-plans.ts` contains only browser-safe link/display contracts,
while `lib/persistence-proxy.ts` owns upstream server calls. `SavedPlans` presents
an independent saved document, preserving the live three-card/exploration flow.

The separate non-owner runtime login has only SELECT/INSERT and capability-scoped
forced RLS. It has no ledger, DDL, UPDATE, DELETE or administrative membership.
Reads use a read-only transaction; writes roll back completely on any failure.
Private links contain a 256-bit server-generated token in a fragment; PostgreSQL
stores its SHA-256 verifier. Access expires after 30 days; browser localStorage
remembers only the last link. API routes are restricted to local development.
Real snapshots retain only Place IDs/app provenance; all Google content and route
metrics remain unavailable without a future intentional refresh. There is no
provider call on reopen. Exact origins and transient geographic evidence are not
retained. [Full mapping, routes, limits, transactions and limitations](docs/saved-plans.md).
UUID/ordinal relationships remain extensible for 50A–50E without implementing them.


### Tasks 46/49 acceptance corrections

Runtime persistence settings now pass through `backend/persistence_config.py`:
explicit restricted settings win; an administrator-style environment selects only
the existing owner-private restricted file, parsed without executing shell.
No administrator SQL connection, role/grant/schema change or startup DB dependency
is introduced. `backend/failures.py` supplies fixed classifications and correlation
logging without sensitive inputs. Next proxies preserve known error envelopes;
invalid planner responses receive a distinct internal-application classification.
The shared origin boundary recognizes IPv4-mapped loopback while rejecting public
forwarding. `SavedPlans` publishes links only after confirmed commit and imports
same-tab hash changes; starting-place controls have explicit grid spacing.
Movie-theater aliases are canonicalized before conflicting-category detection;
the existing one-stop and multi-stop engine, geography, provider retention and
Strict/Flexible limits remain. [Evidence and limits](docs/real-planning.md#tasks-4649-acceptance-fixes--cinema-loopback-and-diagnostics).


## Tasks 46/49 acceptance refinements

Added explicit capability-authorized saved refresh and main-position saved cards; `saved_refresh` never writes provider content. `dev_start` loads owner-private allowlisted data locally. Retail parsing/evidence uses the existing custom-activity and discovery/routing pipeline, with transient containment relationships. Ranking now includes first-leg evidence and exposes sanitized late-arrival reasons. A separately gated loopback-only development snapshot replaces product diagnostics; production proxies strip internal metrics. No migrations, RLS or later-roadmap functionality.

[Details](docs/acceptance-refinements.md).


## November 1 — final Tasks 46/49 acceptance repair

Current behavior supersedes earlier automatic/all-option saved-view descriptions: normal visits keep saved links collapsed, explicit private links render only the selected detailed itinerary, and Open saved plan opens a secure new tab. One explicit selected-stop detail load uses the existing Pro mask with Maps URI; optional phone/website fields require deliberate existing Enterprise contact opt-in. Provider content stays in memory. Structured continuation states distinguish combinations, discovery, bounded exhaustion, limits, constraints and pending routes; ranking is preserved. Actual default-port startup was checked, and occupied backend ports now give actionable guidance. No migration, role/RLS/TLS/quota change or later task. See [the final repair report](docs/final-acceptance49.md) and the latest HANDOVER.md evidence.

## Tasks 46/49 saved-detail reliability and local AI readiness

Reopen advertises a separately gated `automaticVenueDetails` policy; default false.
The client issues at most one selected-only details action per explicit open when
separately approved, with no contact-tier escalation/retry. Ordinary home/remembered
links trigger no provider work. `saved-details-request.ts` centralizes bounded
manual/optional navigation loading; all returned Google content remains in memory.
`RefreshSessions` now guards whole-action UUID replay and exposes fixed admission
reasons/reset estimates; shared durable accounting and existing quotas remain.

`ai_readiness.py` prepares the existing local extraction prompt once in a daemon
thread under an owner-only default-off development flag. Health does not wait.
`performance.py` retains numeric AI timings only; the protected local diagnostic
endpoint includes readiness and timing snapshots. Development numeric Server-Timing
headers separate backend/proxy work; production proxies omit them. No interpreter,
ranking, route concurrency, schema or persistence redesign. See
[measurements and contracts](docs/saved-details-performance49.md).

## Tasks 46/49 sharing/UI refinement — November 1

`RefreshSessions` now records hashed capability/action UUID replay timestamps (30 minutes, 512 entries) rather than cumulative per-capability outings. Each explicit selected-only action has max four unique references and reuses existing shared ProviderBudget/ledger admission. No provider-response cache or schema change. Official website anchors accept validated provider-returned HTTP/HTTPS independently of phone; Maps URLs keep their separate HTTPS allowlist. `/dev/diagnostics` uses SSR + proxy + existing backend local-development guards and returns 404 in production. It replaces the homepage diagnostic disclosure. `/supported-activities` renders shared catalog labels/event metadata, and activity follow-ups link there in a new tab. Pure presentation helpers deduplicate flexible/group warnings without changing planning/ranking. [Detailed boundaries/tests](docs/sharing-ux49.md).

## UI and selected travel mode — November 2

The header links to `/how-it-works`; guide/privacy/terms share restrained information-page styles and use separate native tabs. Form diagnostics/demo actions are removed while result provenance remains. Existing `transport` carries manual preference → interpretation/normalization → origin and inter-stop routing → continuation/output → the existing SQL column. Public planning defaults to driving and accepts only driving/walking, leaving legacy internal models readable. Source/UI conflicts fail explicitly. Existing matrix bodies already support DRIVE/WALK. Context mode guards and client evidence checks prevent mixed-mode reuse; hashes/feasibility retain mode identity. No search/ranking/schema redesign. One shared walking beta notice covers displayed walking routes.

[Acceptance details and evidence](docs/ui-travel-mode49.md).
