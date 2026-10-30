# Task 49 — explicit private saved plans

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
traffic, and return no-store. Next proxies only two fixed paths with a timeout;
all SQL credentials stay in Python. Python remains bound to loopback. This is not
a public deployment security boundary: Task 50 must review deployment/auth/write
protection and distributed abuse controls before deployment.

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
Do not store sensitive outing content in this development MVP. Task 50 must decide
authentication/ownership, revoke/rotate/cleanup, secure browser storage, distributed
rate limits, deployment networking, observability redaction and operational role
management. These are documented limitations, not implemented security features.

UUIDs, ordinal stops, optional timing and provider-neutral references remain
compatible with later additive 50A–50E work; no mandatory destinations, return trips,
new deadline semantics or complex journey interpretation were implemented.
