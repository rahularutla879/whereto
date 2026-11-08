# Task 52B — offline ordering safety investigation

Baseline: clean `4bcf3bf4bff9ffb48a93f87d466c7a0c2d53b2f6`. **No inference, token counting, account/provider API requests or paid-journal writes. The v4 evaluation remains halted.** This is an opt-in experiment, not a production safety fix or model qualification.

## Failure and contract audit

For “Coffee, museum, then coffee in Jersey City tomorrow, return to the starting point within three hours,” the source-order occurrences are Coffee0, museum1, coffee2. The reviewed mandatory relationship is1→2. The model's additional0→1 quote, `Coffee, museum, then`, ends with the cue introducing coffee2, rather than connecting coffee0 to museum1.

`backend/journey.py` verifies graph consistency, source substring membership, presence of an ordering cue, both stop labels somewhere in the edge quotation, and a few direct reversed before/after patterns. It does not independently attach the cue to its arguments or bind repeated labels in the quote to particular source occurrences. Thus the quote is real, both labels occur, the graph is acyclic and a cue exists, yet the relationship is unsupported. Similar failures include borrowed cues, broad quotations spanning unrelated relationships, reversed then-edges and repeated-label misattachment. Negation, conditional language and event timing (“before bank closes”) also cannot safely become visit dependencies merely because a cue exists.

The canonical schema uses source-order stop indexes, independent `source`/`evidence` strings, required/optional stop status and directed edges. It has no explicit source or cue offsets. Pydantic checks bounds, self-edges/cycles and graph/ordering consistency; these are structural checks, not language proofs. Stop occurrence mapping in trusted validation complements these checks but does not establish each cue's scope. Exact names and named-place requirements are separate obligations.

The advanced handoff preserves the supplied graph. `backend/advanced_routing.py` builds ancestor closure and admits visits only after their required ancestors. An invented edge therefore becomes a real route restriction, even if the model supplied every required stop. Source-order iteration in an unspecified journey is a separate legacy behavior; it does not prove that the owner requested mandatory ordering. Partial ordering must remain a graph, never an invented chain.

Existing contradiction checks detect some explicit reciprocal before-clauses; other ambiguities use clarification. The independent experiment does not replace those checks. V3 already says only explicit order creates edges; v4 adds exact relationship quotes and explicitly forbids list-order inference. The failed v4 output demonstrates that instructions and strict JSON alone do not establish compliance. **No new prompt revision is necessary to specify this already stated rule.** No prompt, example, provider wire schema, runtime validator or Qwen setting was changed.

## Three designs

| Approach | False acceptance | False rejection / compatibility | Complexity and latency | Recommendation |
|---|---|---|---|---|
| A. Independent bounded relation proof | Blocks demonstrated cue/occurrence errors within its tested grammar; not a universal English guarantee | Explicit unknown outside grammar; measured costs below | Small pure local check, no additional model call; finite rules and source spans require maintenance | Implemented offline only; review grammar and Qwen migration before activation |
| B. Stronger provenance schema | Makes occurrence ownership inspectable; offsets alone still cannot prove scope/direction | Model offset mistakes and Unicode conventions can cause safe rejection; all providers/legacy fixtures need migration | Larger output/schema and token overhead unmeasured; no counting authorized here | Concrete future schema proposal below, not implemented or activated |
| C. Keep current contract; reject uncertain relationships | Current production contract alone retains the demonstrated acceptance gap; strict unknown on unproven edges is safer | Greater clarification frequency; no unsupported graph repair | Least schema disruption; no inference overhead | Preserve production now; use offline findings to design a reviewed integration, not to declare current validation sufficient |

The narrowest defensible next design is A **in addition to** canonical validation, with C's explicit clarification behavior when proof fails. Do not infer an edge from a comma, remove an unproven edge to make the request pass, or fall back to weaker validation.

## Implemented opt-in experiment

`scripts/cloud_model52_ordering.py`, version **`52b-order-proof-v1-offline`**, imports only `re`. Runtime, paid runners, approved scorer and prompts do not import it. `inspect_order(source, interpretation)` returns ordering-only proof details or `clarification_required`; it neither mutates the extraction nor generates/replaces edges. A passing result does not establish complete semantic correctness, venue identity, dates, returns, durations, optionality, injection safety or permission to plan.

1. Find boundary-matched stop phrases in the original source with existing case-insensitive identity semantics. Derive actual source offsets/text; do not strip articles, normalize names, merge repetitions or greedily choose the first match. A unique, non-overlapping source-order assignment is required. Longer supplied stop names shield overlapping shorter names. Additional unowned mentions or multiple assignments require clarification. Limit candidate mentions and binding work; exhaustion is unknown, never acceptance.
2. Recognize **anchored connectors between adjacent owned occurrences**: before, after (reverse direction), then/finally/afterward, first-then, adjacent first/second ranks, followed-by, or the existing rightward Unicode/ASCII arrows. Recognized imperative prefixes and narrowly recognized suffixes are required; arbitrary intervening prose is not deleted. A trailing cue after the right occurrence cannot prove the preceding pair.
3. Conditional/negative/optional scope is not promoted to an unconditional mandatory edge. Retraction/flexible-order wording outside owned names requires review. Conditional or ambiguous relations involving optional stops remain unknown. Named cue words do not themselves create relationships.
4. For every model edge, require a proven directed path whose complete stop/cue proof spans occur inside that actual edge quotation. This permits justified transitive consequences, never closure over mere source-list order. Wrong indexes, borrowed quotes and reversed paths fail. Missing independently proven mandatory relationships also require clarification.
5. Preserve existing source clarification/conflict outcomes. Empty graphs pass ordering-only checks for straightforward lists with no mandatory cue; this does not endorse the rest of the extraction.

Offsets are zero-based Python Unicode **code-point** positions, end-exclusive. Returned text is taken from the original source. Current matching preserves the canonical case-insensitive quotation convention; this is not a new byte-exact schema or general linguistic equivalence rule. Supported suffix context is deliberately narrow (for example a source-matching extracted location plus today/tomorrow/tonight); scalar grounding still belongs to the unchanged canonical pipeline. Unsupported discourse, ellipsis, pronouns, distant references and unrecognized modifiers must be reviewed. The finite tests cannot establish arbitrary-language soundness.

## Reviewed test evidence and limits

[31 predeclared source rubrics](task52-ordering-safety-cases.json), [six post-freeze examples](task52-ordering-safety-holdouts.json), [measured checks and per-case proof spans](task52-ordering-safety-checks.json). Rubrics were agent-authored/reviewed before execution, not independently reviewed by the owner or a blind human panel. The separate authoritative66-case paid corpus and all gold expectations remain unchanged.

| Source family | Expected mandatory relationships / safe outcome |
|---|---|
| pharmacy first, then supermarket |0→1 |
| pharmacy before bank / pharmacy after bank |0→1 /1→0 |
| pharmacy before bank; independent coffee |0→1 only; coffee remains required, not automatically optional |
| Coffee, museum, then coffee |1→2 only;0→1 remains unproven |
| Coffee, then museum, then coffee |0→1 and1→2, with proven transitive consequences allowed |
| Museum, then coffee |0→1 |
| Coffee and museum / Coffee, museum, and coffee |No mandatory edges |
| coffee first, museum second, then coffee again |0→1 and1→2; distinct repeated occurrences |
| coffee stop0 before coffee stop1 |Exact distinct referenced occurrences0→1 |
| Similar named venues / arrow sequences |Bind full names/occurrences; preserve explicit direction |
| Correct quote with reversed indexes or extra edge |Clarification, not acceptance |
| Cue-only, fabricated, wrong-occurrence or missing evidence |Clarification or canonical structural rejection |
| Ambiguous before-or-after, optional/conditional order, retraction |Clarification; no guessed graph |
| Unrelated or long intervening prose / global first-last scope |Clear intent may exist, but outside supported grammar; clarification |

Results: **31/31 expected bounded outcomes matched**:18 verified-order cases,3 verified-unordered cases,10 clarification cases. **63 unsupported/reversed/extra-edge probes:0 accepted**. Six post-freeze examples passed against a pinned module hash, including new named-arrow, reverse-after, independent-third, trailing-cue, negation and retraction cases. These examples were authored by the same agent; they are not independent blind qualification. One local diagnostic evaluated the31 fixtures and63 probes in about10ms, including fixture construction; this is neither a production latency measurement nor a worst-case bound.

**False-clarification evidence is explicit:** four of the31 cases have clear ordering intent outside this grammar: an intervening unrelated clause, an intervening parenthetical, first/last scope across a semicolon and a474-character clause. All four require clarification. Their natural-language expected relationships are recorded separately from the empty set of mechanically proven relationships. Other unknown cases concern ambiguity/ownership/conditional/negative/event scope. Do not report “100% semantic accuracy” from31 matching expected gate outcomes or treat unknown as an incorrect confident acceptance. No claim of zero false acceptance outside these finite probes.

## Replay without changing historical classifications

Reproduce with:

```sh
cd ~/Documents/whereto
backend/.venv/bin/python -m scripts.cloud_model52_ordering_replay --output docs/task52-ordering-safety-replay.json
backend/.venv/bin/python -m unittest backend.test_cloud_model52_ordering -v
```

The replay opens SQLite `mode=ro`, disables model/network transport during scoring, checks every ignored evidence-file hash before/after, and writes only the explicitly named report under `docs`. [Separate versioned results](task52-ordering-safety-replay.json) retain original row/classification/configuration/response hashes, charges and the historical decoder correction. A replay acceptance cannot authorize dispatch or clear a halt.

| Recorded OpenAI r1 response | Existing structure / trusted source result | New ordering-only gate |
|---|---|---|
| v3 journey-01 |Valid /accepted via historical audited decoder correction |Verified no mandatory order; original `provider_error` row unchanged |
| v3 ordinary-dinner |Valid /accepted |Verified no mandatory order |
| v3 journey-03 |Valid /accepted named-place handoff |Verified no mandatory order |
| v3 journey-07 |Valid /rejected cue-only evidence |Clarification: original rejection preserved |
| v4 journey-04 |Valid /accepted |Verified exact named-place0→1; full owned quote |
| v4 extension-partial |Valid /accepted |Verified only0→1; independent coffee retained |
| v4 extension-repeated |Valid /accepted historically |Clarification:0→1 unproven,1→2 proven; historical critical failure unchanged |

Five previously correct OpenAI interpretations remain ordering-compatible; neither failed output is promoted. The three Google/Anthropic provider-error rows have no model output to replay; they remain errors, not zero-accuracy extractions. No semantic score, latency, usage or old record was rewritten.

**Recorded Qwen:** replayed21 baseline raw extractions and6 final-runtime smoke extractions from the existing investigation fixture. Baseline:2 verified-order,8 verified-unordered,11 clarification. Final smoke:1 verified-order,1 verified-unordered,4 clarification. This is ordering compatibility, not overall extraction correctness.

Of15 ordering unknowns across27 Qwen rows, **six** are clear order expressed by “first and then head out for coffee,” outside this narrow grammar. Three were already canonically blocked for other omissions; **three would become new clarification outcomes** despite previously nonblocking Journey validation. The other nine raw graphs contain unsupported list edges: seven are currently removed by the existing deliberate no-cue legacy normalization, while two repeated-coffee outputs retain the same accepted extra-edge problem. Rejecting raw model graphs is intentionally stricter than silently calling normalized output model-correct. These differences require a reviewed migration decision; **automatic production activation is not justified by this checkpoint**. Qwen instructions/settings and historical fixtures remain byte-identical.

## Stronger provenance and production integration proposal

A future schema version could add immutable source hash, stop occurrence identifier, stop start/end offsets, cue start/end offsets, relationship direction, exact supporting clause and explicit ambiguity status. Server checks must independently validate integer bounds, Unicode index convention, exact source slices, phrase ownership, non-overlap, occurrence multiplicity and the declared direction. A claimed offset is not trusted evidence. The same bounded cue/scope proof is still needed: the failed quote has valid offsets but the wrong relationship. Discontinuous snippets cannot manufacture a relationship across unrelated clauses.

This schema is **not implemented**. Canonical `extra=forbid` means it requires a versioned provider projection/parser migration, legacy handling, all19 examples/fixtures, Unicode/emoji tests and separately authorized full-input/output-budget checks for all providers. No token estimate or successful schema compilation is invented. Uncertain offset mapping must clarify rather than guess. Offsets are not presently needed to reject the known failure, so avoid that migration until its benefit is demonstrated.

A concrete future integration sequence, requiring owner review:

1. Review these source rubrics, the four clear out-of-grammar cases and the Qwen migration differences. Extend only explicitly justified finite grammar with positive/negative tests; use a new validator version and retain these replay results. Obtain independent semantic review before claiming qualification.
2. Exercise a shadow, non-admitting comparison over a broader reviewed offline corpus, including negation/retraction, temporal-event references, optionality, remote mentions, Unicode and all actual ordinary/advanced saved-plan regressions. Do not tune the authoritative66-case gold outputs.
3. Only in a separately approved production integration, insert the extra gate after strict parsing and before advanced handoff/session creation or provider/routing admission, retaining raw extraction for auditing. It must complement all current identity/date/duration/return/source checks and return explicit clarification for unknown. Decide legacy no-cue normalization explicitly; do not silently strip an uncertain edge or reinterpret an unsafe graph as successful model extraction. Keep cloud/provider activation disabled by default and local Qwen unchanged until its compatibility policy is reviewed.
4. Run full backend/frontend/typecheck/lint/build and application verification for that runtime change. Rollback disables the new/cloud interpretation path or keeps affected requests in clarification; it must not silently fall back to the known weaker acceptance or another model. Preserve journal history and persistent halt; a passing replay never grants paid admission.

**Next recommended qualification step is this owner/offline compatibility review, not another paid batch.** The current v4 prompt already states the intended rule; more prompt tuning is not a substitute for independent validation. Any future prompt change, provider projection, paid continuation or halt adjudication requires its own reviewed version and authorization. No production model selection or infrastructure work is supported.

## Journal, other providers and verification

Original paid SQLite file remains byte-identical SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`, integrity `ok`; all10 row hashes, root metadata and all324 ignored files unchanged. The decoder correction, original errors, v3/v4 configurations, reservations, provider evidence and persistent v4 `recorded_halted`/halt sidecar remain intact. Direct read-only recovery validation refuses the halted continuation before any provider transport.

Counts remain **OpenAI7 /Google2 /Anthropic1 =10/594**, remaining584 (191/196/197 per provider). Accounted **$0.047366625**, remaining **$11.952633375**. No reservations, refunds or requests. Original $12/594/198/12k/2k/concurrency1/retries0 limits unchanged. No new journal, override or approval sidecar.

- **Gemini Developer API:** two historical generic400 causes remain unproven; the separate last-readiness IP-denial remains. Next independent action: owner verifies authorized egress against the existing restriction without broadening it, then separately reviews the exact Developer API model/envelope/schema or authorizes a sanitized provider-support inquiry. No speculative call, permission/API enablement or Vertex substitution. Do not touch Maps.
- **Anthropic:** grammar compilation rejected the current schema although input length fits. Next independent action: review the unactivated semantics-preserving grammar-factorization proposal or obtain owner-approved provider-support evidence for the schema/model/endpoint. Keep every canonical field and bound; compiler success and new token counts are not established by this work. No inference or automatic schema activation.

Final suite/security/diff results are recorded in HANDOVER.md. No runtime change, hosted database work, private-data submission, credentials/billing/quota/Maps change, deployment, production provider switch or Task53. Stop for owner review.
