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


## Preparing exact requests without executing an evaluator

`scripts/task52b_prepare_openai.py` is an offline artifact checker, not a provider runner. From the repository root, run `PYTHONPATH=. backend/.venv/bin/python -m scripts.task52b_prepare_openai`. It verifies frozen corpus/prompt/rubric/Q3 hashes, fills only the final user message, and checks the five committed generation/count drafts. It has no credentials, HTTP transport, journal writer or spending permission. See the [technical preparation report](../task52b-openai-technical-preparation.md).

The count draft keeps model, all messages, strict output schema and reasoning configuration. Exact input counts remain unknown until separately authorized provider counting. A local token arithmetic test proves boundary handling, not how many tokens a real model receives. Compact teaching examples remain unchanged; they are not complete strict-wire responses. Actual responses still need every required field and source/semantic review.

A retained Git checkout can match an old source manifest while the modern application correctly fails that identity. Task52B found matching B2 source and package lock at e7937e4;33 tests pass there, but four need the original private evidence at its protected location. Do not copy or symlink a financial journal, edit a hash, or weaken checks to make those pass. Source compatibility is narrower than exact historical environment reproduction.

The owner has deferred human review. Record those120 source, six historical and four normalizer judgments as incomplete; never fill them with AI answers. Deferral is not a financial grant or an amendment of frozen per-response progression rules. Original product decisions remain valid. Current Qwen and production interpretation are unchanged. [Versioned deferral](../task52b-owner-review-deferral-v1.json) · [separate readiness gates](../task52b-openai-readiness-gates-v1.md).


## Restoring original-evidence replay without copying its journal

`task52b_evidence_access` is a trusted offline I/O adapter. It leaves B2 source and ROOT unchanged while opening the existing original evidence path read-only, checking file inventories, content hashes, inodes, permissions and the shared lock. Q1 uses a session-long read lease; Q4B retains its own lock so its unchanged exclusive-lock refusal test still works. SQLite is read-only/query-only and connections retain read leases until close. This is not an OS sandbox or human security certification.

From the matching frozen checkout, use the existing Python executable to run the development checkout's `scripts/task52b_run_offline.py` by absolute path with `PYTHONPATH=.` and `--suite replay`, `--suite boundary` or `--suite historical`. See [exact identities and results](../task52b-execution-boundary.md). Do not run Q4B's exclusive-lock test concurrently with other replay readers. Normal backend discovery deliberately skips the new privileged offline tests; no production toggle is introduced.

The new append/single-send kernel uses the old Q4C state transitions and SQL guard, adding exact START-bound reservations and immutable raw-byte, decoded and grading evidence. Tests mutate only fresh fictional journals; original evidence is never a write fixture. A timeout/crash retains the committed reservation and cannot trigger resend or refund. Real storage/transport enrollment is unavailable; a ticket, passing test or application grant cannot replace experiment permission.

The owner deferred human semantic review. A proposed first-slot-only technical purpose would require separate governance/owner/security and financial approval; it is not activated. Stop after that first response unless genuine independent response review and exact next-operation permission exist. The journey-06 exception, five prepared payloads and old halt are unchanged. This is a route to evidence, not model qualification or production authorization.


## Preparing one network diagnostic without enabling OpenAI

`scripts/task52b_first_slot.py` reuses the journal kernel for exactly extension-repeated/r2. Its operational constructor refuses every enrollment packet before reading credentials or opening a socket. Local tests can use only 127.0.0.1, disposable TLS certificates and a fictional server-side credential. Run `scripts/task52b_run_first_slot.py` by absolute path from the matching B2 checkout with the existing Python executable and `PYTHONPATH=.`; it has no live/account options. [Report and exact prerequisites](../task52b-first-slot-readiness.md).

The transport captures the authorized request as immutable bytes before network work. Tests change the caller's payload after validation and still observe the original SHA on the wire. Verified TLS and hostname checks precede headers; no proxy, redirect, alternative-address retry or automatic resend is used. Missing/late/truncated responses and process death retain the reservation. This proves local protocol behavior, not OpenAI access or model quality.

A raw response body is preserved exactly. A separate decoder envelope binds HTTP status and capture hashes, without inventing model content or restoring graph edges. Raw, legacy and V5.1 grading remain distinct; independent correctness stays unapproved. A file descriptor is a server-owned handle to an already-open file; the fictional secret port reads a private read-only descriptor instead of accepting a browser's secret path. Real key acquisition/enrollment remains unavailable.

A real journal append necessarily changes the physical file hash. Keep the historical hash as a prestate anchor and preserve frozen readers; a reviewed successor fold must validate the original root/ten-row prefix/corrections and the authorized append. Never silently repin the old reader to a changed file. No original-journal write is permitted by this preparation.

The $0.0025 one-request and $0.0125 broader proposals are not grants. Exact counts, applicable worst-case rates/fees, credits and account terms need separately authorized fresh verification. The new proposed readiness scope is one model GET plus one first-payload count, zero inference; it needs governance review rather than substitution into the old five-count contract. Owner review remains deferred and no next diagnostic slot is enabled.


## Exact readiness checks are not inference permission

`task52b_readiness.requests()` validates the unchanged first-slot generation/count hashes and emits one model GET plus one full-input/schema count POST. Count replies do not echo a resolved model: preserve outbound binding rather than inventing one.401/403 stops without widening the restricted key. `ReadinessTransport` cannot read credentials or open sockets; `FictionalReadiness` accepts only canned responses and reuses Q4A exclusive/fsynced writes on fresh fixture storage, never the paid journal. The fixture proves replay refusal, not real account enrollment or independent OS authority.

Run `PYTHONPATH=.:backend backend/.venv/bin/python -m unittest backend.test_task52b_readiness -v` from the repository. These tests require no network/key/SQL/Redis. Raw fixture capture, request substitution, terminal denials, runner replacement/concurrency and money bounds are covered. No human rubric is filled by a passing test.

The official caching guide says a token uses input/read/write pricing, not input plus write; absent TTL selects30m. Preserve12h as a separate reviewed category, but do not enable it in the frozen request. `conservative_quote` uses integer nanodollars, upward category rounding, explicit extras/premium and exact project/model/revision/payload/time binding. It never authenticates those records or approves spending; real application SQL/counter enrollment remains a separate requirement. AI-assisted Support guidance about free counting is distinct from owner authorization, account billing facts and a successful permission test. See [current scope/results](../task52b-readiness-preparation.md).


## First real readiness run: permission denial is terminal evidence

The [authorized readiness report](../task52b-authorized-readiness.md) records one modelGET200 and one exact countPOST401 with missing `api.responses.write`. It contains no inference result or actual token count. Owner acceptance of Support's counting fee statement is distinct from independently checked billing. Do not change permissions or retry a consumed operation to obtain a nicer result.

The separate operator entry pins code/bootstrap/interpreter/CA and the existing owner0600 replacement-key metadata. It reuses the reviewed single-dial class with AST equality because importing the old frozen inference module correctly refuses current-source identity. Scope, INTENT, wire-consumption, raw/validated response and supervisor facts use the existing exclusive/fsynced writer in a new ignored owner-only directory. Source changes, crashes or replacement runners cannot reset that consumption. Credentials never enter request evidence; only the OpenAI dotenv line is read, leaving unrelated keys/Google ADC untouched.

The unchanged58cases plus14new process/TLS/credential tests run offline. `PYTHONPATH=.:backend backend/.venv/bin/python -m unittest backend.test_task52b_readiness_enrolled -v` uses fictional keys and local TLS/DNS fixtures only; it never invokes the real bootstrap. Never run the live CLI as a test or retry it. A future count needs separate owner permission/enrollment; first inference and semantic qualification remain separately gated.

## Prepared count-only continuation after permission refusal

The first live readiness scope is permanently consumed after GET200/count401. A new count-only proposal reuses that evidence read-only; it never resets the old authorization. The [prepared protocol](../task52b-count-only-preparation.md) checks original source/file hashes and a same-UTC-day/24-hour maximum freshness. This GET expires at2026-11-18T00:00Z; stale evidence refuses without silently adding another GET.

An owner's report that Responses changed to Write records a manual action, not independent permission evidence or a send approval. Preserve the old Read metadata and require a separate independently established receipt and explicit send confirmation. No live scope is created during preparation. Fictional independent processes demonstrate exclusive supervisor claim, consumption and INTENT before a single count send; crash/restart cannot mint a replacement. TLS, strict request/response bounds and credential-echo refusal reuse existing primitives. The live entry remains closed pending separately reviewed supervision/key-loader enrollment. These tests do not verify actual project permissions, billing, model quality or qualify any model; semantic review is still deferred.

## Dashboard evidence and prepared count supervision

The [v2 enrollment preparation](../task52b-count-only-enrollment.md) independently inspected the actual existing key dashboard: List models Read, Responses Write, unrelated None. The observed tracking ID/project/expiry match original metadata without reading the secret. A separate owner-only transcript/receipt is hash-bound to the existing credential identity; old Read metadata remains historical. This is a local observer record, not provider-signed permission or a successful API permission check.

The fixed count supervisor reuses the existing one-spawn pattern, pinned runtime/CA/bootstrap, exclusive/fsynced launcher and worker claims, INTENT-before-key-load, single wire and conservative no-retry outcome. Parent/worker/runtime identities are checked and core dumps disabled. No actual send authorization/scope exists now. A new check immediately after TLS rechecks the same hard GET deadline before HTTP; expiry during connection refuses, retaining consumption. Original expiry remains Nov18,2026,00:00UTC(7PM EST Nov17). Permission evidence never creates spending or inference authority. Fictional spawned processes and loopback TLS tests verify this ordering; model accuracy, billing and hosted identity remain unproven.

## Separately authorized model-visibility refresh

The original GET's Nov18,2026,00:00UTC deadline has passed. [GET-only preparation](../task52b-model-get-preparation.md) uses a new scope with one fixed empty model GET and no POST authority. Original integrity remains checkable after expiry; integrity does not restore freshness. Never pass a fabricated earlier clock, rewrite an observation or reset consumed facts.

The existing supervisor/TLS/immutable-writer pattern is reused with source binding and INTENT before key load. A future successful authorized response would expire at the earlier of24hours or next UTC midnight. Neither GET preparation nor GET success authorizes counting or replaces pinned count evidence automatically. Exact owner approval and later reviewed evidence binding remain separate. Fictional spawned-worker/loopback tests cover single sends, failure and replay refusal; they do not establish actual provider availability or model quality.

## Authorized GET stopped without fresh evidence

The [authorized GET attempt](../task52b-authorized-model-get.md) produced no HTTP status or validated model, and remains consumed despite sendStarted=false. Never infer a fresh expiry or reset claims merely because transmission was not recorded. The original expired GET stays unchanged.

A no-network probe reproduces an unstable marshal-based code fingerprint as local references change during an unchanged function's execution. The live capture's generic Refused category does not identify its exact branch. The selected116preflight tests passed, but supervisor fixtures replaced the exchange while TLS fixtures skipped actual supervision; that coverage gap matters. A stable full-code/constant identity and integrated supervised transport regression are needed before a new scoped live authorization. No guard was removed and no retry/count/inference was performed.

## Stable code identity and the missing integrated test

The [offline correction](../task52b-code-identity-fix.md) establishes why marshal was unsuitable: serialization flags changed when another reference to an unchanged constant existed. Source, bytecode and interpreter did not change. A stable typed identity retains full public code fields, nested constants and defaults, compares them with independently compiled pinned source, and checks original module/dependency bindings. Runtime facts use a new scheme; old consumed evidence is not rewritten.

The integrated local-TLS test now runs actual parent→child→source/credential checks→INTENT→fictional key loader→TLS→immutable response. Only isolated configuration/DNS/CA are supplied; exchange and authorization checks are not replaced. The original code still fails in that harness, while fixed code passes in fresh isolated interpreters. This closes the test gap without declaring the historical generic Refused branch proven, reading owner secrets, granting a retry, or qualifying the model. The old scope remains unusable; a new scope and separate owner approval are still required. The count runner's separate pinned marshal check is not silently migrated by this GET fix.

## Count migration and independent GET/count progression

The [dual-runner preparation](../task52b-both-readiness-preparation.md) applies the same deterministic source-compiled identity to count. Its original code still fails the actual supervised local-TLS regression; fixed code passes with the actual loader/writer/evidence gates, including durable INTENT before fictional key access. Two fake-exchange process tests are superseded by integrated denial, crash, concurrency, source-mutation and replay tests.

A new GET-only proposal is not a count authorization. Count's frozen payload/scope remain unchanged; its original proof selector is still expired. Future enrollment must use the actual successful new GET and genuinely fresh permission evidence with explicit owner approval, rather than manufacture timestamps or infer authority from a fixture. Both profiles retain the same UTC-day/24-hour policy and independently reject inference and duplicate sends. No real authority or model qualification is created by offline success.

## Corrected runner: one real GET200

The [fresh authorized GET](../task52b-authorized-fresh-model-get.md) validated gpt-6-luna at2026-11-18T04:35:55.524545Z and expires2026-11-19T00:00Z. Its body hash equals the older response, but freshness comes from this separately authorized actual send and scope, never from editing the older observation. Both prior consumed scopes remain intact and this new scope is also permanently consumed. The real execution passed deterministic source/runtime checks; model visibility still does not certify model quality, counts, prices or inference authority. No POST follows without reviewed actual-evidence binding, fresh permission evidence and separate owner approval.
