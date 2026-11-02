# Technical decisions

This record began with source inspection on October 19, 2026, before Git was initialized; it does not reconstruct earlier project history. Reasons below are limited to code comments, documented behavior, or explicit owner requirements.

## Confirmed current choices

| Choice | Evidence and established reason |
| --- | --- |
| Next.js App Router, React, TypeScript, Tailwind CSS | Present in package.json and app/. The original reason for selecting this stack is not recorded. |
| Client-side rules and local fictional catalog | app/page.tsx calls makePlans directly; README identifies this as a frontend demo without external APIs. No AI provider is selected. |
| Conservative parsing; reject unsupported/ambiguous input instead of partial plans | lib/request.ts, lib/planner.ts, and tests enforce requested activities without unrelated substitutions. |
| Hard limits precede preference ranking | lib/planner.ts filters capacity, cost, travel, date, and timing before scoring. Preference must not bypass feasibility. |
| Preserve requested activity order; return at most three distinct options | Planner enumerates venue combinations and deduplicates strategy winners. This preserves requested order and avoids duplicate recommendations; the original three-option product rationale is not recorded. |
| Explicit fictional event dates and Baltimore calendar | Fixed fixtures demonstrate scheduled events; the date helper uses America/New_York and tests inject a reference day for deterministic results. |
| Local SVG artwork and system fonts | components/artwork.tsx and app/globals.css; README states no remote images/font downloads. Original styling rationale is not recorded. |
| Build with next build --webpack | Explicit package.json script. Reason for choosing Webpack is not recorded. |
| Six concise continuity documents; preserve README | Owner requirement for beginner-friendly continuity without extra bug/feature/flow documents. |

## Proposed future components — not selected or implemented

- Real venue/event data and routing providers: evaluate in Stage 1; no vendor commitment or paid-service approval exists in this record.
- AI interpretation/conversation, interactive map, storage, saved versions, and sharing: product roadmap only. Provider, database, authentication, and hosting choices remain open.

## October 19, 2026 — private GitHub backup

At the owner's request and after explicit approval to create the repository, initialize Git in the existing folder and use the private [rahularutla879/whereto](https://github.com/rahularutla879/whereto) repository as `origin`. Use `main` and the `prototype-v0.1` checkpoint tag. Preserve application files and exclude credentials, environment files, generated outputs, dependencies, and local settings. Browser-based GitHub CLI authentication keeps passwords and access tokens out of chat and the repository. No deployment or automatic backup service is configured.

## October 20, 2026 — minimal Python backend (Task 23)

Use the existing Python 3.12 installation, an ignored `backend/.venv`, and plain FastAPI plus Uvicorn without optional extras. Pin the tested dependencies, including transitive packages, in `backend/requirements.txt`. Use Python's standard `unittest` and HTTP libraries for the backend test and the existing Node test runner for Next.js communication; no additional test framework is needed. Implementation follows the maintainers' [FastAPI first steps](https://fastapi.tiangolo.com/tutorial/first-steps/) and [Uvicorn settings](https://uvicorn.dev/settings/), plus the installed Next.js route-handler documentation.

Keep the boundary limited to health checks. Next.js contacts Python server-side, avoiding a public backend address in browser code and unnecessary CORS configuration. Use uncached checks, a short timeout, and a generic 503 response for an unavailable or unhealthy backend. The homepage and mock planner remain independent. Use two Terminal windows with npm scripts rather than adding a process manager; the existing `npm run dev` command is preserved. Planning migration belongs to Tasks 24–29.

## October 20, 2026 — backend contracts without planner migration (Task 24)

Keep Pydantic types in `backend/models.py`, with reusable scalar constraints and discriminated venue/event records. Preserve current response JSON names and use resolved typed requests rather than duplicating UI form strings or porting text parsing. Retain existing frontend limits, allow unknown optional venue information, and default data-quality metadata to unknown rather than claiming verification. Use a test against actual TypeScript planner outputs to detect cross-language drift without copying its catalog or algorithm. No new dependency, endpoint, frontend integration, or database is needed. Schema validity does not prove supported location, real availability, or request feasibility; those remain future planner responsibilities.

## October 20, 2026 — shared fictional catalog (Task 25)

Use a compact JSON fixture for catalog values and tier/date definitions, consumed by both runtimes with small record expansion adapters. Keep TypeScript keyword patterns and planning logic in place. This prevents independently maintained data copies without adding build or synchronization tools. Python adds explicit provenance through Task 24 models; absent hours and availability stay unknown. Compare every expanded record across runtimes and preserve pre-change output fingerprints to detect accidental behavior changes.

## October 20, 2026 — unranked Python candidates (Task 26)

Use separate additive candidate contracts rather than weakening fully scheduled final-plan validation or inventing ordinary schedules/travel totals. Reuse Task 24 request/venue/event/error/scalar types and the Task 25 loader. Allow repeated request activity entries and require explicit `allowRevisits` for duplicate record IDs. Enumerate lazily in fixture/request order without truncation; provide a collected structured result for the current small dataset. Prune only identity and fixed-event incompatibilities here; defer final feasibility, scheduling, filtering and ranking to Task 27, and frontend integration to Task 28.

## October 20, 2026 — Python constraint evaluation and ranking (Task 27)

Use a separate evaluation/ranking module over Task 26 candidates, with additive Pydantic contracts for nullable calculations and explicit confirmed/provisional/violated states. Keep unknown-hours alternatives separate from confirmed recommendations; do not invent hours or availability to make the fixture pass. A known event schedule is sufficient for mock scheduling unless availability is explicitly required or supplied. Confirmed always means checked against supplied evidence, not real-world verification. Leave legacy frontend result contracts and TypeScript behavior unchanged until Task 28.

Use earliest-finish scheduling for ordered single-day windows/fixed events, Decimal budget comparisons, injectable price/travel quote functions, normalized weighted scores and stable record-ID ties. Prefer stop diversity among near-scoring remaining candidates (within 0.15), with at most three combined confirmed/provisional options and no known-violating options. These small candidate sets need no optimization library, external service or new dependency. Preserve the existing total travel/per-person limits while adding optional backend per-leg/group limits.

Record future significant decisions with date, choice, reason, and relevant tradeoffs. Do not turn options into commitments without an actual decision.


## October 20, 2026 — Task 28 Python execution

Reuse the Task 23 server-side proxy convention for a validated planning POST. Preserve the existing TypeScript interpreter and manual overrides; keep planning exclusively in Task 26–27 Python. Adapt the ranking envelope for existing cards without recalculating or re-ranking. Show provisional alternatives and fictional-data feasibility explicitly, and keep null values unknown. Retain the old engine only under `lib/legacy` for historical regression tests. Use fixed illustration data for initial inspiration cards; an unavailable backend must clear results and show an error. Preserve the established visual design and add no dependencies. Weighted Python ranking intentionally replaces separate TypeScript strategy picks; README and ARCHITECTURE explain the difference. Stop before Task 29.

## October 20, 2026 — standalone local AI, replaceable provider (Task 30)

Select **Qwen3 4B** (`qwen3:4b`, tested `359d7dd4bcda`, Q4_K_M) through the already-installed Ollama 0.35.1. The owner approved its approximately 2.5 GB download after the installed Llama 3.2 3B repeatedly invented a $0 budget for “affordable”. Qwen correctly handled the four required samples twice, with a roughly 5.5-second first call and 1.6–1.9-second warm calls on the M2/16 GB Mac; about 3.2 GB loaded at 4096 context. It fits the requested 3B–4B range without a larger model. Gemma3 4B would require roughly 3.4 GB including vision capability that this text-only task does not need; it was not downloaded. The existing much smaller 270M and 1.5B models were inspected but not benchmarked. This is a suitability evaluation for these samples, not a general model ranking.

Sources: official [Qwen3 4B metadata](https://ollama.com/library/qwen3:4b), [Llama 3.2 metadata](https://ollama.com/library/llama3.2:latest), [Gemma3 4B metadata](https://ollama.com/library/gemma3:4b), [Ollama schema outputs](https://docs.ollama.com/capabilities/structured-outputs) and [thinking controls](https://docs.ollama.com/capabilities/thinking). Downloaded metadata was also checked locally. Set `think: false`, temperature 0, non-streaming schema output, 4096 context, a 512-token output limit and five-minute keep-alive inside the Ollama implementation. A raw response check confirmed no thinking content. The recorded tag/ID is reproducibility evidence; application code does not pull or upgrade models.

Use a small Python `Protocol` with `interpret(text) -> Interpretation`, a provider factory and environment configuration. Standard-library HTTP plus existing Pydantic is enough; no SDK/framework or extra dependency is justified. Keep the partial extraction separate from the resolved planning request. Vendor-specific formats/options stay inside the adapter; planning models and engines have no vendor imports. A future hosted adapter can implement the same interface without changing frontend or itinerary optimization, but no such provider is implemented now.

Qwen omitted “tomorrow” in one additional request, and activity phrases still require normalization/clarification. Schema checks do not prove semantic fidelity. Task 31 must provide appropriate interpretation validation, ambiguity/default/date handling and manual override precedence before connecting AI to planning. Task 30 leaves the existing application execution path intact and stops here.


## October 20, 2026 — Task 31 AI execution and conservative conversion

Reuse `AIProvider.interpret(text)` and extend its partial schema; keep provider-specific prompts/options out of the interpreter, request models and planner. Use a dedicated interpretation endpoint before the existing planning endpoint so uncertain extraction remains inspectable and no AI output participates in itinerary arithmetic. Do not default missing city/group or silently use the old parser. Exact aliases and source guards validate AI output; they do not generate keyword-derived plans. Valid wording outside this conservative boundary may need rephrasing. Common date wording is retained independently of model omissions, while actual relative-date resolution stays in Task 32.

Keep manual controls and track an explicit cost selection separately from the initial Balanced default. Nonblank manual fields win, zeros are real caps, and blank/default controls preserve text. Suggestions require a user choice through the existing text input; do not add a confirmation interface or multi-turn state. Scope dinner timing with an optional stop-index field to preserve lunch and dinner as separate occurrences without rewriting scheduling. Use the existing 29-category fixture and explain unsupported currency, unverified tastes and mode-independent simulated travel.

Expanded schema-only prompting initially caused invented group/location values and unnecessary uncertainties. Complete null-filled examples improved the focused real-model samples; grounding checks reject invented core values. Increase this same model's context/output limits to 8192/1024 to fit the expanded contract and examples. No new model, dependency, API service or infrastructure is installed. Finite smoke tests and guards cannot guarantee complete semantic accuracy; record failures and safe rephrase behavior honestly.

## October 21, 2026 — Task 32 calendar policy

Keep date/time arithmetic out of AI output. Preserve original expressions, resolve them in one bounded standard-library Python module, then send the existing exact-date/minute contract to the planner. Reuse the known Baltimore timezone and disclose UTC fallback elsewhere; do not add geocoding or accept model-guessed zones. Define “this” as upcoming including today and “next” as the following calendar week. Require a day for weekend requests; use a disclosed 6 PM night/evening default. Keep strict after/before minute bounds and manual Date precedence. Reject past starts, overnight windows, DST-ambiguous/nonexistent clocks and windows crossing DST transitions rather than changing the single-day scheduling/ranking system. See ARCHITECTURE.md for examples, default boundaries and limitations.

## October 21, 2026 — Task 33 missing-information handling

Keep pending clarification in page memory as the original grounded interpretation plus separate answers and reference clock. Reuse `/api/interpret`, Pydantic, Task 32 resolution and existing planner contracts instead of adding server storage or a chat framework. Continue simple answers deterministically with no additional AI call. Anchor relative-date meaning to the initial request and revalidate elapsed time before planning. Ask only for required location/group/event dates or an ambiguous supplied detail; optional caps and tastes can remain absent.

Preserve manual provenance and explicit constraints: manual edits win, follow-up corrections affect their named field, and auto display never becomes an override. Replace unclear activity occurrences in place; selecting among alternatives requires an explicit desired list. Keep unsupported requests separate from missing essentials and let valid infeasible requests reach the existing engine’s explanation. Abort/identity guards prevent duplicate or obsolete browser submissions; keep validated state for retry after service failure. This deliberately supports bounded follow-ups, with editing/canceling the original request available for complex changes. No persistence, general conversation engine, new model, dependency or infrastructure is justified for Task 33.

## October 21, 2026 — Task 33 required outing date and response speed

The owner intentionally requires a specific outing date for every finalized itinerary, including ordinary venues. Keep an undated internal candidate-analysis contract for compatibility, but require a dated public planning request and reject undated ranking/publication before candidate work. Continue using deterministic calendar resolution and existing pending answers; ask all missing essentials together, leaving caps, experience mode and exact starts optional. Do not invent dates or imply that an exact mock date verifies real hours/prices/availability. Flexible-date optimization remains future work.

Measured AI latency dominates (seconds), while date/validation/ranking take milliseconds. Reduce redundant prompt schema text and generation of absent optional JSON fields, restoring identical defaults with existing validation. Preserve required unknown core fields, every explicit constraint, schema types and provider replacement boundary. Strengthen budget-currency and total/per-leg examples and run actual-model semantic checks before accepting compact output. Avoid keyword preflight, new caching/conversation infrastructure, extra AI calls, background warming, tighter timeouts or planner rewrites: they are either unsafe for semantics or do not address the measured bottleneck.

Keep all scalar planning constraints present in the Ollama format, even when null, after expanded real-model checks exposed omission risk for group caps/currency. Compact only absent phrase arrays and unused AI clock fields. Normalize an unqualified explicit $ amount to USD only under the existing catalog policy after numeric grounding; retain rejection of explicitly different currencies. This avoids extra model calls or a false missing-currency question without inventing caps or converting currencies.


## October 21, 2026 — Task 34 trustworthy interpretation

Extend the existing Pydantic/source-grounding boundary, retaining one effective request and Task 32 calendar resolver. Replace loose budget-number membership with scope-specific evidence comparisons; add matching travel evidence and bounded conflict/unsupported-requirement checks. Keep minimum-spending requirements unsupported because the existing contract represents maximum caps. Use existing follow-up fields for essential ambiguity and existing edit/preferences recovery for unsupported caps. Do not add a new questionnaire, dependency, provider, retry or AI call.

Revalidate and copy provider instances before grounding: a replaceable adapter may return a mutated model, and validation must not mutate provider-owned state. Reject duplicate JSON keys rather than accepting whichever value happens to be last. Bound extraction strings/arrays while retaining the existing four-stop product explanation. Recheck date/window expiry at the planning API boundary with the same resolver, without changing scheduling calculations.

Real Qwen checks initially exposed an invented derived group budget, a total/per-leg swap and an invented spending mode; guards blocked them. Clarified the existing prompt/examples, including explicit zero caps. The stronger guards remain provider independent and do not silently repair these semantic mistakes. Finite actual-model samples and deterministic tests provide evidence, not a guarantee of exhaustive language understanding. Planner, catalog, ranking, routes and visual design are unchanged.

A paired timing check exposed avoidable generation of unused AI clock fields. Exclude those keys only from Ollama's output schema and serialize examples compactly; the provider-independent extraction contract and normalized result remain unchanged. Retain every actual planning scalar in the required output. Resolve only exact, grounded, matching cost-mode labels repeated as bare uncertainty; do not suppress real preference conflicts as absent budgets.


## October 22, 2026 — conservative missing-year dates

Resolve English named month/day dates in the existing Task 32 local calendar, accepting standard abbreviations and optional periods. A valid date today or later can use the reference year; a passed month/day must ask for a year, with no automatic next-year rollover. A year-only answer supplies that year for the saved unambiguous month/day and is revalidated (including leap days). Explicit past dates stay rejected. Use structured resolver reasons through the existing clarification fields so date/year/weekend/time questions and help match the actual problem. Preserve manual date priority and model-free continuation; add no date-parsing dependency, model arithmetic or extra AI call.


## October 23, 2026 — Task 39 cost safeguards before real providers

Lower actual project day/rate quotas using standard Cloud quota administration, which works without billing even when Maps-specific pages redirect to signup. Disable unused Places methods through zero daily quotas. Keep billing, trial enrollment, budget creation and credentials deferred at their explicit authorization/security boundaries. Document actual values separately from pricing allowances; neither rate quotas nor alerts promise a dollar ceiling.

Prepare one small process-local request-budget module using existing Pydantic/unittest and standard-library locking, with one instance owned by FastAPI. Lock mode to mock at configuration/startup; do not add a live enabling flag or speculative Google adapter. Count attempts before I/O, matrix elements as origins × destinations, failures without refunds and duplicate attempts without retries. Keep existing exhaustive fictional planning untouched. Restarts/multiple workers weaken session totals; deployment-wide accounting is future work. See [verified safeguards and blockers](docs/billing-safeguards.md).


## October 23, 2026 — Task 39 keyless local authentication

Use documented ADC service-account impersonation for the trusted local Python backend. A dedicated account gets a one-permission custom role (`serviceusage.services.use`), avoiding the extra inspection permissions of Service Usage Consumer; the owner gets Token Creator on that account only. No runtime Owner/Editor role, API key or downloadable service-account private key. Routes' documented `cloud-platform` scope is broad and not an API-key allowlist; minimal IAM, protected local source refresh credentials, existing quotas and the hard application live lock remain distinct controls. Credential/token issuance is verified through OAuth/IAM only; no Maps call or provider integration. Source user refresh credentials are reusable sensitive secrets despite short-lived target tokens.

Keep quota/application increases unapplied. Cloud quota metadata reports eligible/non-fixed limits while Console says Adjustable: No; exact discrepancy remains unresolved. Free Trial policy separately prohibits increase requests, and no bypass or paid upgrade is authorized. See [verified authentication and safeguards](docs/billing-safeguards.md).

## October 23, 2026 — Task 40 bounded development discovery

Use Text Search (New) alone for activity plus named destination or optional shared coordinates. Keep discovery behind a separate backend development command/switch; do not unlock generic provider mode or connect existing website requests before Task 46. Reuse the Task 39 budget mechanism and unchanged ceilings, the dedicated existing impersonated ADC identity and explicit quota project. Add official google-auth plus requests, without a Places SDK's retry behavior. Preserve IDs and minimal identity/location data in a discovery contract; leave normalized venue details to Task 41.

Require explicit location rather than inheriting the mock request's Baltimore default. Separate destination, current location, start and travel limits; destination wins. Named queries verify provider geographic components, conservatively excluding missing/mismatched neighborhoods. Coordinate searches use circle bias plus a local radius check, with no invented user radius/start/travel allowance. Name-only queries explicitly override server-IP bias with a nonlocal bias; Google's explicit geographic text takes precedence. No extra geocoding or Nearby calls are necessary. The first authorized live request exposed a method-specific 180-degree rectangle-width restriction that is stricter than the generic viewport documentation; corrected the request and regression check before the final successful verification. Exactly two attempts used; do not issue more under Task 40 authorization.

Request only the six documented fields listed in [venue discovery](docs/venue-discovery.md), triggering Text Search Pro; retain third-party attributions without a public UI or persistent cache. Public display/terms/privacy requirements must be met before frontend integration. These discovery candidates do not establish hours, events, prices, availability, convenient clusters or travel feasibility.

## October 24, 2026 — Task 41 physical-place normalization

Keep a canonical physical-place facts contract distinct from the existing planner/session contracts: Google can identify a concert building without supplying a dated performance. Reuse shared identity/category/scalar/coordinate validation instead of weakening event validation or inventing session data. Provide pure Google normalization and a bridge from the unchanged Task 40 transport DTO; no planner wiring before Task 46. Field selection stays entirely outside normalization, with the existing six-field Pro mask unchanged.

Parse optional Enterprise details from synthetic responses, keeping missing values null and source facts distinct from derived category/receipt timestamps and fictional fixture evidence. Reject malformed supported fields safely and isolate invalid batch entries; preserve ordering and duplicates for Task 42. Allow optional in-memory partial updates by identical provider/Place ID/category, retaining absent facts and credits with field observation times. Retain nested missing values with observation times per scalar/list path; replace complete period lists as units rather than combining periods from different fetches. A new open-now observation does not refresh older hours. This prepares later selective enrichment without implementing a network pipeline or increasing costs. Keep all provider content transient; normalization does not remove Google storage/display restrictions. See [mapping, pricing and policy review](docs/venue-discovery.md).

## October 24, 2026 — Task 42 conservative candidate evidence

Use pure canonical candidate checks after existing geographic validation/normalization, outside Google authentication/transport. Reuse Task 41 facts, receipt-aware merge primitives and the existing category enum. Group original provider IDs first; different IDs need pairwise exact full names/addresses, points within 10 meters and identical venue-specific website paths. Missing corroboration retains possible duplicates, especially same-brand concessions/cinemas in complexes. Today's mask omits websites, so cross-ID merges are deliberately limited to richer already-supplied/offline evidence, without buying details. Preserve every source ID/credit, combine known optional facts without null erasure, and keep multiple requested activity associations on one physical venue. Preserve original provider order while choosing group identity/facts deterministically.

Specific provider types support stronger relevance; missing types/opaque names remain uncertain. Names alone never prove activity support. Reject affirmative service-business mismatches and selected incompatible facility evidence, without assuming broad parks/stadiums/theaters establish specific facilities or scheduled events. Add optional primary-type normalization but no requested API fields. Retain strict destination components and explicit radius checks, rejecting county-only city matches; do not invent polygons, city-center travel caps or driving times. Keep safe reason counts development-only, with no payload/location logs, AI calls, refills, fictional substitutes or planner/routing integration. See [full rules and limits](docs/venue-discovery.md#task-42-deduplication-and-relevance--october-24-2026).

## October 24, 2026 — Task 43 bounded routing evidence

Implement a small backend-only route-calculation protocol outside the fictional planner. Reuse canonical coordinates/Google IDs, existing impersonated ADC/token handling and shared budgets; no SDK or new dependency is needed. Restrict driving to TRAFFIC_UNAWARE and walking to its supported basic request, with Google's six necessary matrix fields. This qualifies for Compute Route Matrix Essentials and avoids traffic/premium costs. Preserve directionality, fractional seconds and unknown failures instead of estimating from straight-line distances.

Compute the union of required adjacent-activity directed pairs once per outing, plus only an explicitly authorized starting point. Use deterministic rectangles containing exclusively required pairs, deduplicate identical waypoints, and locally label same-venue transitions. Do not implement a complex general matrix optimizer. Atomically reserve all planned matrices before any external work so an over-budget outing cannot buy partial evidence. Keep conservative reservations after early failure rather than refunding unsent work or enabling retry loops. Add a local rolling-minute admission check matching the existing 60-element cloud quota while retaining every existing configured ceiling. Process counters do not establish remaining account-wide daily quota or a hard dollar cap.

Handle provider results by explicit indices and documented proto3 scalar defaults; never infer association from array order or turn missing durations/routes into zero. Keep valid siblings on per-element failure; stop further matrices on whole-request/structural failure and expose safe not_requested states. Use a separate disabled-by-default development gate with no public endpoint/startup activation. Task 43 authorizes implementation/offline tests only, not live Google requests. [Detailed interface, official sources and limitations](docs/route-calculator.md).


## October 24, 2026 — development spending target and Task 43 verification allowance

The owner sets a $40–$50/month development API planning target and accepts reasonable controlled spending for authorized tests. Do not treat development as subject to a blanket zero-spend requirement or re-request permission for trivial costs already inside an approved test. Preserve alerts, efficient bounded requests, provider storage rules, default-disabled live operation and separate approval for major quota increases, substantial recurring costs or billing-plan changes. The Free Trial must not be upgraded without explicit approval. This target does not change any actual quota, alert or application ceiling.

The initial one-request/two-element bidirectional proposal was stopped offline: both directions in one Cartesian matrix require four cells. The updated explicit authorization permits exactly one 2×2 driving matrix (including self-pairs), at most four elements and no retry/additional provider request. Use existing matrix-body/transport/parser and shared outing reservation directly for this verification, because normal calculator batching correctly removes self-pairs and would split the two meaningful directions into two requests. No application code change is needed. [Verification ledger](docs/route-calculator.md#authorized-live-verification--october-24-2026).

## October 24, 2026 — Task 44 conservative provider feasibility

Keep feasibility pure and isolated, consuming supplied facts/routes/scheduled instants rather than calling providers or replacing the fictional planner. Reuse provider contracts and existing event categories, leaving the Task 27 evaluator intact because its fictional quotes and single-day windows cannot safely represent these facts. Preserve a three-state outcome with proven violations taking precedence, stable provisional retention and no preference/ranking override.

Retain exact protobuf duration nanos in an additive route field; compare seconds against decimal minute caps without rounding. Match direction/mode, check transfer gaps and total known lower bounds, and keep the authorized first leg separate. No starting point means no first-leg obligation. Missing routes never imply zero.

Use complete applicable dated current hours to prove coverage/conflicts. Require the original venue-local request date alongside its specific normalized periods receipt: receipt can cross midnight and is not request context. Restrict to snapshots received on the evaluation's local date, within the provider's seven-day request window, without guessing truncated/undated/DST-ambiguous boundaries. Keep regular weekly hours provisional rather than assuming no holidays. Preserve movie/event session uncertainty independently from building hours. These conservative limits intentionally retain some potentially infeasible candidates as unverified. No expensive field acquisition, live request, dependency, frontend integration or Task 45/46 work. [Full contract and limits](docs/feasibility.md).


## October 24, 2026 — Task 45: field evidence as an additive display contract

Keep original provider/planner models compatible and generate transient labels through pure adapters. Separate source identity, evidence certainty and supplied/computed/missing basis; do not add a venue-wide verified flag or confidence score. Nested receipts remain field-specific. Merged observations retain contributing original Place IDs. Enterprise-style optional data can use the same contract without requesting it now.

Reuse Task 44 results for scoped constraint messages; do not introduce a second feasibility evaluator or imply that travel/hours checks verify prices/bookings. Keep provider-calculated routes estimated and time-sensitive facts provisional. Missing price/session/inventory evidence stays unknown or requires confirmation. Carry explicit Google Maps/third-party attribution requirements and supplied or officially documented links for Task 46, preserving all retention and disabled-default safeguards. No UI/planner integration in Task 45. See docs/evidence-labeling.md.


## October 25, 2026 — Task 46 real-data integration

Connect the existing candidate walker, evaluator and scoring/diversity selection to normalized Google physical venues and Task 43 route evidence. Keep Task 44 exact travel/uncertainty decisions and Task 45 labels; do not rewrite the fictional planner or invent a separate generator. An explicit provider-ID bridge represents event buildings without relaxing ScheduledEvent session validation. Real results remain provisional while current minimal Pro discovery lacks prices, hours, duration, capacity and session inventory. Hard budgets are retained but explicitly unverified.

Use backend configuration plus a local development opt-in, refusing production/known hosting environments. Preserve mock default and explain provider failure rather than mixing/falling back. Maintain existing Cloud/application ceilings; add only a lower six-Details sublimit under the existing total-request budget. Preserve exact directional seconds for hard travel caps and use safe lower-bound whole minutes in shared time-window prechecks; round up only display quotes.

Starting location is a separate transient authorized point. Device permission happens only on explicit button selection; an explicit destination wins. Manual city/neighborhood discovery remains available when permission fails; first-stop routing requires a real selected point, never an inferred city center. Keep the current explicit unknown-timezone calendar notice beyond supported Baltimore/Washington, DC and publish no invented visit schedule.

Fetch contacts only on an explicit View details action, behind a separate disabled-default Enterprise opt-in. Use existing impersonated ADC, a minimal explicit GET field mask, original Google IDs and the original outing budget. Keep only an active rendered-response promise in page memory; no persistent provider cache. Safe links, missing-data labels and retained credits are required. Zero live Details calls are authorized for this milestone.

The first bounded live browser run exposed legacy simulated-travel summary wording and a generic food query that could surface a daytime café for dinner. Make the summary mode-aware and use a dinner-specific search query without buying extra fields or inferring hours. Recheck offline before a second bounded verification; combine both runs against the same four-search/27-element authorization. This is explicit verification of a code correction, not an automatic retry/refill mechanism. [Details and ledger](docs/real-planning.md).

## October 25, 2026 — Task 46 post-integration stabilization

Fix the qualified weekday/calendar-date conflict in the deterministic resolver rather than altering AI extraction or discarding the weekday. Reject disagreements, preserve explicit years/manual priority and keep the exact manual-test prompt as a full-pipeline regression.

Expose real ranking basis through actual venue names, known inter-stop estimates and an explicit absence of price/rating evidence. Keep shared venues where whole combinations differ, adapt diversity to the positions that can vary, reject duplicate full outings, and prepare at most six extra already evaluated combinations for a no-request Show different options action. Do not increase searches/candidates/routes or refill automatically. Use existing local Lucide symbols and stop names, not venue photographs or new licensed assets.

Replace coordinate entry with natural starting-place text and an explicit unavailable state. Unresolved manual origins block provider work rather than being silently ignored or treated as city centers. Recommend a separately authorized Geocoding API/precision-aware confirmation flow for addresses and ZIPs; named places could use existing Text Search but still need request accounting and disambiguation. No new billable transport, Cloud configuration, credential, quota or live API request is added in this pass. Keep approximately $40–$50/month target, mock default and Task 47 boundary.


Task 46 headline refinement: derive real titles from the selected records, using full pairs for two stops and bounded ordered name highlights for three/four. Expand colliding abbreviations and use supplied addresses for same-name disambiguation. Keep full names in the existing details/tooltip and constrain only the rendered heading to three lines. Use request-grounded dinner/category eyebrows, keeping provisional status in a separate badge. Preserve existing mock recommendation copy and all provider/request limits; this is presentation, not a ranking/provider change.


## October 26, 2026 — consolidated Task 46 quality and cost controls

Discover ten relevant venues with one bounded search/category and Pro type evidence; shortlist using whole-sequence geographic costs before the existing directed matrix/evaluator/ranking flow. Route only missing required pairs on one bounded expansion, retaining outing/process budgets and seen combinations in a ten-minute active-computation continuation; no cross-outing cache or budget refill. Approved limits are 150/outing and 1,500/process matrix elements; Cloud 2,000/day and 150/minute. Preserve unrelated limits, zero retries, mock default, production refusal and billing/security setup.

Optional rating/count fields in the existing searches are cheaper at the Enterprise incremental rate than separate shortlisted-venue Details enrichment. Extend existing quality scoring with a disclosed 50-rating/3.5 prior; ratings cannot establish hard feasibility. Contacts remain on demand behind the existing gate/six-Details sublimit. Resolve manual origins with already-enabled Places Text Search Pro and explicit match/precision confirmation instead of enabling Geocoding or adding keys/permissions. Geocoding v4 OAuth is a later alternative requiring separate approval if Places coverage proves inadequate.

Hide unsupported optional real-card rows while retaining structured uncertainty and critical budget/route/event/dinner/known-failure warnings. Record deferred evidence instead of treating absence as $0 or confirmation. The original Pinstripes trace was not retained: report demonstrated selection weaknesses without inventing one historical cause. All new provider behavior is fixture-tested with no billable live verification in this pass. Task 47 remains unstarted.

## Task 46 manual acceptance — bounded diversity and explicit origin preparation

Keep ten retained relevant venues/category and all current quotas/budgets. A distinct explicit Search for more venues action may refine sparse discovery once, at most two queries inside the original four-search ceiling, without widening geography. Show different options itself reuses checked coverage/staged routes. Preserve existing IDs/queued options/seen combinations and original contact/route budgets; aggregate stage counts explain real coverage instead of promising 10–15 clicks in every city. Pagination, broader areas or larger limits need measured evidence and separate decisions.

Prepare unconfirmed manual origins on an explicit plan submission, require even a single match to be confirmed, and resume that pending request. Cancel on edits/failures; preserve destination precedence and precision consent. Keep strict travel operators as additive flags evaluated with exact route duration, independent from total and first-leg scope. Clear only independently grounded verbatim cap labels or null optional schema labels from model uncertainties; missing/mismatched extracted hard constraints remain blocking. No Task 47 work or live Google calls.

## October 26, 2026 — Task 46 application expansion

Use approved 10-search/20-candidate/300-element ceilings through existing validated settings; initial ten-result pages and 6/4/4 shortlists remain economical. Explicit pagination/refinement preserves the destination and original budget. Staged geographic routing checks only unsent pairs, with atomic reservation, a 64-element stage bound and unchanged 150/minute and 1,500/process limits. Keep unused contact headroom by modestly raising the total outing attempt limit from 20 to 30 (ten searches + six Details + fourteen matrix requests); process attempts stay 50. An unsent local minute pause permits a later deliberate action, never a provider retry or new budget. No Cloud/billing changes, live Google calls, new dependencies or Task 47 work.

## October 26, 2026 — Task 46 bowling coverage diagnosis

Keep the initial strict bowling-type query; make only the explicit same-area alternative an unfiltered bowling text query, requiring affirmative type/name evidence through existing quality assessment. Preserve uncertain name evidence as provisional, reject unsupported generic centers/arcades, and retain provider IDs. Trigger a bounded shortlist expansion for insufficient primary-venue coverage even when restaurant substitutions already yield three plans. Keep existing ranking weights/tolerance and all budgets/tiers/geography unchanged. Expose aggregate coverage, rejection, route and ranking counts in existing results notes, without private inputs or identifiers. Historical DC causes remain unproven; any live diagnostic requires separate authorization.

## October 26, 2026 — local development exploration within Task 46

Keep the six original safe-mode ceilings; replace only their exploration enforcement with finite user-action batches plus a persistent $10/local-day gross estimate guard. Preserve separate provider/tier gates, exact constraints, explicit geography, zero retries, concurrency one and Cloud settings. Use integer micro-USD and a private content-free locked/fsynced file, with failures conservatively charged and measured dispatches reported separately. Fail closed on accounting errors and nonlocal/hosted use, carrying original host/origin through Next proxies. Do not treat estimated allowance as Cloud billing or a monthly cap. Retain transient evidence/continuation capabilities; do not introduce a database, background exploration, location-first redesign, landmark suggestions, geographic broadening or Task 47 work.

## October 27, 2026 — Task 46 location-first extension

Keep the shared planner/evaluator/ranker; add spatial discovery and a bounded route-evidence beam rather than an independent optimizer. Retain multiple geographically separated anchors, per-position identity sets (including repeated categories), previously shown complete IDs and cumulative outing budgets. Frontiers/96-path beams limit computation, not exploration retention. Public references use provider-supported public types and finite route/proximity comparison, never AI-generated coordinates or a guessed city center. Confirmation is mandatory; unknown user city stays unknown and optional origin-free planning remains available.

First-stop minutes/miles use route evidence and scoped strict/inclusive comparisons. Flexible expansion has small documented bands and a per-action stopping rule; hard geographic/travel requirements never expand. Ordinary destination wording becomes a preference only in the new spatial path; explicit membership/exclusions remain address-evidence checks. Preserve default mock, separate optional gates, existing exploration ledger/concurrency/zero retries and Cloud configuration. Test with invented providers only; defer real coverage/accessibility/polygon accuracy to separately authorized verification/future work. No Task 47.

## October 27, 2026 — Task 46 acceptance supersession

Require confirmed/selected origins for every published outing, including explicitly fictional mock references; remove optional-origin UI/fallback and visible meters-radius state while preserving internal hard radius validation. User-edited first preferences supersede extraction; unedited under/at-most semantics remain exact. Replace staged widening with one inclusive doubled Flexible maximum, applied immediately across discovery/reference scoring/feasibility/continuation; preserve original range as a modest ranking preference. Derive public-reference regions from actual activity candidates, with measured pool overlap/travel explanations rather than randomness or a fixed central list. Preserve checked onward seed associations.

Cloud metrics established Places daily exhaustion; raise only the existing SearchText daily override 40→200 under the owner's authorization and confirm asynchronously by read-back. Leave Routes at 2,000/day because no route-daily failure was evidenced; 10,000/day remains unapplied. Minute, Details, billing, IAM/credentials and estimate guard unchanged. Do not infer daily/minute causes from generic Google errors. No live billable verification or Task 47 work.

## October 27, 2026 — Surprise Me supersedes suggested-origin UI

A valid beginning is either a confirmed origin or, in explicit Surprise Me mode, the first selected activity venue. Do not fabricate or require a landmark/origin for Surprise Me. Keep origin-specific preferences inactive in that mode; an explicit source constraint needs an affirmative removal or a location-based method. Keep first/between/total scopes separate and exact. Deliberate Flexible between legs uses the same inclusive 2× rule.

Reuse sequential discovery, selective routing and the existing beam/evaluator/ranker. Add quality-qualified weighted sampling with SystemRandom and controlled test seeds, not AI-invented randomness or shuffled repeats. Known ratings below 3 with at least 10 ratings exclude a Surprise path; unknown/low-count quality remains unverified, not fabricated. Favor unseen primary IDs and different venue regions among suitably ranked eligible options; expose necessary repeats honestly.

Use page-memory-only first Place IDs (120 entries,10 minutes) as bounded hints across new outings, consistent with Google's ID caching exception. No durable storage, fingerprint, cross-user history, raw responses, reviews, contact information or personal coordinates. Existing 10 minute active computation sessions retain per-activity IDs and full seen signatures. Preserve cost controls and unchanged quotas; zero live provider calls for this implementation. Task 47 remains pending.


## October 28, 2026 — comprehensive discovery acceptance

Repair the demonstrated healthy-ledger nested-lock defect without resetting accounting. Hold locks only around durable counter transitions, bound local contention and keep invalid storage fail-closed. Distinguish no field returned from no provider admission; only an explicit unsent contact action can recover without violating no-retry semantics.

Use absolute real evidence scales so tiny within-pool differences cannot crowd out competitive primaries. Preserve shared planner/beam, hard constraints and source truth. Publish/record only actual cards, separate combinations from discovery, and explore provider-backed regional tiles after pages/strategies with finite per-action work. Twenty-driving/fifteen-walking minute defaults guide search only; changing any explicit strict/2× maximum still requires the user. Do not attribute historical Manhattan/Jersey City repetition to a single cause without traces. No Cloud changes, paid requests, durable provider storage or Task 47 work.

## October 28, 2026 — Task 46 discovery and browsing

Separate 100-per-distinct-activity inventory retention from finite search/route work. Preserve exact original requirements while permitting clearly separated evidence-backed travel-violating alternatives for display. Hard geography, safety, prohibited activities and known required-access incompatibility stay excluded. Unknown accessibility stays unknown; no enrichment/tier change.

Favor all-stop coverage within a quality band, using novelty-aware randomness only in Surprise Me. Store immutable three-card page history in browser memory with separate latest capability. Arrows never generate provider work. Preserve ten-minute server no-repeat scope and disclose reload/expiry limits instead of durable Google-content storage.

Retain 150-element rolling-minute protection because no evidence places it below the last verified Cloud limit. Consult shared-ledger capacity, use short cancellable pre-dispatch waits, and preserve unsent frontiers. No quota changes; mock defaults, optional gates and $10/day estimate guard remain.

## October 28, 2026 — geographic recovery and outing validity

Treat ordinary neighborhood wording as prioritization around a compatible, confirmed reference, with an explicit approximation warning; require actual component/boundary evidence for hard geography. Unresolved names need destination correction or deliberate anchor consent, never a manufactured origin or a quota retry. Near-current search geography is separate from a manual route origin. Keep the resolved local date and explicit-time provenance separate from the ten-minute search capability. A default earliest start is planning context, not an appointment. Preserve saved pages on expiry and require explicit date correction. Retain disclosed bounded timezone support rather than adding paid enrichment or inventing global location resolution.

## October 28, 2026 — owner-authorized exploration and activity contract

In explicitly local real exploration, make estimated-cost totals informational rather than admission caps while retaining durable accounting, fail-closed integrity, zero retries, finite work and verified project minute quotas. Cloud read-back confirms 150 route elements/minute; do not substitute the published 3,000 default. Remove only the exploration manual-lookup lifetime ceiling in addition to the already uncapped outing/process work totals. Keep normal behavior intact.

Extend canonical activity contracts with bounded source-grounded custom intents instead of another whitelist or a second planner. Require actual relevance evidence; finding venues does not verify sessions or bookings. Remove participant counts from current interpretation, ranking/capacity decisions, identity and UI. Preserve optional legacy schema fields for future genuinely group-aware features; group-total financial limits remain unverified rather than fabricated from an invented count.

## October 30, 2026 — strict-first recommendation visibility

Require deliberate beyond-limit consent before revealing verified Strict/effective Flexible travel violations. Retain broad inventories and exact original constraints; discovery expansion never modifies eligibility. Prefer useful nearby evidence before city-scale text/rating prominence, while preserving multi-path and all-stop diversity. Keep model interpretation separate from provider coverage; do not buy a new model or provider to repair routing/visibility bugs. Remove unsupported numeric spending UI rather than implying reliable real prices; retain legacy fields and explicit uncertainty. Research alternatives without activating them. Task 47 remains unstarted.

## October 30, 2026 — owner-approved pre-launch roadmap amendment

Use TASKS.md as the living official roadmap, retaining docs/original-roadmap.docx as the unchanged original baseline. Insert pending Tasks 50A–50E after database/security Tasks 47–50 and before deployment Tasks 51–55, without renumbering any of the 135 original tasks. The public Stage 1 checkpoint now includes mixed mandatory/flexible journeys, ordering, optional returns, complete-journey deadlines and saved plans. Task 48 anticipates extensibility without speculative schema or planner work. Stage 2/3 retain their broader optimization/editing scopes. This is planning approval only: no Supabase project, database schema, application behavior or new task implementation is created; Task 47 remains pending and unstarted.


## October 30, 2026 — Task 47 preparation, no runtime database dependency

Choose the Supabase shared session pooler on 5432 for the isolated local FastAPI/PostgreSQL readiness check, avoiding direct IPv6 requirements or a paid IPv4 add-on. Require hostname/CA verification, read-only SQL, explicit invocation and safe fixed output. Use pinned Psycopg with bundled libpq to avoid system build/tool installation; no Supabase SDK, ORM, migrations or persistent pool is justified yet. Keep backend-only credentials in an ignored local env file, separate from Google/Ollama and frontend configuration. Production connection choice and least-privilege runtime credentials depend on future hosting/schema work. Owner project creation, Free organization/region confirmation and real connectivity are pending; Task 47 cannot be complete yet. Task 48 and 50A–50E remain unstarted.


## October 30, 2026 — Task 47 hosted verification accepted

The owner-created `whereto` project in `Where To` (Free), North Virginia (`us-east-1`), passed actual authenticated read-only PostgreSQL verification through the shared session pooler on port 5432. Keep the existing CLI-only check, explicit CA/hostname verification and database-independent mock startup. Task 47 is complete; no application schema, migrations, persistent pool or saved-plan API is introduced. Task 48 and 50A–50E remain unstarted and require separate task scope.


## October 30, 2026 — Task 48 private schema and identifier-only retention

Use explicit SQL migrations through the existing Psycopg driver, with an atomic checksum ledger and transaction-scoped advisory lock. Rehearse with rollback, reject drift/unknown history, then verify using a separate read-only connection. No ORM, new dependency, reset or automatic startup migration is justified. Keep the five product tables in private `whereto`, owned by the administrative migration role; revoke schema/table access from PUBLIC and Supabase API roles, enable/force RLS without permissive policies, preserve verified TLS and disabled Data API. Creating a runtime login or public ownership policy before the save/access contract exists would be premature; those remain Task 49/50 work.

Normalize relationships/order/common constraints; retain only the current grounded activity-intent map as JSONB. Do not restore party-size/numeric-budget requirements or store whole response/session blobs. Preserve UUID stop identities, unbounded ordinal positions, optional timing and source-kind distinctions for future additive 50A–50E migrations; defer unsupported dependency/endpoint/return/deadline logic. Cross-row completeness and updated-at mutation belong to the future transaction writer, not premature triggers.

Official Google Places/Routes policies permit indefinite Place ID storage, not general permanent content caching. Choose identifier-only source records, omitting even temporarily cacheable coordinates to avoid expiration/backup lifecycle machinery. Other providers can record neutral provenance; external IDs require reviewed permissions before expanding the database allowlist. Real generated descriptions, scores, route metrics and display snapshots must not be copied into user-owned columns to bypass retention limits. Task 49 must explicitly design data refresh/attribution and unavailable-provider behavior. This intentionally sacrifices exact real-response round trips. [Mapping, official terms, commands and limitations](docs/database-schema.md). The actual hosted additive migration and read-only verification passed; no application rows remain. Tasks 49, 50 and 50A–50E are unstarted.


## October 30, 2026 — Task 49 immutable anonymous saved plans

Use server-issued ten-minute receipts rather than trusting a browser's full ranked
response. Minimize at issuance; save at most three explicitly selected ordered
options with one selected itinerary, in one transaction. Map normalized constraints
to named columns and retain only allowlisted missing legacy preferences. Preserve
fictional snapshots, but never Google details/metrics/derived ranking or geography
claims. Reopen a separate honest saved representation without re-generation or
provider I/O. Exact origins remain transient and are labeled unavailable.

Use independent 256-bit server-generated read capabilities with SHA-256 verifiers,
30-day access expiry and fragment links imported/cleared by the browser. Immutable
saves need no update/delete privilege. Advisory serialization plus a unique verifier
and document fingerprint makes same-capability retries idempotent. Create a separate
non-owner LOGIN with only USAGE/SELECT/INSERT and forced RLS traversing to the
transaction-local access hash. Administrative credentials are refused at runtime;
only the migration administrator may SET ROLE to the restricted role for tests.
Migration 0002 adds these scoped permissions/columns; Task 48 SQL stays unchanged.

Limit routes to loopback/same-origin development and bound streams/connections/timeouts.
No public list or UUID access. Explicit localStorage retention supports refresh;
shared links, XSS/extensions, history/clipboard syncing and absent revocation/purge
remain limitations. Do not call this authentication. Task 50 retains public security,
accounts/ownership, revoke/rotate, cleanup/retention and distributed abuse protection;
50A–50E retain advanced journey work. [Details](docs/saved-plans.md).


## Tasks 46/49 acceptance corrections

Keep the administrator refusal and capability-scoped RLS. Resolve the owner's
startup mismatch by safely reading the existing restricted runtime configuration
when administrator variables are loaded, never by using a privileged runtime
connection or broadening SQL grants. Honor explicit restricted environments and
fail closed on malformed/insecure private files. Preserve ordinary unconfigured
mock startup and all real-mode flags.

Accept the exact IPv4-mapped loopback address added by Next; keep public forwarding
blocked. Distinguish safe error categories/reference IDs from raw provider/driver
content. Preserve specific local quota-recovery messages. Do not change itinerary
minimums: the engine already supports one stop. Add exact cinema aliases before
ambiguity checks, not an alternate interpreter. Publish private links only after
confirmed commit; handle same-tab fragment imports and clearly identify the last
confirmed saved link. No new migration or Task 50/50A–50E implementation.


## Tasks 46/49 acceptance refinements

Keep Google IDs as the persistent identity, and retrieve permitted current details only on explicit action. Retain user-authored intent without turning it into provider truth. Reuse the existing Details service with a lower Pro mask and conservative existing cost accounting; do not activate new services. Brand identity is hard, retail format soft unless explicitly mandatory; proximity never proves tenancy. Include full verified outbound journey in ranking, retain finite search/routing and diversity. Local profile parsing is data-only, restricted-identity and CI/production guarded. Keep raw counters out of product views; unknown destination calendars need clarification rather than a verified-UTC claim.

[Details](docs/acceptance-refinements.md).


## November 1 — final Tasks 46/49 acceptance repair

Current behavior supersedes earlier automatic/all-option saved-view descriptions: normal visits keep saved links collapsed, explicit private links render only the selected detailed itinerary, and Open saved plan opens a secure new tab. One explicit selected-stop detail load uses the existing Pro mask with Maps URI; optional phone/website fields require deliberate existing Enterprise contact opt-in. Provider content stays in memory. Structured continuation states distinguish combinations, discovery, bounded exhaustion, limits, constraints and pending routes; ranking is preserved. Actual default-port startup was checked, and occupied backend ports now give actionable guidance. No migration, role/RLS/TLS/quota change or later task. See [the final repair report](docs/final-acceptance49.md) and the latest HANDOVER.md evidence.

## November 1, 2026 — explicit saved-open approval and measured AI preparation

Keep permanent Google content out of SQL/browser storage. Existing server Details
can legally populate current selected stops, but manual authorization does not
authorize billing on every saved navigation. Add a separate default-off local
automatic-open flag; do not enable it in the owner's profile without separate
approval. Do not adopt UI Kit/Maps JavaScript/new browser credentials or paid SKUs.

Keep six-attempt capability sessions and shared minute/Cloud/accounting limits.
Expose their distinct causes; prevent replay of a partially failed UUID from
dispatching remaining stops. Failed pre-admission remains uncharged. Do not reset
usage to recover. Historical generic errors cannot identify a Cloud failure.

Measured cold Qwen extraction was 12.9s versus 3.65s warm. One local background
prompt preparation reduced the first post-readiness extraction to 4.10s; it moves
11.3s preparation to startup and does not accelerate warm inference. Keep the
existing model/schema/source safeguards rather than add a keyword interpreter.
Keep finite ten-minute residency, existing 8,192 context and concurrency-one
provider admission. [Evidence/limitations](docs/saved-details-performance49.md).

## November 1 — separate capability access from shared provider admission

A sharing capability must not accumulate a permanent six-request Details bottleneck. Use bounded explicit selected-stop actions and hashed UUID replay metadata while preserving shared minute/concurrency/ledger/Cloud protection. Do not cache restricted content across viewers or promise simultaneous ten-friend enrichment under ten/minute and concurrency one. Keep automatic Pro local-only and Enterprise contacts explicit. Accept validated provider-returned HTTP/HTTPS external official-site links independently of phones; do not infer websites. Move raw development data to a server-protected local route, and derive user activity help from the shared registry. Deduplicate presentation only, preserving hard constraints and ranking. [Evidence and limitations](docs/sharing-ux49.md).

## November 2 — expose existing walking routing without redesigning planning

Reuse the existing transport field, route adapter and SQL column. Explicit mode controls do not rely on a model guess; clear source intent and manual selection must agree. Driving defaults only when no applicable mode is provided. Keep legacy internal data readable and never relabel another saved preference as driving. Mode-specific evidence, immutable session scope and request hashing preserve cache separation. Keep basic Matrix billing/masks/quotas and one required walking beta notice; no speculative second-mode calls. Replace technical product copy with a dedicated user guide, honest result labels and readable policies; preserve substantive privacy/security disclosures.

[Acceptance details and evidence](docs/ui-travel-mode49.md).

## November 2 — regeneration and hours preparation acceptance

A shared provider minute denial is not a provider outage. Preserve admission/ledger limits and repair classification rather than resetting quotas or using refresh as recovery. Keep current editor values authoritative. Present default planning windows as defaults, not promised arrival times. Prepare selected-only hours verification offline; separately authorized contact fields do not authorize hours. See [acceptance record](docs/regeneration-hours49.md).

## November 2 — Text Search hours and capacity acceptance

Use the existing Text Search response for hours rather than per-candidate Details fan-out. The owner separately approved manual selected-only saved Details Enterprise hours; automatic opens remain Pro. Distinguish current dated, typical weekly and unknown hours; no invented arrival/duration or holiday certainty. Do not raise local limits that mirror Cloud capacity; owner exploration already removes cumulative prototype caps. Record tester costs before proposing any Cloud/budget increase. See [acceptance and capacity report](docs/hours-capacity49.md).

## November 2 — development lifecycle repair

Treat a live repository server as an existing instance, not an orphan merely because two processes share its socket. Supervise development runtimes through IPC lifetime ownership and bounded group cleanup; never infer kill authority from a port, process name or stale PID file. Keep3000/8000 fixed and preserve native reload. See [verification](docs/dev-lifecycle.md).


## Task 50 — preserve anonymous capabilities and strengthen existing boundaries

Retain separate runtime credentials, parameterized atomic immutable saves, SHA-256 capability
verification, 30-day RLS expiry and fresh verified-TLS connections. Concrete validation/error gaps
are application changes; no migration or grant change is justified. Reject ambiguous JSON and
malformed persisted provider references, and prevent accidental Next public database configuration.
Do not add blind database retries: commit outcome can be uncertain; the same capability/fingerprint
provides existing idempotency. Supavisor protocol metadata is not PostgreSQL session identity.
The historical intermittent connection error remains unexplained; deterministic interruption and
fresh connection/restart checks provide current evidence. Keep accounts, revocation, deployment
and Tasks 50A–50E/51 outside scope. [Audit](docs/database-security.md).

## Task 50A — preserve semantics before advanced execution

Extend the existing interpreter with one optional typed journey object instead
of a second parser. Source order and explicit order edges are distinct. Missing
legacy objects retain existing simple-request semantics; the current Qwen schema
requires the object so important requirements cannot be skipped as optional output.
Keep original references/clauses, verify structured meanings, and block execution
when required capabilities are absent. Home does not mean origin without explicit
evidence. No provider lookup, routing optimization, feasibility claim, database
migration or persistence expansion is justified here. [Contract and limits](docs/complex-interpretation.md).

## Task 50B — identity evidence before routing

Extend the existing Text Search adapter and canonical venue pipeline rather than
adding a Google integration or asking Qwen to assert venue identity. Require literal
normalized identity, relevant types and branch/location evidence; preserve unresolved
states for aliases and incomplete evidence. Keep exact identity separate from generic
activity eligibility. Require provider-directed containment joined to verified mall
IDs. No proximity-based tenant claims, quotas/tier changes or Details fan-out.

Keep resolution behind a separate backend development/test gate until the routing/
feasibility/integration tasks can honor every constraint. Add honest advanced-status
copy and field-only home follow-ups now: explicit origin confirmation or a location
still needing verification, never inferred home. Preserve the source-grounded Journey
and put answers in transient context. Named ambiguity choices are backend-only for
now, context-bound and expiring; no new public selection route or persistent provider
cache. [Evidence, costs and remaining limits](docs/stop-resolution.md).


## Task 50C — bounded topology over existing route evidence

Consume the server resolver, not client-supplied resolved places. Reuse its outing
budget, authorization/expiry, canonical evidence and exact Matrix batching/transport.
Add a selective directed-pair input to the same calculator so returns and partial
orders do not require an independent provider integration. Keep the ordinary linear
planner and its scoring weights unchanged.

Use at most four occurrences, four shortlisted candidates/occurrence, a 24-path
precedence-aware beam and 27 directed pairs per active computation. Geographic gaps
prune only; verified directional seconds rank routes. Transitive precedence survives
optional omissions. Required identity, final topology and nullable unknown totals
are validated; optional omission and beyond-limit exceptions remain explicit.
Extend the advanced interpretation context only enough to retain existing per-leg
and total-between travel caps/exclusivity. Reuse the source grammar and manual
total-travel precedence; keep these sums separate from whole-trip timing.

A confirmed origin has a private routing alias and coarse confirmation metadata;
no coordinates/address or private Place ID enter returned origin evidence. Keep
original interpretation context internally, excluded from serialization. Retain
canonical hours; only existing conservative current-date closure excludes venues.
No assumed start/arrival, whole-trip duration/deadline arithmetic or feasibility
claim. Reuse existing development gates, add no public endpoint/production flag or
persistence schema. [Detailed rationale, costs and limitations](docs/advanced-routing.md).
