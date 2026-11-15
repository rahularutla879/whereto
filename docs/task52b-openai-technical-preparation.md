> 2026-11-15 follow-up: [original-evidence replay and inactive writer/transport kernel](task52b-execution-boundary.md), [new verification](task52b-execution-boundary-verification-v1.json). All37 frozen replay tests now pass through the separately pinned read-only I/O port; the four private-state location errors below describe the prior checkpoint. Original source/pins, prepared requests and review deferral remain unchanged. New operational enrollment and live HTTP remain unavailable. No provider/account/count request or financial permission follows from these offline results.

# Task 52B — five-slot OpenAI technical preparation

Baseline `7e1df9962c0d8147c80759f9303d551e1c37708f`. This checkpoint prepares data and checks reproducibility. **No provider request, readiness call, token count, reservation, journal write or approval was issued.** No model is qualified or selected. [Build/payload manifest](task52b-openai-preparation-build-v1.json) · [Verification](task52b-openai-preparation-verification-v1.json).

## Owner review deferral

The owner explicitly deferred independent human review in the current conversation. [Versioned decision](task52b-owner-review-deferral-v1.json): `52b-owner-independent-review-deferral-v1`. The 120 source judgments, six historical questions, four normalizer questions and future response reviews remain incomplete. The existing five owner-approved interpretations and exact journey-06 diagnostic semantics remain approved at product level; no repeat product approval is requested.

Deferral is not a signature, independent certification, financial permission or authorization to bypass frozen review gates. The [blank review form](task52-independent-review/REVIEW_FORM.md) and [normalizer checklist](task52-independent-review/QUALIFICATION_CHECKLIST.md) are unchanged. If live technical diagnostics are wanted before independent review, a separately reviewed purpose/progression amendment must explicitly state what unreviewed execution permits. This instruction alone does not amend the existing per-response gate. No response may be called independently correct. Production planning remains unauthorized.

## Frozen execution investigation

The ten errors in the previous 27-pass/10-error run were source-identity refusals, not ten model failures. B2 pins both the implementation root and `package-lock.json`. The current application has later provider-dispatch changes and a security dependency update; replacing only the lock file would neither restore the root nor be appropriate for the working application.

Seven retained commits were examined as Git objects without running their code. Six (8e360c0 through e7937e4) retain the expected 127-file B2 root and lock hash; 3f50032 no longer matches the root. A separate managed checkout of **`e7937e4ab1c2734a6576137dd4233fdaca8966c5`** was used with the existing Python executable. No original file, manifest, dependency pin or result was changed. No historical npm installation was performed. The separate clean source checkout is retained: managed cleanup refused because the app identifies it as this chat's primary checkout; it contains no copied private evidence.

| Identity | Verified value |
| --- | --- |
| B2 implementation root | `eeaec6d0fcc502cb1df2388f9ab808f013cbf711b7f84c91d21e7132ff3d4b8b` |
| Original package lock | `7fde3bb3c81a32f5149f56a3258a8dc9afc563c040a50337c85ea69f483b8404` |
| B2 manifest | `5151423b78a7140790c3e6951c3fb64be49b6887db5b230449b7b011bca4cf14` |

The unchanged four-module test command now produces **33 passes, four errors out of 37**, with no B2 identity errors. The remaining errors need original private evidence/journal at the frozen checkout's expected location. That state is intentionally absent. It was not cloned, symlinked or relocated. The current checkout's source gate still properly refuses. The exact four test IDs and log hashes are recorded in the verification JSON.

This establishes a compatible **source environment**, not complete reproducibility of the original paid execution environment. Python/FastAPI/Pydantic observations and the current distribution/executable hashes are in the build manifest; the original complete transitive environment was not independently reconstructed. A safe read-only original-evidence colocation/port retaining original path, lock, inode and identity checks still needs review before full replay. Do not monkeypatch ROOT, loosen checks, copy the paid database into a synthetic fixture, or repin historical results. The narrow preparation verifier below intentionally constructs data only; it cannot grant B2/live execution authority.

## Exact prepared requests

All five complete generation bodies and five count-request drafts are in [the versioned artifact directory](task52b-openai-diagnostic-prepared-v1/). They contain only the public synthetic corpus and reviewed prompt. Each generation hash equals the existing Q3 `proposedPayloadHash` byte-for-byte. Only the final user content varies from the reviewed frozen template. No warm-up, retry, new example or substituted repetition is included.

| Position | Slot | Generation SHA-256 |
| --- | --- | --- |
| 1 | extension-repeated/r2 | `5c2ad0aa457ae84497f489a1ca155ce805c8f160fd5260f59e0a4a3e8a078c02` |
| 2 | journey-04/r2 | `8166f0e97028d003a13a22ca57c78f1fc3404c32cf11b8b1fa4a94fd437ec105` |
| 3 | extension-partial/r2 | `4a79183fdc6471925a6c9618c34dae1806ff0b3cabd50dbce7061da4f3aa28b4` |
| 4 | journey-06/r2 | `6bcc4fd15bd933cf58e36a78bb0ed89bbe103951b302895e62eae7f7533784bd` |
| 5 | journey-21/r1 | `78db82ab3bfbe2f66e04560312d52d14c25e3dc06dd00d82830f420d77495698` |

The manifest includes original source hashes and all five rubric-case digests. All 120 proposed expectations match the Q3 slots. Reference clock stays `2026-11-05T15:00:00Z`; no current date replaces it. The prompt hash is `1741e5b5ae344fff0e4fff1fba2c4b45fd73b0b86baf73bdae35607f4b1919c9`, configuration hash `4239ddf4810ce65dfc5593c64cb011372abb1e350560ed848ceded06811d28a8`. All 19 examples are unchanged. Their compact teaching outputs validate as existing Pydantic examples; they are not complete strict-schema provider responses. An initial new test incorrectly demanded full strict fields in these examples; that test was corrected, without altering the prompt. Actual returned responses still need every required wire field and unknown-field checks.

Frozen generation controls: `gpt-6-luna`, Responses API, temperature 0, reasoning `none`, standard/default tier, `store:false`, no tools, maximum output 2,000. Complete input bound 12,000, concurrency one, retries zero. Canonical JSON uses sorted keys, compact separators, UTF-8, no newline, `ensure_ascii=false`, `allow_nan=false`. This is the existing repository convention, not a new canonicalization standard.

From the repository root, the following command only checks local files:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. backend/.venv/bin/python -m scripts.task52b_prepare_openai
```

It performs no journal access, credential loading or network operation. Payload possession never authorizes a request.

## Count integration and public API compatibility

Official public documentation was checked on 2026-11-14. The [Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna.md) documents Responses, structured outputs and reasoning `none`. This supports request construction; it does not prove current account access, fixed serving revision, latency or successful acceptance of this complete schema. The model page lists the alias `gpt-6-luna`; no unlisted dated model snapshot was invented.

The [token-count guide](https://developers.openai.com/api/docs/guides/token-counting.md) explains that exact counts include request framing and schema overhead. The [count API reference](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count.md) exposes model/input/text/reasoning. Its reasoning description retains older model-family wording; account acceptance of this exact Luna projection remains untested.

The new count drafts retain the complete `model`, `input`, strict `text.format`, and `reasoning` fields. Generation-only temperature, service tier, output cap and storage controls remain bound in the complete generation artifact. Historical `cloud_model52_live.count_body()` omits reasoning; it is unchanged and must not be silently used as proof of a fresh complete count. This separately versioned projection requires review before any authenticated request. No previous token counts are reused. All five actual counts remain **null**.

The pure input-bound function rejects unavailable/non-integer/boolean/nonpositive/over-cap or mismatched-payload inputs, retaining the original 2,048-token margin. A synthetic count of 9,952 plus margin fits exactly 12,000; this is an arithmetic fixture, not an estimate of these requests. The function is not a readiness attestation. Fresh exact provider count evidence must independently bind model, complete generation/count hashes, time and approved account scope before authorization.

## Accounting and single-send audit

The historical SQLite journal remains a separate halted accounting domain. Read-only verification checked its original root, all ten rows, corrections, all 324 private files and active halt under the existing shared experiment lock with read-only SQLite/authorizer protections. Journal SHA-256 remains `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`; root `b42f566a4525be25023e7ecc29fc41b86c8dc3d1c77899ca949fa0f31f4eb7dd`. Seven OpenAI, two Google, one Anthropic; $0.047366625 accounted, $11.952633375 remaining. No reservation or sidecar was created.

Existing Q4C/Q4D/integration source retains durable operation/slot identity, unique permission nonces, shared locking, immutable START/reservation/INTENT/OUTCOME/REVIEW/HALT facts, a full conservative reservation committed before send, and source/build/model/prompt/response binding. A missing result, review or uncertain delivery refuses progression and retains exposure. No automatic resend or refund. Raw provider output remains immutable, separate from decoding, B2 normalization and V5.1 guarded assessment. Safe rejection is not raw correctness. The exact journey-06/r2 exception cannot generalize to another mutation or authorize planning.

These are inspected existing **offline foundations**, not a newly verified real writer or dispatcher. The real-integration writer accepts only newly created synthetic storage; live dispatch remains an unconditional refusal. The old Ledger's row-updating finish path is not an approved append-only successor. Full Q4A–Q4D crash/signature/concurrency suites were not rerun because their exact source/private-state gate is unresolved; only existing pure Q4C financial boundary arithmetic was additionally exercised. No new reviewer keys, enrollment, signatures or grants were fabricated.

## Verification and remaining boundary

New preparation suite: **13 passed**, no skips/errors. Restored four-module suite: **33 passed, four private-state errors**, no skips; not a full replay pass. `pip check` passes. Final scans, diff and integrity checks are recorded in the machine evidence. Application/frontend/build/container suites were not rerun: there are no application, dependency, deployment or infrastructure changes. No independent human review occurred.

Offline preparation is complete; **live execution remains blocked** by full original-evidence replay integration, reviewed real same-journal append/intent/recovery and single-send transport, genuine protected operational provenance, incomplete independent reviews (or a separately reviewed narrower purpose amendment), and all fresh readiness/financial/operation approvals. See [the exact gated procedure](task52b-openai-readiness-gates-v1.md). The full five-request quote is not account-verified. Stop before contacting any provider. Container-security remediation remains a separate Task 52 staging blocker.
