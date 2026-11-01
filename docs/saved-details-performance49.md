# Tasks 46/49 — saved details and first-search acceptance

November 1, 2026. Continues `9dffe78`. Tasks 50 and 50A–50E remain unstarted.
No schema, role, RLS, TLS, ranking weights, Cloud quota or billing configuration changes.

**Latest local status:** the owner separately approved automatic Pro retrieval on
November 1, 2026. `WHERETO_SAVED_AUTO_DETAILS_DEV=1` is now active only in the
Git-ignored owner profile; fresh clones, mock, CI and production remain unchanged.

## Saved details and authorization

The database deliberately retains Google Place IDs and app-owned planning structure,
not Google names, addresses, routes or provider response snapshots. Thus reopening
alone previously produced activity placeholders until manual Details loading. The
selected option, date, constraints and ordered original references remain unchanged.
Current details are current observations, not the original historical business data.

Reviewed [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies),
[Details fields](https://developers.google.com/maps/documentation/places/web-service/place-details),
[global prices](https://developers.google.com/maps/billing-and-pricing/pricing) and
[Places UI Kit setup](https://developers.google.com/maps/documentation/javascript/places-ui-kit/get-started).
Place IDs have a storage exception; this does not permit permanently retaining
unrestricted Places content. UI Kit would add a browser Maps JavaScript/key setup
and separately billed UI Kit operation. It was not enabled. Google-hosted Maps
links can open a place externally; they do not populate this app's detailed card.
No invented caching exemption or provider-content storage was introduced.

The existing backend Details flow is sufficient for bounded current information.
A **separate default-off** `WHERETO_SAVED_AUTO_DETAILS_DEV` switch now advertises
`automaticVenueDetails` on a successful reopen. Only if that switch, real local
mode and the existing contact/Details gate are all enabled does the client issue
one details action on explicit private-link navigation/reopening. It loads only
the selected option's unique references, maximum four. It uses a fresh UUID, no
retries, no background timers and an in-flight guard. Normal home navigation and
remembered-link availability never open a plan or call Google. Explicit saved-view
reload counts as another deliberate open and would use quota. Duplicate lifecycle
work and double-clicks are suppressed; multiple tabs still share provider limits.

**Owner approval received November 1, 2026.** The exact owner-only setting
`WHERETO_SAVED_AUTO_DETAILS_DEV=1` was enabled in ignored `backend/.env.development`
and loaded by the restarted local worker. Use `0` or remove it to disable. Do not
put it in public defaults, production or CI. This authorizes bounded Pro retrieval
on deliberate saved-link opens/reloads, not normal startup or remembered-link
detection. Manual contact-tier authorization remains separate. Verification used
only invented provider fixtures, an isolated ledger and blocked Google transport;
no live automatic-open request was dispatched during verification.

Automatic mode uses exactly the existing **Pro** mask:
`id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions`.
Published first paid global tier: $17/1,000 ($0.017/stop); two stops $0.034,
four stops $0.068, before applicable free allowances. The local conservative ledger
continues reserving $0.020/stop: $0.040/two or $0.080/four. No discounts/credits
are assumed. Automatic mode never selects optional Enterprise fields. The explicit
phone/website checkbox retains its existing Enterprise mask/gate: add
`nationalPhoneNumber,internationalPhoneNumber,websiteUri` ($20/1,000 first paid tier).
No new ratings, hours, reviews, photos, prices, inventory, Routes or discovery calls.

Names/addresses/status/validated provider map URLs, optional contacts and required
attributions stay only in component memory. They are neither saved in SQL nor
browser persistent storage. Partial failures retain the selected stop and earlier
in-memory facts marked stale. No current routes or historical travel estimates are
invented. A loaded card offers Update current venue details; empty/partial cards
retain Load current venue details. Original alternatives remain stored internally.

## Compact private links

One Your saved plan block has the 30-day sharing description, Copy link, native
new-tab Open saved plan and secondary Forget on this device. Reopen another saved
plan is collapsed and accepts pasted private links. Link and help, duplicate raw
URL input and repeated recovery paragraphs are removed. Clipboard failure tells
the user to use the browser's Copy link address on the actual link. Tokens remain
fragments, cleared after import, never in logs/analytics. Capability hashing,
expiration, selected-only presentation and return-to-planning behavior are unchanged.

## Why later detail loading stopped

The old code discarded admission scope and returned the same venue_refresh_limit
message for different conditions. Deterministic reproduction establishes:

| Boundary | Scope and recovery |
| --- | --- |
| Six Details | One capability, 30 minutes from valid refresh session creation; a two-stop plan can load three times. A new link has its own allowance. |
| Ten Details/minute | Shared process rolling window across all capabilities and ordinary contact loading; a new link cannot bypass it. |
| Persistent minute admission | Shared locked private ledger, ten Details per rolling minute, survives backend restart and covers separate processes. |
| Concurrency one | Shared process; wait for the active provider request to finish. No waiting queue/retry. |
| Fifty refresh sessions | Process registry, inactive entries expire after 30 minutes; known next capacity expiry is returned. |
| Normal-mode total attempts | Existing outing/process ceilings remain; owner exploration removes only previously approved fixed totals, not Details/minute/concurrency. |
| Daily local accounting | Existing owner exploration is a nonblocking $10 estimate warning, not a new hard daily Details quota. Explicit spending-guard unit tests still verify rejection without charging. |
| Cloud quota | Existing last-verified Details 40/day, ten/minute; shared project enforcement cannot be reset by links/restarts. No live quota query/change was performed. |

The owner's ledger was inspected read-only: seven Details reservations/dispatched
that local day, no active recent Details at inspection. This does not establish
Cloud remaining quota or reconstruct the exact historical failed requests. There
was no retained scope-specific evidence to prove which historical limit fired;
we do not claim it was a Cloud quota or database failure. New-link allowances did
not incorrectly share the six-request counter in deterministic reproduction.

A separate replay bug was reproduced: after the first stop failed, repeating the
same UUID could dispatch the previously unattempted second stop. Replay protection
now covers the entire action once any request has been admitted. A wholly rejected
pre-admission action releases its UUID marker and does not consume outing/ledger
allowances. Dispatched failures stay conservatively counted; partial success never
loses earlier results. No usage counters or owner ledger were reset.

Each failed venue now carries a fixed safe reason/message, retryability and a
bounded `retryAfterSeconds` only for a known local window/session expiry. The UI
shows the cause and disables manual loading during that interval, then merely
re-enables the button. It never retries automatically. Authentication/authorization,
local accounting/spending blocks and unspecified/daily Cloud quota require review.
Cloud minute rejection has no fabricated reset time. Google 404 alone is labeled
place unavailable. Database errors remain a separate top-level classified failure.
No SQL, exception text, provider error body, credential or private reference leaks.

## Measured first-search performance

Measurements use the installed `qwen3:4b`, same 8,192 context/schema/prompt/temperature
and zero repairs. Initial `/api/ps` showed no resident model. No model download,
model switch or server-wide Ollama settings change. Durations vary with load.

| Local AI measurement | Before | After startup preparation |
| --- | ---: | ---: |
| First extraction | 12,888.77 ms, genuinely cold | 4,096.53 ms, first after ready |
| Model load | 2,587.62 ms | 5.46 ms |
| Prompt processing | 6,787.24 ms | 214.17 ms |
| Response generation | 3,472.95 ms | 3,844.35 ms |
| Next two same-request searches | 3,651.93 / 3,646.05 ms | 3,929.80 / 4,071.07 ms |
| Warm median of those two | 3,648.99 ms | 4,000.44 ms |

This is a roughly 68% reduction in the first **post-readiness** extraction, not
faster warm inference. Cold work is moved to startup, not eliminated. Controlled
cold preparation itself took 11,309 ms; health returned 200 while it was preparing.
An immediate search before preparation finishes can still wait. The two warm
medians are not an improvement and are not presented as one. Warm movie extraction
was 3,728.64 ms before / 3,821.86 ms after; multi-activity 4,027.86 / 3,973.44 ms.
The model/API residency report was 3,856,589,127 bytes (~3.59 GiB), unchanged model
and context; not a measurement of total machine RAM. Keep-alive is finite ten
minutes, versus five previously. Idle expiry and Ollama unavailability remain safe.

The ignored owner profile enables `WHERETO_AI_WARMUP_DEV=1`. On backend lifespan,
one daemon thread sends one nonprivate sample through the actual extraction prompt
and validator, preparing both the model and its common prompt prefix. It does no
planning/Google/SQL work. Health does not wait. There is no polling/retry loop,
new model, remote warmup, CI/production or mock-mode startup preparation. If local
Ollama is unavailable the request boundary still gives its actionable error.
The default-off flag is available to disable preparation. Fresh clones stay mock.

A deterministic keyword shortcut was **not** introduced: Task 34's source checks,
open-ended brands/activities, relative dates, geography, order and mandatory limits
make an opportunistic bypass unsafe without a larger interpreter change. No
Google concurrency/speculation change: existing concurrency-one admission and
routing/ranking remain authoritative. User-visible loading follows actual stages:
Understanding your request, then Checking venues and travel, with no percentages.

Reproducible provider-shaped offline benchmark:

```sh
cd ~/Documents/whereto
backend/.venv/bin/python -m backend.benchmark_acceptance49
# Optional installed local model only; still blocks Google:
backend/.venv/bin/python -m backend.benchmark_acceptance49 --local-ai
```

Median of three runs per shape:

| Stage | Single-stop, local Qwen | Two-stop, local Qwen |
| --- | ---: | ---: |
| Input validation | 0.009 ms | 0.009 ms |
| Interpretation + calendar/source validation | 3,867.926 ms | 3,950.361 ms |
| Discovery + normalization/filtering, inclusive | 2.247 ms | 5.640 ms |
| Simulated Places transport subset | 0.012 ms | 0.030 ms |
| Simulated Routes transport subset | 0 ms (not needed) | 0.009 ms |
| Routing shortlist | 0.006 ms | 0.035 ms |
| Candidate evaluation, inclusive | 0.125 ms | 0.674 ms |
| Scoring | 0.055 ms | 0.168 ms |
| Complete planning, inclusive | 8.943 ms | 39.791 ms |
| Serialization | 0.722 ms | 1.558 ms |
| Complete local pipeline | 3,877.375 ms | 3,989.915 ms |

The fixture-AI/provider pipeline medians were 8.799/34.993 ms; the separate fictional
planner took 0.027/0.024 ms in those shapes. Inclusive timings overlap and must not
be summed. Calendar/geography validation is included in interpretation/discovery;
beam/diversity remain included in complete planning, not separately measured.
One-/two-stop fixtures dispatched 1/3 simulated Searches and 0/16 simulated matrix
cells, unchanged by preparation; gross illustrative estimates $0.035/$0.185.
Actual Google calls and cost: zero. These fixture transport timings are **not live
Google latency**. The local AI stage dominated the measured cold/warm runs.

Local development diagnostics add only numeric Ollama load/prompt/generation/HTTP/
structured-validation timings and preparation state; no prompt/output/precise GPS.
Development Server-Timing separates backend duration from measured proxy overhead;
production proxies do not forward it. No raw timing panel is added to the product.
Actual live Places/Routes latency and a controlled before/after browser-paint
benchmark were not measured because this task forbids automated billable calls.
Browser interaction checks demonstrate usable results, not precise paint timings.

## Verification

Final suite totals, hosted fixture cleanup and browser dimensions/results are in
HANDOVER.md. Tests cover independent capabilities, same UUID/multiple tabs,
partial success, local minute reset, session expiry, persistent minute/restart,
daily spending guard, Cloud daily/minute/unknown, authentication/authorization,
DB rejection before provider admission, manual Pro/Enterprise masks, readiness
once/default-off/remote/CI/mock guards, compact controls and existing regressions.
No owner saved record is modified. Automatic retrieval is now separately owner-authorized and enabled only in the
private local profile. Real provider success/coverage was not tested live.

Local HTTP fixture checks through the running Next.js proxy returned 200 and three
options on all three iterations. Interpretation HTTP: 51.946/11.549/8.799 ms;
planning HTTP: 38.920/21.240/22.107 ms. Planning Server-Timing measured backend
16.092/10.626/10.345 ms and proxy overhead 6.040/2.583/2.426 ms. These use invented
AI/provider responses, not warm Qwen or live network providers; frontend development
compilation and browser paint are outside the server timing values.

Delivery verification: backend 622 reported (604 executed, 18 opt-in skips),
165.230s; separate hosted 35/35 including those 18 real PostgreSQL checks;
frontend 208/208, 116.655s; TypeScript/ESLint/production build/pip check passed.
Three committed browser fixtures were independently reopened and then removed only
by their recorded hashes; five unrelated plans remain intact. Loaded selected
cards measured 390/390, 529/529 and 1280/1280 client/scroll widths, with keyboard
focus and copy/new-tab/pasted-link/partial-error/restart checks. Actual live Google
calls: zero. Normal services restored and temporary browser tabs closed.
