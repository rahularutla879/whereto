# Task52B validation and admission foundations

Version `52b-validation-admission-foundations-v1`. Started clean `6a6f1994c1a1cb96810fd000b49bec6433568be0`. **Partial phase extraction at the smallest verified boundary; no Ordering V4 enforcement.** Active legacy behavior, Qwen settings/prompt, canonical model schema, Hitech/HITEC correction and every historical evaluation artifact remain unchanged. No provider/counting/Maps request, credential/billing/quotas change, deployment or database migration.

[Verification](task52-validation-admission-verification.json), [prior enforcement design](task52-ordering-enforcement-design.md), [foundation contract/tests](../backend/planning_admission.py), [phase adapter](../backend/validation_phases.py).

## Delivered phases and the explicit stop boundary

The authoritative 66-case corpus pins exact `backend/journey.py` and `backend/interpretation.py` source bytes, along with four other sources. Editing their mixed internal checks would invalidate the current historical compatibility contract. Neither those pins nor the corpus, historical scores or paid configuration were rewritten. No copied validator, dynamic source-code transplant, monkeypatch-based production fork or skip-validation switch was introduced.

| Requested phase | Implemented boundary |
|---|---|
| A — strict model parsing | Existing provider JSON/duplicate-key parsing stays unchanged. New `strict_extraction` reuses the same `Interpretation.model_validate` schema and captures a private pre-legacy snapshot. This is parsed canonical data, **not a claim of original provider wire-byte capture**. |
| B — source/occurrence preparation | Retained inside the pinned interpreter/journey implementation, in its original order. Not independently extracted yet. |
| C — non-order source validation | Same pinned source checks, no duplicate implementation or bypass. Not independently extracted yet. |
| D — selected ordering behavior | Only `legacy-pinned-52b-v1` is accepted. Existing normalizer/cue checks remain authoritative inside the atomic phase. No V4 profile is available. |
| E — calendar/endpoint/duration/manual checks | Same pinned implementation and existing public planning expiry checks, in the same sequence. Not independently extracted yet. |
| F — final disposition/admission | New `LegacyDisposition` preserves the unchanged result, immutable parsed snapshot, evidence origin and phase labels. Explicit `AdmissionRegistry.validate` can issue internal ordinary/handoff authority after this validated disposition. |

`backend.main.interpret_outing` uses `interpret_legacy_result` inside its existing shadow wrapper. The adapter lazily calls the same provider once, passes its original object to the original interpreter, and returns exactly its original result structure. It respects dependency-injected/fixed-clock interpreter operations, preserves exception classification and does not create a registry by default. No extra response fields or new questions. A raw snapshot is immutable canonical JSON bytes; `raw_model` returns a fresh typed copy, so an observer cannot change that stored snapshot. Snapshot/request data is transient, never operational logging or persistence.

`PHASES` deliberately reports `strict_extraction → legacy_source_order_calendar_atomic → final_disposition`. It does **not** pretend that B–E are independent validators. This is the authorized stopping boundary: a full internal phase split still needs a separately reviewed source-compatibility/version strategy that preserves historical validators and current corpus checks. The new modules provide no alternative semantic interpreter.

## Server-owned receipt contract

No registry is globally installed and no public API accepts a new receipt or selects this foundation mode. The contract is usable only by explicit trusted Python/server callers and tests. `require_foundation_for_test()` is a ContextVar scope, not an environment flag, frontend setting or V4 enforcement option.

`AdmissionRegistry` uses a locked process-local table of at most 50 entries, identity-checked opaque `AdmissionReceipt` objects, a random per-registry HMAC key and canonical request fingerprints. Internal objects have non-data-bearing representations; handles, raw text, origins and hashes are not logged or returned in diagnostics. Public models still reject `admissionReceipt`, `validated` and `orderingProfile` fields.

Binding includes:

- A registry-owned request/session scope, original source/input and captured fresh extraction, effective validated result and exact legacy policy version.
- Strictly increasing attempted and issued revisions. A stale revision/capacity failure rejects **before** model work. Starting a new revision invalidates old authority even if the new validation fails; no automatic retry/restoration.
- Required/optional occurrences, original/effective ordering, destinations, endpoints/return requirements, dates, timing, travel and manual preferences through the keyed evidence fingerprint.
- The exact owned execution payload. `_plain` includes **all declared model fields, including excluded origin/search/reference fields**; public `model_dump()` redaction cannot omit them from integrity binding.
- Registry/scope/receipt object identity, purpose, expiration, invalidation and a consumed flag. Matching client JSON or a copied/foreign receipt object is insufficient.

The scope has an absolute **600-second monotonic lifetime**; revisions do not extend it. In-flight validation plus retained entries share the 50-entry bound. Live entries and replay tombstones are never evicted to gain capacity; expired entries are cleaned. A new scope does not reset any provider quota, cost ledger or request admission.

`run` verifies binding under a lock and consumes the receipt before invoking work. It gives the trusted callback an owned copy, not the caller's mutable candidate. Concurrent consumption permits exactly one callback. Timeout, callback failure and uncertain completion retain consumption. Revocation, expiry, new revision, late inherited async contexts and mutation of the owned payload block subsequent provider reservations. Calendar freshness is independently rechecked in the selected ordinary foundation path before provider accounting. An already admitted in-flight provider call is not refunded/retried on expiry.

### Two distinct purposes

- **Ordinary legacy validation:** only fresh model provenance plus a complete legacy `PlanningRequest` without issues can issue ordinary authority. Optional server-supplied execution fields are restricted to the existing origin/search controls and are validated as `PlannerInput`; they cannot override stops, date, ordering or budgets. The receipt binds the exact provided context. Existing origin confirmation/geography/routing feasibility checks remain required; a receipt is necessary foundation evidence, not permission to skip those checks or claim V4 semantic correctness.
- **Advanced handoff:** only the existing `advanced_unavailable`/`LIMITATION` disposition with a journey/context can issue a handoff receipt. It can create that server session; it **cannot reserve searches, routes or details**. Missing date/origin/endpoint questions remain unresolved exactly as before. Provider-ready advanced continuation authority is not fabricated from the handoff.

The only issuer entry point executes actual legacy validation. It accepts no alleged validated-result DTO or client `is_valid` flag. Browser pending inputs produce `source_kind=legacy_effective_pending` with no raw snapshot/receipt and no extra AI call. Ordinary fresh outputs may themselves contain a legacy pending snapshot for later browser reuse; that does not make the saved copy raw evidence on a subsequent call.

This is internal server-code trust, not protection against arbitrary Python code execution, authenticated user accounts, wire-ready tokens or distributed durability. Raw evidence is captured after the existing provider parser; original wire formatting/omitted-field metadata is not newly preserved by this adapter. The legacy policy can still accept its known unsupported ordering edge; a legacy receipt never means V4 ordering-qualified.

## Planning admission matrix

All new guards are **no-ops in normal legacy startup**. Existing checks remain authoritative and run unchanged. The table distinguishes current authority from the explicit foundation test scope. No receipt is added to pure saved viewing or existing save consumers.

| Entry point / new work | Existing authority and expiry | Foundation boundary and remaining work |
|---|---|---|
| `/api/interpret`, `main.interpret_outing` | Request/inference admission, strict parser, existing legacy source validation. | Phase adapter captures fresh provenance; public response unchanged. It does not expose or automatically issue receipts. |
| Clarification/pending followup | Browser state revalidated by pinned interpreter; `referenceTime` is a calendar anchor, **not an authenticated capability TTL**. No extra AI for matching pending. | Explicit registry returns no receipt for legacy effective snapshots. Server-owned pending migration and typed confirmation remain future work. |
| Initial ordinary `/api/plans/generate` → `real_plans` | Validated DTO, date/time expiry, mode/origin confirmation, geography, existing provider budget. | `guard_ordinary` matches the exact owned request in selected scope before creating outing/session work. Default manual/legacy request behavior is unchanged and is not relabeled trusted AI/V4 validation. |
| Alternatives/discovery `/api/plans/options` → `more_real_plans` | Opaque option capability, strict 600s lifetime, immutable context/mode, lock, calendar freshness and shared budget. | Selected scope fails closed after capability lookup and before context mutation/new work. No issuer promotes old option contexts to raw proof. Normal continuation remains unchanged. |
| Regeneration/retry in frontend | Existing interpretation/pending and origin preparation, request cancellation/duplicate controls; no financial reset. | A server caller would need a new validated revision, not reuse a consumed receipt. No automatic retry or new frontend field was added. |
| Advanced `Sessions.create` | Enabled local advanced gate plus eligible legacy interpretation/context. 50 sessions, 600s lifetime. | `guard_handoff` checks matching owned text/result/preferences before constructing a session in selected scope; clarification/noneligible results retain their no-session behavior. |
| `/api/plans/advanced` → `Sessions.run`/`Session.run` | Existing private token, 600s expiry, session lock, date/origin/mode/endpoint checks and server resolver/router. | Selected scope fails closed at `Session.run` before edits/state/provider work. A handoff receipt is not continuation authority. A provider-ready continuation issuer is deferred. |
| `/api/starting-places` | Explicit local lookup gate/query, same process budget, finite 3 matches/no pagination. | Selected scope defers this independent manual action before outing reservation. It needs its own explicit source authority later; an ordinary receipt cannot be borrowed. |
| `/api/starting-areas` | Explicit suggestion query, stored reference capability, budget/routing checks; reference expiry remains 600s. | Selected scope defers before discovery; no hidden reference lookup or origin inference. |
| `/api/venues/details` | Allowed IDs bound to existing outing capability, 30min expiry, duplicate attempt protection and original budget. | Selected scope defers before marking a detail attempt. It cannot mint fresh planning authority from a venue ID. |
| `/api/plans/refresh` → `RefreshSessions.refresh` | Reopen/RLS/private-link/DB expiry on **every action**, selected real option, feature gates, action replay registry (30min/512 entries), shared quotas. | Selected scope defers after existing saved authorization/selection checks and before action bookkeeping/provider work. Unauthorized links still fail existing authorization first. No new semantic issuer from saved data. |
| `/api/plans/save` | Existing 600s save receipt/access binding, selected IDs and ownership/DB constraints. No venue lookup in save. | No new semantic receipt requirement. Saving does not retrospectively certify the source graph. |
| `/api/plans/reopen` / saved viewing | Existing private capability, database ownership/expiry and stored-document validation; no provider work. | No new guard. Viewing remains available under existing rules. |
| All discovery/Routes/Details internals | `OutingBudget.reserve` / `reserve_matrices` before authentication/I/O, full-cell quotas, durable development accounting where enabled, concurrency/zero retries. | `guard_provider` at shared `_reserve_batch` is a final selected-scope barrier before counters or billing reservation. Ordinary bound lease required; handoff/missing/expired/mutated authority rejects. All existing budget checks still run afterward. |
| Frontend Next proxies / worker execution | Existing body/host/origin guards and forwarded safe DTOs. `run_work` copies ContextVars into its worker. | No new public payload/flag; JSON claims of authority remain invalid. Copied lease contexts are marked inactive when the operation ends, so late work cannot reuse them. |

Direct transport functions are trusted internal implementations, not public APIs; they must continue to be called through the existing budgeted services. This foundation does not claim to sandbox malicious server Python callbacks. Selected-scope deferred paths are conservative test barriers, not a partially enabled production enforcement profile. Their valid new-work issuers and public receipt transport are intentionally unimplemented.

## Compatibility and verification

The pinned B–E implementation is unchanged: ordinary no-Journey extractions still work; raw captured results cannot change legacy normalization; all 25 journey fixture results and provider-call counts compare exactly against the previous direct interpreter. Binary/three-stop start/finish still has the known legacy graph-deletion/endpoint-omission limitations. Home remains distinct from origin unless explicitly established. No new ordering questions, confirmations, model defaults, place substitutions or geographic aliases were added. The Hitech/HITEC correction is unchanged.

New foundation tests cover fresh ordinary/advanced purpose binding, immutable snapshots, pending/no-authority outcomes, forged/copied/client handles, wrong policy/revision/session/registry, modified stops/order/date/destination/origin/search settings, absolute expiry/revocation, concurrent single consumption, capacity rejection before model work, failed validation invalidation, callback uncertainty, orphan async context, calendar expiry, quota preservation and all deferred public-work families. A valid ordinary receipt also drives full fake three-stop planning with the original accounting.

An isolated browser/API smoke used fixed clocks and fake providers: interpretation 200, planning 200, three provisional options; one fake model call, three fake searches and three fake Matrix calls. A forged client admission field returned 422 with **no added calls**. This used fictional origin/venues and the real interpretation/generation HTTP boundaries, not the owner's existing outing, live Qwen or real Maps availability. Temporary fixture server was stopped. It is not a full interactive main-form or hosted-browser test.

Final complete backend/frontend/order/source/session/persistence/date, TypeScript/lint/build, security and replay checks are recorded in [verification](task52-validation-admission-verification.json). There are no skipped cases added for this task. Full backend discovery is required because runtime foundations changed. Earlier failed/final verification artifacts are retained historically.

## What remains before V4

1. Review a source-compatibility/version manifest strategy preserving the existing six corpus source pins, gold expectations and old validator behavior. No source-pin bypass or paid-journal migration is acceptable.
2. Extract B/C/D/E inside the interpreter/journey under that reviewed compatibility contract, preserving legacy sequence and errors. Only then can the future profile replace no-cue deletion, cue-only edge acceptance and overlapping arrow/omission checks as a single authority. Do not run legacy normalization after V4.
3. Scope final-visit versus endpoint semantics using occurrence ownership, preserve raw→effective index mappings, and implement the finite ordinary no-Journey absence-proof adapter. This task does not claim those legacy correctness limitations fixed.
4. Implement receipt/provenance transport and server-owned pending/advanced/options/manual/saved-refresh revision handling, with existing capability/expiry/security protections. The current internal opaque objects are not public bearer tokens and cannot work across processes.
5. Typed occurrence-bound order/no-order confirmations remain **design only**: source/request revision, question nonce, expiring single-use capability, contradiction/replay checks and atomic revision updates, no additional AI. Do not reuse activities/endpoint answers for ordering.
6. Keep V4 shadow default-OFF and enforcement unavailable until separately approved full outcome/security/rollout tests. Rollback must stop enforced new-work admission, not fall back to the known unsafe legacy graph behavior. Existing saved pages remain viewable; no database migration now.

Process-local registry/key/object identity deliberately fails closed on restart or another worker. It is not a shared-state production solution. Multi-instance use needs atomic shared revision/consumption/revocation/expiry and a separately reviewed authenticated wire format; no cloud database or hosting was provisioned here.

## Paid evaluation and safety boundaries

Original paid journal/root/ten rows/corrections/configuration and all 324 private files remain byte-identical; V4 halt is intact. OpenAI 7 / Google 2 / Anthropic 1 = 10/594, 584 remaining. Accounted $0.047366625; remaining $11.952633375. Keep $12/594/198/12k-input/2k-output/concurrency-one/zero-retry limits. No new paid journal, slot, approval, refund or counting/inference request. Gemini's two Developer API 400s/IP restriction and Anthropic's grammar-compilation blocker remain independent. No model/prompt/provider/billing/quota/credential change, cloud provisioning, hosted migration or Task 53 work.
