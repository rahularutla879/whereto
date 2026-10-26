# Task 46 — real-data outings

Current consolidated improvement: October 26, 2026. This section supersedes earlier candidate limits, presentation, manual-lookup and option-browsing checkpoints below. Mock remains default; Task 47 has not started. The implementation pass made no billable requests; the separately authorized [controlled verification](#october-26-controlled-live-verification) below records subsequent live usage and its offline correction.

## Current flow

Homepage → existing local AI / deterministic clarification and overrides → backend-controlled real/mock mode → one Places search per distinct activity → canonical normalization, geographic checks, relevance and ID deduplication → geographic shortlist → necessary directed routes → existing candidate walker, evaluator, Task 44/45 evidence and ranking → diverse, source-labeled cards.

Discovery requests up to **10** results/category with pageSize, no pagination or filler. There are still four searches/outing and 29 categories; repeated activities reuse discovery but preserve ordered distinct visits. The Pro mask adds types and primaryType to the existing identity/address/coordinate/components/attribution fields. Dinner-specific queries exclude affirmative cafe/coffee/bakery-only matches lacking restaurant-type evidence. Missing types do not reject a venue by themselves, and mixed cafe/restaurants remain provisional. The retained dinner warning prevents restaurant classification being represented as confirmed dinner service.

## Routing and recommendations

`routing_shortlist.py` computes forward/backward minimum straight-line path costs across the whole requested sequence. This is a geographic heuristic, never a driving/walking quote; strong relevance is preferred and stable IDs break ties. It is not an exclusively greedy next-stop search and does not claim global optimality. After shortlisting, the existing route calculator and candidate walker/evaluator enforce directed provider travel and all hard constraints. Missing legs stay unverified and unreachable legs reject combinations. Unknown prices cannot satisfy budgets. Dates, overrides, multi-activity identity and repeated-category rules remain.

| Stops | Initial shortlist per position | Initial maximum inter-stop elements / requests* | Expanded shortlist | Maximum cumulative inter-stop elements |
| --- | --- | --- | --- | --- |
| Two | 6 | 36 / 1 | 10 | 100 |
| Three | 4 | 32 / 2 | 8 | 128 |
| Four | 4 | 48 / 3 | 6 | 108 |

*Disjoint groups; deduplication/self-identity can reduce counts, and overlapping groups can split rectangles differently. One authorized origin adds at most 6/4/4 initial or 10/8/6 cumulative elements. The original outing's **150-element** and **20-attempt** ceilings always apply, including expansion and on-demand contacts. Failed/reserved work is not refunded. A shortlist with fewer than three acceptable plans may expand once automatically using new pairs, never by retrying a failed provider request. Other expansion is explicit via Show different options.

The existing score now uses a confidence-weighted rating quality component when evidence exists: `(rating × count + 3.5 × 50) / (count + 50)`, mapped onto 0–1 and averaged over all stops. Missing ratings contribute no invented rating; zero-count ratings are omitted. The 3.5/50 prior is a disclosed ranking heuristic, not provider data. Existing spending-mode weights remain; price remains absent. Ratings never override feasibility. Within the existing 0.15 score tolerance, diversity prefers unused primary venues, then meaningful full-itinerary changes, preserving better evidence/convenience outside that tolerance. Shared stops are allowed; duplicate ordered outings are not.

### Why Pinstripes repeated in Washington

The previous three-candidate discovery ceiling limited the pool before ranking. Actual source inspection confirms provider response order was retained, geographic/relevance filtering could reduce the pool, travel determined the real score when quality/prices were missing, and `_select` compared total changed stop IDs without prioritizing the primary venue. Thus changing restaurants could retain the same bowling venue. An offline fixture regression demonstrates that competitive alternatives now produce different primary IDs. **The original Washington candidate responses, excluded IDs and route evidence were not retained**, so we cannot establish whether that particular repetition was caused by provider coverage, truncation, exclusions, travel or their combination. There is no Pinstripes-specific rule. No live request was made to reconstruct the test, and no exhaustive city-coverage claim is made.

## Show different options

The first response includes at most two checked batches beyond the first three. Consuming them makes no provider call. When those are used, `/api/plans/options` receives an unguessable capability, reuses original constraints, the same OutingBudget, discovered facts and existing directional evidence, and excludes every previously returned combination. It prefers unused primary venues within the quality tolerance. It exhausts evaluated coverage before expanding the shortlist once, with only previously unrequested pairs. No additional Places search, random reshuffle, budget reset, pagination or automatic retry occurs. Provider/budget failure stops further expansion; existing cards remain and a useful explanation is displayed. “No more” refers only to checked search coverage, never all businesses in a city.

Continuation state is bounded to 20 entries, expires automatically after ten minutes, and has a per-entry lock. It is active computation memory, not a persistent/cross-outing Google content cache. It includes the confirmed origin when supplied; privacy text discloses this limited retention. Contact capabilities reuse the original outing budget and original IDs. The browser holds contact promises only in the active page, coalescing duplicate openings. No localStorage, database or raw-response log is added. Applicable [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies) and [Routes policies](https://developers.google.com/maps/documentation/routes/policies) still apply; a future persistence/deployment design needs its own review.

## Ratings, contacts and manual starting places

All provider requests remain backend-only, with existing local impersonated ADC, zero retries and production refusal. Base real mode requires VENUE_DATA_MODE=real, WHERETO_REAL_DEV=1 and a development environment. Optional switches default off:

| Switch | Effect | Tier / bounded usage |
| --- | --- | --- |
| WHERETO_RATINGS_DEV=1 | Adds only places.rating and places.userRatingCount to each activity search | Text Search Enterprise; no separate enrichment requests |
| WHERETO_CONTACT_DETAILS_DEV=1 | View details retrieves phone/website on demand | Existing Place Details Enterprise mask; six attempts/outing, inside shared limits |
| WHERETO_START_LOOKUP_DEV=1 | Explicit Find starting place calls `/api/starting-places` | Text Search Pro, three matches, ten lookup attempts/process, shared 50 attempts/process and 10 search attempts/minute |

Rating fields are cheaper in the existing searches than separate shortlisted-venue Details calls: two activity searches cost $0.070 enriched versus $0.064 + six × $0.020 = $0.184 for Pro searches plus six separate Enterprise lookups, before allowances. Contacts are not prefetched. The existing strict phone/HTTPS validation, original Place IDs, Google Maps links/credits and no-booking wording remain.

Manual lookup uses existing **Places Text Search**, which officially supports place/address text and ambiguity, and returns up to three matches for user confirmation. No automatic lookup on typing and no coordinates-entry UI. Types distinguish address/place, ZIP, neighborhood, city and unknown approximate area. A returned address/place point is not a verified entrance; area points are explicitly representative. The user must select Use this representative point before area-based routing; hard first-leg comparisons apply to that point, not the user's actual address. Destination precedence, first-leg direction, near-me radius checks and explicit browser permission remain. Unconfirmed text blocks provider planning rather than inventing coordinates. Addresses/points are not logged or persisted; lookups and failures are coalesced in page memory, and every backend attempt consumes the shared process budget.

Google Geocoding v4 was investigated: it supports backend OAuth (including cloud-platform or narrower geocoding scopes), has an Essentials $0.005/request first paid tier and requires its service to be enabled. [OAuth/setup](https://developers.google.com/maps/documentation/geocoding/get-api-key-v4), [v4 overview](https://developers.google.com/maps/documentation/geocoding/geocoding-v4-overview). This pass enables no Geocoding service, API key, IAM permission or Geocoding quota. Places-based matching is implemented instead. If live verification finds that Places cannot adequately resolve an address/ZIP, dedicated Geocoding enablement and narrowly scoped quotas require separate approval; no fallback silently adds that method.

## Clean presentation and evidence

Unknown optional costs, group totals, capacity, duration, visit times and addresses are omitted from individual real cards. A shared short caveat asks users to check hours/group suitability and says no schedule/booking is confirmed. A hard budget always retains a prominent “cannot verify” warning; movie/event sessions, dinner service, representative origins, unknown routes and known violations remain visible. Future/unrecognized constraint failures are not suppressed. Backend issues and Task 44/45 evidence are unchanged; view details retains available source data/credits and safe links. Full-name/long-name title behavior and mock sample pricing remain. [Field-by-field deferred inventory](deferred-venue-features.md).

## Effective budgets and local operation

Application defaults: candidates 10, matrix 150/outing, 1,500/process, 150/rolling minute; four activity searches, six Details, 20 attempts/outing, 50/process, concurrency one, retries zero. Search and starting-lookup attempts share a 10/rolling-minute guard. Lower validated limits can be supplied through WHERETO_CANDIDATES, WHERETO_MATRIX_OUTING, WHERETO_MATRIX_SESSION and WHERETO_MATRIX_MINUTE; values above the approved maxima fail startup. Process restarts do not reset Cloud daily quotas or billing.

Cloud verified October 26: Text Search **40/day, 10/minute**, Route Matrix **2,000 elements/day, 150/minute**. Exactly the two authorized matrix values changed; all other 34 Places/Routes values are unchanged. Existing GetPlace quotas remain 40/day and 10/minute. No account upgrade, billing/alert/IAM/credential change or billable provider request. See [administration record and costs](billing-safeguards.md#october-26-2026--consolidated-task-46-routing-capacity-and-costs).

Use [README startup/disable commands](../README.md#task-46-real-venues-in-local-development). Real/rating/contact/manual lookup remain deliberately opt-in and are **not live-verified by this pass**. Browser and automated checks use synthetic providers with a fail-on-network guard. Historical live allowances below remain closed.

## Historical verification and superseded stabilization checkpoints

The following sections record earlier behavior and limits; the current consolidated flow above supersedes their three-candidate, 27-element and deferred-manual-lookup statements.

## Verification

Offline automated suites use invented Google responses and fail on unintended network sends. `backend/real_fixture_server.py` is a deliberately launched test-only server; the ordinary app never imports it or enables it through configuration. It replaces AI and provider boundaries, enabling the actual Next.js proxies/client and browser to exercise the complete pipeline without Google. No persistent fixture contains live Google content.

See the final Task 46 checkpoint in HANDOVER.md for exact suites, browser checks and the bounded live ledger. Do not rerun the live verification as an ordinary regression command.


## Bounded live verification ledger — October 25, 2026

| Run | Places Text Search | Route Matrix requests | Billable matrix elements requested | Live Details | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Initial browser outing, bowling → dinner in Baltimore, November 7 | 2 | 1 | 9 | 0 | All HTTP 200; three provisional options |
| Corrected dinner-specific query and mode-aware summary | 2 | 1 | 9 | 0 | All HTTP 200; three provisional options |
| **Total** | **4** | **2** | **18** | **0** | **Within the authorized 4 searches / 27 elements** |

Zero retries, Enterprise search fields, Places Details or other billable Google methods. Each request used the unchanged permitted field masks and existing keyless impersonated ADC. Auth/permission/quota/billing did not cause a runtime failure. Source attribution, original Google venue IDs, actual addresses and positive directional driving estimates reached the browser. Numerical provider metrics/IDs and raw payloads were used transiently and were not copied into committed fixtures or this ledger. At the reviewed first paid tiers, usage corresponds to **$0.218 before free allowances/trial credits**, an estimate rather than a posted charge. Pre-test Console spend was $0.00 and can lag. Billing plan, quotas, alerts, IAM and ADC file were unchanged.

The initial run exposed legacy simulated-travel wording in Your outing; the final browser run verified its correction. A dinner-specific query was also added and offline-tested, but the second live search **still returned a daytime café**. Search wording cannot establish dinner service. The final cards explicitly flag dinner service/hours as unverified; confirmed meal suitability/opening hours require future evidence acquisition. This is a material recommendation-quality limitation, not proof of a feasible dinner booking.

The allowance is now closed. The guarded processes were stopped, local real switches were absent afterward, and the ordinary backend was restarted in mock mode. No further live Task 46 requests are authorized. Contact-success/missing/failure/reopen tests remain mocked; browser geolocation success is mocked, while the browser's actual unavailable/timeout fallback was exercised. Walking is offline-tested only. Broader timezone coverage and real service-hours/prices/session evidence remain future work.


## Post-integration stabilization — October 25, 2026

This is a focused Task 46 follow-up, not Task 47 or a new roadmap item. Zero live Google API calls were made. All existing Cloud/application limits, disabled-default gates, credentials and the prior live ledger above are unchanged.

### Date root cause and correction

The exact prompt “Plan bowling followed by dinner in Baltimore on Saturday, November 7, 2026, for 4 people.” reproduced `date_conflict` through the actual interpretation/clarification service even with correct AI extraction. The deterministic scanner extracted `Saturday` and `November 7, 2026` separately, resolving the first to the next upcoming Saturday rather than treating it as the weekday of the stated date. Manual overrides and frontend follow-up state were not the root cause.

The calendar scanner now recognizes a weekday-qualified named/ISO date as one phrase, validates that its weekday agrees, and ignores redundant AI fragments from that same phrase. Independent dates, mismatched weekdays, invalid days, missing-year/past-date policy and explicit manual priority remain checked. Year-only follow-ups retain qualified date context. The exact prompt now passes both deterministic fixtures through real HTTP/Next proxies and the local Ollama interpretation service without a date question.

### Ranking, shared venues and presentation

Real card titles use the actual ordered venue names. Descriptions explain known estimated inter-stop minutes and venue variety, explicitly stating that unavailable prices/ratings did not determine ranking. The existing score still uses travel convenience when price/quality evidence is absent; tied estimates use diversity and stable ordering, not a hidden venue-quality judgment. First-stop travel is checked separately and does not contribute to this existing inter-stop ranking. No cheapest/highest-rated/open/budget-compliant claim is introduced.

Diversity prefers different whole venue visits, allows shared stops across separate options, and never duplicates a complete ordered itinerary. When only one requested activity has alternatives, useful combinations sharing the fixed stops are retained. This is still a heuristic over provider IDs; it does not prove two businesses offer different experiences. Different options may have the same travel estimate.

Unknown prominent prices now say Price not available and group totals Cost not verified, without a tilde or per-person numeric heading. Hard budgets and their unverified state are retained. Real headers show ordered stop names and existing locally installed Lucide activity symbols in the existing three color themes; they explicitly say illustrations are not venue photos. No new image, photo API, dependency or asset license is introduced.

### Bounded other options

The backend evaluates the same bounded candidate pool once and returns at most six extra eligible options in two batches. The frontend consumes those batches from active-page memory, never resubmitting interpretation, discovery or routing for the action. All options preserve the original request, route/uncertainty evidence and hard constraints. The existing contact capability includes their original Place IDs and retains the same six-contact/overall limits. Edits/new generation clear these options and the contact display session. Regeneration may make a new search; Show different options does not.

The fixture bowling/dinner pool provides nine unique combinations in three pages using the same two synthetic searches/nine matrix elements; a one-combination pool gives no extra button action. Exhaustion is explicit, with no automatic refill or cycling. More genuinely new businesses would require another user-initiated search and potentially more provider budget. The earlier four-candidate/30-element proposals remain proposals only; no increases are needed for this bounded action.

### Manual starting-place resolution: implemented versus deferred

Implemented: ordinary text input for a place/address/neighborhood/ZIP, no latitude/longitude controls, separate destination, explicit geolocation button, clear unavailable/manual fallback messages, transient excluded request field, and a backend refusal before any provider I/O when manual text is unresolved. Text entry never silently becomes a city-center/device position and never silently disables a first-stop cap. Removing the unresolved entry permits destination-only planning when no first-stop requirement remains. No address/coordinate logging or persistence is added.

Deferred: actual text-to-coordinate lookup and confirmation. Google's [Geocoding API](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding) is suited to addresses/ZIPs and reports `location_type` and `partial_match`; an area result must be labeled approximate and explicitly selected as a reference point, not the user's exact location. Named businesses/landmarks could use the existing Places Text Search API, but another request consumes a search slot and needs shared resolution/planning budget accounting plus ambiguity handling. Existing venue discovery must not be reused to pretend a neighborhood is an exact starting address.

Recommended separately approved follow-up: enable/verify Geocoding API only after confirming supported keyless authentication/least privilege; set a proposed 10/day, 5/minute Cloud quota; add at most one explicit resolution attempt per outing within the existing 20/50 total attempts, no retries/autocomplete/pagination; display up to three candidates with provider address/precision and require selection. Require explicit consent to route from an approximate reference point; describe limits as applying from that reference, not verified from the user's position. Do not add a new credential or expand access silently. [Current global pricing](https://developers.google.com/maps/billing-and-pricing/pricing) lists 10,000 monthly free Geocoding events then $5/1,000 ($0.005/request) in the first paid tier; account-wide usage and actual billing may differ. These are documented proposals only: no Cloud API enablement, IAM/authentication/quota change or live method was performed. Manual lookup remains unavailable until that work is authorized and verified.

### Verification

Full backend and frontend suites, lint, TypeScript, production build and dependency consistency passed (exact totals and practical browser checks are in HANDOVER.md). New regressions cover the exact prompt/continuation/manual priority, weekday conflicts, preserved year answers, shared venue pools, unique bounded batches, hard-cap rejection across all alternatives, unknown cost rendering, unresolved manual starts with zero provider calls, and option changes with unchanged request counters. Desktop/mobile browser checks use only the fail-on-network fixture server; successful local Ollama date interpretation is separately verified. No live recommendation-quality/Geocoding/Details verification is claimed for this pass.


### Headline refinement within Task 46 stabilization

`lib/real-headlines.ts` builds titles only from the selected venue records. Two-stop options use “Venue A & Venue B”; three/four-stop options use ordered name highlights, shortening individual names beyond 28 Unicode characters. Ordinary four-stop titles stay within 121 characters. If shortening would give two options the same title, full names are retained instead; same-named businesses can use their supplied addresses to distinguish them. No source names, endorsements or venue facts are invented. Full names remain in the heading tooltip and existing itinerary details.

Eyebrows now read “OPTION 1 · BOWLING + DINNER”, using the actual ordered categories and validated dinner-stop indices. Food is not relabeled dinner without request evidence. The provisional status stays in the separate existing visual badge/result disclosure; it is removed from the eyebrow/headline text. Mock recommendation copy is unchanged. Real headings wrap anywhere when necessary and have a three-line display limit with equal reserved height, preserving card alignment on desktop/mobile. Shortening is presentation only and never changes venue IDs, order, constraints, sources or the available option pool.

Five focused tests cover two-, three-, four-stop and long/colliding/same-named venue titles, ordered/repeated activities, evidence-based dinner labels and absence of invented claims. The full mocked HTTP pipeline also asserts the exact two-stop title and eyebrow. The explicit offline fixture server has a synthetic long-name scenario for browser layout checks; normal startup never enables it. No new asset/dependency/license or Google call is introduced. Exact final test/browser results are in HANDOVER.md; Task 47 remains unstarted.

## October 26 controlled live verification

Baseline commit: `8275184`. Owner-authorized totals: two rating-enabled activity Text Searches, one manual-origin Text Search, two contact Details requests, 36 route elements, no retries/other billable methods. Tested the actual website → local AI → validated planner → existing impersonated Google transports for bowling then dinner in Washington, DC, November 14, 2026, three people. The date, group and order survived without another date question.

Preflight used read-only Cloud administration/Monitoring and protected ADC metadata. Text Search and GetPlace were each 40/day, 10/minute; Matrix was 2,000/day, 150/minute. Monitoring reported 27 Text Search quota deductions and 85 matrix elements across the preceding 72 hours, with no recent minute traffic; it did not expose an authoritative current daily remaining balance/reset timestamp. No quota pagination or administration error occurred. Read-only postflight showed unchanged queried quotas and 72-hour deductions of 30 searches, two Details and 103 matrix elements, corroborating deltas of three/two/18. ADC was the expected impersonated identity, mode 0600. The isolated process began with empty application counters; existing four searches, six Details, 20 attempts/outing, 50/process, concurrency one and zero retries remained. Test-only environment overrides lowered routing to 36 elements/outing and/process, preventing automatic expansion beyond the authorization. No Cloud quota, billing, IAM, credential or enabled-service changes.

A temporary pre-send allowlist delegated to the actual Google transport, counted attempts before sending, rejected duplicate sends/unauthorized methods, and stopped further provider data sends on any non-200. It was not a fixture server. Only counters, HTTP statuses and operation categories were saved outside Git; no response bodies, tokens, coordinates or contact records were saved. Local server access logging was disabled.

| Actual operation | Requests | Matrix elements | Result |
| --- | ---: | ---: | --- |
| Text Search Enterprise, activity discovery | 2 | 0 | HTTP 200 each; rating/count mask, pageSize 10 |
| Text Search Pro, manual public landmark | 1 | 0 | HTTP 200; pageSize 3 |
| Place Details Enterprise, contacts | 2 | 0 | HTTP 200 each; original IDs/minimal existing mask |
| Compute Route Matrix Essentials, directed driving | 1 | 18 | HTTP 200 |
| Automatic retries / other billable methods | 0 | 0 | None |

Gross first paid-tier estimate: `2 × $0.035 + $0.032 + 2 × $0.020 + 18 × $0.005 = $0.232`, before free allowances/trial credits. This is not a posted charge. [Official pricing](https://developers.google.com/maps/billing-and-pricing/pricing) was checked again; billing balance/actual posted cost/alert configuration were not freshly read. No quota, billing, authentication or provider HTTP error occurred; no guard-blocked send occurred. The allowance is closed, including unused elements; do not automatically repeat it.

### Live observations and limits

- Three initial combinations had distinct ordered venue pairs, but only two distinct primary venues. Both cached Show different options batches yielded six more previously unseen pairs, with the provider ledger unchanged. Shared primary venues were allowed; three distinct primary venues were not demonstrated. This is no claim of exhaustive city coverage.
- Searches requested ten results/category and routing sent only 18 elements, below the authorization. The UI did not expose raw or post-filter discovery/shortlist counts, and those counts were not captured before transient backend state was destroyed. **Ten relevant venues per category was not established live.** The deterministic ten-per-category fixture verifies discovery size and six-per-position/36-element initial shortlisting offline. Live routing was bounded and directed; displayed selected legs ranged from 8–17 estimated driving minutes. Unused candidate identities/evidence were not retained.
- Google ratings/counts appeared in expanded plans and contact panels; recommendation text disclosed their role. The existing confidence-weighted scorer consumed these fields. Counterfactual rating influence, sparse-count moderation, exact hard travel rejection and missing data remain covered by offline tests rather than an additional live run.
- Two different original venue IDs were selected explicitly for contact requests. Both returned usable telephone links; one exposed a valid HTTPS official website, while the other displayed Website unavailable. That wording means no usable link surfaced, not that the business has no website. The panel does not distinguish absent from rejected unsafe/non-HTTPS values. A close/reopen reused active-page contact information without another request. Google Maps links/attribution and no-reservation wording remained visible. Link destinations were inspected; safe rel attributes remain covered by automated tests; no phone call, reservation or ticket purchase was made.
- One explicit Washington Monument lookup returned ambiguous public matches with names/addresses, including a similarly named landmark in another city. The Washington match was selected; its address/place precision explicitly required confirming the intended entrance. This is a provider point, not a verified entrance or personal location. The Washington destination remained in the request; selecting an origin invalidated prior cards. **No plan was regenerated with this origin**, avoiding additional first-leg elements. Approximate-area selection/first-leg limits and browser geolocation success/denial remain offline-tested; device permission was not requested in this run.
- Missing cost/capacity/schedule placeholders stayed hidden. Dinner-service warning, shared hours/group-suitability caution, provisional status, source attribution and no-booking wording remained. The real UI was exercised at its 529-pixel browser viewport; subsequent 1280×800 desktop and 390×844 mobile checks verified restored mock mode without horizontal overflow. Real-card desktop/mobile coverage remains from the consolidated offline browser checks; it was not repeated at both widths live.

### Demonstrated bowling defect and offline correction

The live cards labeled a racing arcade as a bowling stop. Its [official Washington venue page](https://f1arcade.com/us/washington-dc) describes simulator racing; the search-context label alone was insufficient bowling evidence. The query previously used only bowling text and no strict provider type. The deterministic relevance fallback also allowed an explicitly named arcade to remain uncertain when no bowling support existed. We did not retain its raw Google types, so cannot attribute Google's particular match to one specific type value.

The small correction requests `includedType=bowling_alley` plus `strictTypeFiltering=true` for bowling only, per [Google's documented filter](https://developers.google.com/maps/documentation/places/web-service/text-search#strictTypeFiltering). The local relevance check rejects affirmative arcade evidence without bowling type/name support. Multi-activity bowling/arcade venues with bowling evidence remain, as do genuinely missing-data provisional candidates; no business-name blacklist, extra request, field tier, quota or other-category change. An invented fixture verifies rejection through discovery, shortlisting and final plans. **This correction was tested offline only; the live cards preceded it.** Broader venue classification and sparse local coverage are still limitations.

After testing, the live process was stopped, all optional/base gates removed from the replacement process, and MOCK DATA verified in the browser. The temporary verification frontend/backend were subsequently stopped. No default/source/profile credential/gate settings were enabled. Verification after the correction: **383 backend tests, 124 frontend tests, ESLint, TypeScript and production build passed**. The initial sandbox-only backend attempt failed on localhost/TypeScript helper permissions; the authorized local rerun passed. No raw Google response fixture or live screenshot was retained. Original roadmap/release tag unchanged; Task 47 not started.
