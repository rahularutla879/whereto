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
