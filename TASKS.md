# Milestones and tasks

## Authoritative original roadmap

The authoritative source is [the original Word roadmap](docs/original-roadmap.docx), preserved byte for byte from the owner’s document. The checklist below transcribes its exact task wording and sequence, with the original phase/section headings, objectives, tools and completion tests. These source descriptions are plans, not permission to install tools, activate services or incur costs.

Status as of October 22, 2026: Tasks 01–36 are completed per the owner’s current status; existing implementation notes and verification evidence are preserved in the historical tracker below and HANDOVER.md. A completed task does not claim that all technologies in its original description were adopted (for example, progress is tracked here rather than docs/ROADMAP.md). Task 37 is **complete**: its project identity, access and unlinked billing status were verified in Google Cloud Console. Task 38 is **complete**: Places API (New) and Routes API independently show enabled, with billing still unlinked; Tasks 39–135 are pending. Existing prototype overlap does not complete those later tasks.

The original section completion tests apply to the whole section, not to each individual task. In particular, the real-venue/route completion test for section 1D belongs to Tasks 37–46 together; Task 37 requires only the Cloud project. Original cost/provider statements below are historical roadmap text, not current pricing verification.

### Phase 0 — Set up everything

Objective: Prepare your Mac and create a clean, secure project where Codex can work.

Tools: Codex, GitHub, VS Code, Node.js, Python, Git.

Expected cost: $0, assuming existing Codex access is sufficient.

#### 0.1 — Set up the development environment

- [x] Task 01 — Install Codex. Open the ChatGPT desktop app, access Codex, and sign in.

- [x] Task 02 — Install VS Code. This is where we can inspect the project files, although Codex will write most of them.

- [x] Task 03 — Install Homebrew. A package manager that makes installing development tools easier on macOS.

- [x] Task 04 — Install Git, Node.js, and Python. Have Codex verify that the installed versions are compatible with our framework.

- [x] Task 05 — Create the whereto folder. This will contain the entire application.

Completion test: Codex can access our project folder, run Terminal commands, and create a sample file.

#### 0.2 — Create our GitHub repository

- [x] Task 06 — Create a GitHub account or sign in.

- [x] Task 07 — Create a private repository named whereto.

- [x] Task 08 — Connect the local project to GitHub.

- [x] Task 09 — Configure Git and .gitignore. Make sure passwords, API keys, and secret configuration files cannot accidentally be committed.

- [x] Task 10 — Make the first commit and push.

GitHub becomes our code backup and version history. Every major working milestone will have a checkpoint that we can return to if something breaks.

Completion test: The private GitHub repository contains our project files, and Codex can commit changes.

#### 0.3 — Establish the development rules

- [x] Task 11 — Create README.md. Simple instructions for starting, testing, and understanding the project.

- [x] Task 12 — Create AGENTS.md. Tell Codex to use beginner-friendly explanations, small changes, secure coding practices, and automated testing.

- [x] Task 13 — Set the technology stack. Next.js, TypeScript, Tailwind, FastAPI, PostgreSQL, and provider adapters.

- [x] Task 14 — Create a progress file. Use docs/ROADMAP.md to track milestones and completed features.

- [x] Task 15 — Establish a testing routine. Codex should test every meaningful change, explain any failures, and update the documentation.

Completion test: We have a reproducible development project with clear rules, instead of a folder containing unrelated pieces of code.

#### Checkpoint 0 — Development environment ready

At this point, we can begin building the actual app.

### Phase 1 — Build Stage 1: The basic MVP

Objective: A user describes an outing, and the app produces useful combinations of real places with actual travel-time estimates.

#### 1A. Build the frontend

Tools: Codex, Next.js, TypeScript, Tailwind CSS.

- [x] Task 16 — Initialize the Next.js application. Create the frontend and verify it opens in the browser.

- [x] Task 17 — Design our homepage. Add the Where To? name, tagline, and natural-language input box.

- [x] Task 18 — Add the Generate Plan button. Make it trigger a real application action instead of being decorative.

- [x] Task 19 — Add loading, error, and empty states. Users should know when their plan is being generated or something fails.

- [x] Task 20 — Build itinerary result cards. Display venue names, order of activities, travel estimates, and schedule.

- [x] Task 21 — Build a detailed itinerary view. Clicking a plan reveals all its stops and venue information.

- [x] Task 22 — Make everything mobile-responsive. Test on phone-sized and desktop-sized screens.

Completion test: We have an attractive website with a working interface, initially using realistic mock venue data.

#### 1B. Build the backend

Tools: Codex, Python, FastAPI, Pydantic, Pytest.

- [x] Task 23 — Initialize the Python backend. Create a health-check endpoint and connect it to the frontend.

- [x] Task 24 — Define our data structures. Create models for outing requests, activities, venues, constraints, itinerary stops, and complete itineraries.

- [x] Task 25 — Build a sample venue dataset. Include bowling alleys, bars, restaurants, movie theaters, and other common activities in a fictional testing environment.

- [x] Task 26 — Build a deterministic itinerary generator. Combine matching venues into possible multi-stop plans.

- [x] Task 27 — Add basic filtering and ranking. Remove obviously unsuitable combinations and select three distinct options.

- [x] Task 28 — Connect the frontend to the generator. The Generate button should now return results produced by our backend.

- [x] Task 29 — Write automated tests. Verify valid requests, invalid inputs, impossible routes, and correct activity order.

Completion test: The app generates three itineraries from mock data using working application logic—not prewritten cards.

#### 1C. Add natural-language understanding

Tools: Codex, Ollama or a hosted AI model, Pydantic.

- [x] Task 30 — Set up the AI model. Begin with local Ollama if its accuracy and speed are acceptable on the Mac; otherwise evaluate a hosted model.

- [x] Task 31 — Build the prompt interpreter. Extract activities, location, date, time, number of people, budget, and travel constraints.

- [x] Task 32 — Resolve natural date expressions. Understand phrases such as "tomorrow evening" and "next Saturday" using the location's timezone.

- [x] Task 33 — Ask only necessary follow-up questions. Never force users through a long questionnaire when enough information is already provided.

- [x] Task 34 — Validate the AI output. Reject malformed or inconsistent data and handle unclear requests safely.

- [x] Task 35 — Build an editable request summary. Show the interpreted constraints so users can correct mistakes without rewriting everything.

- [x] Task 36 — Create a natural-language test suite. Test requests containing multiple activities, unusual phrasing, missing constraints, and conflicting instructions.

Completion test: Someone can type, "Four friends, bowling and drinks in Baltimore, Saturday after six, short drives," and the application understands the requirements correctly.

#### 1D. Integrate real venues and travel times

Tools: Google Cloud Console, Places API (New), Routes API, Google Maps Platform.

This is where the app becomes genuinely useful.

- [x] Task 37 — Create a Google Cloud project.

  Status: **Complete** — created and opened **Where To**, project ID **`where-to-512422`**, on October 22, 2026. The project’s Billing page confirms **no billing account linked**. No mapping APIs, API keys, service-account credentials, trial or paid services were activated by this task. [Open project](https://console.cloud.google.com/welcome?project=where-to-512422).

- [x] Task 38 — Enable the necessary mapping APIs. Start with Places and Routes; use Maps JavaScript API when we build the interactive map.

  Status: **Complete** — on October 22, 2026, independently verified **Places API (New)** (`places.googleapis.com`) and **Routes API** (`routes.googleapis.com`) both display **API Enabled / Manage** in **Where To**, project **`where-to-512422`**. Routes was enabled with one direct Enable click, without linking billing. Google then redirected to card-verification/free-trial terms; stopped without continuing, then verified actual API state read-only. Billing independently remains **not linked**; Maps JavaScript API remains **disabled**. No card details, trial enrollment, signup terms acceptance, API keys, live API requests or other API activation. Activation is complete; authorization for billable use is not granted. See the final HANDOVER.md checkpoint. Tasks 39 and 40 have not started.

- [ ] Task 39 — Configure billing safeguards. Restrict API keys, set appropriate quotas and budgets, and add app-level request limits.

- [ ] Task 40 — Implement real venue search. Search by activity and geographical area.

- [ ] Task 41 — Normalize venue data. Extract provider IDs, names, locations, ratings when available, hours, websites, and other supported fields.

- [ ] Task 42 — Add deduplication and relevance checks. Avoid repeated venues and misleading matches.

- [ ] Task 43 — Build the route calculator. Request actual driving or walking durations between candidate places.

- [ ] Task 44 — Filter infeasible combinations. Reject excessive travel times and known opening-hour conflicts.

- [ ] Task 45 — Add accurate source labeling. Distinguish verified data from estimates and unknown availability.

- [ ] Task 46 — Integrate real venue and route data with the existing planner. Keep mock-data mode available for testing and development.

Google Maps Platform is usage-based, and Places billing depends on the specific fields requested. We'll only request the information we need and keep API quotas conservative.

Google for Developers

Completion test: Entering a Baltimore outing request produces real venues, actual routing estimates, and source links. The app never invents a movie showtime, reservation, or price it hasn't verified.

#### 1E. Save plans and launch our first MVP

Tools: Supabase PostgreSQL, GitHub, Vercel or other frontend hosting, Python backend hosting.

- [ ] Task 47 — Create a Supabase project. Set up the hosted PostgreSQL database.

- [ ] Task 48 — Create the initial database tables. Plans, constraints, generated itineraries, itinerary stops, and source metadata.

- [ ] Task 49 — Save and retrieve plans. A browser refresh should not destroy a saved itinerary.

- [ ] Task 50 — Configure safe database access. Keep privileged credentials on the server, validate requests, and protect write operations.

- [ ] Task 51 — Add usage limits and basic error logging.

- [ ] Task 52 — Choose production-compatible hosting. Deploy the frontend and backend to services permitted for our intended usage.

- [ ] Task 53 — Configure environment variables and HTTPS. No secret keys in public frontend code or GitHub.

- [ ] Task 54 — Perform end-to-end testing. Generate, open, save, refresh, and view a plan on a phone.

- [ ] Task 55 — Invite initial testers. Collect feedback on recommendation quality, travel feasibility, and usefulness.

Supabase currently offers a free plan that includes a PostgreSQL database suitable for small prototypes.

Supabase Docs

One hosting consideration: Vercel's free Hobby plan is restricted to non-commercial use. Since we're ultimately building a business, we'll review the appropriate hosting tier before a commercial launch.

Vercel

#### Checkpoint 1 — Stage 1 complete

We have a real, publicly accessible outing planner that accepts natural-language requests and generates multi-stop itineraries using real venue and route data.

### Phase 2 — Build Stage 2: Smart planning and optimization

Objective: Generate plans that match individual priorities, not just places that happen to be close together.

#### 2A. Build the complete preference system

Tools: Codex, Next.js, Pydantic, PostgreSQL.

- [ ] Task 56 — Expand the planning schema. Support budget, group size, dates, activities, travel, quality, cuisine, accessibility, atmosphere, and other relevant variables.

- [ ] Task 57 — Classify constraints. Separate mandatory rules from flexible preferences.

- [ ] Task 58 — Add an optional manual preference panel. Users can enter or adjust preferences without typing.

- [ ] Task 59 — Synchronize text and manual inputs. A user can describe an outing naturally and then adjust the extracted settings.

- [ ] Task 60 — Support activity-specific preferences. For example, "Cheap bowling, premium dinner."

- [ ] Task 61 — Support unknown and unspecified values. Don't silently invent information when the user hasn't supplied it.

- [ ] Task 62 — Add conflict detection. Identify contradictory requirements and offer clear alternatives.

Completion test: Users can combine natural-language requests with manual settings, and the app correctly preserves every constraint.

#### 2B. Build budget and cost intelligence

Tools: Codex, FastAPI, PostgreSQL, available venue-price sources.

- [ ] Task 63 — Add the three spending modes. Budget-friendly, Balanced, and Best Experience.

- [ ] Task 64 — Add a continuous cost-versus-experience slider. Users can position themselves anywhere between saving money and maximizing quality.

- [ ] Task 65 — Support strict maximum budgets. Per person and per group.

- [ ] Task 66 — Create an activity-level budget allocator. Let users spend more on selected activities.

- [ ] Task 67 — Build a cost estimation service. Store provider-supported prices or clearly identified estimates where available.

- [ ] Task 68 — Calculate known cost breakdowns. Include per-person cost, group cost, and known additional fees.

- [ ] Task 69 — Handle missing prices correctly. Don't mark a plan within budget if critical venue costs are unknown.

- [ ] Task 70 — Build the cost comparison interface. Show estimated prices, confidence/source information, and differences between plans.

For these first stages, we will not promise live prices for every venue. Comprehensive menu data, movie ticket prices, and booking availability require additional provider coverage in Stage 6.

Completion test: A user can request a cheap outing, a premium outing, or a carefully balanced outing, and receive appropriately ranked options without the app misrepresenting unavailable prices.

#### 2C. Improve itinerary optimization

Tools: Python, Pytest, routing provider, optional OR-Tools.

- [ ] Task 71 — Create the optimization scoring system. Evaluate venue quality, travel convenience, price, and preference match.

- [ ] Task 72 — Guarantee hard-constraint filtering. Known violations must be excluded before the app ranks results.

- [ ] Task 73 — Implement scheduling logic. Calculate arrival, activity duration, departure, and subsequent travel.

- [ ] Task 74 — Add configurable timing buffers. Allow for parking, waiting, and transitions.

- [ ] Task 75 — Handle fixed-time events. Only schedule specific movie showtimes or reservations when actual timing data is available.

- [ ] Task 76 — Optimize activity order. Reorder flexible activities to reduce travel or improve timing.

- [ ] Task 77 — Support fixed activity order. Respect requests such as "bowling first, movie last."

- [ ] Task 78 — Optimize candidate selection. Avoid unnecessarily expensive route calculations and inefficient venue combinations.

- [ ] Task 79 — Diversify recommendations. Produce meaningfully different plans rather than three slight variations of the same outing.

- [ ] Task 80 — Explain recommendations. Show verified, understandable reasons for each option.

- [ ] Task 81 — Implement infeasibility explanations. Suggest which constraints could be relaxed when no valid plan exists.

- [ ] Task 82 — Test complex scenarios. Include conflicting budgets, closed venues, long travel times, special requirements, and constrained schedules.

We can begin with straightforward Python algorithms. If the constraints become sufficiently complex, we can add OR-Tools without changing how users interact with the product.

#### 2D. Upgrade the user experience

Tools: Codex, Next.js, Tailwind CSS, Playwright.

- [ ] Task 83 — Build comparison cards. Compare price, total travel, overall duration, ratings, and suitability.

- [ ] Task 84 — Add explanation panels. Users can understand why one plan was recommended over another.

- [ ] Task 85 — Add quick filters. Cheaper, closer, better rated, less travel, or change the activity mix.

- [ ] Task 86 — Re-optimize when preferences change. Updating a slider or constraint should generate new recommendations.

- [ ] Task 87 — Test on mobile. Ensure advanced options are tucked away unless the user wants them.

- [ ] Task 88 — Run Stage 2 acceptance tests and save a GitHub release checkpoint.

#### Checkpoint 2 — Stage 2 complete

The app understands detailed constraints, supports all three spending modes, evaluates trade-offs, optimizes activity combinations, and clearly explains its recommendations.

### Phase 3 — Build Stage 3: The interactive itinerary planner

Objective: Users can modify their plans freely without starting the search again.

#### 3A. Build the interactive map

Tools: Google Maps JavaScript API, Next.js, Codex.

- [ ] Task 89 — Integrate an interactive map. Display the actual venue locations.

- [ ] Task 90 — Add numbered venue markers. Show each activity stop in itinerary order.

- [ ] Task 91 — Draw the travel route. Display the planned journey using routing-provider data.

- [ ] Task 92 — Synchronize the map and itinerary cards. Selecting a place in either view highlights it in both.

- [ ] Task 93 — Show venue details. Address, supported ratings, hours, links, and available price information.

- [ ] Task 94 — Add transport-mode switching. Recalculate routes using supported driving, walking, or transit options.

- [ ] Task 95 — Design mobile map navigation. Use a simple Map/Plan switch or expandable map.

- [ ] Task 96 — Test map accuracy and rendering performance.

Completion test: Users can visually inspect the full route and tap any venue to learn more.

#### 3B. Build the manual itinerary editor

Tools: Next.js, FastAPI, PostgreSQL, routing provider.

- [ ] Task 97 — Implement Replace Venue. Show suitable alternatives for a specific stop.

- [ ] Task 98 — Implement Add Activity. Insert an activity anywhere in the itinerary.

- [ ] Task 99 — Implement Remove Activity. Delete a stop and recalculate the remaining route.

- [ ] Task 100 — Implement Reorder Activities. Support buttons and drag-and-drop on compatible devices.

- [ ] Task 101 — Implement Lock Activity. Preserve chosen venues and fixed times during subsequent planning.

- [ ] Task 102 — Build incremental recalculation. Update the affected routes, timing, and cost estimates without unnecessarily rebuilding everything.

- [ ] Task 103 — Detect edit conflicts. Warn users when an edit violates hard constraints or collides with a locked activity.

- [ ] Task 104 — Build Undo and Redo. Allow users to revert changes.

- [ ] Task 105 — Add edit previews. Show how travel time, price, and schedule would change before applying an edit.

- [ ] Task 106 — Test every editing action. Verify that venue identities, times, costs, and locked stops remain consistent.

Completion test: Someone can manually build an itinerary from recommendations, change its structure, and always see updated calculations.

#### 3C. Add natural-language itinerary editing

Tools: Codex, AI model, Pydantic, FastAPI.

- [ ] Task 107 — Create an AI editing endpoint. Accept requests referring to an existing plan.

- [ ] Task 108 — Interpret editing instructions. Support replace, add, remove, reorder, lock, and time changes.

- [ ] Task 109 — Build structured editing commands. The AI must output validated operations rather than directly modify database records.

- [ ] Task 110 — Preserve existing constraints. Don't discard the original budget, travel limit, or locked venues.

- [ ] Task 111 — Generate edit previews. Display proposed changes for approval.

- [ ] Task 112 — Recalculate the updated plan. Run the scheduling and optimization engines.

- [ ] Task 113 — Explain conflicts and alternatives. For example, explain why moving the movie later may be impossible without verified showtime data.

- [ ] Task 114 — Add conversational editing history. Users can refer to previous changes within the current plan.

- [ ] Task 115 — Run language and regression tests. Verify that the AI edits only the intended parts.

Completion test: A user can type "Keep bowling, find a better bar, and reduce travel to 10 minutes per stop," review the proposed changes, and apply them.

#### 3D. Add persistence, history, and sharing

Tools: Supabase PostgreSQL, FastAPI, GitHub.

- [ ] Task 116 — Build plan versioning. Save snapshots or change records for every approved edit.

- [ ] Task 117 — Create a plan history view. Display previous versions and their differences.

- [ ] Task 118 — Implement Restore Version. Revert to an earlier itinerary when needed.

- [ ] Task 119 — Create secure shareable links. Friends can view an itinerary without creating an account.

- [ ] Task 120 — Add owner-only editing. Shared read-only links must not provide editing access.

- [ ] Task 121 — Support plan duplication. Users can copy an itinerary and modify their own version.

- [ ] Task 122 — Add a simple export option. Produce a readable itinerary or printable view with venue links.

- [ ] Task 123 — Secure shared data. Use unguessable share tokens, appropriate expiration/revocation controls, and protect private plan details.

- [ ] Task 124 — Test editing permissions and plan recovery.

Completion test: Users can save a plan, return to it, restore an older version, and share a view-only link with friends.

#### 3E. Production testing and release

Tools: Codex, GitHub, Pytest, Playwright, hosting dashboards.

- [ ] Task 125 — Create comprehensive backend unit tests. Cover natural-language interpretation, constraints, ranking, routing, scheduling, and editing.

- [ ] Task 126 — Create browser interaction tests. Cover plan creation, manual adjustments, map interactions, saving, and sharing.

- [ ] Task 127 — Test cross-device layouts. Check desktop, mobile, and tablet screen sizes.

- [ ] Task 128 — Perform accessibility testing. Keyboard navigation, readable text, button labels, and sufficient visual contrast.

- [ ] Task 129 — Add monitoring and operational safeguards. Error logging, performance monitoring, API quotas, and request rate limits.

- [ ] Task 130 — Add privacy and legal basics. Explain how plan/location data is handled, publish appropriate policies, and review venue-data and map-provider terms.

- [ ] Task 131 — Perform basic security testing. Validate API authorization, secret handling, input limits, and potential abuse.

- [ ] Task 132 — Test with real users. Include different budgets, activity combinations, locations, and group sizes.

- [ ] Task 133 — Fix critical defects and usability issues.

- [ ] Task 134 — Deploy the completed Stage 3 release.

- [ ] Task 135 — Tag the release in GitHub and update documentation.

#### Checkpoint 3 — Stages 1–3 complete

We have a deployed, responsive web application capable of generating, optimizing, editing, saving, and sharing itineraries built from real venue and routing data.

---

## Historical implementation tracker

The following pre-recovery tracker is retained verbatim, including historical status statements and task references. Use the authoritative checklist above for the single numbered roadmap sequence and current next task. These historical sections are evidence, not additional roadmap tasks.

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

## Original roadmap — Task 36: comprehensive AI interpretation testing

- [x] Inspect instructions, continuity documents and existing coverage; establish 175 backend/99 frontend baseline and reproduce the exact Task 35 conflict request with real Qwen.
- [x] Run a focused acceptance matrix across extraction, dates/DST, clarification, hard constraints, preferences, summary edits, service failures and fictional-data limitations without duplicating existing broad edge-case tests.
- [x] Fix discarded nontrailing party counts, competing minimum-budget explanations and ungrounded model activity text in errors; add six focused deterministic regression tests.
- [x] Pass 181 backend/99 frontend tests, ESLint, TypeScript and production build; pass 20 real-Qwen runs and 10 production-browser journeys at 1280×720 and 390×844.
- [x] Measure cold/warm AI separately from model-free follow-up/regeneration; count browser model/candidate requests and preserve existing architecture, dataset, dependencies and release tags.
- [x] Review the full diff, document acceptance evidence/limitations and commit/push tested changes to the existing private repository.

Task 36 is complete. Task 37 may begin in a separate session; it was not started here.

### Focused date correction after Task 36

- [x] Accept full English month names and standard abbreviations, optional periods, either day/month order and explicit years.
- [x] Infer only a valid current-local-year date today or later; ask for the year of a passed month/day and a leap year for yearless February 29 where needed. Never silently advance a year.
- [x] Continue year-only answers deterministically with preserved context; send reason-specific date/year/weekend/time questions and guidance through the existing clarification fields.
- [x] Pass 194 backend/102 frontend tests, ESLint, TypeScript and production build; verify the exact six-person dinner request, corrections, preference synchronization and manual priority in the real Qwen/FastAPI/Next.js browser.
- [x] Review the complete diff, update relevant documentation and commit/push the tested correction while preserving release tags. No Task 37 work.
