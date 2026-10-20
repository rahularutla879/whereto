# Current architecture

Source baseline: October 20, 2026. A single-page Next.js App Router application with a client component and local planning modules, plus a minimal FastAPI backend. Next.js serves/renders the page; itinerary generation runs synchronously in the client. The backend only exposes health status; no backend planning endpoint or external service is implemented.

```text
Root layout + global styles
          |
Homepage: request text + optional preferences (React state)
          |
makePlans -> parse activities/location + resolve date
          |
Validate input -> fictional catalog -> capacity/date filtering
          |
Enumerate venue combinations in requested activity order
          |
Budget/travel filtering -> schedule stops -> rank/deduplicate
          |
Up to 3 cards + expandable details, or explanatory empty state
```

## Backend health boundary (Task 23)

`Browser or HTTP client -> Next.js GET /api/health -> FastAPI GET /health`

FastAPI runs locally through Uvicorn on `127.0.0.1:8000`. Next.js calls it server-side using `BACKEND_URL`, defaulting to that address; the variable is never sent to browser code. The homepage does not call the health endpoint or depend on backend availability. No CORS middleware is needed for this server-to-server call.

The Next.js route disables fetch/response caching, validates the expected status, and enforces a three-second timeout. Success returns `{"status":"ok","backend":"ok"}`; connection failures, timeouts, invalid JSON/status, and upstream HTTP errors return HTTP 503 `{"status":"error","backend":"unavailable"}` without exposing internal errors. Tests use local HTTP servers; Python's standard test library avoids extra backend test packages.

## Input to itinerary

1. app/page.tsx handles form submission and calls makePlans. Preferences override corresponding parsed values; blank fields use recognized text or defaults (Baltimore, four people, no budget/travel cap, balanced ranking).
2. lib/request.ts recognizes catalog keywords, preserves first-mentioned activity order, and reports unmatched text. Dates use Baltimore's calendar; an explicit reference day supports repeatable tests.
3. lib/planner.ts rejects unsupported cities/wording, invalid limits, and more than four distinct activities. Events require an exact matching fixture date. Candidate pools must have adequate mock capacity.
4. It enumerates venue combinations without reordering activities. Mock travel per leg is `5 + abs(zone difference) * 8` minutes. Total activity cost and total inter-stop travel must fit hard limits.
5. Scheduling starts ordinary stops at 10 AM, delays food to at least 5 PM when the request says dinner, and respects fixed event starts, travel, and a midnight finish. Duration includes waiting between stops.
6. Budget, balanced, and experience scores each select a best candidate; the selected preference comes first and duplicate winners are omitted. Cards show mock per-person cost, group total, travel, and scheduled stops. No result is persisted.

## Key files

| File | Responsibility |
| --- | --- |
| backend/main.py | FastAPI application and health endpoint |
| backend/requirements.txt | Pinned essential backend dependencies and required transitive packages |
| backend/test_health.py | Uvicorn HTTP health test |
| app/api/health/route.ts | Server-side health communication with timeout and failure response |
| app/api/health/route.test.ts | HTTP communication and failure tests |
| .env.example | Optional server-only backend address |
| app/layout.tsx | Root HTML, metadata, global stylesheet import |
| app/page.tsx | Homepage, request/preferences state, submit behavior, result/empty states, PlanCard expansion |
| app/globals.css | Tailwind import, colors, typography, responsive layout, reduced-motion styles |
| components/artwork.tsx | Original inline SVG hero/card illustrations |
| lib/request.ts | Activity/location parsing and calendar-date helpers |
| lib/mock-data.ts | Typed 29-category fictional catalog, venue tiers/capacities, two event dates |
| lib/planner.ts | Validation, combinations, mock travel, scheduling, ranking, display helpers |
| lib/planner.test.ts | Automated planner and parser behavior tests |
| package.json | Dependencies and development/check commands |
| next.config.ts, tsconfig.json, eslint.config.mjs, postcss.config.mjs | Framework, TypeScript, lint, and stylesheet tooling |

React state holds requests, preferences, results, and expanded cards in memory. There is no database, browser persistence, account system, or cross-session history. Icons use lucide-react; illustrations and fonts need no external media service.

## Future architecture — not implemented

Stages 1–3 in [TASKS.md](TASKS.md) need real venue/event lookup and route information, richer constraints and optimization, then a map, editing, conversation, saved versions, and sharing. Server-side credential handling will be needed if selected providers require secrets. API boundaries, providers, AI model, map library, storage, authentication, and hosting remain undecided; this is not a committed design.
