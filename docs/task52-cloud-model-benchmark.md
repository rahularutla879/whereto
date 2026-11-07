# November 7, 2026 — exactly one OpenAI inference; stopped for review

Started clean at `559ade909cd2babfe0d35219be91df2f7a9d7a3e`. **Exactly one original OpenAI `journey-01/r1` call was sent; HTTP 200, provider status `completed`. No second inference or Google/Anthropic call was sent.** [Detailed safe evidence, hashes and review](task52-openai-first-attempt.json), [cumulative aggregate](task52-cloud-model-results.json). No production model is qualified and further paid dispatch is paused for owner review.

| Metric | First OpenAI attempt |
|---|---|
| Model / original slot | `gpt-6-luna` / `journey-01`, repetition 1 |
| Source | Synthetic: “Dinner and drinks in Jersey City tomorrow.” |
| Complete inference operation | **2,764.799709ms** (full response body, not first-token timing) |
| p50 / p90 / p95 / maximum | Each 2,764.799709ms, **n=1**; not a useful latency distribution |
| Canonical structured validity | **1/1** complete output; zero missing/unknown properties |
| Trusted source-grounded acceptance | **1/1**; no issues, unsupported items or clarification questions |
| Automated semantic assertions | Activities pass; journey equality flags two evidence-string differences |
| Fully correct semantic cases | **Not declared**; provenance-comparison review pending |
| Input / output tokens | **5,058 /180** provider-reported; reasoning0, total5,238 |
| Cache usage | cache-write5,055; cache-read0 (both reported by provider) |
| Usage-based conservative estimate | **$0.00072225**, using all5,058 input tokens at$0.125/M and180 output at$0.50/M; not an invoice charge |
| Authoritative journal reservation | **$0.0025 retained**; no release/rewrite |
| Provider-reported invoice charge | Unavailable |
| Cumulative attempts | **OpenAI1 /Google2 /Anthropic1 =4/594** |
| Remaining original slots | OpenAI197 /Google196 /Anthropic197 =590; no reallocation |
| Aggregate conservatively accounted / remaining | **$0.0377 /$11.9623** of$12 |

## Predispatch gates and unchanged request

Journal read-only integrity/root/row hashes matched the three-slot checkpoint before dispatch. Existing date gate2026-11-07UTC and provider/global readiness ages were still valid; no expiry was bypassed. One fresh non-inference count of the exact payload, including explicit reasoning none, returned200/**5,058**. All66 previously counted inputs/payload hashes remain valid, conservative bound7,125<12k. Existing restricted key access/Responses Write is demonstrated by successful counting and generation; no permission change. Existing credits**$4.93**, auto-reload**OFF**, rechecked in console immediately before dispatch; no purchase, reload or billing change.

[Model and current prices](https://developers.openai.com/api/docs/models/gpt-6-luna), [pricing](https://developers.openai.com/api/docs/pricing) and [processing terms](https://developers.openai.com/api/docs/guides/your-data) were rechecked. Standard short-context input/output$0.10/$0.50 per million, default cache-write$0.125; unchanged global synthetic-only request, no regional premium/extended cache option. API data is not used for training by default; standard abuse retention/exceptions remain. `store=false` is not ZDR. Request unchanged: model Luna, temperature0, reasoning none, default service tier, max_output_tokens2000, strict reviewed JSON Schema, no tools or conversation linkage; only synthetic non-personal input.

The existing journal committed **`reserved_uncertain`/$0.0025 for OpenAI/journey-01/r1 before HTTP dispatch**. A guard verified that committed row, unchanged prior three rows, exact payload hash and a single OpenAI transport call; the existing whole-run lock/max_new_attempts=1 enforced concurrency one. No warmup, alternative prompt, retry, fallback or modified generation request.

## Successful response; decoder audit correction

The provider returned `error:null` in a successful completed Responses envelope. The old evaluation decoder checked whether the error key existed, misclassifying this as `provider_error` before extracting usage/output or invoking scoring. **This was an evaluation-tool bug, not an OpenAI rejection.** The complete provider response and total transport timing were already durably recorded. A narrow evaluation-only fix now rejects non-null errors or non-200 HTTP operations; a regression covers successful null-error envelopes and real/error-null HTTP failures. No prompt, schema, corpus or application interpreter changes.

**Do not rewrite the journal to hide the original classification.** The OpenAI row and full reservation remain untouched; its original hash and exact saved response hash bind the separate offline correction. Existing Google/Anthropic failure rows and root metadata are byte-for-byte unchanged. Raw journal/report-command status therefore remains `provider_error`; curated evidence explicitly distinguishes this original harness classification from the HTTP200/completed provider observation. Offline decoding/scoring used only the saved response, with no network or second inference. Provider-separated exports retain the original raw record.

## Semantic result and owner review

The unchanged canonical parser and trusted interpretation/source-grounding pipeline accept the output. Both **Dinner and drinks are retained as required activity occurrences**, source order preserved. Location **Jersey City** and raw **tomorrow** are grounded; deterministic fixed-reference resolution yields**2026-11-06** in America/New_York from2026-11-05T15:00:00Z (the synthetic reference date, not the real run date). No explicit ordering constraint, optionality, exact named venue, return endpoint, total/travel/visit-duration bound or deadline exists in this source; none was invented. Unknown people/budget/currency/transport/cost remain null in the model extraction. Ordinary interpreter defaults are existing trusted behavior, not model requirements. Manual inspection found no omitted/altered required stop or hallucinated requirement/identity in this one output.

The unchanged automated journey comparator differs **only** at `stops[0].evidence` and `stops[1].evidence`: actual `Dinner`/`drinks`, versus sparse gold defaults `""`/`""`. Both actual values are exact source spans and pass source grounding. **Do not remove provenance validation, edit gold or quietly weaken the comparator to report a pass.** This is a candidate evaluator false positive requiring explicit review; no fully-correct label or full-corpus accuracy is assigned. Applicable semantic inspection and exact two-field diff are retained in the detailed evidence. No expectation was changed. The original recorded provider_error already fails closed for future OpenAI dispatch; owner review is required before designing an audited continuation past that classification. The remaining197 calls must not start automatically.

## Hashes, verification and stop

Request payload `8bab2d72f16e623b58faa8ae56880ed494db14f6c226741cf16b71b8dbfdb78e`; configuration `1c2352a7ec2b0bf826567de22b36ff2265bcd957e979d5b307cface7b5e0ee4e`; stored response object `e1d59ba1e521d8ee4c7d7eb738aa80a8707186018963fd3ba9311702ccfeb7d9`; exact output-text SHA-256 `4a53dfe716fbc79639c0db32a64dd0d043bb904d9f1572ac869ebcf85c2fabe5`. Detailed evidence defines hashing and includes model identifier, original record/file hashes, unchanged prompt/canonical/wire schema hashes. No key/authentication header or raw unnecessary output is committed.

Preflight admission/boundary regressions **12/12 passed** (0.621s). After the narrow decoder fix, harness + original AI/interpretation/journey/timing/source-grounding suites **162/162 passed** (23.543s), including a new regression for error:null successes and non-200/error failures. Relevant frontend planning/preferences/advanced/request-management tests **33/33 passed** (820.293ms). No application runtime code changed, so full application/build/browser/hosted suites were not rerun; prior full-frontend model-call-count instability is not claimed resolved by this subset. Security scan: **375 current tracked/new files and25 private JSON evaluation artifacts**, zero configured-credential matches; keys remain in ignored regular mode600 config. Journal integrity/root/three original row hashes and frozen prompt/schema/configuration hashes reverified. Complete tracked/new-file diff, JSON and local-link checks reviewed before commit. No actual provider inference occurred during regression tests.

**Not ready for automatic remaining-corpus dispatch.** Review the decoder correction and evidence-only comparator discrepancy, preserve this consumed slot/reservation, and approve any necessary audited continuation before the next unused slot. No OpenAI API/schema rejection was observed; broader accuracy, tail latency, critical gates and the expanded-corpus98% requirement remain unestablished. One2.765s interpretation is compatible with being a component of a five-second target; it does not demonstrate complete itinerary performance or justify production selection. No Places/Routes, Maps/billing/quota/credential change, Qwen/runtime/provider switch, saved database change, hosting/shared-state work, production deployment or Task53.

---

# Earlier readiness and benchmark checkpoints (historical where superseded)

# November 7, 2026 — OpenAI non-inference readiness verified

From clean `873c3c325f42e2322186aec0bab0fdd5fc32c043`, the owner reported manually setting the existing Task52B Evaluation key's Responses capability to Write. Read-only console inspection confirms the existing restricted evaluation-project key now includes `api.responses.write` (the console Write setting also includes read). No key, account permission, role or billing setting was changed by the agent.

**OpenAI is ready for its first bounded synthetic inference attempt; dispatch is paused at the owner's explicit instruction. Zero inference requests were sent in this check.** The existing adapter/prompt/schema/source rules are unchanged. Counting is not proof of schema-compilation success, semantic accuracy or latency; no production qualification is claimed.

- Exactly **132 non-inference requests**, all HTTP 200, to `POST https://api.openai.com/v1/responses/input_tokens`: 66 through the frozen harness, followed by 66 with its explicit `reasoning.effort=none` setting included in the counting request. No retry/fallback or other provider request. Both count sets agree case by case.
- Complete input includes the system instructions, all 19 example pairs, each synthetic scenario, message framing and the exact strict `text.format` JSON Schema. **66 cases: minimum 5,053, maximum 5,077 tokens (`ordinary-flexible`); first slot `journey-01/r1`: 5,058 tokens.** Existing conservative bound **7,125 =5,077 +2,048**, below **12,000**. Output remains `max_output_tokens=2000`; reasoning none, standard tier, store false, no tools.
- [Official counting contract](https://developers.openai.com/api/docs/guides/token-counting) and [current Luna model/support/pricing](https://developers.openai.com/api/docs/models/gpt-6-luna) rechecked November 7. `gpt-6-luna` is listed with Responses/structured-output support and the existing credential successfully counts its complete inputs. Standard short-context input/output **$0.10/$0.50 per million**, cache-write input $0.125; the unchanged conservative ledger rates reserve **$0.0025/attempt** at the full 12k/2k caps. No reservation was made because there was no inference.
- Existing API credits **$4.93**, auto-reload **OFF**, rechecked in console; no purchase, subscription or billing change. Approved global synthetic-only processing scope is unchanged; no private owner text is submitted.
- Original journal is byte-for-byte unchanged, SHA-256 **`3eef2041d51d7ffa66bfe16c18e0b5084a244f8923cc983384fb0640edaadd93`**. Read-only SQLite integrity `ok`; all row/root hashes identical before/after. Cumulative inference attempts remain **OpenAI 0 /Google 2 /Anthropic 1 =3/594**, **$0.0352 conservatively retained**, **$11.9648 remaining**, actual error charges unavailable. OpenAI retains 198 slots; aggregate retains 591. Provider198/global594/$12, concurrency1 and retries0 unchanged. Neither Gemini failure nor Anthropic failure was repeated.
- Version/hash unchanged: `52b-v3-equivalent-default-compaction`, configuration `1c2352a7ec2b0bf826567de22b36ff2265bcd957e979d5b307cface7b5e0ee4e`, prompt `751fb278f570e1b15ca839f403ccc97798588e979870e2a0c554e3a7c6aa8da2`, canonical schema `7ca1ed2e2701d4adc4735bc523abba1c7eb09060c5fa61b07da37673d8aec965`. Corpus66/six source hashes still match. The mode-600 ignored evidence files `openai-count-evidence-2026-11-07.json`, `openai-explicit-reasoning-counts-2026-11-07.json` and `openai-readiness-summary-2026-11-07.json` retain every count/case/payload hash without authentication headers or keys.
- Focused readiness/admission regressions **12/12 passed** (0.635s); no new tests or code changes. Credential values scanned against the documentation diff and private readiness artifacts with zero matches; ignored configuration remains mode600. Full diff reviewed. Full app/build/browser regression suites were not rerun for this read-only API check/documentation update.

No model/runtime/script/prompt/corpus/source-grounding, Maps, billing, infrastructure, production AI provider or Task 53 change. Next step is owner review and a separate instruction to send the first original OpenAI slot, under the existing allowance. The current harness additionally requires its **2026-11-07 UTC** date gate and provider-specific readiness age≤24h; reverify pricing/date/readiness if resuming after either expires. Google/Anthropic compatibility blockers remain unchanged; do not resume them automatically. Earlier results below are historical where superseded by this readiness check.

---

# November 6 local / November 7 UTC, 2026 — Task 52B Phase 1 blocker continuation

**Stopped on concrete provider blockers; no production model selected.** Started from clean `8df31f2544c5a9be14ba45f5f7d8e01c54eb85ed`. Two new single-attempt calls were made: Google 1 and Anthropic 1; OpenAI 0. Including the original failed Google slot, **3/594 attempts are consumed, $0.0352 conservatively retained, $11.9648 authorization remains**. No provider reported token usage or a charge for these errors; actual charges are unavailable. This is a partial reliability comparison with zero model outputs, not an accuracy or speed comparison. [Machine-readable evidence](task52-cloud-model-results.json), [complete prompt/schema revision audit](task52-prompt-revision-v3.json), [semantic review rubric](task52-semantic-review.md).

## Current benchmark

| Metric | OpenAI | Google | Anthropic |
|---|---|---|---|
| Exact model/version | `gpt-6-luna` | `gemini-3.8-flash` | `claude-haiku-5-5` |
| Newly dispatched attempts | 0 | 1 | 1 |
| Cumulative attempts consumed / remaining | 0 / 198 | 2 / 196 | 1 / 197 |
| Calls completed with model output | 0 | 0/2 attempts | 0/1 attempt |
| Valid structured responses | Unavailable (no attempts) | 0/2 attempts; no outputs to parse | 0/1 attempt; no output to parse |
| Validated accepted responses | Unavailable | 0/2 attempts | 0/1 attempt |
| Fully correct semantic cases | Unavailable | Unavailable | Unavailable |
| Critical constraint failures | Unmeasured, 0 outputs reviewed | Unmeasured, 0 outputs reviewed | Unmeasured, 0 outputs reviewed |
| Unsupported hallucinations | Unmeasured | Unmeasured | Unmeasured |
| Safe clarifications | Unmeasured | Unmeasured | Unmeasured |
| p50 inference latency | Unavailable | Unavailable | Unavailable |
| p90 inference latency | Unavailable | Unavailable | Unavailable |
| p95 inference latency | Unavailable | Unavailable | Unavailable |
| Maximum inference latency | Unavailable | Unavailable | Unavailable |
| Input tokens | Unavailable | Unavailable | Unavailable |
| Output tokens / output length | Unavailable | Unavailable | Unavailable |
| Actual provider-reported charges | Unavailable | Unavailable | Unavailable |
| Conservatively accounted charges | $0 | $0.0330 | $0.0022 |
| Data/privacy conditions | Global API; no training by default; abuse-retention exceptions; `store=false` planned | Separate paid Developer API; global processing, no training under paid terms, abuse exceptions | Commercial global API; storage/inference distinction, retention exceptions; no feedback/training opt-in |
| Qualification outcome | Permission blocked | Request compatibility blocked | Schema grammar compilation blocked |

The planned denominators remain **66 scenarios and 198 original slots/provider**, 594 total. Generated-output semantic/structured-validity denominators are zero, so no semantic percentage is reported. Attempt-based response availability is 0/2 Google and 0/1 Anthropic. All three consumed attempts are terminal provider errors, with no refusals/timeouts or uncertain transport reservations observed. No mandatory-stop, order, return, identity, duration or injection gate can be declared passed from these results. The expanded-corpus 98% qualification gate is unestablished.

Complete **error operation** timings (body fully consumed) were Google original `journey-01/r1` 1,149.791750ms, Google revised `journey-02/r1` 1,369.127542ms, Anthropic `journey-01/r1` 396.463000ms. They are excluded from inference percentiles. Google error-operation p50/p90/p95/max: 1,149.791750/1,369.127542/1,369.127542/1,369.127542ms (n=2); Anthropic all four 396.463000ms (n=1). Cold/warm inference, successful schema setup cost and subsequent-request behavior are unavailable.

## Reconciliation and immutable paid accounting

Before changing tooling, read-only SQLite integrity was `ok`: exactly the original Google `journey-01/r1` failure and $0.0165, matching the prior report. Original journal file SHA-256 was `d6d2d257c21530a41dea60a00475ffbfc83fd34f2ebb17ddddb6275d9ee26df4`. The original root metadata string hash remains `c4f48d1da35fbbecd55c8b42eced5b267b06f8322cf8dce77b7b99f92a2e0b4c`; original record digest remains `7a0545f019b16337faa5d02f3efd73f32b3052698eb16384ef98b2b182577305`. Both were rechecked after appending the two new rows. The journal was never recreated, reset, cloned or migrated. Its final hash and rows are reflected in the aggregate evidence; integrity remains `ok`.

Continuation opens the **same journal with its stored original configuration**, first verifies the pinned legacy configuration/row and every unchanged authorization field, and exclusively creates a sidecar containing the reviewed v3 configuration. Every new attempt records its own configuration hash/prompt version. Only the specifically acknowledged original failure permits moving to the next unused Google slot; any other prior failure/uncertainty stops that provider. A persistent accepted-semantic/cap halt still stops the entire experiment. Reports read SQLite in read-only mode. Locks, committed-before-dispatch full-cap reservations, original slot keys, 198/provider, 594 aggregate and $12 remain enforced. No slots are reassigned.

## OpenAI: permission blocker, no account change

Current console details confirm an active **WhereTo Model Evaluation project-scoped restricted key**, expiry November 13, with only `api.model.chat_completions.request`; it has neither Responses write nor Admin access. Existing balance **$4.93**, auto-reload off. The revised free count again returned 401 requiring **`api.responses.write`**. [Official complete-input counting](https://developers.openai.com/api/docs/guides/token-counting) uses `POST /v1/responses/input_tokens`, counting message roles and structured formatting. There is no verified narrower complete-input counting mechanism for this exact candidate; local tiktoken has no confirmed Luna mapping. Character estimates were not used.

The evaluation-only OpenAI adapter now uses **`POST /v1/responses`** and matching `input` plus `text.format` schema in the count request, removing the earlier Chat-Completions-versus-Responses counting mismatch. Planned settings remain model `gpt-6-luna`, output cap 2,000, reasoning `none`, standard tier, `store=false`, no tools. [Official model specification](https://developers.openai.com/api/docs/models/gpt-6-luna) lists Responses and structured output. No successful input count or inference is claimed. Verified standard short-context input/output remain $0.10/$0.50 per million; reservation input rate $0.125 conservatively covers the higher input class. Existing console limits are 5,000 RPM/2M TPM; no changes made.

**Exact owner action:** OpenAI Platform → Settings → Organization → API keys → **Task52B Evaluation** → Edit → keep Restricted and the existing evaluation project; grant only **Model capabilities → Responses → Request** (`api.responses.write`). Chat Completions can be set to None because the revised evaluation uses Responses. Leave Models/List/Files/Assistants/Admin and other APIs at None. Do not change organization roles, create an Admin key, select All, or alter billing. This endpoint permission permits Responses generation as well as counting; the key console does not establish a count-only narrower grant. **This permission expansion was not authorized or applied.** After owner action, rerun free complete-input counts/readiness and review the exact Responses payload before any remaining OpenAI slot. Credits alone do not clear the gate.

## Google: Developer API, unresolved generic 400

This is the owner's separately funded **AI Studio / Gemini Developer API**, not Vertex/managed inference and not Maps ADC/billing. Endpoint `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent`, `x-goog-api-key` header. Default Gemini Project, Gemini-only service-account-bound/IP-restricted key, Tier 1, **$5.00 prepaid / auto-reload off** were rechecked. The existing approved IPv4 transport selection remains; no IP restriction or IAM change. Free authenticated model metadata/count requests succeed, ruling out a blanket key/IP denial for those operations; generation compatibility is not proved by them. Existing console limits: 1,000 RPM/2M input TPM/10,000 RPD. No API enabled or managed-platform account used.

Offline review of the [official REST reference](https://ai.google.dev/api/generate-content), [v1beta discovery](https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta) and [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) identified the documented enum `LOW` (original `low`) and deprecated legacy `responseSchema`. Revised JSON uses `generationConfig.responseFormat.text` with `mimeType=APPLICATION_JSON` and standard JSON Schema, preserving `$defs/$ref`, nullable `anyOf`, enums, every property/required field and numeric/array constraints. Ignored temperature is omitted. Local tests validate all 66 exact serialized payloads against the reviewed fields/schema subset. The exact revised GenerateContent representation also receives HTTP 200 from free countTokens. **The original representation also counts successfully**: counting does not prove schema compilation or that lowercase `low` caused the original error.

The one resumed original slot `journey-02/r1` still returned **HTTP 400 `INVALID_ARGUMENT`**, identical generic message, no field violations/details, usage or model output. Thus the exact cause remains **unresolved**; do not attribute it confidently to casing, schema size, region, authentication or service mismatch. No third Google attempt was sent. Retain both errors in reliability and reserve $0.0165 each. Provider support/documented compatibility evidence is needed for this schema/model/Developer API combination before any further paid probe. Do not switch to Vertex, enable services, change Maps, purchase credits or retry a consumed slot. [Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing) rechecked: global $0.75/$3.75 per million through December 31, 2026, then $1.50/$7.50; thinking counts as output. Date/pricing readiness remains fail closed.

## Anthropic: token cap fixed; grammar-size blocker

Free provider counting reproduced the original **12,408** exactly before revision. The common revision counts **10,931 maximum over every one of the 66 actual complete inputs**, including `system`, all 19 example pairs and `output_config` schema/injected-formatting overhead via `POST /v1/messages/count_tokens`. The reduction is **1,477 tokens**. Bound **11,443 = max +512** retains margin for the documented estimate variability; 557 tokens remain below the authorized cap. No truncation or cap increase. Google also counts all 66: max 5,786 plus its existing 2,048 framing allowance =7,834. Free counters are not inference attempts and are not latency measurements. Count/readiness artifacts are private and version-bound.

Workspace/key/model metadata access, **$5.00 / auto-reload off**, global inference under the approved synthetic commercial conditions and standard $0.10/$0.50 per million short-context pricing were rechecked. Existing limits remain 1,000 RPM/500k input TPM/80k output TPM. No premium US-only inference setting, cache writes or tools were enabled. Endpoint `POST https://api.anthropic.com/v1/messages`, `x-api-key` and version `2023-06-01`; output 2,000, thinking disabled, effort low.

The first original slot returned **HTTP 400 `invalid_request_error`**, narrowly classified as **schema grammar-size failure**, before model output/usage. [Official structured-output limits](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#schema-complexity-limits) explain internal compiled-grammar limits in addition to 24 optional/16 union parameter limits. This wire schema has **15 union declarations, zero omitted-from-required properties and zero tools**; these source-level counts do not establish reference-expanded or internal grammar capacity. No schema branch, mandatory field or null semantics was removed after this failure. No further Anthropic attempt was sent.

Next proposal for review: obtain provider-supported compilation guidance for the exact synthetic schema (request ID retained privately), or design an offline-proved equivalent representation preserving all properties/nulls/relations and rerun source-grounding/fairness checks. Any later paid compatibility confirmation must use an unused slot in this same journal, retain the failed slot/version, and return for review rather than running speculative probes. Increasing tokens would not resolve this observed grammar blocker and is not proposed. No additional credit purchase is needed.

## Common prompt/schema revision and fairness

Version **`52b-v3-equivalent-default-compaction`** applies to every candidate. The **system prompt, all 19 example user texts/order, every nested journey/activity fact and every nondefault value remain unchanged**. Only repeated top-level example fields equal to declared parser defaults are omitted: `people`, `budget_group`, `currency`, `travel_total_minutes`, `travel_leg_minutes`, `transport`, `cost`, where applicable. All 19 reconstruct identically under the unchanged `Interpretation` model. Forty-five redundant schema `title` annotations are removed from provider wire schemas; canonical trusted schema remains unchanged. No semantic instruction/example/expectation was dropped. This proves data equivalence of the example reconstructions, not model accuracy.

The [revision audit](task52-prompt-revision-v3.json) lists **every removed field/value and title path**, original/revised prompt and all provider schema hashes, fixed time and input bounds. The original consumed Google slot keeps v2. New slots carry v3. Provider mechanics differ only as documented: OpenAI Responses strict JSON; Google standard responseFormat JSON Schema; Anthropic unsupported bounds retained as descriptions plus trusted offline checks. No change was made to application prompt/examples/defaults/schema/source validation or corpus.

Corpus raw hash remains `5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f`; **66 cases: 25 journey extraction, 26 ordinary assertions, 15 prose semantic review; six source hashes match**. Canonical schema hash `7ca1ed2e2701d4adc4735bc523abba1c7eb09060c5fa61b07da37673d8aec965` unchanged. Prompt v3 hash `751fb278f570e1b15ca839f403ccc97798588e979870e2a0c554e3a7c6aa8da2`. No gold expectation was found to require a change; no reference corpus/source/fixture was edited. Source hash/shape validation is distinct from complete manual gold adjudication, which remains open.

## Verification and privacy

Final harness **40/40** (22.219s); readiness-expiry test also passes with a fixed clock. Full backend **1,011 reported /974 passed /37 opt-in skips** (196.064s); original interpretation/source-grounding/AI/timing subset **121/121** (0.918s), local socket/IPC rerun **17/17** (2.087s). Relevant frontend subset **33/33** (826.061ms), affected mocked integration file **2/2** in isolation (931.333ms). Complete frontend was run twice: **282/283 passed** both times; the unchanged `app/api/interpret/route.test.ts:171` model-call-count assertion failed (9 vs10, then13 vs14) under the full run. The isolated pass does not establish a clean full-suite pass; possible scheduling/duplicate-admission interaction remains unresolved, and runtime/test expectations were not changed to hide it. Initial backend sandbox run had local-socket/tsx errors and the then-outdated failure-latency assertion; targeted fixes/reruns and the final full backend run passed. No fresh browser, hosted SQL, full production build or cloud concurrency test was performed for this evaluation-only change. Runtime implementation paths/defaults/startup/config/dependencies are unchanged; source inspection is not browser verification.

Security scan: all three configured credential values checked against **374 current tracked/new files** and **1,908 historical blobs**, **zero matches**. Ignored config and journal verified untracked; config mode600. Original root metadata and Google record hashes, integrity, corpus66/source hashes and 3/$0.0352 totals rechecked. Full tracked/new-file diff and local Markdown/JSON checks reviewed before publication.

Credentials remain in the existing ignored mode-600 regular configuration only; no key/header is in reports, argv, frontend, Git or normal logs. Artifacts use private evaluation storage and provider-separated exports, with no real sessions/capabilities/origins. HTTPS only, redirects/proxies/retries off, exact endpoint/method allowlists and provider-isolated headers. Free count bodies contain only the synthetic prompt/schema. Synthetic commercial processing review remains limited to this experiment; no production-user-data or ZDR claim. No purchases, auto-reload, broad permissions, Maps requests/billing/quotas, Qwen changes, infrastructure, migrations, release tags, production switch or Task 53 work.

## Recommendation and next authorized work

**No production model selection yet.** Best correctness, fastest qualified, overall winner and principal alternative are all unavailable because no candidate produced output. None can currently be said to support five-second end-to-end planning. Even future successful model timing excludes Places, Routes, shared-state/hosting and browser rendering.

Owner action is needed for the minimal OpenAI Responses Request scope. Google/Anthropic need provider-compatibility guidance or a reviewed, semantically equivalent schema proposal before further paid slots; no automatic resumption. Preserve original journal and all consumed failures. Remaining slots: OpenAI 198, Google 196, Anthropic 197, **591 total**; no reallocation, new allowance or automatic retries. Further readiness/paid resumption must use the recorded common version (or explicitly reviewed next version) with fresh pricing/account checks and original spend controls.

**Shared-state/cloud next steps are review only:** after successful model qualification, present exact architecture/region/processing/recurring-cost and bounded staging authorization to the owner; only after separate approval implement shared admission/session/provider accounting, managed secrets/state, then private staging and bounded full-pipeline canaries. No shared-state or cloud resource implementation is authorized now. Task 52 stays in progress; stop this phase for owner review.

---

# Historical checkpoint before this continuation (superseded counts/readiness)

# November 6, 2026 — Task 52B Phase 1 controlled evaluation

Baseline clean `main` at `8e79924093fbbcb5a9d62118b14232a8af95970e`. **Qualification incomplete; no production model selection yet.** One Google inference attempt returned HTTP 400 without model output. OpenAI and Anthropic stopped at readiness. [Aggregate results/configuration](task52-cloud-model-results.json). The November 5 report below is historical; its zero-attempt/account-unavailable statements are superseded by this checkpoint.

Authorization remains **66 unchanged synthetic cases × three repetitions × three providers, maximum 594 attempts/198 per provider, $12 aggregate token spend, 12,000 input/2,000 output tokens, concurrency one, no automatic retries or reallocation**. No purchase, Maps call/billing/quota change, infrastructure, production model switch, migration or Task 53 occurred in this continuation. Owner account/credit/key setup happened separately in this conversation. Those approvals cover synthetic evaluation, not production user data.

## Current benchmark results

No model generated a semantic response. “Unavailable” means no observation, not a passing score. Counts of structured/accepted responses use attempted inference as their denominator; semantic accuracy uses generated model outputs, of which there are zero.

| Metric | OpenAI | Google | Anthropic |
|---|---|---|---|
| Exact model/version | `gpt-6-luna`, served revision unobserved | `gemini-3.8-flash`, served revision unobserved | `claude-haiku-5-5`, metadata ID confirmed |
| Calls completed with model output | 0/198 planned | 0/198 planned | 0/198 planned |
| Inference attempts consumed | 0/198 | **1/198**, HTTP 400 | 0/198 |
| Valid structured responses | Unavailable, n=0 attempts | **0/1 attempt**, no model body | Unavailable, n=0 attempts |
| Validated accepted responses | Unavailable, n=0 | **0/1 attempt**, n=0 model outputs | Unavailable, n=0 |
| Fully correct semantic cases | Unavailable, 0 reviewed/66 planned | Unavailable, 0 reviewed/66 planned | Unavailable, 0 reviewed/66 planned |
| Critical constraint failures | Unavailable, 0 outputs | Unavailable, 0 outputs | Unavailable, 0 outputs |
| Unsupported hallucinations | Unavailable | Unavailable | Unavailable |
| Safe clarifications | Unavailable | Unavailable | Unavailable |
| p50 inference latency | Unavailable | Unavailable | Unavailable |
| p90 inference latency | Unavailable | Unavailable | Unavailable |
| p95 inference latency | Unavailable | Unavailable | Unavailable |
| Maximum inference latency | Unavailable | Unavailable | Unavailable |
| Billed/reported input tokens | Unavailable; 0 inference sends | Unavailable; no usage returned | Unavailable; 0 inference sends |
| Output tokens received | 0 | 0 | 0 |
| Provider charge / conservative estimate | $0 inference liability | **$0.0165 reservation retained**, invoice unavailable | $0 inference liability |
| Data/privacy conditions | Standard global API; no training by default; abuse retention; `store=false` | Paid Developer API; global processing and limited abuse logging; no tools/grounding | Global commercial API; no express training permission; retention exceptions |
| Qualification outcome | Blocked: token-count permission/bound | Stopped: request compatibility | Blocked: input exceeds cap |

The complete Google **HTTP error operation** took **1,149.791750ms**. Its p50/p90/p95/max are all that value, **n=1 error response**, measured around send and complete body reading. These are not model-inference performance observations. The JSON's generic operation percentiles include this error; explicitly named inference percentiles are null. No cold/warm distinction, successful schema compilation/setup timing, inference output length, accuracy, expanded-corpus 98% gate, fastest qualified model or principal qualified alternative can be established. The error is one safe operational failure, not a semantic success or proof of a model correctness failure.

**Recommendation: no production model selection yet.** Retain the three candidates pending their specific blockers. There is no successful interpretation evidence for five-second plausibility, and no Places, Routes, Cloud Run, Redis, PostgreSQL, browser rendering or higher-concurrency measurement. Full end-to-end five-second planning remains unproven.

## Verified account readiness and exact blockers

**OpenAI:** owner explicitly approved `gpt-6-luna` to replace deprecated GPT-4.1 mini. [Official specification](https://developers.openai.com/api/docs/models/gpt-6-luna) lists Chat Completions, structured outputs and reasoning `none`. Standard short-context input/output are $0.10/$0.50 per million; cache-write $0.125. Ledger rates conservatively use **$0.125/$0.50** to cover the higher input class, without assuming cache discounts. No Fast/Flex/Batch/regional premium. Earlier November 6 console checks: WhereTo Model Evaluation, Global Standard, $4.93 balance, auto-recharge off, model listed, 5,000 RPM/2M TPM; key expires November 13 and grants only Chat Completions Request. This is console-listed availability, not successful inference authentication.

Actual non-inference `POST /v1/responses/input_tokens` returned **401, missing `api.responses.write`**. [Official token-counting guidance](https://developers.openai.com/api/docs/guides/token-counting) provides complete Responses input counts. Local tiktoken 0.12.0, inspected only in ignored evaluation storage, has no mapping for Luna; a guessed tokenizer was not admitted. **Prerequisite:** owner-reviewed counting permission/credential or an official complete-payload bound for this restricted Chat Completions configuration, including reviewed framing differences. Access was not broadened. No inference sent.

**Google:** owner selected AI Studio/Developer API setup explicitly during this conversation; this is a documented service change from the original managed Cloud proposal, not reuse of Maps ADC. Default Gemini Project **`gen-lang-client-0829295259`** has its separate paid account; earlier November 6 console checks verified $5, auto-reload off, Tier 1, and `gemini-3.8-flash` limits **1,000 RPM/2M input TPM/10,000 RPD**. The provider's $250 account cap is not experiment authorization. Key is Gemini-only, Google service-account-bound and restricted to this machine's verified IPv4. Initial metadata was denied over IPv6; the local transport selects IPv4 without broadening the cloud restriction. Subsequent metadata returned **200** and confirmed `models/gemini-3.8-flash`.

[Model/lifecycle](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) documents stable structured output; [introductory pricing](https://ai.google.dev/gemini-api/docs/latest-model) is **$0.75/$3.75 per million input/output through December 31, 2026**, reasoning included. Standard global inference only; no region guarantee. Free complete-input counting explicitly included serialized schema as extra counted text (to avoid generationConfig/schema omission): **7,023 tokens**. Conservative admission adds 2,048 framing/schema tokens plus a 252-byte replacement bound for the last corpus input: **9,323 ≤12,000**.

The first inference, **`journey-01`, repetition 1**, at `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent`, returned **400 `INVALID_ARGUMENT`, “Request contains an invalid argument.”** No usage, candidate, details or request ID. **Prerequisite:** review mechanical request/schema compatibility offline before any further sends; do not retry this consumed slot. Current [REST reference](https://ai.google.dev/api/generate-content) deprecates legacy `responseSchema` in favor of `responseFormat.text.schema`; the generic 400 does **not** prove that deprecation caused the error. No fix, prompt tuning or replacement call was attempted. The ledger refuses configuration drift: any reviewed wire-version transition must preserve the same journal, original consumed slot and aggregate ceilings. The stopped provider does not automatically resume.

**Anthropic:** [Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview) is active, exact ID `claude-haiku-5-5`, retirement no sooner than October 7, 2027; standard short-context input/output **$0.10/$0.50 per million**. Earlier console checks: funded WhereTo Model Evaluation workspace, $5, auto-reload off, Evaluation tier, shared **1,000 RPM/500k input TPM/80k output TPM**, US workspace storage, global inference default, key expires November 13. No separate workspace spend cap; internal ledger remains authoritative. Actual non-inference GET `/v1/models/claude-haiku-5-5` returned **200**. Actual free POST `/v1/messages/count_tokens` returned **12,408 input tokens**, already over 12,000 before conservative margin (**14,708 bound**). **Prerequisite:** explicit owner review of a higher input cap with revised reservation math, or one common new prompt/example version for all models. Neither was applied; zero inference requests.

## Privacy, preserved behavior and reproducibility

Reviewed [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data), [Google paid-service terms](https://ai.google.dev/gemini-api/terms#paid-services), [Anthropic API retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) and [commercial exceptions](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data). OpenAI standard abuse retention can apply up to 30 days with exceptions; `store=false` is not ZDR. Google paid prompts/responses are not used to improve products; limited safety logging and international transient processing can occur. Anthropic does not train on retained API data without express permission; standard retention/legal/policy exceptions apply. No provider ZDR arrangement or account-wide optional logging setting is assumed verified. Synthetic non-personal extraction has no identified prohibited purpose; production user text remains unauthorized. No feedback sharing, Search/Maps grounding, browser history, saved itineraries/capabilities, private origins or real provider payloads were sent.

Exactly **six non-inference readiness operations** occurred (OpenAI 1, Google 3, Anthropic 2), distinct from the one inference attempt. Credentials are loaded from ignored mode-600 `backend/.env.cloud-evaluation`; no auth header/key is retained in artifacts or ordinary logs. Raw synthetic response/readiness detail is protected in ignored local artifacts; committed aggregate excludes IPs, keys and billing identity. Owner credit purchases during setup are separate from experiment token usage; the agent purchased nothing.

Evaluation-only [`cloud_model52_live.py`](../scripts/cloud_model52_live.py) adds explicit `prepare` and `live` commands around [`cloud_model52.py`](../scripts/cloud_model52.py). HTTPS endpoints/methods are allowlisted; TLS stays verified; redirects and SDK retries are disabled; socket timeouts are bounded; complete response is read before timing ends. One process lock spans the live run; SQLite FULL-synchronous reservations precede dispatch. Failed/unknown/completed slots stay consumed. Previous provider failures stop automatic continuation. Accepted automated semantic mismatches halt for review. No arbitrary corpus/prompt/model/endpoint/state/budget overrides, paid warmups or fallback.

Prompt version **`52b-v2-unchanged-instructions-reviewed-wire-settings`** records settings changes made before the first paid attempt: Luna reasoning none/standard tier; Haiku temperature omitted/thinking disabled/low effort; Gemini low thinking. System instructions and all 19 examples remain unchanged. Mechanical schemas preserve the same canonical properties and offline bounds/source validation: OpenAI strict schema; Anthropic unsupported bounds in descriptions; existing Google inlined uppercase/nullable representation. No interpreter/parser/source-grounding module changed. Google's wire compatibility remains unresolved, not certified.

Corpus unchanged SHA-256 **`5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f`**: 66 unique IDs, 25 journey expectations, 26 ordinary checks, 15 prose extensions, six matching source hashes. Reference time **2026-11-05T15:00:00Z**. No authoritative expectation changed. The three exact owner examples remain offline historical Qwen replays; no extra paid scenarios were added. Full semantic adjudication/expanded-corpus qualification remain unperformed because no model output exists.

The single durable journal at ignored `backend/.local/task52-model-evaluation/journal.sqlite` must never be deleted/reset/forked. Protected provider-separated response exports and readiness remain local; committed JSON records hashes/configuration/counters. Runtime defaults remain **Qwen `qwen3:4b`/Ollama**; no runtime imports the evaluation code. Startup, ordinary/advanced planning, manual preferences, saved security, Google provider admission/quotas/billing, release tags and production refusal remain unchanged.

## Cost, verification and next steps

Maximum reservation per request/provider: OpenAI **$0.0025/$0.495 for 198**, Google **$0.0165/$3.267**, Anthropic **$0.0022/$0.4356**; combined **$4.1976**. Anthropic remains inadmissible on token size despite that cost calculation. Current liability **$0.0165**, remaining authorized allowance **$11.9835**. Remaining slots: OpenAI 198, Google 197, Anthropic 198, aggregate 593; no reassignment. No actual invoice/token usage was returned for the 400, so its retained reservation is not a claimed provider charge.

- Fake harness and HTTP-boundary suites **29/29**, including full fake 594 slots, cost ceilings, missing/unknown/duplicate structured properties, grounding, interrupted/timeout recovery, persistent critical halt, no redirects/retries and secret redaction.
- Existing backend interpretation/grounding/ordinary/advanced/provider regressions **236 reported /234 passed /two opt-in hosted skips**, captured repeat 2.313s. Frontend **39/39**, 925.234ms. These are test durations, not inference benchmarks.
- No full app/browser/hosted SQL/build/load tests were run for evaluation-only edits. Existing application defaults/source preservation is tested/compared, not claimed browser verification. Final secret scan, diff review and publication evidence are in HANDOVER.

Resolve the specific permission, token-cap and wire-version blockers first. Resume remaining authorized slots only with reviewed equivalent instructions and preserved accounting; no model selection until successful semantic/latency evidence exists. Only after model qualification and separate recurring-cost/processing approval: implement shared DTO/store interfaces, durable reservation/fencing authority, shared admission/sessions and offline recovery checks; prepare a reviewable private staging plan. No hosting resources or Task 53 work is authorized now. **Stop Phase 1 here for owner review.**

---

# Historical November 5 — cloud model preparation checkpoint

November 5, 2026; baseline `285690b`. **Paid evaluation blocked; no model qualified.** This report is a preparation/readiness result, not a completed live benchmark. No inference, account setup, deposit, subscription, infrastructure or production change occurred. The owner approved only 594 synthetic single-attempt calls and $12 aggregate token spend; that allowance remains entirely unused. Infrastructure packages S/L/P and Task 53 are not approved by this experiment.

## Results returned for owner review

Unavailable means no observations, not zero errors or a 0% accuracy score. Each candidate's planned denominator is 198 attempts (66 scenarios × three repetitions). Actual accuracy/validity/latency denominators are **zero** for every candidate; no percentage or percentile can be calculated. “Calls completed” counts inference responses, not documentation retrieval.

| Metric | OpenAI | Google | Anthropic |
|---|---|---|---|
| Exact model/version | `gpt-4.1-mini-2025-04-14` (deprecated) | `gemini-3.8-flash` (documented stable ID; served revision unobserved) | `claude-haiku-5-5` (served revision unobserved) |
| Calls completed | 0/198 planned | 0/198 planned | 0/198 planned |
| Paid attempts including failures/unknown sends | 0/198 | 0/198 | 0/198 |
| Valid structured responses | Unavailable, n=0 | Unavailable, n=0 | Unavailable, n=0 |
| Validated accepted responses | Unavailable, n=0 | Unavailable, n=0 | Unavailable, n=0 |
| Fully correct semantic cases | Unavailable, 0 cases evaluated | Unavailable, 0 cases evaluated | Unavailable, 0 cases evaluated |
| Critical constraint failures | Unavailable | Unavailable | Unavailable |
| Unsupported hallucinations | Unavailable | Unavailable | Unavailable |
| Safe clarifications | Unavailable | Unavailable | Unavailable |
| p50 inference latency | Unavailable | Unavailable | Unavailable |
| p90 inference latency | Unavailable | Unavailable | Unavailable |
| p95 inference latency | Unavailable | Unavailable | Unavailable |
| Maximum latency | Unavailable | Unavailable | Unavailable |
| Input tokens | 0 submitted | 0 submitted | 0 submitted |
| Output tokens | 0 received | 0 received | 0 received |
| Actual provider-reported charges or estimated charges | $0 experiment expenditure; no invoice queried | $0 experiment expenditure; no invoice queried | $0 experiment expenditure; no invoice queried |
| Data/privacy conditions | Standard API no training by default; abuse retention; account unverified | Managed Cloud terms; abuse logging/caching exceptions; account and region unverified | Commercial API terms; standard retention/exceptions; account and region unverified |
| Qualification outcome | Stop: deprecated | Blocked: model-service readiness/region/terms | Blocked: credential/funding/region readiness |

No best correctness model, fastest qualified model, overall winner or principal qualified alternative can be identified from zero observations. **Recommendation: no production model selection yet.** Retain Google and Anthropic as unevaluated candidates. Reject this OpenAI candidate from dispatch under the owner's deprecation rule; do not silently use the provider's suggested replacement. A replacement requires explicit owner review. Neither five-second end-to-end planning nor the 1.8-second interpretation hypothesis is demonstrated. This experiment would exclude Places, Routes, Cloud Run, Redis, PostgreSQL and browser paint even if it had run.

## Official provider verification

Public pages were searched and opened November 5. These establish documented product behavior, not account access, actual limits, contractual residency or permission to change payment settings. Some former Vertex AI URLs now redirect to Gemini Enterprise Agent Platform/Model Garden documentation; the managed Cloud product was reviewed, not silently replaced with consumer Gemini or the separate AI Studio API.

### OpenAI

- Exact snapshot `gpt-4.1-mini-2025-04-14`; alias `gpt-4.1-mini`. Official [model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini) marks it deprecated and lists structured outputs, Chat Completions and Responses. [Deprecations](https://developers.openai.com/api/docs/deprecations) announces API removal January 14, 2027. **Stop this provider before API calls**, even if credentials later appear.
- Published uncached text input/output $0.40/$1.60 per million tokens. Proposed stateless endpoint is `POST https://api.openai.com/v1/chat/completions`, `model`, `messages`, `response_format.type=json_schema`, strict schema, output cap 2,000 and `store=false`. No tools, files, background mode, batch, fine-tuning or caching configuration.
- [Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) are model/project/tier dependent; actual RPM/TPM and balance are unknown. No rate-limit increase requested. Standard global processing would not establish US East residency; account eligibility/configuration for regional processing remains unverified.
- [API data controls](https://developers.openai.com/api/docs/guides/your-data): API content is not trained on by default; standard abuse-monitoring retention can be up to 30 days, with exceptions. `store=false` is not ZDR. Synthetic extraction poses no identified content-policy issue, but no account-level processing approval is claimed.
- [Prepaid billing](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing): new API accounts use prepaid billing, minimum purchase $5; auto-reload is enabled by default at setup. **No purchase or auto-reload authorized or performed.** Existing balance/subscription is unknown; a ChatGPT login is not proof of API readiness.

### Google managed Gemini

- Official [model specification](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash) lists `gemini-3.8-flash`, GA September 2, 2026; retirement September 2, 2027 or later. Text structured output, GenerateContent and Count Tokens are supported. Processing availability lists `global`, `us`, `eu`, not a guaranteed `us-east4` inference endpoint.
- [Managed pricing](https://cloud.google.com/model-garden/pricing): standard global input/output **$0.75/$3.75 per million** through December 31, 2026; **$1.50/$7.50** from January 1, 2027. Non-global listed pricing adds 10%. Output includes reasoning. Prices/tax/billing currency must be rechecked on resumption; no premium implicitly approved. No provisioned throughput, committed spend or recurring deployment is needed by the proposed pay-as-you-go request path, but account-specific billing eligibility/minimum obligations remain unverified.
- [Official REST quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash) uses `POST https://aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/global/publishers/google/models/gemini-3.8-flash:generateContent`, bearer authentication, `contents`, system instructions and generation configuration. [Structured output](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/control-generated-output) uses `responseMimeType=application/json` and `responseSchema`; schema counts as input. Complexity can cause 400 errors; no retry allowance is created by that fact.
- Standard PayGo uses account usage tiers/dynamic capacity, not guaranteed throughput. Account tier, permissions, actual quota and service availability have not been established. The protected existing Maps identity/Free Trial is not evidence of model authorization. No ADC authentication, API enablement, IAM or billing mutation was attempted.
- [Cloud data governance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention): no training without prior permission/instruction; abuse monitoring and advanced-model safety logging can retain content. Caching and grounding have separate retention behavior. No Search/Maps grounding or tools are requested. Synthetic non-personal inputs are compatible with the documented extraction use; applicable account terms, safety addenda, caching settings and region still need review. No blanket ZDR assertion or real-user-data approval.

### Anthropic

- Official [Haiku 5.5 specification](https://platform.claude.com/docs/en/models/haiku-5-5/overview) and [model overview](https://platform.claude.com/docs/en/models/overview) list `claude-haiku-5-5`, retirement no sooner than October 7, 2027. No other Haiku model is substituted. [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) provides `output_config.format={type:json_schema,schema:...}`; unsupported constraints require mechanical transformation and local validation.
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing): prompts under 100k input tokens $0.10/$0.50 per million uncached input/output; proposed 12k cap stays below long-context pricing. Global is standard pricing; US-only `inference_geo=us` is 1.1×. [Residency](https://platform.claude.com/docs/en/manage-claude/data-residency) distinguishes inference geography from storage. Neither is verified for this account; no premium chosen automatically.
- Proposed `POST https://api.anthropic.com/v1/messages` with backend-only `x-api-key`, required API version header, system/messages, `max_tokens=2000`, structured output, no tools/cache-control/retries. Thinking/effort defaults and shared output/reasoning cap must be explicitly checked before a measured run. Full first-response/schema compilation time must remain in latency; no paid warmup.
- [Rate limits](https://platform.claude.com/docs/en/api/rate-limits) depend on the organization's tier/spend limits; actual account access/RPM/TPM unknown. [Billing](https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage) generally uses prepaid credits, with invoicing and subscriber credits for eligible accounts. No funded organization, eligible credits or actual minimum checkout amount verified. Do not purchase credits, claim/link subscriptions, or enable auto-reload without separate approval. Timeouts may still be charged.
- [Commercial retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data): standard deletion within 30 days, legal/policy exceptions; flagged inputs/outputs up to two years and safety classification scores up to seven years; feedback has separate retention. [API data arrangements](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) distinguish ZDR eligibility and Covered Models; no ZDR arrangement assumed. No express training permission or feedback is submitted. Synthetic extraction has no identified prohibited purpose; actual account processing terms/settings remain unverified.

## Account readiness and precise prerequisites

Credential-presence checks found no OpenAI/Anthropic/Gemini key or model project in the process. Ignored project configuration files `.env.development`, `.env.database`, `.env.persistence` were checked by variable names/presence only; no cloud-model credential was found. Credentials were not printed, changed or read from another person's account. Existing database secrets and Maps ADC were not used for inference. This does **not** establish whether the owner has an account elsewhere.

1. **OpenAI:** review a nondeprecated replacement explicitly before further candidate work; this task does not choose it. If later approved, verify the owner's API project/balance, existing funds, processing terms/region and restricted backend credential. Any new deposit needs separate approval.
2. **Google:** identify an owner-authorized model-service project/account/identity; verify API availability, minimal permissions, existing billing eligibility, tier/capacity, approved region and applicable safety/logging/caching terms. If this requires enabling a service, changing IAM, upgrading Free Trial billing or purchasing capacity, return that concrete change for separate authorization. Do not reuse the Maps identity.
3. **Anthropic:** provide an owner-controlled funded API organization or verified eligible existing credits and a backend-only evaluation key; verify balance, limits, terms/retention and inference region. If no funds exist, obtain approval for the exact minimum deposit/tax before purchase. Do not create a subscription.
4. Credentials must use secure process configuration, following the existing ignored local conventions; never frontend configuration, CLI arguments, Git or chat. Merely supplying a key does not bypass the blocked live command.

## Corpus and semantic review

Unchanged SHA-256 `5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f`. Exactly **66 unique IDs**, 25 journey fixture references, 26 ordinary expected-check references, 15 prose-reviewed extension descriptions. All six source hashes match HEAD. Existing offline component results are historical and unchanged. Real recorded Qwen files remain historical evidence, distinct from authored fixture replies and new cloud output.

The three exact owner examples are absent verbatim from the 66 inputs, although related cases are present. New offline replay tests use their existing Qwen recordings without paid inference:

- Exact college → coffee → “return within 3 hours tomorrow”: exact named identity, required order, inclusive 180 minutes and endpoint clarification preserved.
- Jersey City grocery + pharmacy + optional coffee, origin return within 90 minutes: two required plus one optional, origin endpoint and inclusive 90 minutes preserved.
- Unicode grocery → pharmacy → return-to-start: two required stops, arrow edge and origin endpoint preserved; missing date/destination are not invented.

These are **three historical-output replays**, not new cloud results or additional paid scenarios. Adding these exact inputs to a paid corpus would require explicit corpus/design review while preserving the 594 total ceiling. No authoritative expected output was changed. No expectation was declared incorrect.

Full semantic adjudication is not automated by this checkpoint: 25 journey cases receive partial structural semantic comparisons, 26 ordinary cases receive existing expected checks, and 15 prose extensions require human review. All automatic outputs remain `fullyCorrect=null`/`reviewRequired=true` until reviewed. Local per-provider review templates bind every judgment to the complete response and configuration hashes. The `review` command rejects untouched, incomplete, duplicate or stale judgments, requires source-grounding review, reports explicit per-field applicability denominators and lists each reviewed critical failure. Invalid structured output cannot become a correct extraction/clarification by manual labeling. All-three-repeat case counts are separate from attempt counts; no automatic production qualification occurs. Automated passes cannot establish 98% accuracy or clear a critical gate. Journey comparisons exclude source wording and computed deadline minutes; exact identity/provenance, deadline relation/time, relative date/time, hallucinations and all requested field-level precision/recall still require adjudication. No expanded corpus or 20% holdout was created or tuned against. This is a remaining Stage A review requirement, not a fabricated score.

## Implemented tooling and limits

[`scripts/cloud_model52.py`](../scripts/cloud_model52.py) is evaluation-only; application imports/defaults/settings/startup remain untouched. No application provider registry entry or transport is added. The script imports the existing local system prompt and few-shot examples verbatim. Prompt version `52b-v1-unchanged-local-instructions`; prompt and canonical/provider schema hashes are in [preparation metadata](task52-cloud-model-preparation.json). Fixed reference time `2026-11-05T15:00:00Z`; destination calendar handling remains in the trusted resolver. Explicit synthetic destination timezone is supplied where known; unknown remains unknown. No source validator or date resolver is weakened.

Implemented: mechanical provider request/response mapping; raw missing-property audit plus existing duplicate/unknown/type parser; trusted `interpret_request` validation; complete-response timing around the injected transport; full synthetic response collection separate from operational logs; refusal/error/truncation classification; provider usage including Google reasoning; independent provider records; nearest-rank percentiles including failed-call latency; fixed-matrix resumable orchestration, per-provider local response export and safe aggregate report. Transports must return after consuming the complete response. “Validated accepted” means source-validated ordinary extraction or the existing grounded advanced handoff (exact shared limitation marker only), not an executable itinerary. Rejected output and targeted clarification remain separate outcomes. Ordinary and advanced source validation run offline without provider search/routing or session creation; this is not the full advanced orchestration endpoint.

Schema changes are mechanical and isolated: canonical projection removes unused AI clocks, journey conflict flag and computed deadline minute as the local adapter does; all object properties become required and schema defaults are removed. OpenAI uses strict JSON schema. Anthropic moves unsupported numeric/string/array limits into descriptions. Google inlines references, uses uppercase types and nullable fields, translates const to enum, and moves unsupported restrictions into descriptions. Original Pydantic bounds and unknown-key checks still enforce the canonical contract; a separate property audit rejects missing or extra wire fields, including shared-contract clocks deliberately omitted from the wire schema. No provider's semantic instructions are shortened. Wire compatibility, schema complexity/setup latency, model thinking options and exact tokenizer overhead remain unverified live; no schema is declared provider-certified.

The live command **always refuses** at this checkpoint. No HTTP/authentication transport is shipped while account/processing prerequisites are missing. Fake adapters test orchestration; they are not live-ready integrations. Stage A's offline safety components are implemented, but full semantic rubric review/token bounds and final wire compatibility remain open. Stages C–E have not run.

## Budget, concurrency and recovery

One SQLite journal under ignored `backend/.local/task52-model-evaluation/` is intended for the whole experiment, not one new journal per provider/run. No paid journal has been created. Canonical run metadata is immutable. CLI exposes no custom corpus, state path, budget, model, repetition or free-form prompt override. Test paths are injected only by offline tests. Never delete/copy/reset the paid journal to repeat attempts; retain it through recovery and publication. Complete synthetic raw responses stay local/ignored; commit aggregate evidence only.

Before each injected call: verify exact unchanged corpus entry and repetition 1–3; require a verified complete-input token upper bound ≤12,000; reserve one of 198 provider/594 aggregate slots and worst-case 12k input +2k output spend; synchronously commit before dispatch. Nanodollar integer accounting avoids rounding overspend. A process lock spans each complete operation; reservation admission uses an immediate SQLite transaction. No SDK retries, fallback, background calls or provider reallocation. Reserved/uncertain/completed slots are never repeated on resume. A crash before a send conservatively consumes a slot; a crash after a send cannot cause a repeated call.

Verified global standard-price worst-case reservations (estimates, not charges):

| Candidate | Per attempt | 198 attempts |
|---|---:|---:|
| OpenAI deprecated snapshot (not dispatched) | $0.0080 | $1.5840 |
| Gemini introductory global | $0.0165 | $3.2670 |
| Haiku global, below 100k | $0.0022 | $0.4356 |
| Total theoretical original matrix | | **$5.2866** |

The independent hard spend ceiling remains **$12**. Unused OpenAI calls/money cannot expand another provider's 198 slots. Missing usage/timeouts retain full reservation; complete valid provider usage can reconcile downward at verified uncached standard rates. Observed over-cap usage is retained as liability and halts further admission. Accepted automated semantic mismatches also persist a review halt across restart; resuming does not bypass it. Cached input classes are conservatively charged at ordinary input rate; no cache writes requested. Any future cache-write/fast-mode/region pricing requires changed configuration review before use. No dashboard alert is relied on as a hard cap. Deposits/subscriptions/tax/premiums are outside this token authorization and block the affected provider.

Payload measurements: maximum serialized messages 23,581 bytes; canonical schema 6,465 bytes. **Bytes are not token counts.** No complete provider-specific upper bound/tokenizer overhead is verified. Requests must refuse rather than assume the prompt fits, truncate instructions or silently increase the cap. No paid count-token, model-list, warmup or diagnostic calls were made. Pricing/date/region must be refreshed before live capability is enabled; existing metadata must not be edited to reset allowances.

## Reproduction and verification

Working folder: `/Users/rahularutla/Documents/whereto`.

```sh
backend/.venv/bin/python -m scripts.cloud_model52 inspect
backend/.venv/bin/python -m unittest backend.test_cloud_model52 -v
backend/.venv/bin/python -m scripts.cloud_model52 report
```

`inspect` validates corpus/source hashes and prints safe configuration/counts. After recorded outputs exist, `export` writes each provider’s local response JSON and an initial review template without overwriting existing review work; `review` validates completed judgments and emits aggregate metrics. These remain offline and inside the ignored evaluation directory. `report` refuses if no paid journal exists; it does not create one. `live` refuses with the readiness report path. These commands do not contact providers.

Current results: **22/22 harness tests**, including all three fake adapters, token/refusal/truncation/malformed responses, missing/duplicate/unknown fields, source-grounded hallucination rejection, historical owner examples, $12 ceiling, 198/594 counters, timeout/no retry, reserved/completed restart recovery, configuration drift, token-bound refusal, unapproved prompt rejection, lock exclusion and over-cap halt. Exhaustive fake reservations cover all 594 slots and the $5.2866 estimate; they consume no paid attempts. **236 existing backend tests reported: 234 passed, two opt-in hosted PostgreSQL skips**, 4.051s. **39/39 focused frontend tests**, 2.049s. Test durations are offline regression durations, not model latency. No failed test run is counted as passing.

No browser/live model/hosted database/load/full-app build was run for evaluation-only tooling; no new browser or end-to-end claim. Current runtime files and model defaults match baseline. Secret scan, final diff and publication verification are recorded in HANDOVER.

## Next checkpoint, then later infrastructure

First resolve affected provider prerequisites above, review the exact-example corpus gap and complete the semantic rubric/token-bound/wire review. Enable a single-attempt transport only after these gates, with current pricing/region/account evidence and the same durable experiment journal; rerun offline safety checks before paid dispatch. Use no extra warmups or retries. Collect and adjudicate every response, list each critical failure individually, then return measured comparison to owner. Do not treat safe invalid output as successful extraction.

Only after model qualification and separate infrastructure authorization: lock an approved model/region and exact recurring SKUs/terms; implement shared DTO/store interfaces, durable metadata reservation/fencing authority and shared admission/sessions; verify failure/recovery offline; prepare reviewable private staging configuration. Resource creation, paid staging, hosted migrations, public deployment and Task 53 remain outside this checkpoint. See the existing [implementation sequence](task52-production-implementation-plan.md). **Stop here for owner review; Phase 1 qualification remains incomplete.**
