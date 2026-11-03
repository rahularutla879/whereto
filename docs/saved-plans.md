Current Task 50E adds optional app-owned advanced `routingPolicy` (`traffic_aware_current`/`walking`) and `departureNow` intent metadata. Missing legacy fields mean the historical policy was not recorded, never retroactive traffic awareness. “Now” is historical on reopen; no live instant, Google route values or precise origin is persisted. Saved zero counted time explicitly does not establish actual visit duration. Existing selected-only v1/v2 private links, 30-day expiry, restricted identity, forced RLS and verified TLS remain. [Hosted/browser verification and exact cleanup](task50e-consolidated.md).

Task 50E refinement: saved-v2 optional fields preserve original Journey, effective visit overrides, explicit departure provenance and entire-outing/travel-only scope. Legacy v2 defaults to entire-outing; v1 remains supported. Provider evidence/private origins are still excluded. Hosted tests verify committed selected-only overrides and separate-process reopening, with exact disposable cleanup. [Evidence](task50e-followup.md).

> Current Task 50E: approved local website and version 2 saving integration is implemented. Initial milestone descriptions below are historical; see [current flow, gates and limits](advanced-integration.md).

> Current Task 50 security audit and acceptance: [safe database access](database-security.md). Earlier task-pending statements below are historical.

# Task 49 — explicit private saved plans

> Latest November 1 refinement: [shared-link admission, official websites and UI verification](sharing-ux49.md) supersedes the six-per-capability session and homepage diagnostics descriptions below. Automatic Pro remains owner-approved local only.

Task 49 implements local-development saving/reopening; Task 50 and 50A–50E are
outside this change. Ordinary generation never depends on a database connection.

## HTTP and trust boundary

`POST /api/plans/generate` and `/api/plans/options` add `saveReceipt` and
`saveAccessToken` only for savable results. Both are independently generated with
Python `secrets.token_urlsafe(32)` (256 random bits). The bounded locked receipt
registry retains at most 100 minimized snapshots for ten minutes. Eviction,
expiry, process restart or another worker means generating again before saving;
it never falls back to accepting a client snapshot. Issuing receipts does no SQL.

`POST /api/plans/save` accepts exactly `{receipt, accessToken, candidateIds,
selectedId}`: three options maximum, four stops per option, bounded candidate IDs,
strict token syntax, no unknown fields. Selected IDs must belong to the exact
server receipt, and the access token must match its server-issued verifier.
Clients cannot write a plan body, ranking, geographic verification or route claim.
The client-selected itinerary and option ordering are saved explicitly. One
immutable save per receipt; retries keep the same token/selection. The frontend
locks selection after submission to avoid changing an uncertain committed save.

`POST /api/plans/reopen` accepts exactly `{accessToken}`. There is no list, update,
delete or UUID-based retrieval API. Missing, inaccessible and expired links share
one 404. Malformed requests get bounded 422s; conflicts/expired receipts get 409;
streamed payloads above 4096 bytes get 413; fixed credential-free outage messages
use 503. Both Next and Python bound bodies, reject public/forwarded/cross-origin
traffic, and return no-store. Next proxies only fixed save/reopen/refresh paths with a timeout;
all SQL credentials stay in Python. Python remains bound to loopback. Public deployment requires a separately scoped
review of networking and distributed abuse controls; Task 50 preserves this
local-only architecture.

## Five-table mapping and transaction

The Task 48 migration is unchanged. Additive `0002_private_saved_plans.sql` adds
hashed access verification, save fingerprint, 30-day access expiry and selected
option to plans; a small preferences object to constraints for existing optional
legacy people/budget/cost fields and user-authored origin wording; fictional
snapshots/metrics on stops/itineraries. No Google response blob column is added.

`backend/saved_plans.py` maps normalized date, timezone, location intent, activities
(including repeated/custom activities), activity intents, time window, explicit
flags, transport, Strict/Flexible preferences, inclusive/exclusive maxima, total
inter-stop limit, geography requirements, access/availability requirements,
revisits and dinner indexes into existing named columns. Optional legacy ranking
preferences are retained, not used as real-provider verification. Original raw
prompt is intentionally omitted. Provider-resolved destination context, device
coordinates, exact starting place and ephemeral continuation/details tokens are
not retained. Search radius/location-first tuning and novelty history are transient, not saved constraints. Origin-based plans label their missing first-leg information;
request limits are preserved without claiming origin/geographic re-verification.

One Psycopg connection/context owns all five table inserts and closes on success
or exception. SQL values are parameters; only constant allowlisted identifiers
are composed using Psycopg SQL. A transaction-scoped advisory lock plus a unique
SHA-256 access verifier and a minimized-document fingerprint serialize repeated
submissions. A duplicate returns success only for the same immutable document;
a changed selection cannot overwrite it. Any stop/source/constraint failure rolls
back the entire write. A lost commit response can be retried with the same receipt
and capability while that receipt remains valid; after expiry, reopening the
retained link establishes whether it committed. The frontend retains the token
in memory for retries; browser storage is written only after confirmed success.

Reads run in a read-only transaction, order by explicit option/stop positions,
check contiguous order, complete membership, source modes, selection and Pydantic
contracts, and reconstruct an independent saved document (version 1). No generator
or provider is invoked. Invalid/incomplete records are unavailable, never silently
replanned. Expired outing dates remain viewable; link expiry is separate.

Connections use the existing verified TLS CA/hostname settings, five-second
connect/query and two-second lock timeouts, no automatic retries, and a four-slot
nonblocking process connection guard. Each transaction scopes its access verifier
with `set_config(..., true)` so it cannot leak into a pooled session. Runtime
identity must be the separate non-owner/NOBYPASSRLS role. RLS traverses each child
to a plan whose hash matches the current capability and whose access is unexpired.
The role can only SELECT/INSERT product rows: no ledger, updates/deletes or DDL.
Database failure never changes or removes generated/saved UI content.

## Retention, provenance and display

Official policies rechecked for this task:
[Places policies](https://developers.google.com/maps/documentation/places/web-service/policies),
[Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id),
[Routes policies](https://developers.google.com/maps/documentation/routes/policies).
They exempt Place IDs from caching restrictions. We retain **only** those Google
identifiers and app-owned provider/kind/unknown-status provenance. Google names,
addresses, coordinates, ratings/counts, URLs, opening hours, photos, contacts,
prices, attribution payloads, Routes Matrix results, durations/distances, derived
scores/classifications, generated descriptions and verification claims are not
stored. Provider observation timestamps are not invented. Saved Google references
are labeled Google Maps; name/details/routes remain unavailable. Deleted or stale
Place IDs do not prevent viewing original ordered activities. There is no live
refresh button in Task 49 and no automatic Google request on open/refresh. A future
intentional refresh must preserve the original plan even if refresh fails.

Fictional mock names/neighborhoods/prices, planned timing and inter-stop metrics
are retained as server-authored fictional snapshots, independently of later catalog
changes. They are visibly labeled fictional, never live prices/availability. UI
uses a separate minimal saved-plan representation; live three-card pagination and
exploration remain independent and unchanged.

## Anonymous capabilities and limits

Links use `/#saved=<token>` so tokens stay out of HTTP paths/query/access logs and
ordinary Referer headers. The page imports and clears the fragment with
`history.replaceState`; the document sets a no-referrer policy and persistence responses specify no-referrer/no-store. The
database stores SHA-256 verifiers of high-entropy random tokens, not plaintext
capabilities. Request bodies must never be enabled in application/proxy/analytics
logs. Server receipt state retains a verifier, not a plaintext access token.

A link grants read access to anyone who possesses it for 30 days. This is not
identity, ownership or an account. The browser remembers only the last saved token
in localStorage; an explicit **Forget on this device** removes that local copy,
not other copies. XSS, browser extensions, shared devices, clipboard syncing,
screenshots, copied URLs and browser history/sync can leak capabilities. Fragment
clearing reduces exposure but cannot guarantee history erasure. No revocation or
regeneration API exists: new generation/save creates a separate link and does not
invalidate the old link. Expiry denies reads but does not purge stored rows/backups.
Do not store sensitive outing content in this development MVP. Future deployment work must address
account needs, revoke/rotate/cleanup, browser storage, distributed
rate limits, deployment networking and operational role
management. Task 50 audits current anonymous authorization and observability redaction. These are documented limitations, not implemented security features.

UUIDs, ordinal stops, optional timing and provider-neutral references remain
compatible with later additive 50A–50E work; no mandatory destinations, return trips,
new deadline semantics or complex journey interpretation were implemented.

## Acceptance fixes after Task 49

The owner's FastAPI process had all database settings, but sourcing
`backend/.env.database` selected the migration administrator. Task 49 intentionally
refused that identity; the proxy reduced the cause to a generic 503. This was not a
Supabase outage or a rejected Google-shaped plan. Authenticated read-only TLS and
migration/RLS verification passed. Both mock and actual planner-produced,
sanitized provider-fixture shapes were subsequently committed/reopened through the
restricted login without changing SQL grants, RLS, TLS or migrations.

`backend/persistence_config.py` now honors an explicitly supplied restricted
runtime environment. When the existing administrator-style `postgres.*` environment
is present, it reads **only** the already provisioned `backend/.env.persistence`
for application SQL. It never connects as administrator or uses SET ROLE to make
that connection acceptable. The file must be an owner-controlled regular file,
not a symlink, at most 4096 bytes, with no group/other permissions. A small
allowlisted assignment parser reads it without executing shell. An ordinary
unconfigured startup never reads it or connects automatically. Explicit restricted
settings win, including bad credentials, so failures cannot silently fall back.
No password or credential was changed by this fix.

Save failures no longer publish a candidate link or replace the last confirmed
link. Success requires both HTTP success and `saved: true`, emitted after commit.
A lost response is retried with the same receipt/capability/selection; a new link
is offered only after confirmation. A remembered link may belong to an earlier
successful plan; a link created by the old failed-save UI may have **no database
record** and cannot recover a never-committed itinerary. Generate/save again for a
new confirmed link. Existing committed capabilities remain compatible.

The page now handles initial fragments and `hashchange` navigation in the same
tab. It captures the token before clearing the fragment; malformed fragments show
an explicit error rather than silently opening a different remembered plan.
Second-tab, refresh and backend-restart retrieval were tested for actual hosted
records. Invalid/expired/missing references remain indistinguishable at SQL/API
access boundaries and cannot reveal other plans.

Errors now carry a fixed category and safe correlation ID through Python and
Next: missing runtime config, wrong role, rejected login, connection failure,
access denial, save validation, transaction failure, unavailable link and internal
application error. Server evidence logs only reference/category/operation/exception
class; no SQL, exception strings, configuration, request bodies or tokens. A
malformed successful planner response is classified as an application error rather
than falsely calling the backend unavailable. See HANDOVER.md for exact checks.


## Saved cards and explicit current venue details

Reopened options now replace the demo/generated cards in the main results area. Save/link management follows the cards. The compact private link interface has Copy feedback, Open and collapsed Forget/help. `POST /api/plans/refresh` verifies the existing capability and original option before sequential, bounded Place Details Pro reads. Current names/addresses/status/credits stay in browser memory only; saved structure and SQL never change. No automatic provider request on reopen.

[Exact architecture, evidence rules, fields, billing, limits and verification](acceptance-refinements.md).


## November 1 — final Tasks 46/49 acceptance repair

Current behavior supersedes earlier automatic/all-option saved-view descriptions: normal visits keep saved links collapsed, explicit private links render only the selected detailed itinerary, and Open saved plan opens a secure new tab. One explicit selected-stop detail load uses the existing Pro mask with Maps URI; optional phone/website fields require deliberate existing Enterprise contact opt-in. Provider content stays in memory. Structured continuation states distinguish combinations, discovery, bounded exhaustion, limits, constraints and pending routes; ranking is preserved. Actual default-port startup was checked, and occupied backend ports now give actionable guidance. No migration, role/RLS/TLS/quota change or later task. See [the final repair report](final-acceptance49.md) and the latest HANDOVER.md evidence.

## Latest acceptance: current details and simpler links

The current selected-only detail UI now has compact link management and a collapsed
Reopen another saved plan input; duplicate raw URL/help fields are removed.
Automatic current details on explicit navigation have a **separate default-off**
local policy, not implied by manual refresh authorization. The owner separately
approved and enabled it in the ignored local profile November 1, 2026. Only selected stops use the existing Pro fields,
with all shared quotas/ledger safeguards and no permanent Google content.
Whole-action replay prevention and specific capability/minute/Cloud/auth/accounting
errors replace generic enrichment-limit explanations. Known local reset estimates
re-enable a button only; they do not schedule provider requests. See
[exact fields, limits, costs and tests](saved-details-performance49.md). Earlier
statements that there is no refresh describe original Task 49, not later acceptance.

## Current sharing and contact behavior

A fresh explicit open/update permits at most four unique selected stops. The old six-per-link session no longer limits friends cumulatively. Hashed capability/action replay metadata expires after 30 minutes; shared ten/minute, concurrency-one, ledger and Cloud quotas still apply. Plan retrieval is independent of enrichment. Only explicit Enterprise loading requests phone/website; safe provider-returned HTTP/HTTPS official sites and phones display independently. No provider content is persisted. [Exact limits, tests and caveats](sharing-ux49.md).

## November 2 — saved travel-mode preference

New plans store driving/walking as app-owned configuration in the existing `transport` column. Old null/missing values default to driving on read; no owner row is updated. Other legacy mode labels are preserved as original preferences, not converted into driving estimates. Google route content is still excluded; current Details loading, selected-only view, links, expiry, restricted identity and forced RLS are unchanged. Hosted rollback tests and an exactly cleaned committed browser fixture verify walking persistence; no migration.

[Acceptance details and evidence](ui-travel-mode49.md).

## November 2 — regeneration and hours preparation acceptance

The confirmed-save interface has one heading and one expiry/sharing sentence; prior links remain distinguishable after another save fails. Copy/Open/Forget share an accessible wrapping action group. Collapsed Saved preferences formats the existing constraints and explicit/default time flags, preserving exclusive limits and mode. Contacts use the same opt-in mask with simpler wording. No SQL or retention change. See [acceptance record](regeneration-hours49.md).

## November 2 — Text Search hours and capacity acceptance

Saved intros no longer mention API quota. Central casing preserves brands and provider names. Separately approved WHERETO_SAVED_HOURS_DEV enables the explicit Load opening hours action for at most four selected references using Details Enterprise and the server-loaded original saved date/window. Automatic opens remain Pro-only. Hours-only updates preserve independently timestamped contacts/names in page memory. Current/typical/unknown hours display beside each stop; nothing is stored in SQL or browser persistent storage. See [acceptance and capacity report](hours-capacity49.md).

## Task 50A — interpretation remains transient

Complex interpretation fields and `context` are not added to saved-plan DTOs or
SQL. Unsupported advanced requests produce no resolved planner request or save
receipt. Existing ordinary saved plans, selected options, RLS and restricted/TLS
connections remain unchanged. Original requests, precise home references and
coordinates are not newly persisted. Advanced persistence remains Task 50E.


## Task 50E — advanced application integration

Task 50E adds SavedDocument version 2 for selected advanced options using existing tables/permissions, app-owned requirements and permitted Place IDs. Current venue refresh stays independently authorized; discarded historical route evidence is never reconstructed. [Contracts, limits and verification](advanced-integration.md). Earlier task-pending statements above are historical. Task 51 remains unstarted.


## November 3 — Task 50E acceptance repair

The owner-reported ordinary interpretation and advanced UI regressions are repaired. Both paths share the original form/card/history/save controls; advanced actions now support bounded combinations, same-area discovery and explicit scoped travel exceptions. Required identities, ordering, returns, whole-trip timing, original budgets and private persistence protections remain enforced. No migration, profile/Cloud/billing/model change or Task 51 work. [Root causes, parity, bounds, evidence and remaining limits](task50e-repair.md). Earlier one-page limitations describe the original checkpoint.
