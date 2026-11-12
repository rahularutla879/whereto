# Evidence, discrepancies and verification

## Scope and baseline

Researched November 10, 2026 against actual HEAD `a7ed1066fe3c082dd6e9b48dbfdfa58f53b610f8`, on branch `main`. The remote is the owner's existing private GitHub repository. This delivery adds documentation only: 30 Markdown files under `docs/learning`, a small root README link and a HANDOVER entry. Application behavior, prompts, model, policies, credentials, journals, approvals and infrastructure are unchanged. Task 53 was not started.

Ten pre-existing untracked V5 files were present initially and their hashes were captured. During authoring, independent work changed three of those files and committed the offline V5 checkpoint as `b1efe96f73448de9308886a4d1f2005680579c4c`, including additional evidence and root documentation updates. This course preserved that commit, read its specification/checklist and reconciled the lessons/index. The handbook author changed none of its implementation/research files. Preservation is checked against their new committed bytes, not falsely against the obsolete initial snapshot. Final clean-state verification follows the documentation commit/push.

## Repository research and source review

The static source/test map indexes 460 Python, TypeScript, TSX, launcher and SQL files across app/components/lib/backend/scripts, excluding installed dependencies, private configuration and generated output. Python AST (Abstract Syntax Tree) declarations and TypeScript export declarations were inspected to build the map before authoring. The key implementation review followed route entry points, client branches, interpretation/contracts, local model payload, source/calendar/duration checks, ordinary and advanced search/ranking/timing, Google transport/budgets, persistence/migrations, session/worker ownership and research identities. The map is a navigation index, not a claim that every test was executed.

Root README, AGENTS, CONSTRAINTS, HANDOVER, TASKS, ARCHITECTURE and DECISIONS were inspected for current versus historical scope. Q1–Q4C, ordering V1–V4, B1/B2/source/admission, Hitech investigation, cloud proposals and evaluation reports were cross-referenced. Installed Next route-handler documentation was checked locally. Existing code and explicit newer checkpoint evidence take precedence over stale descriptive headings. No new web research or current provider pricing/availability claims are needed for this repository snapshot.

## Important implementation/documentation discrepancies

| Issue | Verified implementation / consequence | Handbook treatment |
|---|---|---|
| Bare Sydney / Hitech City relative dates | `location_context.timezone_for` returns fallback UTC for each. `date_resolution.resolve_datetime` adds unsupported_date for today/tomorrow without exact manual date. | Chapter 7 explicitly stops fresh examples at calendar clarification and marks downstream steps conditional. Hitech geography fix does not fix timezone mapping. |
| Hitech spelling incident | Parent-bound Hitech/HITEC matching defect reproduced and fixed offline; original full response unavailable. | Defect distinguished from unproven original incident cause and live availability. |
| README historical task notes | Older sections say Task 51 unstarted; newer code/docs implement its local foundation. Task 52 remains in progress. | State timeline explained without rewriting historical notes. |
| ARCHITECTURE historical planned extension | Earlier Tasks 48/50A–50E headings say not implemented; later sections/code implement local saving/advanced flow. | Current local flow taught separately from historical status. |
| Early CONSTRAINTS capacity/travel scope | Party size is no longer an active capacity/ranking filter. Ordinary inter-stop caps remain scoped; advanced complete-trip constraints include applicable origin/return/dwell. | Explicit scope tables and path-specific limits; no blanket first/home exclusion for advanced journeys. |
| Legacy ordering versus source-first V4 | Active checks can accept the invented repeated-stop edge and can remove start/finish edges. V4 sees raw copies but is default OFF and never enforces. | Known gaps retained; no “fixed in production” claim. |
| Owner V5 default list order | Independently committed offline V5 prototype at b1efe96 changes proposed list semantics relative to frozen V4. | Committed prototype taught with its 66-case impact, finite coverage and prompt/Q3 incompatibility; no runtime activation or historical relabeling. |
| Ordinary real ranking versus old weighted summary | `score_candidates` is intermediate; current real path adds classification/verified-seconds priority and 60-second diversity; Surprise Me samples. | Chapter 10 explains final selection as well as scores, and distinguishes real beam from full mock product. |
| Admission foundations versus active admission | `planning_admission` guards are no-ops in ordinary startup; explicit Python test scope exercises that internal foundation. Task 51 request/inference admission is active separately. | Separate scopes; no active public semantic receipt claim. |
| Save reply / retained content | Generated results already carry save access token; `save` returns `{saved:true}` after transaction. Real provider content/routes/origin are excluded; advanced saves retain selected app-owned structure. | API and persistence lesson use exact response and retention distinctions. |
| AI prompt symbol and schema | Actual symbol is SYSTEM_PROMPT; the Ollama wire schema modifies derived Pydantic schema, excluding computed fields and requiring extraction fields. | Names and schema lesson match source, not an invented second prompt variable. |
| Original paid evaluator source compatibility | B2 extraction is behaviorally reconstructed; old pins intentionally refuse changed journey source. | No historical environment execution, paid override or qualification claim. |
| Q4B versus Q4C trust implementation | Q4B's historical design has no verifier; later Q4C implements a synthetic verifier only. | Timeline distinguishes implemented offline cryptography from absent real enrollment/authority. |

## Checks performed for this delivery

- Checked actual HEAD, branch, remote and initial Git status before authoring; captured byte hashes for all ten pre-existing untracked files.
- Inspected each authored chapter/reference, linked core claims to existing source functions and corrected the timezone, final real-ranking, save response, prompt-name and admission-scope distinctions above.
- Statically checked all relative Markdown targets and explicit heading fragments in `docs/learning` and the new root links. V5 source links were reconciled after the independent b1efe96 commit; no link requires uncommitted workspace-only data.
- Checked 20 chapter numbers, 30 course Markdown files, five takeaways/five comprehension questions per chapter, code excerpts, reading/practical exercises, separate solution anchors and counts (100 questions plus 40 hands-on exercises).
- Compared the API inventory to AST-discovered decorators in `backend/main.py` and the Next `app/api/**/route.ts` files: 13 explicit backend routes and 13 Next route handlers, including the health path translation. Request field tables were extracted without importing the application or generating live OpenAPI.
- Checked all nine Mermaid blocks for recognized flowchart/sequence forms, balanced labels/subgraphs/alt blocks and connections against inspected architecture. **No Mermaid renderer/parser was installed or executed**; visual rendering remains unverified in this task. Diagrams use simple standard syntax and remain readable as source.
- Ran a small offline pure-function calendar check with explicit `2026-11-10T15:00:00Z`: both public Sydney/today and Hitech City/tomorrow examples returned UTC fallback and unsupported_date. This called no AI, Google or database and does not count as browser/end-to-end acceptance.
- Reviewed the complete intended staged documentation diff including all new files, checked whitespace, scanned for credential-shaped material, and compared unrelated-file hashes to the independent committed checkpoint. The temporary authoring/validation scripts remain outside the repository.

## What was not verified, and why

No fresh model output, browser journey, real venue availability, Maps call, hosted SQL query, cloud provider request/counting/readiness, financial journal inspection or infrastructure check was performed. Full backend/frontend/lint/typecheck/build suites were not rerun because no application source or dependencies changed; historical totals are labeled historical, not reused as new passes. No new opt-in resource authorization was inferred.

## Remaining uncertain or incomplete evidence

- A–E actual fresh Qwen outputs and real venue/routing feasibility are unknown. C/D omit core inputs; A/B/E have the current calendar limitation. Every walkthrough branches at those boundaries.
- Bounded source grammar is not arbitrary-language correctness. The known legacy ordering gap remains. V5 committed offline artifacts are not an approved runtime semantic change.
- Original Hitech incident response/correlation/provider payload cannot be reconstructed from available sanitized aggregates; the exact incident cause is unconfirmed.
- Q1 independent gold/response review, six unresolved field judgments and broader semantic/latency coverage are incomplete. Historical model errors and proposed guards do not establish production qualification.
- Q4C verifies signed synthetic offline protocol facts, not real human independence, protected operator trust, real journal write recovery, power-loss/distributed durability or paid execution authority.
- Hosting proposals, historical provider prices/model metadata and fleet performance are unactivated/unmeasured here. No five-second end-to-end or public deployment claim is made.
- Mermaid rendering and a full accessibility/browser audit are not part of these source-based documentation checks.

[Course contents](README.md) · [Debugging playbook](DEBUGGING_PLAYBOOK.md)

## Task 52B local application fixture checkpoint

Reviewed chapters 3, 6, 7, 9, 10, 12, 14 and 15 against the actual adapter, FastAPI callback, frontend proxies, advanced sessions, budgets and save service. Updated chapters 3/7/9/12/15 plus command/debug references for the explicit fixture and its limits. The other 15 chapters and 20-chapter structure are preserved. [Exact current verification](../task52-v51-local-application-verification.json) distinguishes real browser checks, API tests, synthetic persistence and incomplete historical simulations.

## Task 52B manual/pending compatibility

Reviewed chapters 3/7/9/12/13/15 and their source references; updated those chapters plus glossary/debugging guidance. Other 14 chapters and the 20-chapter structure are preserved. [Current source/build identities, test totals and historical simulation results](../task52-v51-manual-pending-verification.json). Earlier fixture-only refusal and verification counts describe their earlier checkpoints.

## Task 52 packaging maintenance

Reviewed/updated chapters 3, 5, 6, 12, 14, 15 and 18, plus file map, commands, glossary and debugging references for the actual packaging artifacts. Existing 20-chapter structure and all other chapter content retained. No API contract or exercise answer was changed. Native assembled-payload checks and unavailable Docker verification must remain clearly distinguished; see [checkpoint](../task52-cloud-deployment-preparation.md).

## Task 52 actual local containers

Updated chapters 14, 15 and 18 plus commands, glossary and debugging guidance for verified Colima/Rosetta builds, runtime tests and unresolved vulnerability findings. Reviewed packaging references in chapters 3/5/6/12; their unchanged application explanations remain valid. No other chapter was changed; the 20-chapter structure and existing exercises are preserved. Source paths and signal behavior were checked against the installed Next/Uvicorn code. [Verification](../task52-local-container-verification.json).

## Task 52 container security remediation

Reviewed and updated chapters 5/14/15/18 plus glossary, commands and debugging references. All other chapters, the 20-chapter structure and existing exercises remain unchanged. References match the actual deployment lock, Docker pip-check step and exact-override packaging test. [Original/control/patched scanner comparison and test evidence](../task52-container-security-verification.json) distinguish automated findings from confirmed exploitability and preserve historical qualification identities.

## Task52 application financial authority

Reviewed chapters8/12–15/18; updated12–15/18 and glossary/commands/file map. Existing20-chapter structure and unrelated examples/exercises retained. New references name actual inactive modules/routines; UTF-8-byte accounting is explicitly fictional, and hosted isolation, model qualification and grant approval are not claimed. Exact results are in [the verification record](../task52-application-financial-verification.json).

## Task52 native reconstruction

Reviewed/updated chapters12–15/18 plus glossary/commands/file map. All20 chapters and unrelated exercises/examples preserved. References match the inactive native factories, leased SQL transitions, reusable selection-only receipt and synthetic process/restore tests. No normal-startup, browser or hosted-readiness claim. [Exact results](../task52-native-session-verification.json).

## Authenticated local service checkpoint

Reviewed chapters3/6/7/12–15/18/20; appended current experimental explanations to3/6/7/12–15/18, glossary, commands, file map and debugging references. All20 chapter files remain; unaffected chapter bytes and original explanations are preserved. Source paths, function names and local links were checked against the actual inactive profile. [Exact710-pass/16-skip verification and unexecuted checks](../task52-service-isolation-verification.json) distinguish local synthetic authority from hosted identity, model quality or production readiness.
