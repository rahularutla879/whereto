# Where To? — handover

Last verified: October 19, 2026. GitHub backup setup changed Git metadata, ignore rules, and continuity documentation only; application code and README are unchanged.

## Current state

- Implemented frontend prototype: a single homepage with request entry, example request, optional preferences/reset, up to three distinct plan cards, expandable itinerary details, and explanatory empty states.
- Local deterministic planning supports 29 activity categories, date resolution, group capacity, per-person budget, total inter-stop travel limits, and budget/balanced/experience ranking.
- Everything in the Baltimore venue/event catalog is fictional, including prices, capacities, schedules, and travel. This is the prototype for an AI-powered product; no AI service is connected.
- No backend API routes, real venue lookup, routing integration, database, accounts, persistence, interactive map, bookings, or deployment configuration were found. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Verification evidence

- `npm test` passed **49 of 49 tests** on October 19, 2026 (`lib/planner.test.ts`). Tests cover all catalog categories, deterministic/distinct results, unsupported requests/cities, dates, schedule conflicts, budgets (including zero), travel limits, capacities, and preference ranking.
- Source inspection confirms the frontend controls and responsive styles exist. Browser interactions, visual layout, accessibility, and end-to-end behavior were **not tested in this session**. README browser examples are instructions, not proof of execution.
- `npm run lint` and `npm run typecheck` passed during GitHub backup setup. Production build and browser checks were not run in this setup session.
- Pre-setup SHA-256 file comparisons confirmed application code, configuration, dependency manifests/lockfile, README, and the original Next.js rules block are unchanged. The initial staged file review covered all 23 files, including a credential-pattern scan with no findings.
- The initial commit `ae24a307ae0aa2c0e56229961d6a09eea932320a` was pushed and verified through GitHub. Repository privacy and the expected project files were checked remotely. A follow-up documentation commit records this setup; `prototype-v0.1` identifies the final setup checkpoint.

## Known limitations and open risks

- Baltimore only; one to four distinct activities. Conservative keywords can reject ordinary phrasing, negation, alternatives, and specific times. Repeated activity categories are collapsed.
- Events exist only on fictional November 7 and November 14, 2026 fixtures. Regular venue opening hours and availability are unchecked. See README for mock timing and cost assumptions.
- Travel uses invented neighborhood zones; ranking chooses among venue combinations in the requested activity order, not an optimized real route. Fewer than three results can be valid.
- No additional confirmed bug is recorded here; passing unit tests do not prove the absence of defects or browser issues.

## Version control and backup

- Git was initialized in the existing folder on `main`, with no prior Git history or remote to replace. GitHub CLI was installed and authenticated through browser sign-in.
- Owner-approved private repository: [rahularutla879/whereto](https://github.com/rahularutla879/whereto). `origin` uses `https://github.com/rahularutla879/whereto.git`; local `main` tracks `origin/main`.
- `.gitignore` excludes environment files (except a placeholder-only `.env.example`), dependencies, build outputs, logs, credential files, and local editor/agent/hosting settings. Excluded files remain on the computer. No `.env` file was present and no credentials were found in the reviewed commit candidates; pattern scanning is not a guarantee against all possible secrets.
- This backs up committed source and documentation. Future edits require another commit and push; saving files locally does not automatically back them up. No application deployment was performed.

## Continue from here

Current milestone: **Stage 1 — real venues and route information**, not complete. Some Stage 2 behavior exists only against mock data; Stage 3 remains planned. See [TASKS.md](TASKS.md).

Next recommended task: define and select a Stage 1 real venue and routing data approach for Baltimore. Compare candidate sources for coverage, price, permitted use, required credentials, and missing-data behavior. Completion means a documented recommendation and testable integration criteria; any paid service requires owner approval before adoption. No provider is selected yet.

For a fresh session: follow AGENTS.md, inspect the current code and Git status again, and use README.md for exact startup/check commands. Dependencies are already present; no API keys or `.env` file are needed for the prototype. Do not install packages merely to read or update these documents.
