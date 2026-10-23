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
