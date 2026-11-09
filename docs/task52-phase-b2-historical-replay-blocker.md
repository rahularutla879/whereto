# Superseding checkpoint: owner approved behavioral reconstruction

The [B2 behavioral reconstruction and one-helper extraction](task52-b2-behavioral-extraction.md) proceeded under explicit owner authorization to use current-runtime evidence. This does **not** clear or rewrite the exact-historical-environment blocker below, change the preflight, execute old code, or authorize paid evaluation. Historical findings/results remain unchanged; the new evidence has its own identity.

---

# Task 52B B2 — historical execution prerequisite blocked

Baseline clean `1f76df7c3dd2b211391995eefbb812972953d585`. **No historical validation code executed and no mutating preparation fragment extracted.** Runtime remains `52b-runtime-phase-b1`. This checkpoint implements an offline fail-closed preflight and documents the prerequisite failure; it does not deliver an executor or a Phase B2 runtime identity.

Acceptance: verify retained sources and available dependency evidence, establish a truly isolated reproducible execution environment before any pinned edit, and stop if that gate cannot be met. The owner's explicit hard stop applies. [Machine-readable findings and verification](task52-phase-b2-preflight-verification-v1.json), [preflight](../scripts/task52_historical_preflight.py), [negative tests](../backend/test_historical_preflight.py).

## Verified evidence versus missing evidence

| Item | Finding |
|---|---|
| Historical source | Original allowlist verifies commit `b04f85ff82aa1b1befc2d44527c8e80a22ed080e`, tree `e9dae3d8029d200e3782da4c6d66dceea86b9d30`, implementation root, corpus and all six source pins. No current code is substituted into that source check. |
| Corpus | Original 66-case SHA256 `5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f` unchanged. |
| Current B1 | Its exact manifest/checker still verifies; schema digest and source-set hashes unchanged. Retained B1 results/manifests remain byte-identical. |
| Version pins | The historical requirements bytes equal B1's recorded requirements hash. All 24 explicitly pinned distribution versions match installed metadata. Python is 3.12.1, matching B1's recorded Python version. No package was imported/installed to manufacture historical dependency equivalence. |
| Artifact identity | No approved historical interpreter/stdlib artifact digest, wheel/installed-file artifact lock, native/platform or timezone-data environment identity was found in the retained manifests or reviewed repository/snapshot files. The B1 manifest explicitly records a source-set build and `reproducibleContainerBuild=false`. Version equality does not establish these missing byte identities. |
| Schema | Its source bytes and the **schema hash recorded in B1** are retained. The schema has not been regenerated inside a verified historical execution environment in this checkpoint. |
| Execution isolation | A minimal restrictive macOS `sandbox-exec` Python-version-only probe was denied under the managed sandbox (exit 71). Repeating the synthetic version-only probe with authorized local process permission terminated with signal 6 before producing output. The exact native failure cause is unproven. No denial-canary/network/file-protection acceptance suite succeeded, so historical execution confinement is **unverified**. This does not establish that macOS sandboxing is impossible. |

The OS probes loaded no historical source and received no model inputs, credentials or journal. Their environment contained only fixed PATH/bytecode controls; Python used `-I -S -B`. Neither result is accepted as proof of isolation. A Python socket monkeypatch, scrubbed environment or temporary directory alone would not prove that historical code cannot read credentials/write the paid journal; no such fallback was used to execute it.

The repository and retained Git tree were searched for environment/container/wheel/hash locks and attestations. A Node package lock and pinned Python requirements exist, but neither supplies a historical Python artifact/environment attestation. A separate parent-side read-only audit also reviewed all 322 retained private JSON artifacts and ten journal detail records for execution-artifact identity fields; none were found (ordinary wheelchair-access schema keys are unrelated). The preflight itself still never accesses that journal. This is a bounded evidence search, not a claim that no owner backup or external build artifact could exist.

## Delivered preflight and failure semantics

`scripts/task52_historical_preflight.py` reads only the allowlisted Git sources, existing exact-byte manifests and installed distribution **metadata**. It does not extract a checkout, import old validators, access credentials/journals, install packages, make network calls or create any paid state. Its CLI is:

```sh
cd ~/Documents/whereto
backend/.venv/bin/python -m scripts.task52_historical_preflight
```

Expected exit **2** means blocked, not a successful replay. The separate test suite expects that outcome. `require_execution_ready()` always refuses under the current zero-approved-environment registry, including caller attempts to force or assert readiness. There is deliberately **no executor hidden behind this gate**, no current-dependency fallback and no public/runtime startup hook. Recovering an artifact cannot silently activate code; a future runner and environment allowlist require reviewed implementation/tests.

Negative tests cover unknown/changed historical source, tampered B1 manifest claiming artifact approval, unpinned/duplicate requirements, missing/mismatched dependencies, caller force/assertion attempts and unintended journal/file access in the preflight. These tests establish this limited trusted audit's behavior, not a sandbox for arbitrary historical/native code.

## Lowest-risk candidate — analysis only, not extracted

Candidate `backend.journey.normalize_explicit_durations`, current lines 127–169; function source SHA256 `d807d729123f4e6bd48185c04c1c67e3d327af3d8fc1a588745457a1fbf15656`.

- **Call site:** `validate_journey` calls it with `(raw, guarded, j)` immediately after `normalize_extracted_references(raw, ai)`, after the no-Journey early return, and before legacy no-cue edge deletion/source validation. Its position must remain unchanged.
- **Inputs/dependencies:** original text; same-length first/between/travel-masked text; the already reference-normalized Journey. It reads duration regex/constants, `duration_value`, `duration_relation`, `unresolved_return_clause`, `Duration`, and endpoint source/kind. Dynamic helper lookup and existing monkeypatch behavior must be retained by a future wrapper.
- **Mutations:** fills an absent `journey.total_duration` or an absent existing stop's `duration` from bounded source evidence. It does not overwrite present values. Competing stop associations/multiple duration phrases and invalid/oversized values are skipped under current rules.
- **Occurrences/graph:** it does not add/remove/reindex stops, rewrite source identities, alter required/optional status, change edges or create an endpoint. B1's existing occurrence mapping remains applicable. Earlier reference normalization can remove a final home/back stop, so this helper must continue seeing the post-reference stop list.
- **Disposition/errors:** returns no clarification itself. The later unchanged validators assess source/relation/scope correctness and choose clarification/advanced handoff. Existing constructor/helper exceptions must propagate at the same point; no error swallowing or fallback. Adding a duration can affect advanced classification later, which is why moving it earlier/later is unsafe.
- **Coverage to retain:** all 25 journey fixtures, 27 Qwen and seven OpenAI outputs plus B1's ordinary/manual/pending/error/date contrasts. Add isolated duration probes for absent/present/conflicting dwell and whole-trip fields, masked travel-only wording, bare return, repeated/ambiguous stops, inclusive/exclusive relations and source-length limits before a future extraction. Existing current-process traces are useful references, not proof of exact historical execution.

This is a smaller mutation surface than `normalize_extracted_references`, which can delete stops/edges and reclassify endpoints. **No function was moved or wrapped.** No original-versus-new B2 mutation/DTO/session comparison is claimed because there is no new B2 implementation.

## What is needed to unblock

1. Recover a verifiable contemporaneous execution artifact/environment lock, including interpreter/stdlib, exact dependency artifacts/native ABI and relevant system/timezone data, bound to the retained source/schema/input/clock identities. Do not generate today's hashes and label them historical.
2. If no such artifact exists, owner review must explicitly approve a **separately labeled reconstruction baseline** and its provenance standard. Matching pinned versions may support that proposal, but this checkpoint does not treat it as exact historical reproduction or as approval to relax the hard stop. Old paid outcomes/labels remain untouched.
3. Implement a reviewed separate-process runner with verified source/import roots, scrubbed environment, credentials and the real journal excluded, all network/model access denied, writes restricted to a controlled output channel, and bounded time/memory. Demonstrate synthetic read/write canary denial, socket denial without contacting a provider, child-process restrictions, error/timeout handling and no current-source/dependency fallback before loading a validator. A verified retained container artifact is another possible mechanism; none was found/provisioned here.
4. Only after those gates pass, select the duration helper, freeze complete DTO/error/mutation/provider/session traces in the isolated old process, make exactly that one extraction under a new runtime identity, and compare the current process against it. Do not change the historical evaluator or its pins to make the new runtime pass old equality checks.

No permission, credentials, billing or infrastructure change is needed for the current blocked preflight. Future environment provenance/confinement approval is the missing prerequisite, not authority to spend on an account or rerun an inference slot.

## Verification and preserved state

Current-runtime B1 traces and its 27 Qwen/seven OpenAI frozen ordering replay remain unchanged. They run with fake providers/fixed clocks and are explicitly labeled **current B1 compatibility**, not isolated historical reproduction. Original paid classifications/configurations are unchanged.

No runtime/shared application file changed, so full backend/frontend/TypeScript/lint/build/browser were not rerun. The B1 totals (1,159 backend passes/37 opt-in skips; 285 frontend passes; typecheck/lint/build and controlled-date browser smoke) remain historical results. Fresh focused/preflight/ordering/admission/session/security totals are in the linked verification report. No skip or expected outcome was added to conceal a failing production test.

All six pins, old manifests/checkers, Qwen/prompt/schema, source-grounding, legacy normalization, default-OFF shadow, disabled enforcement, current B1 source identity, saved/pending/admission behavior and Hitech/HITEC correction are unchanged. The existing `hitech city tomorrow` unknown-destination-timezone clarification remains a separate issue.

All 324 private files, ten paid rows/corrections/reservations and persistent halt remain unchanged. OpenAI 7 / Google 2 / Anthropic 1 = 10/594; 584 remain; $0.047366625 accounted / $11.952633375 remaining. Preserve $12/594/198, 12k input/2k output, sequential one and zero retries. No historical execution, inference/counting/Maps/provider request, new journal/allowance, refund, billing/key/quotas/model change, transport, infrastructure/migration or Task 53 work. Gemini HTTP400/IP and Anthropic grammar compilation remain separate blockers.
