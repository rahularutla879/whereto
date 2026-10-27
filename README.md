# where to?

**Less planning. More hanging out.**

A mobile-first outing planner built with Next.js (App Router), TypeScript, React, and Tailwind CSS. The Python planner uses deterministic local rules, with fictional Baltimore venues by default and deliberate local real-data mode for Google Maps venues/routes. The website sends raw text and manual preferences through a server-side Next.js proxy to FastAPI. The local Qwen3 4B model interprets the request; Python validates it before its existing generator and ranking engine create itineraries. The AI provider can be replaced independently of the planner.

## Task 46: real venues in local development

Mock remains the safe default. The website badge says **MOCK DATA** or **REAL DATA · LOCAL DEV**. Real results contain Google Maps venues and driving/walking estimates; prices, hours, visit duration, showtimes and reservations still need confirmation. They are provisional options, not bookings or verified budget matches.

From `/Users/rahularutla/Documents/whereto`, stop the backend with Control+C, then deliberately start real mode in that Terminal:

```sh
cd /Users/rahularutla/Documents/whereto
VENUE_DATA_MODE=real WHERETO_REAL_DEV=1 WHERETO_ENV=development npm run dev:backend
```

Keep the existing `npm run dev` frontend running in the second Terminal and reload the page. Existing local Ollama and protected impersonated ADC must be available. No source-code change is needed. Do not use these switches in production or hosting settings. Generating real plans makes billable Google requests within the existing application/Cloud limits; do not repeat the completed Task 46 live verification without a new allowance.

To turn real mode off, stop that backend with Control+C and run:

```sh
unset WHERETO_EXPLORATION_DEV VENUE_DATA_MODE WHERETO_REAL_DEV WHERETO_CONTACT_DETAILS_DEV WHERETO_RATINGS_DEV WHERETO_START_LOOKUP_DEV WHERETO_PLACES_DEV WHERETO_ROUTES_DEV
npm run dev:backend
```

Reload the frontend and confirm **MOCK DATA**. No Google credentials are needed for mock mode.

Every outing needs a valid beginning under **Where should your outing start?** Choose current location, **I'll choose where to start**, or **I'm new to the city — Surprise me!** Current/manual modes use a confirmed origin; Surprise Me begins at its first activity venue with no landmark or first-leg journey. No location/lookup request happens on page load. Mock remains fictional and needs no Google credentials.

Phone/websites, ratings and manual lookup each retain an explicit local opt-in, off by default. For a **separately authorized future controlled live test**, stop the backend and use this combined command from the same project folder:

```sh
VENUE_DATA_MODE=real WHERETO_REAL_DEV=1 WHERETO_ENV=development WHERETO_RATINGS_DEV=1 WHERETO_CONTACT_DETAILS_DEV=1 WHERETO_START_LOOKUP_DEV=1 npm run dev:backend
```

The October 26 controlled verification exercised ratings, contacts and landmark lookup live: three Text Searches, two Details calls and 18 route elements. That allowance is closed; further live testing needs separate authorization. A bowling relevance correction was then verified offline only. [Results and limits](docs/real-planning.md#october-26-controlled-live-verification). Existing protected keyless credentials are reused. No new API or key is needed for manual lookup: it uses Places Text Search. Contact calls happen only when you open **View details**, under **View plan**. They use Place Details Enterprise. Ratings use optional Text Search Enterprise fields. Both tiers and costs are explained in the linked guide. Do not put the switches in production or a shell profile. Use the unset/normal-start command above to deactivate them.

Real discovery initially requests up to **10 results per distinct activity**. **Search for more venues** explicitly fetches at most two next pages or refined same-area searches per action, retaining up to **20 relevant venues/activity**. No typing-triggered search, automatic pagination, wider destination or budget reset is introduced. **Show different options** uses checked combinations first, then selectively checks unsent routes. Complete itineraries never repeat within the active search. Open **About these estimates** to see the actual runtime ceilings and aggregate counts showing where venues were filtered, routed or ranked. [Bowling coverage diagnosis and remaining live unknowns](docs/real-planning.md#task-46-diagnosis--repeated-bowling-venues).

Application ceilings are **10 venue searches, 20 candidates/activity, 300 route elements and 30 total attempts per outing**, shared by all option/search actions and contacts. Unused contact allowance is reserved within the outing’s attempt budget; process ceilings stay **50 attempts and 1,500 route elements**. The older city-wide API path uses **36/32/48 elements for two/three/four stops**, plus **6/4/4** with a starting point. The website now uses the location-first path described below; its request counts depend on anchors and checked routes. Later stages use at most 64 new elements each. The unchanged **150-elements/rolling-minute** guard can pause exploration: wait at least a minute and explicitly choose Show different options again. No retry or new request is scheduled automatically. Coverage, hard constraints and budgets determine how many plans are possible.

For smaller offline/development ceilings, set `WHERETO_SEARCHES_OUTING`, `WHERETO_CANDIDATES`, `WHERETO_MATRIX_OUTING` or `WHERETO_REQUESTS_OUTING` before starting the backend. Existing `WHERETO_MATRIX_SESSION` and `WHERETO_MATRIX_MINUTE` also only lower approved maxima. Defaults are ceilings, not targets. Cloud was read back October 27: **200 searches/day, 10/minute; 2,000 route elements/day, 150/minute**. Only the Places daily override was increased after a confirmed daily-quota failure. Expanded outings can cost more; see [current budgets and gross estimates](docs/billing-safeguards.md#task-46-approved-application-limit-expansion). All live gates remain off by default.

With sufficient suitable venues, the invented twenty-by-twenty fixture supports 15 successive alternative actions with three new pairs each. The existing ten-by-ten fixture still covers all 100 pairs. Real cities may have far fewer matching venues; no fixed number of options is promised. “Under 5 minutes between venues” is strict: exactly five minutes fails. [Acceptance fixes and remaining limits](docs/real-planning.md#task-46-manual-acceptance-fixes).

Ordinary real results omit unavailable price/capacity/timetable placeholders. Hard budgets remain visibly unverified; important dinner, movie/event and missing-route warnings remain. Actual venue-based headlines, Google ratings when present, source attribution and the mock design are preserved. [Deferred evidence and when warnings remain](docs/deferred-venue-features.md).

[Full real-data flow, safeguards, limitations, pricing and tests](docs/real-planning.md). Historical checkpoints below describe the mock prototype unless stated otherwise.

## Development exploration (Task 46 only)

Normal mode keeps its existing limits. Exploration removes the six search/candidate/outing/process ceilings while retaining finite work per action and a persistent **$10 estimated gross/local-day** guard. It is off by default and cannot enable Google access by itself. Optional ratings, contacts and manual lookup still require their separate flags. No live verification is authorized by these instructions.

For separately authorized local testing, stop the backend, then run from the project folder:

```sh
cd /Users/rahularutla/Documents/whereto
VENUE_DATA_MODE=real WHERETO_REAL_DEV=1 WHERETO_ENV=development WHERETO_EXPLORATION_DEV=1 WHERETO_DEV_DAILY_USD=10 npm run dev:backend
```

The page shows **DEVELOPMENT EXPLORATION**. Open **About these estimates** for outing request/element counts, estimated outing/day cost and remaining estimated allowance. Discovery and routing remain finite; more options use existing evidence first. No background exploration starts on page load. Production/staging/hosting indicators and nonlocal HTTP callers are refused. Keep the backend bound to `127.0.0.1` using the existing command.

The guard stores counters only at `~/.local/state/whereto/development-cost.json` (private permissions). All exploration outings, manual searches and contact requests using that file share it, including after backend restart. `WHERETO_DEV_COST_LEDGER` optionally chooses a private absolute path; do not switch/delete files to reset usage. Unreadable, busy or corrupt accounting refuses work. Increase `WHERETO_DEV_DAILY_USD` only by an explicit local configuration change and review spending first. A $10 daily allowance is **not** a $40–$50 monthly cap: five fully used days consume that target before allowances, and unrelated/normal-mode usage is not included.

To stop exploration and return to mock mode:

```sh
unset WHERETO_EXPLORATION_DEV VENUE_DATA_MODE WHERETO_REAL_DEV WHERETO_RATINGS_DEV WHERETO_CONTACT_DETAILS_DEV WHERETO_START_LOOKUP_DEV WHERETO_PLACES_DEV WHERETO_ROUTES_DEV
npm run dev:backend
```

Reload and confirm **MOCK DATA** without the exploration notice. [Accounting, costs and limitations](docs/billing-safeguards.md#development-exploration-estimate-guard); [discovery and continuation](docs/real-planning.md#development-exploration-mode).

## Location and Surprise Me planning (Task 46)

Describe your destination, activities, date and group, then choose a beginning:

- **Use my current location**: select **Share my location** to request permission. No automatic GPS or inferred city/address. Denial leaves the other choices available.
- **I'll choose where to start**: enter an address, hotel, landmark, station, ZIP, neighborhood or city. Plan/Regenerate finds matches; confirm one and the original submitted request continues. Approximate areas use a labeled representative point.
- **I'm new to the city — Surprise me!**: “Discover unexpected places and let us plan your outing from the first activity.” No address, suggested landmark, GPS or origin journey is requested. Actual first-activity venues guide later activity searches around several promising paths.

Current/manual modes keep the first-stop Minutes/Miles control. Validated natural wording fills it automatically; manual edits win. Flexible uses an inclusive **2× maximum immediately** (20 minutes → 40; 5 miles → 10 road miles), while keeping the original value editable. Strict under excludes equality; at-most includes it. Extra flexible travel is labeled; no return journey is assumed.

Surprise Me hides those first-stop inputs and preserves their inactive values for switching back. Its optional **How far are you willing to travel between activities?** control accepts minutes or road miles, Strict or deliberate Flexible. Flexible doubles only that per-leg preference. Blank means no invented hard limit. Explicit source wording stays strict unless you deliberately edit it; separately stated total travel stays hard. Real Google seconds/road meters decide compliance, not display rounding or map proximity.

If the prompt contains an origin-based first-stop constraint, Surprise Me pauses: choose a location-based mode or select **Remove the first-stop constraint for Surprise Me**. This removes only that scope for the same submitted text, preserving unrelated constraints. Changing the prompt revalidates the choice. Switching modes invalidates incompatible recommendations; confirmed origin input/preferences are retained in page memory and first-leg routes are checked again when returning.

Surprise Me filters relevance, geography, duplicate identities and hard feasibility before recommending. Known ratings below 3 with at least 10 ratings are excluded from its selection; missing/low-count ratings are not invented or treated as poor quality. Weighted randomness balances legitimate quality, travel convenience, unseen first venues and different activity regions. It uses server-side system randomness, not a fixed seed. Complete itineraries do not repeat within an active outing. Different first venues are preferred when suitable checked alternatives exist; no novelty percentage is guaranteed.

Page memory remembers at most **120 first-venue Place IDs for ten minutes after display**, across new Surprise Me requests. Reload/close clears it. There is no database, cookie, localStorage, fingerprint or shared user history, and no names, contact data or coordinates in that history. Active computation sessions independently expire after ten minutes. [Method, retention and Google policy](docs/real-planning.md#surprise-me-discovery-mode).

Ordinary destination wording can include convenient nearby places. **Only within Washington, DC** and **No Virginia** remain hard provider-address checks. Addresses and Google credits remain visible. Origin-based options never silently change your confirmed start. Internal validated radius constraints remain available for compatible origin-based API inputs.

Mock mode supports Surprise Me with fictional venues and simulated minutes, no origin journey and no Google calls. Road-mile preferences require real routing and are refused in mock mode. For mock manual starts, the confirmed reference and fixed five-minute/about-one-mile first leg remain explicitly fictional. Real coordinates cannot verify travel to fictional businesses.

For separately authorized local real development, use the existing startup commands above; Surprise Me requires no new flag, lookup API or billing tier. Manual lookup still needs its separate starting-lookup opt-in. Ratings and contacts retain their own opt-ins. **No live Google testing is authorized by these instructions.** Stop the backend and use the unset/start command above to restore mock mode.

## Start the application — beginner instructions

You need **Node.js 20.9 or newer**, **npm**, and **Python 3.12**. All three are already installed on this computer; Python 3.12.1 was verified without reinstalling it.

1. Open the **Terminal** app.
2. Go to this project folder by typing the following, then press **Enter**:

   ```sh
   cd /Users/rahularutla/Documents/whereto
   ```

3. The project dependencies have already been installed. If this is a fresh copy, run this once and wait for it to finish:

   ```sh
   npm install
   ```

   This downloads the packages listed in `package.json` into this project's `node_modules` folder. It doesn't install tools globally.

4. The backend environment and dependencies are already installed on this computer. On a **fresh copy only**, set them up once from the same project folder:

   ```sh
   python3 --version
   python3 -m venv backend/.venv
   backend/.venv/bin/python -m pip install -r backend/requirements.txt
   ```

   Confirm the version is Python 3.12 before creating the environment. These commands install packages inside the project, not globally. Do not recreate an existing working environment.

5. Open the existing **Ollama** app so the installed `qwen3:4b` model is available. No model download is needed on this computer. Start the backend in this Terminal window:

   ```sh
   npm run dev:backend
   ```

   Wait for “Application startup complete.” Keep this window open.

6. Open a **second Terminal window**, then start the website:

   ```sh
   cd /Users/rahularutla/Documents/whereto
   npm run dev
   ```

7. Keep both windows open. Open **[http://localhost:3000](http://localhost:3000)** in your browser. If Next.js prints a different port because 3000 is busy, use that port instead.

8. Verify the connection by opening **[http://localhost:3000/api/health](http://localhost:3000/api/health)**. You should see `{"status":"ok","backend":"ok"}`. This means Next.js successfully contacted Python. The direct backend check at **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)** returns `{"status":"ok"}`.

9. To stop the application, press **Control + C in each Terminal window**.

The two commands avoid an extra process-management dependency. `npm run dev` still starts just the frontend.

Planning requires both servers and the local AI service. If Python is stopped, Plan my outing shows an unavailable-service explanation and no generated plans. It never falls back to the retired browser planner. The initial three inspiration cards are a fixed illustration, not a generated response. Health checks time out after three seconds. AI has a 60-second default provider timeout, a 70-second proxy timeout and a 75-second browser timeout. After interpretation, planning keeps its ten-second proxy and fifteen-second browser timeouts. Increase the AI timeout only alongside those outer limits.

The default backend address is `http://127.0.0.1:8000`. No configuration is required. For a different backend address, copy `.env.example` to `.env.local`, change `BACKEND_URL`, and restart Next.js. This setting is server-only. Do not add `NEXT_PUBLIC_` to it. The connection is server-to-server, so no browser CORS configuration is needed.

You can edit files and see changes in the browser while the development server is running. Starting it does not publish your site on the internet. No accounts, API keys, or `.env` file are needed.

## Try the mock planner

Click **Try an example**, then **Plan my outing**. Or type:

> We're 4 friends in Baltimore. We want bowling, drinks, and a movie.

You will get up to three distinct demo plans, introduced by a simple count such as **Found 3 possible plans.** A visible **Sample results** label and short disclosure explain that the venues, prices, travel times and event schedules are fictional. **About these estimates** expands to explain unchecked opening hours/availability, excluded costs and transport assumptions. Important plan-specific unknowns or conflicts remain visible beside the affected card. Use **View plan** to expand the itinerary and see its sample venues, durations, per-person costs and group total. Card headlines, labels and short descriptions compare the displayed options using their actual preference match, cost, travel and sample venue quality. Tied options acknowledge different venues or stop order; no position is automatically the cheapest or best.

Try these requests too:

- `Coffee and art in Baltimore for 2 people`
- `We're 6 friends in Baltimore. We want food and a movie.`
- `A walk and coffee in Baltimore for 2 people`

You can plan entirely through your request without opening **Set preferences**. For example: `We're 6 friends in Baltimore. We want coffee, museum, then coffee tomorrow, under $100 per person, with at most 30 minutes total travel. Best experience.`

After successful interpretation, **Set preferences** displays the resolved location, date, group size, budget/travel caps and cost mode. These automatic values are for inspection; they do not override your next text request. No extra AI call is made, and typing does not trigger interpretation. Unspecified caps/date remain blank; Balanced is the existing default when no cost mode is stated.

Deliberately changing a control overrides that field in later requests until you clear it or click **Reset preferences**. Clearing a field releases its override. A zero budget/travel limit remains a real limit; clicking Balanced deliberately also overrides conflicting text. Opening the panel or viewing automatic values creates no override. Missing location or group size opens a short follow-up below your request. Answer there to continue automatically. Budget/travel limits and group capacity remain hard constraints, while cost mode ranks eligible plans.

## Planner review and improvements

The original planner recognized only **bowling, drinks, movies, food, coffee, outdoors, and art**. Museums were folded into art. Karaoke was not recognized: a dinner-and-karaoke request could return dinner alone. An entirely unknown request silently fell back to bowling, drinks, and a movie. Group size only changed the displayed total, and dates were labels without event schedules.

The updated planner supports **29 categories**:

- Regular venues: bowling, drinks, movies, food/dinner, coffee, outdoor walks/parks, art galleries, museums, karaoke, arcades, escape rooms, mini golf, shopping, zoos, hiking, picnics, and skating.
- Scheduled events: baseball, basketball, football, soccer, hockey, general sporting events, concerts/live music, theater/plays, musicals, ballet, opera, and comedy shows.

Museums and galleries are separate. A baseball request cannot be replaced with another sport. Ballet and opera have their own fictional performances rather than being replaced with a stage play.

### Unknown requests

There is **no unrelated activity fallback**. Unsupported phrases, alternatives, exclusions, unresolved uncertainty and requests over four stops get an explanation instead of a partial plan. AI suggestions for “something competitive” are labeled suggestions and require an explicit activity choice. Every requested occurrence stays separate: `coffee, museum, then coffee` produces three stops; `lunch and dinner` produces two meal stops. Dinner timing applies only to the dinner stop.

This is a local AI interpreter with conservative validation, not guaranteed understanding of arbitrary language. Exact phrase normalization and source-grounding guards can ask you to rephrase valid wording. Unknown venue qualities remain unverified. There is no keyword fallback, automatic retry, hosted AI call, or permanent saving of outing requests. A pending clarification stays only in the current page’s memory. Ordinary tests mock AI; real-model smoke checks are opt-in.

### Fictional dates and timing

All scheduled events have **invented entries only on November 7 and November 14, 2026**. These dates are fixture data, not real schedules. Expand **Supported activities & fictional event dates** under the planner to see the catalog and instructions.

- Set the Date preference or type an ISO date, a full English month name, or a standard abbreviation: `nov 11`, `Nov. 11`, `11 Nov`, `Nov 11, 2026`, or `11 November 2026` (case-insensitive; Sep and Sept both work).
- Without a year, the app uses the current local calendar year only if that month/day is valid and today or later. If it has passed this year, it asks which year; reply with just a four-digit year, such as `2027`. It never silently moves the date to next year. February 29 needs a valid leap year.
- Today, tonight, tomorrow, tomorrow evening, and weekdays resolve in Baltimore local time. “This Friday” means upcoming Friday including today; “next Friday” means Friday in the following Monday–Sunday week. This rule also applies to Saturday/Sunday and the other weekdays.
- This/next weekend asks you to choose Saturday or Sunday. Saturday night means the upcoming Saturday with a disclosed 6 PM start default. Explicit clock bounds override that default.
- Type clock windows such as `at 6 PM`, `18:00`, `noon`, `from 6 PM to midnight`, or `between 6 and 9 PM`. `after 6 PM` starts no earlier than 6:01 PM; `before 10 PM` ends no later than 9:59 PM. Ambiguous `at 7` needs AM/PM.
- Dates use Python calendar arithmetic, never AI guesses. Baltimore uses America/New_York; unknown location timezones use a disclosed UTC fallback reference. The fictional catalog still only covers Baltimore.
- Past starts/dates, conflicting windows and overnight outings such as 10 PM–1 AM get an explanation. Nothing silently shifts to another day. DST-ambiguous/nonexistent times or windows crossing a clock change need a different window.
- Multiple or invalid dates require correction. The Date preference takes priority over dates in the text.
- Events without a date, or without a matching fixture on that date, produce a message. No different date or activity is substituted.
- Regular venue suggestions need no event fixture; real opening hours and availability remain unchecked.
- Without requested times, mock regular stops begin at 10 AM (or the current local minute if later today); evening/night defaults to 6 PM. Dinner begins no earlier than 5 PM. Event start times are fixed. Stops follow the order you list, include mock travel, cannot overlap, and must finish by midnight. Total duration includes waiting between scheduled stops.

### Preferences that change plans

- **Budget:** a hard cap in USD **per person**, including every mock activity. Explicit text like `$25 per person` is also understood. Zero is allowed for free activities.
- **Travel:** a hard cap on **total mock travel between stops**. It excludes getting there, returning home, and waiting for an event. Zero permits a single stop but not travel between multiple stops.
- **People:** filters mock capacity, not just the group total. Options have invented limits of 4, 8, or 20 people. For example, changing from 4 to 12 people eliminates smaller options. A group over 20 gets an explanation rather than invented capacity.
- **Cost preference:** ranks budget, balanced, or experience options first. Experience uses a fictional venue tier, not reviews or verified quality. Budget-friendly picks use lower costs; hard limits always win. Python selects up to three distinct options under the chosen mode; tight constraints can yield fewer. Confirmed fictional-data options precede provisional alternatives.

### Browser checks you can try

First click **Reset preferences** so old settings do not override your request. For each request, click **Plan my outing** and expand **View plan**.

| Request / setting | Expected result |
| --- | --- |
| `Dinner and karaoke in Baltimore for 4 people` | Both stops, dinner no earlier than 5 PM |
| `Coffee, museum, then coffee in Baltimore for 2 people` | Three ordered stops, with distinct coffee venues |
| `Lunch and dinner in Baltimore for 2 people` | Two food stops, only dinner constrained to 5 PM |
| `Baseball game in Baltimore for 4 people on 2026-11-07` | Fictional events on that exact date |
| `Concert in Baltimore for 4 people on 2026-11-08` | No matching fixture; no date substitution |
| `Dinner and skydiving in Baltimore for 2 people` | Unsupported explanation; no dinner-only plan |
| `Something competitive then cocktails in Baltimore for 6 people` | Suggestions labeled separately; no invented chosen activity |
| `Coffee in Baltimore for 2 people tomorrow` | Resolves tomorrow in Baltimore local time and plans that date |
| `Coffee` | Asks for unknown location and group size |
| `Coffee in Baltimore for 2 people`, budget `0` | No affordable coffee plan; cap is honored |


## About the sample data

**Every venue in mock mode is fictional.** Event schedules, start times, capacities, prices, neighborhood assignments, durations, and travel times are invented to demonstrate the interface. They are not verified quotes, actual routes, current availability, or opening hours.

Costs are per person, in USD. The group total is the sample per-person cost multiplied by the group size. Estimates exclude transport fares, taxes, tips, booking fees, and extras. Travel is the total between stops using a simple made-up neighborhood model; it excludes getting to the first stop and returning home. The displayed itinerary duration includes activities, inter-stop travel, and any waiting for scheduled events. Shopping prices exclude purchases; the free picnic option requires bringing your own food. No real bookings or reservations are made.

There is no user-account authentication, payment integration, database or production deployment. Task 46 adds deliberately enabled backend Google APIs using the existing keyless local authentication.

## Project files

- `data/mock-venues.json` — shared fictional catalog values for TypeScript and Python.
- `backend/mock_data.py` — validated shared fixture loader and venue/event retrieval.
- `backend/test_mock_data.py` — dataset validation, lookup, missing samples, and frontend consistency tests.
- `backend/models.py` — validated request, venue, candidate and ranking API contracts.
- `backend/planner.py` — Python candidate generation (Task 26), reused by the live API.
- `backend/ranking.py` — filtering, scheduling and ranking (Task 27), called by the live API. Ordinary outings remain explicitly provisional because the fixture has no opening hours.
- `backend/test_ranking.py` — hard constraints, modes, unknown data, stable/distinct selection and generator integration tests.
- `backend/test_models.py` — model validation and comparison with actual frontend planner results.
- `backend/main.py` — health, AI interpretation and validated planning endpoints.
- `backend/interpretation.py` — provider-independent normalization, grounding guards and manual precedence.
- `backend/date_resolution.py` — deterministic calendar/time resolution; policy and limitations in ARCHITECTURE.md.
- `app/api/interpret/route.ts` — server-side interpretation proxy.
- `backend/requirements.txt` — exact tested backend dependency versions, including required transitive packages.
- `backend/test_health.py` — real backend HTTP test using Python’s standard test library.
- `backend/.venv/` — local Python environment, excluded from Git.
- `app/api/health/route.ts` — server-side Next.js health endpoint calling Python.
- `app/api/health/route.test.ts` — HTTP communication and failure tests.
- `.env.example` — optional backend address example, with no secrets.
- `app/page.tsx` — homepage, request form, optional preferences, result cards.
- `app/globals.css` — Tailwind setup, responsive styles, and reduced-motion support.
- `app/layout.tsx` — page title, description, and root layout.
- `components/artwork.tsx` — original SVG illustrations. No remote images or font downloads.
- `lib/planner.ts` — display types/formatting plus historical resolver retained for regression tests only.
- `lib/planning-client.ts` — asynchronous proxy request and Python-to-card display adapter; no planning algorithm.
- `lib/legacy/planner.ts` — retired algorithm, isolated for historical regression/contract tests only.
- `data/demo-plans.json` — fixed inspiration cards, never used as a request fallback.
- `app/api/plans/generate/route.ts` — server-only Python planning proxy using `BACKEND_URL`.
- `app/api/plans/generate/route.test.ts` — real Python/proxy/client integration and upstream failure tests.
- `backend/test_api.py` — actual HTTP planning API validation and behavior tests.
- `lib/mock-data.ts` — typed adapter for the shared fixture plus activity keyword patterns.
- `lib/request.ts` — historical keyword/date resolver, used only by regression references.
- `lib/planner.test.ts` — tests for parsing, distinct plans, budgets, travel caps, and unsupported cities.

## Checks

Run these from the project folder:

```sh
npm test
npm run test:backend
npm run lint
npm run typecheck
npm run build
```

`npm test` checks historical regression behavior, current Python/proxy/client integration and Next.js health communication, including upstream errors, invalid responses, timeouts, and a stopped backend. `npm run test:backend` validates the shared dataset, retrieval helpers, planning models, candidate generation and filtering/ranking, compares them with actual TypeScript planner results (using the installed frontend dependencies), and starts a temporary backend on an available local port to check the HTTP response; neither test command requires the development servers to be running. `lint` checks code quality. `typecheck` checks TypeScript. `build` confirms Next.js can build the application.

To run a production build **locally**, run `npm run build` and then `npm start`. Keep the backend running in the other Terminal for planning and `/api/health`. This still does not deploy anything.

## Troubleshooting

- **“command not found: npm”**: install Node.js LTS, close Terminal, and reopen it.
- **“Cannot find module”**: run `npm install` in this folder, then try again.
- **The browser can't connect**: keep `npm run dev` running and use the exact Local URL printed in Terminal.
- **Health check says backend unavailable**: run `npm run dev:backend` in the first Terminal and wait for startup. Check that port 8000 is free and `BACKEND_URL` matches if you changed it.
- **“No module named uvicorn” or missing `backend/.venv/bin/python`**: follow the fresh-copy backend setup in step 4.
- **Old “Relative dates are not resolved yet” message after updating the project:** the running Python process may still have old code loaded. Stop that backend in its Terminal with Control+C, then run `npm run dev:backend` from the current project folder and retry. The startup command watches backend changes.
- **“AI interpretation unavailable”**: open the existing Ollama app, confirm `ollama list` includes `qwen3:4b`, and keep the Python backend running. No keyword fallback exists.
- **“Python planner unavailable”**: start `npm run dev:backend`, wait for startup, then retry. No browser fallback exists.
- **No plans appear**: check the explanation, try Baltimore, leave budget/travel blank, and click Try an example. Very low limits can exclude every sample combination.


## Task 28 verification you can repeat

With both servers running, click Try an example → Plan my outing → choose Surprise Me when asked → View plan. You should see sample results, fictional prices/times and an expandable About these estimates section. To test confirmed fictional-data feasibility, enter `Baseball and concert in Baltimore for 4 people on 2026-11-07`. For no matching event, use `Concert in Baltimore for 4 people on 2026-11-08`. For no affordable plan, enter `Coffee in Baltimore for 2 people` and set Maximum budget to `0`.

To prove Python is required, press Control+C in the backend Terminal only, then click Plan my outing again. The cards must disappear and an unavailable message must appear. Restart with `npm run dev:backend` and retry. The three cards visible before any submission are fixed inspiration examples only.

Task 27 ranks using normalized affordability, experience and travel weights; this differs from the retired planner’s separate budget/balanced/experience picks. Balanced can therefore favor a higher-priced venue when the combined score is better. Activity order and hard limits remain mandatory. Tasks 28–33 are complete. The active website uses local AI interpretation and Python planning.


Task 29 verification passed on October 20, 2026: real Python results, hard limits, all three spending modes, backend failure/recovery, delayed duplicate submission protection, and keyboard interactions at mobile, tablet and desktop sizes. All 75 backend tests, 56 frontend tests, lint, TypeScript and production build passed. An exact-midnight display error was fixed, and two preference hints were darkened for readability; the homepage layout is preserved. Detailed evidence and audit limits are recorded in HANDOVER.md.

## Local AI checks (Tasks 30–32)

The **Plan my outing** button uses the Python AI interface. Ollama/Qwen3 must be available for the default configuration; automated suites mock the model and require no running Ollama.

The selected model is **Qwen3 4B** (`qwen3:4b`, tested ID `359d7dd4bcda`), downloaded with owner approval. It occupies about 2.5 GB on disk; Task 30 reported about 3.2 GB loaded on the M2 Mac with its then-4096-token context. No Ollama reinstall or upgrade was needed. In Task 30, the four required requests were extracted correctly in two consecutive runs; the first call took about 5.5 seconds and warm calls about 1.6–1.9 seconds. This is a small local evaluation, not a guarantee for arbitrary requests.

From the project folder, with Ollama open, run:

```sh
backend/.venv/bin/python -m backend.ai.smoke
```

This sends four example requests to the installed model, prints extracted JSON and approximate seconds per request, and checks communication/schema validity. Review the printed values for accuracy: a valid JSON object can still contain invented or omitted information. This command never installs or downloads anything. If Ollama is stopped, open the existing Ollama app (or run `ollama serve` in another Terminal). `ollama list` shows installed model names; do not download a missing model without checking its size and approving the download first.

For configuration, export settings in the same Terminal before running Python. `.env.example` lists all names; Python does not automatically read `.env.local`.

```sh
export AI_PROVIDER=ollama
export AI_MODEL=qwen3:4b
export AI_BASE_URL=http://127.0.0.1:11434
export AI_TIMEOUT_SECONDS=60
```

`AI_MODEL` selects an installed model. The timeout is in seconds and must be positive. Keep these settings server-side; never use `NEXT_PUBLIC_`. No account, credential, Ollama Python SDK or new backend dependency is needed.

Reusable Python use (separate from the live planner):

```python
from backend.ai import AIError, create_provider

provider = create_provider()
try:
    partial = provider.interpret("Three friends want coffee under $15 each.")
    print(partial.model_dump(mode="json"))
except AIError as error:
    print(str(error))
```

Activity phrases are not supported-category IDs, and unknown group sizes/budgets/dates/locations remain nullable. Do not pass this partial extraction directly to the planner. Task 31 uses `interpret_request` to normalize and validate extraction, preserve unknowns, and apply manual preferences before constructing `OutingRequest`. Clear errors explain an unavailable Ollama service, missing model, timeout or invalid reply. The normal backend tests mock AI responses and verify replaceable providers without requiring Ollama.

For the focused Task 31 semantic/integration check, run:

```sh
backend/.venv/bin/python -u -m backend.ai.smoke_interpretation
```

It checks eight actual model requests, prints extraction, validation issues and Python plan counts, and exits unsuccessfully when the tested expectations fail. It covers explicit stops, repeats, separate lunch/dinner, indirect preferences, missing values, constraints, manual date override and the previously observed “tomorrow” failure. In the Task 31 run, tomorrow was retained by Qwen and also protected by the service guard; it remained unresolved. Task 32 now resolves these expressions deterministically; finite tests do not prove arbitrary-language accuracy. At the expanded schema/examples, observed warm calls were roughly 4.4–5.8 seconds; a first revised-provider call took about 12.7 seconds. Adapter context/output limits are now 8192/1024 tokens, still with thinking disabled and the same installed model.

The AI output contains nullable scalar constraints, original activity/date/time wording, preferences, suggestions and uncertainties. Suggestions never automatically become itinerary stops. Only USD catalog costs are supported; no currency conversion is performed. Text group budgets and per-leg travel caps are passed to the existing backend fields. Python resolves original date/time phrases into calendar dates and minutes since midnight; ambiguous or stop-specific times need rephrasing. AI-calculated calendar/time fields are ignored. Transport is preserved, but fictional travel remains mode-independent. Non-numeric tastes are recorded in notes, not presented as verified venue attributes.

For the focused Task 32 check against the installed Qwen3 4B, run:

```sh
backend/.venv/bin/python -u -m backend.ai.smoke_dates
```

It uses a fixed aware reference clock and checks 13 date/time requests, original model phrase preservation, clarification outcomes and actual Python planning. No model is downloaded. Task 32 verification and current limitations are recorded in HANDOVER.md. Task 33 adds the follow-up interaction described below.

## Follow-up questions (Task 33)

Type your outing normally; Set preferences remains optional. If an essential detail is missing, answer the short question below the request and click **Continue planning**. When both city and group size are missing, supply them together. For example, `Coffee` asks for a city, number of people and day; `Baltimore`, `4` and `Tomorrow` are enough to continue. You do not need to repeat “Coffee”.

Every outing needs a specific date before itineraries can be generated. If it is missing, answer “What day are you planning to go?” with Today, Tomorrow, This Saturday, Next Friday or a supported exact date. Weekend requests need Saturday, Sunday or an exact date. Unclear activities and clock windows may need a specific choice. Budget, travel caps, spending preferences and an exact start time remain optional; leaving them out does not trigger a question. Unsupported cities/activities, overnight outings and unavailable event dates get explanations without invented replacements.

Your original text, ordered/repeated stops, resolved date context, explicit caps and preferences are kept while you answer. Follow-up answers use deterministic validation without another model call. Settings you deliberately change still win; automatically displayed values do not become manual settings. Invalid answers and service errors keep the request available to correct or retry. Edit the original text or use **Try an example** to replace the outing; **Cancel follow-up** clears the pending clarification. Refreshing or closing the page clears this temporary state.

Follow-up fields accept simple city names, numbers (also one–twenty), supported activity names and the existing date/time wording. More complex corrections, currencies or constraints can require editing the original request. All planning still uses the same fictional catalog and Python engine.

### Required dates and response speed — Task 33 follow-up

A date in your original words or deliberately selected in Set preferences is used without another question. Missing city, group and date details are collected together; simple answers resume the original outing without another model call. A date does not verify the fictional venues’ hours, availability, prices or travel. There is no flexible-date comparison feature.

The measured bottleneck was local AI processing, rather than itinerary calculations. The same model now receives the schema once and can omit absent optional JSON fields; validation restores their existing defaults and preserves stated constraints. Measured before/after timings are recorded in HANDOVER.md; latency varies with device/model state. Date/ranking computation is milliseconds, and follow-up completion remains fast because it does not call the model again. No background warming service or new model is required.


### Interpretation validation (Task 34)

The app checks the AI's structured answer before planning. If a date, city or group size is unclear, answer the existing follow-up. For conflicting budgets, unsupported requirements or an unreliable interpretation, use the explanation to edit your request or set the relevant preference. Minimum spending and travel distance limits are unsupported; use maximum USD budgets and minutes/hours of travel. Automatic preference values come only from a validated request; settings you deliberately change still take priority.

An unavailable AI service or invalid AI response produces a retry message and no itinerary. There is no backup keyword interpreter. Date answers continue without another AI call. Checks cover common explicit wording, but unusual phrases may need rephrasing; fictional catalog results never verify real availability or venue requirements.

Optional actual-model Task 34 verification, with Ollama running:

```sh
backend/.venv/bin/python -m backend.ai.smoke_validation
```

Normal `npm test` and `npm run test:backend` remain independent of a running AI model.


## Google API safeguards and discovery (Tasks 39–40)

Keep using the same local startup commands above. Real providers are disabled by default; Task 46 connects them to the website only under the deliberate local switches above. No Google credential or billing setup is needed for the fictional planner. Leave `VENUE_DATA_MODE` unset (default `mock`) or set it to `mock` in the backend Terminal. Unknown mode values prevent backend startup; remove that override to resume mock mode. Python does not automatically read Next.js environment files.

Lower project quotas and local request-budget checks are implemented. The owner linked Free Trial billing; a $50/month account-wide alert budget is saved, and keyless local OAuth authentication is configured outside the project. Mock mode does not use those credentials. Alerts track actual usage before credits at $25/$45/$50 and do not stop requests; future linked projects would share the budget. See [verified settings, costs and exact owner approval steps](docs/billing-safeguards.md). No payment or account action is needed to continue locally. Task 40 provides an isolated backend development adapter. Its two authorized live verification attempts are complete; do not run additional live tests without separate authorization. Leave `WHERETO_PLACES_DEV` unset for normal use. See [discovery behavior and developer reference](docs/venue-discovery.md).
