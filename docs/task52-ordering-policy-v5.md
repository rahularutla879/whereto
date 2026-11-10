# Task 52B Ordering Policy V5 — offline owner-policy proposal

Policy `52b-order-policy-v5-offline`; scorer `52b-semantic-v4-owner-list-order-PROPOSED`. Started clean `a7ed1066fe3c082dd6e9b48dbfdfa58f53b610f8`. The owner explicitly changed the product requirement: a complete chronological activity list implies visit order. This is a new policy, not a correction to the frozen V4 findings. No production behavior, model instructions or evaluator authority changes here.

## Source-first decision contract

The independent offline implementation is `scripts/task52_ordering_v5.py`. It first binds each proposed stop to a unique original source occurrence using the frozen bounded occurrence binder, then classifies the entire source independently of the model graph. A valid substring or nearby cue alone never proves an edge. Inputs are bounded to 8,000 characters/32 stops, occurrence matching retains its existing bounded search, and a model edge quote is limited to 500 characters. Unconsumed or uncertain source scope returns unknown/clarification; no invalid edge is silently deleted.

| Source form | V5 relationship | Boundary |
| --- | --- | --- |
| Coffee, museum, dinner; Coffee and museum | Consecutive source occurrences ordered, including transitive consequences | Complete bounded itinerary syntax, not an arbitrary conjunction or mention |
| Coffee, museum, then coffee | 0→1 from comma/list evidence; 1→2 from then evidence | Three distinct source occurrences; trailing then cannot justify a different explicit relationship |
| Coffee, then museum, then dinner; directional arrows | Consecutive explicit order | Correct direction and occurrence ownership required |
| Pharmacy before bank; coffee whenever convenient | Pharmacy→bank only; coffee required and independent | Explicit partial order overrides list default |
| Dinner and bowling, in any/either order | No mandatory edge | Suffix scopes a complete plain list; conflicting explicit then/start/finish is not erased |
| Museum after dinner | Dinner→museum | Explicit relation takes priority over mention position |
| Maybe coffee, then dinner | Coffee stays optional; coffee→dinner applies if coffee is visited | Leading maybe without explicit then has ambiguous group scope and clarifies |
| Coffee, maybe museum, dinner | Conditional edges through optional museum, required coffee→dinner consequence | Proposed conditional semantics need case review and future planner integration |
| Start with coffee, visit museum, finish at pharmacy | Coffee first, pharmacy last; required closure 0→1, 1→2, 0→2 | Only bounded two/three-visit forms; no inferred home/origin identity |
| Visit museum, then return to the starting point | One visit plus separate return requirement | Return is not another activity; non-order endpoint validation remains mandatory |
| Nested groups, quoted/negated/hypothetical lists, conditions, unowned headings or qualifiers | Unknown/clarification | No general-purpose language parser or prompt-injection exception |

Bare lists and finite imperative prefixes (including Do/Plan, visit/get/buy/go to) are supported. Connectors include comma, Chinese comma, and, then, →, ⇒ and ->. Explicit before/after, ordinal and bounded fronted clauses delegate source analysis to the unchanged V4 grammar. Unscoped multi-stop before/after language remains unknown. Local “whenever convenient” leaves the activity required but excludes it from mandatory placement. “Maybe/optionally” changes only a demonstrably owned occurrence. Flexibility never implies optionality.

For optional visits, **the proposed graph is conditional on the visits occurring**. Compute source-proven transitive closure before restricting to selected visits: skipping an optional middle stop must neither force its attendance nor lose order between required surrounding stops. This proposal does not implement those semantics in the production planner. Case-level owner and independent review remain required.

## Evidence and graph semantics

Each frozen evidence record binds policy, original source SHA256, occurrence indexes, exact code-point span/text, connector/cue span, direction, rule, conditional status and an evidence digest. Model assertions are reported separately from source-required closure and implied relationships. The model must include enough evidence to encompass the proven relationship. A chain 0→1→2 proves 0→2; redundant direct edges are unnecessary, but an asserted transitive edge still needs a source quote covering its proof path. Missing required reachability and unsupported extra edges both reject. Raw outputs are never repaired or overwritten.

This is ordering-only verification. Exact names, activities/multiplicity, required/optional status, endpoints, geography, calendars, duration relations, budgets and every other source requirement still need canonical non-order validation. A V5 ordering pass supplies no planning admission, financial authority or independent semantic signoff.

The replay compares raw and effective legacy snapshots separately. Mapping is known only when occurrence source/kind/status, endpoint and total duration survive unchanged. Unknown mappings fail closed. An unchanged occurrence mapping does not prove required order survived: the effective graph is checked separately. Legacy no-cue normalization can erase V5 list order. V5 has no application import or enforcement hook; legacy remains authoritative and V4 shadow remains default-OFF.

## Frozen rubric amendment and 66-case impact

[Proposed full rubric](task52-q1-rubric-v2-owner-list-PROPOSED.json) has identity `52b-q1-rubric-v2-owner-list-order-PROPOSED`, parent `52b-q1-qualification-v1`, all original 66 sources and 24 dimensions. [Predeclared impact decisions](task52-v5-rubric-impact-decisions-v1.json) are separate from automatic recognizer coverage. [Full per-case impact](task52-ordering-v5-all66-impact-v1.json) records original/proposed closure, source evidence, changed fields, pending judgments and implementation limits.

* 18/66 mandatory graph amendments, 1/66 conditional-order amendment (journey-06).
* 1/66 conditional candidate awaiting owner judgment (extension-inclusive); its original unresolved field is unchanged.
* 1/66 additional language/order judgment (ordinary-multilingual); no English-only inference about “aur”.
* 45/66 graphs unchanged. Thus 19 concrete graph amendments, two further pending cases; not 21 approved graph changes.

All six original Q1 unresolved field judgments remain intact. All 66 individual gold approvals and seven original response signoffs remain outstanding. Three cases explicitly require new owner judgment: journey-06, extension-inclusive and ordinary-multilingual. General approval of list order is not approval of optional projection details or individual cases. The copied full rubric preserves non-order facts and original unresolved records; changed ordering/provenance fields are explicitly proposed, never relabeled historical gold.

Source recognizer coverage is a different denominator: 36/66 recognized categories and 30/66 unknown. Unknown includes clear requests outside this finite grammar, not only linguistic ambiguity. Duration annotations, some budget/accessibility context, implicit semicolon groups and unowned geography/date phrases require further bounded review; no claim of production integration readiness or universal natural-language accuracy is made. Definitive proposed reference semantics do not falsely imply the implementation proves them.

## Recorded response reassessment

[Seven OpenAI and 27 Qwen comparisons](task52-ordering-v5-historical-replay-v1.json) retain original hashes, prompt cohorts and findings. Original paid responses are read only; complete current B2 results reproduce Q1 identities at its fixed clock. This is approved behavioral reconstruction, not exact historical Python/dependency reproduction.

| OpenAI slot | Frozen V4/Q1 finding | New V5 ordering / unchanged legacy combination |
| --- | --- | --- |
| journey-01/r1 | Correct under former agent rubric; historical decoder correction preserved | Missing new dinner→drinks relationship; blocked |
| ordinary-dinner/r1 | Correct under former agent rubric | Missing new dinner→drinks relationship; blocked |
| journey-03/r1 | Correct named visit | Compatible candidate only |
| journey-07/r1 | Source-provenance rejection | Still rejected: “first, then” identifies neither stop |
| journey-04/r1 | Correct named college→coffee | Compatible candidate only |
| extension-partial/r1 | Correct partial order, independently required coffee | Compatible candidate only |
| extension-repeated/r1 | Historically accepted **critical invented 0→1 edge**; V4 guard rejected | Both 0→1 and 1→2 now have V5 proof; candidate only |

For extension-repeated, the exact same raw quotes are rechecked: “Coffee, museum, then” contains the owned first pair and the comma evidence for default list order. Its trailing then is **not** reattributed as their temporal cue. The valid museum→later coffee proof, all three visits, return to confirmed origin, inclusive 180-minute limit, Jersey City and tomorrow remain. No additional non-order error was found in the retained agent findings, but full independently reviewed correctness is still null. The original accepted unsafe V4 classification, stopped row and persistent halt remain unchanged. All seven outputs remain historically structurally valid; five historical agent-correct outputs are not silently relabeled V5 qualified.

Qwen: V4 ordering compatible 25/27 (including audited projections), V5 raw ordering compatible 19/27; transitions 17 compatible→compatible, 8 compatible→blocked, 2 blocked→compatible. Only 8/27 also preserve V5 order through unchanged legacy journey processing. Five originally reviewed correct V4 graphs now fail new V5 expectations; six former raw ordering errors become V5 ordering-compatible, which is not a claim of complete extraction correctness. These are mixed historical fixtures, not an accuracy estimate. No historical score is overwritten.

## Q3/Q4 compatibility and next checkpoint

The old Q3 artifact remains byte-for-byte frozen and is superseded **for future V5 evaluation only**. [Amended proposal](task52-q3-openai-v5-PROPOSED-v2.json) keeps exactly extension-repeated/r2 → journey-04/r2 → extension-partial/r2 → journey-06/r2 → journey-21/r1. No slot is sent or newly authorized; proposed maximum remains five/$0.0125, subject to later actual prices and approval.

The existing 370-byte v4 instruction says “Never infer edges from list order.” It directly conflicts with the owner decision. No prompt, example meaning or canonical schema is changed here. Future prompt/configuration/payload/build identities are null, all five slots inadmissible. A separately reviewed prompt/examples proposal is necessary before V5 testing. Q4A–Q4C remain frozen V4 offline engineering evidence and signature contracts, not V5 authorization. Future work needs a new purpose/source/build, case review, current readiness and exact owner approval, with the original halt preserved.

Recommended next bounded checkpoint: owner/independent review of this V5 decision table and impacted rubrics, including optional projection and unresolved language scope, followed by a separately scoped prompt-only amendment proposal. Do not expand validation extraction or activate production enforcement. Gemini remains blocked on Developer API HTTP400/IP evidence; Anthropic remains blocked on schema grammar compilation.

## Verification and limits

See [verification](task52-ordering-v5-verification-v1.json), [version manifest](task52-ordering-v5-manifest-v1.json), 38 predeclared cases, eight same-agent post-freeze cases and the test module. Holdouts are separated from implementation tuning but are not independent human review. Original V1–V4 expectations stay frozen; their old list-order negative labels are not incorrectly reused as V5 gold. Local timing is not cloud/app latency. No model has passed production qualification.

All 324 private files and the ten-row journal/corrections/halt are preserved: OpenAI7/Google2/Anthropic1, 10/594, $0.047366625 retained/$11.952633375 remaining. Original six source pins/corpus/schema/paid evaluator unchanged; it still refuses B2. Original $12/594/198/12k/2k/concurrency-one/zero-retry caps apply. No real request, reservation, enrollment, approval, runtime enforcement, provider/model/prompt, Maps, billing, quota, infrastructure, migration or Task53 change.
