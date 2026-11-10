# Task 52B scope and exit review

Review baseline: clean `e55de4f0245ad8b1b427795582d04fec126a0b90`. This checkpoint changes planning documentation only. Recommendations below are not implementation, spending, halt-clearance or deployment approval.

## Actual roadmap and acceptance language

The numbered roadmap has **no separate original Task 52B checkbox or acceptance definition**. Task 52A/52B and Phase 1 are subsequent subdivisions. Both current [TASKS.md](../TASKS.md) and retained Phase 52A commit `285690b` say:

> Task 52 — Choose production-compatible hosting. Deploy the frontend and backend to services permitted for our intended usage.

> Task 53 — Configure environment variables and HTTPS. No secret keys in public frontend code or GitHub.

> Task 54 — Perform end-to-end testing. Generate, open, save, refresh, and view a plan on a phone.

> Task 55 — Invite initial testers. Collect feedback on recommendation quality, travel feasibility, and usefulness.

The later [52B implementation blueprint](task52-production-implementation-plan.md), step 2, adds this model-screen acceptance:

> Acceptance: critical semantic suite passes, no new hallucination acceptance, cost/count cap, matched latency and full/source-grounding tests. If no model passes, stop model promotion and revise proposal.

Its step 14 says:

> Owner approval is the final step before any P/public rollout. Do not proceed to Task 53–55 inside52B merely because infrastructure works.

The later [AI evaluation protocol](task52-ai-performance-evaluation.md#evaluation-corpus-and-scoring) requires:

> 100% required-stop/critical order/duration/deadline/return/identity preservation on this safety suite; zero unsafe accepted hallucinations/injection effects; no reduction in existing source-grounded tests

It separately proposes “≥98% fully correct semantic cases” for an **expanded corpus**, manual gold review and at least 20% held-out authored paraphrases. These are model qualification proposals, not original hosting-roadmap wording or evidence already achieved. Expanded/held-out paid cases outside the original 66-case matrix require separate authorization. The later five-second browser SLO, ≥1,000 actions/cohort and large synthetic concurrency rungs are release/performance proposals; neither the original hosting task nor the $12 experiment certifies or funds them.

Ordering V1–V4, shadow, validation extraction, admission receipts and source-version work arose from observed safety failures and later owner requests. They are useful evidence/foundations, **not an obligation to complete every architectural refactor before returning a model comparison**. Their safety findings remain binding: known unsafe acceptance cannot be hidden by a faster model or an aggregate score.

## Completion matrix

Categories: **Q** required to close current 52B Phase 1 qualification honestly; **H** required for full Task 52 hosting completion, after separate approval; **L** production/release work belonging to the actual later numbered task; **O** optional/deferred; **B** explicit blocker/owner decision. A blocker may gate Q or H; categories do not confer authorization.

| Item | Evidence / completed work | Remaining work and category |
|---|---|---|
| Provider-neutral synthetic screen | 66 fixed cases, original slots/caps, durable journal, errors/usage/latency/scoring tools | **Q/B:** reviewed successor evaluation identity and safe dispatch compatibility; original evaluator refuses changed B2 source. No bypass or repinning. |
| Semantic rubric and qualification | Structured/source checks plus case reviews; empty-gold evidence and generic-label scoring corrected separately | **Q:** adjudicate all applicable original gold criteria (25 journey, 26 ordinary, 15 prose cases); exact denominators, independent review gap and critical failures visible. Unreviewed output is not fully correct. |
| Independent ordering assessment | V4 offline proof, bounded grammar, 27 Qwen/seven OpenAI replays; default-OFF observer | **Q:** bind immutable raw output, complete legacy result and independent V4 decision in an offline evaluation-only adapter. Test missing as well as extra/reversed edges. Unknowns remain safe failures/clarifications. |
| B1 capture and B2 duration extraction | 75 reconstruction traces, 25 mutation traces; new runtime identity; full regressions green | **O:** defer B3 and general C/D/E extraction. No qualification prerequisite demonstrated. |
| Authoritative V4 runtime integration | Design exists; legacy remains authoritative, including known unsafe ordering/start-finish limitations | **H/B:** before cloud interpretation activation, approve and qualify one enforcing trust boundary or another demonstrably safe design. Required change is safety behavior, not a prescribed complete phase decomposition. No deployment of the known unsafe path. |
| Typed ordering confirmation | Occurrence/revision/capability design only | **O:** existing rephrase outcome is sufficient initially. Rich confirmation can be separately scoped later; no invented new roadmap number. |
| OpenAI GPT-6 Luna | Seven outputs: five compatible/correct under agent rubrics, one trusted provenance rejection, one accepted critical invented edge | **Q/B:** not qualified. Preserve failure/halt. Decide whether a separately versioned guarded system merits bounded evaluation, or reject this candidate/profile and return no selection. |
| Gemini Developer API | Two consumed generic HTTP 400s; later IP-blocked metadata access | **Q/B:** finite compatibility decision below. Mark blocked/unavailable if not resolvable; never silently substitute Vertex. |
| Anthropic | One grammar compilation failure; input length already fixed | **Q/B:** finite schema-equivalence/support decision below; token increase is irrelevant. |
| Comparison/recommendation | Historical timing/costs preserved; no qualified model | **Q:** reviewed comparison with unavailable metrics, raw vs guarded outcomes, and either qualified selection recommendation or explicit no-selection/blocker decision. No obligation to spend every remaining slot. |
| Hosting choice/usage compatibility | Proposed Cloud Run/state/Supabase architecture and capacity/cost analysis | **H/B:** owner-approved commercial services, model processing region/terms, current exact quotes, workload and spending envelope. Design is not deployment. |
| Shared admission/sessions/provider accounting | Process-local foundation plus opaque-reference/SQL/Redis design | **H:** if using proposed multi-instance hosting, implement and verify shared atomic ownership/reservation/fencing/expiry before deployment. This cannot be renamed Task 53 to make Task 52 complete. |
| Containers, readiness and minimum hosting proof | Blueprint only; no new resources | **H:** separately authorized deployment; frontend/backend operate independently of owner Mac, correct ingress/readiness, minimal safe staging acceptance and rollback. |
| Environment/secrets/HTTPS configuration | Local protections exist; production configuration unimplemented | **L: Task 53.** Minimum secure staging credential/transport plumbing needed to test Task 52 is a dependency, not permission to complete the general Task 53 rollout inside Phase 1. Never deploy exposed secrets/plaintext to defer safety. |
| Full generate/open/save/refresh/phone release acceptance | Local historical tests do not certify hosted release | **L: Task 54**, including original ordinary/complex journey acceptance and cross-task environment/HTTPS validation. Hosting smoke still belongs to Task 52; it is not full end-to-end signoff. |
| Public tester recruitment | Unstarted | **L: Task 55**, not model qualification or hosting research. |
| Large load rungs, GPU/hybrid routing, general parser, rich UI, exact historical-environment recovery | Proposals or separate blocked research | **O:** only reopen for a measured need. No automatic expansion of grammar, models, paid corpus or infrastructure. |

## Minimum safe qualification architecture — no further general extraction

Further B3/C/D/E extraction is **not necessary before offline cloud comparison**. The current complete legacy validator can remain atomic. An isolated, explicitly named evaluation adapter can take copies of strict raw extraction/source, execute the unchanged complete legacy validation under the B2 identity, and independently inspect raw ordering with V4 before legacy normalization erases evidence. Run both without network/provider side effects. Retain the full non-order/calendar/endpoint checks; V4 checks alone cannot certify an interpretation.

Report three distinct results: (1) raw model correctness against reviewed source expectations, (2) legacy validation outcome, (3) proposed guarded-system disposition. A safe unordered projection is an audited model error, not raw correctness. A rejected invented edge is a safe failure, not a successful extraction. Missing explicit mandatory relationships, occurrence ownership, ordinary interpretations without Journey and ambiguous endpoints need explicit tests. If the existing V4 helper does not fully cover a case, mark it unresolved rather than fabricating proof. Bind source/runtime/schema/prompt/scorer/configuration/response identities and deterministic clocks; unknown combinations fail closed. No internal preparation record or model JSON issues planning authority.

This is an offline architecture proposal, not implemented enforcement or a replacement historical evaluator. The frozen original evaluator continues refusing current changed pins. Before paid continuation, a separately approved successor dispatch integration must reuse the **same journal**, retain its root, old rows/corrections and persistent halt history, and bind the new approval/version/unused slots. Existing unit-test reference scopes are never a live-dispatch path. If an append-only continuation cannot coexist safely with the source gate/halt, remain blocked; do not create another journal or generic override.

No restoration of exact historical execution is needed for separately labeled current-runtime comparison. It remains necessary if someone later claims exact historical reproduction. B2 reconstruction is neither that proof nor model qualification.

## Seven historical OpenAI outputs

| Original r1 slot / prompt cohort | Historical disposition to preserve | Offline qualification relevance |
|---|---|---|
| journey-01 / v3 | HTTP200; original row decoder error, append-only offline correction; valid/source accepted | Dinner/drinks/geography/date agent-reviewed correct after evidence comparator fix; not independent signoff. |
| ordinary-dinner / v3 | Accepted | Correct ordinary extraction under reviewed rubric. |
| journey-03 / v3 | Accepted | Exact named college preserved. |
| journey-07 / v3 | Trusted rejection | Graph direction correct but `first, then` fails required stop-bound provenance; remains a safe failure. |
| journey-04 / v4 prompt | Accepted | College→coffee supported. |
| extension-partial / v4 prompt | Accepted | Pharmacy→bank only; independent coffee required. |
| extension-repeated / v4 prompt | **Accepted critical failure** | Extra coffee0→museum1 unsupported; correct museum1→coffee2/return/180-minute bound do not cure it. V4 offline rejects the extra edge. |

All seven are structured-valid; legacy trusted acceptance is 6/7, agent-reviewed correctness 5/7, two distinct failures. Historical rows, scores, latency and reservations remain unchanged. These are tiny mixed-version engineering samples, not seven independent human-qualified successes or a production accuracy estimate. Neither model nor guarded profile qualifies today. The persistent halt remains authoritative. No remaining slot is implicitly authorized by this review.

## Finite provider compatibility decisions

- **Gemini:** first assemble one sanitized evidence package with exact service/version/model/schema/configuration identities and allowlisted error classification; compare existing exact payloads with already retained official API/schema guidance. Request provider support clarification if needed, but sending a support message/package requires owner authorization. The two generic 400s do not establish a specific schema defect. Separately have the owner approve any necessary evaluation-key egress-IP correction; do not widen restrictions or touch Maps. Prove mechanical schema equivalence offline. Stop with “blocked” if provider guidance cannot establish compatibility. Only afterward propose one unused-slot compatibility attempt with exact cap and halt; no speculative schema ladder or repeat of consumed slots. Developer API and managed Vertex are different products/privacy/IAM/billing paths; choosing the latter needs an explicit decision.
- **Anthropic:** produce one factoring/complexity-reduction proposal (for example shared nullable-Duration definitions), preserving all canonical fields, required/null meanings, bounds and provenance. Check exact documented dialect and reference-expanded complexity offline; source-level union counts or token counts do not prove server grammar compilation. Seek provider-supported compilation guidance for existing error evidence, subject to permission to contact support. If equivalence/provider support is insufficient, mark blocked. A later single unused-slot compatibility attempt needs separate authorization; never rerun the failed slot or purchase credits.
- **OpenAI:** decide on the versioned guarded evaluation above before any new inference; freeze raw-vs-effective scoring and full-case review. Refresh availability, complete input counts, prices, credits, processing conditions and expiry only in a future authorized readiness checkpoint. Historical readiness/credits are not current verification. No prompt tuning is automatically required by this scope review.

A blocked candidate can be reported as unavailable in a valid partial comparison. It cannot be declared slower/inaccurate from HTTP errors, or silently replaced. If no candidate meets hard gates, finish Phase 1 with **no production model selection** and a specific owner decision, not an endless refactor.

## Hosting design versus deployment

The existing proposal is Google `us-east4` frontend/backend, volatile encrypted Redis evidence, regional HA operational PostgreSQL authority, and retained Supabase saved plans in AWS `us-east-1`. SQL owns atomic revision/claim/consume/revoke, ownership fences, reservation and uncertain dispatch records; Redis is not financial/single-use truth. A signed token alone cannot prevent replay. Current process-local receipts are neither restart-durable nor multi-instance authority; all new-work entry points need the approved issuer/consumer design before distributed activation.

These are **recorded estimates, not freshly verified prices or approved purchases**: fixed infrastructure $457–1,160/month before AI/Maps, proposed staging review ceiling $1,300/month; illustrative 50-DAU scenario $1,100–1,800/month including assumed usage; proposed public review envelope $2,000/month. Separate staging and production increase costs. Old GPT-4.1-mini-based cost assumptions do not price the current candidate. Exact machine/HA/storage/egress/tax/support quotes, Google volatile-content terms, fleet quotas, pooling, retention and operator burden remain decisions. Owner may approve a simpler safe architecture; the proposed premium HA inventory is not an original Task 52 mandate.

Hosting region does not establish inference residency. Historical OpenAI synthetic testing used Standard global processing, store=false and standard abuse-retention conditions; synthetic permission is not private-user processing approval. Production model DPA/region/logging/retention and Google ephemeral-state terms block activation even after semantic qualification. No current provider terms or account balances were refreshed here.

**Selection blockers:** incomplete rubric/held-out evidence, critical ordering failure, unavailable provider output/compatibility, versioned evaluator readiness and matched correctness/latency/usage evidence. **Deployment blockers:** approved production terms/region/recurring cost, authoritative ordering trust boundary and all planning admission issuers, shared atomic state/accounting, secure build/ingress/secret delivery/readiness, quotas, operational recovery and actual hosted proof. End-to-end five-second performance remains unproven and needs separately budgeted full-pipeline release evidence; model-only timing cannot establish it.

## Bounded remaining checkpoints and approvals

Each row is one checkpoint with one deliverable and one gate; do not automatically advance or refactor beyond it.

| Checkpoint | Single measurable deliverable | Acceptance gate / approval |
|---|---|---|
| Q1 — freeze qualification contract | One versioned offline qualification specification with all 66 case rubrics, raw/legacy/guarded outcome definitions and a source/runtime/scorer manifest | Every critical field has an applicable expectation or explicit unresolved judgment; seven outputs and original negative probes replay with no unsupported edge admitted. No historical relabeling; owner reviews remaining grammar/independent-review limits. No B3 required. |
| Q2 — close provider compatibility decisions | One three-provider readiness/blocker table with exact supported payload identities and one finite disposition/provider | Offline schema equivalence established or provider explicitly blocked; no speculative paid probes. Owner decisions for IP/service/schema changes, support contact and any nonbillable checks precede those actions. |
| Q3 — propose bounded continuation | One exact ordered unused-slot plan and append-only same-journal/version/admission patch proposal | Offline tests prove unchanged original rows/halt history, duplicate refusal, full reservations, caps/no retries, source/profile matching and immediate semantic stop. Owner explicitly approves continuation; this review does not clear the halt. |
| Q4 — execute/review only an approved screen | One reproducible correctness/latency/token/cost comparison with per-failure evidence | Fresh readiness plus approved dispatch bounds; stop at first critical/unknown. Preserve consumed matrix slots. If evidence inadequate, return “not qualified,” not an automatically expanded batch. Any later full-matrix/expanded-corpus proposal is one new bounded owner decision. |
| Q5 — Phase 1 owner decision | One signed-off model recommendation or explicit no-selection/blocker report | Hard gates and exact sample/repetition denominators supported; independent review status/98% expanded-corpus applicability stated. No tiny sample qualification. Either approve next hosting package or stop Phase 1 blocked; unused allowances are not obligations. |
| H1 — full Task 52 continuation, separately authorized | One accepted hosting deployment against an approved exact configuration/budget and safety acceptance inventory | Only after selection/safety and hosting approvals: implement minimum necessary runtime enforcement/admission/shared state, build/deploy and prove independent frontend/backend operation, ingress/readiness/accounting/rollback. Existing blueprint supplies detailed tests; do not make general B–E refactoring a separate gate. No resources now authorized. |

Q1–Q5 close the **current model-qualification Phase 1**, possibly with no selection. They do not complete the original hosting Task 52. If a comparison cannot be supported within remaining original slots or money, request a revised experiment decision; never top up, reallocate provider attempts or add expanded paid cases automatically. All three repetitions remain part of the original planned matrix; consumed mixed-version failures cannot be rerun to construct an artificial clean cohort.

**Exact stopping boundary:** full Task 52B/Task 52 ends only when the approved hosting choice is actually implemented and frontend/backend deployment acceptance is documented; owner reviews unresolved model/SLO/production risks. If no safe model/hosting path is approved, Task 52 remains in progress or explicitly blocked. Task 53 then owns production environment/secrets/HTTPS configuration acceptance; Task 54 owns full hosted generate/open/save/refresh/phone end-to-end acceptance; Task 55 owns inviting testers. Where secure staging dependencies overlap Task 53, record the prerequisite and leave its broader checkbox uncompleted. Do not redefine deployment as a later invented task, or claim public Stage 1 completion from private staging alone.

## Read-only verification and preserved limits

- Clean start and expected HEAD verified. Original roadmap wording checked at current HEAD and retained `285690b`. Inspected current validation phases, same-position duration delegate, internal registry, shadow and linked version/architecture/evaluation reports.
- Existing B2 evidence: backend 1,171 passed /37 opt-in skips; frontend 285; TypeScript/lint/build passed. These are **prior implementation checks**, not rerun for documentation-only changes. No fresh browser/model/hosted test or performance claim.
- Read-only SQLite integrity `ok`; provider counts OpenAI 7 / Google 2 / Anthropic 1, total 10/594, 584 remaining. Accounted $0.047366625; remaining $11.952633375. Journal SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`; all 324 private files match the retained prior snapshot; last recorded halt preserved.
- Original six pins/corpus/manifests/paid records and runtime sources are outside this documentation diff. Original $12 aggregate, 198/provider, 12k input/2k output, concurrency one and zero retries unchanged. V4 enforcement unavailable; shadow default-OFF; Qwen and current app behavior unchanged.
- Delivery checks: documentation links/quotes, complete new/tracked diff, whitespace and configured-secret scan. No inference/counting/Maps/provider request, accounting change, purchase, credential/permission/billing change, deployment, migration, infrastructure or Task 53 work.
