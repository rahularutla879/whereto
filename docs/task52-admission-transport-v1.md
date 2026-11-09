# Task 52B admission transport / atomic-state design v1

**Design only.** No wire receipt field, endpoint, SQL/Redis implementation, migration, account or deployment. [Source compatibility and extraction](task52-source-compatibility-v1.md); [existing internal implementation](task52-validation-admission-foundations.md). This is a proposed application protocol, not a claim of configured cloud guarantees or a current price quote.

## Existing guarantees and limits

`AdmissionRegistry.validate` alone issues internal authority after real legacy validation: fresh complete ordinary request or advanced handoff. Pending effective snapshots get no raw attestation/receipt. Fingerprints bind original input, raw/effective data and policy; the receipt additionally binds complete owned execution payload, process/scope identity, monotonically attempted/issued revision, purpose, absolute 600s expiry and consumed state. Excluded origin/search fields are included. `run` atomically consumes once before callback; copied/forged/cross-registry/cross-scope/stale/wrong-policy/altered payload fails; uncertainty stays consumed. A failed new validation invalidates older revisions. Handoff cannot reserve provider work. Context-local guards are no-ops under default legacy startup.

Process restart loses table/key/object identity: old authority becomes unusable. This is safe refusal, not recoverability. No public clients can claim authority by matching JSON fields. Current default manual generation and legacy pending behavior remain unchanged; they are **not** newly certified trusted interpretation paths. The process registry is an internal foundation only and cannot be deployed as multi-instance authorization.

## Production architecture comparison and recommendation

| Option | Forgery / replay / revocation | Operational tradeoff |
|---|---|---|
| Opaque server-held reference, durable shared authority metadata | Random unguessable reference plus context ownership, SQL atomic consume/revision/expiry checks; one successful claim across instances | DB lookup/transaction per new operation; evidence fetched separately. Minimal public data and easier invalidation. **Recommend.** |
| Signed token plus durable replay/revocation registry | Signature authenticates claims; SQL still required for single-use, current revision, revocation and fencing | Key rotation/audience/version/parser complexity; larger potentially identifying client payload, no avoided safety transaction. No advantage at present. Signature alone is insufficient. |
| Self-contained signed token or Redis-only lock | No durable single-use/revision guarantee in the proposed failure model | Reject as authoritative. Lost consumption cannot restore spent capacity. |
| Existing private saved/option capability alone | Already useful for scoped access/membership | Does not certify a raw graph or authorize unrelated/fresh work; retain and layer purpose checks rather than replacing it. |

Use the **proposed** regional Cloud SQL PostgreSQL operational ledger for authoritative metadata and fencing, consistent with the Task 52 architecture. Use proposed volatile Redis for bounded encrypted request/source/plan evidence and short-lived inventory only. Keep saved plans and their existing Supabase capability/RLS protections separate. No new service purchase is recommended by this checkpoint; provisioning still requires separate approval. A Supabase-only operational authority is a separately benchmarked alternative, not an automatic fallback during SQL failure.

Durable metadata contains opaque context/request/operation IDs, current revision, validated policy/build/schema identity, purpose, keyed payload/evidence digests, fixed expiry, status/fence, reservation references and terminal outcome classification. Never raw text, quotes, coordinates, venue responses or saved-link secrets in that ledger/backups/logs. Keyed digests remain sensitive pseudonymous metadata: retention/access control still required. Volatile evidence uses random references and version/expiry binding, not public stable text hashes. Loss/mismatch of Redis evidence causes refusal/rephrase, never reconstruction of trust from client JSON or a stale SQL digest alone.

Future public transport: a random ≥256-bit opaque handle, redacted from URLs/logs/analytics; delivered only through an approved same-origin server flow and bound to a server-issued anonymous session context (not claimed user authentication). Require existing Origin/CSRF protections, TLS, cookie controls, explicit audience/purpose and request revision. A stolen handle alone must not work in another context. Same-context bearer theft remains a risk requiring XSS/session protection. No predictable request IDs or client-issued nonce can mint authority. Key rotation needs versioned server secrets and safe invalidation; it cannot be modeled by today's process identity.

## Required state machine and atomic operations

These are protocol requirements, not SQL shipped in this task. One reviewed transaction implementation must cover lock ordering, deadlocks, idempotency and retry policy without hidden provider retries.

1. **Begin revision:** lock anonymous request/session authority row; check owner, fixed expiry, active policy/build and monotonic revision. Mark attempted revision before expensive validation. Failed validation does not resurrect an older receipt. Save evidence in bounded volatile storage with revision/expiry; publish no usable capability until evidence and validation are complete.
2. **Issue:** transaction compares current attempted revision, policy and expiry; inserts purpose-bound ready authority with unique opaque-handle digest, payload/evidence fingerprints and immutable validated identity. A concurrent newer revision prevents stale issue. Crash between Redis write and SQL commit leaves only expiring orphan evidence; crash after commit with lost response does not create a second operation or free allowance.
3. **Claim operation:** transaction locks owner/session revision plus authority row in a fixed order; checks handle/context/audience/purpose, expiry with DB time, policy allowlist, current revision, complete payload/evidence binding and existing capability eligibility. Atomically transition ready→claimed using a unique operation ID and monotonic fence. A single winning claim returns server-owned state; losers read status, never dispatch. Repeated POSTs may return existing status/result, not re-consume or resubmit.
4. **Reserve/dispatch:** claim is not spending permission. Use the existing proposed durable provider budget/attempt ledger, same parent outing/context/account quotas, concurrency and hard caps. Before each admitted provider operation check current fence/revision/revocation/date/evidence freshness. Reserve durably and record dispatch intent before I/O. No provider call on failed state read/lock/quota. Revisions cannot reset budgets.
5. **Complete or uncertain:** append provider/result classification, retain attempt/reservation when send may have happened. Worker death after intent is uncertain, not retryable/free. No exact-once external API claim is possible merely from a database transaction. Fenced workers cannot publish stale results; cancellation/revocation stops subsequent dispatch/publication but cannot unsend an already launched call. Provider idempotency may be used only if documented and separately approved; never assume it.
6. **Revoke/expire:** transaction increments revision/fence or disables policy and invalidates unused dependent authority. Absolute request/capability/evidence expiry never slides on edit. Tombstones/dispatch uncertainty remain through their security/accounting retention period; TTL cleanup is not the authorization check. Failover/restart reads durable state; stale Redis caches cannot authorize. No unlocked fallback on SQL/Redis outage.

DB transactions own revision/claim/fence/consumption/revocation, parent accounting and dispatch uncertainty; Redis owns no financial or single-use truth. Redis evidence retrieval cannot be atomic with SQL: bind immutable evidence digest/version, recheck claim/fence around retrieval, refuse if missing or changed. No provider dispatch before durable claim **and** reservation. Integration needs two-worker/crash/failover tests; the offline process tests here do not establish distributed linearizability.

One SQL read/transaction and bounded Redis fetch per operation add latency/operating cost; exact RTT, contention, pool limits and pricing are unmeasured. Reuse the proposed ledger rather than introduce a second database/queue or token service. No five-second performance claim or recurring cost approval follows.

## Issuer / consumer matrix (future design)

| Path | New-work issuer and bound authority | Consumer / limits |
|---|---|---|
| Fresh ordinary interpretation, Journey absent | Complete strict extraction + source/scalar/calendar/manual validation; finite complete unordered absence proof for future V4. Bind source activity occurrences without inventing Journey fields. | Ordinary generator consumes exact request plus confirmed origin/search revision. Manual direct input needs its own deterministic manual-source validation issuer, not an exemption or alleged AI receipt. |
| Fresh advanced interpretation | Validated graph + context may issue **handoff only** even when origin/date/endpoint missing. | Session creation consumes handoff; no provider authority until all required answers and endpoint/date/geographic admission pass. |
| Raw model output | Strict decoder and full selected server policy only | Never public authority by itself. No extra model pass. |
| Matching legacy browser pending snapshot | No fresh raw issuer; retain legacy branch under existing default profile | Future enforced path requires original server-held raw evidence + authenticated pending capability/revision, or rephrase. Never relabel a normalized graph as raw. |
| New clarification answers | Existing pending capability/owner/revision + typed allowlisted answer + deterministic source/manual checks; preserve original unrelated constraints | New revision invalidates previous work authority, keeps budgets and absolute expiry. Answer source provenance is distinct from AI. No extra inference. Ordering confirmation interface remains design only. |
| Advanced continuation | Server session owner/capability, current policy/provenance, validated answer changes, endpoint/date/origin and previous state | New one-operation authority for initial search/route or bounded expansion. Existing token, lock and parent quotas remain; no reset via new child handle. |
| Alternatives/options/discovery | Existing server-owned option membership, opaque capability/expiry, immutable validated request revision; explicit operation kind | Reuse checked inventory where no provider work; new discovery/routing requires a purpose-bound child claim on same budget. Client cannot submit a replacement graph. |
| Regenerate / changed preferences or destination | Validate changed source/manual fields and new request revision | Old authority invalid; no replay of consumed generate. Fixed expiry and spent budgets preserved where operation remains same outing. |
| Origin lookup / area suggestion | Explicit independent user action plus source-bound query and context | Separate bounded lookup/suggestion purpose before route-ready authority; never require a nonexistent full itinerary, infer origin or silently move destination. |
| Contact/details | Existing allowed place IDs/outing capability and one-attempt guards + explicit permitted field purpose | Child detail claim with same provider ledger; no fresh planning graph from place ID. |
| Saved viewing/reopen | Existing private capability, ownership/RLS, expiry and stored-document checks | No semantic receipt, provider call or reinterpretation needed. |
| Save selected server result | Existing server membership/save receipt/access checks | Saves effective result, not original raw-model certification; no new semantic issuer. |
| Saved refresh | Existing private saved access checked on every action, selected real option/fields, explicit refresh action; server creates **refresh-only** claim | No raw-model attestation or new route authority. Preserve action replay protection, saved expiry and shared process/fleet billing/abuse budgets. Fresh per-action outing accounting is not a quota reset; preserve existing intentional per-action bounds. |
| Legacy active sessions/effective snapshots | Explicit version/provenance tag; serve existing permitted cached/view operations until existing expiry | Never upgrade as raw evidence. Enforced cohort blocks new provider work without reconstructable validation/owner revision. No automatic AI call, silent lifetime extension or database migration here. |

Existing advanced/options/save/private-link capabilities remain necessary but purpose-specific. A receipt must not replace their ownership, membership, expiry or RLS checks. Main-form rephrase is the initial safe outcome for unknown ordering; no new user-facing field is implemented.

## Terminal destination contract and reviewed design expectations

These are proposed scoped semantics and acceptance tests, **not runtime fixes**. A terminal visit may overlap a geographic endpoint only after independently establishing identity and occurrence ownership. Neither last list position nor equal display names establish equivalence.

| Source meaning | Required representation / safe outcome |
|---|---|
| “Start with coffee, visit museum, finish at pharmacy” | Three required visits; first/last reachability constraints follow owned global cues, not commas. Pharmacy is final required visit; no extra unknown endpoint just because of `finish at`. |
| “Visit museum, then finish at SUNY College of Optometry” where College is explicitly extracted as a visit | Preserve exact named final visit and order; do not duplicate or demote it. If wording/occurrence cannot distinguish a visit from a separate destination, clarify. |
| “Get groceries, then drive to [named final destination]” as distinct endpoint | Keep groceries and independently grounded terminal destination; verify provider identity before routing, never invent coordinates or drop endpoint travel. |
| “Return to where I started” | Endpoint origin reference, resolved only to the user's confirmed origin; required trip timing includes return where specified. |
| “Return home” / “finish at home” without established home | Unresolved home endpoint; ask where to end. Device/current origin is not home. A later answer may explicitly bind home/origin; no silent assumption. |
| Same named place appears twice / “coffee, museum, then coffee” | Distinct occurrence IDs even if venue identity ultimately equals; museum→later coffee only in this source. Do not merge visits, invent coffee0→museum or infer return. |
| “Pharmacy before bank; coffee whenever convenient” | Required pharmacy/bank/coffee; only pharmacy→bank; convenient is not optional. Optional `maybe coffee` remains optional and independently scoped. |
| Unknown terminal geography, conditional or distant finish cue | No planning-ready endpoint/graph authority; preserve stops and ask a specific rephrase/endpoint question. |

Finish-at clause scope must be independently proved before retiring the legacy blanket endpoint omission check. Current legacy limitations remain; do not claim this document changes live home, return or last-stop behavior.

## Remaining gates and rollback

Complete source-version registry review, literal legacy B–E extraction/equivalence, raw-field/normalization mapping, ordinary absence proof and terminal scope before a test-only enforced profile. Then implement server-held pending/manual/continuation issuers and complete all bypass/expiry/quota tests before public transport. Shared state, migrations and live tests require separate approval. Initially unknowns use rephrase; future occurrence-bound typed confirmation needs single-use pending capability, request revision, ownership, contradiction checks and deterministic no-model validation.

Enforcement rollback revokes affected unused authority and closes new work; it never falls back to known unsafe legacy order acceptance. Read-only saved viewing survives under its existing security policy. Keep the default legacy profile and local shadow unchanged until separately approved rollout gates pass. Gemini HTTP400/IP and Anthropic grammar compilation are unrelated outstanding blockers. No paid evaluation restart is implied.
