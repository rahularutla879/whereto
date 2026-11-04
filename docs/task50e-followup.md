Current November 3 consolidated acceptance supersedes the historical traffic-unaware policy and earlier verification below. Driving now uses explicitly approved TRAFFIC_AWARE/Pro. [Current implementation, matched measurements and rendered checks](task50e-consolidated.md). Task 51 remains unstarted.

# Task 50E follow-up acceptance repair

Baseline: `6153e1b`. This continues Task 50E. Task 51 is unstarted. No deployment,
Cloud quota, billing, authentication, model setting or database schema change.

## Presentation and duration answers

The existing ordinary `PlanCard` remains the baseline. Remove the illustration
caption, retain artwork and required Google/third-party attribution. Routine unknown
hours no longer create a prominent per-card warning. Unknown whole-trip/deadline
feasibility still gets a short material qualification; explicit travel exceptions
and known closures remain visible and blocking where appropriate.

Advanced View plan shows ordered venues, actual supplied duration, one concise hours
section per venue, ratings when supplied, safe venue/leg links, final/return legs,
route total and applicable whole-trip/deadline comparison. Omit missing-duration
paragraphs, raw hours-state labels, observation timestamps, raw requirement flags,
technical timing reasons and timezone identifiers. Clock projections preserve the
provider's destination-local offset instead of converting to the browser's timezone.
One compact timing explanation is available when relevant. Ordinary details retain
their original content. Shared disclosure carries general limitations.

The shared detail-link selector visibly underlines advanced venue/directions links,
with hover, visited and keyboard focus styles and mobile wrapping. Google attribution
is retained separately as required attribution, not an invented directions link.
No private-origin coordinates or Place IDs enter public directions URLs.

Dwell answers label **Duration (minutes)**, show example20, accept integer0–10080,
and default explicitly to **Exactly this long**. At most/at least/strictly under/
approximate remain separate choices. Approximate has no guaranteed maximum.
The original occurrence and supplied ATM duration/deadline are never replaced;
timing answers reuse existing model/discovery/route evidence.

## Nearby start: reproduced cause and correction

Running the baseline with the exact grocery-return text and a confirmed device
origin produced destination → nearby consent → another date question with zero
searches. Repeating nearby consent then raised `ValueError: Change the destination
through explicit regeneration.` The public endpoint collapsed that validation error
and true expiry into the same generic invalid/expired message. This is reproduced
behavior, not proof of the owner's exact historical payload.

Nearby consent now binds the original authorized origin to a separate coordinate
search area and is idempotent for that origin. A server-verified prior manual lookup
can establish the public locality/calendar. Otherwise coordinate-biased discovery
uses the existing Places adapter, then consistent verified public venue timezone/
address evidence can resolve the relative date. GPS/browser timezone alone never
asserts a city/calendar. Unknown calendar evidence still asks for an exact date and
retains the coordinate search and successful discoveries without repeating them.
A representative ZIP/city or inaccurate GPS point remains visibly approximate.

An explicit destination/hard geographic restriction cannot be replaced with origin
geography. Excluded regions remain enforced. Origin edits require regeneration;
accepted near-origin choice stays visible in canonical Location state. Date/location
edits cancel stale client responses. Actual expiry has its own safe code and one
regeneration recovery; malformed answers retain the current session and use a
separate message. Ten-minute expiry, locks and shared budgets are unchanged.

## Route discrepancy investigation

The pipeline uses the exact explicitly authorized point and provider Place IDs in
directional Matrix requests. `DRIVE` uses `TRAFFIC_UNAWARE`, no departureTime or
premium options, and the original minimal duration/distance mask. Walking remains
Walking. Seconds parse directly, retain nanoseconds for hard constraints, and divide
by60 for minutes. Final UI rounds route seconds to tenths of a minute.

New deterministic fixtures distinguish origin→college1320s (22min), college→coffee
200s and coffee→origin1860s (31min). They verify leg association, total, mode,
unchanged policy and private-origin link exclusion. Existing direction, malformed
metrics, route reuse, mode invalidation and constraints regressions remain.

There is no original historical origin/accuracy, Google Maps departure/traffic
setting, chosen path/entrance or response to establish the precise22-versus31 cause.
Traffic policy is a plausible difference, not a proven explanation. Driving now
explicitly says it excludes live traffic, in shared disclosure and advanced legs.
No live Maps estimate is substituted and no traffic-aware tier is enabled.
The protected development diagnostics expose fixed route-policy/source/precision/
accuracy metadata; never precise origin, request text, IDs or raw payloads.

## Discovery funnel and improvement

The ordinary discovery adapter already supplies relevance, geography, page cursors,
retail/brand/containment, normalization and deduplication. Advanced resolution reuses
it. Named identities remain fixed. Whole-date verified closure filters remain;
unknown hours alone do not exclude. All routes still need directional evidence and
temporal evaluation before display. Explicit additional discovery follows real
cursors/approved query variants in the same area, at most two requests/action and
six pages/activity,100 retained candidates/group within existing smaller budgets.

Two losses were identified: geographic beam pruning favored a narrow prefix before
later stops gained representation; orchestration selected the first three timed
candidates and bypassed the router's existing diversity selection. The finite beam
now balances every occurrence, including checked-history usage, before repeatedly
favoring one venue. Final selection diversifies comparable timing/route categories
within the existing60-second travel window. Current pages remain stable across
field answers. Hard limits/evidence always take precedence. Discovery actions also
balance page counts so a later activity is not indefinitely behind earlier groups.

Aggregate developer diagnostics distinguish provider results, normalization,
geography/relevance rejection, duplicates, unique observed places, retained venues,
checked/unchecked venues, offered venues/assignments and pending routing. Internal
identities remain transient. Counts are finite coverage, never a citywide inventory;
not-yet-searched/routed is not called ineligible. Rich paginated inventories test
later activity representation and further distinct options without false exhaustion.
Four stops,24-path beam,27 directed-pair union/action,32 actions,256 checked
assignments and original ten-minute expiry remain. No automatic widening, retries,
new provider operation or speculative parallel searches.

## Measurements and acceptance

Development timing records fixed numeric stage labels only: local Qwen HTTP/load/
prompt/output/validation; provider admitted search/lookup/matrix/details spans;
named/activity resolution, routing and timing; safe backend/proxy Server-Timing;
client origin preparation, HTTP, loading feedback and browser total. Production
omits client measurements and proxy timing. Admission spans include authentication
and batch work; they are not presented as isolated network-wire latency.

Eight installed-Qwen requests (two runs each) passed the four exact interpretations:
college13.829/15.743s; grocery10.251/12.189s; grocery+ATM16.962/21.372s;
dinner/bowling14.556/18.137s. Model load4.860–15.925ms, output generation
9.925–21.053s, prompt185–366ms. These were warm requests; no cold model eviction,
settings change or controlled Qwen speedup is claimed. Date/validation after output
was1.1–50.6ms. The earlier reported30s cannot be reconstructed from these samples.

Offline same-fixture before/after samples are recorded separately from AI/network
and browser. The nearby repair removes an unnecessary interaction and reuses
existing evidence; it does not claim a faster model. Initial small fixture browser
college run: loading19.3ms, interpretation HTTP437.3ms, origin0.4ms, planning HTTP
366.6ms and total861.1ms including first development proxy compilation. Google and
Qwen are simulated in that sample. Additional actual-Qwen browser measurements and
final suite results are appended after verification.

No actual Google request was sent; real transports are blocked by the isolated test
server. Synthetic request ledgers remain distinct from posted charges. Existing
estimates are $0.035/Enterprise search and $0.005/Matrix cell, plus existing lookup/
Details rates; these are application assumptions, not newly verified prices.

Hosted checks57/57 passed, including restricted role, RLS/TLS, rollback/concurrency,
legacy and committed advanced reopen/cleanup. Browser saved the second option of
page3 and reopened only college+cafe7 in a native new tab with current invented
provider facts. Cleanup uses only its exact generated capability hash.

Device GPS permission timed out in the in-app browser; no location was assumed.
Backend tests exercise an explicitly authorized device origin through coordinate
search, public calendar, outbound/return route and cards. Browser uses confirmed
manual origins for end-to-end coverage. No live GPS/provider coverage or full
accessibility audit is claimed. Unknown hours, finite exploration, unsupported
separate home/time grammar and previous documented product limits remain.


## Final measured browser journeys

Actual installed Qwen plus invented provider responses, one browser sample/case:

| Request | Loading feedback | Interpretation HTTP | Origin preparation | Initial advanced/ordinary HTTP | Browser total |
| --- | ---: | ---: | ---: | ---: | ---: |
| College + coffee | 17.6ms | 14.130s | 0.8ms | 322.2ms | 14.504s |
| Ordinary dinner/bowling | 13.4ms | 13.420s | 0.6ms | 889.9ms | 14.360s |
| Grocery return, to area question | 19.7ms | 14.686s | 1.1ms | 2.688s | 17.478s |
| Grocery + ATM/45, to area question | 35.7ms | 38.660s | 0.9ms | 77.5ms | 38.790s |

Explicit nearby continuation then took613.9ms (518.8ms HTTP); exact-dwell answer
93.1ms (39.3ms HTTP), no extra AI. These browser totals include the client/proxy/
local networking/rendering path and development compilation; timing components
are inclusive and are not additive CPU-exclusive profiles. Tests/build were running
concurrently. The slow ATM sample spent35.160s generating model output,456.854ms
prompt processing and50.013ms model loading; its local AI HTTP took38.384s.
This demonstrates the continuing model-generation bottleneck, **not a measured
Qwen speed improvement**. The historical30s request and cold-model behavior remain
unreconstructed. No prompt/schema/model/thread/keep-alive setting was changed to
obtain a superficial timing result or weaken validation.

The first college provider/identity phase measured11.961ms named resolution,
7.323ms activity discovery,3.926ms routing and2.294ms timing. Admitted synthetic
search spans totaled5.455ms and Matrix0.876ms. Real Google network latency was not
measured. Next development logs additionally separated initial advanced proxy
compilation19ms from40ms application processing; warm advanced proxy compilation
was1.6–2.0ms with30–44ms application processing. Server-Timing retains the separate
numeric backend/proxy measurement for local inspection.

Same-fixture offline before/after medians, three samples each: college6.960/6.548ms,
grocery8.650/8.281ms, ATM23.034/9.026ms. Those are orchestration-only, tiny inventories,
shared-machine/uncontrolled-load samples. They are not a whole-app or model speedup.
The repair eliminates repeated invalid nearby interaction and date/lookup work,
keeps field answers model-free and cached routes reusable; new coverage work remains
explicit instead of doing larger speculative searches up front.

Browser acceptance: desktop1280 and mobile390×844, actual DOM client/scroll widths
390/390 and1280/1280, one main form/date control. Exact A–D requests reach their
correct ordinary/advanced paths. Grocery return uses the retained confirmed start;
ATM exact20 + supplied5 + route6 =31min within45, with a return leg. All three
options can vary both flexible stops. Strict first maximum1 excludes the two-minute
leg; explicit beyond retains original1. Flexible1 allows maximum2 and shows the
preferred-range deviation. Walking yields55min and is rejected by45; Driving
restores31 without another model call. Four browser text requests produced exactly
four extractions despite these regenerations. E–G combinations/discovery/history
worked; history counter comparison was unchanged. H selected only college+cafe7
from page3, opened in a native new tab and reopened after backend restart. Expanded
cards have one hours section per venue; all inspected venue/directions links were
underlined with safe targets. No caption/routine warning, overflow or duplicate form.
Keyboard/native controls and expansion were exercised; this is not a full audit.

Screenshots: `/tmp/50ef-mobile-final.png`, `/tmp/50ef-mobile-return-final.png`,
`/tmp/50ef-duration-final.png`, `/tmp/50ef-desktop-final.png`. These display invented
provider fixtures; they are not live Google verification. The baseline code and
reproduction retain before evidence for the removed label/box and nearby rejection.


## Final verification and accounting

Final complete backend: **901 reported,866 passed,35 opt-in skips**,214.161s.
The35 skips are27 separately executed hosted cases and8 unchanged opt-in PTY
lifecycle cases; normal owner backend/frontend health and homepage are HTTP200.
Frontend **252/252**,117.729s; focused **174 passed,one hosted skip**,24.488s;
hosted **57/57**,34.363s. The9 new backend cases exercise device/manual/representative
origins, invalid/replayed/expired answers, source geography, duration validation,
rich pagination/all-stop coverage and mismatched directional seconds. Three new
frontend cases cover concise presentation, units/relation and destination-local
clock formatting. Production build, TypeScript, ESLint, pip consistency, npm tree,
production audit (zero vulnerabilities), full tracked/new-file review and whitespace
checks passed. Secret scan found zero configured credential matches in current
sources/generated assets or Git history. Repository stays private; release tag
`prototype-v0.1` is unchanged. No owner/private configuration or ledger was changed.

A controlled college fixture with additional cafes measured:

| Explicit action | Searches | New Matrix cells | Existing gross estimate |
| --- | ---: | ---: | ---: |
| Initial page | 2 | 5 | $0.095 |
| Different options | 0 | 6 | $0.030 |
| More nearby (duplicate-aware page) | 1 | 0 | $0.035 |
| Previous/Next or dwell-only update | 0 | 0 | $0 |

The discovery example reused already verified pairs and additional cached options;
newly discovered/routed identities can incur additional cells, within the same27-pair
union/action and shared accounting. Rich later-page tests separately prove that new
eligible identities are retained/routed. These numbers are inventory-dependent,
not promised per-click prices or exhaustive coverage.

The cumulative separate browser fixture ledger, including restarts, recorded23
Enterprise searches,4 Pro origin lookups,236 Matrix cells and4 Details actions;
synthetic gross estimate **$2.193**. Actual Google traffic/cost: **0/$0**.
The four actual-model browser text requests stayed atfour extractions through nearby,
dwell, Strict/Flexible and mode regenerations. Eight additional standalone Qwen
samples bring local model verification to12 expected semantic outcomes. No cold
model run or real Google latency/coverage check is claimed.

Browser save cleanup independently checked the exact generated hash, model2,
original public request and only `Synthetic_college`/`Synthetic_cafe_7`, deleted that
single record and checked committed absence using a fresh connection. Other owner
records were untouched. Created tabs/remembered test link and temporary3050/3051/
8050 servers were closed; viewport reset. The normal owner3000/8000 servers remain.

Corrected verification failures: the old device-calendar test assumed zero discovery
before a date question; it now uses deliberately unknown public calendar evidence
and verifies coordinate discovery cannot invent a timezone. Rich coverage assertions
were corrected to distinguish all represented venues from still-unchecked complete
combinations. An existing frontend assertion required a material total-time warning;
that concise qualification is retained without restoring the routine box. The
approximate option retains its recognizable wording and adds the no-maximum note.
The isolated development copy initially lacked fixture data/configuration; it was
completed and pinned to existing repository dependencies before measured acceptance.
No failed attempt is reported as passing.

Functional follow-up acceptance is verified. **Qwen generation latency remains a
measured limitation**; no universal sub30-second response or model speed improvement
is claimed. Live device GPS and the owner's historical route discrepancy remain
unverified for the specific evidence reasons above. Task51 remains unstarted.


## November 3 — Task 50E compact details and editable itinerary preferences

This acceptance refinement continues `d526d6a`; it does not start Task 51.

### Shared cards and contact details

Both planning paths now render the original `PlanCard`, shared `ItineraryStop`,
artwork, numbered list, typography, actions and three-card grid. Advanced cards add
only supplied visit bounds, useful directional legs, requested ending and one
expandable timing/budget explanation. Ordinary scoring is unchanged. Names,
addresses, ratings and hours remain in their primary itinerary presentation.
Nested **View details** now adds phone/website, the contact/booking notice and any
new required third-party credit. Repeated identity/address/rating/hours, Maps links
already shown above, and repeated Google branding are removed. Link underlines and
mobile wrapping are shared. Actual travel exceptions remain visible.

Opening the itinerary does not request contacts or hours. A deliberate contact
click uses the existing gated Details operation, original outing budget, duplicate
protection and transient browser cache. Advanced contacts use that same capability;
no new field mask, API operation, automatic request, quota or Cloud setting is added.

### One effective preferences contract

Accepted advanced answers now appear in **Set preferences → A few details to make
it yours → Visit times and itinerary preferences**. All stop durations and their
Exact/At most/At least/Under/Approximate meanings, departure, original duration
references, source-required return/final destination and retained verified branch
choices are shown. Existing Date, Location, Travel mode and Starting location
controls stay canonical. Required source stops/return cannot be removed by a timing
edit. A different starting point is edited using the existing location control;
a different geographic calendar needs Location regeneration.

The server owns `AdvancedEdits` and effective preferences. The browser has one
editable draft, not separate clarification and preference forms. Structured edits
amend a trusted copy for timing; original Journey/source text remain unchanged.
Overrides are identified as explicit user changes. Clearing a duration/departure
override restores its original source value. Draft edits applied with the nearby
clarification preserve both answers for later model-free replay.

Changing a visit clears stale cards, selection receipts and page history. Regenerate
uses the same active token, resolver and directional route evidence. Timing is
recomputed; no old timing verdict is reused. Mode/origin/travel-configuration changes
use deterministic continuation and incompatible routes are not reused. Verified
branch edits can reuse previously checked compatible pairs; only missing pairs are
routed. Retained choices cannot inject arbitrary Place IDs. Cross-calendar branch
changes require area/date revalidation rather than stale calendar reuse.

### Entire outing versus travel-only

“Return within 45 minutes” remains an inclusive **entire outing** constraint. The
scope selector explains both meanings; selecting travel-only is a deliberate,
visible override of that original scope. It reuses the same source amount/relation,
not a second independent budget. Every route leg, including origin and return, is
counted. Independent deadlines still include visits. Required shopping and ATM
stops remain required even with unknown or excluded visit time.

With grocery 20 + ATM 5, 45 minutes including visits leaves 20 for travel. Grocery 10
leaves 30. Travel-only 45 allows 45 of route travel, with visits excluded from that
bound; these schedules are not interchangeable. Exact/inclusive/exclusive and
minimum/maximum/approximate semantics are retained. Approximate has no guaranteed
completion maximum. A minimum does not invent an upper bound.

Zero never drops a stop and is never advertised as realistic shopping. Zero counted
time requires travel-only plus an explicit acknowledgement, and is refused for an
entire-outing budget or independent finish deadline. Switching back requires a
positive duration or clearing the override. Original zero wording also requires
clarification before any fit claim. Travel-only cards do not present excluded/zero
counted dwell as a verified elapsed outing duration.

### Google route investigation and authorization

Audited the actual Matrix request: DRIVE + `TRAFFIC_UNAWARE`, or WALK without a
routing preference; **no departureTime**; minimal existing duration/distance/status
mask. Exact directional Place IDs (or separately confirmed origin coordinates),
protobuf seconds/nanoseconds, origin→first, inter-stop and return/end legs all use
the same evidence. Display rounding is not used for hard checks. The transient
cache is directional and mode-specific within an immutable routing configuration;
timing edits reuse it, incompatible configuration changes require regeneration.
No route policy/cache/cost tier was changed in this refinement.

Google's [Routes billing rules](https://developers.google.com/maps/documentation/routes/usage-and-billing)
classify traffic-aware Matrix requests as Pro. The
[global pricing list](https://developers.google.com/maps/billing-and-pricing/pricing)
shows first paid volume Essentials $5/1,000 elements (10,000 monthly free events)
versus Pro $10/1,000 (5,000 free events), checked November 3. At 27 elements the gross
estimate would change from $0.135 to $0.270 (+$0.135), before allowances/taxes/volume
adjustments. This would need explicit approval of the higher SKU and coordinated
request/evidence/cache/enforcement/saved-description/accounting changes. It was
**not activated**. Request volume, approved operations and quotas stay unchanged.
No live Google comparison was performed and no consumer Maps parity is claimed.
Consumer UI route choice, entrances, departure assumptions and traffic may differ;
manual consumer estimates are not provider evidence.

The shared notice now says: “Travel estimates use Google Maps. Driving estimates
exclude live traffic. Actual travel times may change, especially for future outings.”
It is shown once, including for tomorrow's outing. Repetitive per-leg traffic copy
is removed. Walking remains identified with its existing pedestrian-route warning.
These are estimates retrieved under the approved policy, not current live-traffic
or guaranteed future arrival predictions.

### Persistence, measured performance and verification

Saved v2 adds optional defaulted `budgetScope`, `originalJourney`, duration override
occurrences and departure override provenance. Old v2 defaults to entire-outing;
v1 remains compatible. Selected-only saving, capability links/30-day expiry,
restricted role, forced RLS and verified TLS remain. No migration. Only app-owned
requirements and permitted references are saved; no contact content, ratings,
hours, route metrics or private origin coordinates are added to storage.

Offline backend benchmark (20 alternating edits each): duration median 1.231 ms,
max 1.642 ms; scope median 1.195 ms, max 1.369 ms. Additional searches/Matrix requests: 0.
These measure local session/edit/timing evaluation, not Qwen, network or cold start.
The existing Qwen latency limitation is unchanged; no model speedup is claimed.
Browser 20→10 produced 31→21 minutes with 6 minutes of fixture travel and ATM 5 retained.
Through 20, 10 and explicit travel-only, fixture counts stayed searches 9, elements 70,
Details 4, AI 3: **zero incremental model/provider calls**. These are invented responses;
actual Google sends were blocked. The AI count measures fixture interpretations,
not fresh actual-Qwen timing. One interpretation per new text remains unchanged.

Desktop 1280 and mobile 390 acceptance covers ordinary dinner/bowling, named college
then coffee, grocery/ATM/return with 45 including visits, travel-only, accepted 20→10
editing, compact ordinary/advanced contacts, history and selected second-option
save/new-tab reopen. Links are underlined; no Select itinerary action or horizontal
overflow. New saved constraints/provenance also pass committed PostgreSQL reopen
in another process. Exact disposable hashes/selected identities were checked and
cleaned, then committed absence verified; owner records untouched.

Final frontend suite: **260/260**, 154.531s, run serially after a resource-contended
HTTP startup attempt. TypeScript, ESLint, production build, pip dependency check,
top-level npm dependency check and production audit (zero vulnerabilities) pass.
Full `npm ls --all` (also with optional omitted) flags pre-existing lockfile references
to `@emnapi/core` 1.10.0 / `@emnapi/wasi-threads` 1.2.1 under the uninstalled optional
Tailwind WASM platform package, whose ranges request ^1.11.1 / ^1.2.2. This is an
existing dependency-tree limitation, not reported as passed. Package manifests and
lockfile are unchanged; the native macOS build succeeds. No unrelated upgrade was
made. Hosted-enabled suite **58/58**, including 28 hosted cases and offline
compatibility checks, 30.350s (final repeat). Exact second-option browser saves were verified for
both named college/cafe and travel-only grocery/ATM, then independently cleaned.

Full backend: **914 reported, 878 passed, 36 opt-in skips**, 173.001s.
Skips are 28 hosted cases (run separately) and 8 unchanged PTY lifecycle cases;
PTY checks were not rerun because startup/shutdown code was unchanged. Final
focused timing/save/edit regressions: 90 reported, 79 passed, 11 hosted skips;
final strict edit/session contracts: 27 reported, 25 passed, 2 hosted skips. The
corrected legacy exploration fixture also passes independently. Full staged diff
review includes all 34 changed/new files, ordinary formatting and private-source
handling; whitespace checks pass. Credential scan: 2 configured sensitive values,
1,335 current files/assets and 2,155 historical objects, **zero matches**. Package
manifests/lockfile, private 0600 profiles, provider gates/quotas/billing, repository
privacy and release tag remain unchanged.

Additional final browser evidence: an unsubmitted eight-minute grocery draft survived
changing to Walking, with ATM five minutes, return and 45 minutes retained and a fresh 30-minute all-leg
walking route (43-minute outing). AI stayed 2; searches 6→8 and elements 48→72 were
needed for the incompatible mode. A travel-only 45 choice with grocery 20/ATM five minutes
kept both stops and the return, checking 30 minutes of travel rather than 55 elapsed.
The selected second option reopened at 390px with walking, scope, original text,
20-minute override and original ATM five minutes intact. One saved card only; scroll width 390.
All created browser tabs were closed and viewport reset. Only temporary 3051/8050
services were stopped; normal owner 3000/8000 services remained healthy. Owner
configuration was untouched.

Cumulative browser fixture ledger (including restarts): 14 Enterprise searches,
3 Pro manual starting lookups, 142 Matrix elements, 6 Details actions; synthetic
gross estimate **$1.416**. Actual Google sends/cost **0/$0**. Timing edits/scope
changes themselves add no paid requests. The two selected browser records were
removed only after exact hash, original source, selected IDs and new provenance
checks; fresh connections confirmed absence. Private capability links are not
committed or included in delivery output.

The first full backend attempt encountered sandbox socket/IPC permission errors;
it was rerun with the required local integration-test permissions. Initial focused
fixtures assigned raw dictionaries instead of Duration models and used a partial
single-cell response that was still complete; the fixture errors were corrected.
The first ordinary browser attempt lacked its exact invented extraction; that
explicit test reply was added. Neither failure is reported as passing. A draft
entered before nearby clarification and its replay are specifically regression
checked. No deployment, authentication/provider changes or new roadmap task.

The complete backend rerun initially exposed a legacy route-exploration fixture
using two zero-minute visits. It was updated to one explicit minute per visit,
keeping its infeasible-cached-path and later-feasible-path assertions. The focused
regression passes; zero wording is separately covered as clarification.


## November 3 — consolidated Task 50E refinement

The owner's explicit current-traffic decision replaces the earlier unactivated Pro proposal. Traffic-aware routing/accounting, return/now semantics, shortest-first exploration, five dwell bounds and a measured model investigation continue Task 50E. Unsafe model changes were rejected; the latency acceptance item remains open. Existing card identity, editable answers, selected private saving, security, startup and roadmap numbers remain. Task 51 stays unstarted. [Implementation, measurements, verification and limitations](task50e-consolidated.md).


## November 4 — final Task 50E acceptance repair

Shared readable duration formatting, named closed-visit recovery with explicit stop-specific permission, balanced optional-stop recommendations and editable missing coffee dwell continue Task 50E. Exact enforcement, other venues’ hours, source constraints, selected private saving and approved provider accounting are preserved. No migration, Cloud/profile/model/dependency change or Task 51 work. [Diagnosis, measured counts, trust/lifecycle contracts and verification](task50e-final-acceptance.md).
