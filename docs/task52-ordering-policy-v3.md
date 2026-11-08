# Task52B V3 ordering and normalization decision

The three V2 blockers are resolved **in an offline, opt-in policy**, not in production. `52b-order-policy-v3-offline` preserves proven start/finish order, independently scopes a local optional third stop, and safely projects seven recorded unordered Qwen graphs without accepting their invented edges. The halted paid evaluation remains halted. No provider, token-counting, inference or Maps requests were sent.

Baseline: clean `9aa9035cdf80a171195c82d7ece448bc99241712`. [Machine-readable comparison](task52-ordering-compatibility-v3.json), [29 predeclared source rubrics](task52-ordering-compatibility-v3-cases.json), [separate freeze history and holdouts](task52-ordering-compatibility-v3-holdouts.json). These are same-agent reviewed fixtures, **not independent human signoff or universal semantic accuracy**. Historical V1/V2 reports, all model outputs, original scores and authoritative 66-case corpus are unchanged.

## Single source-first contract

| Source situation | Independent requirement | Model-graph treatment | Safe next action |
|---|---|---|---|
| A. Explicit mandatory order | Unique occurrence binding and bounded directional proof, inside each edge's real quote | Retain proven edges; missing, reversed, unsupported or inadequately quoted edges block | Remaining canonical validation, or clarify/rephrase |
| B. Clearly unordered list | Complete finite list parse, with only reviewed non-order metadata; absence of a recognized cue alone is insufficient | Empty graph remains empty | Remaining canonical validation |
| C. Unsupported model edge on clearly unordered source | Same complete absence proof as B, independent of proposed graph | Only source-bound forward, nonconflicting edges can receive an explicit audited empty-graph projection; retain original graph/error/hash | Continue other validation with unordered semantics; raw model ordering remains incorrect |
| D. Potential mandatory intent without proof | Unknown connector, unowned cue/qualifier, incomplete binding or unsupported scope | Never delete or guess potentially real requirements | Clarify/rephrase; no route/session publication |
| E. Contradiction, negation or condition | Remaining conditional/negative language, conflicting graph or ambiguous alternatives | No projection or silent repair | Clarify; contradiction and unsupported grammar may share conservative unknown outcome |
| F. Partial order with independent stops | Prove only scoped relationships; independently identify local optional/flexible qualifiers | Preserve proven graph; reject extra chain edges, missing requirements or changed optionality | Remaining canonical validation, or clarify/rephrase |

The ordering decision retains source/extraction hashes, original graph, source category, occurrence coordinates, qualifier spans, proven relationships/cues, unsupported model edges, trusted ordering-only graph, normalization reason, raw-model correctness and safe next action. No production/session admission is granted by this object. `project()` requires an exact recomputed decision, returns a deep copy, and changes only order/order mode for C. It cannot hide or overwrite a raw model error. Case C is **not** a successful raw semantic extraction.

Removing an invented edge after independently proving an unordered source does not remove a user requirement. Removing an edge merely because proof failed could remove a real but ambiguous requirement; D/E therefore never normalize. The model graph is not used to decide source intent. Tests vary empty/reversed/conflicting graphs and model required/optional flags while requiring identical source analysis.

## Trust boundary and bounded ownership

`source_analysis()` binds source-order stop occurrences using frozen V1 ownership primitives, discards proposed edges, and reuses frozen V2 relationship grammar on a graph-free copy. Locally owned qualifier text is replaced with same-length spaces for proof scope, then every proof/quote is mapped to the **original** source coordinates. A raw quote still must contain the actual owned relationship and cue. The modified scope text never becomes model evidence.

Local `maybe`/`optionally` with finite get/grab/have/visit/stop verbs must attach to one independently delimited occurrence; a following order cue or multi-stop scope cannot be erased. The `and` connector is retained. `whenever convenient` on an independent stop means required but freely placed, not optional. A source/model requirement mismatch blocks, rather than changing stop status. Unowned negative, conditional, alternative or qualifier words remain blocking. No arbitrary comma splitting or prose deletion is used to infer a graph.

The absence proof recognizes finite imperative/list connectors plus source-bound location and finite date/dwell/return/shared-mall metadata. It supports exact `whichever is closer first` as no **fixed** mandatory edge while requiring the model's flexible mode to agree. A separate named endpoint may own `finish at` only when its actual source clause does not overlap a visit occurrence. Other identity/endpoint/timing checks remain mandatory. Unknown metadata cannot authorize deletion. Generic labels cannot absorb ordering/qualifier words to hide them; named-place words are excluded from cue detection only under the existing separate identity contract.

Binary `Start with/at A and/, finish at B` is proven from the original source before any legacy normalization. V3 retains its real edge, rather than restoring an edge after the old normalizer removed it. The old cue vocabulary lacks start/finish and can erase the relationship; two authorities must not run sequentially in a future integration.

Limits: 8,000 source codepoints, 32 stops, and frozen bounded occurrence-binding work. Unknown/ambiguous bindings, unowned extra mentions and oversized input clarify. Each edge's real quote remains capped at 500 characters. Source analysis presupposes strict parsed, complete, source-bound stop identities; it does not independently establish arbitrary-language activity completeness, exact businesses, optionality outside the grammar, endpoints or date/time correctness.

## Measured compatibility

| Measurement | Current production / V2 | Offline V3 |
|---|---|---|
| All27 Qwen ordering decisions | V2:9 clarifications; production safely normalizes7 but accepts2 unsupported repeated-stop graphs | 2 clarifications, both unsupported repeated-stop graphs;7 audited normalizations;18 raw correct graphs compatible |
| Previously nonblocking correct Qwen graphs |13/13 V2 compatible |13/13 compatible |
| Separate existing canonical blocks |3 return/time omissions +2 identity ambiguities |All5 remain unresolved; ordering pass cannot authorize a request |
| Seven recorded OpenAI outputs |V2:5 compatible,2 rejected |5 compatible,2 rejected |
| Declared clear-source cases |V2:5 unnecessary questions /19 |0/19 unnecessary questions |
| Declared unknown-source cases |10 reviewed ambiguity/out-of-grammar cases |10/10 clarify |
| Proven mandatory relationships |17 direct edges across15 declared explicit/partial cases |17/17 preserved, with source-owned direction/evidence |
| Unordered clear sources |4 declared cases |4/4 retain no mandatory graph; Case C tested separately |
| Required / optional occurrences |43 required +4 optional across19 clear cases |47/47 status agreement; flipped optional/required probes block |
| Repeated visits |3 declared clear sources |3/3 preserve distinct occurrences and reviewed partial/full/no order |
| Partial orders |6 declared sources |6/6 preserve only supported relationships |
| Named-place boundaries |3 declared cases,5 named occurrences |3/3 ordering compatible; projections do not change any identity field |
| Unsupported single-edge replacement probes |V2 baseline0/92 accepted (different, overlapping probe construction) |0/147 unsupported edges retained;11/147 audited empty projections,136/147 reject |
| Additional exploratory clear release-limit requests |3 clear sources, selected after freeze |3/3 still clarify; measured separately, not passing holdouts |
| Final post-freeze tests |Separately authored after final module freeze |8/8 matched; not independent human review |

The147 probes span original clear-source V1 cases, clear V2 cases and new clear V3 cases. Negative V2 fixtures deliberately containing wrong model graphs are excluded as gold-source graphs; otherwise replacing a reversed fixture edge with the correct relationship would falsely be called a false acceptance. Overlapping fixtures/probes are not independent observations or population error rates. Original31 cases/63 appended probes/six holdouts and V2's40/92/eight reproduce unchanged.

Freeze history is explicit: first12 holdouts yielded11 matches and one safe false clarification because masking optionality erased `and`. That connector defect was corrected. Those12 and two subsequent passed sets of8 were promoted to28 regressions before finite `Plan` imperative compatibility and flexible-mode agreement changes. The final separate8 were authored after the final module SHA freeze; all8 and all28 regressions pass. No failed holdout was concealed or relabeled independently reviewed.

### Per-output replay

| Original OpenAI r1 slot | V3 ordering result | Historical distinction |
|---|---|---|
| journey-01 |Compatible unordered |Original decoder-error row/correction preserved |
| ordinary-dinner |Compatible unordered |Finite `Plan dinner...` imperative supported |
| journey-03 |Compatible single mandatory visit |Exact named-place requirements unchanged |
| journey-07 |Reject |Cue-only `first, then` still lacks both owned stops in its quote |
| journey-04 |Compatible0→1 |SUNY College of Optometry before coffee, full evidence |
| extension-partial |Compatible0→1 only |Coffee remains required and independently placed |
| extension-repeated |Reject unsupported0→1 |Museum1→coffee2 still proved; extra first-coffee→museum never projected away |

Qwen D's3 rows and E's4 rows receive the audited unordered projection. Their raw invented edges remain recorded incorrect. Two repeated-stop Qwen rows remain rejected. The remaining18 correct raw graphs remain compatible. All per-output hashes, original/current production results, V2/V3 decisions and evidence coordinates are in the machine report; this is not retrospective rewriting of model scores.

### Runtime overhead and limits

1,450 local decisions (50×29 fixtures), including source analysis, deep copy and evidence hashes but excluding fixture construction: p50 **103.583µs**, p95 **155.458µs**, maximum **533.0µs** on this machine. The machine report binds these observations to module/fixture hashes. V2 historical timing remains separate; copying and validation scopes differ. This is neither universal worst-case timing nor full-app latency. Existing source/binding caps bound work; unfamiliar long clauses still clarify. No routing, HTTP or extra AI pass is needed.

## Proposed integration — not activated

An **opt-in/shadow implementation proposal** is justified; default activation is not release-ready. The three targeted blockers are resolved, but three additional common clear forms still fail the bounded grammar. These are explicit release limits, not semantic ambiguities or reasons to silently delete requirements.

1. At `backend.interpretation.interpret_request`, preserve the strict parsed extraction and original text immediately before `validate_journey()` (currently around line439). Use one versioned source-first decision before the legacy graph can be changed. Saved interpretations/follow-up paths must use the same boundary.
2. In an explicitly selected V3 profile, split/parameterize `backend.journey.validate_journey` so its legacy order normalization (around lines298–306) and later cue-only graph checks are replaced by this single decision authority. Retain all non-order strict graph structure, mandatory-stop, source, identity, duration, return, date and endpoint checks. Do **not** call the old order normalizer after V3 or restore a removed edge afterward. Isolate the finite helper into a runtime-safe module only under the separate integration change.
3. Retain original extraction/source/hash/normalization diagnostics separately from a copied effective graph. Never publish an unproven graph. Verified no-order keeps ordinary planning semantics; partial/explicit constraints flow unchanged to advanced routing, whose ancestor checks already enforce graph dependencies. No session at `main.interpret_outing` / `sessions.create`, ordinary request, or provider work may occur while unresolved.
4. Initial rollout flag/version is OFF by default; shadow comparisons may measure policy differences without granting requests or clearing cloud halts. Activation needs owner approval and full backend/frontend/typecheck/lint/build plus main-form browser verification. Historical Qwen corpus and cloud replays are required compatibility gates, not training data guarantees.
5. Existing main-form rephrase behavior is a safe initial unknown outcome: preserve original text, explain which relationship needs clarification, and publish no planning token. The current question type allowlist has no `ordering` kind; do **not** reuse `activities` answers, which can fabricate a full chain. A future structured ordering answer needs typed occurrence IDs, explicit dependencies/no-order choices, source-version binding, separate user-answer provenance, canonical graph validation and an interpretation snapshot. Accept deterministic user-confirmed requirements without rerunning AI; do not claim such UI/backend support already exists.
6. Rollback disables new admissions under V3 and returns to the unchanged legacy path after invalidating V3-dependent pending confirmations/sessions, never by editing paid evidence or silently reinterpreting an existing graph. Define expiry/version binding before integration. No additional data collection, provider calls or private operational raw-text logs; bounded decision diagnostics only.

Post-freeze exploratory checks, recorded separately in [release limits](task52-ordering-v3-release-limits.json), found three clear forms that still clarify: `Start at pharmacy and finish at bank in Jersey City tomorrow` (city suffix outside the binary rule), `Start with coffee, visit museum, and finish at pharmacy` (three-stop start/finish), and `Do dinner and bowling tomorrow` (finite imperative vocabulary excludes Do). The last is an avoidable question versus V2; the first two keep real requirements from being normalized away. **3/3 additional clear release-limit requests remain false clarifications**, distinct from0/19 declared clear-source cases. No tuning followed these observations. Decide supported release language or address these narrowly with new separated tests before default integration; do not expand into a general parser.

Remaining out-of-grammar examples include distant/global qualifiers, negated/conditional order, unknown temporal anchors (`After lunch...`), `before B closes`, unrecognized connectors, long parentheticals and repeated references with ambiguous ownership. They remain unknown, not inferred or silently normalized. Do not keep expanding grammar just to obtain zero questions. Source-intent proof also depends on independently verified complete stop extraction; arbitrary omissions remain a separate canonical safety boundary. No new model prompt revision is required by this offline change; changing a prompt alone cannot independently validate cue scope.

## Paid state, other providers and verification

Read-only SQLite integrity is OK. All10 rows/root/corrections,324 ignored private files and the v4 persistent halt remain byte-identical. Direct read-only `verified_rows()` recovery also refused the actual halted continuation (`Unexpected/uncertain/halted attempt; never retry`). Journal SHA256: `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`. OpenAI7/Google2/Anthropic1;584 total slots remain (191/196/197). Retained **$0.047366625**, remaining **$11.952633375**; zero new attempts or spend. Original $12/594/198,12k/2k, concurrency1 and retries0 remain unchanged.

Gemini's two Developer API400 causes remain unproven and its separate IP restriction remains unresolved. Next work is local request/schema/error compatibility review and owner verification of the allowed source IP, not another speculative request or managed-platform substitution. Anthropic's grammar-size rejection still requires a separately reviewed schema-complexity projection with complete canonical reconstruction and offline negative/null/required-field tests. No credential, endpoint, schema, account or billing changes were made for either provider.

Verification:314-test relevant backend run completed with313 passed/one opt-in PostgreSQL test skipped; final31 ordering/replay tests passed after the last offline-only refinements. Full frontend283/283 passed in116.927s. Production/shared application files are unchanged, so full backend discovery, TypeScript/lint/build and browser staging were not rerun. Standard secret scan and all3 actual evaluation-key value scans across current files/history found zero matches; configuration/journal remain ignored mode600. Full tracked/new diff and result/hash consistency reviewed before delivery. No private outputs or credentials were added.

Next step: owner review of this policy and the three release limits, then a separately scoped opt-in/shadow integration and clarification design. Default integration needs the common-language release gaps resolved or an explicitly accepted supported-language scope, followed by complete application verification. Keep the paid v4 continuation halted. A larger paid batch, production model selection, infrastructure or Task53 is not the next authorized action.
