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

Task 28 is complete and has been verified by Task 29. Real-data integrations remain future work.

## Original roadmap — Task 29: verify the complete mock planning system

- [x] Inspect Tasks 23–28, project safeguards, shared data, current frontend/backend and existing tests.
- [x] Verify real Python requests and displayed results for all required journeys, constraints, modes, distinctness and honest fictional/provisional states.
- [x] Exercise invalid/missing/contradictory inputs, backend shutdown/recovery, delayed loading and counted duplicate submission protection.
- [x] Perform meaningful mobile/tablet/desktop, manual-preference, detail-expansion and basic keyboard/accessibility checks.
- [x] Fix the demonstrated midnight display defect and two faint preference hint colors; add focused midnight regression coverage without new dependencies or planner changes.
- [x] Pass all backend/frontend tests, lint, TypeScript and production build; review the full diff and record evidence in HANDOVER.md.

Task 29 is complete. Its verification predates Task 30 below; fictional-data limitations remain explicit.

## Original roadmap — Task 30: set up the AI model

- [x] Inspect project and hardware; verify existing Ollama without reinstalling/upgrading.
- [x] Compare suitable small models; evaluate installed Llama 3.2 and download Qwen3 4B with explicit owner approval.
- [x] Verify Qwen3 4B locally with two runs of the four required samples and eight additional requests; record timings and semantic limitations.
- [x] Implement a standalone configurable AI provider protocol and Ollama adapter, safe errors and opt-in smoke check; preserve the current application path.
- [x] Add 11 mocked tests including provider substitution; pass backend/frontend tests, lint, TypeScript and production build.
- [x] Update documentation and review the complete source diff; back up tested changes to the existing private repository.

Task 30 is complete and its provider interface is reused by Task 31.

## Original roadmap — Task 31: build and integrate the AI prompt interpreter

- [x] Inspect project, frontend input flow, Task 24 contracts, Task 30 provider and Python engine before changes.
- [x] Add provider-independent interpretation service and FastAPI/Next.js endpoint; submit raw text from Plan my outing.
- [x] Preserve ordered/repeated stops, nullable unknowns, raw date/time wording, explicit constraints, preferences, suggestions and uncertainty.
- [x] Apply explicit manual overrides, including zero limits and explicitly chosen Balanced; blank/default fields preserve text.
- [x] Refuse unsupported/ambiguous/invalid/model-failure requests without keyword fallback; reuse existing Python engine.
- [x] Add automated coverage, real Qwen smoke (including tomorrow), browser integration check; pass backend/frontend tests, lint, TypeScript and build.
- [x] Review full diff, update documentation and back up source to the existing private repository.

Task 31 is complete. Task 32 below supersedes its unresolved-date behavior; no confirmation redesign, multi-turn clarification or new infrastructure was added.

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

## Original roadmap — Task 32: resolve relative dates and times

- [x] Inspect Task 31 extraction, manual controls, contracts, scheduling, tests and documentation.
- [x] Resolve supported calendar/time phrases deterministically before the planner; preserve original wording and ignore AI arithmetic.
- [x] Document local timezone/fallback, this/next, weekend/evening defaults and manual Date precedence.
- [x] Explain past/conflicting/overnight/DST-ambiguous requests without relaxing single-day constraints.
- [x] Cover fixed calendar boundaries and actual interpretation/proxy/client/engine integration, including omitted tomorrow.
- [x] Complete real-Qwen smoke (13 Task 32 + 8 Task 31 cases), full regression checks (114 backend/74 frontend), lint, TypeScript, production build, diff review and private GitHub backup.

Task 32 completed at this checkpoint; Task 33 is recorded below.

### Focused correction before Task 33 — natural-language-only planning

- [x] Reproduce and trace untouched-preference failure; confirm the live backend still returned the old Task 31 date guard while the current checkout resolved the same request.
- [x] Restart the current backend with reload; keep natural-language planning independent of manual controls.
- [x] Display the existing successful structured interpretation in controls, with separate deliberate manual markers and no extra model calls.
- [x] Test subsequent requests, clearing/reset, zero/Balanced precedence, missing essentials and failures; verify in real development/production browsers.
- [x] Pass 115 backend/81 frontend tests, lint, TypeScript and production build; review the complete diff and back up to the private repository.

This was a Task 32 follow-up correction before Task 33.

## Original roadmap — Task 33: intelligent missing-information handling

- [x] Inspect Tasks 31–32, optional/manual preference provenance, actual planner requirements and existing regressions.
- [x] Ask targeted questions for missing city/group, scheduled-event dates, ambiguous weekends, activity choices and clock windows; leave missing optional caps/preferences alone.
- [x] Retain the original extraction/text/calendar reference and merge validated answers without another AI call; preserve repeated/ordered stops and hard constraints.
- [x] Keep manual precedence, support cancellation/replacement, reject invalid answers, retain retry state after failures, and block duplicate/late submissions.
- [x] Pass 136 backend and 87 frontend tests, lint, TypeScript and production build; verify real Ollama/Python/Next.js browser flows.
- [x] Review complete diff, update continuity documentation and push tested changes to the existing private repository, preserving release tags.

Task 33 is complete. Stop here; Task 34 is recorded below.

### Task 33 focused follow-up — mandatory date and response speed

- [x] Measure the real Ollama/FastAPI/production Next.js pipeline cold and warm for complete, missing city/group/date and model-free follow-up scenarios.
- [x] Reduce redundant model prompt/output work while retaining structured validation, semantic extraction and provider replacement.
- [x] Require a valid date for every published outing, reuse natural-language date answers, and prevent candidate work while clarification is pending.
- [x] Preserve manual precedence, auto display, repeated stops, constraints, neutral location questions, cancellation/retry and duplicate protection.
- [x] Pass 149 backend/87 frontend tests, lint, TypeScript, production build and real-browser acceptance scenarios; review diff and back up tested work.

Task 33 remains complete with the updated policy. Task 34 is recorded below.


## Original roadmap — Task 34: strengthen interpretation and response validation

- [x] Inspect and document existing schema, source, date, clarification, preferences and feasibility guarantees and gaps.
- [x] Strengthen the existing provider-independent trust boundary; reject malformed/unknown data, ungrounded constraints and demonstrable scope/intent conflicts without fallback or additional AI calls.
- [x] Preserve manual overrides, independent constraints, zero caps, repeated activity order, required dates, deterministic follow-ups and unchanged planner/UI behavior.
- [x] Add deterministic regression and real HTTP integration tests; verify actual Qwen and browser scenarios, including clarification completion.
- [x] Record 172 backend/88 frontend passes, real-model/browser evidence and measured latency tradeoff; review full diff and push tested changes to the existing private repository, preserving tags.

Stop after Task 34. Task 35 is not started.


### Focused usability follow-up — date answer examples

- [x] Keep the missing-date question; show only resolver-supported examples beside date follow-ups, including correction attempts.
- [x] Preserve existing parsing/answers/overrides/continuation; add rendered date/non-date regression tests.
- [x] Pass 90 frontend/172 backend tests, lint, TypeScript and production build; verify invalid/ambiguous answers → “tomorrow” → planning in a real browser, review diff and push tested changes. Task 35 remains unstarted.


## Original roadmap — Task 35: editable AI interpretation summary

- [x] Inspect authoritative interpretation, preferences/manual provenance, dates, clarification, validation and Python planner before changes.
- [x] Show compact resolved effective outing details automatically; distinguish unspecified optional choices from defaults.
- [x] Reuse existing preferences and clarification answers for corrections, ordered/repeated activities and model-free regeneration through existing server validation.
- [x] Preserve manual settings/new-request replacement, zero/Balanced, hard constraints, pending corrections/retry/cancel/reset, duplicate protection and immediate stale-card removal.
- [x] Pass 175 backend/95 frontend tests, lint, TypeScript and production build; verify real Ollama/FastAPI/Next.js scenarios A–F, narrow layout and keyboard focus/navigation. Separate wide-desktop viewport was not exercised; see HANDOVER.md.
- [x] Review complete diff, update continuity documentation and push tested changes to the existing private repository, preserving tags.

Task 35 is complete. Stop here; Task 36 is not started.


### Task 35 focused UI refinement — compact overview and collapsible editor

- [x] Keep initial preferences collapsed; collapse only after successful planning/regeneration, preserving deliberate opening and failure/clarification access.
- [x] Keep Edit details focused on the existing controls; tighten summary spacing and omit unspecified optional rows without duplicating state.
- [x] Verify native date locale formatting and add readable selected-date guidance, preserving ISO values and existing resolver/validation.
- [x] Pass 99 frontend/175 backend tests, lint, TypeScript and production build; verify desktop/mobile edit/regenerate, stale cards, invalid edits, repeated stops, pending questions and keyboard interaction with real services.
- [x] Review scoped diff, update relevant continuity notes and commit/push to existing private repository with tags preserved. Stop before Task 36.
