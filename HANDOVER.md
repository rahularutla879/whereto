# Where To? — handover

Last verified: October 20, 2026. Original roadmap Task 23 adds a minimal Python backend and server-side Next.js health connection. Homepage design and mock planning code are unchanged.

## Current state

- Implemented frontend prototype: a single homepage with request entry, example request, optional preferences/reset, up to three distinct plan cards, expandable itinerary details, and explanatory empty states.
- Local deterministic planning supports 29 activity categories, date resolution, group capacity, per-person budget, total inter-stop travel limits, and budget/balanced/experience ranking.
- Everything in the Baltimore venue/event catalog is fictional, including prices, capacities, schedules, and travel. This is the prototype for an AI-powered product; no AI service is connected.
- FastAPI exposes `GET /health`; Next.js exposes `GET /api/health`, which contacts Python server-side. No planning API, real venue lookup, routing integration, database, accounts, persistence, interactive map, bookings, or deployment is implemented. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Verification evidence

- `npm test` passed **49 of 49 tests** on October 19, 2026 (`lib/planner.test.ts`). Tests cover all catalog categories, deterministic/distinct results, unsupported requests/cities, dates, schedule conflicts, budgets (including zero), travel limits, capacities, and preference ranking.
- Source inspection confirms the frontend controls and responsive styles exist. Browser interactions, visual layout, accessibility, and end-to-end behavior were **not tested in this session**. README browser examples are instructions, not proof of execution.
- `npm run lint` and `npm run typecheck` passed during GitHub backup setup. Production build and browser checks were not run in this setup session.
- Pre-setup SHA-256 file comparisons confirmed application code, configuration, dependency manifests/lockfile, README, and the original Next.js rules block are unchanged. The initial staged file review covered all 23 files, including a credential-pattern scan with no findings.
- The initial commit `ae24a307ae0aa2c0e56229961d6a09eea932320a` was pushed and verified through GitHub. Repository privacy and the expected project files were checked remotely. A follow-up documentation commit records this setup; `prototype-v0.1` identifies the final setup checkpoint.

## October 19, 2026 — original roadmap Tasks 02–04 environment verification

- Task 02 complete: VS Code 1.85.1 is present at `/Users/rahularutla/Downloads/Visual Studio Code.app`; bundle/package versions and main executable presence were checked. It is outside Applications and `code` is absent from PATH. Moving it to Applications and enabling the terminal shortcut are optional convenience steps. GUI launch was not tested.
- Task 03 complete: Homebrew 7.0.10 runs from `/opt/homebrew/bin/brew`.
- Task 04 complete: Git 2.50.1 (Apple Git-155), Node.js v24.2.0, npm 11.3.0, and Python 3.12.1 all respond to version checks. Installed Next.js 16.4.2 requires Node >=20.9.0; installed npm requires Node ^20.17.0 or >=22.9.0. Node v24.2.0 satisfies both.
- Python's `venv`, `ensurepip`, and SSL modules import successfully; `python3 -m pip --version` reports pip 25.0.1. Python 3.12 satisfies the current FastAPI Python >=3.10 requirement ([maintainer package metadata](https://pypi.org/project/fastapi/)). FastAPI is absent from the checked Python environment and can be deferred until backend development. No backend dependency set or running API was tested.
- No tools were installed/upgraded, no application/dependency/configuration files or Git history were changed, and Task 23 was not started. Only HANDOVER.md and TASKS.md were updated. Initial Git status was clean. Verification covered tool commands and compatibility requirements; application tests and browser checks were not rerun for this environment-only task.

## October 20, 2026 — original roadmap Task 23

- Acceptance criteria met: existing Python 3.12.1 verified; `backend/.venv` created without reinstalling Python; only FastAPI, Uvicorn, and their required dependencies installed. Exact tested versions are pinned in `backend/requirements.txt`. Virtual environment and bytecode are ignored by Git; `pip check` reports no broken requirements.
- FastAPI `GET /health` returns HTTP 200 `{"status":"ok"}`. Next.js `GET /api/health` calls it using server-only `BACKEND_URL` (default `http://127.0.0.1:8000`) and returns HTTP 200 `{"status":"ok","backend":"ok"}`. Requests are uncached with a three-second timeout; backend errors or invalid responses return HTTP 503 `{"status":"error","backend":"unavailable"}`.
- Checks passed: `npm test` **50/50** (49 existing planner tests plus an HTTP communication test covering success, HTTP errors, malformed/unexpected JSON, a stalled server, and a stopped server); `npm run test:backend` **1/1** (real Uvicorn HTTP response); `npm run lint`; `npm run typecheck`; `npm run build`; Python dependency consistency check. Initial network tests were blocked by the sandbox and rerun with local network permission. An initial frontend test lifecycle failure was corrected before the passing run.
- Live HTTP checks against Python on port 8000 and Next.js on port 3000 returned the expected JSON. A production server on port 3001 also returned the successful combined health response in the browser. The port-3000 development server was already running before this work and was preserved; a second `next dev` attempt exited after detecting it.
- Browser smoke check used the production build on port 3001: Try an example populated the request, Plan my outing returned three mock plans, and View plan expanded the itinerary with three stops. The initial browser attempt against the existing development server did not respond to the example button; the clean production instance passed. No homepage source, styles, artwork, or planning logic changed. Broader browser/accessibility/responsive regression testing was not performed.
- Startup: two Terminal windows in `/Users/rahularutla/Documents/whereto`, running `npm run dev:backend` and `npm run dev`; stop each with Control+C. No extra process-management or test dependencies were introduced. README includes fresh-copy setup, verification, and troubleshooting.
- Full Git diff, including new files and pre-existing documentation changes, reviewed. Homepage, styles, artwork, planner, and npm dependencies/lockfile remain unchanged. No credentials or environment files are included beyond the placeholder-only `.env.example`.
- Earlier uncommitted Tasks 02–04 documentation was preserved and included with the continuity updates. Task 24 and planning migration have not started. No external service, AI, map, or database was added. The `prototype-v0.1` tag must remain at `f62ff7ae85ca85f3ef6fbf169046c22c720950ed`.

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

Task 23 is complete. Stop here until the owner requests the next original-roadmap task. Tasks 24–29 will address backend planning work; no planning logic has moved to Python. The product integration milestones in TASKS.md remain incomplete and no provider is selected.

For a fresh session: follow AGENTS.md, inspect the current code and Git status again, and use README.md for exact startup/check commands. Dependencies are already present; no API keys or `.env` file are needed for the prototype. Do not install packages merely to read or update these documents.
