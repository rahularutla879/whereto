Current Task 50E uses the existing authorized current-hours search evidence for fresh destination-local “now” arrivals. Exact arrivals known closed are excluded; opening before arrival is allowed; closing during a required dwell fails. Missing/unknown visit bounds or hours remain qualified. No automatic Details request or new paid fields are added for this timing check. Existing overnight, 24-hour, special-day, freshness and DST rules remain. [Acceptance and boundaries](task50e-consolidated.md).

# Tasks 46/49 — search hours, saved hours and development capacity

November 2, 2026. Acceptance refinement; Tasks 50 and 50A–50E remain unstarted.

## Display and field authorization

Saved venue introductions no longer mention API quota; existing loading/error/stale
states, explicit update actions and Google/third-party attribution remain. Shared
formatters capitalize known activity/mode labels and recognized destination spellings
(e.g. Near Me, Jersey City, New York). Arbitrary geographic text, acronyms, apostrophes,
brand spelling and provider venue names are preserved rather than blindly title-cased.
Custom all-lowercase activity phrases receive sentence casing. This changes display
only, never search queries, canonical IDs, stored values or source evidence.

`WHERETO_HOURS_DEV=1` is a new local-real-development gate for the owner's explicitly
requested Text Search hours. It is enabled in the ignored owner profile, alongside the
already approved Enterprise ratings gate. Fresh clones/CI/production stay off. The
owner separately approved `WHERETO_SAVED_HOURS_DEV=1` for the explicit selected-only
Load opening hours action; that flag is enabled only in the ignored owner profile too.
The startup parser accepts both flags as data; no arbitrary shell configuration runs.
Automatic saved-open Details stays Pro-only; no Enterprise background action/retry.

Base Text Search mask remains:
`places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType,nextPageToken`.
Normal discovery adds existing `places.containingPlaces`; authorized ratings adds
`places.rating,places.userRatingCount`; authorized hours adds
`places.currentOpeningHours,places.regularOpeningHours,places.timeZone`.
One request contains the union; there is no second search just to fetch hours.
Explicit minimal starting-place lookup masks remain Pro. No extra phone, website,
photos, reviews or secondary-hours fields are silently added to search.

Current/regular hours trigger Text Search Enterprise, $35/1,000 ($0.035/request) at
the first paid global tier, versus Pro $32/1,000. This is $0.003/request extra when
upgrading a Pro search. Existing owner rating-enabled searches already use Enterprise,
so their SKU/estimated rate does not rise again for hours. Search admission, ledger
reservation, actual dispatch accounting and diagnostic SKU labels all use the same
hours-or-ratings decision. Failed dispatched attempts remain counted; rejected local
admission does not dispatch a request. Gross estimates exclude allowances/credits and
are not posted bills or a hard monthly guarantee.

Automatic saved Pro mask is unchanged:
`id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions`.
Manual contacts still adds `nationalPhoneNumber,internationalPhoneNumber,websiteUri`.
The separately approved manual hours action adds
`timeZone,currentOpeningHours,regularOpeningHours` to Pro; no contact fields are
added unless independently requested. It costs Details Enterprise $20/1,000, at most
four unique selected stops ($0.02 each/$0.08 per four-stop action before allowances).
The same ten/minute, project quota, concurrency-one, capability validation, action UUID
replay prevention and durable accounting apply. Original saved date/window comes from
SQL, never a client-supplied replacement date. Current names/contacts already in page
memory retain their own receipt timestamp when hours alone are updated. Contact updates
retain independently observed hours, and returned attributions from both lookups are
combined without dropping provider credits. Hours display their own checked time. New hours are
not used to overwrite original saved stops or imply historical details were retained.

Official references reviewed:
[Text Search fields](https://developers.google.com/maps/documentation/places/web-service/text-search),
[Place Details fields](https://developers.google.com/maps/documentation/places/web-service/place-details),
[OpeningHours/timezone reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places),
[global prices](https://developers.google.com/maps/billing-and-pricing/pricing),
[Places policies](https://developers.google.com/maps/documentation/places/web-service/policies).

## Hours interpretation and eligibility

The discovery DTO now carries hours, venue timezone and original response-receipt time
through the existing canonical normalizer. It no longer discards those fields at the
minimal discovery bridge. Protobuf zero hour/minute components are normalized as zero,
without manufacturing a missing period or weekday. An empty point is rejected rather
than becoming an invented 24-hour schedule; a missing weekday is derived only from
an explicit provider date. Regular/current/special-day evidence remains
separate. No today/openNow inference establishes availability for another day.

The pure hours projection uses fresh dated current periods within their supported
seven-day window and verified venue timezone. Entirely closed days or no overlap with
explicit mandatory outing bounds exclude that venue before further candidate routing.
Default 10AM planning starts are not treated as mandatory user arrival times. If no
exact time is supplied, the whole date is considered; early-opening venues are not
incorrectly excluded merely because of a default start. Overnight/24-hour periods,
end-of-date midnight, special days and DST are handled conservatively. Stale,
truncated, undated, missing or out-of-coverage evidence remains unverified. A differing
outing/venue timezone does not establish closure from an incorrectly converted clock.

A partial overlap does not prove an unknown-length visit fits. Existing real stops
still have unknown arrival/departure/duration; no timeline is invented. The existing
feasibility evaluator can establish full visit coverage when actual aware arrival and
departure evidence is supplied (offline tests), but live results do not claim it merely
because a user entered a broad outing window. Open hours never verify bookings,
showtimes, tickets, dinner service or activity participation. Ranking weights,
Driving/Walking, route modes/distances, hard geography and Strict/Flexible remain.

Expanded View plan and each selected saved stop have a compact Opening hours section:
requested date, venue timezone, date-specific ranges/special-day indication, overnight
notation or closed day. Typical weekly hours are collapsed. Outside reliable current
coverage, relevant regular hours are labeled Typical with special-day uncertainty.
Missing evidence displays Hours unverified. Regular hours alone never exclude a venue
as definitively closed. All-current-hours-closed results explain the checked date/window
instead of reporting a provider failure or inventing replacement venues.

## Capacity audit — no Cloud or spending increases

| Protection | Current local setting | Last verified Cloud setting / purpose |
|---|---:|---|
| Search + origin lookup | 10 requests/minute, shared process + durable ledger | Text Search 10/minute; 200/day |
| Details, all links/viewers/actions | 10/minute, shared process + ledger | Details 10/minute; 40/day |
| Matrix | 150 elements/minute, process + ledger | 150/minute; 2,000/day; element accounting |
| Provider concurrency | 1 | Application admission/financial protection; zero retries |
| Ordinary non-exploration outing | 10 searches, 300 matrix cells, 30 attempts; Details6 | Bounded application/financial safeguard |
| Ordinary process session | 50 attempts, 1,500 matrix cells, 10 lookups | Application safeguard, not a Cloud quota |
| Active continuation registry | 50 contexts, ten-minute expiry (was20) | Bounded transient computation memory, no additional provider admission |
| Authorized owner exploration | cumulative search/attempt/matrix/lookup ceilings removed already | Finite action stages, 100/activity discovery and shared minute/Cloud limits remain |
| Saved explicit open/action | four unique selected references; action replay guard30min/512 entries | Capability/abuse protection; no lifetime six-per-link bottleneck |
| Owner local estimated spending | $10/local-day warning, nonblocking in exploration | Financial visibility; existing $50 account alert is not a hard cap |
| Non-exploration estimated spending | configured hard local guard when used | Deliberate financial protection; not raised |

Cloud values above are the repository's last verified values, not a fresh quota query
or a claim about current remaining allowance. Actual Cloud daily quotas are enforced
by Google; local accounting does not reset/bypass them. The durable ledger survives
backend restarts; process-window resets cannot bypass its minute accounting. Do not
delete/reset it to recover. Retries are explicit user actions, never automatic sends.

The active continuation registry was a distinct avoidable application restriction:
only 20 fresh searches could be retained, so the 21st evicted an active search before
its ten-minute expiry. It now retains **50** isolated active contexts, still bounded,
still expiring after 600 seconds, still evicting oldest at capacity. This changes memory
retention only: no provider action, concurrency, rate, daily quota or spending allowance
is increased, and no background Google work is added. It can avoid unnecessary fresh
searches caused by early continuation eviction. A deterministic 30-session reproduction
lost the first session before the fix; retention/50-entry eviction/expiry tests pass.
A separate invented two-activity/three-candidate hours-context measurement allocated
35.93 MiB (36.19 MiB peak) for 50 independent context-data copies (existing budget/session
references excluded). This is a representative fixture,
not a worst-case full-pool memory guarantee; the cap remains finite for that reason.

The repeated-testing minute limits mirror Cloud capacity, and owner exploration already
removes cumulative prototype request ceilings. Therefore **no provider admission cap,
concurrency, Cloud value or spending threshold was raised**. Raising a local Cloud mirror
alone would increase rejection/billable exposure rather than usable Cloud capacity.
Ten consecutive searches are supported across admitted shared windows, not promised
simultaneously. Specific errors and deliberate Retry preserve preferences without
refresh. Double-click/replay guards remain. Hours filtering can reduce wasted routing.

Strict/Flexible-only reuse was considered: prior hard-limit discovery/shortlisting can
omit candidates and route evidence needed under a changed limit. Mutating that session
would compromise immutable preferences, saved pages and no-repeat history. This pass
keeps fresh bounded generation instead of introducing a cross-configuration provider
cache or claiming a pruned pool is equivalent to a new search. That optimization needs
a separately reviewed transient snapshot/re-evaluation design, not a quota reset.

### Tester planning estimates

Assume each tester generates/regenerates ten two-activity outings/day, each with three
Enterprise searches (including destination resolution) and12 matrix elements, plus one two-stop saved open (two Pro Details)
and one manual hours load (two Enterprise Details). The browser fixture measured three searches and12 cells for this shape; these are
scenario assumptions, not production averages. The starting point is already confirmed.
One new manual-origin lookup/tester/day adds one Search request and $0.032/tester
($0.32/$0.80/$1.60 for10/25/50); an optional two-stop contact action adds two Details
and $0.04/tester. Discovery/exploration can cost more.
Gross paid-tier estimate/tester/day:30×$0.035 +120×$0.005 +2×$0.017 +2×$0.020 = **$1.724**.
The conservative app Details estimate uses $0.020 for both tiers, totaling $1.73. A lean two-search variant would instead cost $1.374/tester/day.

| Testers | Searches/day | Matrix elements/day | Details/day | Estimated gross/day | Required daily Cloud capacity |
|---:|---:|---:|---:|---:|---|
|10|300|1,200|40|$17.24|At least300 Search/day; Details at current cap |
|25|750|3,000|100|$43.10|At least750/3,000/100 respectively |
|50|1,500|6,000|200|$86.20|At least1,500/6,000/200 respectively |

If each active tester initiates one such outing per minute, peak search/matrix demand
is30/120 for10 testers,75/300 for25,150/600 for50. A simultaneous saved-open + manual
hours action would demand40/100/200 Details per minute respectively. Current10/minute
Search/Details and concurrency-one cannot support that instantaneous demand. Even the
10-tester daily example exceeds the owner's monthly spending target if repeated every
day. Any quota, concurrency or recurring-budget increase needs a separate costed owner
approval and Cloud review. No such change was made. Sharing a plan remains independent
of enrichment: valid capabilities still retrieve app-owned structure when Google is
limited; multiple friends do not get a permanent per-link lifetime request allowance.

## Persistence, security and verification

No migration. SQL stores only existing app-owned constraints/ordered selected structure
and permitted references; search/Details hours are transient provider evidence, excluded
from receipt documents, SQL and browser persistent storage. Saved automatic Pro and
manual hours are separate actions. Hours failure preserves the saved plan. Restricted
runtime identity, TLS, forced RLS, capability hashing/expiry and owner records remain.
All verification uses invented provider fixtures with live Google dispatch forbidden.
See final HANDOVER checkpoint for actual suite totals, hosted cleanup and browser proof.

Final verification: backend **671 run,651 passed,20 hosted skips**; frontend **232/232**;
separate hosted **37/37** (20 actual PostgreSQL rollback checks plus17 offline). TypeScript,
ESLint, production build, dependency consistency and credential scans passed. Desktop1280
and mobile390 verified generated/saved date-specific hours, contacts retained after manual
hours, selected-only new-tab reopening, unknown/all-closed fixtures, continuation and actual
shared-window recovery without refresh. The committed disposable plan was exactly cleaned;
owner records were preserved. Details of screenshots/counters are in HANDOVER.md. No live
Google requests were dispatched. Approved profile flags load through normal startup;
restricted database/TLS and both health endpoints passed. No later roadmap work started.
