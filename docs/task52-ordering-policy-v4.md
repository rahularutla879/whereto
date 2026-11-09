# Ordering V4 release-gap closure and default-OFF shadow

`52b-order-policy-v4-shadow` closes the three demonstrated V3 gaps in a separately frozen policy. A real observer is wired at the API interpretation boundary, **OFF by default and selectable only through an explicit local Python test context**. It never authorizes a plan, changes an interpretation, normalizes the active graph, asks a question or returns diagnostics in the application response. No new model, counting, provider or Maps requests were sent.

Baseline: clean `d271ed1c349d21dfb7bf598a3e6eb47e724c3025`. [New measurements/hashes/replays](task52-ordering-v4-results.json), [20 predeclared contrasts](task52-ordering-v4-cases.json), [10 separated post-freeze cases](task52-ordering-v4-holdouts.json). The original [V3 policy](task52-ordering-policy-v3.md), fixtures, measurements and classifications remain historical. Policy V4 is unrelated to the frozen cloud **prompt** V4: no prompt, canonical schema or paid configuration changed. All rubrics here are same-agent reviews, not independent human signoff or population accuracy.

## Three finite changes

1. **Binary start/finish plus neutral context:** allow a source-owned `in <exact extracted location>` suffix and a finite relative date word on the existing binary start/finish construction. The entire residual suffix must match; wrong/missing locations, additional clauses, conditions and unowned qualifier words still block. Geography/date values remain unchanged and subject to the existing canonical checks. No return or duration is created.
2. **Three-stop global first/last:** accept exactly `Start with/at A, visit B, and finish at C`, with three independently bound required occurrences. Explicit global first and last constraints establish A→B and B→C (therefore A→C), rather than inferring order from commas. Both edges require a quote containing the complete supporting first/last construction, all owned stop phrases and its cues. The recorded leading cue offset identifies the global construction; the grammar independently verifies both start and finish, not just that one offset. Repeated A/C names remain distinct source occurrences. Conditional/optional middle visits and unrecognized connectors remain unknown.
3. **Do imperative:** recognize only actual source-leading `Do ` outside the first stop span. It does not establish order: `Do dinner and bowling` remains unordered; `Do dinner before bowling` still requires the independently proven directional edge. `Do not...` remains negative and blocked. Named words inside stop identities cannot become imperative/cue evidence.

The finite helper deliberately treats `home`/start-like visit labels as endpoint ambiguity, not a confirmed visit or origin. A real named establishment containing Start/Finish remains an exact identity owned by its own span; those words do not establish a relationship.

## One authority and immutable raw errors

V4 retains V3's A–F contract: proven mandatory order; independently proved unordered activity lists; audited empty-graph projection of source-bound forward model edges only on a clearly unordered source; unknown potential requirements; conditional/conflicting requirements; and scoped partial orders. Its decision retains original graph/hash, source/cue/occurrence proof, unsupported model relationships, normalization reason and ordering-only next action. Insufficient evidence never authorizes deletion of a potentially real requirement.

An audited projection is not a correct raw model extraction. Exact identity, occurrence count, required/optional status, date, durations, deadlines and endpoints remain independently validated. `maybe coffee` stays optional; `whenever convenient` alone does not make coffee optional. The shadow invokes `inspect_order`, never `project`, and discards all proposed trusted graphs. Legacy validation/normalization remains the sole active authority. **It can still erase start/finish edges in the active response**; the V4 proof preserves them only in the observer decision. An explicit test confirms both raw edges are observed while the legacy response graph remains empty. This task does not claim to fix that live behavior without enforcement approval.

## Frozen replay and negative evidence

| Measurement | Frozen V3 | Refined V4 |
|---|---:|---:|
| Correct recorded Qwen raw graphs compatible |18/18|18/18|
| Auditable unordered Qwen projections |7|7|
| Incorrect repeated-stop Qwen graphs rejected |2/2|2/2|
| Correct recorded OpenAI outputs compatible |5/5|5/5|
| Incorrect recorded OpenAI outputs rejected |2/2|2/2|
| Three original clear release gaps clarified |3/3|0/3|
| New declared source rubrics matched |Compared separately in machine report|20/20|
| Separated post-freeze rubrics matched |Compared separately in machine report|10/10|
| False clarification on new reviewed clear sources |11/15|0/15|
| Negative/ambiguous new sources incorrectly accepted |—|0/15|
| Original unsupported edge replacements retained |0/147|0/147|
| Additional unsupported edge replacements retained |—|0/33|

All ten original V3 unknown-source cases remain safely clarified; V3's29 cases,8 final holdouts and28 promoted regressions retain their outcomes. Original V1/V2 tests and their fixture/probe expectations remain unchanged. Qwen's five other canonical return/time/identity blocks remain unresolved. Cloud journey-07 still fails inadequate cue-only evidence; extension-repeated still fails the invented coffee0→museum1 edge while museum1→coffee2 stays proved. No output, score, reservation or historical classification was rewritten.

The180 edge probes are overlapping fixture tests, not180 independent real requests. Forward invented edges on an independently proved unordered list may be projected empty in the **offline decision**; the unsupported edge itself is never retained or marked correct. The real shadow does not apply even that projection. Negative tests include reversed/missing edges, partial-order extra chains, repeated names, borrowed/missing quotes, Start/Finish names, conditional/global/distant qualifiers, wrong city, endpoint ambiguity and the original coffee failure.

## Actual shadow boundary and isolation

The initial proposed hook in `backend.interpretation.interpret_request` was removed after the frozen corpus correctly rejected a changed pinned source hash. **That file is byte-identical to baseline**. The authoritative66-case corpus/hash checks and paid tooling were not relaxed.

`backend.main.interpret_outing` now delegates through `backend.ordering_shadow.interpret_observed` before `interpret_request` proceeds. OFF calls the original operation exactly as before. Explicit local `capture_local_test()` selection decorates only its lazy provider: the existing factory/provider runs once, its returned extraction is strictly validated into a separate observer snapshot, and the **original extracted object** continues into the unchanged interpreter and legacy normalizer. No alternative provider, fallback or retry exists. Observer failure cannot trigger another model call. An optional-module import failure before dispatch safely uses the original operation; failures after dispatch never cause a fallback dispatch.

Saved pending follow-ups may already contain normalized effective graphs. They therefore emit only `saved_snapshot_skip`, continue unchanged with no extra AI, and are **not claimed as raw-model observation**. Direct Python calls to the pinned interpreter bypass this API-only observer. These are explicit coverage limits.

Diagnostics exist only in the caller's transient local-test context, maximum16 entries. Only allowlisted category/outcome/status enums, bounded counts and a boolean normalization comparison are exposed—no source text, quotes, offsets, stable text hashes, keys, response bodies, locations or plan capabilities. No new operational log, database or saved-plan storage is added.

One daemon worker maximum, no queue,8,000 source characters,32 stops,32KiB serialized interpretation and frozen bounded matching work. The request waits at most the configured25ms interval for observation; timeout/error/busy/oversize skips observation rather than changing the user outcome. A stuck worker holds only one bounded snapshot and prevents further observation until it finishes. Threads are not forcibly killed; OS/GIL scheduling and the bounded caller-side snapshot/serialization cost prevent any hard real-time guarantee. This is local-test instrumentation, not a public production monitoring service.

ON/OFF tests compare actual HTTP status/body, full interpretation/questions/pending state, legacy empty-graph normalization, main session handoff, actual advanced-session content/count, and unchanged save/routing invocation counts. They also cover strict parser rejection, destructive observer mutation, timeout/internal/import error, saturated worker, bounded diagnostics and saved-followup skip. No observer output is consumed by route/session admission.

A local browser smoke used fixed synthetic text, a fake provider and the real ASGI interpretation boundary. OFF/ON both returned HTTP200 and identical full response bodies; the fake provider ran once each. This was an isolated loopback fixture page, **not** a live Qwen/Google test or full planner UI acceptance. Its temporary server was stopped afterward.

## Performance and release decision


| Local fixture measurement | Samples | p50 µs | p95 µs | Maximum µs |
|---|---:|---:|---:|---:|
|Policy only|1000|102.959|168.125|300.375|
|Interpretation boundary OFF|100|460.708|550.167|825.792|
|Interpretation boundary ON|100|736.000|860.500|11836.084|

All100 ON fixture observations completed; no timeout/busy/error in this timing sample. Error/timeout behavior is tested separately. The difference of boundary medians is about0.275ms, not a production latency estimate.

See the bound machine report for exact timings. Local policy-only measurement uses1,000 checks (50×20); interpretation boundary uses100 OFF and100 ON calls with a fake provider and fixed clock. It includes observer copy/thread/wait overhead but excludes network/model/routing/browser latency. No production p95, cloud-model speed or five-second end-to-end claim follows.

The three specified gaps are closed and a separately approved enforcement implementation can now be considered. **Enforcement is not activated or automatically release-ready.** Resolve the full regression-suite date-fixture failures and review the finite grammar, skipped pending-snapshot coverage and clarification contract first. Conditional, alternative, unfamiliar or distant relationships still clarify; offsets alone are never semantic proof. Do not expand the grammar into a general parser merely to suppress questions.

For a future enforcement switch, insert one source-first authority inside the pinned interpreter only under a new reviewed application/evaluation compatibility version. Retire overlapping legacy order normalization/cue-only checks for that profile; do not let both mutate the graph. Keep all other canonical checks and block ordinary/advanced session publication on unknown. Existing rephrase remains safe; typed occurrence-bound ordering confirmations need a separately implemented user-provenance contract without another AI call. Rollback disables new enforced admissions and invalidates dependent pending/session versions, without rewriting historical evidence. Turning off shadow requires only leaving the local test context; ordinary startup already leaves it OFF.

## Paid and provider boundaries

The original SQLite journal/root/ten rows/corrections and324 ignored private files stay byte-identical; persistent v4 paid halt remains. OpenAI7/Google2/Anthropic1 =10/594;584 remain (191/196/197). Retained$0.047366625; remaining$11.952633375. Original$12/594/198,12k input/2k output, concurrency1 and retries0 unchanged. No reservation, retry, refund, approval sidecar or new paid journal was created.

Gemini's two historical Developer API400s and separate IP restriction remain unresolved; Anthropic's grammar-size compilation failure remains unresolved. No keys, schemas, endpoints, billing, quotas, credits, production model, cloud infrastructure, database migration or Task53 changes occurred. Recommended next task is owner review of the measured release/observer contract and a bounded regression/date-fixture maintenance checkpoint before any enforcement or paid-evaluation proposal.

## Verification checkpoint

Final focused ordering/source/parser/interpretation/shadow suite: **107/107 passed** (5.404s). New shadow/release-only tests18/18 passed. Full frontend **283/283 passed** (116.793s); TypeScript, lint and production build passed. Initial TypeScript execution overlapped the build's generated `.next/types` replacement and was rerun successfully after the build finished; no TypeScript source fix was needed.

The required full backend run is **not green**:1,125 tests ran,15 failure entries,30 errors,37 skipped (139.229s). Subtests create extra failure entries, so do not subtract these counts to claim an exact passing total. All41 distinct failing methods reproduced the **same failing set** with the new shadow explicitly bypassed (15 failure entries/30 errors again). Many fixtures use2026-11-07 and now hit the unchanged date-expiry boundary before their expected quota/routing/save assertions; the local HTTP API fixtures show the same422-versus200 consequence. Representative date failures were also reproduced separately. No assertion, fixture date, production clock or expiry guard was weakened or rewritten. Initial sandbox failures for local HTTP/Node IPC were resolved by the authorized local-permission run; external/model transports stayed blocked. This confirms pre-existing suite failures, not a green release qualification. Fix or explicitly clock these test fixtures in a separate maintenance checkpoint before enforcement approval.

[Machine-readable verification and baseline comparison](task52-ordering-v4-verification.json). Standard secret scan and scans of all3 actual evaluation key values across current/new files/history found zero matches. Configuration/journal are ignored mode600. SQLite integrity, all10 row hashes/root/corrections,324 private files and actual halted recovery were checked read-only and unchanged. Journal SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`. Full tracked/new diff, frozen hashes, JSON and local links reviewed. No new dependency or startup setting was added.
