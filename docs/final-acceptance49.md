# Final Tasks 46/49 acceptance repairs — November 1, 2026

This supersedes the saved-view/startup/continuation UX in the preceding acceptance
checkpoint. Task 50 and Tasks 50A–50E remain unstarted. No ranking rewrite, schema
migration, credential/role/RLS/TLS change, Google quota/billing change or new
provider service was introduced. Verification uses invented Google fixtures.

## Continuation state and messages

The duplicate exhaustion sentence originated in two backend fields: `message`
used “We've”, while an error used “We have”. The adapter's exact-string Set kept
both, then concatenated them. The same backend wording now feeds both fields;
`planningMessage` also canonicalizes contractions/punctuation before deduplication
and preserves distinct errors. One live status sits beneath continuation controls.
Page restoration carries the latest action flags, rather than stale page flags.

The backend publishes a validated `continuationStatus` with six kinds:

| Kind | Meaning/action |
| --- | --- |
| available | Verified eligible combinations remain; Show different options. |
| discovery_remaining | Checked combinations exhausted; finite searches/pages/regions remain; Explore farther. |
| search_exhausted | Current bounded strategies and useful combination work exhausted; both disabled, adjust area/preferences. |
| provider_limited | Provider/application admission prevents work; existing pages/constraints retained. |
| constraints | Checked options cannot meet original requirements; explicitly adjust or explore, never silently widen. |
| pending_routes | Known places need bounded route verification; Show different options can perform it. |

Retained inventory alone no longer implies useful work forever. Missing directed
pairs considered promising by the existing spatial planner, unoffered eligible combinations and a remaining bounded frontier determine
combination work; sequential discovery checks actual unfinished jobs, pages,
anchors, finite regions and the configured retention ceiling. Known exhausted
requests return a structured no-op with no provider I/O. This describes application
coverage, never the nonexistence of venues elsewhere. Ranking/scoring/weights,
Strict/Flexible enforcement, diversity and complete uniqueness are unchanged.

Local minute pauses retain recoverable action flags and their capability. Actual
failed Google requests keep the existing no-retry protections; a stopped outing
is not reset to retry an attempted provider request. Errors carry explicit safe
action flags so the UI can disable established no-work actions while keeping
page history. A network failure alone does not erase action availability. Changing
preferences remains explicit. Provider limits and search exhaustion are distinct.

## Saved plan navigation and selected detail view

A normal `/` visit reads only remembered link availability and leaves **Saved
plans** collapsed after the main content. Expanding it never fetches/replaces the
current outing. **Open saved plan** is a native link with `target="_blank"` and
`rel="noopener noreferrer"`; the current page/selection/pages stay intact. Keyboard
activation uses browser link behavior. Copy is separate; popup-blocking guidance
explains copying/opening another tab, with no same-tab fallback.

Explicit `#saved=...` navigation opens the saved plan and clears the fragment.
Only its selected itinerary is rendered, in stored stop order, with original option
number, date/location and preserved constraints. Alternatives stay in SQL and the
version-1 document for compatibility. No new save-only-selected behavior or record
rewriting. Generic placeholders previously existed because all three stored
alternatives were rendered and Google content was deliberately omitted from SQL.

An explicit-view history boolean plus a per-tab sessionStorage capability reference
allows refreshing that deliberately opened view. The ordinary device reference
remains in localStorage. No provider content is stored in either. A normal new
navigation has no explicit-view marker and cannot auto-restore saved cards.
Non-saved hash navigation does not reopen/reset current detail content. **Return
to planning** clears explicit view state and restores the prior in-memory outing.
Malformed/failed links show their own status without old saved cards or demo
alternatives masquerading as the requested saved plan.

## Current details, licensing and useful links

One **Load current venue details** button loads only selected-option references.
The backend enforces selected membership after the existing capability/RLS/expiry
read. Other original alternatives cannot be used for detail fan-out. No automatic
Google request occurs on normal startup, private-link opening or saved-view reload.

Default mask: `id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions`
(**Place Details Pro**). The additional Maps URI stays in the existing Pro tier.
Only provider-supplied, validated HTTPS Google Maps URLs are displayed; no guessed
venue URLs. Current names/addresses/business status and map links populate ordered
stops after loading. The heading uses current verified names when available; the
original Google-derived title was never stored and cannot honestly be recovered
as historical truth if a venue has changed its name.

Optional unchecked **Include phone and website (existing paid contact tier)** adds
only the already-supported `nationalPhoneNumber,internationalPhoneNumber,websiteUri`
fields, using the existing contact development gate. This explicit opt-in selects
the existing **Enterprise** tier, not a new higher tier/service. No wildcard,
ratings, reviews, photos, hours, ticket/price/inventory fields are added. Search
ratings authorization is not treated as permission to retrieve saved Details
ratings. Unavailable fields have no fabricated fallback.

Both choices share the existing six-Details active capability budget, ten/minute
protection, concurrency one, zero retries and persistent exploration accounting.
A selected option has at most four stops; one Details request per unique stop.
The conservative ledger remains $0.020/attempt for both choices. The previously
reviewed global first paid list rates are $0.017 Pro/$0.020 Enterprise; credits/free
allowances are not assumed and current posted billing is not verified by tests.
No live billable Google requests occurred in this repair.

Refreshed content lives only in component memory. SQL continues to retain only
permitted Place IDs/app-owned structure/provenance. Partial failures preserve the
original stops, successful details and earlier in-memory names labeled stale.
Closure is labeled explicitly. Original route estimates were not retained; no
route refresh/regeneration occurs. Backend restart/private-link reopening still
works; refreshed provider content must deliberately be loaded again.

One appropriate Google Maps attribution remains per card; redundant route/stop/
contact-panel brand repetitions are removed. Returned third-party credits remain,
with exact duplicate credits consolidated. Venue-specific navigation links and
separately returned contact credits are preserved. Policy references:
[Details fields](https://developers.google.com/maps/documentation/places/web-service/place-details),
[Places attribution/storage](https://developers.google.com/maps/documentation/places/web-service/policies).

## Startup investigation and current commands

The inspected owner profile/runtime files exist, are owned by the owner and mode
0600, parse correctly, enable the intended local real flags and select the restricted
runtime identity. Existing TLS certificate/hostname verification remains intact.
Local Ollama is reachable with the configured Qwen model installed. The protected
impersonated ADC file is present; no live Google authentication/venue request was
used to claim credential validity. Existing Next proxies target port 8000.

At investigation time the owner's processes were already healthy: backend `/health`
and frontend `/api/health` returned 200; mode was real with exploration/manual lookup/
contacts enabled. The earlier unspecified startup failure could not be reconstructed
from these healthy processes. Re-running the commands while those ports were in use
**did** reproduce the backend's low-level address-in-use error; Next correctly
identified its existing server. Backend preflight now gives a concise reuse/Control+C
instruction and never silently selects another port. The probe matches Uvicorn's
SO_REUSEADDR behavior: a real TCP TIME_WAIT regression reproduced and fixed a
false occupied-port result on rapid restart. It also gives safe actionable
private-file instructions rather than printing arbitrary parser/config errors.

Stop an existing instance in its Terminal with Control+C, then:

```sh
# Terminal 1
cd ~/Documents/whereto
npm run dev:backend
```

```sh
# Terminal 2
cd ~/Documents/whereto
npm run dev
```

Both exact commands were executed after a controlled restart on the owner's local
machine. They started on 8000/3000, returned healthy proxied responses and enabled
the intended real profile without manual sourcing. `npm run dev:backend -- --mock`
was separately started on 8000 and generated three mock options through the actual
frontend proxy. The offline provider-shaped browser backend then loaded the same
profile/restricted identity while blocking all real provider HTTP sends. It is an
explicit test harness, not a production fallback or globally enabled startup flag.

Fresh clones remain mock without an owner profile. Tests/direct server execution do
not read that profile; CI/known hosting/production refuse the local launcher.
Database configuration remains backend-only, administrator identity refused and TLS
verified. No credential, local model, owner accounting ledger or Cloud settings changed.

## Verification and remaining limits

Exact totals, hosted fixture cleanup and browser evidence are in the latest
HANDOVER.md checkpoint. Tests cover all continuation states/no-op repeats, no retry
on provider failures, selected-only refresh/authorization, minimal/optional masks,
map URL validation, normal versus explicit launch, page restoration, provider
credits and occupied-port guidance, alongside the existing full regressions.

Anonymous links remain shareable 30-day capabilities without accounts/revocation.
Transient computation receipts/sessions do not survive backend restart; committed
private saved-plan links do. Original live names/routes were not retained, and
Google coverage/current traffic/actual billable retrieval were not tested. Existing
bounded discovery and tenant/brand/calendar coverage limitations remain. No new
mandatory stops, return trips, journey deadlines or Task 50 security feature is added.

## Subsequent saved-details/performance refinement

[November 1 follow-up](saved-details-performance49.md) supersedes the link/help UI
and generic refresh-limit behavior above. Selected-only/new-tab/security contracts
remain. An automatic-details framework is implemented but stays disabled pending
separate owner billing approval. Local Qwen startup preparation is enabled only
in the ignored owner profile; health stays nonblocking. Ranking is unchanged.
