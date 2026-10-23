# Task 39 — billing and provider safeguards

Status: **partially complete / awaiting owner authorization**. Checked October 22–23, 2026 in the existing signed-in Cloud Console. No billing authorization or permission to make Google data requests is implied. Task 40 has not started.

## Verified Cloud state

Project **Where To**, ID **`where-to-512422`**. Places API (New), `places.googleapis.com`, and Routes API, `routes.googleapis.com`, both show API Enabled. Maps JavaScript API, `maps-backend.googleapis.com`, still offers “enable this API” and is disabled. The project Billing page explicitly reports no linked billing account. Credentials lists no API keys, no OAuth clients and no service accounts. None were created.

Only Console administration, public documentation and local test traffic were used. No live Places/Routes data request, billing link, trial enrollment, card entry, paid signup/terms acceptance or other API activation occurred.

## Actual project quotas: before and after

These are observed values, not assumed Google defaults. All applicable displayed usage counters were zero. Changes were submitted as reductions and verified in both updated table values and success receipts. No increases or permission changes were needed.

| API/method | Per day before → after | Per minute before → after |
| --- | --- | --- |
| Places SearchTextRequest | 100 → **20 requests** | 600 → **10 requests** |
| Places SearchNearbyRequest | 100 → **20 requests** | 600 → **10 requests** |
| Places GetPlaceRequest | 100 → **40 requests** | 600 → **10 requests** |
| Places AutocompletePlacesRequest | 100 → **0** | 12,000 unchanged |
| Places GetPhotoMediaRequest | 175,000 → **0** | 600 unchanged |
| Places LookupMediaRequest | 100 → **0** | 600 unchanged |
| Places LookupReviewPostsRequest | 100 → **0** | 600 unchanged |
| Places LookupUserContentSummaryRequest | 100 → **0** | 600 unchanged |
| Places SearchMediaRequest | Unlimited → **0** | 600 unchanged |
| Places SearchReviewPostsRequest | Unlimited → **0** | 600 unchanged |
| Routes ComputeRoutes (per request) | 100 → **20 requests** | 3,000 → **10 requests** |
| Routes ComputeRouteMatrix (per element) | Unlimited → **300 elements** | 3,000 → **60 elements** |

All ten Places per-minute-per-user quotas and both Routes per-minute-per-user quotas were Unlimited and remain unchanged. They showed no usage measurement; project-wide limits above still apply. Other services were untouched. There were **17 quota reductions** in total. Unused Places methods have zero daily quotas; leaving their rate quotas unchanged does not authorize their use.

Rationale: four activity searches per outing × five local test outings = 20 searches/day for a chosen search method; Details allows up to eight selective lookups per test outing. Both search methods have separate quotas, so these are not one combined 20-search allowance. Ten requests/minute supports deliberate single-developer tests. Three candidates at each of four stops require three adjacent 3 × 3 matrices = **27 elements per outing**; 300/day accommodates about ten such outings, and 60/minute allows two without a large burst. Ordinary route calls have their own 20/day limit. These are deliberately small initial ceilings; future code must stop or explain insufficient coverage rather than silently omit activities.

The Maps-specific quota URL redirected to card-verification/free-trial signup. No signup was accepted. The ordinary [Quotas and system limits page](https://console.cloud.google.com/iam-admin/quotas?project=where-to-512422) provided working administration without billing. Thus quota editing itself was **not blocked** by billing in this project. Recheck all limits after any future billing/setup change.

Per-minute quotas control bursts, not monthly spending. Daily quotas reset and are also not monthly dollar caps. We cannot guarantee a hard monthly spending ceiling with this configuration or application counters.

## Costs to understand before approval

Current global USD pay-as-you-go list; free events are monthly **per SKU**, not a blanket project allowance. First paid tier, per 1,000 events:

| Service/SKU | Free events/month | Paid USD/1,000 |
| --- | ---: | ---: |
| Text/Nearby Search Pro (each) | 5,000 | $32 |
| Text/Nearby Search Enterprise (each) | 1,000 | $35 |
| Text/Nearby Search Enterprise + Atmosphere (each) | 1,000 | $40 |
| Details Essentials / Pro / Enterprise / Atmosphere | 10,000 / 5,000 / 1,000 / 1,000 | $5 / $17 / $20 / $25 |
| Details Photos | 1,000 | $7 |
| Autocomplete Requests | 10,000 | $2.83 |
| Compute Routes Essentials / Pro / Enterprise | 10,000 / 5,000 / 1,000 | $5 / $10 / $15 |
| Matrix Essentials / Pro / Enterprise (elements) | 10,000 / 5,000 / 1,000 | $5 / $10 / $15 |

Text Search and Details IDs-only SKUs have unlimited no-cost events. This does not make richer requests free. Billing-account usage is aggregated across linked projects. Prices/allowances can change; recheck before activation. [Official pricing](https://developers.google.com/maps/billing-and-pricing/pricing).

Places bills the highest requested field tier. For example, `displayName` triggers Pro; `rating`, `regularOpeningHours`, `currentOpeningHours`, `priceLevel` and `websiteUri` trigger Enterprise; reviews and atmosphere data can trigger Enterprise + Atmosphere. Request only explicit needed fields, never a wildcard. Retrieving photo media is separate from asking for photo metadata. Pagination adds requests. [Field tiers](https://developers.google.com/maps/documentation/places/web-service/data-fields), [Places usage and per-method quotas](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing).

A route request and a matrix request are different: a 3-origin × 3-destination matrix has **9 billable elements**, even though sent as one HTTP request. Traffic-aware routing, waypoint optimization, and 11–25 intermediate waypoints can raise Compute Routes to Pro; two-wheel routing can raise it to Enterprise. Use the least costly required features after approval. [SKU triggers](https://developers.google.com/maps/billing-and-pricing/sku-details), [Routes usage and limits](https://developers.google.com/maps/documentation/routes/usage-and-billing). The app's 27-element ceiling is below Google's documented 625-element ordinary matrix maximum and 100-element transit/TRAFFIC_AWARE_OPTIMAL maximum.

Both APIs require billing for use, even where an allowance applies: [Places setup](https://developers.google.com/maps/documentation/places/web-service/get-api-key), [Routes setup](https://developers.google.com/maps/documentation/routes/get-api-key). Free allowances do **not** guarantee no charges, particularly for higher tiers, other linked projects or credential abuse.

## Budget: proposed, not created

The [project Budgets and alerts page](https://console.cloud.google.com/billing/budgets?project=where-to-512422) asks to **select a billing account** before any budget can be created. The project is unlinked. A project-scoped billing budget/alerts cannot be finished for this project in that state. This is a billing-authorization blocker, not a quota-permission error.

Recommendation, **subject to owner approval**: a $5 USD monthly alerts-only budget scoped to this project and all services, with actual-spend email alerts at **50% ($2.50), 90% ($4.50), 100% ($5)**. Include project-owner and billing-administrator recipients, verify the owner's email recipient in Console without recording it in Git, and exclude credits from the cost basis where supported to avoid hiding usage. These custom thresholds are supported. Notifications may lag costs; they do not stop requests or enforce a $5 ceiling. Current Cloud spend-cap budgets list eligible Cloud services, **not Places or Routes**. [Budget instructions and permissions](https://docs.cloud.google.com/billing/docs/how-to/budgets), [spend-cap eligibility](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

Owner steps, only if choosing to authorize financial setup:

1. Open [project Billing](https://console.cloud.google.com/billing/linkedaccount?project=where-to-512422), verify **Where To** / `where-to-512422`, and decide whether to authorize linking a Cloud Billing account and accepting Google's financial/API terms. Card entry, personal account verification and financial/terms decisions are for the owner; do not share payment details in chat or Git. No action is required to remain safely in mock mode.
2. After explicit approval and account setup, recheck quotas. In **Billing → Budgets & alerts → Create budget**, select the linked account, name the budget “Where To development”, choose this project, all services, Monthly, Specified amount **$5**, and the three actual-spend thresholds above. Verify email recipients and save. Budget creation needs billing-budget permissions (for example Billing Account Costs Manager/Administrator, or supported project-scoped permissions); do not broaden IAM speculatively.
3. Confirm the saved budget, thresholds and recipients before considering credentials or live use. Linking billing alone does not approve live requests. No automatic billing-disabling workflow or extra paid infrastructure was configured.

## Credentials: deliberately deferred

For server-side web-service keys, use **IP address application restrictions** matching the public source IP Google observes, plus API restrictions for only the required service. Prefer separate Places-only and Routes-only keys and separate development/production credentials when those environments exist. Browser referrers are inappropriate for the Python backend; `127.0.0.1` and private LAN addresses are not the public outbound address. [Official security guidance](https://developers.google.com/maps/api-security-best-practices).

No stable public egress IP has been established for the local Mac or future host. Do not invent one or allow broad IP ranges. Defer keys until a verified, suitably stable outbound IP is available; otherwise evaluate supported server OAuth separately in an authorized task. No static-IP service, proxy or OAuth setup was added. Future credentials need an approved backend-only secret location (untracked environment/secure store locally, hosting secret injection later), API and application restrictions at creation, and no key value in logs, source, GitHub, `NEXT_PUBLIC_*`, client components or browser bundles. No secret location was needed or populated now.

## Implemented application controls and limits

`backend/provider_budget.py` uses existing Pydantic, standard-library locks/context managers and unittest. FastAPI creates one session budget per process at startup. Only `VENUE_DATA_MODE=mock` is accepted; omission defaults to mock, and any live/invalid value fails startup. `require_live_provider()` always refuses live access; there is no enabling environment switch, Google client, transport, discovery implementation or frontend integration.

| Guard for future adapters | Ceiling |
| --- | ---: |
| Searches per outing, across methods/pages | 4 |
| Candidates per activity before routing | 3 |
| Matrix elements per outing | 27 |
| All provider attempts per outing, including details/routes | 20 |
| Concurrent external attempts per backend process | 1 |
| Automatic retries | 0 |
| All provider attempts per local process/session | 50 |
| Matrix elements per process/session | 300 |

Counts reserve atomically **before** work; failures retain consumed attempts/elements. Duplicate exact request identities within an outing are rejected, including after failure; no automatic retry or response cache exists. Concurrency contention and limit violations raise understandable `ProviderLimitError` messages before work; concurrency capacity is released even after exceptions. Matrix accounting reserves the full product, not one request. Settings are immutable and can only be lowered within these ceilings. Candidate checks reject excessive counts instead of silently truncating.

These are tested **accounting primitives prepared for later adapters**, not a completed external integration. Future adapters must call the live authorization gate first, use the shared process budget, share one outing budget across the whole planning flow, reserve every attempt/page/lookup, use stable exact-request identities, avoid hidden SDK retries, and return safe errors at their boundary. Search belongs before candidate combination (`planner._pools`); routing should batch adjacent candidate pairs before ranking, not issue requests for every itinerary or from `evaluate_candidate`. Reuse results within the outing in a manner allowed by provider terms; no persistent Google data cache was implemented.

The existing mock candidate generator remains exhaustive (up to 81 combinations), and fictional venue/travel evidence, AI interpretation, validation, date resolution, clarification, manual edits and ranking remain unchanged. Local Ollama has its existing separate settings and no automatic retry; this budget is for future venue/travel providers.

Process restarts, reloads, multiple workers, machines and newly created sessions reset/multiply counters. Keep future local live testing to one worker and deliberately review usage before a restart. These controls do not stop another credential user or guarantee a maximum monthly bill. No database, Redis, queue, SDK or dependency was added.

## Verification and stopping point

Passed: **204 backend tests**, **102 frontend tests**, ESLint, TypeScript checks and production build. Ten focused budget tests cover strict settings, disabled live mode, attempts/search/candidate/matrix limits, cross-outing session accounting, duplicate/retry refusal, failure retention, concurrent threads/release, invalid arguments and network-free unchanged mock results. Initial sandbox runs failed on local sockets/tsx IPC; approved reruns passed. One initial new test used invalid category names; corrected to the existing `drinks`/`food` IDs before passing.

No real-model smoke test or local planner browser/visual regression was rerun; existing HTTP/AI-fixture/interpretation/planning regressions passed. Cloud browser verification covers actual project/API/billing/credentials/quota states. Full diff/new-file and secret-pattern review is required before commit; release tags must be preserved.

Stop at **Task 39 partial**: quotas and local safeguards are established; budget setup awaits billing approval, credentials await secure egress/secret handling, and live use awaits separate explicit authorization. Before Task 40 uses real data, close these blockers, reverify saved limits/alerts/restrictions and plan a bounded field mask/SKU. Do not begin Task 40 now.
