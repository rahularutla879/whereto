# Task 52B Ordering V5.1 — confirmed owner rules, offline proposals

Policy **`52b-order-policy-v5.1-owner-decisions-offline`**, scorer `52b-semantic-v5.1-owner-decisions-PROPOSED`. Baseline verified clean `2f2d9395d20b4cc1aaf86b707fbdf479e22352f6`: V5 commit b1efe96 plus the separately committed learning handbook. No handbook file is edited or included in this checkpoint. V5 and original V1–V4/Q1/Q3/Q4 artifacts remain frozen.

## Confirmed semantics

| Owner decision | Consequence | Safe boundary |
| --- | --- | --- |
| A: complete activity lists imply chronology | Coffee, museum, dinner and Coffee and museum produce source-occurrence precedence | No order from mentions, examples, quotes, hypotheticals, negation, headings or injection |
| B: optional stops preserve sequence if selected | Coffee→optional museum→dinner; omitting museum retains coffee→dinner | Optional attendance is never made mandatory; uncertain qualifier scope still clarifies |
| C: flexible placement is not optionality | Pharmacy→bank; coffee whenever convenient leaves required coffee independent | No edge attaches flexible coffee to either stop; explicit partial scope takes priority |
| D: reviewed multilingual connectors | Whole-word Roman-script Hindi aur between owned activities means and | No substring match, arbitrary transliteration, identity translation or unfamiliar grammar |

Explicit before/after/first/last/start/finish relations take priority over conflicting list defaults. Explicit unordered or flexible instructions override defaults only in their verified scope. Contradictory/conditional/unknown scope clarifies instead of fabricating a valid graph. Repeats retain separate source occurrences. Return and separate terminal geography remain endpoint constraints, not additional visits. Optional and flexible groups are different concepts.

## Bounded implementation and immutable evidence

`scripts/task52_ordering_v51.py` reuses frozen V5 source analysis for English, preserving its 8k-character/32-stop bounds, occurrence ownership, qualifier handling and source-first classification. The frozen V5 implementation is not edited. The V5.1 graph/evidence verifier is separately versioned: every model assertion and required reachability must be proven; unsupported edges are not dropped. An already supplied transitive chain is sufficient, without redundant direct edges.

For aur only, a private same-length analysis view replaces whole-word tokens strictly between already bound source occurrences with and. An exact existing corpus frame, **Kal Hyderabad mein [list] plan karo**, is additionally recognized for ordering only. It neither resolves Kal nor translates activities. Unknown city/Hindi frames, aurora/gaur, Devanagari connectors, unreviewed words and ambiguous code-switching remain unknown. English-style location/date suffixes retain V5's bounded rules; they do not prove geographic identity or resolve dates.

The analysis view never replaces the original request or model output. Stop objects and edge quotes are unchanged. Occurrence/cue offsets refer to the original same-length source; evidence text and SHA256 are reconstructed from the **original** source and bound to the V5.1 policy. A quote saying and when the user wrote aur fails. Cue-only, wrong occurrence, wrong direction, borrowed cues and missing relationships fail. This is ordering-only proof, not full semantic correctness, planning admission or paid authority.

## Optional projection and actual planner compatibility

The owner confirmed the previously proposed rule: compute full source-proven transitive closure first, then project onto selected visits. Coffee→optional museum→dinner therefore retains required coffee→dinner when museum is absent; including museum retains its intermediate position. `selected_visit_projection` is an offline consequence record only: it rejects omitting required occurrences, duplicate/invalid indexes and unknown policies, never creates an itinerary or authority.

Inspection and fake-candidate tests establish that the **existing** `backend.advanced_routing._ancestors` computes full closure before `_shortlist` intersects ancestors with selected visits. For the intact constrained three-stop graph, the actual shortlister produces exactly (0,2) and (0,1,2), with no reverse order or forced optional attendance. No provider is called. Thus the current route engine can represent this rule for a validated graph; a new conditional-order schema is not required by this evidence.

This does **not** make V5.1 deployable. Current legacy source checks/no-cue normalization may reject or erase list edges before routing. Future approved enforcement must supply one authority and retire overlapping legacy ordering logic, preserve raw/effective mappings and validate all non-order requirements. No runtime function is changed here; legacy remains authoritative, V4 shadow default-OFF, V4/V5/V5.1 enforcement unavailable.

## Proposed Q1 amendment: all 66 cases

[New proposed full rubric](task52-q1-rubric-v3-v51-PROPOSED.json), identity `52b-q1-rubric-v3-owner-decisions-v5.1-PROPOSED`, explicitly references original Q1 and the unchanged V5 proposal. [All66 impact](task52-ordering-v51-all66-impact-v1.json) records source hashes, expected graphs/flexibility, evidence analysis and remaining review fields separately.

Compared to original Q1: **19 mandatory graph amendments, two conditional graph amendments,45 unchanged**. The extra mandatory amendment is ordinary-multilingual. The two conditional cases are journey-06 and extension-inclusive. Flexible required coffee and explicit partial/unordered expectations remain intact; owner decisions do not turn flexible placement into optional attendance.

All six original Q1 unresolved records remain preserved in their frozen parent. In this **new proposal only**, Rule B supplies a proposed resolution of extension-inclusive.mandatory_order, with conditional groceries→coffee and unchanged return/90-minute/date requirements. It is not independently signed gold. Five proposed unresolved fields remain:

* journey-25.required_activities;
* ordinary-multilingual.dates_timezones (Kal remains ambiguous);
* ordinary-budget.budget_transport;
* ordinary-ambiguity.required_activities;
* extension-contradictory.required_activities.

The general optional-placement and aur meanings no longer require another owner product decision. Individual case correctness, all24 dimensions and all66 gold rubrics still require independent review. Source-grammar coverage is **37/66 recognized,29/66 unknown/outside grammar**. Unknown includes clear language beyond this bounded grammar, not only genuine semantic ambiguity. It is not an accuracy metric or an excuse to manufacture passing expectations.

## Full OpenAI prompt proposal

[Exact complete prompt/request template and19-example audit](task52-cloud-prompt-v51-PROPOSED-v1.json), version **`52b-cloud-v5.1-owner-list-order-PROPOSED-v1`**. Prompt hash **`1741e5b5ae344fff0e4fff1fba2c4b45fd73b0b86baf73bdae35607f4b1919c9`**; proposed configuration hash **`4239ddf4810ce65dfc5593c64cb011372abb1e350560ed848ceded06811d28a8`**. The artifact also supplies exact system UTF8 and canonical-message-byte hashes.

Three replacements are recorded reversibly: source text is not visit order; only explicit temporal words create edges; and the v4 370-byte addition forbidding list inference. New instructions cover owner A–D, optional projection, flexible/partial/unordered scope, repeated occurrence indexes, endpoint separation, contiguous evidence containing both stops and the actual list connector or scoped cue, unknown/contradiction clarification and unchanged non-order protections.

All19 original example inputs remain identical. Four **proposed** example ordering meanings change, with complete original/proposed replies recorded:

| Example | Change |
| --- | --- |
|10 Dinner/drinks|Add default0→1|
|12 Groceries/optional coffee/return|Add conditional0→1, retain optionality/return/45-minute meaning|
|15 Zara/Nike visits|Add0→1, retain brand identities/same-mall requirement|
|19 Separate timed bank/coffee visits|Add0→1, retain each exact duration|

The other15 replies keep their meanings, including existing repeated-coffee chain, explicitly flexible bank/groceries, single mall-with-brands intention, named endpoints and contradiction clarification. Tests reverse all system edits and remove only order/ordering from example comparisons to prove non-order instructions/facts were retained. The canonical schema and OpenAI strict wire schema are unchanged. No Qwen/OpenAI active prompt or existing example is edited.

The full request template keeps gpt-6-luna, store=false, reasoning none, temperature0, default service tier, no tools and max_output_tokens2000. Twelve-thousand input cap remains a prerequisite. **No tokens are counted or approximated as certified evidence**: complete input counts, availability, credits, key access, current pricing/terms/limits are unknown until separately approved readiness checks. This artifact is not live authorization or proof the provider will accept it.

## Historical replay and future Q3/Q4

[Separate V5.1 replay](task52-ordering-v51-replay-v1.json) executes recorded evidence only. Qwen19/27 ordering compatible,8/27 also compatible through unchanged legacy journey processing; OpenAI4/7 ordering compatible and4/7 compatible through complete unchanged B2. These counts match V5: none of these34 recorded ordering dispositions changes in V5.1. Qwen scope remains ordering/journey-only; OpenAI complete B2 DTO hashes reproduce frozen Q1 at its fixed clock. No exact historical environment or full independent correctness is claimed.

The two dinner/drinks outputs lack new default order and remain V5.1 errors. Journey-07 still fails its cue-only provenance. Extension-repeated now has valid default0→1 and explicit1→2 evidence, with distinct occurrences and unchanged return/inclusive180/geography/date checks; its **historically accepted V4 critical error, row, costs and persistent halt remain unchanged**. Policy compatibility does not convert any raw output into independently qualified full correctness.

[New successor proposal](task52-q3-v51-PROPOSED-v3.json), identity `52b-q3-openai-b2-v5.1-owner-decisions-PROPOSED-v3`, preserves exactly:

1. extension-repeated/r2: three visits, full0→1→2 sequence, origin return/inclusive180.
2. journey-04/r2: exact college then coffee, valid evidence, no invented geography/date.
3. extension-partial/r2: pharmacy→bank; coffee required and independently placeable.
4. journey-06/r2: groceries required; conditional groceries→optional coffee.
5. journey-21/r1: original contradiction must clarify, never publish a fabricated graph.

All five sources and their24-field expectations remain bound, with new **proposed** prompt/configuration/payload identities. No selected field is unresolved, but all independent case reviews remain blank. Future live build, owner approval, readiness and operation permission remain null. The five/$0.0125 amount is an unchanged historical **proposed cap**, not a current price guarantee or new financial authorization.

Old Q3/V5 proposals and Q4A–Q4C builds/signature purposes remain frozen and cannot authorize V5.1. A new reviewed build/purpose, real operator boundary, independent reviews and separately approved fresh readiness are still required before any future exact-scope live decision. Do not resume the old halted scope. Gemini HTTP400/IP and Anthropic grammar-compilation blockers remain separate and unchanged.

## Verification and next review

[Verification and immutable identities](task52-ordering-v51-verification-v1.json), [offline manifest](task52-ordering-v51-manifest-v1.json). New cases are same-agent authored; post-freeze contrasts are not independent human signoff. No model is production qualified. Review this proposed prompt, changed example meanings and individual rubrics next; do not silently activate an evaluator, policy or prompt.

Original journal/324 files/halt and all original caps are preserved: OpenAI7/Google2/Anthropic1,10/594,$0.047366625 accounted/$11.952633375 remaining. No real grants/reservations/enrollment, provider/count/metadata/account/Maps call, production/source validation/Qwen/model/prompt, billing/quotas/infrastructure/migration or Task53 change.
