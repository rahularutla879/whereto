# Where To? — developer learning handbook

A complete self-study course for the product owner, beginning with programming vocabulary and ending with safe investigation of the actual application.

**Research baseline:** `a7ed1066fe3c082dd6e9b48dbfdfa58f53b610f8`, November 10, 2026. This is a source-based handbook, not a fresh live acceptance test. Ten initially untracked V5 files were independently committed during authoring as `b1efe96f73448de9308886a4d1f2005680579c4c`; this course includes that offline checkpoint while preserving application behavior. [Evidence, discrepancies and limitations](VERIFICATION.md).

## How to begin

Start with chapter 1 and keep the glossary open. Study chapters 2–6 in order before reading request traces. Each sitting can cover one chapter: read, locate the linked functions, answer five questions, then do the reading and practical exercise. Check the separate solutions afterward. Do not run paid providers to complete a lesson.

- **First pass — foundations:** chapters 1–6. Learn values, functions, browser/server boundaries and contracts.
- **Second pass — one request:** chapters 7–11. Trace source words into validated requirements, candidates, routes and options.
- **Third pass — state and safety:** chapters 12–15. Learn saving, lifetimes, accounting and offline verification.
- **Fourth pass — independent development:** chapters 16–20. Understand history, evaluation limits, cloud proposals and safe modifications.

There are **20 chapters, 100 comprehension questions and 40 hands-on exercises** (20 code-reading and 20 practical): **140 numbered learning activities**. Begin with read-only work. Later exercises describe an isolated worktree; none requires changing this application's production behavior.

## Chapters

1. [01 — What Where To Does and Everything Built So Far](01-what-where-to-does-and-everything-built-so-far.md)
2. [02 — Programming and Web Development Fundamentals](02-programming-and-web-development-fundamentals.md)
3. [03 — Overall Application Architecture](03-overall-application-architecture.md)
4. [04 — Frontend React Next.js TypeScript and Tailwind](04-frontend-react-next-js-typescript-and-tailwind.md)
5. [05 — Backend Python FastAPI and Pydantic](05-backend-python-fastapi-and-pydantic.md)
6. [06 — APIs HTTP JSON and Frontend Backend Communication](06-apis-http-json-and-frontend-backend-communication.md)
7. [07 — Complete End to End Outing Request Lifecycle](07-complete-end-to-end-outing-request-lifecycle.md)
8. [08 — AI Interpretation Qwen Ollama Prompts and Structured JSON](08-ai-interpretation-qwen-ollama-prompts-and-structured-json.md)
9. [09 — Validation Source Grounding and Ordering Rules](09-validation-source-grounding-and-ordering-rules.md)
10. [10 — Planning Algorithms Filtering Scheduling and Ranking](10-planning-algorithms-filtering-scheduling-and-ranking.md)
11. [11 — Google Places and Routes APIs](11-google-places-and-routes-apis.md)
12. [12 — PostgreSQL Supabase Sessions and Saved Plans](12-postgresql-supabase-sessions-and-saved-plans.md)
13. [13 — State Management Caching and Request Lifecycles](13-state-management-caching-and-request-lifecycles.md)
14. [14 — Security Rate Limits Accounting and Reliability](14-security-rate-limits-accounting-and-reliability.md)
15. [15 — Testing Mocks Debugging and Error Handling](15-testing-mocks-debugging-and-error-handling.md)
16. [16 — Git GitHub and the Development Workflow](16-git-github-and-the-development-workflow.md)
17. [17 — Task 52B Cloud AI Evaluation and Ordering Research](17-task-52b-cloud-ai-evaluation-and-ordering-research.md)
18. [18 — Cloud Hosting Deployment and Scalability](18-cloud-hosting-deployment-and-scalability.md)
19. [19 — How to Read Debug and Modify This Codebase Yourself](19-how-to-read-debug-and-modify-this-codebase-yourself.md)
20. [20 — Complete Project Glossary and Technical Reference](20-complete-project-glossary-and-technical-reference.md)

## Practical references

- [Project file map](PROJECT_FILE_MAP.md) — verified directories, important files and source/test symbol index.
- [API reference](API_REFERENCE.md) — current routes, request contracts, response families and failure rules.
- [Data-flow reference](DATA_FLOW_REFERENCE.md) — values, owners, transformations and privacy boundaries.
- [Debugging playbook](DEBUGGING_PLAYBOOK.md) — symptoms and bounded investigation using actual messages/checks.
- [Development commands](DEVELOPMENT_COMMANDS.md) — read-only, offline, startup and isolation instructions.
- [Exercise workbook](LEARNING_EXERCISES.md) — all 140 activities and optional isolated practice setup.
- [Exercise solutions](EXERCISE_SOLUTIONS.md) — separate answers and guidance.
- [Glossary](GLOSSARY.md) — definitions with project examples and source links.
- [Verification and evidence limits](VERIFICATION.md) — source discrepancies, checks and boundaries.

## Reading conventions

**Implemented** names executable application behavior. **Offline prototype** names research not activated in planning. **Proposed** names a design not deployed. **Historical evidence** retains its original conditions and does not count as a fresh verification. Worked venue/time/score tables are fictional teaching data, never real availability or price claims.

Links are relative to the repository. A function name tells you what to search within the linked file. Markdown viewers differ in Mermaid support; diagram source remains readable even where diagrams are not rendered. [Root startup guide](../../README.md) remains the source for the owner's ordinary two-terminal startup.
