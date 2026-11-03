# Task 50E consolidated acceptance refinement

Continuation of `227833e`; Task 51 remains unstarted. This report supersedes the earlier traffic-unaware policy. Five functional refinements are implemented; **the Qwen latency acceptance item remains open**. No safe overall inference optimization was retained. Final verification is recorded below.

## Reproduction and interpretation

Actual installed Qwen 3 4B reproduced all six exact owner requests before edits. In request A it retained the college, required coffee and forward order, but omitted both the return endpoint and the 180-minute budget. The source omission guard correctly stopped that incomplete interpretation; the failure was not a cyclic order. In request B the ordered stops survived, but “now” established neither the date nor an actual departure.

Qwen retains the **original verified instructions, nineteen examples, schema, 8,192-token context, 1,024-token output cap, thinking-off, temperature-zero and ten-minute keep-alive policy**. Experimental prompt/schema reductions were rejected for lost destinations, invented constraints or higher tail latency. A golden request test proves the full final inference payload is byte-identical to the original baseline for the rich money/travel example. Only options-observation instrumentation remains. All deterministic source/order/duration/calendar guards still run; no model failure invokes a keyword itinerary fallback. Missing endpoints/durations are handled by the existing structured/source-grounded flow described below, not by an unverified faster extractor.

A bare “be back” is an unresolved endpoint. Even if extraction omits that endpoint, the source validator can ask where it means after validating all other extracted requirements. It does not invent a return location. The existing deterministic explicit-duration normalizer preserves “within 3 hours” as a whole-trip inclusive 180-minute maximum while that question is pending. Only the user's explicit “Return to my starting point” answer creates/accepts that endpoint. A separate address remains unverified under the existing endpoint limitation. Missing outing dates and confirmed origins use existing targeted questions; missing visit lengths leave whole-trip feasibility unverified and remain editable. Sixty college minutes plus thirty coffee minutes leave ninety minutes for every directional travel leg.

## Current traffic evidence and cost

All Driving Matrix bodies use `DRIVE` and `TRAFFIC_AWARE`. Walking stays `WALK` without a routing preference. No `TRAFFIC_AWARE_OPTIMAL`, traffic-model modifier, second verification pass, automatic retry or extra Cartesian cells are introduced. Optimal is excluded to honor the owner-selected TRAFFIC_AWARE policy and avoid its additional route-optimization latency. Omitting departureTime means the provider uses request time, including when the outing date is in the future. Every origin, inter-stop, return and final-destination leg uses this same policy and its exact protobuf duration for hard comparisons. Display rounding never changes enforcement.

The existing minimal response mask adds only `fallbackInfo`. A fallback that does not establish traffic-aware routing yields unknown timing without numeric travel evidence or an automatic retry. This prevents a traffic-unaware fallback from being advertised as traffic-aware. Pair caches remain directional and scoped to the immutable mode/origin/selected identities. Policy labels and observation times gate reuse; current evidence expires after five minutes. Legacy unaware inputs remain decodable for historical contracts but cannot enter a live route cache. Deliberate regeneration can refresh expired routes using retained venue evidence. Exploration with expired evidence asks for regeneration rather than silently displaying stale estimates.

The shared Driving notice is: “Travel times are based on current Google traffic estimates. Actual travel times may change, especially for future outings.” Walking gets route-estimate wording and the existing beta warning. No consumer Google Maps parity is promised: route/entrance selection, request instant and consumer algorithms may differ.

Owner authorization explicitly includes Matrix Pro. First paid global tiers are **$0.010/Driving element** (Pro, 5,000 monthly free events) and **$0.005/Walking element** (Essentials, 10,000 monthly free events). Accounting remains conservative gross list price and does not assume remaining free events or verified Cloud billing. A separate `matrix_pro_element` ledger key preserves existing Essentials history and charges new Driving reservations/dispatch correctly. Both SKUs consume the same shared 150-element minute allowance. Deliberate regeneration after the five-minute freshness window can need fresh Matrix calls for previously checked pairs; existing admission, quotas, daily gross accounting and no-retry protections still apply. This is not an automatic polling or verification pass. No Cloud billing/quota/identity/private profile is changed, and no live Google comparison is performed.

Sources checked November 3, 2026: [Matrix departure, duration and fallback contract](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix), [fallback routing modes](https://developers.google.com/maps/documentation/routes/reference/rest/v2/FallbackInfo), [traffic-aware Pro billing](https://developers.google.com/maps/documentation/routes/usage-and-billing), [global SKU prices](https://developers.google.com/maps/billing-and-pricing/pricing).

## Convenience and exploration

Hard requirements and evidence/timing classification precede convenience. Within eligible checked results the shortest known directional travel comes first. A modest sixty-second convenience band allows all-stop novelty among similarly practical alternatives; existing quality scoring remains intact. Later explicit pages use unseen complete combinations, retaining mandatory destinations and return/final legs. Discovery keeps the bounded nearby frontier, deduplication and selective new pairs. Neither action reruns Qwen; “Show different” performs no Places search. A bounded routing stage can establish missing pairs for already known venues. The app does not claim global optimality or that bounded discovery exhausts Google venues.

Strict/Flexible retain their existing maxima and exact equality rules; Flexible can allow up to its existing twice-preferred travel maximum. Beyond-limit travel requires its separate explicit action. Neither Flexible nor an exception waives the whole-trip budget, independent deadline, reachability, required stop or geography.

## Visit-duration semantics

| Choice | Counted visit bounds | Completion implication |
| --- | --- | --- |
| Exactly N | [N, N] | Fixed counted duration |
| At most N | [0, N] | Inclusive upper bound; zero is not asserted realistic |
| At least N | [N, unknown] | Minimum only; no finite completion proof |
| Strictly under N | [0, N) | Upper boundary excluded |
| Approximate N | [0, unknown] | Soft estimate; no guaranteed maximum |

Unknown visits stay required. Exactly thirty minutes fails a strict under-thirty limit; 29:59.999999999 passes. Zero requires the existing explicit travel-only scope and zero-counted-time acknowledgement, cannot remove shopping, and cannot establish full elapsed feasibility under an independent deadline. Travel-only excludes visit time from the original single budget; separately required elapsed deadlines still count visits. All accepted durations remain in the existing preferences panel and can be edited without restarting, rerunning Qwen or re-fetching compatible venue/route evidence.

## Now and opening hours

“Now” resolves against the verified destination-local date and a fresh aware departure instant, including seconds. It does not freeze the interpretation timestamp or imply a default 10 AM start. A confirmed origin is required so the app cannot imply the user already occupies the first venue. Explicit departure overrides remain editable. Refreshing/regenerating updates the current intent; saved plans describe it as historical and retain no live instant or precise origin.

Applicable current dated hours, observation freshness, venue timezone, special-day precedence and whole visit bounds remain the authority. A known-closed exact arrival is excluded even when dwell is unknown; opening before arrival is allowed, while closing during a mandatory visit fails. Unknown hours/arrival/latest departure remain qualified and never become “confirmed open.” When available hours need bounded visit times, the existing editable dwell controls ask for them. Overnight, 24-hour, DST and missing/stale evidence regressions retain their conservative behavior. No automatic extra Place Details lookup is added.

## Verification and measurements

The controlled installed-model experiment used the same cold dinner request plus two warm rounds of the same ten public/invented outing texts. Each cold sample deliberately unloaded only the installed selected model and checked the inventory first. No downloads, Google sends, code reloads, heavy tests/builds or intentional competing model calls occurred during either measured run. Earlier contaminated/pilot runs are excluded. Original and experimental raw extraction, effective source contracts, token counts, actual options, load/prefill/generation/HTTP times, source hashes and allocation are retained in [the investigation artifact](../backend/evaluation/results-task50e-model-investigation.json).

| Metric | Original verified baseline | Rejected adaptive candidate |
| --- | ---: | ---: |
| Warm samples | 20 | 20 |
| Warm median | 26.080 s | 22.869 s |
| Warm p90 (nearest rank) | 34.112 s | 41.195 s |
| Worst warm call | 36.588 s | 58.789 s |
| Matched cold dinner | 31.050 s | 26.036 s |
| Median warm prompt tokens | 4,752.5 | 3,036 |
| Median warm output tokens | 277.5 | 245 |
| Median warm model load | 0.004 s | 0.008 s |
| Median warm prompt evaluation | 0.500 s | 0.373 s |
| Median warm generation | 25.439 s | 20.815 s |
| Median HTTP overhead beyond provider total | 1.60 ms | 2.50 ms |
| Cold model load / prefill / generation | 1.316 / 18.306 / 11.301 s | 0.795 / 10.782 / 14.360 s |

The adaptive candidate reduced median latency by 12.3%, prompt tokens by 36.1% and output tokens by 11.7%, **but increased p90 by 20.8% and worst latency by 60.7%**. Switching between compact/full prefixes/contexts caused expensive load/prefill calls; two full-prompt calls took 51.206 and 58.789 seconds, close to the unchanged 60-second timeout. This is not an accepted improvement. The final production policy is restored to the baseline; no final speedup is claimed. Generation remains the dominant measured warm bottleneck.

Ollama reported 3,856,589,127 bytes allocated for the baseline 8K context; the rejected 4K path reported 3,175,339,786 bytes and reported 3,800,291,082 bytes when switching to full extraction. These are model allocation observations, **not peak process/system RAM**. The retained baseline has no claimed memory reduction. Installed selected model size is 2,497,293,931 bytes; digest/model/options are in the artifact. Other installed model metadata was inspected, but no alternative was downloaded, compared or selected.

A second projection retaining the original prompt but forbidding empty optional output fields invented Baltimore, a same-mall constraint and clarification for college/coffee. Earlier compact candidates omitted named cities or invented Baltimore. Both are rejected, not shipped. The final byte-identical baseline request test passes. Accuracy takes precedence over speed; latency remains an explicit open acceptance item under the owner's fallback instruction.

| Semantic case | Controlled adaptive experiment | Final retained policy / effective workflow |
| --- | --- | --- |
| Three-hour college/coffee return | 2/2 effective contracts; raw endpoint/cap could still be omitted | Original extraction retained; bounded source duration validation preserves 180, targeted endpoint confirmation required |
| College/coffee now | 2/2 | Required ordered stops retained; fresh verified local calendar/departure supplied by deterministic integration |
| College/coffee tomorrow | 2/2 after rejecting invented-city candidate | Original extraction retained, unknown city remains unknown |
| Grocery/ATM/45-minute return | 2/2 | Grocery + original ATM five + return + inclusive source 45 preserved |
| Ordinary dinner/bowling/Jersey City | Cold + 2 warm passed | Original ordinary interpretation retained |
| Grocery/return without cap | 2/2 effective contracts | No extra stop/cap; Python resolves original tomorrow even if AI omits date_expressions |
| Repeated coffee/museum/coffee/New York | 2/2 | All three occurrences/order and named area retained |
| Zara/Nike same mall | 2/2 | Both brands and containment relation retained |
| Flexible bank/grocery/New York | 2/2 | Flexible order and named area retained |
| Ambiguous college/Penn Station | 2/2 targeted clarification | Original full-prompt extraction/ambiguity response retained, final named endpoint not dropped |

A final actual-Qwen smoke check of all six exact owner requests passed after restoring the original payload: 12.735, 12.349, 14.685, 19.597, 14.288 and 12.496 seconds. These are warm functional observations, not a controlled optimization comparison; no speedup is attributed to unchanged inference. Raw final outcomes are in the same artifact.

These 21 effective experimental outcomes passed source review, but do not erase its raw omissions or latency failure. The final policy is the original accuracy baseline, protected by the golden payload test; the experiment is not used to claim a shipped optimization. `scripts/benchmark50e.py` reproduces the controlled baseline/current measurement with all Google sends blocked. Actual venue/route/hour acceptance uses invented provider fixtures. Live Google cost for this refinement is **$0**.

### Functional and persistence checks

| Check | Result |
| --- | --- |
| Full backend discovery | 929 reported: 893 passed, 36 opt-in skips, 172.556 s |
| Focused final source/timing/inference regressions | 53/53 passed, 0.732 s; all final timing tests also ran in the full suite |
| Frontend tests | 265/265 passed, 116.588 s |
| Authorized hosted PostgreSQL suite | 58/58 passed, 33.601 s |
| TypeScript / ESLint / production build | Passed |
| Python dependency check / top-level npm dependencies | Passed |
| Production npm audit | Zero vulnerabilities |
| Complete npm dependency tree | Pre-existing optional off-platform WASM warnings remain: `@emnapi/core` 1.10.0 vs ^1.11.1 and `@emnapi/wasi-threads` 1.2.1 vs ^1.2.2 beneath Tailwind's optional WASI package; no dependency change |

A first concurrent frontend run had one fixture-startup timeout; the complete serial rerun passed. Earlier Qwen runs that competed with development reload preparation/builds were excluded, not presented as matched performance evidence. Final secret/diff review is recorded at the delivery checkpoint below.

Hosted checks used the existing authorized restricted identity, verified TLS, forced RLS and disposable records. Version 1 and legacy/defaulted version 2 remain supported. Advanced saved provenance retains original/effective constraints, selected stop identities, explicit overrides, return ending and optional historical routing policy. Reopening in a separate process passed. No migration or owner record was changed. The browser's one selected-option-two test record was verified by its exact capability hash, source, ordered college/cafe identities, 180-minute cap and 60/30 overrides, then deleted by that exact hash; committed absence was verified. Private capability values are excluded from this report.

### Actual rendered browser acceptance

Tests used a production build at isolated localhost ports, invented Google-shaped Places/Matrix/contact/hour responses and **all actual Google sends blocked**. Qwen extraction replayed previously captured actual local-model outputs; the separate model benchmark calls the installed model directly. Desktop was 1280 px and mobile 390 px; rendered scroll widths equaled their viewports. These are simulated venue/route results, not claims about real opening hours, real travel or bookable visits.

| Journey | Rendered outcome |
| --- | --- |
| Ordinary dinner/bowling tomorrow in Jersey City | Three ordinary options, correct area/date, compact View plan/contact details, underlined links and no duplicate venue/contact blocks |
| College → coffee → be back within three hours | Targeted endpoint confirmation, explicit date/origin, college first, required coffee and return retained; invented six-minute travel plus explicit 60/30 visits produced 96-minute options under the 180-minute cap |
| College → coffee now | Verified local today and fresh departure, confirmed origin, duration questions for applicable hours; 10/15-minute visits gave a 29-minute invented outing with qualified clock projections |
| Known-closed mandatory college now | Zero cards and explicit required-stop hours message; no substitution or claim of being open |
| College → coffee tomorrow | Shortest checked options 3/4/5 travel minutes; next unseen options 6/7/8 minutes; all retained college first |
| Show different / discover nearby | No extra model call; Show different used no Places; bounded discovery added one new Places page in the observed named journey; Previous/Next retained the displayed pages |
| Grocery + ATM five minutes + return within 45 minutes | Nearby-origin consent/date preserved; grocery 20 meant 31-minute invented elapsed outing, then 10 meant 21 minutes; ATM five minutes/return/source cap remained |
| Compatible grocery 20 → 10 edit | Stale cards cleared immediately. Before/after fixture counters identical: 13 searches, 81 Matrix elements, 3 Details, 5 interpretation replays; **zero additional model/provider calls** |
| Explicit travel-only scope | Same required stops/ATM/return; all three legs consumed the 45-minute travel-only cap, visits excluded; effective summary explicitly said so. Immediate compatible edits reused evidence. One edit after five-minute expiry refreshed 24 route elements, with no extra model or Places search |
| All five duration meanings | Fixed/upper/lower/strict-upper/soft bounds retained through regeneration; minimum/approximate did not claim a finite total |
| Explicit zero counted time | No cards before acknowledgement; after explicit travel-only + acknowledgement, grocery remained with “actual visit duration is not established,” ATM stayed five minutes and travel remained six invented minutes |
| Forced advanced-session expiry | Edited 20 → 10 without retyping/restarting; result 21 minutes with original requirements. Expired-session refresh added 2 Places searches and 24 route elements, **zero model calls**; pending edit survived |
| Walking mode | Walking label/disclosure, three ten-minute walking legs, no traffic-aware-walking claim; model replay count unchanged |
| Grocery/return without a whole-trip cap | Required grocery and return retained; visit duration remained unspecified, no ATM invented |
| Flexible plus long routes | Three 60-minute driving legs plus 60/30 visits = 270 minutes; zero compliant cards under the 180-minute whole-outing cap, even when first-stop Flexible preference allowed the leg |
| Save selected advanced option / new-tab reopen | Only original option two reopened, with matching selected identities, source and explicit constraints; historical route wording; mobile no overflow; exact disposable cleanup completed |

Ordinary and advanced views still use the original shared `PlanCard`, artwork, typography, three-card layout, action placement, Save selection and contact-only expansion from `227833e`. No Select itinerary button, duplicated name/address/rating/hours/contact notice or advanced-only shell was introduced. Meaningful warnings, source links and Google/third-party credits remain. No extra contact/hours lookup was added. On-demand authorization, private selected-only links/30-day expiry, ordinary score math, original order/retail/optional stop/deadline/date/security contracts and the two-command development lifecycle remain covered by the existing regression suites.

Screenshots were inspected at both widths: desktop shared cards, mobile advanced card, mobile duration preferences and mobile selected saved card. Temporary browser tabs/isolated servers are closed after acceptance; owner development services remain running.

### Structured-edit measurements

Forty sequential offline session actions over invented compatible directional evidence: grocery-duration changes (20 samples) median **1.618 ms**, p90 **2.285 ms**, worst **2.847 ms**; scope changes (20 samples) median **1.583 ms**, p90 **3.012 ms**, worst **4.013 ms**. These measure the local evaluator, not browser or live-provider latency. Both required stops, ATM five minutes, return and source 45-minute cap were asserted on every action. Additional model/Places/Matrix calls: **zero**. Reproduce with `backend/.venv/bin/python scripts/benchmark50e_edits.py --output /tmp/50e-edits.json`.

Actual production-build browser timing measured from keyboard Regenerate submission to the updated card becoming visible. Four duration edits took **131, 126, 127, 127 ms** (median 127); four scope edits took **524, 117, 120, 118 ms** (median 119). This includes UI/proxy/backend time, excludes manual typing and uses invented cached provider responses. Fixture counters stayed exactly 3 searches, 24 Matrix elements, zero Details and one interpretation replay throughout; there were no additional calls. This does not predict real Qwen/Google end-to-end latency. Raw samples/method are in [the structured-edit measurements](../backend/evaluation/results-task50e-edits.json).

### Delivery status and remaining limitation

This pass does **not** declare all six consolidated improvements complete. Traffic-aware routing/accounting, three-hour return handling, shortest-first exploration, the five duration meanings and now/current-hours behavior are implemented and verified. Accepted grocery-duration editing remains working, including expiry recovery. The Qwen latency item remains open because candidate changes either lost source-grounded facts or worsened tail latency; the previous correct inference policy is preserved. No new model download, provider, private profile, billing/quota, deployment or roadmap task was used to work around that limitation. Consumer Google Maps parity and live Google latency/coverage remain unverified.

Current source, tests, new benchmark scripts and all measurement records were reviewed; the credential scan found zero configured private-value matches in current files/assets and Git history. The existing optional WASM dependency-tree warning is the only dependency check exception. Repository privacy and the original release tag are preserved; Task 51 remains unstarted.
