# Development rules

These rules apply to every development session in this project.

- Make technically justified decisions; explain disagreements instead of automatically agreeing.
- Inspect existing code before changing it. Preserve working functionality and visual design unless the task requires changes.
- Choose simple, reliable, maintainable solutions. Avoid unnecessary refactoring and documentation overhead.
- Assume the owner has no coding knowledge. Explain outcomes plainly and give exact, consistent instructions, including the working folder and commands when needed.
- Work on one focused task at a time. Establish acceptance criteria before implementation and stop when they are satisfied.
- Test relevant functionality, not just compilation. Report exactly what passed, failed, or was not tested; never treat source inspection as browser verification.
- Before reporting completion, review the full Git diff, including new files and existing changes. If Git is unavailable, disclose that and compare against a pre-edit file snapshot; do not initialize Git without authorization.
- Never expose secrets or make destructive changes without approval. Follow [CONSTRAINTS.md](CONSTRAINTS.md) for safeguards and hard planning constraints.
- Distinguish fictional data from verified information and implemented features from future plans.
- Update documentation when relevant: current state and checks in HANDOVER.md, milestone status in TASKS.md, significant decisions in DECISIONS.md, structural changes in ARCHITECTURE.md. Keep README.md as the beginner startup guide.
- For application, architecture, contract, data-flow, algorithm, dependency, configuration, security or testing-strategy changes, review and update the affected developer-handbook material in `docs/learning/`. Preserve the 20-chapter structure and unaffected material. Verify examples and references against the code, distinguish production from experimental behavior, and report which chapters were reviewed and updated. Keep documentation-only, evaluation-record-only and fixture-only edits out of unaffected chapters. Commit handbook updates with the implementation.
- Start by reading HANDOVER.md and CONSTRAINTS.md, then TASKS.md and relevant architecture/decisions. Inspect Git status and preserve unrelated work.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
