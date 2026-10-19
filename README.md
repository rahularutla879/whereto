# where to?

**Less planning. More hanging out.**

A mobile-first outing planner built with Next.js (App Router), TypeScript, React, and Tailwind CSS. This first version is a frontend demo: the planner uses deterministic local rules and fictional Baltimore venues. It does not connect to an AI service or any external API.

## Start the website — beginner instructions

You need **Node.js 20.9 or newer** and **npm**. They are already installed on the computer used to create this project. If you're using another computer, install the LTS version from [nodejs.org](https://nodejs.org/) first.

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

4. Start the website:

   ```sh
   npm run dev
   ```

5. Keep Terminal open. Open your web browser and visit **[http://localhost:3000](http://localhost:3000)**. If Terminal shows a different port because 3000 is busy, use the address it prints instead.

6. To stop the website, click in Terminal and press **Control + C**.

You can edit files and see changes in the browser while the development server is running. Starting it does not publish your site on the internet. No accounts, API keys, or `.env` file are needed.

## Try the planner

Click **Try an example**, then **Plan my outing**. Or type:

> We're 4 friends in Baltimore. We want bowling, drinks, and a movie this Saturday.

You will get three distinct demo plans. Use **View plan** to expand each itinerary and see its fictional venues, sample durations, per-person costs, and estimated group total.

Try these requests too:

- `Coffee and art in Baltimore for 2 people tomorrow`
- `We're 6 friends in Baltimore. We want food and a movie on Friday.`
- `A walk and coffee in Baltimore this Sunday`

**Set preferences** lets you override the location, day, group size, maximum budget per person, maximum total travel time between stops, and cost preference. A zero budget is supported for free activities. Reset preferences to clear overrides. The cost preference changes the first recommendation. Group size also filters mock capacity.

## Planner review and improvements

The original planner recognized only **bowling, drinks, movies, food, coffee, outdoors, and art**. Museums were folded into art. Karaoke was not recognized: a dinner-and-karaoke request could return dinner alone. An entirely unknown request silently fell back to bowling, drinks, and a movie. Group size only changed the displayed total, and dates were labels without event schedules.

The updated planner supports **29 categories**:

- Regular venues: bowling, drinks, movies, food/dinner, coffee, outdoor walks/parks, art galleries, museums, karaoke, arcades, escape rooms, mini golf, shopping, zoos, hiking, picnics, and skating.
- Scheduled events: baseball, basketball, football, soccer, hockey, general sporting events, concerts/live music, theater/plays, musicals, ballet, opera, and comedy shows.

Museums and galleries are separate. A baseball request cannot be replaced with another sport. Ballet and opera have their own fictional performances rather than being replaced with a stage play.

### Unknown requests

There is **no unrelated activity fallback**. If the parser cannot understand part of a request (including an unknown activity mixed with a supported one), it returns an explanation and no partial plan. More than four activities are rejected instead of silently dropping extras. Ambiguous wording such as “concert or theater,” negations, and “concert after dinner” asks you to simplify: list the activities in the order you want, e.g. `Dinner and concert`.

This is a conservative keyword parser, not an AI service. It may ask you to rephrase ordinary descriptions, named artists/teams, specific times, or other wording it cannot understand. Use the preference controls for exact dates, group size, and limits. It does not claim to understand arbitrary natural language. Requests are not sent to an external service or saved.

### Fictional dates and timing

All scheduled events have **invented entries only on November 7 and November 14, 2026**. These dates are fixture data, not real schedules. Expand **Supported activities & fictional event dates** under the planner to see the catalog and instructions.

- Set the Date preference or type a date such as `2026-11-07` or `November 7, 2026`.
- Simple weekdays, today/tonight, and tomorrow resolve using the current calendar day in **America/New_York** (Baltimore). A weekday means its next occurrence, including today; “next Saturday” means the next future Saturday. An explicit reference day is injected in automated tests.
- Multiple or invalid dates require correction. The Date preference takes priority over dates in the text.
- Events without a date, or without a matching fixture on that date, produce a message. No different date or activity is substituted.
- Regular venue suggestions need no event fixture; real opening hours and availability remain unchecked.
- Mock regular stops begin at 10 AM, and dinner begins no earlier than 5 PM. Event start times are fixed. Stops follow the order you list, include mock travel, cannot overlap, and must finish by midnight. Total duration includes waiting between scheduled stops.

### Preferences that change plans

- **Budget:** a hard cap in USD **per person**, including every mock activity. Explicit text like `$25 per person` is also understood. Zero is allowed for free activities.
- **Travel:** a hard cap on **total mock travel between stops**. It excludes getting there, returning home, and waiting for an event. Zero permits a single stop but not travel between multiple stops.
- **People:** filters mock capacity, not just the group total. Options have invented limits of 4, 8, or 20 people. For example, changing from 4 to 12 people eliminates smaller options. A group over 20 gets an explanation rather than invented capacity.
- **Cost preference:** ranks budget, balanced, or experience options first. Experience uses a fictional venue tier, not reviews or verified quality. Budget-friendly picks use lower costs; hard limits always win. Duplicate best picks are omitted, so tight constraints can yield fewer than three options.

### Browser checks you can try

First click **Reset preferences** so old settings do not override your request. For each request, click **Plan my outing** and expand **View plan**.

| Request / setting | Expected result |
| --- | --- |
| `Dinner and karaoke in Baltimore` | Food and karaoke stops, no missing karaoke |
| `Museum and coffee in Baltimore` | Museum and coffee, not an art-gallery substitution |
| `Baseball game in Baltimore on 2026-11-07` | Only fictional baseball events on that date, with mock start times |
| `Baseball game in Baltimore on 2026-11-08` | No matching mock event; no unrelated plan |
| `Concert in Baltimore` | Asks for a date and shows the fictional fixture dates |
| `Dinner and skydiving in Baltimore` | Explains unsupported wording; no dinner-only plan |
| `Concert and theater on 2026-11-07` | Explains timing constraints; overlapping shows cannot fit |
| `Dinner and karaoke`, budget `25` | Only plans costing at most $25 per person |
| `Dinner and karaoke`, 12 people | Only mock options with capacity for at least 12 |
| `Bowling and drinks`, budget `30`, travel `5` | Removes routes over five total mock travel minutes |
| `Dinner and karaoke`, no limits, switch Budget-friendly / Best experience | The first recommendation and price change |

## About the sample data

**Every venue is fictional.** Event schedules, start times, capacities, prices, neighborhood assignments, durations, and travel times are invented to demonstrate the interface. They are not verified quotes, actual routes, current availability, or opening hours.

Costs are per person, in USD. The group total is the sample per-person cost multiplied by the group size. Estimates exclude transport fares, taxes, tips, booking fees, and extras. Travel is the total between stops using a simple made-up neighborhood model; it excludes getting to the first stop and returning home. The displayed itinerary duration includes activities, inter-stop travel, and any waiting for scheduled events. Shopping prices exclude purchases; the free picnic option requires bringing your own food. No real bookings or reservations are made.

There is no authentication, payment integration, database, external API integration, or production deployment.

## Project files

- `app/page.tsx` — homepage, request form, optional preferences, result cards.
- `app/globals.css` — Tailwind setup, responsive styles, and reduced-motion support.
- `app/layout.tsx` — page title, description, and root layout.
- `components/artwork.tsx` — original SVG illustrations. No remote images or font downloads.
- `lib/planner.ts` — constraint filtering, scheduling, ranking, and deterministic planner logic.
- `lib/mock-data.ts` — typed fictional catalog, capacities, prices, and fixed event fixtures.
- `lib/request.ts` — conservative activity recognition and calendar-date resolution.
- `lib/planner.test.ts` — tests for parsing, distinct plans, budgets, travel caps, and unsupported cities.

## Checks

Run these from the project folder:

```sh
npm test
npm run lint
npm run typecheck
npm run build
```

`npm test` checks the planner's behavior. `lint` checks code quality. `typecheck` checks TypeScript. `build` confirms Next.js can build the application.

To run a production build **locally**, run `npm run build` and then `npm start`. This still does not deploy anything.

## Troubleshooting

- **“command not found: npm”**: install Node.js LTS, close Terminal, and reopen it.
- **“Cannot find module”**: run `npm install` in this folder, then try again.
- **The browser can't connect**: keep `npm run dev` running and use the exact Local URL printed in Terminal.
- **No plans appear**: check the explanation, try Baltimore, leave budget/travel blank, and click Try an example. Very low limits can exclude every sample combination.
