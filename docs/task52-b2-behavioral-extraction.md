# Task 52B B2 — approved behavioral reconstruction and duration extraction

Baseline clean `2fec366463a255efd5e96286e6250f7452b0cf49`. Owner approved a separately labeled current-runtime behavioral reconstruction in place of exact historical environment execution for this checkpoint. **No historical validator source was executed.** The earlier exact-environment preflight remains unchanged and blocked; it is not bypassed or repurposed.

Reconstruction identity: **`52b-behavior-reconstruction-duration-b2-v1`**. Runtime identity: **`52b-runtime-phase-b2`**. [Frozen pre-edit evidence](task52-b2-behavior-baseline-v1.json), [runtime manifest](task52-runtime-phase-b2.json), [verification](task52-b2-reconstruction-verification.json).

The reconstruction is current-runtime behavioral evidence, not a byte-identical historical interpreter/dependency environment, replacement evaluator, new accuracy claim, planning receipt or permission for paid inference. All four prohibitions are explicit in the baseline artifact. Original paid configuration/response hashes, classifications, source pins and corpus remain untouched.

## Exactly one mutating fragment

`backend.journey.normalize_explicit_durations(raw, guarded, journey)` is now a thin compatibility delegate to `backend.duration_preparation.normalize_explicit_durations`. Its original public signature/docstring and its call **after reference normalization and before legacy edge/source checks** remain. No caller, error handler or downstream validator moved.

The algorithm body was relocated without changing conditions, branches, assignments, source text, length/bounds checks or relation handling. Global references are qualified through the live `backend.journey` module, including `re`, `DURATION_WORDING`, `duration_value`, `duration_relation`, `unresolved_return_clause` and `Duration`. This preserves late lookup and existing test/user-code helper patch semantics instead of capturing eager aliases. A static AST test removes only the module qualification/import and verifies the relocated body against the retained source **as data**, without executing it.

The helper fills an absent existing stop's `duration` or absent `journey.total_duration` from the same guarded/source clauses. It does not overwrite conflicting existing values, add/remove/reindex stops, alter optionality/identities/order/endpoint, or guess competing associations. Exact/minimum/maximum/under/approximate relations, whole-trip return wording, travel-only masking, invalid/negative/fractional/oversized numbers, source length limits and ambiguous repeated stops preserve their old handling. It returns no clarification itself; unchanged later validation/classification decides the result. Dynamic helper/constructor errors retain type, message, mutation state and precedence.

Unrelated reference/travel normalizers, `interpretation.py`, canonical schema, Qwen/prompt/model settings, source grounding, ordinary/advanced/saved/expiry behavior, Hitech/HITEC geographic rules and unknown-destination-timezone clarification are unchanged. Only the runtime identity constant in `source_preparation.py` advances to B2; prepared-record type and mapping algorithm remain B1. Existing admission evidence automatically binds that new runtime ID through its existing import; no new admission issuer or transport was added.

## Evidence frozen before editing

Before changing runtime sources, the approved current B1 environment produced the new baseline artifact:

- All **75 frozen interpretation traces** matched the pre-existing B1 artifact exactly. They cover 25 journey fixtures, 27 recorded Qwen outputs, seven OpenAI outputs and ordinary/manual/pending/date/error contrasts.
- **25 direct duration probes** captured complete before/after Journey DTOs, return/error outcomes and dynamic dependency invocation order. They cover relation variants, whole-trip/dwell fields, return/home/bare return, repeated/ambiguous visits, existing conflicting fields, masked travel, numeric/source bounds and injected dependency errors.
- Frozen metadata/schema hashes are sample regression vectors; no actual paid configuration or historical result is relabeled.

After extraction, the current-runtime reconstruction matches all 75 trace rows and all 25 complete duration traces. Other than the two duration positions, direct probes require the complete Journey to remain unchanged. Whole interpreter DTO/error comparisons still run, and the separately labeled recorded replay matches the frozen Qwen/OpenAI/case/probe/journal comparison fields. These are finite engineering regressions under declared clocks, not population semantic accuracy or independent human signoff.

## Historical source integrity and explicit test fixtures

`backend/journey.py` intentionally has a new source hash. **The original evaluator's unchanged `corpus()` and `metadata()` now refuse this checkout.** Original six pins, corpus SHA256, old manifests, scores and paid journal were not repinned. B1's old working-tree verifier also refuses B2. Retained Git source identity still verifies. Future exact historical execution remains subject to the original source and separately verified environment requirements.

Many existing *fake-provider unit tests* previously obtained their sample cases through the paid evaluator's source-qualified reader. Those tests must distinguish fixture data from current paid readiness. Ten evaluation-test modules now explicitly return an `OfflineUnitSuite` through standard unittest `load_tests`; all existing test bodies/assertions remain, with no cases removed or skipped. The recorded-replay test and B1 trace comparison use an explicit read-only reference scope. Current-version assertions select B2 while original manifests/checkers remain byte-identical.

`task52_b2_test_fixture.reference_scope` is a **mock/data fixture**, not an evaluator or validation profile:

1. It verifies the exact B2 source-set manifest and immutable reference corpus bytes/counts.
2. It calls the saved, unmodified original source gate and **requires its journey-hash refusal** before injecting reference data for the scoped test. Outside/after the scope the actual gate continues to refuse. New tests prove this and prove that a reservation outside fixtures fails before adding even a fake attempt.
3. It temporarily supplies a deep copy of the unchanged gold/reference data to mechanical fake unit tests. Frozen request/config hashes remain literal test vectors, not B2-ready approvals. No source-equality claim is returned by this fixture.
4. Fake unit suites use a temporary **fictional unit-state directory**, never a clone of the paid journal or another authorized experiment. Read-only recorded replay keeps the actual journal location. SQLite/path/OS-write guards forbid paid-state writes; private environment reads and HTTP/socket operations are blocked. Existing inner fake mocks remain fake. Network/model/credential transports are never permitted by this scope.
5. Context cleanup restores globals and closes temporary fixtures. Nothing imports this scope in production startup or normal planning. It supplies no CLI dispatch, source-check override flag, public receipt or planning authority.

These trusted unit-test I/O guards are **not an OS sandbox for historical/native code** and are not presented as one. No old source is dynamically imported or executed. Actual paid evaluator integrity checks remain unchanged; their expected rejection is explicitly tested, rather than being called a successful B2 readiness result. The original unit-test scenarios still exercise parser/scoring/accounting/transport mechanics with known fake data and no real allowance.

Run evaluation tests with the documented full discovery command or by **module**, for example `backend/.venv/bin/python -m unittest backend.test_cloud_model52`. Direct class/method invocation omits unittest `load_tests` and will safely hit the original source refusal; it is not the fixture entry point. No new test is skipped on that account.

## Versioning and remaining limits

The B2 runtime manifest binds actual implementation hashes (including changed journey and new duration module), source/data root, unchanged schema, prepared type, dependency/build evidence, original baseline relationship and the frozen reconstruction digest. The verifier rejects changed baseline bytes as well as unknown runtime/purpose or changed implementation/schema. This remains a source-set identity, not a reproducible deployed/container image.

B2 does not activate Ordering V4, change the active Qwen prompt, add typed confirmations, change source-grounding semantics or complete C–E. The existing unsafe legacy ordering acceptance/start-finish limitations remain; model qualification is still halted. No extra extraction is authorized by these results. Stop for owner review before B3.

The original ten attempts and 324 private files remain unchanged: OpenAI 7 / Google 2 / Anthropic 1 = 10/594; 584 remain; $0.047366625 accounted / $11.952633375 remaining. All $12/594/198, 12k input/2k output, concurrency-one/no-retry rules remain. Gemini HTTP400/IP and Anthropic grammar-compilation blockers remain separate. No inference/counting/Maps, purchase/billing/credential/quotas change, infrastructure, database migration or Task 53 work.
