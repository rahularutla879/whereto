# Milestones and tasks

Status baseline: October 19, 2026. Checked means implemented, not necessarily verified. Verification evidence belongs in [HANDOVER.md](HANDOVER.md). Stages are product goals, not claims that integrations already exist.

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
