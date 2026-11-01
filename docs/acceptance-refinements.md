# Tasks 46/49 — saved cards, retail, ranking and local startup

This is an acceptance refinement of completed Tasks 46/49. Task 50 and 50A–50E
remain unstarted. No migration, SQL grant/RLS change, dependency, provider service,
Cloud quota/billing change or live Google verification is included.

## Saved itineraries and deliberate refresh

Saved itineraries occupy the main result position, in original option/stop order,
with the selected option marked. Generated recommendations, pagination and
exploration precede the secondary Save/reopen controls. Reopened plans hide demo
and unrelated generated cards. The new-outing form stays available. Real stops
initially use activity/intent placeholders; no raw Place ID is a primary title.
The same general card grid and responsive styling are used. Constraints remain
available in a disclosure. Unknown travel is unavailable, never zero.

`POST /api/plans/refresh` accepts the existing private `accessToken`, original
`candidateId`, and a UUID `refreshId` generated only by a deliberate button action.
It reopens through the existing restricted-login, capability-scoped RLS read
transaction, checks expiry and option membership, and closes SQL before provider
I/O. No arbitrary client Place ID is accepted. It refreshes only that option's
unique Google references, sequentially (at most four). No generation or route call
occurs. Neither the saved structure nor its constraints/selection is updated.

The exact Place Details New mask is
`id,displayName,formattedAddress,businessStatus,attributions`: **Place Details Pro**.
There are no photos, ratings, hours, reviews, contacts, inventory or schedules.
Names/addresses/status/credits/timestamps live only in the current browser component;
no database, disk, localStorage or server provider-content cache is created.
Reload restores placeholders until another intentional refresh. Closed or missing
venues retain their original stop. Partial results remain visible; quota/service
failures stop remaining fan-out. A UUID prevents replaying the same refresh action;
a new explicit action uses a new UUID but shares the same per-capability budget.
Repeated deliberate attempts can exhaust six Details requests in the active
30-minute refresh session. There are no automatic retries. Provider failures remain
charged; failed pre-admission actions can be deliberately attempted after repair.

This reuses the already enabled, separately gated Details GET capability, beneath
the existing Enterprise contact field tier. It requires local real mode and
`WHERETO_CONTACT_DETAILS_DEV=1`. It adds no new billable method or higher tier.
Normal fresh clones/tests/production do not enable it. Existing process/outing
limits, concurrency one, 10 Details/minute and persistent exploration accounting
apply. Cloud Details quota remains the last verified 40/day, 10/minute; no claim
is made about current remaining Cloud quota. The estimate conservatively retains
**$0.020/Details attempt**, although the global published initial Pro list tier is
$17/1,000 ($0.017), with a 5,000 monthly free cap. Credits/allowances are not assumed
and posted billing can differ. Four detail reads estimate at most $0.080 under this
conservative ledger, six $0.120. Opening links costs **zero** provider operations.

The official [Details field tiers](https://developers.google.com/maps/documentation/places/web-service/place-details),
[global prices](https://developers.google.com/maps/billing-and-pricing/pricing),
[Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
and [service terms](https://cloud.google.com/maps-platform/terms/maps-service-terms)
were reviewed. Place IDs may be retained; unrestricted provider-content storage
is not introduced. Existing user-authored activity intent (e.g. “Zara outlet”)
is retained as intent, never promoted to a provider-verified name. A separate
user-label editor/storage field is unnecessary and not implemented. Google Maps
and any returned third-party credits remain visible.

The normal link interface says **Your saved plan** and “Copy this private link to
reopen your plan for 30 days. Anyone with the link can view it.” Copy feedback is
visible; Open and Forget remain available. There is one collapsed copyable link,
plus the separate collapsed pasted-link import. Recovery instructions stay in
collapsed help. Hashing, secure tokens, expiry/no-store/no-referrer/local boundary
are unchanged. Failed saves never create confirmed links. Anonymous links still
have no accounts, ownership, revocation or public-deployment protection.

## Retail semantics and evidence

Qwen's extraction instructions retain brand/format/mandatory wording verbatim.
The existing deterministic normalizer preserves retail phrases as custom activity
IDs. There is no finite brand catalog or brand-specific exception. “Zara outlet”
uses brand-preserving outlet/store searches; a regular Zara or flagship is eligible
without confirmation. Outlet format gets a small preference bonus when supported
by the actual name. “Only outlets” / “no regular stores” retains a hard format
restriction and excludes unverified formats. Verified names are never rewritten
to call an ordinary store an outlet. A failed preferred query may make one bounded
same-brand regular-store refinement, using the existing shared search budget.

A brand requires exact provider name identity plus retail type; generic format
suffixes are allowed. A similarly named “Zara inspired boutique”, an unrelated
retailer, mall-only search hit, or missing retail evidence cannot satisfy it.
This is conservative source evidence, not independent trademark/fraud verification.
Nonstandard branch names can be missed rather than guessed. Generic shopping,
clothing/shoe/electronics/book/department/specialty stores, malls, shopping centers,
retail plazas and outlet centers have separate intent from brand tenants. Single
retail and retail+coffee/dinner plans use the same constraint/routing engine.

`places.containingPlaces` is added to the existing Text Search mask at the same
Pro tier (or already opted-in ratings Enterprise tier). It returns IDs/resource
names, **not display names**, and does not guarantee comprehensive tenant coverage.
The canonical in-memory parent record joins a parent ID to separately discovered
mall facts before naming a mall or marking its type verified. A store near a mall
without containment evidence is not a tenant. “Mall with Zara” intersects actual
mall IDs with parent IDs from a brand-store search. Multiple required brands must
share a verified mall; separate brand visits with a same-mall requirement require
a common verified mall ID before ranking. A named-mall tenant request checks the
mall separately. Relationship searches are finite (at most three brand checks per
mall request) and individually charged to existing quotas/budgets. No Nearby
Search, indoor navigation, floor map, inventory or new data provider is activated.

Geographic/travel boundaries are unchanged: ordinary destination preference can
include nearby candidates with addresses shown, while explicit hard geography is
retained. No verified brand hit means incomplete checked coverage, not proof that
no store exists. The UI offers Explore farther; it does not fill with unrelated
brands. Mall-directory or another licensed provider may improve future coverage,
but no such integration or later-roadmap task is begun.

## Ranking and continuation audit

Two distinct causes of later shorter options existed. Explore farther can discover
new venues/pages/regions that were absent initially. Separately, first-stop travel
was omitted from convenience scoring even with a confirmed origin and no entered
limit; unknown partial beam routes used zero in a travel sum; the initial diversity
selection could prefer a previously unseen venue within 0.15 of the best score
before taking the strongest known option. Those could defer better known choices.

Hard feasibility still precedes ranking. Real convenience now uses verified
first-stop plus directional inter-stop minutes, with unknown evidence earning no
convenience. Beam pruning includes the origin and orders unknown evidence behind
verified paths. The highest-scored eligible option is selected first; subsequent
cards balance all-stop novelty within 0.08 of the best remaining score. Comparable
scores use shorter known journeys before ID ties. Venue quality/relevance and
Strict/Flexible limits are preserved. Nearby first-stop search anchors now favor
the next nearby promising anchor even without a travel cap. No initial fetch-all
100-candidate or Cartesian matrix operation is introduced.

Show different options makes no Places searches. It uses retained discoveries and
selective routing as before, preserving constraints, complete-itinerary uniqueness
and all-stop diversity. Explore farther expands finite coverage and reranks the
expanded pool without deleting page history or saved selections. No globally
optimal claim is made about undiscovered/unverified venues.

Sanitized `rankingAudit` records known/new venue counts, eligible/deferred counts,
selected score components and first/inter-stop minutes. Per-option late reasons
distinguish newly discovered venues, newly verified known venues, and remaining
already-ranked combinations, with a flag for shorter travel than previously shown.
No private origin coordinates, tokens, raw provider objects or credentials enter
the dedicated snapshot. Existing route/search/cost counters remain intact.

## Normal explanations and local diagnostics

One shared **Before you go** notice follows cards, page arrows and discovery
controls, before saving. **About these recommendations** is collapsed and concise.
Generic session/location caveats are consolidated there. Option-specific hard
violations, missing routes, accessibility/evidence conflicts and known closure
remain visible. Single-stop cards do not show a zero inter-stop journey.

Raw JSON, counters, cost ledger and ranking internals are absent from normal
recommendation explanations. In Next development only, **Local development tools**
can explicitly load a sanitized snapshot from `/api/development-diagnostics`.
Backend access additionally requires loopback/same-origin boundaries, local real
mode and `WHERETO_DIAGNOSTICS_DEV=1`; production Next returns 404 and renders no
panel. Production proxy payloads strip internal diagnostics and developer notes.
This is a local development boundary, not public production authentication.

The UTC fallback came from a small static destination-name map before provider
discovery, not the browser clock or lost Google timezone response. The map now
covers Jersey City/New Jersey and recognized NYC neighborhoods, plus known UK,
US and Indian cities used here. It is an explicit named-area calendar reference,
not a paid timezone/geocoding lookup or universal coordinate resolver. Known
provider timezone values remain supported by the canonical model; no unapproved
timezone API/field tier is added. When an unknown named destination makes a relative
date ambiguous, ask for an exact date or recognizable city. Missing destination
is clarified first. Explicit dates/times remain intact. Browser timezone is used
only for the existing expressly nearby/browser-calendar flow, never to override a
known destination. UTC-boundary tests distinguish New York, Hyderabad and London.

## Startup

From the repository, Terminal 1: `npm run dev:backend`. Terminal 2: `npm run dev`.
The launcher reads owner-only ignored `backend/.env.development` data when present,
then the existing restricted `backend/.env.persistence`. Files must be regular,
owned by the user, mode 0600, bounded, with allowlisted plain assignments. Shell
commands are never executed. Administrator identity is refused. Existing verified
TLS settings remain. No provider or database call occurs merely to start.

The owner's profile enables only their explicitly requested existing real-mode,
exploration/ratings/contact/manual-lookup flags, nonblocking $10 warning and local
diagnostics. It contains no credentials; database credentials stay in their
separate private file. Fresh clones without a profile remain mock; CI/hosting/
production refuse to load profiles. Direct unittest/uvicorn execution never imports
the profile. Explicit mock override: `npm run dev:backend -- --mock`.
Stop the active backend with Control+C before changing modes. Real planning/refresh
uses Google only when the owner deliberately requests it. Tests always use offline
fixtures and isolated accounting; the owner's real ledger is never reset.

## Verification notes

Offline fixtures are explicitly invented and never become production fallbacks.
The actual local Qwen model initially lost a mall relationship; source-grounded
few-shot examples corrected the checked “mall with Zara” and “Nike and Adidas
stores in the same mall” extractions. A deterministic validation guard now rejects
lost mall/mandatory-format semantics instead of silently recommending a simpler
store request. It does not manufacture replacement model activities. Brand-specific
interpretation remains bounded by the source phrase and normal clarification flow.

Selected saved cards receive keyboard focus on reopening while retaining DOM option
order. Refresh does not move focus or alter the selected option. Pending remembered
link reads cannot replace a newly edited outing. Detailed check totals, hosted
fixture cleanup and actual browser evidence are in the latest HANDOVER.md entry.

A failed repeat refresh keeps earlier in-memory names with an explicit stale label;
reloading still clears those provider facts. Single-stop generated cards show the
actual venue address so a nearby store cannot appear to be inside the search city
merely because the original request named it. Hosted test cleanup targets only the
known disposable capability hash; pre-existing owner plans are preserved.


## November 1 — final Tasks 46/49 acceptance repair

Current behavior supersedes earlier automatic/all-option saved-view descriptions: normal visits keep saved links collapsed, explicit private links render only the selected detailed itinerary, and Open saved plan opens a secure new tab. One explicit selected-stop detail load uses the existing Pro mask with Maps URI; optional phone/website fields require deliberate existing Enterprise contact opt-in. Provider content stays in memory. Structured continuation states distinguish combinations, discovery, bounded exhaustion, limits, constraints and pending routes; ranking is preserved. Actual default-port startup was checked, and occupied backend ports now give actionable guidance. No migration, role/RLS/TLS/quota change or later task. See [the final repair report](final-acceptance49.md) and the latest HANDOVER.md evidence.
