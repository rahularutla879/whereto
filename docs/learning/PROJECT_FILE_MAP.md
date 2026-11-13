# Project file map

Verified source/test inventory at initial baseline `a7ed106`, reconciled with independent offline V5 commit `b1efe96`, November 10, 2026. Important files are explained first; the full symbol index below records **460** source/test files. Symbols are statically read declarations, not an execution trace. No secret/profile/dependency-directory inventory is published.

## Repository-level guides and configuration

- [README.md](../../README.md) — Beginner startup and current/historical product notes.
- [AGENTS.md](../../AGENTS.md) — Development rules and installed Next.js documentation requirement.
- [CONSTRAINTS.md](../../CONSTRAINTS.md) — Safeguards, approved scopes and dated superseding limits.
- [HANDOVER.md](../../HANDOVER.md) — Newest checkpoint first, historical evidence underneath.
- [TASKS.md](../../TASKS.md) — Official roadmap and historical implementation tracker.
- [DECISIONS.md](../../DECISIONS.md) — Why architectural/behavior choices were made; read latest entries in context.
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — Architecture timeline; older planned headings may be superseded.
- [package.json](../../package.json) — Node dependency ranges and named commands.
- [package-lock.json](../../package-lock.json) — Resolved Node package dependency graph.
- [backend/requirements.txt](../../backend/requirements.txt) — Pinned Python dependencies.
- [next.config.ts](../../next.config.ts) — Next configuration and refusal of public database environment variables.
- [tsconfig.json](../../tsconfig.json) — TypeScript compile/check configuration.
- [eslint.config.mjs](../../eslint.config.mjs) — Static lint configuration.
- [.env.example](../../.env.example) — Placeholder-only public configuration examples; never use to store secrets.

## Important implementation files

| File | Responsibility |
|---|---|
| [app/page.tsx](../../app/page.tsx) | submit/runPlanning, ordinary and advanced actions, explicit preference and page ownership. |
| [lib/planning-client.ts](../../lib/planning-client.ts) | generateOuting and adaptRanking: interpretation branching, generation, runtime response checks. |
| [components/location-controls.tsx](../../components/location-controls.tsx) | Confirmed device/manual origin, Surprise Me conflicts, explicit lookup/permission lifecycle. |
| [lib/preferences.ts](../../lib/preferences.ts) | Distinguish manual overrides from automatically displayed inferred fields. |
| [backend/main.py](../../backend/main.py) | Routes, local/private middleware, safe failures, provider budget and runtime dispatch. |
| [backend/models.py](../../backend/models.py) | ContractModel, OutingRequest/PlanningRequest, venue/candidate/evaluation/result models. |
| [backend/interpretation.py](../../backend/interpretation.py) | InterpretationInput/Result, strict source/scalar/manual/calendar pipeline and questions. |
| [backend/ai/__init__.py](../../backend/ai/__init__.py) | Interpretation schema, strict JSON parser, AISettings and Ollama-only factory. |
| [backend/ai/ollama.py](../../backend/ai/ollama.py) | Local extraction prompts/examples/schema payload and bounded loopback transport. |
| [backend/journey.py](../../backend/journey.py) | Occurrence/order/endpoint/duration semantics, normalization and active legacy checks. |
| [backend/duration_preparation.py](../../backend/duration_preparation.py) | B2 extracted duration helper with dynamically delegated legacy dependencies. |
| [backend/source_preparation.py](../../backend/source_preparation.py) | Versioned raw capture and occurrence preparation, not general semantic authority. |
| [backend/validation_phases.py](../../backend/validation_phases.py) | Named legacy disposition and wrapper boundary. |
| [backend/planning_admission.py](../../backend/planning_admission.py) | Python-only admission foundation; ordinary startup guards are no-ops, not V4 enforcement. |
| [backend/ordering_shadow.py](../../backend/ordering_shadow.py) | Default-OFF observer; local test scope only, no graph mutation or plan authority. |
| [backend/planner.py](../../backend/planner.py) | Fictional Baltimore coverage, pools, depth-first product generation and stable IDs. |
| [backend/ranking.py](../../backend/ranking.py) | Ordinary feasibility, earliest-time schedule, weighted scoring and diverse selection. |
| [backend/real_planning.py](../../backend/real_planning.py) | PlannerInput, real_plans/more_real_plans, discovery/route/evaluation orchestration. |
| [backend/sequential_discovery.py](../../backend/sequential_discovery.py) | Location-first staged real discovery and selective route work. |
| [backend/discovery_inventory.py](../../backend/discovery_inventory.py) | Finite retained search inventory, pages and discovery state. |
| [backend/spatial_beam.py](../../backend/spatial_beam.py) | Geographic shortlist support; gaps are heuristics, not travel evidence. |
| [backend/advanced_planning.py](../../backend/advanced_planning.py) | AdvancedInput/Result and session orchestration, answers, timing, alternatives and saving. |
| [backend/advanced_preferences.py](../../backend/advanced_preferences.py) | Occurrence-scoped dwell/identity edits, budget scope and closure permission removal. |
| [backend/stop_resolution.py](../../backend/stop_resolution.py) | Exact named identity versus generic discovery, shared-mall relationships and choices. |
| [backend/advanced_routing.py](../../backend/advanced_routing.py) | Precedence-aware bounded paths, topology, directed-pair admission and route selection. |
| [backend/advanced_timing.py](../../backend/advanced_timing.py) | Elapsed ranges, departure/deadline and hours checks over server-owned routes. |
| [backend/places.py](../../backend/places.py) | Places requests, search-body construction, candidate parsing and discovery. |
| [backend/places_transport.py](../../backend/places_transport.py) | Backend-only OAuth Text Search transport with gates and accounting. |
| [backend/routes.py](../../backend/routes.py) | Directed route contracts/calculator, traffic-aware driving, walking and freshness. |
| [backend/routes_transport.py](../../backend/routes_transport.py) | Validated minimal matrix HTTP transport; retries zero. |
| [backend/venue_models.py](../../backend/venue_models.py) | Canonical provider facts and nullable source evidence. |
| [backend/venue_normalization.py](../../backend/venue_normalization.py) | Convert Google records to canonical facts without inventing values. |
| [backend/venue_quality.py](../../backend/venue_quality.py) | Activity relevance and candidate quality checks. |
| [backend/venue_geography.py](../../backend/venue_geography.py) | Destination/radius/exclusion evidence; narrow Hitech/HITEC parent-bound comparison. |
| [backend/planning_hours.py](../../backend/planning_hours.py) | Destination-date hours projection and conservative closure handling. |
| [backend/feasibility.py](../../backend/feasibility.py) | Pure supplied-evidence travel/hours/session evaluation, no I/O. |
| [backend/provider_budget.py](../../backend/provider_budget.py) | Local provider gates, outing/process attempt/element ceilings and reservation ownership. |
| [backend/development_cost.py](../../backend/development_cost.py) | Protected durable local estimated gross-cost/minute accounting, no ledger reset. |
| [backend/admission.py](../../backend/admission.py) | Process request/inference admission and explicit production/hosting refusal. |
| [backend/provider_work.py](../../backend/provider_work.py) | Worker ownership/cancellation propagation separate from HTTP lifetime. |
| [backend/request_middleware.py](../../backend/request_middleware.py) | Bounded readers/body, duplicate/burst admission and safe outcomes. |
| [backend/failures.py](../../backend/failures.py) | Stable safe messages and content-free correlation logging. |
| [backend/operations.py](../../backend/operations.py) | Bounded structured events, measurements and log sink. |
| [backend/saved_plans.py](../../backend/saved_plans.py) | Safe documents, receipt membership, restricted transactions, save and reopen. |
| [backend/saved_advanced.py](../../backend/saved_advanced.py) | Selected-only version 2 app-owned advanced requirements/order/provenance; redacts origins. |
| [backend/saved_refresh.py](../../backend/saved_refresh.py) | Selected saved option current details/contacts/hours and action replay bounds. |
| [backend/persistence_config.py](../../backend/persistence_config.py) | Backend private runtime connection parsing/validation. |
| [backend/option_sessions.py](../../backend/option_sessions.py) | 50 active ordinary continuation contexts, 600-second expiry and per-session locks. |
| [backend/testing_clock.py](../../backend/testing_clock.py) | Explicit isolated test clocks and child API fixture factory; no production fixed clock. |
| [backend/dev_start.py](../../backend/dev_start.py) | Private local-profile loader and backend startup behavior. |
| [scripts/dev-server.mjs](../../scripts/dev-server.mjs) | Frontend/backend process lifecycle launcher; protects unrelated listeners. |
| [scripts/cloud_model52.py](../../scripts/cloud_model52.py) | Original evaluation corpus/configuration/scoring foundations. |
| [scripts/cloud_model52_v4_live.py](../../scripts/cloud_model52_v4_live.py) | Frozen halted evaluator; source mismatch refusal remains. Do not execute for lessons. |
| [scripts/task52_q1.py](../../scripts/task52_q1.py) | Frozen qualification/reconstruction identities and offline seven-response comparisons. |
| [scripts/task52_q2.py](../../scripts/task52_q2.py) | Finite provider request/schema compatibility decisions without inference. |
| [scripts/task52_q3.py](../../scripts/task52_q3.py) | Fictional continuation/state model for exact successor proposal. |
| [scripts/task52_q4a.py](../../scripts/task52_q4a.py) | Offline synthetic protocol; live dispatch unconditionally refuses. |
| [scripts/task52_q4b.py](../../scripts/task52_q4b.py) | Read-only immutable original-storage inspection, not a writable adapter. |
| [scripts/task52_q4c_auth.py](../../scripts/task52_q4c_auth.py) | Detached signatures, pinned synthetic trust/revocation and purpose-specific role checks. |
| [scripts/task52_q4c_protocol.py](../../scripts/task52_q4c_protocol.py) | Exact historical-DDL fictional protocol, fake exchange, immutable attempt/review facts. |
| [scripts/task52_ordering_v5.py](../../scripts/task52_ordering_v5.py) | Independently committed offline owner-policy V5 recognizer at b1efe96; no runtime integration. |

## Data, migrations and research

- [backend/migrations](../../backend/migrations) — Two SQL schema versions; do not run them for study.
- [data](../../data) — Shared fictional venue data and project data contracts; inspect file provenance before treating a record as real.
- [backend/evaluation](../../backend/evaluation) — Local semantic fixtures and recorded Qwen results, not production venue content.
- [docs](../../docs) — Implementation/evaluation evidence, proposals, JSON manifests and frozen historical results.
- [docs/learning](../../docs/learning) — This course, references, separate solutions and verification.
- [backend/TESTING.md](../../backend/TESTING.md) — Clock ownership, offline test commands and opt-in resource boundaries.

Important research starts: [Q1 contract](../task52-q1-qualification-v1.md), [Q2 compatibility](../task52-q2-provider-compatibility.md), [Q3 design](../task52-q3-continuation-design.md), [Q4A](../task52-q4a-successor-offline-v1.md), [Q4B](../task52-q4b-journal-operator-review.md), [Q4C](../task52-q4c-offline-protocol-v1.md), [V4 policy](../task52-ordering-policy-v4.md), [cloud proposal](../task52-cloud-architecture-evaluation.md) and [Hitech investigation](../hitec-destination-investigation.md).

## Complete app source and test index

Next.js App Router pages and same-origin HTTP proxies. page.tsx owns interactive form orchestration; layout.tsx and globals.css own shared page structure/style.

| File | Top-level declarations / reading cue |
|---|---|
| [app/api/development-diagnostics/route.ts](../../app/api/development-diagnostics/route.ts) | `GET` |
| [app/api/health/route.test.ts](../../app/api/health/route.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [app/api/health/route.ts](../../app/api/health/route.ts) | `runtime`, `GET` |
| [app/api/interpret/route.test.ts](../../app/api/interpret/route.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [app/api/interpret/route.ts](../../app/api/interpret/route.ts) | `runtime`, `POST` |
| [app/api/planning-mode/route.ts](../../app/api/planning-mode/route.ts) | `runtime`, `GET` |
| [app/api/plans/advanced/route.ts](../../app/api/plans/advanced/route.ts) | `runtime`, `POST` |
| [app/api/plans/generate/route.test.ts](../../app/api/plans/generate/route.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [app/api/plans/generate/route.ts](../../app/api/plans/generate/route.ts) | `runtime`, `POST` |
| [app/api/plans/options/route.ts](../../app/api/plans/options/route.ts) | `runtime`, `POST` |
| [app/api/plans/refresh/route.ts](../../app/api/plans/refresh/route.ts) | `runtime`, `POST` |
| [app/api/plans/reopen/route.ts](../../app/api/plans/reopen/route.ts) | `runtime`, `POST` |
| [app/api/plans/save/route.ts](../../app/api/plans/save/route.ts) | `runtime`, `POST` |
| [app/api/starting-areas/route.ts](../../app/api/starting-areas/route.ts) | `runtime`, `POST` |
| [app/api/starting-places/route.ts](../../app/api/starting-places/route.ts) | `runtime`, `POST` |
| [app/api/venues/details/route.ts](../../app/api/venues/details/route.ts) | `runtime`, `POST` |
| [app/dev/diagnostics/page.tsx](../../app/dev/diagnostics/page.tsx) | `dynamic` |
| [app/how-it-works/page.tsx](../../app/how-it-works/page.tsx) | Imports, configuration, fixture registration or side-effect statements; read file |
| [app/layout.tsx](../../app/layout.tsx) | `metadata` |
| [app/page.tsx](../../app/page.tsx) | Imports, configuration, fixture registration or side-effect statements; read file |
| [app/privacy/page.tsx](../../app/privacy/page.tsx) | Imports, configuration, fixture registration or side-effect statements; read file |
| [app/supported-activities/page.tsx](../../app/supported-activities/page.tsx) | Imports, configuration, fixture registration or side-effect statements; read file |
| [app/terms/page.tsx](../../app/terms/page.tsx) | Imports, configuration, fixture registration or side-effect statements; read file |

## Complete components source and test index

Reusable cards, location/date controls, clarification, advanced preferences, saved views, details, directions and result copy. These render state and emit actions; they do not own authoritative planning.

| File | Top-level declarations / reading cue |
|---|---|
| [components/advanced-plan.tsx](../../components/advanced-plan.tsx) | `AdvancedDetails`, `AdvancedClarifications` |
| [components/advanced-preferences.tsx](../../components/advanced-preferences.tsx) | `AdvancedPreferenceFields` |
| [components/alternative-actions.tsx](../../components/alternative-actions.tsx) | `AlternativeActions` |
| [components/artwork.tsx](../../components/artwork.tsx) | `HeroArtwork`, `CardArtwork` |
| [components/beyond-preferences.tsx](../../components/beyond-preferences.tsx) | `BeyondPreferences` |
| [components/clarification-field.tsx](../../components/clarification-field.tsx) | `ClarificationField` |
| [components/development-diagnostics.tsx](../../components/development-diagnostics.tsx) | `DevelopmentDiagnostics` |
| [components/exploration-notice.tsx](../../components/exploration-notice.tsx) | `ExplorationNotice`, `explorationStage` |
| [components/first-leg-travel.tsx](../../components/first-leg-travel.tsx) | `FirstLegTravel` |
| [components/itinerary-pagination.tsx](../../components/itinerary-pagination.tsx) | `ItineraryPagination` |
| [components/itinerary-stop.tsx](../../components/itinerary-stop.tsx) | `ItineraryStop`, `EndingStep` |
| [components/location-controls.tsx](../../components/location-controls.tsx) | `StartingLocationHandle`, `LocationControls` |
| [components/opening-hours.tsx](../../components/opening-hours.tsx) | `OpeningHours` |
| [components/outing-date-field.tsx](../../components/outing-date-field.tsx) | `OutingDateField` |
| [components/outing-summary.tsx](../../components/outing-summary.tsx) | `activityEditText`, `formatOutingDate`, `outingDetails`, `OutingSummary` |
| [components/plan-card.tsx](../../components/plan-card.tsx) | `PlanCard` |
| [components/plan-cost.tsx](../../components/plan-cost.tsx) | `PlanCost` |
| [components/planning-feedback.tsx](../../components/planning-feedback.tsx) | `PlanningFeedback` |
| [components/real-venue-facts.tsx](../../components/real-venue-facts.tsx) | `VenueRating`, `RealVenueFacts` |
| [components/results-information.tsx](../../components/results-information.tsx) | `ResultsInformation` |
| [components/route-directions.tsx](../../components/route-directions.tsx) | `RouteDirections` |
| [components/saved-cards.tsx](../../components/saved-cards.tsx) | `SavedCards` |
| [components/saved-plans.tsx](../../components/saved-plans.tsx) | `SavedPlans` |
| [components/venue-details.tsx](../../components/venue-details.tsx) | `GoogleCredits`, `VenueDetails` |

## Complete lib source and test index

Browser/server TypeScript contracts, clients, adapters, state/lifetime helpers, display functions and offline TypeScript tests. lib/legacy/planner.ts preserves historical prototype logic; Python owns active planning.

| File | Top-level declarations / reading cue |
|---|---|
| [lib/acceptance-errors.test.ts](../../lib/acceptance-errors.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/acceptance46.test.ts](../../lib/acceptance46.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/advanced-planning.test.ts](../../lib/advanced-planning.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/advanced-planning.ts](../../lib/advanced-planning.ts) | `Dwell`, `AdvancedStop`, `AdvancedOption`, `AdvancedQuestion`, `AdvancedData`, `AdvancedState`, `adaptAdvanced`, `continueAdvanced` |
| [lib/advanced-preferences.test.ts](../../lib/advanced-preferences.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/advanced-preferences.ts](../../lib/advanced-preferences.ts) | `AdvancedPreferences`, `AdvancedDraft`, `advancedDraft`, `advancedEdits`, `rememberAdvancedEdit`, `durationRelation` |
| [lib/advanced-resolution.test.ts](../../lib/advanced-resolution.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/clarification-field.test.ts](../../lib/clarification-field.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/continuation.ts](../../lib/continuation.ts) | `planningMessage`, `restoreContinuation`, `continuationNotice` |
| [lib/coverage-errors.test.ts](../../lib/coverage-errors.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/database-environment.test.ts](../../lib/database-environment.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/destination-context.test.ts](../../lib/destination-context.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/destination-context.ts](../../lib/destination-context.ts) | `DestinationContext`, `currentRelative`, `explicitOrigin`, `recoveryCode` |
| [lib/development-access.ts](../../lib/development-access.ts) | `diagnosticBoundary` |
| [lib/development-origin.ts](../../lib/development-origin.ts) | `developmentOriginHeaders` |
| [lib/discovery-actions.test.ts](../../lib/discovery-actions.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/display-format.ts](../../lib/display-format.ts) | `destinationLabel`, `transportLabel`, `activityDisplay`, `outingDateLabel` |
| [lib/duration-format.test.ts](../../lib/duration-format.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/duration-format.ts](../../lib/duration-format.ts) | `formatSeconds`, `formatDuration` |
| [lib/exploration.test.ts](../../lib/exploration.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/failure-diagnostics.ts](../../lib/failure-diagnostics.ts) | `classifiedFailure`, `failureText` |
| [lib/final-acceptance49.test.ts](../../lib/final-acceptance49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/first-preference.test.ts](../../lib/first-preference.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/first-preference.ts](../../lib/first-preference.ts) | `FirstPreference` |
| [lib/hours-display49.test.ts](../../lib/hours-display49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/itinerary-pages.test.ts](../../lib/itinerary-pages.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/itinerary-pages.ts](../../lib/itinerary-pages.ts) | `BEYOND_NOTICE`, `beyondNotice`, `signature`, `beyondPage`, `ItineraryPages` |
| [lib/legacy/planner.ts](../../lib/legacy/planner.ts) | `CostPreference`, `Preferences`, `Stop`, `Plan`, `PlannerResult`, `EXAMPLE_REQUEST`, `EMPTY_PREFERENCES`, `SUPPORTED_ACTIVITIES`, `legTravel`, `scheduleRoute`, `makePlans`, `formatTime` |
| [lib/location-first.test.ts](../../lib/location-first.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/location.test.ts](../../lib/location.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/location.ts](../../lib/location.ts) | `requestLocation`, `requestStartingLocation` |
| [lib/maps-directions.ts](../../lib/maps-directions.ts) | `mapsDirections` |
| [lib/mock-data.ts](../../lib/mock-data.ts) | `MOCK_EVENT_DATES`, `CanonicalActivity`, `Activity`, `CATALOG`, `ACTIVITY_LABELS`, `activityLabel`, `Venue`, `VENUES` |
| [lib/open-exploration.test.ts](../../lib/open-exploration.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/option-batches.ts](../../lib/option-batches.ts) | `nextOptions`, `expandedOptions` |
| [lib/outing-editor.test.ts](../../lib/outing-editor.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/outing-summary.test.ts](../../lib/outing-summary.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/persistence-proxy.ts](../../lib/persistence-proxy.ts) | `persistenceProxy` |
| [lib/planner.test.ts](../../lib/planner.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/planner.ts](../../lib/planner.ts) | `CostPreference`, `Preferences`, `OutingPayload`, `Quality`, `DisplayVenue`, `Stop`, `Plan`, `PlannerResult`, `ResolvedOuting`, `EXAMPLE_REQUEST`, `EMPTY_PREFERENCES`, `SUPPORTED_ACTIVITIES`, `resolveOuting`, `formatTime` |
| [lib/planning-client.test.ts](../../lib/planning-client.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/planning-client.ts](../../lib/planning-client.ts) | `adaptRanking`, `ClarificationField`, `ClarificationAnswers`, `PendingOuting`, `ValidatedOuting`, `generateOuting`, `LocationContext` |
| [lib/planning-session.test.ts](../../lib/planning-session.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/planning-session.ts](../../lib/planning-session.ts) | `PlanningSession` |
| [lib/planning-timing.ts](../../lib/planning-timing.ts) | `beginPlanningTiming`, `recordPlanningTiming`, `planningElapsed`, `planningTiming`, `measurePlanning` |
| [lib/preferences.test.ts](../../lib/preferences.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/preferences.ts](../../lib/preferences.ts) | `PreferenceField`, `PreferenceState`, `emptyPreferenceState`, `editPreference`, `manualPreferences`, `displayInterpretedPreferences`, `interpretedPreferences` |
| [lib/provider-cancellation.test.ts](../../lib/provider-cancellation.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/provider-diagnostics.ts](../../lib/provider-diagnostics.ts) | `providerDiagnosticNotes` |
| [lib/provider-proxy.ts](../../lib/provider-proxy.ts) | `providerProxy` |
| [lib/proxy-failures.ts](../../lib/proxy-failures.ts) | `invalidUpstreamResponse` |
| [lib/public-planning-payload.ts](../../lib/public-planning-payload.ts) | `publicPlanningPayload` |
| [lib/real-headlines.test.ts](../../lib/real-headlines.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/real-headlines.ts](../../lib/real-headlines.ts) | `realHeadlines` |
| [lib/real-planning.test.ts](../../lib/real-planning.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/recommendation-copy.test.ts](../../lib/recommendation-copy.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/recommendation-copy.ts](../../lib/recommendation-copy.ts) | `RecommendationFacts`, `recommendationCopy` |
| [lib/refinements49.test.ts](../../lib/refinements49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/regeneration-ux49.test.ts](../../lib/regeneration-ux49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/request-management.test.ts](../../lib/request-management.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/request.ts](../../lib/request.ts) | `todayInBaltimore`, `validDate`, `resolveDate`, `parseRequest` |
| [lib/results-presentation.test.ts](../../lib/results-presentation.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/results-presentation.ts](../../lib/results-presentation.ts) | `DEMO_DISCLOSURE`, `OPENING_HOURS_ISSUE`, `resultsSummary`, `consumerMessage`, `failureMessage`, `estimateNotes`, `planWarnings` |
| [lib/route-directions.test.ts](../../lib/route-directions.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/saved-details-reliability.test.ts](../../lib/saved-details-reliability.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/saved-details-request.ts](../../lib/saved-details-request.ts) | `loadSavedDetails`, `detailsFeedback` |
| [lib/saved-navigation.ts](../../lib/saved-navigation.ts) | `TAB_SAVED_KEY`, `savedLaunchToken` |
| [lib/saved-plan-refresh.ts](../../lib/saved-plan-refresh.ts) | `RefreshedVenue`, `mergeRefreshed` |
| [lib/saved-plans.test.ts](../../lib/saved-plans.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/saved-plans.ts](../../lib/saved-plans.ts) | `TOKEN`, `SAVED_KEY`, `privateLink`, `fragmentToken`, `SavedPlan`, `preferenceText`, `validateSaved` |
| [lib/server-timing.ts](../../lib/server-timing.ts) | `timingHeaders` |
| [lib/sharing-ux49.test.ts](../../lib/sharing-ux49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/stabilization.test.ts](../../lib/stabilization.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/starting-areas.ts](../../lib/starting-areas.ts) | `FirstTravel`, `Geography`, `OriginPreparation`, `StartingSuggestion`, `StartingAreaSession` |
| [lib/starting-confirmation.ts](../../lib/starting-confirmation.ts) | `StartingConfirmation` |
| [lib/starting-places.ts](../../lib/starting-places.ts) | `StartingMatch`, `StartingPlaceSession` |
| [lib/strict-local.test.ts](../../lib/strict-local.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/submission-feedback.test.ts](../../lib/submission-feedback.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/supported-activities.ts](../../lib/supported-activities.ts) | `supportedActivityGroups` |
| [lib/surprise-history.ts](../../lib/surprise-history.ts) | `SurpriseHistory` |
| [lib/surprise.test.ts](../../lib/surprise.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/task46-improvements.test.ts](../../lib/task46-improvements.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/traffic-policy50e.test.ts](../../lib/traffic-policy50e.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/ui-travel-mode49.test.ts](../../lib/ui-travel-mode49.test.ts) | Offline test/fixture declarations: Imports, configuration, fixture registration or side-effect statements; read file |
| [lib/venue-details.ts](../../lib/venue-details.ts) | `Credit`, `ContactDetails`, `safeWebsite`, `safeMapsUrl`, `ContactLookupError`, `VenueDetailsSession` |
| [lib/venue-hours.ts](../../lib/venue-hours.ts) | `HoursEvidence` |

## Complete backend source and test index

FastAPI boundaries, strict contracts, local model adapter, source/calendar validation, ordinary and advanced planners, Google adapters, quotas/accounting, SQL persistence and unittest suites.

| File | Top-level declarations / reading cue |
|---|---|
| [backend/.local/task52-eval-deps/certifi/__init__.py](../../backend/.local/task52-eval-deps/certifi/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/certifi/__main__.py](../../backend/.local/task52-eval-deps/certifi/__main__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/certifi/core.py](../../backend/.local/task52-eval-deps/certifi/core.py) | `exit_cacert_ctx` |
| [backend/.local/task52-eval-deps/certifi/tests/__init__.py](../../backend/.local/task52-eval-deps/certifi/tests/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/certifi/tests/test_certify.py](../../backend/.local/task52-eval-deps/certifi/tests/test_certify.py) | Offline test/fixture declarations: `TestCertifi` |
| [backend/.local/task52-eval-deps/charset_normalizer/__init__.py](../../backend/.local/task52-eval-deps/charset_normalizer/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/charset_normalizer/__main__.py](../../backend/.local/task52-eval-deps/charset_normalizer/__main__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/charset_normalizer/api.py](../../backend/.local/task52-eval-deps/charset_normalizer/api.py) | `from_bytes`, `from_fp`, `from_path`, `is_binary` |
| [backend/.local/task52-eval-deps/charset_normalizer/cd.py](../../backend/.local/task52-eval-deps/charset_normalizer/cd.py) | `encoding_unicode_range`, `unicode_range_languages`, `encoding_languages`, `mb_encoding_languages`, `get_target_features`, `alphabet_languages`, `characters_popularity_compare`, `alpha_unicode_split`, `merge_coherence_ratios`, `filter_alt_coherence_matches`, `coherence_ratio` |
| [backend/.local/task52-eval-deps/charset_normalizer/cli/__init__.py](../../backend/.local/task52-eval-deps/charset_normalizer/cli/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/charset_normalizer/cli/__main__.py](../../backend/.local/task52-eval-deps/charset_normalizer/cli/__main__.py) | `query_yes_no`, `FileType`, `cli_detect` |
| [backend/.local/task52-eval-deps/charset_normalizer/constant.py](../../backend/.local/task52-eval-deps/charset_normalizer/constant.py) | `CompatibleFamillyRange` |
| [backend/.local/task52-eval-deps/charset_normalizer/legacy.py](../../backend/.local/task52-eval-deps/charset_normalizer/legacy.py) | `detect` |
| [backend/.local/task52-eval-deps/charset_normalizer/md.py](../../backend/.local/task52-eval-deps/charset_normalizer/md.py) | `CharInfo`, `_char_info`, `MessDetectorPlugin`, `TooManySymbolOrPunctuationPlugin`, `TooManyAccentuatedPlugin`, `UnprintablePlugin`, `SuspiciousDuplicateAccentPlugin`, `SuspiciousRange`, `SuperWeirdWordPlugin`, `CjkUncommonPlugin`, `SuspiciousKatakanaPlugin`, `ArchaicUpperLowerPlugin`, `ArabicIsolatedFormPlugin`, `is_suspiciously_successive_range`, `mess_ratio` |
| [backend/.local/task52-eval-deps/charset_normalizer/models.py](../../backend/.local/task52-eval-deps/charset_normalizer/models.py) | `CharsetMatch`, `CharsetMatches`, `CliDetectionResult` |
| [backend/.local/task52-eval-deps/charset_normalizer/utils.py](../../backend/.local/task52-eval-deps/charset_normalizer/utils.py) | `_character_flags`, `is_accentuated`, `remove_accent`, `unicode_range`, `is_latin`, `is_punctuation`, `is_symbol`, `is_emoticon`, `is_separator`, `is_case_variable`, `is_cjk`, `is_hiragana`, `is_katakana`, `is_hangul`, `is_thai`, `is_arabic`, `is_arabic_isolated_form`, `is_cjk_uncommon`, `is_unicode_range_secondary`, `is_unprintable`, `any_specified_encoding`, `is_multi_byte_encoding`, `identify_sig_or_bom`, `should_strip_sig_or_bom`, `iana_name`, `cp_similarity`, `is_cp_similar`, `set_logging_handler`, `cut_sequence_chunks` |
| [backend/.local/task52-eval-deps/charset_normalizer/version.py](../../backend/.local/task52-eval-deps/charset_normalizer/version.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/idna/__init__.py](../../backend/.local/task52-eval-deps/idna/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/idna/__main__.py](../../backend/.local/task52-eval-deps/idna/__main__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/idna/cli.py](../../backend/.local/task52-eval-deps/idna/cli.py) | `_looks_like_alabel`, `_build_parser`, `_iter_stdin`, `_convert_one`, `main` |
| [backend/.local/task52-eval-deps/idna/codec.py](../../backend/.local/task52-eval-deps/idna/codec.py) | `Codec`, `IncrementalEncoder`, `IncrementalDecoder`, `StreamWriter`, `StreamReader`, `search_function` |
| [backend/.local/task52-eval-deps/idna/compat.py](../../backend/.local/task52-eval-deps/idna/compat.py) | `ToASCII`, `ToUnicode`, `nameprep` |
| [backend/.local/task52-eval-deps/idna/core.py](../../backend/.local/task52-eval-deps/idna/core.py) | `_joining_type`, `IDNAError`, `IDNABidiError`, `InvalidCodepoint`, `InvalidCodepointContext`, `_combining_class`, `_is_script`, `_punycode`, `_unot`, `valid_label_length`, `valid_string_length`, `check_bidi`, `check_initial_combiner`, `check_hyphen_ok`, `check_nfc`, `valid_contextj`, `valid_contexto`, `check_label`, `alabel`, `ulabel`, `_check_std3`, `_warn_transitional`, `uts46_remap`, `encode`, `decode` |
| [backend/.local/task52-eval-deps/idna/idnadata.py](../../backend/.local/task52-eval-deps/idna/idnadata.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/idna/intranges.py](../../backend/.local/task52-eval-deps/idna/intranges.py) | `intranges_from_list`, `_encode_range`, `_decode_range`, `intranges_contain` |
| [backend/.local/task52-eval-deps/idna/package_data.py](../../backend/.local/task52-eval-deps/idna/package_data.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/idna/uts46data.py](../../backend/.local/task52-eval-deps/idna/uts46data.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/regex/__init__.py](../../backend/.local/task52-eval-deps/regex/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/regex/_main.py](../../backend/.local/task52-eval-deps/regex/_main.py) | `match`, `prefixmatch`, `fullmatch`, `search`, `sub`, `subf`, `subn`, `subfn`, `split`, `splititer`, `findall`, `finditer`, `compile`, `purge`, `cache_all`, `template`, `escape`, `_compile`, `_compile_replacement_helper`, `_pickle` |
| [backend/.local/task52-eval-deps/regex/_regex_core.py](../../backend/.local/task52-eval-deps/regex/_regex_core.py) | `error`, `_UnscopedFlagSet`, `ParseError`, `_FirstSetError`, `RegexFlag`, `Namespace`, `_shrink_cache`, `_fold_case`, `is_cased_i`, `is_cased_f`, `_compile_firstset`, `_check_firstset`, `_flatten_code`, `make_case_flags`, `make_character`, `make_ref_group`, `make_string_set`, `make_property`, `_parse_pattern`, `parse_sequence`, `is_actually_fuzzy`, `apply_quantifier`, `apply_constraint`, `parse_quantifier`, `is_above_limit`, `parse_limited_quantifier`, `parse_fuzzy`, `parse_fuzzy_item`, `parse_cost_constraint`, `parse_cost_limit`, `parse_constraint`, `parse_fuzzy_compare`, `parse_cost_equation`, `parse_cost_term`, `parse_fuzzy_test`, `parse_count`, `parse_paren`, `parse_extension`, `parse_comment`, `parse_lookaround`, `parse_conditional`, `parse_lookaround_conditional`, `parse_atomic`, `parse_common`, `parse_call_group`, `parse_rel_call_group`, `parse_call_named_group`, `parse_flag_set`, `parse_flags`, `parse_subpattern`, `parse_flags_subpattern`, `parse_positional_flags`, `parse_name`, `is_octal`, `is_decimal`, `is_hexadecimal`, `parse_escape`, `parse_numeric_escape`, `parse_octal_escape`, `parse_hex_escape`, `parse_group_ref`, `parse_string_set`, `parse_named_char`, `parse_property`, `parse_property_name`, `parse_set`, `parse_set_union`, `parse_set_symm_diff`, `parse_set_inter`, `parse_set_diff`, `parse_set_imp_union`, `parse_set_member`, `parse_set_item`, `parse_posix_class`, `float_to_rational`, `numeric_to_rational`, `standardise_name`, `lookup_property`, `_compile_replacement`, `parse_repl_hex_escape`, `parse_repl_named_char`, `compile_repl_group`, `make_sequence`, `RegexBase`, `ZeroWidthBase`, `Any`, `AnyAll`, `AnyU`, `Atomic`, `Boundary`, `Branch`, `CallGroup`, `CallRef`, `Character`, `Conditional`, `DefaultBoundary`, `DefaultEndOfWord`, `DefaultStartOfWord`, `EndOfLine`, `EndOfLineU`, `EndOfString`, `EndOfStringLine`, `EndOfStringLineU`, `EndOfWord`, `Failure`, `Fuzzy`, `Grapheme`, `GraphemeBoundary`, `GreedyRepeat`, `PossessiveRepeat`, `Group`, `Keep`, `LazyRepeat`, `LookAround`, `LookAroundConditional`, `PrecompiledCode`, `Property`, `Prune`, `Range`, `RefGroup`, `SearchAnchor`, `Sequence`, `SetBase`, `SetDiff`, `SetInter`, `SetSymDiff`, `SetUnion`, `Skip`, `StartOfLine`, `StartOfLineU`, `StartOfString`, `StartOfWord`, `String`, `Literal`, `StringSet`, `Source`, `Info`, `_check_group_features`, `_get_required_string`, `Scanner` |
| [backend/.local/task52-eval-deps/regex/tests/test_regex.py](../../backend/.local/task52-eval-deps/regex/tests/test_regex.py) | Offline test/fixture declarations: `StrSubclass`, `BytesSubclass`, `RegexTests`, `test_main` |
| [backend/.local/task52-eval-deps/requests/__init__.py](../../backend/.local/task52-eval-deps/requests/__init__.py) | `check_compatibility`, `_check_cryptography` |
| [backend/.local/task52-eval-deps/requests/__version__.py](../../backend/.local/task52-eval-deps/requests/__version__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/requests/_internal_utils.py](../../backend/.local/task52-eval-deps/requests/_internal_utils.py) | `to_native_string`, `unicode_is_ascii` |
| [backend/.local/task52-eval-deps/requests/_types.py](../../backend/.local/task52-eval-deps/requests/_types.py) | `SupportsRead`, `SupportsItems`, `is_prepared` |
| [backend/.local/task52-eval-deps/requests/adapters.py](../../backend/.local/task52-eval-deps/requests/adapters.py) | `_urllib3_request_context`, `BaseAdapter`, `HTTPAdapter` |
| [backend/.local/task52-eval-deps/requests/api.py](../../backend/.local/task52-eval-deps/requests/api.py) | `request`, `get`, `options`, `head`, `post`, `put`, `patch`, `delete` |
| [backend/.local/task52-eval-deps/requests/auth.py](../../backend/.local/task52-eval-deps/requests/auth.py) | `_basic_auth_str`, `AuthBase`, `HTTPBasicAuth`, `HTTPProxyAuth`, `HTTPDigestAuth` |
| [backend/.local/task52-eval-deps/requests/certs.py](../../backend/.local/task52-eval-deps/requests/certs.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/requests/compat.py](../../backend/.local/task52-eval-deps/requests/compat.py) | `_resolve_char_detection` |
| [backend/.local/task52-eval-deps/requests/cookies.py](../../backend/.local/task52-eval-deps/requests/cookies.py) | `MockRequest`, `MockResponse`, `extract_cookies_to_jar`, `get_cookie_header`, `remove_cookie_by_name`, `CookieConflictError`, `RequestsCookieJar`, `_copy_cookie_jar`, `create_cookie`, `morsel_to_cookie`, `cookiejar_from_dict`, `cookiejar_from_dict`, `cookiejar_from_dict`, `merge_cookies` |
| [backend/.local/task52-eval-deps/requests/exceptions.py](../../backend/.local/task52-eval-deps/requests/exceptions.py) | `RequestException`, `InvalidJSONError`, `JSONDecodeError`, `HTTPError`, `ConnectionError`, `ProxyError`, `SSLError`, `Timeout`, `ConnectTimeout`, `ReadTimeout`, `URLRequired`, `TooManyRedirects`, `MissingSchema`, `InvalidSchema`, `InvalidURL`, `InvalidHeader`, `InvalidProxyURL`, `ChunkedEncodingError`, `ContentDecodingError`, `StreamConsumedError`, `RetryError`, `UnrewindableBodyError`, `RequestsWarning`, `FileModeWarning`, `RequestsDependencyWarning` |
| [backend/.local/task52-eval-deps/requests/help.py](../../backend/.local/task52-eval-deps/requests/help.py) | `_implementation`, `info`, `main` |
| [backend/.local/task52-eval-deps/requests/hooks.py](../../backend/.local/task52-eval-deps/requests/hooks.py) | `default_hooks`, `dispatch_hook` |
| [backend/.local/task52-eval-deps/requests/models.py](../../backend/.local/task52-eval-deps/requests/models.py) | `RequestEncodingMixin`, `RequestHooksMixin`, `Request`, `PreparedRequest`, `Response` |
| [backend/.local/task52-eval-deps/requests/packages.py](../../backend/.local/task52-eval-deps/requests/packages.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/requests/sessions.py](../../backend/.local/task52-eval-deps/requests/sessions.py) | `merge_setting`, `merge_hooks`, `SessionRedirectMixin`, `Session`, `session` |
| [backend/.local/task52-eval-deps/requests/status_codes.py](../../backend/.local/task52-eval-deps/requests/status_codes.py) | `_init` |
| [backend/.local/task52-eval-deps/requests/structures.py](../../backend/.local/task52-eval-deps/requests/structures.py) | `CaseInsensitiveDict`, `LookupDict` |
| [backend/.local/task52-eval-deps/requests/utils.py](../../backend/.local/task52-eval-deps/requests/utils.py) | `dict_to_sequence`, `super_len`, `get_netrc_auth`, `guess_filename`, `extract_zipped_paths`, `atomic_open`, `from_key_val_list`, `to_key_val_list`, `to_key_val_list`, `to_key_val_list`, `parse_list_header`, `parse_dict_header`, `unquote_header_value`, `dict_from_cookiejar`, `add_dict_to_cookiejar`, `get_encodings_from_content`, `_parse_content_type_header`, `get_encoding_from_headers`, `stream_decode_response_unicode`, `iter_slices`, `iter_slices`, `iter_slices`, `get_unicode_from_response`, `unquote_unreserved`, `requote_uri`, `address_in_network`, `dotted_netmask`, `is_ipv4_address`, `is_valid_cidr`, `set_environ`, `should_bypass_proxies`, `get_environ_proxies`, `select_proxy`, `resolve_proxies`, `default_user_agent`, `default_headers`, `parse_header_links`, `guess_json_utf`, `prepend_scheme_if_needed`, `get_auth_from_url`, `check_header_validity`, `_validate_header_part`, `urldefragauth`, `rewind_body` |
| [backend/.local/task52-eval-deps/tiktoken/__init__.py](../../backend/.local/task52-eval-deps/tiktoken/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/tiktoken/_educational.py](../../backend/.local/task52-eval-deps/tiktoken/_educational.py) | `SimpleBytePairEncoding`, `bpe_encode`, `bpe_train`, `visualise_tokens`, `train_simple_encoding` |
| [backend/.local/task52-eval-deps/tiktoken/core.py](../../backend/.local/task52-eval-deps/tiktoken/core.py) | `Encoding`, `_special_token_regex`, `raise_disallowed_special_token` |
| [backend/.local/task52-eval-deps/tiktoken/load.py](../../backend/.local/task52-eval-deps/tiktoken/load.py) | `read_file`, `check_hash`, `read_file_cached`, `data_gym_to_mergeable_bpe_ranks`, `dump_tiktoken_bpe`, `load_tiktoken_bpe` |
| [backend/.local/task52-eval-deps/tiktoken/model.py](../../backend/.local/task52-eval-deps/tiktoken/model.py) | `encoding_name_for_model`, `encoding_for_model` |
| [backend/.local/task52-eval-deps/tiktoken/registry.py](../../backend/.local/task52-eval-deps/tiktoken/registry.py) | `_available_plugin_modules`, `_find_constructors`, `get_encoding`, `list_encoding_names` |
| [backend/.local/task52-eval-deps/tiktoken_ext/openai_public.py](../../backend/.local/task52-eval-deps/tiktoken_ext/openai_public.py) | `gpt2`, `r50k_base`, `p50k_base`, `p50k_edit`, `cl100k_base`, `o200k_base`, `o200k_harmony` |
| [backend/.local/task52-eval-deps/urllib3/__init__.py](../../backend/.local/task52-eval-deps/urllib3/__init__.py) | `add_stderr_logger`, `disable_warnings`, `request` |
| [backend/.local/task52-eval-deps/urllib3/_base_connection.py](../../backend/.local/task52-eval-deps/urllib3/_base_connection.py) | `ProxyConfig`, `_ResponseOptions` |
| [backend/.local/task52-eval-deps/urllib3/_collections.py](../../backend/.local/task52-eval-deps/urllib3/_collections.py) | `_Sentinel`, `ensure_can_construct_http_header_dict`, `RecentlyUsedContainer`, `HTTPHeaderDictItemView`, `HTTPHeaderDict` |
| [backend/.local/task52-eval-deps/urllib3/_request_methods.py](../../backend/.local/task52-eval-deps/urllib3/_request_methods.py) | `RequestMethods` |
| [backend/.local/task52-eval-deps/urllib3/_version.py](../../backend/.local/task52-eval-deps/urllib3/_version.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/urllib3/connection.py](../../backend/.local/task52-eval-deps/urllib3/connection.py) | `_normalize_header_value`, `_normalize_header_values`, `HTTPConnection`, `HTTPSConnection`, `_WrappedAndVerifiedSocket`, `_ssl_wrap_socket_and_match_hostname`, `_match_hostname`, `_wrap_proxy_error`, `_get_default_user_agent`, `DummyConnection`, `_url_from_connection` |
| [backend/.local/task52-eval-deps/urllib3/connectionpool.py](../../backend/.local/task52-eval-deps/urllib3/connectionpool.py) | `ConnectionPool`, `HTTPConnectionPool`, `HTTPSConnectionPool`, `connection_from_url`, `_normalize_host`, `_normalize_host`, `_normalize_host`, `_url_from_pool`, `_close_pool_connections` |
| [backend/.local/task52-eval-deps/urllib3/contrib/__init__.py](../../backend/.local/task52-eval-deps/urllib3/contrib/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/urllib3/contrib/emscripten/__init__.py](../../backend/.local/task52-eval-deps/urllib3/contrib/emscripten/__init__.py) | `inject_into_urllib3` |
| [backend/.local/task52-eval-deps/urllib3/contrib/emscripten/connection.py](../../backend/.local/task52-eval-deps/urllib3/contrib/emscripten/connection.py) | `EmscriptenHTTPConnection`, `EmscriptenHTTPSConnection` |
| [backend/.local/task52-eval-deps/urllib3/contrib/emscripten/fetch.py](../../backend/.local/task52-eval-deps/urllib3/contrib/emscripten/fetch.py) | `_RequestError`, `_StreamingError`, `_TimeoutError`, `_obj_from_dict`, `_ReadStream`, `_StreamingFetcher`, `_JSPIReadStream`, `is_in_browser_main_thread`, `is_cross_origin_isolated`, `is_in_node`, `is_worker_available`, `send_streaming_request`, `_show_timeout_warning`, `_show_streaming_warning`, `send_request`, `send_jspi_request`, `_run_sync_with_timeout`, `has_jspi`, `_is_node_js`, `streaming_ready`, `wait_for_streaming_ready` |
| [backend/.local/task52-eval-deps/urllib3/contrib/emscripten/request.py](../../backend/.local/task52-eval-deps/urllib3/contrib/emscripten/request.py) | `EmscriptenRequest` |
| [backend/.local/task52-eval-deps/urllib3/contrib/emscripten/response.py](../../backend/.local/task52-eval-deps/urllib3/contrib/emscripten/response.py) | `EmscriptenResponse`, `EmscriptenHttpResponseWrapper` |
| [backend/.local/task52-eval-deps/urllib3/contrib/pyopenssl.py](../../backend/.local/task52-eval-deps/urllib3/contrib/pyopenssl.py) | `inject_into_urllib3`, `extract_from_urllib3`, `_validate_dependencies_met`, `_dnsname_to_stdlib`, `get_subj_alt_name`, `_get_common_name`, `WrappedSocket`, `PyOpenSSLContext`, `_verify_callback` |
| [backend/.local/task52-eval-deps/urllib3/contrib/socks.py](../../backend/.local/task52-eval-deps/urllib3/contrib/socks.py) | `_TYPE_SOCKS_OPTIONS`, `SOCKSConnection`, `SOCKSHTTPSConnection`, `SOCKSHTTPConnectionPool`, `SOCKSHTTPSConnectionPool`, `SOCKSProxyManager` |
| [backend/.local/task52-eval-deps/urllib3/exceptions.py](../../backend/.local/task52-eval-deps/urllib3/exceptions.py) | `HTTPError`, `HTTPWarning`, `PoolError`, `RequestError`, `SSLError`, `ProxyError`, `DecodeError`, `ProtocolError`, `MaxRetryError`, `HostChangedError`, `TimeoutStateError`, `TimeoutError`, `ReadTimeoutError`, `ConnectTimeoutError`, `NewConnectionError`, `NameResolutionError`, `EmptyPoolError`, `FullPoolError`, `ClosedPoolError`, `LocationValueError`, `LocationParseError`, `URLSchemeUnknown`, `ResponseError`, `SecurityWarning`, `InsecureRequestWarning`, `NotOpenSSLWarning`, `SystemTimeWarning`, `InsecurePlatformWarning`, `DependencyWarning`, `ResponseNotChunked`, `BodyNotHttplibCompatible`, `IncompleteRead`, `InvalidChunkLength`, `InvalidHeader`, `ProxySchemeUnknown`, `ProxySchemeUnsupported`, `HeaderParsingError`, `UnrewindableBodyError` |
| [backend/.local/task52-eval-deps/urllib3/fields.py](../../backend/.local/task52-eval-deps/urllib3/fields.py) | `guess_content_type`, `format_header_param_rfc2231`, `format_multipart_header_param`, `format_header_param_html5`, `format_header_param`, `RequestField` |
| [backend/.local/task52-eval-deps/urllib3/filepost.py](../../backend/.local/task52-eval-deps/urllib3/filepost.py) | `choose_boundary`, `iter_field_objects`, `encode_multipart_formdata` |
| [backend/.local/task52-eval-deps/urllib3/http2/__init__.py](../../backend/.local/task52-eval-deps/urllib3/http2/__init__.py) | `inject_into_urllib3`, `extract_from_urllib3` |
| [backend/.local/task52-eval-deps/urllib3/http2/connection.py](../../backend/.local/task52-eval-deps/urllib3/http2/connection.py) | `_is_legal_header_name`, `_is_illegal_header_value`, `_LockedObject`, `HTTP2Connection`, `HTTP2Response` |
| [backend/.local/task52-eval-deps/urllib3/http2/probe.py](../../backend/.local/task52-eval-deps/urllib3/http2/probe.py) | `_HTTP2ProbeCache` |
| [backend/.local/task52-eval-deps/urllib3/poolmanager.py](../../backend/.local/task52-eval-deps/urllib3/poolmanager.py) | `PoolKey`, `_default_key_normalizer`, `PoolManager`, `ProxyManager`, `proxy_from_url` |
| [backend/.local/task52-eval-deps/urllib3/response.py](../../backend/.local/task52-eval-deps/urllib3/response.py) | `ContentDecoder`, `DeflateDecoder`, `GzipDecoderState`, `GzipDecoder`, `MultiDecoder`, `_get_decoder`, `BytesQueueBuffer`, `BaseHTTPResponse`, `HTTPResponse` |
| [backend/.local/task52-eval-deps/urllib3/util/__init__.py](../../backend/.local/task52-eval-deps/urllib3/util/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/.local/task52-eval-deps/urllib3/util/connection.py](../../backend/.local/task52-eval-deps/urllib3/util/connection.py) | `is_connection_dropped`, `create_connection`, `_set_socket_options`, `allowed_gai_family`, `_has_ipv6` |
| [backend/.local/task52-eval-deps/urllib3/util/proxy.py](../../backend/.local/task52-eval-deps/urllib3/util/proxy.py) | `connection_requires_http_tunnel` |
| [backend/.local/task52-eval-deps/urllib3/util/request.py](../../backend/.local/task52-eval-deps/urllib3/util/request.py) | `_TYPE_FAILEDTELL`, `make_headers`, `set_file_position`, `rewind_body`, `ChunksAndContentLength`, `body_to_chunks` |
| [backend/.local/task52-eval-deps/urllib3/util/response.py](../../backend/.local/task52-eval-deps/urllib3/util/response.py) | `is_fp_closed`, `assert_header_parsing`, `is_response_to_head` |
| [backend/.local/task52-eval-deps/urllib3/util/retry.py](../../backend/.local/task52-eval-deps/urllib3/util/retry.py) | `RequestHistory`, `Retry` |
| [backend/.local/task52-eval-deps/urllib3/util/ssl_.py](../../backend/.local/task52-eval-deps/urllib3/util/ssl_.py) | `_is_has_never_check_common_name_reliable`, `assert_fingerprint`, `resolve_cert_reqs`, `resolve_ssl_version`, `create_urllib3_context`, `ssl_wrap_socket`, `ssl_wrap_socket`, `ssl_wrap_socket`, `is_ipaddress`, `_is_key_file_encrypted`, `_ssl_wrap_socket_impl` |
| [backend/.local/task52-eval-deps/urllib3/util/ssl_match_hostname.py](../../backend/.local/task52-eval-deps/urllib3/util/ssl_match_hostname.py) | `CertificateError`, `_dnsname_match`, `_ipaddress_match`, `match_hostname` |
| [backend/.local/task52-eval-deps/urllib3/util/ssltransport.py](../../backend/.local/task52-eval-deps/urllib3/util/ssltransport.py) | `SSLTransport` |
| [backend/.local/task52-eval-deps/urllib3/util/timeout.py](../../backend/.local/task52-eval-deps/urllib3/util/timeout.py) | `_TYPE_DEFAULT`, `Timeout` |
| [backend/.local/task52-eval-deps/urllib3/util/url.py](../../backend/.local/task52-eval-deps/urllib3/util/url.py) | `Url`, `_encode_invalid_chars`, `_encode_invalid_chars`, `_encode_invalid_chars`, `_remove_path_dot_segments`, `_normalize_host`, `_normalize_host`, `_normalize_host`, `_decode_percent_encoding`, `_normalize_host_percent_encoding`, `_normalize_zone_id_percent_encoding`, `_idna_encode`, `_encode_target`, `parse_url` |
| [backend/.local/task52-eval-deps/urllib3/util/util.py](../../backend/.local/task52-eval-deps/urllib3/util/util.py) | `to_bytes`, `to_str`, `reraise` |
| [backend/.local/task52-eval-deps/urllib3/util/wait.py](../../backend/.local/task52-eval-deps/urllib3/util/wait.py) | `select_wait_for_socket`, `poll_wait_for_socket`, `_have_working_poll`, `wait_for_socket`, `wait_for_read`, `wait_for_write` |
| [backend/acceptance_fixtures.py](../../backend/acceptance_fixtures.py) | `search_fixture`, `FixtureAI` |
| [backend/admission.py](../../backend/admission.py) | `AdmissionError`, `Lease`, `AdmissionStore`, `LocalLease`, `LocalAdmission`, `fingerprint`, `validate_environment` |
| [backend/advanced_planning.py](../../backend/advanced_planning.py) | `enabled`, `AdvancedAnswerError`, `AdvancedInput`, `PublicStop`, `PublicLeg`, `PublicOption`, `AdvancedResult`, `directions_link`, `maps_link`, `Session`, `Sessions` |
| [backend/advanced_preferences.py](../../backend/advanced_preferences.py) | `Choice`, `DwellAnswer`, `AdvancedEdits` |
| [backend/advanced_routing.py](../../backend/advanced_routing.py) | `_ancestors`, `Visit`, `OmittedStop`, `AdvancedLeg`, `TravelCheck`, `TotalBetweenCheck`, `OriginEvidence`, `AdvancedRouteCandidate`, `HoursExclusion`, `AdvancedRoutingResult`, `_signature`, `_balanced_paths`, `_shortlist`, `_gap`, `_topology`, `_check`, `_total_check`, `AdvancedRouter` |
| [backend/advanced_timing.py](../../backend/advanced_timing.py) | `explicit_departure`, `DurationRange`, `_bounds`, `_plus`, `TimingReason`, `Projection`, `TimedVisit`, `TimedCandidate`, `AdvancedTimingResult`, `_combine`, `_limit`, `_project`, `_leg_range`, `_visit_hours`, `_evaluate`, `evaluate_advanced_timing` |
| [backend/ai/__init__.py](../../backend/ai/__init__.py) | `Interpretation`, `parse_interpretation`, `AIError`, `AIProvider`, `AISettings`, `create_provider` |
| [backend/ai/ollama.py](../../backend/ai/ollama.py) | `example`, `OllamaProvider` |
| [backend/ai/smoke.py](../../backend/ai/smoke.py) | `main` |
| [backend/ai/smoke_dates.py](../../backend/ai/smoke_dates.py) | `main` |
| [backend/ai/smoke_interpretation.py](../../backend/ai/smoke_interpretation.py) | `main` |
| [backend/ai/smoke_journey.py](../../backend/ai/smoke_journey.py) | `semantic_errors`, `main` |
| [backend/ai/smoke_reliability.py](../../backend/ai/smoke_reliability.py) | `main` |
| [backend/ai/smoke_validation.py](../../backend/ai/smoke_validation.py) | `main` |
| [backend/ai_readiness.py](../../backend/ai_readiness.py) | `snapshot`, `start` |
| [backend/benchmark_acceptance49.py](../../backend/benchmark_acceptance49.py) | `run` |
| [backend/between_policy.py](../../backend/between_policy.py) | `between_intent`, `mask` |
| [backend/continuation_status.py](../../backend/continuation_status.py) | `continuation_status`, `known_route_work` |
| [backend/database_check.py](../../backend/database_check.py) | `DatabaseCheckError`, `connection_settings`, `verify_database`, `main` |
| [backend/database_migrate.py](../../backend/database_migrate.py) | `MigrationError`, `migration_files`, `applied_migrations`, `migrate`, `verify_schema`, `main` |
| [backend/date_resolution.py](../../backend/date_resolution.py) | `CalendarIssue`, `DateExpressionError`, `DateResolution`, `_named_date_parts`, `complete_year_answer`, `_date_expression`, `_clock`, `_time_expression`, `_wall_issue`, `resolve_datetime` |
| [backend/dev_start.py](../../backend/dev_start.py) | `read_private`, `environment`, `port_available`, `main` |
| [backend/development_cost.py](../../backend/development_cost.py) | `AccountingError`, `daily_limit`, `dispatch`, `DevelopmentCost` |
| [backend/development_diagnostics.py](../../backend/development_diagnostics.py) | `record`, `snapshot` |
| [backend/discover_places.py](../../backend/discover_places.py) | `main` |
| [backend/discovery_inventory.py](../../backend/discovery_inventory.py) | `merge_inventory` |
| [backend/display_duration.py](../../backend/display_duration.py) | `seconds_text` |
| [backend/duration_preparation.py](../../backend/duration_preparation.py) | `normalize_explicit_durations` |
| [backend/evaluation/__init__.py](../../backend/evaluation/__init__.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [backend/evaluation/run.py](../../backend/evaluation/run.py) | `main` |
| [backend/evidence.py](../../backend/evidence.py) | `Source`, `Claim`, `DisplayAttribution`, `EvidenceLabels`, `google_attribution`, `venue_source`, `_leaves`, `venue_labels`, `distinct_venue_labels`, `route_labels`, `CheckLabel`, `FeasibilityLabels`, `feasibility_labels`, `fictional_labels`, `user_detail_label` |
| [backend/failures.py](../../backend/failures.py) | `correlation`, `evidence`, `provider_code`, `provider_status` |
| [backend/feasibility.py](../../backend/feasibility.py) | `EvidenceStop`, `FeasibilityInput`, `EvidenceCheck`, `FeasibilityResult`, `_state`, `_local_instant`, `_covers`, `_hours`, `evaluate_feasibility`, `filter_feasible_candidates` |
| [backend/hours_fixtures49.py](../../backend/hours_fixtures49.py) | `fixture_hours` |
| [backend/interpretation.py](../../backend/interpretation.py) | `activity_category`, `ManualPreferences`, `ClarificationAnswers`, `PendingClarification`, `ClarificationQuestion`, `InterpretationInput`, `InterpretationContext`, `InterpretationResult`, `has_minimum_spending`, `source_constraint_issues`, `advanced_travel_fields`, `interpret_request` |
| [backend/journey.py](../../backend/journey.py) | `JourneyModel`, `Duration`, `RequestedStop`, `OrderConstraint`, `Endpoint`, `Deadline`, `SharedPlace`, `Journey`, `duration_value`, `duration_relation`, `normalize_explicit_durations`, `normalize_extracted_references`, `is_reference_occurrence`, `validate_journey`, `unresolved_return_clause`, `ambiguous_return`, `missing_return_confirmation` |
| [backend/journey_fixtures.py](../../backend/journey_fixtures.py) | `reply`, `FixtureAI` |
| [backend/location_context.py](../../backend/location_context.py) | `relative_destination`, `timezone_for`, `DestinationContext`, `outing_problem`, `anchor_compatible` |
| [backend/location_fixtures.py](../../backend/location_fixtures.py) | `place`, `spatial_search_fixture`, `acceptance_search_fixture`, `acceptance_matrix_fixture`, `neighborhood_fixture` |
| [backend/location_policy.py](../../backend/location_policy.py) | `ContractModel`, `FirstTravel`, `Geography`, `first_intent`, `geographic_intent`, `effective_max`, `radius`, `first_measure`, `exceeds` |
| [backend/main.py](../../backend/main.py) | `lifespan`, `local_request_timing`, `failure`, `exploration_local_only`, `health`, `invalid_request`, `generate_plan`, `interpret_outing`, `interpret_endpoint`, `planning_mode`, `ContactRequest`, `venue_details`, `OptionsRequest`, `more_options`, `starting_places`, `starting_areas`, `generate_endpoint`, `options_endpoint`, `private_plan_boundary`, `persistence_response`, `save_endpoint`, `reopen_endpoint`, `safe_application_errors`, `refresh_saved_plan`, `development_diagnostics`, `advanced_endpoint` |
| [backend/migrations/0001_initial_planning.sql](../../backend/migrations/0001_initial_planning.sql) | SQL schema/migration statements |
| [backend/migrations/0002_private_saved_plans.sql](../../backend/migrations/0002_private_saved_plans.sql) | SQL schema/migration statements |
| [backend/mock_data.py](../../backend/mock_data.py) | `_Definition`, `_Tier`, `_Fixture`, `load_mock_venues`, `get_mock_venues`, `get_mock_venue`, `available_activities` |
| [backend/mock_origin.py](../../backend/mock_origin.py) | `apply_mock_origin` |
| [backend/mock_surprise.py](../../backend/mock_surprise.py) | `mock_surprise`, `more_mock_surprise` |
| [backend/models.py](../../backend/models.py) | `ContractModel`, `calendar_date`, `ActivityType`, `CostPreference`, `TransportationMode`, `DataStatus`, `DataQuality`, `OutingRequest`, `PlanningRequest`, `TimeWindow`, `HoursRange`, `HoursEvidence`, `VenueIdentity`, `Venue`, `ScheduledEvent`, `ItineraryStop`, `Itinerary`, `PlanningError`, `PlanningResult`, `CandidateStop`, `fixed_times_compatible`, `CandidateItinerary`, `CandidateGenerationResult`, `ConstraintIssue`, `PriceQuote`, `TravelQuote`, `PlannedStop`, `RecommendationReason`, `RankedItinerary`, `ContinuationStatus`, `RankingResult` |
| [backend/operations.py](../../backend/operations.py) | `BoundedLogHandler`, `event`, `stage`, `snapshot` |
| [backend/option_sessions.py](../../backend/option_sessions.py) | `OptionSessions` |
| [backend/ordering_shadow.py](../../backend/ordering_shadow.py) | `_record`, `capture_local_test`, `_compute`, `interpret_observed`, `observe` |
| [backend/performance.py](../../backend/performance.py) | `record_ai`, `snapshot`, `stage`, `provider_snapshot` |
| [backend/persistence_config.py](../../backend/persistence_config.py) | `runtime_settings` |
| [backend/persistence_setup.py](../../backend/persistence_setup.py) | `main` |
| [backend/places.py](../../backend/places.py) | `DiscoveryError`, `DiscoveryModel`, `SearchArea`, `StartingLocation`, `TravelConstraints`, `DiscoveryRequest`, `search_body`, `DiscoveryCandidate`, `DiscoveryResult`, `parse_response`, `require_development_discovery`, `PlacesDiscovery` |
| [backend/places_transport.py](../../backend/places_transport.py) | `_AuthRequest`, `access_token`, `text_search` |
| [backend/planner.py](../../backend/planner.py) | `supports_location`, `_pools`, `_walk`, `iter_itinerary_candidates`, `generate_candidates` |
| [backend/planning_admission.py](../../backend/planning_admission.py) | `AdmissionError`, `_plain`, `_Scope`, `AdmissionReceipt`, `_Entry`, `_Lease`, `AdmissionOutcome`, `AdmissionRegistry`, `_check`, `_fresh_ordinary`, `guard_ordinary`, `guard_handoff`, `guard_provider`, `guard_deferred`, `require_foundation_for_test` |
| [backend/planning_diagnostics.py](../../backend/planning_diagnostics.py) | `_ids`, `merge_discovery_audits`, `empty_coverage`, `planning_coverage`, `coverage_notes`, `bottlenecks` |
| [backend/planning_hours.py](../../backend/planning_hours.py) | `typical_hours`, `venue_hours` |
| [backend/provider_budget.py](../../backend/provider_budget.py) | `ProviderLimitError`, `ProviderSettings`, `ProviderBudget`, `OutingBudget`, `local_real_enabled`, `exploration_environment` |
| [backend/provider_errors.py](../../backend/provider_errors.py) | `classify`, `attach_accounting` |
| [backend/provider_work.py](../../backend/provider_work.py) | `check_cancelled`, `wait_for_capacity`, `run_work` |
| [backend/ranking.py](../../backend/ranking.py) | `mock_price`, `simulated_travel`, `_windows`, `evaluate_candidate`, `score_candidates`, `_select`, `rank_candidates`, `recommend_plans` |
| [backend/real_fixture_server.py](../../backend/real_fixture_server.py) | `main` |
| [backend/real_fixtures.py](../../backend/real_fixtures.py) | `search_fixture`, `matrix_fixture`, `details_fixture`, `paginated_search_fixture`, `bowling_diagnostic_fixture` |
| [backend/real_planning.py](../../backend/real_planning.py) | `PlannerInput`, `real_plans`, `empty`, `more_real_plans`, `discovery_activities`, `can_discover`, `sequential_can_discover`, `expand_venue_discovery` |
| [backend/refinement_fixtures.py](../../backend/refinement_fixtures.py) | `place`, `search_fixture`, `FixtureAI`, `refreshed` |
| [backend/request_middleware.py](../../backend/request_middleware.py) | `RequestManagement` |
| [backend/retail.py](../../backend/retail.py) | `RetailIntent`, `intent`, `query`, `matches_brand`, `verdict` |
| [backend/routes.py](../../backend/routes.py) | `RouteError`, `RouteModel`, `RoutePoint`, `AuthorizedStart`, `RouteRequest`, `DirectedRouteRequest`, `RouteLeg`, `RouteResult`, `RouteCalculator`, `require_development_routes`, `waypoint`, `matrix_body`, `same_location`, `location_key`, `plan_matrices`, `batch_pairs`, `_leg`, `parse_matrix`, `GoogleRouteCalculator`, `current_evidence` |
| [backend/routes_transport.py](../../backend/routes_transport.py) | `_validate_basic_body`, `compute_matrix` |
| [backend/routing_expansion.py](../../backend/routing_expansion.py) | `select_stage` |
| [backend/routing_shortlist.py](../../backend/routing_shortlist.py) | `shortlist`, `expansion_width`, `balanced_following` |
| [backend/saved_advanced.py](../../backend/saved_advanced.py) | `redact_source`, `AdvancedSaved`, `issue_advanced` |
| [backend/saved_plans.py](../../backend/saved_plans.py) | `SaveRequest`, `OpenRequest`, `FictionalFacts`, `SavedStop`, `FictionalMetrics`, `SavedOption`, `SavedDocument`, `PersistenceError`, `safe_document`, `Receipts`, `digest`, `database`, `insert`, `write_document`, `read_document`, `save`, `reopen` |
| [backend/saved_refresh.py](../../backend/saved_refresh.py) | `RefreshRequest`, `fetch_saved_details`, `verified_maps_url`, `RefreshSessions`, `automatic_details_enabled`, `refresh_issue`, `saved_hours_enabled` |
| [backend/search_fields.py](../../backend/search_fields.py) | `hours_enabled`, `ratings_enabled`, `enterprise_search`, `search_mask` |
| [backend/sequential_discovery.py](../../backend/sequential_discovery.py) | `mode`, `search_area`, `key`, `add_job`, `retain_job_results`, `run_job`, `anchors`, `initialize`, `can_expand`, `next_region`, `expand` |
| [backend/source_preparation.py](../../backend/source_preparation.py) | `Occurrence`, `OccurrenceMapping`, `PreparedSource`, `strict_extraction`, `_fields`, `_spans`, `_bindings`, `prepare_source`, `observe_effective` |
| [backend/source_text.py](../../backend/source_text.py) | `comparable`, `verbatim`, `valid_input` |
| [backend/spatial_beam.py](../../backend/spatial_beam.py) | `candidates` |
| [backend/starting_areas.py](../../backend/starting_areas.py) | `StartingAreaQuery`, `References`, `suggest_starting_areas`, `_suggest_starting_areas` |
| [backend/starting_places.py](../../backend/starting_places.py) | `verified_start_calendar`, `StartingPlaceQuery`, `lookup_starting_places` |
| [backend/starting_scoring.py](../../backend/starting_scoring.py) | `regions`, `compare` |
| [backend/stop_resolution.py](../../backend/stop_resolution.py) | `ResolvedCandidate`, `ResolvedStop`, `ResolvedJourney`, `_label`, `_words`, `_identity`, `_discovery_activity`, `StopResolver` |
| [backend/strict_local_fixtures.py](../../backend/strict_local_fixtures.py) | `local_places`, `local_matrix`, `local_origin` |
| [backend/surprise.py](../../backend/surprise.py) | `weighted`, `quality`, `quality_qualified`, `venue_order`, `select`, `region`, `record`, `validate_beginning` |
| [backend/test_acceptance46.py](../../backend/test_acceptance46.py) | Offline test/fixture declarations: `TravelAcceptance`, `OptionsAcceptance` |
| [backend/test_acceptance_regeneration49.py](../../backend/test_acceptance_regeneration49.py) | Offline test/fixture declarations: `Regeneration` |
| [backend/test_acceptance_repair.py](../../backend/test_acceptance_repair.py) | Offline test/fixture declarations: `InterpretationRepairTests`, `FlowRepairTests`, `ContinuationRepairTests`, `OriginCalendarRepairTests`, `OrdinaryParityMatrixTests`, `DateCorrectionRepairTests`, `BeyondDiscoveryRepairTests` |
| [backend/test_acceptance_saved_cinema.py](../../backend/test_acceptance_saved_cinema.py) | Offline test/fixture declarations: `CinemaAcceptance`, `RuntimeConfiguration`, `SafeDiagnostics` |
| [backend/test_activity_audit.py](../../backend/test_activity_audit.py) | Offline test/fixture declarations: `ActivityAudit` |
| [backend/test_advanced_planning.py](../../backend/test_advanced_planning.py) | Offline test/fixture declarations: `IntegrationTests`, `HostedAdvancedTests` |
| [backend/test_advanced_routing.py](../../backend/test_advanced_routing.py) | Offline test/fixture declarations: `start`, `activity`, `named`, `record`, `AdvancedRoutingTests` |
| [backend/test_advanced_timing.py](../../backend/test_advanced_timing.py) | Offline test/fixture declarations: `duration`, `context`, `AdvancedTimingTests` |
| [backend/test_ai.py](../../backend/test_ai.py) | Offline test/fixture declarations: `extraction`, `AITests` |
| [backend/test_api.py](../../backend/test_api.py) | Offline test/fixture declarations: `PlanningApiTests` |
| [backend/test_bowling_diagnosis46.py](../../backend/test_bowling_diagnosis46.py) | Offline test/fixture declarations: `BowlingDiagnosis` |
| [backend/test_calendar_dates.py](../../backend/test_calendar_dates.py) | Offline test/fixture declarations: `NamedCalendarTests` |
| [backend/test_clarification.py](../../backend/test_clarification.py) | Offline test/fixture declarations: `ClarificationTests` |
| [backend/test_cloud_model52.py](../../backend/test_cloud_model52.py) | Offline test/fixture declarations: `output`, `response`, `HarnessTests`, `load_tests` |
| [backend/test_cloud_model52_audit.py](../../backend/test_cloud_model52_audit.py) | Offline test/fixture declarations: `CorrectionTests`, `load_tests` |
| [backend/test_cloud_model52_batch.py](../../backend/test_cloud_model52_batch.py) | Offline test/fixture declarations: `SmallBatchTests`, `load_tests` |
| [backend/test_cloud_model52_live.py](../../backend/test_cloud_model52_live.py) | Offline test/fixture declarations: `LiveBoundaryTests`, `load_tests` |
| [backend/test_cloud_model52_offline.py](../../backend/test_cloud_model52_offline.py) | Offline test/fixture declarations: `fixture`, `reference`, `OfflineComparisonTests`, `OrderingContractTests`, `ProposalTests`, `load_tests` |
| [backend/test_cloud_model52_ordering.py](../../backend/test_cloud_model52_ordering.py) | Offline test/fixture declarations: `cases`, `reply`, `OrderingSafetyTests`, `load_tests` |
| [backend/test_cloud_model52_ordering_v2.py](../../backend/test_cloud_model52_ordering_v2.py) | Offline test/fixture declarations: `cases`, `CompatibilityTests` |
| [backend/test_cloud_model52_ordering_v3.py](../../backend/test_cloud_model52_ordering_v3.py) | Offline test/fixture declarations: `cases`, `OrderingPolicyTests` |
| [backend/test_cloud_model52_ordering_v4.py](../../backend/test_cloud_model52_ordering_v4.py) | Offline test/fixture declarations: `cases`, `ReleaseGapTests` |
| [backend/test_cloud_model52_revision.py](../../backend/test_cloud_model52_revision.py) | Offline test/fixture declarations: `RevisionTests`, `load_tests` |
| [backend/test_cloud_model52_semantics.py](../../backend/test_cloud_model52_semantics.py) | Offline test/fixture declarations: `SemanticComparatorTests`, `load_tests` |
| [backend/test_cloud_model52_v4.py](../../backend/test_cloud_model52_v4.py) | Offline test/fixture declarations: `V4ReadinessTests`, `load_tests` |
| [backend/test_cloud_model52_v4_live.py](../../backend/test_cloud_model52_v4_live.py) | Offline test/fixture declarations: `readiness`, `review`, `ContinuationTests`, `load_tests` |
| [backend/test_database_check.py](../../backend/test_database_check.py) | Offline test/fixture declarations: `DatabaseCheckTests` |
| [backend/test_database_schema.py](../../backend/test_database_schema.py) | Offline test/fixture declarations: `MigrationOfflineTests`, `HostedSchemaTests` |
| [backend/test_database_security.py](../../backend/test_database_security.py) | Offline test/fixture declarations: `SecurityTests`, `HostedSecurityTests` |
| [backend/test_date_resolution.py](../../backend/test_date_resolution.py) | Offline test/fixture declarations: `DateResolutionTests` |
| [backend/test_dev_lifecycle.py](../../backend/test_dev_lifecycle.py) | Offline test/fixture declarations: `wait`, `free`, `health`, `processes`, `descendants`, `Terminal`, `Lifecycle` |
| [backend/test_discovery100.py](../../backend/test_discovery100.py) | Offline test/fixture declarations: `Pools`, `Classification`, `PipelineAlternatives`, `Disconnect` |
| [backend/test_discovery_acceptance.py](../../backend/test_discovery_acceptance.py) | Offline test/fixture declarations: `Accounting`, `Geography`, `Discovery` |
| [backend/test_duration_b2.py](../../backend/test_duration_b2.py) | Offline test/fixture declarations: `DurationExtractionTests` |
| [backend/test_editable_preferences.py](../../backend/test_editable_preferences.py) | Offline test/fixture declarations: `EditablePreferencesTests`, `HostedEditablePreferencesTests` |
| [backend/test_evidence.py](../../backend/test_evidence.py) | Offline test/fixture declarations: `venue`, `EvidenceTests` |
| [backend/test_expanded_limits46.py](../../backend/test_expanded_limits46.py) | Offline test/fixture declarations: `ExpandedLimits` |
| [backend/test_exploration.py](../../backend/test_exploration.py) | Offline test/fixture declarations: `ExplorationTests` |
| [backend/test_feasibility.py](../../backend/test_feasibility.py) | Offline test/fixture declarations: `endpoint`, `period`, `stop`, `route`, `request`, `FeasibilityTests` |
| [backend/test_final50e.py](../../backend/test_final50e.py) | Offline test/fixture declarations: `extracted`, `ConsolidatedTests`, `NowHoursTests`, `load_tests` |
| [backend/test_final_acceptance49.py](../../backend/test_final_acceptance49.py) | Offline test/fixture declarations: `ContinuationTests`, `SelectedRefreshTests`, `StartupTests` |
| [backend/test_followup_repair.py](../../backend/test_followup_repair.py) | Offline test/fixture declarations: `FollowupTests` |
| [backend/test_health.py](../../backend/test_health.py) | Offline test/fixture declarations: `HealthTest` |
| [backend/test_historical_preflight.py](../../backend/test_historical_preflight.py) | Offline test/fixture declarations: `HistoricalPreflightTests` |
| [backend/test_hitec_geography.py](../../backend/test_hitec_geography.py) | Offline test/fixture declarations: `components`, `HitecSpellingTests`, `HitecPlanningTests` |
| [backend/test_hours_acceptance49.py](../../backend/test_hours_acceptance49.py) | Offline test/fixture declarations: `HoursAcceptance` |
| [backend/test_interpretation.py](../../backend/test_interpretation.py) | Offline test/fixture declarations: `extraction`, `InterpretationTests` |
| [backend/test_journey.py](../../backend/test_journey.py) | Offline test/fixture declarations: `JourneyTests` |
| [backend/test_location_acceptance.py](../../backend/test_location_acceptance.py) | Offline test/fixture declarations: `leg`, `Acceptance`, `Pipeline` |
| [backend/test_location_first.py](../../backend/test_location_first.py) | Offline test/fixture declarations: `LocationFirst` |
| [backend/test_location_lifecycle.py](../../backend/test_location_lifecycle.py) | Offline test/fixture declarations: `GeographyLifecycle`, `LifecycleAPI` |
| [backend/test_mock_data.py](../../backend/test_mock_data.py) | Offline test/fixture declarations: `fingerprint`, `MockDataTests` |
| [backend/test_models.py](../../backend/test_models.py) | Offline test/fixture declarations: `venue`, `event`, `itinerary`, `RequestTests`, `VenueAndScheduleTests`, `ResultTests` |
| [backend/test_open_exploration.py](../../backend/test_open_exploration.py) | Offline test/fixture declarations: `OpenExploration` |
| [backend/test_ordering_enforcement_design.py](../../backend/test_ordering_enforcement_design.py) | Offline test/fixture declarations: `case`, `EnforcementDesignBoundaries` |
| [backend/test_ordering_shadow.py](../../backend/test_ordering_shadow.py) | Offline test/fixture declarations: `post_asgi`, `ShadowIsolationTests` |
| [backend/test_phase_b.py](../../backend/test_phase_b.py) | Offline test/fixture declarations: `PhaseBTests` |
| [backend/test_places.py](../../backend/test_places.py) | Offline test/fixture declarations: `place`, `request`, `DiscoveryTests`, `TransportTests` |
| [backend/test_planner.py](../../backend/test_planner.py) | Offline test/fixture declarations: `CandidateTests` |
| [backend/test_planning_admission.py](../../backend/test_planning_admission.py) | Offline test/fixture declarations: `PlanningAdmissionTests` |
| [backend/test_provider_budget.py](../../backend/test_provider_budget.py) | Offline test/fixture declarations: `ProviderBudgetTests` |
| [backend/test_ranking.py](../../backend/test_ranking.py) | Offline test/fixture declarations: `candidate`, `ordinary`, `evaluate`, `RankingTests` |
| [backend/test_real_planning.py](../../backend/test_real_planning.py) | Offline test/fixture declarations: `outing`, `RealPlanningTests` |
| [backend/test_refinements49.py](../../backend/test_refinements49.py) | Offline test/fixture declarations: `RetailTests`, `RefreshTests`, `StartupCalendarRanking` |
| [backend/test_reliability.py](../../backend/test_reliability.py) | Offline test/fixture declarations: `ReliabilityTests` |
| [backend/test_request_management.py](../../backend/test_request_management.py) | Offline test/fixture declarations: `AdmissionTests`, `MiddlewareTests` |
| [backend/test_required_dates.py](../../backend/test_required_dates.py) | Offline test/fixture declarations: `RequiredDateTests` |
| [backend/test_routes.py](../../backend/test_routes.py) | Offline test/fixture declarations: `point`, `element`, `response`, `route_request`, `RouteTests`, `RouteTransportTests` |
| [backend/test_saved_details_reliability.py](../../backend/test_saved_details_reliability.py) | Offline test/fixture declarations: `RefreshReliability`, `ReadinessTests` |
| [backend/test_saved_plans.py](../../backend/test_saved_plans.py) | Offline test/fixture declarations: `fixture`, `request_for`, `OfflinePersistenceTests`, `HostedPersistenceTests` |
| [backend/test_search_hours49.py](../../backend/test_search_hours49.py) | Offline test/fixture declarations: `SearchHours` |
| [backend/test_session_capacity49.py](../../backend/test_session_capacity49.py) | Offline test/fixture declarations: `SessionRetention` |
| [backend/test_sharing_ux49.py](../../backend/test_sharing_ux49.py) | Offline test/fixture declarations: `SharedViews`, `WebsiteTests` |
| [backend/test_stop_resolution.py](../../backend/test_stop_resolution.py) | Offline test/fixture declarations: `place`, `stop`, `ResolutionTests`, `EndpointClarificationTests` |
| [backend/test_strict_local.py](../../backend/test_strict_local.py) | Offline test/fixture declarations: `StrictLocal` |
| [backend/test_summary_edits.py](../../backend/test_summary_edits.py) | Offline test/fixture declarations: `SummaryEditTests` |
| [backend/test_surprise.py](../../backend/test_surprise.py) | Offline test/fixture declarations: `Selection`, `Pipeline` |
| [backend/test_task46_improvements.py](../../backend/test_task46_improvements.py) | Offline test/fixture declarations: `ImprovementTests` |
| [backend/test_task50e_coverage_unicode.py](../../backend/test_task50e_coverage_unicode.py) | Offline test/fixture declarations: `InitialCoverage`, `UnicodeSources`, `SafeInterpreterErrors` |
| [backend/test_task50e_final_acceptance.py](../../backend/test_task50e_final_acceptance.py) | Offline test/fixture declarations: `AcceptanceRepairTests`, `HostedClosedVisitTests` |
| [backend/test_task50e_legs_exploration.py](../../backend/test_task50e_legs_exploration.py) | Offline test/fixture declarations: `ReturnPhrases`, `LegsExploration` |
| [backend/test_task52_ordering_v5.py](../../backend/test_task52_ordering_v5.py) | **Offline V5 research committed independently as b1efe96**; Offline test/fixture declarations: `reply`, `V5OrderingTests` |
| [backend/test_task52_q1.py](../../backend/test_task52_q1.py) | Offline test/fixture declarations: `QualificationContractTests` |
| [backend/test_task52_q2.py](../../backend/test_task52_q2.py) | Offline test/fixture declarations: `ProviderCompatibilityTests` |
| [backend/test_task52_q3.py](../../backend/test_task52_q3.py) | Offline test/fixture declarations: `Refused`, `FictionalProtocol`, `ContinuationProposalTests` |
| [backend/test_task52_q4a.py](../../backend/test_task52_q4a.py) | Offline test/fixture declarations: `wire`, `envelope`, `fake_responses`, `child_crash`, `child_compete`, `SuccessorTests` |
| [backend/test_task52_q4b.py](../../backend/test_task52_q4b.py) | Offline test/fixture declarations: `RealShapeFiction`, `CompatibilityTests` |
| [backend/test_task52_q4c.py](../../backend/test_task52_q4c.py) | Offline test/fixture declarations: `SyntheticKeys`, `scope`, `execute`, `review`, `crash_child`, `competitor`, `Q4CTests` |
| [backend/test_task52_version_review.py](../../backend/test_task52_version_review.py) | Offline test/fixture declarations: `VersionReviewTests`, `AdmissionReviewThreatTests` |
| [backend/test_testing_clock.py](../../backend/test_testing_clock.py) | Offline test/fixture declarations: `request`, `CalendarFixtureTests` |
| [backend/test_travel_mode49.py](../../backend/test_travel_mode49.py) | Offline test/fixture declarations: `AI`, `InterpretationModes`, `PlannerModes` |
| [backend/test_validation.py](../../backend/test_validation.py) | Offline test/fixture declarations: `ValidationTests` |
| [backend/test_venue_normalization.py](../../backend/test_venue_normalization.py) | Offline test/fixture declarations: `enriched`, `normalize`, `NormalizationTests` |
| [backend/test_venue_quality.py](../../backend/test_venue_quality.py) | Offline test/fixture declarations: `venue`, `QualityTests` |
| [backend/testing_clock.py](../../backend/testing_clock.py) | `_datetime_at`, `calendar_clock`, `route_evidence_clock`, `fixture_api` |
| [backend/travel_classification.py](../../backend/travel_classification.py) | `number`, `display_measure`, `classify`, `select_diverse`, `deviation_penalty`, `limit_notice` |
| [backend/travel_constraints.py](../../backend/travel_constraints.py) | `travel_evidence`, `exclusive_limit`, `resolved_travel_label`, `normalize_verbatim_travel` |
| [backend/travel_mode.py](../../backend/travel_mode.py) | `is_walking_route_phrase`, `resolve_mode` |
| [backend/travel_mode_fixtures.py](../../backend/travel_mode_fixtures.py) | `matrix` |
| [backend/validation_phases.py](../../backend/validation_phases.py) | `LegacyDisposition`, `validate_legacy`, `interpret_legacy_result` |
| [backend/venue_details.py](../../backend/venue_details.py) | `contact_links`, `fetch_details`, `DetailsSessions` |
| [backend/venue_geography.py](../../backend/venue_geography.py) | `normalized`, `distance_m`, `geographic_reason`, `geographic_detail` |
| [backend/venue_models.py](../../backend/venue_models.py) | `public_url`, `Coordinates`, `Attribution`, `HoursPoint`, `HoursPeriod`, `OpeningHours`, `PlaceTimeZone`, `PriceAmount`, `PriceRange`, `ContainingPlace`, `VenueFacts` |
| [backend/venue_normalization.py](../../backend/venue_normalization.py) | `NormalizationError`, `_object`, `_date`, `_hours`, `_money`, `_price_range`, `_attributions`, `_supplied`, `_assign`, `normalize_google_place`, `normalize_google_places`, `normalize_discovery_candidates` |
| [backend/venue_quality.py](../../backend/venue_quality.py) | `Relevance`, `DistinctVenue`, `QualityResult`, `relevance`, `_key`, `_alias`, `_merge`, `assess_candidates` |

## Complete scripts source and test index

Local lifecycle tools, offline benchmarks/replays, frozen cloud evaluation and Q1–Q4C protocols. A filename containing live is not authorization to execute it. V5 files initially untracked were independently committed as b1efe96 during course authoring; the prototype remains offline.

| File | Top-level declarations / reading cue |
|---|---|
| [scripts/benchmark50e.py](../../scripts/benchmark50e.py) | `admin`, `Meter` |
| [scripts/benchmark50e_edits.py](../../scripts/benchmark50e_edits.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [scripts/benchmark51.py](../../scripts/benchmark51.py) | `measure`, `main` |
| [scripts/cloud_model52.py](../../scripts/cloud_model52.py) | `digest`, `corpus`, `schema`, `wire_schema`, `compact_examples`, `messages`, `metadata`, `Adapter`, `AdmissionError`, `Ledger`, `exclusive`, `timezone_for`, `validate`, `score`, `missing_properties`, `_run_one`, `run_one`, `run_matrix`, `corpus_review_template`, `review_template`, `adjudicate`, `summarize`, `main` |
| [scripts/cloud_model52_audit.py](../../scripts/cloud_model52_audit.py) | `append_json`, `correction_value`, `record_correction`, `effective_record` |
| [scripts/cloud_model52_batch.py](../../scripts/cloud_model52_batch.py) | `check_fresh`, `make_plan`, `run_next` |
| [scripts/cloud_model52_live.py](../../scripts/cloud_model52_live.py) | `private_json`, `credentials`, `HTTP`, `inference_path`, `allowed_paths`, `validate_google_request`, `count_body`, `prepare`, `acknowledged_legacy_failure`, `continuation_ledger`, `live`, `main` |
| [scripts/cloud_model52_offline.py](../../scripts/cloud_model52_offline.py) | `occurrences`, `article_projection`, `score` |
| [scripts/cloud_model52_ordering.py](../../scripts/cloud_model52_ordering.py) | `spans`, `bind_occurrences`, `reach`, `inspect_order` |
| [scripts/cloud_model52_ordering_compatibility.py](../../scripts/cloud_model52_ordering_compatibility.py) | `sha`, `fixture_reply`, `production`, `positive`, `brief`, `check_cases`, `negative_probes`, `_build`, `build`, `write_report` |
| [scripts/cloud_model52_ordering_policy_replay.py](../../scripts/cloud_model52_ordering_policy_replay.py) | `brief`, `compare_cases`, `_build`, `build` |
| [scripts/cloud_model52_ordering_release_replay.py](../../scripts/cloud_model52_ordering_release_replay.py) | `samples`, `_build`, `build` |
| [scripts/cloud_model52_ordering_replay.py](../../scripts/cloud_model52_ordering_replay.py) | `file_hash`, `cloud_rows`, `qwen_rows`, `replay` |
| [scripts/cloud_model52_ordering_v2.py](../../scripts/cloud_model52_ordering_v2.py) | `relation`, `inspect_order` |
| [scripts/cloud_model52_ordering_v3.py](../../scripts/cloud_model52_ordering_v3.py) | `digest`, `blank`, `source_analysis`, `inspect_order`, `project` |
| [scripts/cloud_model52_ordering_v4.py](../../scripts/cloud_model52_ordering_v4.py) | `digest`, `blank`, `start_finish`, `source_analysis`, `inspect_order`, `project` |
| [scripts/cloud_model52_proposal.py](../../scripts/cloud_model52_proposal.py) | `messages`, `payload`, `schema_stats`, `google_array_projection` |
| [scripts/cloud_model52_semantics.py](../../scripts/cloud_model52_semantics.py) | `reference_wire`, `reference_result`, `evidence_failures`, `compare_reference` |
| [scripts/cloud_model52_v4.py](../../scripts/cloud_model52_v4.py) | `configuration`, `payload`, `journal_snapshot`, `future_plan`, `count_body`, `CountingHTTP`, `prepare`, `anthropic_grammar_proposal` |
| [scripts/cloud_model52_v4_live.py](../../scripts/cloud_model52_v4_live.py) | `now`, `code_hashes`, `fresh`, `check_readiness`, `ExistingLedger`, `rows_and_root`, `approval`, `load_approval`, `verify_review`, `verify_record_evidence`, `approved_extension_checks`, `expected_endpoint_clarification`, `verified_rows`, `run_next`, `record_review`, `halt_after_review` |
| [scripts/dev-server.mjs](../../scripts/dev-server.mjs) | Imports, configuration, fixture registration or side-effect statements; read file |
| [scripts/security-scan.py](../../scripts/security-scan.py) | Imports, configuration, fixture registration or side-effect statements; read file |
| [scripts/task52_b2_behavior.py](../../scripts/task52_b2_behavior.py) | `sha`, `duration_cases`, `duration_trace` |
| [scripts/task52_b2_test_fixture.py](../../scripts/task52_b2_test_fixture.py) | `reference_data`, `reference_scope`, `OfflineUnitSuite` |
| [scripts/task52_historical_preflight.py](../../scripts/task52_historical_preflight.py) | `HistoricalReplayBlocked`, `requirement_pins`, `version_comparison`, `audit`, `require_execution_ready` |
| [scripts/task52_ordering_v5.py](../../scripts/task52_ordering_v5.py) | **Offline V5 research committed independently as b1efe96**; `Evidence`, `closure`, `proof`, `neutral_tail`, `source_analysis`, `inspect_order` |
| [scripts/task52_ordering_v5_identity.py](../../scripts/task52_ordering_v5_identity.py) | Offline V5 frozen manifest/build verification: `verify_document`, `verify` |
| [scripts/task52_ordering_v5_review.py](../../scripts/task52_ordering_v5_review.py) | **Offline V5 research committed independently as b1efe96**; `read`, `rubric_interpretation`, `amendment`, `impact`, `mapping`, `replay`, `proposal` |
| [scripts/task52_phase_b2_identity.py](../../scripts/task52_phase_b2_identity.py) | `verify` |
| [scripts/task52_phase_b_identity.py](../../scripts/task52_phase_b_identity.py) | `verify` |
| [scripts/task52_phase_b_replay.py](../../scripts/task52_phase_b_replay.py) | `digest`, `scenarios`, `run`, `characterize` |
| [scripts/task52_q1.py](../../scripts/task52_q1.py) | `sha`, `digest`, `verify`, `offline`, `private_hashes`, `replay` |
| [scripts/task52_q2.py](../../scripts/task52_q2.py) | `expanded`, `restored`, `schema_shape`, `proposals`, `historical_evidence`, `static_payloads` |
| [scripts/task52_q3.py](../../scripts/task52_q3.py) | `baseline`, `proposal` |
| [scripts/task52_q4a.py](../../scripts/task52_q4a.py) | `Refused`, `live_dispatch`, `plan`, `fsync_dir`, `private_create`, `crash`, `FakeTransport`, `FictionalFixture`, `Engine` |
| [scripts/task52_q4a_identity.py](../../scripts/task52_q4a_identity.py) | `verify` |
| [scripts/task52_q4a_scoring.py](../../scripts/task52_q4a_scoring.py) | `assess` |
| [scripts/task52_q4b.py](../../scripts/task52_q4b.py) | `Incompatible`, `_authorizer`, `_snapshot`, `_validate`, `inspect_original` |
| [scripts/task52_q4c_auth.py](../../scripts/task52_q4c_auth.py) | `Denied`, `canonical`, `parse`, `exact`, `digest`, `hash_field`, `stamp`, `fresh`, `public_key`, `Trust`, `fields`, `owner_data`, `rubric_data`, `permission_data`, `validate_data`, `Verified`, `_verify`, `verify` |
| [scripts/task52_q4c_identity.py](../../scripts/task52_q4c_identity.py) | `verify_build`, `binding` |
| [scripts/task52_q4c_protocol.py](../../scripts/task52_q4c_protocol.py) | `utc`, `die`, `admission`, `SyntheticJournal`, `Engine` |
| [scripts/task52_version_review.py](../../scripts/task52_version_review.py) | `VersionError`, `sha`, `digest`, `git`, `selected`, `source_root`, `identity`, `verify`, `replay_descriptor` |

## Outside the map

Private `.env`/database profiles, local cost/evaluation journals, credentials, installed dependencies, generated `.next` files and virtual environments are deliberately excluded. The course does not need their contents. V5 files now have committed source links at b1efe96; offline implementation is explicitly distinguished from proposed semantics review and absent runtime integration.

Newly reconciled V5 guides: [specification](../task52-ordering-policy-v5.md), [review checklist](../task52-ordering-v5-review-checklist.md) and [proposed full Q1 amendment](../task52-q1-rubric-v2-owner-list-PROPOSED.json).

## Deployment packaging

`deployment/Dockerfile.frontend` / `Dockerfile.backend`: locked-input non-root image recipes. `prepare_backend.py` and `backend-files.json`: explicit runtime payload. `backend_entry.py` / `frontend-entry.mjs`: strict container startup. `requirements-linux-amd64.lock`: Python wheel hashes. `*.cloudrun.yaml.tmpl`: placeholder-only private hosting review templates. `container-smoke.sh`: local image test, not deployment.

- `experiments/shared_state/application_grants.py` / `.sql`: inactive application grant and fictional inference composition.
- `experiments/shared_state/grant_rules.sql` / `grant_witness.sql`: protected pricing/limits and separate local epoch/exposure witness.
- `experiments/shared_state/grant-build.json` / `grant_identity.py`: distinct source profile; not a grant.
- `experiments/shared_state/run_grants.py` / `test_application_grants.py`: disposable two-database restore/concurrency and application-contract checks.

Native restart reconstruction: `experiments/shared_state/native_sessions.py` (inactive composition), `native_graph.py` (fixed typed factories), `native_sessions.sql`/`native_witness.sql` (synthetic protected transitions), `run_native.py`/`test_native_sessions.py` (disposable process/restore tests), `native-build.json`/`native_identity.py` (separate exact-source profile). [Report](../task52-native-session-reconstruction.md).

- `experiments/service_isolation/`: inactive synthetic workload authentication, native ticket routing, narrow delivery-only SQL adapter, four isolated service processes and adversarial container tests; no startup import or provider HTTP client.
- `docs/task52-service-isolation.md`: service/credential matrix, request and recovery contract, verified local limitations and next identity gate.

- `experiments/hosted_identity/`: inactive Google/IAP verification, scoped forwarding, witness nonce roles, isolated signed-fixture tests, Node proxy contract and exact source manifest; not included in normal startup/images.
- `docs/task52-staging/hosted-enrollment-v1.json`: inert identity/role/audience/secret/network/recovery review matrix; no resource is created.

- `lib/server-identity.ts`, `lib/identity-json.ts`: server-only verified metadata/IAP, bounded identity parsing/cache and public HTTP proofs.
- `lib/private-server-boundary.ts`: trusted installation and actual proxy seam; current status-only profile refuses business requests.
- `experiments/hosted_startup/`: local Next/FastAPI process checks, explicit source/bootstrap isolation and parent identity reuse.
- `deployment/private_startup.py`: nonlaunchable production dependency gate, not an override of `backend.main`.


## Inactive ordinary hosted workflow

- `experiments/ordinary_hosted/`: inactive public/native ordinary mapping, authenticated local facade, stable timestamp adapter and synthetic process tests.
- `lib/private-outing.ts`: optional browser ownership extension; `lib/planning-client.ts` propagates it only when returned by the private profile.


## Inactive ordinary private browser checkpoint

`components/private-ordinary-experience.tsx` is the inactive private UI; `lib/private-ordinary-client.ts` is its memory-only controller. `experiments/ordinary_ui/` contains the separately versioned local composition, read-only probes and tests. `app/api/private-ordinary/revoke/route.ts` returns404 without a selected profile.
