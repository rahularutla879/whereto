# Task 52B — local V5.1 manual edits and continuation

Baseline: `e720a458e06afa520d0c3e5ae10878855d7b7e95`. Local bridge identity: `52b-v51-local-manual-pending-v1`. This checkpoint changes only the explicit disposable application fixture and its tests. Production interpretation, generalized ordering grammar, B2 source identities, Qwen, reviewed prompts, evaluation machinery and public DTOs are unchanged.

## Root cause and boundary

The generalized `validate_for_development` intentionally accepts fresh raw evidence only. It refuses pending effective snapshots, manual preferences, current-location claims and clarification answers. The earlier fixture caught that refusal and rephrased. The main form already clears incompatible cards and continuation references through `replaceRequest`, and retains deliberate manual preferences separately through `manualPreferences`. Date and destination can use advanced typed answers; mode/area regeneration can re-enter interpretation with a pending snapshot. No frontend rewrite is needed.

The new `scripts/task52_v51_local_continuation.py` bridges those existing contracts inside `application_fixture` only. It does not alter the fresh-only validator or duplicate its ordering rules. Every usable result re-runs the original generalized proof against the current exact text and the server-owned raw extraction. It never copies a graph out of client pending state or generates a missing edge. New source text must obtain its own fixture extraction, evidence spans and occurrence mapping. The fixture's exact-source lookup supplies fake model output; it is not an ordering gold-answer repair.

## Existing controls and source ownership

Supported manual overlays are date, search area, transport mode and the existing bounded total between-stop travel cap. The bridge calls the existing `resolve_datetime`, `resolve_mode`, `advanced_travel_fields` and `geographic_intent`; it writes effective controls into `InterpretationContext`, not the raw extraction. Named visits, endpoints, stop counts, optionality, ordering, return and whole-trip duration remain owned by the re-proved source. Contradictions and unsupported activity wording cannot be resolved through a date/location answer or unrelated field. Edit the source and submit a new validated interpretation.

Existing `PendingClarification` DTOs remain browser snapshots, never credentials. A bounded process-local cache remembers the digest of each issued typed snapshot, its raw-extraction identity and its original ten-minute monotonic deadline. The digest covers text, graph, answers and reference time. Modified, unknown, expired, cross-source or restarted-process snapshots refuse. Valid answers can add date and location using existing answer fields; a natural-language date requires known calendar context, while an exact ISO date can precede area confirmation; the original request reference time remains fixed. Reissuing a snapshot does not extend its original deadline. The cache holds at most 50 entries, is locked, and is destroyed with the fixture. It grants no planning receipt, user identity, distributed durability or cryptographic certification. Even a matching snapshot must pass renewed source proof and deterministic control validation.

Advanced sessions remain the sole existing orchestration/capability mechanism. A fixture-only wrapper refuses relative advanced date answers while the destination calendar is unknown, without mutating the session; use an exact ISO date or confirm the area first. This guards an existing advanced-continuation limitation without changing production. Origin confirmation, dwell, departure, route choices, date changes and permitted destination answers use the existing typed endpoints. Source edits clear old frontend continuation/answer state. Regeneration receives a new server token; it does not repurpose an old graph or save receipt. Invalid/expired tokens refuse before work. Receipt/access-token/candidate mismatches refuse saving. Existing independently held old bearer capabilities are not proactively revoked by a textarea edit: they still refer only to their old session and expire under the existing policy. Adding cross-request revocation or a public request-revision protocol is outside this local-only checkpoint.

## Supported and blocked workflows

| Action | Local outcome |
|---|---|
| Fresh source, missing date/area | Existing advanced questions; valid explicit controls or issued pending answers retain the graph. |
| Date/area/mode preference change | Re-proof unchanged source; deterministic overlay; existing session and route checks apply. Reuse server-held raw evidence; no model I/O. |
| Changed text/order/optionality | Fresh server-owned extraction and occurrence proof; no old pending graph or advanced answers reused. |
| Confirm return origin or supply visit duration | Existing advanced answers; no second model call, invented point or guessed duration. Unknown timing stays unverified; overrun/unreachable required routes produce no options. |
| Contradictory/ambiguous activities | Clarification, no planning. A corrected supported source is a new interpretation. |
| Activity, time or endpoint meaning through a generic pending answer | Blocked; rephrase the original source. Existing typed advanced departure/origin controls remain available. |
| Manual spending/party/cost changes, current-location-dependent source, unsupported first-limit context | Blocked rather than silently dropped. These are not newly implemented semantics. A source that fails the fresh proof (for example an unlocated relative-date expression or unconfirmed home endpoint) remains blocked even if an override might otherwise help; this bridge does not broaden that grammar. |
| Tampered/expired/unknown/legacy pending snapshot | Blocked; never promoted into raw model evidence. |

The fixture now has 16 authored sources: its original 13 are unchanged, plus reversed-order, optional-to-required and contradiction-correction examples. It remains deliberately finite as a fake provider; the generalized validator is not an exact-request classifier. No grammar was added.

## Presentation and saving

Included optional visits preserve `requirement=optional` and conditional position in the typed options and saved selected graph. Skipping an optional visit preserves required visits and closure, as tested by the existing planner tests. Flexible required visits retain their permitted positions; repeats retain occurrence IDs; named places and origin endings remain exact.

The active `ItineraryStop` component does not currently label included optional attendance. The saved view already labels required/optional visits accurately. There is no disposable-fixture-only display hook, so this checkpoint leaves the production UI unchanged rather than adding a public presentation switch. A future separately reviewed display change can consume the existing typed field without a schema change. No raw response is changed to affect presentation.

Existing receipt selection and save/reopen interfaces use only the selected itinerary. The fixture still uses disposable `MemoryDocuments`; it proves selection/serialization/display, not real SQL transactions or RLS. Unknown current hours, duration and reopened route timing remain explicitly unverified. Synthetic venue names and route estimates are not real provider availability.

## Isolation and verification

Use the unchanged loopback launch commands in the [original local workflow](task52-v51-local-application-integration.md#local-use). Normal app startup never imports the bridge. No HTTP enablement parameter, model factory, credential loader, real transport, real database connection or financial authority was added. The fixture owns a fresh default `ProviderBudget` for its lifetime and restores the previous object afterward; it never resets a running session's allowance. This fixes test-context budget leakage. Request and advanced fixture calendar clocks now use the same timezone-aware reference; monotonic expiry, quota and billing clocks remain independent.

Automated checks use actual Next interpretation/persistence proxies, FastAPI middleware/endpoints, existing sessions/planner and save service with synthetic evidence. They cover pending date/area answers, walking regeneration, text and optionality edits, stale source/graph/raw/reference rejection, capability expiry, mismatched selected saves, contradiction correction, return confirmation and dwell timing. The original 12 generalized-ordering tests remain intact.

Actual browser checks separately covered missing context followed by simultaneous date/area edits, changed-text card invalidation, reversed activity order, walking preference regeneration, mobile optional-to-required source change, selecting/saving/reopening one itinerary with both visits required, contradiction clarification and a corrected-source plan. Desktop 1280 and mobile 390 were checked; mobile document width matched viewport width. No Maps link or current venue-detail refresh was opened. These observations do not claim every automated negative was browser-tested.

Final relevant backend runs: 239 tests (212 passed/27 opt-in skips) plus 82 lifecycle/calendar/edit tests (81 passed/one opt-in skip), zero failures/errors. The original 12 ordering, nine new manual/pending and seven application-fixture methods passed. A final 239-method and four-application-boundary rerun passed after the unknown-calendar answer guard. All 34 exact previously incomplete historical methods completed successfully over two rounds of bounded isolated batches; none remain incomplete in that recorded set. Frontend 289 passed; TypeScript, lint and production build passed. No full-backend discovery rerun is claimed.

See [versioned verification](task52-v51-manual-pending-verification.json) for exact test IDs/counts, source hashes and unchanged journal evidence. Earlier failed fixture assertions and misspelled targeted module names were corrected; no historical test or expected source outcome was weakened. Full application backend discovery was not rerun; relevant suites and the exact previous 34 historical simulations were tested separately in bounded batches. A full-suite pass is not claimed from partition evidence.

## Remaining approval gates

Production V5.1 remains disabled. Independent source/response review, production enforcement and admission design approval, broader manual/pending semantics, optional-attendance presentation, and any incomplete historical regressions remain separate activation gates. The local provenance cache is not suitable for multi-instance/restart-durable authorization. All paid permissions, real operator enrollment, fresh provider readiness and same-journal execution remain unauthorized. Task 53 remains unstarted.
