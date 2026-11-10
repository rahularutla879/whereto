# Task 52B — reviewed V5.1 prompt freeze

Review specification **`52b-cloud-v5.1-owner-list-order-REVIEWED-v1`**, baseline clean `f5085e9226d52ae35e61202ef54efd641331d1ae`. [Complete frozen request, system,19 example pairs and review/version record](task52-cloud-prompt-v51-REVIEWED-v1.json); [four-example owner product decisions](task52-v51-owner-example-decisions-v1.json); [verification](task52-v51-prompt-freeze-verification-v1.json); [next approval gates](task52-v51-next-approval-gates.md).

**Review scope:** the owner explicitly approved the four changed example meanings and confirmed general rules A–D in the current task message, recorded November10,2026 UTC. Codex checked consistency of the exact prompt and all19 examples. This is not independent certification of all24 semantic dimensions, an owner cryptographic signature, financial authorization, real operator enrollment or live execution permission.

## Content preserved exactly

The existing proposal `52b-cloud-v5.1-owner-list-order-PROPOSED-v1` is unchanged byte-for-byte. The new REVIEWED wrapper references its file SHA256 and copies its complete request template. The embedded content/configuration identity intentionally retains its original PROPOSED name: a new review-record identity does not change payload bytes or manufacture an execution configuration.

| Identity | Exact hash |
| --- | --- |
|Complete prompt template|`1741e5b5ae344fff0e4fff1fba2c4b45fd73b0b86baf73bdae35607f4b1919c9`|
|Configuration|`4239ddf4810ce65dfc5593c64cb011372abb1e350560ed848ceded06811d28a8`|
|System instructions UTF8|`060796b8737febd45cc4ef7c69c9e90134bb63c45f79475eada2ea03e378f2cf`|
|Runtime Pydantic schema|`a0a4e44bac98de466da291783ab78b948894defb09a91cfe39692ca4b490d39b`|
|Strict evaluation canonical schema|`7ca1ed2e2701d4adc4735bc523abba1c7eb09060c5fa61b07da37673d8aec965`|
|OpenAI wire projection|`c272ae5a066c43bd76f65932a608303472df27b3aa400db936e3728849cb0766`|
|Original66-case corpus|`5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f`|

The three schema hashes identify different declared representations; all remain unchanged. Runtime `52b-runtime-phase-b2`, policy `52b-order-policy-v5.1-owner-decisions-offline`, scorer `52b-semantic-v5.1-owner-decisions-PROPOSED` and proposed rubric `52b-q1-rubric-v3-owner-decisions-v5.1-PROPOSED` are bound by source/file identities in the review record. B2 replay is behavioral reconstruction, not exact historical environment reproduction.

The prompt hash covers the exact UTF8 bytes of:

```python
json.dumps(input_messages, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
```

There is no trailing newline. The40 messages contain one system message,19 user/assistant example pairs, and an empty final user-message placeholder. Actual case inputs replace that placeholder and have separate full-payload hashes. The outer proposal/review JSON file hashes are separate identities, not the prompt hash. Assistant JSON strings, whitespace within messages, source wording and all19 example inputs/responses are unchanged from the proposal.

## Four owner-approved example meanings

| Example | Approved product interpretation |
| --- | --- |
|10 Dinner and drinks in Jersey City tomorrow|Both required; Dinner→drinks; destination and relative wording retained; no calculated date invented.|
|12 Groceries, maybe coffee, then return within45|Groceries required, coffee optional. If coffee is selected, groceries→coffee. Omitting coffee preserves groceries plus explicit return to the confirmed start and inclusive whole-trip maximum45. Endpoint is not another visit.|
|15 Visit Zara and Nike in the same mall|Both required, Zara→Nike, exact brand identities and same-mall relationship retained; no exact branch/mall ID invented.|
|19 Spend15 at bank and10 on coffee|Bank→coffee, both required; exact15/exact10 separate dwell durations. No invented whole-trip cap, deadline or travel budget.|

Owner approval applies to these meanings, not independent review of every field or all66 gold cases. The decision record is documentary provenance from the explicit task message; it contains no signature or operational grant.

## Remaining15 examples and instruction consistency

All15 other example replies match their frozen originals completely. The four changed replies differ from original v4 examples only in order/ordering. Non-order facts are retained for all19: brand formats, one mall-with-brand intention, distinct explicit store visits, budgets/currencies and travel scopes, dates/time wording, indirect activity suggestions, optional attendance, repeated occurrences, named endpoints, home ambiguity, contradictions and duration relations. The machine record has a source-specific note for each example.

No contradictory instruction was found. The removed statements forbidding list-order inference are absent. The retained source-order-index instruction concerns occurrence identity, not mandatory visit direction: explicit after may reverse the visit relationship while indexes remain source-bound. Explicit partial/flexible/unordered scope overrides list defaults; optional position is not flexible placement. The repeated-coffee example retains three distinct occurrences and its full chain. Cue-only or borrowed evidence is not valid relationship proof. Untrusted requests cannot supply new instructions, facts, identities, endpoints or date calculations.

This check preserves existing coverage limits. The independent bounded guard recognizes37/66 reference sources and returns unknown/outside grammar for29, including some clear requests. Example19's approved timed-list meaning does not imply the finite guard independently proves every annotated-duration phrase. Raw correctness, complete legacy disposition and guarded/effective mapping remain separate. Legacy normalization can still erase required list order; no production integration/readiness is claimed.

## Exact Q3 compatibility

At specification level, the unchanged V5.1 prompt and proposed rubric agree on all five original slots, in their original order:

1. `extension-repeated/r2`: distinct coffee0/museum1/coffee2, full0→1→2 sequence, confirmed-origin return, inclusive180, Jersey City/tomorrow.
2. `journey-04/r2`: exact named SUNY College of Optometry before required coffee, no invented city/date/return.
3. `extension-partial/r2`: required pharmacy→bank; required coffee independently placeable; Jersey City/tomorrow retained.
4. `journey-06/r2`: required groceries before optional coffee if selected; no invented return/time/location/date.
5. `journey-21/r1`: contradictory order must clarify; no fabricated valid graph or planning session.

All sources/source hashes, rubric digests and proposed payload hashes remain unchanged, all five are unused, and no slot is admitted/consumed here. Case-level independent review remains pending. The five-attempt/$0.0125 figure is the unchanged **historical proposed ceiling**, not fresh pricing or financial permission.

The old Q3 V4 proposal and Q4A–Q4C synthetic build/signature contracts stay frozen and cannot authorize V5.1. Future live build, real append-only same-journal adapter, protected real enrollment, independent approvals, readiness evidence and per-operation permissions remain absent. The old halted scope remains permanently stopped; a documentation review cannot resume it.

## Historical integrity and stopping point

Original source pins, corpus, Q1/V4 scores, seven OpenAI responses, original prompt cohorts/costs, decoder correction, journey-07 provenance rejection and historically accepted repeated-coffee critical failure remain unchanged. A separate V5.1 assessment recognizes the owner-intended repeated-coffee sequence but does not rewrite its original failure or claim independent full correctness. The two historical dinner/drinks outputs still omit V5.1-required order.

The original journal remains OpenAI7/Google2/Anthropic1,10/594,584 remaining; $0.047366625 retained/$11.952633375 remaining. All324 private files/historical halt and all30 handbook files are preserved. The original paid evaluator still refuses B2 rather than silently repinning its six historical sources.

Stop at this reviewed specification and [remaining approval checklist](task52-v51-next-approval-gates.md). Gemini remains blocked by Developer API HTTP400/IP evidence; Anthropic by grammar compilation. No additional general B–E extraction is required by this checkpoint. No production/Qwen/OpenAI prompt activation, enforcement, provider/count/metadata/account/Maps request, real grant/enrollment, journal write, billing/credentials/quotas, infrastructure/migration or Task53 change.
