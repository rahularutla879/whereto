> Current execution path (Task 31): homepage → Next.js/FastAPI POST /api/interpret → replaceable local AI provider → validated request/manual merge → POST /api/plans/generate → Task 26 generator → Task 27 ranking. Earlier task sections below describe historical checkpoints. TypeScript no longer interprets submitted text or executes planning in the app.

# Current architecture

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
- Full ISO dates and English full/three-letter month names with day/year work in month-first or day-first order, including ordinal suffixes and “7 of November 2026”. Missing years, invalid dates and conflicting expressions need clarification. Explicit dates are validated, never rolled forward or replaced by fixture dates. A nonblank manual Date wins over natural-language date ambiguity/conflicts, while independent time constraints remain in force.

Clock semantics (planner resolution is whole minutes):

- `6 PM`, `18:00`, noon = 720, midnight as a start = 0. Midnight as an end = 1440, the end of the selected day. `between 6 and 9 PM` inherits PM for the bare first hour; `from 18:00 to 21:00`, dash ranges, `at`, `start(s)/starting`, `end(s)/ending`, `until` and `by` are supported. Unqualified hours such as `at 7` need AM/PM. Explicit 24-hour clocks retain their values.
- `after 6 PM` means earliest 18:01 and `before 10 PM` means latest 21:59, strict bounds at minute precision. `at`, `between`, `from/to`, `until` and `by` are inclusive planner boundaries. Multiple bounds intersect without discarding constraints; incompatible starts/windows need clarification. These are overall outing bounds, not individual-stop appointments.
- Without explicit starts, evening/night/tonight defaults to 18:00 through midnight, disclosed in notes. Explicit starts take precedence over the day-part default. Ordinary no-time requests retain 10:00–24:00; an end-only window earlier than 10:00 permits a midnight earliest start. Today without an explicit/day-part start uses no earlier than the current local minute (rounded up), disclosed. A requested start already past today, past date, expired window, or past evening default returns clarification; nothing moves automatically to tomorrow.
- 22:00–01:00 is identified as overnight and refused with a single-day explanation. Other reversed/empty windows report contradictory constraints. Explicit following-day/overnight wording is refused. The planner's midnight cutoff and all feasibility/ranking rules are unchanged.
- On a resolved date, local times that do not exist or occur twice at DST changes require an unambiguous time. Windows crossing an offset change require a window wholly before/after it because the existing planner computes wall-clock durations. No artificial fold or elapsed-time equivalence is invented.

Unsupported wording (including morning/afternoon without supported explicit treatment, missing-year dates and broader relative phrases) can require an exact Date and overall clock window. Stop-specific time wording in multi-stop requests requires clarification. Finite phrase guards and AI extraction do not guarantee arbitrary-language completeness. Clarification uses the existing issues/empty-state path; there is no new UI flow, session state, parser framework, dependency or infrastructure.

Fixed-clock tests cover local/UTC boundaries, month/year/leap transitions, all weekday semantics, weekend boundaries, conflicting/past/overnight windows, noon/midnight and DST folds/gaps/crossing windows. Interpreter-to-engine tests and actual HTTP proxy/client tests exercise source omission of tomorrow, dates/time windows and manual precedence. `backend.ai.smoke_dates` separately checks original Qwen phrase fidelity and deterministic/planner outcomes; it never downloads a model.

## Natural-language-only correction after Task 32

The reproduced live failure was a stale FastAPI runtime on port 8000: both the Next.js proxy and direct backend returned the old Task 31 “relative dates are not resolved yet” issue, while a fresh process importing the current checkout resolved the identical full request to October 22, 2026 with location/group/budget/travel/cost intact. The old process was stopped and the current backend restarted using the existing reload-enabled development command. No resolver or AI arithmetic workaround was added.

The separate frontend display gap is fixed in `lib/preferences.ts` and `app/page.tsx`. State holds displayed `values` and per-field `manual` markers. `manualPreferences` submits only deliberate nonblank edits (including zero), plus deliberately selected cost/`costExplicit`; auto-populated values never become manual input. Clear releases a field; reset clears all markers/values. Functional state updates preserve edits made while a request is pending.

`generateOuting` now accepts an optional client-only `onInterpreted` callback in its existing context argument. After a successful interpretation with no issues, it validates/maps the existing effective `request` fields to controls and invokes the callback before the unchanged planning POST. No API request/response schema, provider protocol or planner contract changes. Date display uses Python’s resolved calendar value; null optional caps/date remain blank, with the existing Balanced UI default. There is one model interpretation per submit, none per keystroke or preference display. Issues/provider failures do not populate guessed values and never call a fallback. Successful interpretation may remain visible even if the subsequent planner call fails; it is explicitly labeled as values from the last interpreted request.

Tests cover state transitions, zero/Balanced overrides, release/reset, pending edits, failure boundaries, actual HTTP interpretation-to-engine/card data and fixed-clock complete requests. Live development and clean production browser checks additionally verify untouched-panel text submission, repeated stops, tomorrow, auto display, replacement by new text, deliberate overrides, genuinely missing essentials and backend failure/recovery. Styles, recommendation design, fixture and ranking are unchanged.

## Task 33 — temporary clarification state

The existing `/api/interpret` input gains optional `pending` and `answers` fields. Python’s `PendingClarification` contains the unchanged original text, grounded `Interpretation`, separate typed answers and an aware reference clock. The response adds `questions` (field, natural question, essential/ambiguous kind), `pending` and `unsupported` explanations; existing `issues`, notes and resolved request remain compatible. All state is Pydantic-validated on every submission. There is no server session store, database, authentication, new endpoint or conversation framework.

The homepage holds this envelope in React memory. A new request calls the existing AI provider once. A continuation copies and revalidates the saved extraction, applies simple answers deterministically, and uses the existing Task 32 date resolver and `OutingRequest` validation. The initial clock anchors relative-date meaning across follow-ups; the current clock rechecks past dates/starts before planning. Answered locations recompute local calendar interpretation from that original reference. Date corrections replace only date wording, preserving independent clock bounds; overall time corrections require an explicit user answer. An unclear activity occurrence is replaced in its original position while known stops/repeats remain. Alternative/no-activity requests ask for an explicit ordered stop list.

Required location/group drive catalog matching, capacity and group cost. Exact dates are required for `EVENT_ACTIVITIES`, and ambiguous supplied date/time/activity constraints need clarification. Missing budget, travel caps, optional preferences and ordinary flexible dates do not. Original unsupported requirements produce explanations rather than clarification loops. Invalid answers retain the original state for correction; valid-but-infeasible requests proceed to the unchanged ranking explanation and clear clarification state.

Precedence remains deliberate nonblank manual setting → explicit follow-up correction → original interpretation. Answers stay separate from `ManualPreferences`; displayed inferred values still use Task 32’s manual markers. All explicit original money/travel/experience fields remain in the extraction and continue through existing grounding/validation. The UI sends only genuine manual controls on each continuation.

`PlanningSession` provides a single active AbortController and identity guard: duplicate submits are ignored; cancellation, editing text and Try an example abort and invalidate old results. The client checks cancellation before sending a plan. A valid extraction is retained through planner failure, allowing a model-free retry. Successful planning (including honest infeasibility) clears pending state. Provider/network failures keep the original text; failures during continuation keep saved state and answers. No automatic retry occurs. Reload/close intentionally discards temporary state. The small follow-up panel reuses existing preference/button styles; cards, artwork, fixture and scheduling/ranking engines are unchanged.

The answer grammar is deliberately bounded: simple cities, numeric/one–twenty group sizes, catalog activity aliases and Task 32 dates/clock windows. Complex corrections and unsupported requirements can require editing the original text. This is not a general chat interface or guarantee of arbitrary-language understanding.

Task 33 location wording correction: missing/uncertain-location prompts and empty location placeholders are city-neutral. Clarification accepts a supplied city directly and passes it unchanged to the existing planner; catalog coverage is checked there rather than asking users to replace their city during clarification. The fictional catalog still covers Baltimore only, so other cities receive the existing unsupported-location result. Missing locations remain unknown; no city/device-location default is introduced.
