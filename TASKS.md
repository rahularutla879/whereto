# Milestones and tasks

Status baseline: October 20, 2026. Checked means implemented, not necessarily verified. Verification evidence belongs in [HANDOVER.md](HANDOVER.md). Stages are product goals, not claims that integrations already exist.

## Original roadmap — environment setup verification

Verified October 19, 2026; details and limits are recorded in HANDOVER.md.

- [x] Task 02 — VS Code present (1.85.1, in Downloads); Applications placement and terminal shortcut are optional.
- [x] Task 03 — Homebrew installed (7.0.10).
- [x] Task 04 — Git, Node.js, npm, and Python installed; checked Next.js/npm and FastAPI Python version requirements are satisfied. FastAPI installation is deferred until backend work.

## Original roadmap — Task 23: initialize the Python backend

- [x] Verify existing Python 3.12; create an ignored backend virtual environment and install essential dependencies.
- [x] Add FastAPI `GET /health` and server-side Next.js `GET /api/health` communication without changing the planner or design.
- [x] Document local startup and add backend/communication tests; pass automated tests, lint, TypeScript, build, and live HTTP communication checks. See HANDOVER.md for browser verification and limits.

Task 23 is complete. These backend foundations do not complete a real-data product integration milestone.

## Original roadmap — Task 24: define backend data structures

- [x] Inspect the working TypeScript contracts, catalog, planner, tests, and project guidance.
- [x] Define reusable Pydantic request, activity, constraint, venue/event, stop, itinerary, result/error, and data-quality types in one backend module.
- [x] Validate inputs and response consistency, preserve current JSON names, and test optional/unknown/fictional information, schedules, serialization, and FastAPI schema compatibility.
- [x] Pass backend and frontend tests, lint, TypeScript checks, and production build; review the complete diff and update relevant documentation. Evidence is in HANDOVER.md.

Task 24 is complete. Its contracts are reused by the later Task 26 candidate generator; no planning endpoint is implemented.

## Original roadmap — Task 25: create the Python mock venue dataset

- [x] Inspect and preserve the existing fictional venue/event data and all 29 supported categories.
- [x] Extract one shared JSON source; load and validate Python venue/event records using Task 24 models, with explicit fictional provenance and unknown hours.
- [x] Add reusable category/kind/date/ID retrieval and distinguish supported categories from categories with sample records; add no planning or optimization logic.
- [x] Test loading, validation, scheduled events, missing samples, and exact frontend consistency; pass backend/frontend tests, lint, TypeScript checks, and production build.
- [x] Review the complete diff and update continuity/architecture documentation. Evidence is in HANDOVER.md.

Task 25 is complete. The frontend still plans locally using the same shared dataset.

## Original roadmap — Task 26: build the Python itinerary generator

- [x] Inspect the TypeScript planner, Task 24 contracts, Task 25 loader/shared fixture, and project safeguards.
- [x] Generate deterministic ordered candidates, including repeated categories and explicit revisit handling, using validated shared records only.
- [x] Preserve identity, provenance, uncertainty, exact event dates/times; reject incompatible fixed events and explain missing records without partial outings.
- [x] Add candidate-specific Pydantic contracts and lazy enumeration without truncation; defer final filtering, scheduling, scoring, ranking, and frontend integration.
- [x] Pass backend/frontend tests, lint, TypeScript checks, and production build; review the full diff and update relevant documentation. See HANDOVER.md for evidence and limits.

Task 26 is complete. No planning endpoint or frontend connection is implemented.

## Original roadmap — Task 27: filter and rank Python itineraries

- [x] Inspect project guidance, Task 24 models, shared dataset, Task 26 generator, TypeScript planner/tests and continuity documents.
- [x] Evaluate hard budgets (person/group), travel (total/leg), capacity, ordered activities, opening/availability windows, event timing, dinner and outing time bounds.
- [x] Calculate costs, travel, durations and schedules with provenance; separate confirmed recommendations, provisional alternatives and known violations.
- [x] Normalize deterministic affordability/quality/convenience scores for all three spending modes; select up to three distinct options with structured explanations and actionable empty results.
- [x] Reuse the candidate generator and shared records; allow replacement price/travel providers without new dependencies, services or frontend integration.
- [x] Add backend correctness/integration tests; pass backend/frontend tests, lint, TypeScript checks and production build; review the full diff and update relevant documentation.

Task 27 is complete and is reused by Task 28.

## Original roadmap — Task 28: connect the website to Python

- [x] Preserve the homepage design, parser, manual override precedence and formatting.
- [x] Add validated FastAPI planning POST and reuse Task 23’s server-side Next.js proxy pattern.
- [x] Render Task 26–27 ranked results, unknown values, explicit fictional feasibility/provisional labels and clear errors; never fall back to TypeScript.
- [x] Add loading/duplicate-submit protection; isolate the retired planner for regression tests and keep static inspiration cards.
- [x] Test API, frontend integration, backend failures and the browser journey with both servers; pass all required checks and review the full diff.
- [x] Update startup/architecture/handover documentation and back up the tested changes to the existing private repository.

Task 28 is complete. Stop before Task 29. Real-data integrations remain future work.

## Prototype baseline — implemented

- [x] Homepage, outing request, example request, preference controls/reset, result cards, expandable itinerary, and empty states. Source inspected; browser/visual behavior unverified this session.
- [x] Local 29-category planner with fictional venues/events, date handling, mock schedules/capacity, budget/travel caps, and preference ranking. Existing suite passed 49/49 tests; see HANDOVER.md for coverage limits.
- [x] Lightweight documentation and continuity system.
- [x] Owner-approved private GitHub repository and verified initial source/documentation backup. GitHub setup and checkpoint details are recorded in HANDOVER.md.

## Stage 1 — basic planning with real venues and route information (current)

- [ ] **Next focused task:** select a real venue and routing data approach for Baltimore. Compare coverage, price, permitted use, credentials, and missing-data behavior. Record the recommendation and measurable integration acceptance criteria in DECISIONS.md; obtain approval before adopting paid services.
- [ ] Integrate real venue records with stable identity, source links, location, and honest handling of unknown hours/prices/availability. Keep fictional results clearly separated.
- [ ] Add actual inter-stop route information with explicit transport mode and source; replace mock travel in real-data plans.
- [ ] Produce a complete basic itinerary using real venue/route data, with actionable explanations when input or data is insufficient.
- [ ] Verify the user journey in a browser and test provider failures, unavailable data, and existing planner regressions.

Stage acceptance: a Baltimore outing can be planned with identifiable real venues and sourced route information; estimates and unknowns are visible, failures are explained, and relevant functional/browser checks are recorded. Provider details and freshness expectations must be agreed in the next task. **Not complete.**

## Stage 2 — advanced constraints, budgets, modes, optimization (planned)

- [x] Prototype foundations only: mock per-person budget, group capacity, date/timing, travel caps, and budget/balanced/experience ranking. This does not complete Stage 2.
- [ ] Define advanced constraints and experience modes with explicit acceptance criteria; distinguish mandatory requirements from preferences.
- [ ] Apply constraints and budgets to real venue/event/route data, with clear cost inclusions and unknowns.
- [ ] Optimize itinerary selection/timing and, if agreed, stop order while preserving hard constraints and explaining tradeoffs.
- [ ] Test conflicting/zero limits, infeasible schedules, missing data, mode changes, and optimization outcomes.

Stage acceptance: agreed constraints, budgets, modes, and optimization work against real data and never silently relax hard limits; functional evidence is recorded.

## Stage 3 — interactive planning, versions, sharing (planned)

- [ ] Interactive map connected to itinerary stops and routes.
- [ ] Add/remove/replace/reorder stops and recalculate feasibility and estimates.
- [ ] Conversational changes with explicit handling of ambiguous instructions and existing constraints.
- [ ] Saved itinerary versions and restore behavior; decide storage and any account requirements first.
- [ ] Shareable plans with defined access/privacy behavior and validation of shared views.
- [ ] Browser/end-to-end checks for map, edits, conversation, restore, sharing, and failure states.

Stage acceptance: users can inspect routes on a map, revise plans directly or conversationally, restore saved versions, and share the intended version with appropriate access controls. Changes preserve hard constraints or clearly explain conflicts.

Work on one focused task at a time. Update status only with implementation evidence, and record verification separately. No dates or technology commitments are implied by this tracker.
