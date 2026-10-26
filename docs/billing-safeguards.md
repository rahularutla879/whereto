> Task 46 now connects these components to the existing local planner. Mock remains default; real mode and contact lookups require deliberate switches. [Current flow, safeguards and closed live ledger](real-planning.md). Sections below preserve earlier task checkpoints.

# Task 39 — billing and provider safeguards

Status: **Tasks 39–42 complete; discovery disabled by default**. Task 40 adds an isolated, explicitly gated backend discovery adapter; exactly two authorized live Text Search attempts occurred (400, then 200). See the Task 40 section at the end and [venue discovery](venue-discovery.md). Earlier Task 39 checkpoints below are historical; later dated sections supersede them. Safeguards were reverified October 23, 2026. Task 40's live allowance is exhausted; further requests need separate authorization. No paid upgrade is authorized. Tasks 41–42 add offline normalization and candidate quality checks; no new live requests, fields, dependencies or safeguard changes. The Task 42 tests use synthetic responses only. Cloud quotas/billing were not rechecked or changed for this offline work. Task 43 has not started.

## Verified Cloud state

Project **Where To**, ID **`where-to-512422`**. Places API (New), `places.googleapis.com`, and Routes API, `routes.googleapis.com`, both show API Enabled. Maps JavaScript API, `maps-backend.googleapis.com`, still offers “enable this API” and is disabled. The project is now linked to the owner-created Free Trial billing account. Earlier unlinked-billing evidence below is historical; see the continuation section. There are no API keys or application OAuth clients. One dedicated keyless service account and local impersonated ADC are now configured; see the final authentication section.

Only Cloud administration, OAuth/IAM authentication, public documentation and local checks were performed by the agent. The owner separately completed trial signup and project billing linkage. The agent made no live Places/Routes request, paid upgrade, card entry or financial terms acceptance. Only the two identity APIs recorded in the authentication section were additionally enabled.

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

## Earlier budget proposal — historical, superseded by continuation

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

Earlier stopping point: **Task 39 partial**. The owner has since completed trial signup; see the continuation for the remaining credential blocker. Live use still needs separate explicit authorization. Before Task 40 uses real data, close these blockers, reverify saved limits/alerts/restrictions and plan a bounded field mask/SKU. Do not begin Task 40 now.


## October 23 continuation — Free Trial and quota review

The owner personally enrolled in the Free Trial and authorized a **$50** monthly alert budget (Part 2), superseding the old $5 proposal; the completion-report reference to $5 was treated as stale. No paid upgrade or live Maps traffic is authorized.

### Billing verification

- The project welcome page explicitly says **You're in free trial**, **0 out of $300 credits used**, and **Expires 21 January 2027**. The billing-account banner independently displays **$300.00 credit and 90 days remaining**. These are observed values, not an assumed signup balance or calculated expiration. Usage reporting can lag.
- Opening this project's linked Billing page leads to **My Billing Account**. That account's Account management table explicitly lists **Where To / where-to-512422** under Projects linked to this billing account. Its type label is **Direct** (direct billing, not proof of a paid account); the explicit Free Trial banner and Upgrade control establish current trial status. No billing-account ID or personal financial information is committed.
- Google documents that the Free Trial does not automatically upgrade: without an upgrade, it ends when credit is exhausted or the trial expires and associated resources stop. That is a trial-wide protection, not a configurable $50 monthly limit. Never click Upgrade without separate owner authorization. [Free Trial behavior](https://docs.cloud.google.com/free/docs/free-cloud-features).
- The budget form offers **Spend cap enforcement (available for limited services)**. Google's current eligible-service list includes Gemini API, Agent Platform, Cloud Run and Cloud Run functions, **not Places or Routes**. No usable Maps monthly spend-cap budget was established, and no spend-cap feature was activated. Alerts are not a hard cap and can arrive after usage costs accrue. [Eligibility and limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

### Budget saved and independently verified

The owner explicitly approved **account-wide scope** after the project picker listed Where To with a disabled checkbox and left only **All projects (1)** available. No cause for this Console scope limitation was established. This broader scope is intentional and approved; it is **not a project-only budget**.

Saved budget **Where To development**, **Monthly**, specified amount **$50 USD**, alerts-only, all projects/all services on the linked account. The independent budget listing shows **This billing account**, **50%, 90% and 100%**, **$0.00/$50.00**, **No credits used**, and spend-cap status **Not applicable**. Reopened saved settings verify actual-cost triggers at **$25, $45 and $50**, both **Savings programmes** and **Other savings** unchecked, and **Email alerts to billing admins and users** checked. Promotional/free credits are therefore excluded from the budget calculation: it watches usage cost before credits, rather than just a post-credit amount payable. This is actual reported cost, not forecasted cost; reporting can lag over 24 hours. [Budget cost basis](https://docs.cloud.google.com/billing/docs/how-to/budgets).

The billing account currently has only Where To linked; **any projects linked later will also count toward this same $50 budget**. Separate project-owner email is disabled for this account-wide scope; notifications use the enabled billing-admin/user recipient roles. Individual recipient delivery was not independently verified. No custom Monitoring channel or Pub/Sub topic was added. Configuration is verified; no notification email delivery test or billable threshold test was performed. No old $5 budget was created. This alert budget neither pauses APIs nor caps spending.

### Quotas reverified, no changes

All **17 reductions in the table above remain active** after signup, including zero daily quotas for seven unused Places methods. All displayed measurable usage is zero; per-user quotas remain Unlimited. The quota table now labels these quotas **Adjustable: No**. No edit or increase was submitted, and the reason for that label was not established; owner approval alone must not be assumed to make increases available. Do not upgrade to paid to obtain quota changes without explicit authorization.

Current official pricing rechecked: Search Pro/Details Pro each have 5,000 free monthly events per SKU; Details Essentials and Routes/Matrix Essentials each have 10,000; Enterprise categories have 1,000. Paid prices and relevant categories remain as in the cost table. Do not use the obsolete $200 monthly-credit summary still present on some usage pages. Places charges depend on the highest requested field tier; matrix billing counts origins × destinations. The account's $300 trial credit is separate from these SKU allowances. [Current pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [Places billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing), [Routes billing](https://developers.google.com/maps/documentation/routes/usage-and-billing).

### Proposed development limits — NOT applied

The initial limits protected a project with no billing safeguards. Twenty searches/day allows only five four-activity tests per chosen method. Three candidates/activity and 27 matrix elements constrain discovery quality. A reasonable next controlled trial is around ten four-activity outings per active testing day, with up to two searches per activity, five candidates/activity and selective details for at most twelve venues. This is a proposal for approval, not permission for live work.

| Google quota | Current day / minute | Proposed day / minute |
| --- | --- | --- |
| Text Search (separate method) | 20 / 10 requests | **100 / 20 requests** |
| Nearby Search (separate method) | 20 / 10 requests | **100 / 20 requests** |
| Place Details | 40 / 10 requests | **150 / 30 requests** |
| Compute Routes | 20 / 10 requests | **50 / 10 requests** |
| Route Matrix | 300 / 60 elements | **1,000 / 150 elements** |

Keep unused methods at zero/day and per-user quotas unchanged. Two searches × four activities × ten outings = 80 searches/day, leaving modest headroom. Twelve details × ten outings = 120/day. Three adjacent 5 × 5 matrices = **75 elements/outing**, or 750 across ten outings. Matrix results must be reused across candidate combinations; 1,000/day is a ceiling, not a target. Ordinary route calls remain selective.

Proposed application ceilings, also **NOT applied**: searches 4 → **8/outing**; candidates 3 → **5/activity**; matrix 27 → **75 elements/outing**; all attempts 20 → **30/outing**; session attempts 50 → **250**; session elements 300 → **1,000**. Keep concurrency **1**, retries **0**, duplicate prevention, error counting and live lock unchanged. A session means one process; restarting still resets it.

These maxima are not calibrated to make every possible daily workload free. For example, 1,000 matrix elements/day over 30 days is 30,000 elements: Essentials' 10,000 free allowance would leave 20,000 × $0.005 = **$100** in usage cost at current list rates, before trial credit, excluding other APIs. Pro/Enterprise features can cost more. Prefer a reviewed set of active test days and least-cost required fields/features; review the credit and gross usage reports between sessions. Do not consume trial credit merely because it is available. A $50 alert cannot stop this workload at $50.

### Credential recommendation and existing application controls

The current Mac has no verified stable public outbound IP; future hosting is unselected. Billing signup does not solve that restriction. No IP was invented, no unrestricted key created, and no credential test or live Maps request was made.

Google now recommends **OAuth 2.0 over API keys for supported server-side services**. Both APIs support OAuth; Routes client libraries support Application Default Credentials. A safe future option is a dedicated minimally privileged service account with short-lived tokens: an attached identity on a suitable Google-hosted backend or workload identity federation elsewhere, and approved service-account impersonation for local development. Use narrow supported Places scopes, verify the exact Routes scope and IAM restrictions separately, and prove minimum necessary access before creating an identity. Use the correct project for billing/quota. Do not use the owner's broad ADC identity or download a service-account JSON private key as a shortcut. No service account, IAM grant, OAuth setup, SDK or hosting service was added in this continuation. [Server security guidance](https://developers.google.com/maps/api-security-best-practices), [Places authorization scopes](https://developers.google.com/maps/documentation/places/web-service/reference/rpc/google.maps.places.v1), [Routes RPC reference](https://developers.google.com/maps/documentation/routes/reference/rpc/google.maps.routing.v2), [Routes ADC support](https://developers.google.com/maps/documentation/routes/client-libraries).

If API keys are chosen instead, create separate Places-only and Routes-only backend credentials restricted to verified public egress IPs, with separate dev/production usage and an approved secret store outside the source tree. Do not provision a static-IP service or broaden IP ranges as an incidental step. Secure local OAuth/impersonation can be evaluated before hosting, so a paid hosting selection is not inherently required; the unresolved choice is the authorized credential/identity strategy. No credential values belong in Git, logs, frontend components, public environment variables or browser bundles.

Application source, environment examples, dependency manifests, mock planner/data and provider limits are unchanged from commit `9192f23`. The existing ten focused budget/isolation tests passed again. Live mode is still rejected and `require_live_provider()` always refuses. Full frontend/backend regressions, real-model smoke tests and local browser/visual checks were not rerun for this cloud/documentation-only continuation.


### Earlier continuation status — superseded by authentication setup

**Implemented/verified:** Free Trial linkage/status/observed balance and expiry; saved approved $50 account-wide gross actual-cost email alerts; all 17 earlier quota reductions; existing local budget tests and live lock. **Proposed only:** quota/application-limit increases and future credential/identity strategy. **Deferred:** API keys/OAuth/service accounts, because a stable-IP key strategy or a separately reviewed minimal OAuth identity/permissions setup has not been established. **Task 39 remains partial on credentials**, with no budget-authorization blocker left. No paid upgrade or live usage is authorized; Task 40 has not started.

To continue credential setup, choose and authorize either a verified suitable public-egress/IP-restricted key arrangement with approved secret storage, or a concrete minimal service-account/OAuth impersonation plan for local development. Any required IAM grants must be reviewed before creating access; no broad owner credentials or unrestricted temporary key. Hosting is not required merely to research/prepare the local OAuth option. Approval of proposed limits does not authorize live calls, and current Console adjustability must be rechecked without upgrading the billing account.


## October 23 authentication completion — Task 39 complete

### Chosen authentication and verified permissions

Use **local Application Default Credentials (ADC) with service-account impersonation** for the trusted Python backend. Both APIs explicitly support OAuth 2.0. The interactive official setup pages expose the full instructions after **3. Make your first request → OAuth token**; the initial static page omits these details. Routes requires `https://www.googleapis.com/auth/cloud-platform`; Places accepts it too. Places also supports narrower `maps-platform.places.textsearch`, `.nearbysearch` and `.details` scopes for separate future Places token requests. No narrower standard Routes scope was verified; do not substitute the unrelated Routes Preferred scope. [Routes setup](https://developers.google.com/maps/documentation/routes/get-api-key?setupProd=configure), [Places setup](https://developers.google.com/maps/documentation/places/web-service/get-api-key?setupProd=configure), [Places method scopes](https://developers.google.com/maps/documentation/places/web-service/reference/rpc/google.maps.places.v1).

Configured and independently read back:

- Service account: `whereto-local-maps@where-to-512422.iam.gserviceaccount.com`.
- Runtime project role: `projects/where-to-512422/roles/wheretoMapsConsumer`, containing **only `serviceusage.services.use`**. This is the permission required to consume the project's quota/billing. A one-permission custom role avoids the monitoring/service-inspection permissions bundled into Service Usage Consumer. No runtime Owner, Editor, resource-management, IAM-management, billing-management or quota-editing role was granted. [Quota-project permission and custom roles](https://docs.cloud.google.com/docs/quotas/set-quota-project).
- The signed-in owner has `roles/iam.serviceAccountTokenCreator` **on this service account only**. The role includes `iam.serviceAccounts.getAccessToken` and token/signing permissions; no project-wide Token Creator grant or service-account self-impersonation grant was added. Administrator setup uses the owner's existing project Owner role, not a new grant. [Local Python impersonation](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment), [token creation](https://docs.cloud.google.com/iam/docs/create-short-lived-credentials-direct).
- Enabled `iam.googleapis.com` and `iamcredentials.googleapis.com` for documented identity administration/impersonation. These are authentication services, not venue/routing integrations. IAM API use is free; no hosting or additional paid service was provisioned. [IAM pricing](https://cloud.google.com/iam/pricing).

OAuth scopes and IAM grants serve different purposes. The shared `cloud-platform` scope is broad; the dedicated account's minimal IAM role limits its permissions. **This is not an API-key-style allowlist for only two APIs**: `serviceusage.services.use` allows project API consumption, and any later added IAM roles could expand access. Do not add resource roles or enable further provider services incidentally. Future Places adapters should use the narrower supported Places scopes where practical. No claim is made that OAuth tokens alone enforce the application's request limits.

Direct owner-user ADC would expose the owner's authority to the application and was not selected as its target identity. IP-restricted API keys remain an alternative when a suitable public egress IP is verified; the current Mac has no established stable address. Impersonation works without inventing an IP, downloading a private key or choosing paid hosting. Attached service identity/federation remains a future deployment choice.

Administrator setup required the existing owner's `serviceusage.services.enable`, `iam.roles.create`, `iam.serviceAccounts.create`, `resourcemanager.projects.setIamPolicy` and `iam.serviceAccounts.setIamPolicy` permissions. Those setup permissions were not granted to the runtime identity. Runtime token refresh needs the source owner's `iam.serviceAccounts.getAccessToken` permission on the target; project consumption uses the target's `serviceusage.services.use`. Read-only quota inspection used the administrator, not the runtime identity.

### Local credential storage and safe checks

Installed Google Cloud CLI **590.0.0** using Google's documented Homebrew cask. Homebrew installed its Python 3.13/runtime dependencies and updated required certificate/OpenSSL packages; the application's existing Python virtual environment and dependency files were unchanged. The owner personally completed the CLI login and ADC browser approvals.

Local ADC is at `~/.config/gcloud/application_default_credentials.json`, outside the repository, verified as `impersonated_service_account` targeting only the account above, with file mode **0600**. **A sensitive, reusable user OAuth refresh credential exists inside this ADC file**, and the CLI has its own local login store. Short-lived access tokens do not make those source credentials short-lived or harmless: anyone who steals the source refresh credential could exercise the source user's permitted access. Keep this trusted Mac and credential file protected; never copy it into source, frontend, logs, Git or documentation. No API key, service-account JSON private key, app OAuth client or token file was created.

Google's bundled Python authentication library successfully discovered ADC, selected the expected impersonated identity and refreshed it into a valid token with **less than 60 minutes remaining**. The verification transport allowed only `oauth2.googleapis.com` and `iamcredentials.googleapis.com`; tokens remained in memory and were neither printed nor explicitly saved. This proves the identity/token flow, **not successful Places/Routes authorization or responses**, which were intentionally not tested. No Google client/library was added to the FastAPI application and no live adapter was implemented.

Quota attribution was verified with Google's supported Python setting `GOOGLE_CLOUD_QUOTA_PROJECT=where-to-512422`; the service account also belongs to this same project. When a future approved adapter is introduced, set this in that backend Terminal (or pass the quota project explicitly in the authentication library):

```sh
cd /Users/rahularutla/Documents/whereto
export GOOGLE_CLOUD_PROJECT=where-to-512422
export GOOGLE_CLOUD_QUOTA_PROJECT=where-to-512422
```

These non-secret variables were set for the isolated verification process, not written into application configuration or the owner's shell profile. Current mock startup needs no authentication action. If local ADC later needs reauthorization, the tested Google command is:

```sh
gcloud auth application-default login --impersonate-service-account=whereto-local-maps@where-to-512422.iam.gserviceaccount.com --project=where-to-512422 --scopes=https://www.googleapis.com/auth/cloud-platform
```

Complete Google's browser approval personally with the project owner's account. Do not add an optional positional account argument: that combination failed in this installed CLI because the impersonation source flow does not return the ID token its account-validation path expects. Retrying without that argument succeeded. The CLI's `application-default set-quota-project` command rejected impersonated ADC as non-user credentials; no hand-edit or insecure workaround was used. The environment/programmatic method above is separately documented and verified. [Supported quota attribution](https://docs.cloud.google.com/docs/quotas/set-quota-project).

### Quotas, billing and final verification

All **36 Places/Routes quota values** were compared before and after identity setup through read-only Service Usage administration; they are identical, including all **17 prior reductions** and unchanged per-user values. Missing protobuf numeric values represent zero for the seven disabled daily methods. No quota or application ceiling changed and no quota increase/edit was submitted.

Console still shows **Adjustable: No** with disabled row checkboxes for Places. Read-only Cloud Quotas metadata for all 36 quotas separately reports **`isFixed=false` and `quotaIncreaseEligibility.isEligible=true`**. Therefore these are not established to be permanently fixed provider limits; the precise reason for the Console discrepancy remains unconfirmed. The current administrator has project Owner access, and no new IAM role was added to overcome the display. Google's **Free Trial policy expressly prohibits quota-increase requests**. Metadata eligibility is not an approval or an exception to that rule. Proposed increases remain unapplied and must not be attempted as a bypass. Any future change requires owner approval, a billing account legitimately eligible under Google's rules and, where required, provider quota review/support. A paid upgrade is not authorized or needed to complete Task 39. [Trial restrictions](https://docs.cloud.google.com/free/docs/free-cloud-features#during-free-trial), [quota metadata](https://docs.cloud.google.com/docs/quotas/reference/rest/v1/projects.locations.services.quotaInfos), [quota permissions/review](https://docs.cloud.google.com/docs/quotas/view-manage).

The live Console again confirms Free Trial **$300.00 remaining**, **90 days remaining**, and the welcome page's observed expiry **January 21, 2027**; no paid upgrade. Project billing linkage was independently confirmed through Cloud Billing administration. The existing **Where To development $50 monthly account-wide budget** was listed and reopened: actual thresholds **50/90/100% ($25/$45/$50)**, both savings/credit categories unchecked, billing-admin/user email alerts checked. No settings changed and email delivery was not tested. An optional budget-API read was blocked with `SERVICE_DISABLED`; it was not enabled because Console verification sufficed. Alerts remain notifications, not spending caps.

Final API/inventory checks: Places and Routes enabled; Maps JavaScript disabled; **API key inventory empty**; service account has **zero user-managed keys**. Read-back confirms its sole runtime role and sole explicit impersonation binding. All **10 focused provider-budget/mock-isolation tests passed**. Application code, configuration, dependencies, fixtures and fictional-data planner are unchanged; the live guard remains unconditional. Full backend/frontend suites, lint, TypeScript, build, actual-model tests and planner browser checks were not rerun for this Cloud/local-authentication/documentation-only continuation. Initial system-Python administration checks hit a certificate-store error; Homebrew Python with trusted certificates succeeded without disabling TLS verification.

**Task 39 is complete**: billing alerts, existing conservative quotas, application guards and a verified keyless local credential arrangement are established. This does **not** authorize or begin Task 40, live Google requests, quota/application-limit increases, paid-account upgrade or deployment. Any live integration still requires explicit owner approval, bounded field masks/features, correct quota attribution and mandatory use of the existing guard/budget boundaries. Keep using the fictional planner normally; no further owner login action is currently pending.

## October 23 Task 40 — authorized discovery verification

The owner's Task 40 instruction separately authorized at most two live Text Search attempts after offline tests. **Exactly two occurred**, including failures: first HTTP 400 (invalid 360-degree rectangle bias), then HTTP 200 after correcting the rectangle to the method's 180-degree maximum, returning three geographically verified Baltimore bowling candidates. Existing local impersonated ADC worked for actual Places access. No automatic retry, pagination, Details/Nearby/Routes call, expensive optional field, quota increase, new identity/key or paid upgrade. No Places quota/billing error. The originally planned coordinate live search was not sent; coordinates/radius are offline-tested only. The allowance is exhausted.

The six explicit mask fields and their individually verified tiers, Pro request estimate, safe command, policy/privacy boundaries and complete verification ledger are documented in [venue discovery](venue-discovery.md). Two successful Pro requests would be $0.064 at first-tier list rates before allowances/credits; this is an estimate, not observed charges, and one actual attempt was rejected. Exact posted usage/billing was not measured.

Before testing, read-only administration confirmed Places/Routes activation and all 36 unchanged quota values, including 17 earlier reductions. Console reverified Free Trial ($300/90 days shown), the saved $50 account-wide monthly alerts-only budget, actual $25/$45/$50 thresholds, both credit categories excluded and billing-admin/user email checked. An optional Cloud Billing administration API call returned HTTP 403 `SERVICE_DISABLED`; no administration API was enabled, and Console supplied verification. This was separate from Places and did not block successful Places authentication. Email delivery remains untested.

The generic `VENUE_DATA_MODE`/Routes gate stays locked; Task 40's isolated backend `WHERETO_PLACES_DEV=1` discovery exception does not activate the website or planner. Development switches were scoped to verification processes, removed in `finally`, and disabled behavior rechecked. Every adapter search reserves the existing budget before authentication/I/O, retaining failures and preventing duplicates, with unchanged session/search/candidate/concurrency limits and no automatic retries. Counters still reset on process restart. Future testing needs separate live authorization and usage review; billing alerts remain notifications, not a hard cap.

## October 24 Task 43 — offline route calculator

Task 43 implements the isolated backend calculator described in [route-calculator.md](route-calculator.md). Basic DRIVE/TRAFFIC_UNAWARE or WALK matrices use only `originIndex,destinationIndex,status,condition,distanceMeters,duration`: **Compute Route Matrix Essentials**, no traffic, tolls or premium feature. Current global first-tier rate is $5/1,000 elements with 10,000 free monthly elements; 27 elements is $0.135 at list rate before allowances/credits, not measured charges. [Official pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [SKU triggers](https://developers.google.com/maps/billing-and-pricing/sku-details#compute-route-matrix-essentials).

Whole-plan admission counts the exact origins × destinations products and checks remaining outing/session/request/concurrency budgets before authentication/I/O. Unchanged 27 elements/outing, 300 elements/session, 20 requests/outing, 50/session, 3 candidates/activity, concurrency 1 and retries 0. Added local rolling-minute check mirrors the existing 60-elements/minute project quota; cloud 300/day and 60/minute quotas remain unchanged and authoritative. Prior usage in other processes cannot be inferred offline. Rejected batches reserve nothing; accepted planned batches retain all reservations even if a provider failure leaves later matrices unsent. Counts are conservative local admission totals, not billing receipts. No splitting to evade caps, automatic waiting/retries, candidate expansion or per-itinerary API calls.

Separate `WHERETO_ROUTES_DEV=1` gate is checked in calculator and transport before authentication and remains absent by default; it is only for a separately authorized future local live verification. Generic `VENUE_DATA_MODE` remains mock-only, and Places' development gate grants no routing access. No live Places/Routes requests, token refreshes, quota/billing/IAM/credential changes, new keys or dependencies occurred for Task 43. Existing ADC is reused by code only. Full backend verification blocked external connections and recorded zero attempts; new route tests also forbid sockets and mock provider/authentication. Cloud usage/balance/quotas were not rechecked in this offline session. Saved budget alerts remain notifications, and the trial remains subject to available credit/expiry. A future controlled live check needs separate authorization and prior read-only safeguard/usage review.

## October 24 — updated spending policy and authorized Routes verification

The owner sets an approximately **$40–$50/month development API planning target** and accepts reasonable, controlled spending for authorized development/tests. This is not a blanket zero-spend policy or authorization for uncontrolled requests. Continue within an already authorized request/element allowance without repeated approval for trivial costs; monitor usage and estimated versus posted costs, retain existing alerts/quotas/request/concurrency/retry limits, batch efficiently and cache only when provider terms permit. Avoid unnecessary premium fields/features. Major quota increases, substantial recurring costs and billing-plan changes require separate approval. Preserve Free Trial without an explicitly approved upgrade. No actual limit/alert/billing change follows automatically from this target.

Updated Task 43 authorization permitted **ONE Routes driving matrix request, up to FOUR elements**, including self-pairs. Actual result: **one request/four returned elements, HTTP 200**, both meaningful directions successful with positive metrics, self-pairs zero, zero Places calls and zero retries/additional routing requests. Existing local keyless impersonation succeeded; ADC file unchanged. Both development switches absent and route-disabled guard passed afterward. Allowance exhausted. [Complete privacy-safe verification ledger](route-calculator.md#authorized-live-verification--october-24-2026).

Local settings/credential metadata and existing previously verified records were reviewed; prior Free Trial/expiry ($300 original, January 21, 2027), $50 account-wide alerts ($25/$45/$50), cloud matrix 300/day and 60/minute, and application ceilings were not modified. Current credit balance, aggregate usage and posted charges were not independently refreshed. Four elements at the documented Essentials first paid-tier rate estimate **$0.02 before allowances/trial credit**, not measured charges. Test-only limits lowered the single process/outing to one request/four elements; no permanent limit, billing, quota, IAM, key or credential edit. No raw provider content or numerical routing metrics retained in Git. No Task 44 work.


## October 24 Task 45 — offline evidence labeling

Pure source/verification adapters and synthetic tests only: zero live Places/Routes calls, token refreshes or Cloud administration. Existing field masks/tiers, billing settings/alerts, quotas, application budgets, credentials and disabled-default gates are unchanged. No Details/Enterprise request, extra route lookup, persistent cache or dependency was added. Official policy pages were read as documentation. Cloud posted costs/credit balance were not rechecked. The approximately $40–$50/month planning target remains unchanged. Task 46 integration is deferred; see [evidence labeling](evidence-labeling.md).


## Task 46 — October 25, 2026 local planner safeguards

The owner authorized bounded end-to-end verification (four Text Search requests/27 matrix elements maximum, no retries or Details). Existing project APIs/quota limits were freshly read through Cloud administration: SearchText 20/day and 10/minute; GetPlace 40/day and 10/minute; matrix 300 elements/day and 60/minute. No changes were submitted. Existing runtime ADC's impersonated type, exact target and restrictive permissions were checked without exposing credential content.

Cloud Console still showed the Free Trial ($300 credit/88 days at the pre-test inspection), $0.00 recorded spend against the saved $50 monthly account-wide budget, and 50%/90%/100% alerts. Those displayed figures can lag usage and do not prove zero accrued charges. The read-only Budget API returned 403 to the existing CLI identity; the saved settings were verified in Console instead, without broadening IAM or changing the budget/account.

Real planner access requires two deliberate local backend switches and refuses production/known hosting environments. All existing request/candidate/matrix/session/concurrency/retry ceilings remain. On-demand contacts have a separate disabled-default switch and a six-attempt sublimit inside existing budgets. Contact fields trigger Place Details Enterprise: current global first-tier $20/1,000 requests after 1,000 free/month (checked against Google's official pricing October 25). No live Details request is part of Task 46. [Current flow, pricing and final ledger](real-planning.md).

Task 46 final ledger: **4 live Text Search requests, 2 Route Matrix requests / 18 billable elements, 0 Details, 0 retries**, all six provider requests HTTP 200. Estimated first-tier gross usage $0.218 before allowances/credit; no posted-cost claim. Console also confirmed actual-spend alerts at $25/$45/$50, excluded savings/credits, billing-admin/user email notifications enabled, and account-wide scope (project-owner toggle unavailable for that scope). No setting was saved or changed. Live processes stopped and mock restored. [Detailed findings and closed allowance](real-planning.md#bounded-live-verification-ledger--october-25-2026).

## October 26, 2026 — authorized Text Search daily quota adjustment

Manual real-data testing exhausted the project's custom 20/day Text Search allowance. Read-only Cloud Monitoring diagnosis identified `places.googleapis.com/SearchTextRequest`, limit `SearchTextRequestPerDayPerProject`, as the exhausted Google quota; this was not the application's 50-attempt process limit. The owner clarified the conflicting initial targets and explicitly authorized **40/day while preserving the actual current minute limit**.

Using the existing administrator CLI identity and project `where-to-512422`, one Service Usage consumer-override PATCH changed only the existing Text Search daily override from **20 to 40**. The update specified only `overrideValue`, used no force/safety-check override and no mutation retry, and completed successfully. A subsequent read-only operation check and complete before/after comparison of all **36 Places/Routes quota values** verified exactly one change:

| Quota | Before | Verified after |
| --- | --- | --- |
| Places Text Search per project/day | 20 requests | **40 requests** |
| Places Text Search per project/minute | 10 requests | **10 requests** |
| Route Matrix per project/day | 300 elements | **300 elements** |
| Route Matrix per project/minute | 60 elements | **60 elements** |

The request's reference to an existing 20/minute limit was incorrect; fresh administration reads confirmed 10/minute, which was preserved. All other Places/Routes quotas, application request/candidate/element/concurrency/retry limits, and default-disabled real/contact gates remain unchanged. No application source or credentials changed. No backend restart, billable Places/Routes/Details call or availability retry occurred. Increasing a configured allowance does not establish that today's usage has reset or that real planning will now succeed; no provider-data request was made to test availability.

Google accepted this specific update to an existing below-default consumer override (the reported daily default remains 75,000). This supersedes earlier uncertainty about whether this particular edit would be accepted; it is not proof that general Free Trial quota-increase requests are available. No billing-account/plan change, paid upgrade, API enablement, IAM change, budget edit or alert edit was requested. The existing Free Trial and saved $50 budget with $25/$45/$50 alerts were left untouched; current credit balance, posted charges and budget settings were not freshly inspected. Alerts remain notifications, not a hard spending cap, and the approximately $40–$50/month development target remains in force. This quota change grants no additional live-test authorization.

Verification for this administration/documentation-only change: successful operation completion, read-only 36-value quota comparison, full Git diff and whitespace review. Application tests/build/browser checks were not rerun because application files are unchanged. Temporary administration helpers/snapshots remain outside the repository and contain no saved access tokens. Task 47 was not started.
