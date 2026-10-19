# Where To? — handover

Last verified: October 19, 2026. This session changed documentation only.

## Current state

- Implemented frontend prototype: a single homepage with request entry, example request, optional preferences/reset, up to three distinct plan cards, expandable itinerary details, and explanatory empty states.
- Local deterministic planning supports 29 activity categories, date resolution, group capacity, per-person budget, total inter-stop travel limits, and budget/balanced/experience ranking.
- Everything in the Baltimore venue/event catalog is fictional, including prices, capacities, schedules, and travel. This is the prototype for an AI-powered product; no AI service is connected.
- No backend API routes, real venue lookup, routing integration, database, accounts, persistence, interactive map, bookings, or deployment configuration were found. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Verification evidence

- `npm test` passed **49 of 49 tests** on October 19, 2026 (`lib/planner.test.ts`). Tests cover all catalog categories, deterministic/distinct results, unsupported requests/cities, dates, schedule conflicts, budgets (including zero), travel limits, capacities, and preference ranking.
- Source inspection confirms the frontend controls and responsive styles exist. Browser interactions, visual layout, accessibility, and end-to-end behavior were **not tested in this session**. README browser examples are instructions, not proof of execution.
- Lint, TypeScript checks, and production build were not run in this documentation-only session. No prior results are asserted.
- Documentation checks confirmed all six continuity files, required content, the original Next.js rules block, and an unchanged README/application baseline.

## Known limitations and open risks

- Baltimore only; one to four distinct activities. Conservative keywords can reject ordinary phrasing, negation, alternatives, and specific times. Repeated activity categories are collapsed.
- Events exist only on fictional November 7 and November 14, 2026 fixtures. Regular venue opening hours and availability are unchecked. See README for mock timing and cost assumptions.
- Travel uses invented neighborhood zones; ranking chooses among venue combinations in the requested activity order, not an optimized real route. Fewer than three results can be valid.
- No additional confirmed bug is recorded here; passing unit tests do not prove the absence of defects or browser issues.
- `git status --short --branch` failed: **not a Git repository**. No Git diff/history/remotes were available. GitHub connection is unknown; Git was not initialized. This session used a pre-edit file snapshot to review scope.

## Continue from here

Current milestone: **Stage 1 — real venues and route information**, not complete. Some Stage 2 behavior exists only against mock data; Stage 3 remains planned. See [TASKS.md](TASKS.md).

Next recommended task: define and select a Stage 1 real venue and routing data approach for Baltimore. Compare candidate sources for coverage, price, permitted use, required credentials, and missing-data behavior. Completion means a documented recommendation and testable integration criteria; any paid service requires owner approval before adoption. No provider is selected yet.

For a fresh session: follow AGENTS.md, inspect the current code and Git status again, and use README.md for exact startup/check commands. Dependencies are already present; no API keys or `.env` file are needed for the prototype. Do not install packages merely to read or update these documents.
