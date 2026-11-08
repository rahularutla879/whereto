# Task 52B Phase 1 — November 8 offline ordering and scoring review

Baseline: `61ea4284756840895d04c0608d2cdbc72277fd9d`. **Zero new inference, counting or account API requests.** Only public documentation was fetched. No production code, active evaluation prompt/schema/adapter, Qwen settings or corpus changed. [Immutable-output replay](task52-offline-replay.json), [unactivated prompt proposal](task52-prompt-proposal-v4.json), [synthetic offline holdouts](task52-offline-holdouts.json). Historical measurements and dispositions remain labeled in [the benchmark](task52-cloud-model-benchmark.md).

## Diagnosis and recommendation

Source: “Go to the pharmacy first, then the supermarket.” The output's two required stops are `the pharmacy` and `the supermarket`, source-order occurrence indexes0 and1. Its directed edge0→1 predicts the intended dependency, but `order.source="first, then"` identifies neither stop. Stop evidence belongs to each individual occurrence; it does not automatically supply the separate edge's provenance.

`Journey.consistent` validates index bounds, cycles and ordering consistency; it cannot prove the graph came from the source. `validate_journey` independently checks source spans, required occurrences, stop/evidence consistency and relationships. Each edge must have a grounded ordering cue and contain both referenced stop phrases. This rejection is **correct under the intentional established contract**. The current prompt says edge evidence must be verbatim but does not explicitly say it must include both stops: insufficient generated evidence plus an instruction/contract gap, not a JSON Schema syntax defect.

The interpretation boundary invokes this guard before ordinary planning or an advanced handoff. Missing/ambiguous context remains clarification; no route is produced from the rejected result. A valid partial/reverse/flexible graph goes through advanced context, whose routing/timing components enforce occurrence-index ancestor constraints. Ordinary linear planning cannot enforce an arbitrary partial graph; `validate_journey` routes such cases to the advanced path. Downstream enforcement respects the supplied graph; it cannot repair an incorrectly extracted graph.

| Approach | Benefit | Risks / disposition |
|---|---|---|
| A: clarify model instructions | Aligns generated edge evidence with existing contract; no output schema/runtime change | May still fail, needs a separately versioned live sample and full counts; long relationships must fit existing500-character source cap. **Recommended proposed change.** |
| B: separate stop spans plus cue span | Could represent long or noncontiguous relationships precisely | Would need a new occurrence-bound provenance schema, independent span validation, direction/scope grammar, repeated-name disambiguation, overlap handling and migration. Substrings or concatenated quotes alone do not prove a relationship. **Not implemented or recommended for this checkpoint.** |
| C: keep strict validator and reject insufficient evidence | Preserves current safeguards and Qwen compatibility | Safe failures reduce usable accuracy; does not solve model reliability alone. **Retained, combined with proposed A.** |

Existing validation is deliberately bounded, not a general language theorem prover. In particular, a reversed `before/after` quote is rejected by the production guard; an incorrectly reversed index graph with a full `first, then` quote can reach a grounded advanced handoff. The strict semantic graph comparator rejects that graph against reviewed expectations. Repeated identical names can also leave an occurrence relationship ambiguous despite containing both strings. Tests expose these limits; do not declare universal ordering safety or treat a full quote as sufficient qualification. No production validator was relaxed or strengthened here. Broader ordering hardening, if pursued, needs its own reviewed scope.

## Conservative article comparison implemented offline

New opt-in `scripts/cloud_model52_offline.py`, scorer `52b-semantic-v3-source-bound-generic-the`, leaves historical v2 `score`, audit correction/recovery and the paused paid runner unchanged. It constructs a comparison copy only; raw output, trusted interpretation and financial evidence are untouched.

The only additional equivalence is lower-case **`the X` versus `X`** where:

- X is in a finite existing generic vocabulary and the production alias table, and both phrases resolve to the same existing activity category.
- Both gold and actual stops have `kind=activity`, the same required/optional status, matching activity/source lists and the same number of occurrences.
- Both exact original-case phrases occur at source-order, word-boundary spans; the longer span is precisely `the ` plus the shorter span for that same occurrence.
- All other properties remain compared strictly. Source evidence is still audited against the original actual stop occurrences and unchanged trusted rules.

This is not general category matching or blind article stripping. Named places, brands, capitalized proper names, arbitrary labels, modifiers, verbs, singular/plural changes and a/an do not get this exception. `coffee shop` is not equated with `coffee`, even though they share a category. “The Pharmacy” and “The Coffee House” keep their exact identities. Unprovable repetition-count or ambiguous span mappings stay strict for review. Required/optional differences, lost occurrences, relations, return and deadlines cannot be repaired by this projection. This normalization is **not used in production** or the active paid scorer.

Empty/omitted **reference evidence** still means unspecified exact quotation. Nonempty actual evidence must own the right source occurrence; optional provenance remains required; an explicitly nonempty gold evidence string remains exact. Missing actual required properties fail structural auditing. The offline audit also rejects `journey:null`: local legacy parsing permits null, but the strict evaluation wire requires an object. This stricter wire check changes none of the four recorded responses and leaves historical v2/local compatibility untouched. Valid JSON is not full correctness. A rejected output cannot count as correct extraction; incomplete rubric judgments fail. Automated scores keep `fullyCorrect=null`/`reviewRequired=true`; agent rubric inspection is separate from independent human signoff, which remains outstanding.

## Replay of the four original v3 OpenAI responses

| Original r1 slot | Structured | Trusted source validation | Provenance | Offline v3 semantics / effect |
|---|---|---|---|---|
| journey-01 | Valid | Accepted | Valid for all applicable facts | All automatic assertions pass; correct under prior agent rubric; no new semantic-score change |
| ordinary-dinner | Valid | Accepted | Valid stop sources; empty required-stop extra evidence permitted | Assertions pass; prior correct agent disposition unchanged |
| journey-03 | Valid | Accepted advanced handoff | Exact SUNY identity and source clause preserved | Assertions pass; prior correct agent disposition unchanged |
| journey-07 | Valid | Rejected | Stop spans grounded; edge provenance insufficient | Article-only flags removed; trusted disposition/clarification mismatch remains; **safe failure**, never correct extraction |

No proposed prompt or schema can retroactively change a recorded output. A separate **hand-authored fake output** with a full relationship quote passes the Journey contract in regression testing; it is not a model response, repaired historical score or evidence the model will follow the proposal. Actual four timings, token usage, hashes, original classifications and reservations are unchanged. Original journey-01 remains a recorded historical decoder `provider_error` plus independently verified append-only correction, not a rewritten row.

All21 original baseline raw Qwen extractions in `results-task50e-model-investigation.json` were replayed through unchanged canonical Journey validation:5 ordinary-contract passes,12 advanced handoffs,4 ambiguity/rephrase outcomes. This does not remeasure latency or claim all21 are fully correct. Recorded Qwen baseline/final metadata/results, all19 examples, runtime adapter hash and six corpus source hashes are unchanged; no local model invocation. Existing Qwen interpretation/source-grounding regressions are retained.

## Unactivated common prompt v4 proposal

`52b-v4-PROPOSED-order-edge-quotes` appends exactly370 UTF-8 bytes to the existing system message. The exact addition and hashes are in [the proposal](task52-prompt-proposal-v4.json). It asks each edge to quote one contiguous source span containing both referenced stop.source phrases and the explicit ordering cue, use correct occurrence indexes/direction, never infer edges from list order, and preserve ambiguity rather than guessing. No existing instruction or example is removed, reordered or edited. All19 example meanings and the canonical schema are unchanged; all five existing example edges already include their referenced stops.

The same addition is constructed mechanically for all three providers. Active v3 payloads/configuration remain byte-identical, and no live runner imports this proposal. Existing v3 attempts stay in their own comparison cohort, including all failures. Any future prompt/provider-schema revision needs its own configuration identity and original unused slots; no consumed slot can be repeated for prompt tuning or a balanced comparison.

Offline feasibility uses earlier **complete v3 provider counts**, plus370 added UTF-8 bytes, a32-token boundary allowance and existing headroom: OpenAI7,527; Google8,236; Anthropic11,845 versus12,000. **These are planning estimates, not exact or certified new complete-input counts.** Provider tokenization/injected formatting may differ; no tokenizer or provider counting endpoint was invoked. Future readiness must count every complete proposed request with schema/formatting overhead before any inference. Output stays2,000; no cap increase. Counts cannot prove schema compilation.

Four separate synthetic contract holdouts were authored after the rule/proposal freeze and not used to tune the addition. They test before, partial order, repeated coffee-shop occurrences and article-bearing named businesses; correct fake outputs pass and cue-only/reversed edges fail. They are not independent blind model evaluation, extra paid corpus scenarios or a98% qualification corpus.

## Google and Anthropic offline compatibility

Public documentation reviewed November8:

- [Gemini structured-output guide](https://ai.google.dev/gemini-api/docs/structured-output) describes grammar complexity and ignored length constraints. Its current examples use **Interactions** and lower-case MIME strings; do not transplant them into generateContent.
- The [generateContent REST reference](https://ai.google.dev/api/generate-content) separately documents `generationConfig.responseFormat.text`, `mimeType=APPLICATION_JSON` and `schema`. These match our reviewed active Developer API envelope. It is not Vertex/managed-model identity or billing. No endpoint/service switch occurred. Public reference bodies were fetched with verified certificates when the documentation browser could not read Markdown.
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) documents grammar-size/internal limits separately from input tokens. Our wire schema has15 syntactic union nodes, zero optional properties and no requested tools. This is not proof of compiled expansion staying below all internal limits. The consumed grammar-size failure remains; no claim that a shorter prompt fixes it.
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) explicitly warns that schema-conforming output may contain mistakes; clearer instructions do not replace trusted source checks.

A **separate unactivated Google wire candidate** moves only array min/max bounds into descriptions to reduce grammar multiplication. All properties, requiredness, types, nulls, enums and references remain identical; existing canonical parsing enforces the original bounds. Static tests compare those structures and reject oversized output. This does not prove the generic400 cause or compatibility; it is not part of the prompt-only v4 proposal and must be counted/versioned separately if ever approved. No Anthropic schema redesign, partitioned multi-call workaround or field removal was implemented.

Unsent support questions: Does this exact generateContent model support the documented format and current schema/reference/union shape? Can support identify the two consumed400 field categories using safe request identifiers supplied privately by the owner? Which array bounds/nesting cause grammar-state growth? For Anthropic, how are15 raw union nodes expanded through references and repeated structures, and what semantics-preserving schema mapping can compile? Supply only approved synthetic schema/hash/model/endpoint/settings and allowlisted error categories through an owner-approved channel; no keys/auth headers/private text. No support message was sent.

## Journal, verification and next gate

The original SQLite file SHA-256 is `d13b585b4821be465be1c635792471072f11f38258f87e2e94126481835e9a45`. Read-only integrity is `ok`; all seven rows and exact root metadata match the pre-work snapshot. Original correction and paid-run plan remain intact. **OpenAI4 /Google2 /Anthropic1, total7/594; $0.039866625 accounted; $11.960133375 remaining.** Original198/provider,12k/2k, concurrency1, retries0 and$12 ceiling unchanged. No new sidecar clears the stopped runner or releases a reservation.

Final test/security results are recorded in HANDOVER.md. The first backend run exposed an expired November7 endpoint fixture; the first complete frontend run had281/283 with two further expired fixture-clock failures. Only test-process clocks were fixed; assertions and production date policy stay unchanged. Full application runtime/build/browser/hosted qualification is not claimed by these offline changes.

**Ready for owner review of the offline proposal, not ready to dispatch the next paid batch.** Required next steps: owner reviews the prompt/scorer/provider proposal; refresh all provider-supported complete-input counts and dated model/account/terms/readiness checks within a separately authorized readiness step; then approve a concrete bounded unused-slot plan preserving the existing journal and historical version cohorts. No model selection, hosting/shared-state work or Task53. No inference, Maps calls, billing/quota/credential/payment changes or database migration occurred.
