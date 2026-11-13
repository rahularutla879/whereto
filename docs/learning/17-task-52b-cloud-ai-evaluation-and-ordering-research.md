# 17 — Task 52B Cloud AI Evaluation and Ordering Research

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## The question is qualification, not merely speed

**Evaluation** compares a model's recorded outputs against explicit expectations. **Qualification** requires enough evidence to satisfy safety, correctness, latency, cost and operational gates. Local Qwen was chosen for replaceable on-device extraction; later measured latency and interpretation failures motivated cloud investigation. That investigation did not authorize replacing the active provider.

The [52A architecture proposal](../../docs/task52-cloud-architecture-evaluation.md), [performance proposal](../../docs/task52-ai-performance-evaluation.md), [benchmark history](../../docs/task52-cloud-model-benchmark.md) and [scope/exit review](../../docs/task52-scope-exit-review.md) distinguish evaluation from hosting. Task 52 is still in progress; Task 53 is not begun by this course.

## What the 66-case corpus measures

[docs/task52-q1-rubric-v1.json](../../docs/task52-q1-rubric-v1.json) and [the Q1 contract](../../docs/task52-q1-qualification-v1.md) bind 66 original sources. They cover ordinary requests and complex journeys, including repeated stops, partial order, optionality, home/return, durations, constraints, ambiguity and adverse inputs. Original reference depth differs: 25 structured journey references, 26 partial ordinary references and 15 prose references. Do not call every original reference a complete independently checked answer.

Q1 records 24 dimensions per case, including applicability and absence checks. **Not applicable** means a field must not be invented, not “anything goes.” Six judgments remain awaiting review across six cases, seven cases have gap notes, and all 66 require independent gold review. **Gold** means the expected reference answer; it can itself require adjudication. All seven complete OpenAI outputs also need independent response signoff. Same-agent authored rubrics and finite holdouts are not independent certification.

The proposed original design is 66 cases × three repetitions × three providers = 594 slots, 198/provider. Slots are bounded attempt identities, not guaranteed successful responses. A provider error consumes a slot; unused allowance is not permission to retry it.

## Historical attempts and accounting

The Q2 machine matrix records candidate IDs `gpt-6-luna`, `gemini-3.8-flash` and `claude-haiku-5-5` ([frozen matrix](../task52-q2-decisions-v1.json)). These are historical evaluation configurations, not current model recommendations or active production adapters. The earlier 52A first-candidate suggestion and later evaluated IDs differ because the research progressed.

At the Q4C baseline the checked-in reports retain ten paid attempts: seven OpenAI, two Google and one Anthropic. Historical retained accounting is $0.047366625, with $11.952633375 of the original $12 ceiling remaining and 584 unused slots. These figures are historical repository evidence, not a fresh journal read or provider invoice check in this task. No private journal or credentials are needed to study them.

A **journal** is a durable record of attempted operations, identities, reservations, outcomes and corrections. An **append-only correction** adds a separately bound explanation without rewriting the original row. The original journey-01 decoder failure and later correction must both remain. HTTP provider errors do not count as successful semantic responses, and their durations are not successful inference latency.

An output token limit and complete input count bound spending; concurrency one and retries zero limit overlap and uncertainty. Reservations are conservative exposure, not necessarily posted invoices. A timeout after send can remain chargeable/uncertain. Full response timing, token usage, model/configuration and prompt cohorts must be retained separately.

## Why evaluation stopped

The recorded v4-prompt repeated case extracted coffee0, museum1, coffee2 plus return and duration, correctly asserted museum1→coffee2, but also asserted unsupported coffee0→museum1 under the then-current unordered-list policy. Legacy validation accepted that extra edge. A critical **accepted unsafe** result is more serious than a safely rejected malformed response. The screen halted even though other fields and timing looked good.

Historical seven-output reassessment distinguishes seven structurally valid outputs, six legacy acceptances and five proposed guard-compatible outputs. Journey-07 is a provenance failure that was safely blocked; the repeated case is an ordering failure historically accepted. These are not seven independently certified semantic outcomes, nor an estimate from a complete 66-case campaign. The active Qwen prompt/model and production policy were not replaced.

## Ordering V1 through V5

| Version | Purpose and result | Status/limit |
|---|---|---|
| V1 | Source-owned occurrence/edge proof; rejects invented repeated-stop edge | Offline finite grammar caused avoidable questions on correct wording |
| V2 | Broader bounded connectors and compatibility analysis | Offline; plain unordered Qwen list edges still needed safe normalization handling |
| V3 | Source-first categories, independently proved unordered projection, local optional scope, binary start/finish | Offline; raw errors retained; three additional release wording gaps remained |
| V4 | Close measured start/finish/city-suffix/imperative gaps; default-OFF raw observer | Frozen offline policy and observational context; no enforcement |
| Owner-requested V5 | Default bounded itinerary lists to sequential order, preserving explicit exceptions and repeated occurrences | Committed offline prototype at `b1efe96`; no runtime integration, prompt amendment or paid authority |
| V5.1 | Verify conditional sequence and bounded “aur” against the original text | Frozen research proof is reused by an explicit, default-OFF Python development adapter |

“Cloud prompt v4” and “Ordering Policy V4” are different identities. One defines what is sent to a model; the other is an independent source-based inspection policy. Reusing the number does not make their authority interchangeable.

Under frozen V4, “Dinner and drinks” independently has no mandatory graph edges, although the ordinary source-order planner still visits dinner first. Under proposed V5 it becomes dinner→drinks by default. “Pharmacy before bank; coffee whenever convenient” retains only pharmacy→bank; coffee remains required and independently flexible. “Coffee, museum, then coffee” changes from explicit 1→2 under old policy to a default sequential chain under the owner's request. This changes the rubric: preserve original judgments and record a new policy comparison rather than declaring old outputs retroactively correct.

## Committed V5 evidence and remaining proposal boundaries

The independent `b1efe96` checkpoint completed the offline recognizer/replay, not application integration. [Its specification](../task52-ordering-policy-v5.md) records 18 mandatory graph amendments, one conditional amendment, two further pending cases and 45 unchanged graphs across the 66 sources. All six original unresolved Q1 fields remain. The finite recognizer classifies 36/66 sources and returns unknown/outside grammar for 30/66; gold expectations and recognizer coverage are different denominators.

Its seven historical OpenAI comparisons now block the two dinner/drinks outputs for missing the newly required relationship, retain journey-07's provenance block, and mark the repeated case ordering-compatible under V5 without rewriting its historical V4 accepted-critical error. Recorded Qwen comparisons have 19/27 raw V5 ordering-compatible outputs but only 8/27 preserving V5 order through unchanged legacy processing. These ordering-only replays are not full independent extraction accuracy or new model calls.

Optional-middle semantics propose computing source closure before projecting selected visits, preserving required surrounding order without forcing an optional stop. That conditional behavior and individual impacted cases still need review. The unchanged cloud v4 prompt explicitly forbids list-order inference and conflicts with V5. The [amended Q3 proposal](../task52-q3-openai-v5-PROPOSED-v2.json) keeps the same five unused slots and proposed maximum, but future prompt/configuration/payload/build identities are null and all slots remain inadmissible. Q4A–Q4C remain frozen V4 engineering evidence, not V5 execution grants. See [the blank review checklist](../task52-ordering-v5-review-checklist.md).

## Source compatibility and admission

The generalized development adapter reads the current request and supplied extraction directly. It does not consult the benchmark answer. The original five cases remain regression fixtures, and new cases exercise the same source rules with different visits and wording. The frozen scorer, historical paid halt and the diagnostic exception retain their original meanings. A successful synthetic handoff leaves model qualification and production activation open. [Generalization report](../task52-v51-ordering-preservation-generalization.md)

A **source version** identifies the exact code/schema/prompt/scorer environment used for evidence. Hash-pinned evaluation prevents results produced by one validator from being silently attributed to another. The B2 change extracted only `normalize_explicit_durations`; it was behaviorally reconstructed against frozen traces, not an exact historical execution environment. The original paid evaluator correctly refuses the changed source. Test-only fixture scopes are not live gate overrides.

`AdmissionRegistry` is an internal foundation binding validated payload, scope, revision, purpose, expiry and selected legacy policy. It prevents replacing validated data with arbitrary client JSON or reusing a stale revision. Durable public one-operation authorization remains a design: it needs shared atomic consumption/revocation/fencing and separate provider reservations. A digest identifies bytes; it is not owner consent.

A real field excerpt from `Verified` in `scripts/task52_q4c_auth.py`:

```python
@dataclass(frozen=True)
class Verified:
    role: str
    envelope: bytes
    packet_hash: str
    execution_authorized: bool = False
```

Line 1 makes the record immutable after construction. Line 2 names the verified-fact type. Lines 3–5 retain the role, canonical signed envelope bytes and packet identity. Line 6 explicitly denies execution authority. Input is a packet that passed its purpose-specific verifier; output is an offline fact, never a real paid-dispatch grant. Invalid trust, role, signature, bounds or expiry raises a denial before such a fact is usable. The protocol must additionally enforce durable replay/state checks.

A **fence** is a monotonically changing ownership/version marker preventing an old worker from publishing after a newer owner takes over. A **nonce** is a one-use identifier for detecting replay. A **signature** authenticates exact bytes under a trusted key; it does not prove reviewer independence or approve a different purpose.

## Q1–Q4C: what completed, precisely

| Checkpoint | Completed | Still not provided |
|---|---|---|
| Q1 | Frozen qualification contract, 66×24 rubric records, seven-response offline reconstruction | Independent gold/response approval; universal semantic parser; paid readiness |
| Q2 | Finite compatibility decisions; OpenAI ready only for Q3 proposal | Google HTTP400/IP blocker resolved; Anthropic grammar compilation proven; model qualification |
| Q3 | Exact five-unused-slot successor proposal and bounded same-journal design | Dispatch authority, new reservation or concrete live adapter |
| Q4A | Fictional temporary-state successor protocol, crash/locking tests, unconditional live refusal | Real same-journal execution boundary or real independent approvals |
| Q4B | Fixed read-only original-storage inspection and exact-schema fictional checks; operator trust design | Writable real adapter, trust enrollment or live permission |
| Q4C | Detached Ed25519 verifier and signed exact-schema synthetic protocol with six purpose-specific roles | Real trust/store/clock protection, enrollment, live activation or independent human signoff |

Q4C's protocol sequence is signed scope→START→FULL SQLite reservation→INTENT→closed fake exchange→OUTCOME→signed 24-field REVIEW. From [task52_q4c_auth.py](../../scripts/task52_q4c_auth.py), the source's authority is deliberately bounded; the [protocol document](../../docs/task52-q4c-offline-protocol-v1.md) specifies `execution_authorized=false` for validated offline facts. This is a field-level code-reading target: find it and read the constructor/consumer, rather than copying an imagined live API.

**Ed25519** is a public-key signature algorithm. Q4C tests create disposable synthetic keys; they do not use or enroll the owner's real SSH keys. Six roles separate owner scope, rubric review, readiness permission, readiness evidence, execute-one permission and response review. Three test keys generated under one local user do not prove three independent people. Filesystem and SQLite commits are not one distributed transaction; uncertain recovery must halt, not resend.

No cloud model is production-qualified. Before any approved live continuation there must be independently reviewed expectations, a reviewed compatible concrete build, real trust/authorization boundaries, fresh exact readiness, preserved original journal/halt, and exact bounded owner permission. Before deployment there must also be shared operational services, provider/privacy approval, cloud integration and hosted acceptance. None follows automatically from budget remaining or passing fictional tests.

## Five key takeaways

1. Qualification requires correctness and operational evidence, not speed alone.
2. The 66-case references have different depths and pending reviews.
3. Accepted invented ordering halted the screen.
4. V5 changes expectations and must not rewrite historical outcomes.
5. Q4C authenticates offline synthetic facts without enabling real execution.

## Check your understanding

17.Q1. How many original slots were proposed?
17.Q2. Why keep a failed row after a decoder correction?
17.Q3. What is the difference between raw correctness and safe blocking?
17.Q4. Does a hash authorize paid work?
17.Q5. Why is no cloud model qualified?

## Code-reading exercise — 17.R

Compare the Q1 three outcome axes with the V4 policy and locate execution_authorized in task52_q4c_auth.py.

## Practical exercise — 17.P

Create a paper comparison with columns original source, immutable raw output, old rubric result and proposed V5 result. Use invented examples only; edit no frozen artifact.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-17).

[Previous chapter](16-git-github-and-the-development-workflow.md) · [Contents](README.md) · [Next chapter](18-cloud-hosting-deployment-and-scalability.md)


### Current cloud-model qualification review (documentation only)

The [finite selection audit](../task52b-model-qualification-status.md) returns Task52B to model qualification. The existing five-case packet has120 independent judgments still blank. Owner-approved meanings need no repeat approval; a model screen needs independent review, a current exact execution identity and explicit financial permission. Older replay tests now refuse frozen B2 identity on the changed checkout; that is not a fresh model result. Five diagnostic successes cannot establish the broader clean-cohort/held-out gate. No infrastructure, model or evaluation runtime changed in this review.
