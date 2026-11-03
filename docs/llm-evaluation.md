## Current Task 50E evaluation

The installed Qwen model, original verified prompt/schema, 8K/1,024 bounds, thinking-off, temperature-zero, one interpretation per new text and startup preparation remain. No safe inference optimization was retained: compact candidates lost destinations, a shared-prompt projection invented constraints, and an effective-contract-correct adaptive candidate worsened p90/worst latency despite a lower median. Qwen latency acceptance remains open. A golden payload test protects the retained accuracy baseline. Structured edits/exploration remain model-free. Existing tooling now records actual per-row options; `scripts/benchmark50e.py` supplies controlled matched measurements. Reload/build-contaminated runs are excluded. [Measured results, semantic matrix and explicit limitation](task50e-consolidated.md). Historical measurements below retain their original context.

# Interpretation model evaluation — October 30, 2026

No model was switched or downloaded. No paid inference or Google calls were used. This evaluates language extraction and deterministic validation, not venue supply or routes. Recommendations below are hypotheses where no local comparison exists.

## Verified current configuration

- App default and locally installed baseline: **`qwen3:4b`, 4.0B, GGUF Q4_K_M**. Installed digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`; disk size **2,497,293,931 bytes**. Do not confuse it with Qwen2.5 or a cloud tag.
- Local model metadata identifies the Qwen3 Thinking **2507** artifact; the app explicitly sets `think=false`. The tag/digest above identify the tested installation.
- Local Ollama **0.35.1**, Apple **M2**, **16 GiB unified memory**, Mac14,15 (read-only checks). The metadata advertises a larger architecture context; actual app inference is **8,192 tokens**, not the advertised maximum.
- `backend/ai/ollama.py`: `/api/chat`, Pydantic JSON schema in `format`, seven fixed examples, `stream=false`, `think=false`, temperature 0, `num_predict=1024`, keep-alive five minutes. App timeout defaults to 60 seconds. No automatic model/provider retry or fallback interpreter.
- Pydantic rejects extra keys, invalid values and duplicate JSON fields; incomplete/truncated output is rejected. Source-grounded activity order, dates, exact travel scope/comparisons and manual overrides are validated afterward. A schema-valid answer can still omit a neighborhood or misunderstand intent.
- [Ollama's structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs) describes JSON schema/Pydantic validation. Schema enforcement alone does not establish factual or semantic accuracy.

## Dataset and method

`backend/evaluation/cases.json` contains **26 authored cases**, with expected normalized activities, ordered repetitions, destination/clarification and applicable travel/geographic/date/accessibility expectations. It covers dining/nightlife, custom activities, movie synonyms, neighborhoods/boroughs, GSIW, near/around-me, separate manual-origin wording, strict/flexible minutes/miles, no-Virginia, wheelchair access, explicit/relative dates, Kothapet, Hindi-English, informal grammar, ignored people and unverified budgets. These are synthetic test inputs, not personal history.

The runner checks localhost and the already-installed model inventory, refuses uninstalled models, uses the unchanged app adapter, and blocks `requests` provider sends while exercising interpretation. It never calls venue discovery. Each run has 26 cases plus repeats of the first three, serially. Expected clarification is scored separately from accepted planning. “Kal” deliberately requires date clarification because the deterministic calendar parser does not verify Hindi relative dates. The runner records extraction versus validation outcomes and timings. Temperature 0 is not a guarantee of identical output across model/runtime versions.

Run from `/Users/rahularutla/Documents/whereto`:

```sh
backend/.venv/bin/python -m backend.evaluation.run --real-validation --output /tmp/whereto-llm-results.json
```

This temporarily tests real-mode interpretation policy **inside the runner only**, with provider HTTP sends blocked. It does not persist or activate website live flags. The first baseline used the default mock validator to expose mode-dependent failures; the real-validation run separates them. Result artifacts contain only authored-case metrics and model metadata, never Google content.

## Measured results

The initial run passed **23/26 combined checks**, with **26/26 schema-valid responses**, **26/26 normalized activity/order checks**, and **25/26 exact destination checks**. Cold first request (model absent from `/api/ps` beforehand) took **14.092 seconds**. Median subsequent requests was **5.331 seconds**, including three repeated cases. Those repeated cases preserved the tested activities/destinations/outcomes; their latency increased under concurrent local test/build workload, so this is not an isolated throughput benchmark.

The loaded model allocation reported afterward was **3,800,291,082 bytes**, all reported as VRAM/unified allocation, at context 8,192. This is **not measured peak process/system memory**; tokenizer, runtime, KV allocation, macOS and other applications add overhead. No reliable continuous peak-memory measurement was obtained.

Three failures need separate interpretation:

1. Kothapet, Hyderabad was shortened by the model: a genuine locality-extraction weakness. Deterministic preservation may recover a clearly grounded clause, but should not invent geographic knowledge.
2. Correctly extracted Manhattan plus a different manual-origin city triggered an unnecessary location uncertainty/follow-up downstream. A stronger model does not automatically fix validation policy.
3. Wheelchair access was rejected by mock-mode essential-requirement validation; the separate real-policy run also exposed a redundant model uncertainty despite a clearly stated requirement. Real-mode validation now retains that explicit requirement with a verification note. Unknown support is never confirmed access, and known incompatible venues remain excluded.

The baseline does not prove complete hallucination detection or all-language support. Only the authored fields/cases were scored. It does not measure Google coverage, time-to-itinerary, actual origin confirmation, venue quality or cold performance for alternative models. Per-case results are in `backend/evaluation/results-qwen3-4b-baseline.json`.

## Final measured run after validation fixes

The final real-policy run produced **26/26 schema-valid**, **26/26 normalized activity/order**, **25/26 exact raw destinations**, **25/26 combined raw-extraction checks**, and **26/26 validated-pipeline checks**. The remaining raw mismatch was `Kothapet` versus `Kothapet, Hyderabad`; the existing source-grounded destination normalizer recovered the full explicitly stated clause. The origin and wheelchair uncertainty fixes are narrow deterministic validation changes, not prompt tuning or a model replacement.

Cold first request took **14.320 seconds** (model absent from the resident inventory before the run); median subsequent latency was **6.162 seconds**, including three repeated cases. All three repeats preserved the checked fields/outcomes. Runs were not isolated from other development workload. The initial real-policy run before these fixes also passed 23/26; its warm median was 11.401 seconds under concurrent checks, illustrating why these timings are observations rather than a throughput guarantee.

`backend/evaluation/results-qwen3-4b-final.json` preserves per-case outcomes, model digest, dataset and unchanged adapter hashes. One evaluation comparison was corrected after capture: the validated canonical `near me` must count as correct for an authored `around me` request. No model output or timing was changed. The reproducible runner now applies that same comparison. Measured loaded allocation remained 3,800,291,082 bytes; peak memory remains **not measured**.

26/26 on a small authored set is not general accuracy, exhaustive hallucination detection, or proof that every paraphrase is supported. No alternative model was benchmarked. The last budget source-grounding regression separately verifies that removing cost follow-ups cannot introduce an unstated numeric cap; unverified monetary intent is never certified as affordable.

## Alternatives researched, not locally benchmarked

Download sizes are snapshots from official Ollama tags, **not RAM requirements**; tags can change. For a 16-GiB Mac, one quantized 4B model is the conservative first comparison. An 8–9B candidate may fit at modest context but leaves less headroom for Next.js, Python and macOS; actual memory/latency must be measured before claiming practicality. No universal tokens/second estimate is supplied.

| Candidate | Official tag snapshot / license | Potential benefit and trade-off | Local result |
|---|---|---|---|
| Current Qwen3 4B | Installed 2.50 GB Q4_K_M; current adapter/schema | Existing predictable integration; measured locality weakness | Baseline measured above |
| Qwen3 8B | 5.2 GB Q4_K_M, Apache 2.0 | Same family, more parameters; more memory/latency, no proven app improvement | Not installed/tested |
| Qwen3.5 4B | Library lists distinct runtime artifacts around 3.3/4.0 GB, Apache 2.0 | First candidate for newer instruction/multilingual behavior at a smaller footprint; verify exact runtime tag | Not installed/tested |
| Qwen3.5 9B | Library lists Q4/runtime artifacts around 6.6/7.6 GB, Apache 2.0 | Possible stronger extraction; tighter 16-GiB headroom | Not installed/tested |
| Llama 3.1 8B instruct | 4.9 GB Q4_K_M, Llama community license | Independent instruction baseline; license conditions and language coverage differ | Not installed/tested |
| Gemma 3 4B IT | 3.4 GB current Q4_K_M tag, Gemma terms | Alternative multilingual instruction model; vision isn't needed here | Not installed/tested |
| Ministral 3 8B | 6.0 GB Q4_K_M, Apache 2.0 | Official JSON/system-prompt capabilities, edge focus; larger memory | Not installed/tested |

Sources: [Qwen3 8B tag](https://ollama.com/library/qwen3:8b), [Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b), [Qwen3.5 9B](https://ollama.com/library/qwen3.5:9b), [Llama 3.1 8B](https://ollama.com/library/llama3.1:8b), [Gemma 3 4B](https://ollama.com/library/gemma3:4b), [Ministral 3 8B](https://ollama.com/library/ministral-3:8b). Licenses should be rechecked for intended distribution/deployment.

Published Qwen and Gemma model cards provide general language/instruction evaluation; those are author-reported benchmarks, not Where To? results, not Q4 accuracy on this M2, and not proof of geographic correctness. In particular, a library page's large flagship-model benchmark table must not be attributed to its small 4B/9B variant. [Qwen model card](https://huggingface.co/Qwen/Qwen3-8B), [Gemma model card](https://huggingface.co/google/gemma-3-4b-it).

Other installed models were found (Llama3.2 latest 3.2B Q4_K_M, DeepSeek-R1 1.8B Q4_K_M and Gemma3 270M Q8_0). They were not tested or represented as stronger candidates. No additional download was authorized.

## Recommendation and future architecture

**Keep Qwen3:4b for current development; evaluate, rather than adopt, a newer/stronger candidate.** Fix the demonstrated strict-alternative/search-priority bugs independently: none is an LLM routing failure. The measured small dataset warrants targeted locality/uncertainty improvement, not a claim that passing this small final dataset is sufficient for production.

After separate approval, obtain one exact Qwen3.5 4B local quantized tag, then run this same dataset/settings three times and a held-out paraphrase set, including more Indian localities. Compare exact locality retention, unnecessary/necessary questions, malformed output, strict/flexible scopes, warm/cold latency and real peak memory under normal app load. If it does not materially improve semantics, test Qwen3 8B or another family before considering paid hosting. Do not tune prompts per candidate to manufacture a comparison advantage. Preserve old results/version/digest and review any change separately.

Future deployment should retain the provider-neutral `AIProvider` boundary and deterministic date, travel, source and manual-precedence validation. A hosted model is an independently authorized privacy/cost decision, with explicit server-side credentials, request limits and no hidden fallback. Existing deterministic checks already provide the useful hybrid separation; a second speculative parser/model call is unnecessary now. The model must not resolve exact landmark coordinates, invent session availability or override confirmed origins. Task 47 remains unstarted.

## Task 50A — complex semantic extension

The same installed Qwen3 4B, temperature zero, 8192 context/1024 output bounds,
thinking-off and one-shot preparation are retained. The structured projection
now requires every journey/stop constraint field (nullable when absent); generated
clock minutes and conflict flags remain Python-only. Initial optional nested
fields were insufficient: schema-valid replies omitted dwell/whole-trip constraints.
Source validation refused them rather than producing incomplete itineraries.
Curated examples cover ordinary requests, exact places, brands, optionality,
ordering, endpoints, budgets/deadlines, dwell times and ambiguity. Two redundant
ordinary examples were replaced to limit prompt growth. The regression runner
scores structured meanings and safe execution outcomes, not JSON validity alone.

See [contract and reproducible commands](complex-interpretation.md). Final bounded
accuracy, timings and evaluation limits are recorded in HANDOVER.md. No new model,
provider, dependency, Google operation or persistence change is introduced.
