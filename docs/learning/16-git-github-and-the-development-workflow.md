# 16 — Git GitHub and the Development Workflow

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## History is part of the application

**Git** records snapshots of files in commits. A **commit** has an identity, parent(s), message and tree. **HEAD** is the currently selected commit; a **branch** is a movable name pointing at a line of development. **GitHub** hosts the remote repository. **Working tree** means the files on disk; the **index** or staging area selects what goes into the next commit. Where To? needs these distinctions because owner work, frozen evaluation artifacts and documentation can coexist without belonging in the same change.

The verified starting baseline was `a7ed106`, not just an assumed reported hash. Ten V5 files were initially untracked. **Untracked** means Git does not yet include a file in a commit; it never means disposable. While this course was authored, independent work committed them and additional V5 evidence as `b1efe96`. The course was reconciled to that checkpoint; this documentation change preserves it. Always reread status/HEAD before staging because another development session can change them.

## Read the actual project history

The inspected history contains:

```text
a7ed106 Task 52B Q4C: verify signed offline exact-schema continuation
b72dfa5 Task 52B Q4B: inspect historical journal read-only and define operator boundary
a4bd708 Task 52B Q4A: verify offline successor protocol with fictional state
```

Line 1 identifies the baseline's signed synthetic protocol checkpoint. Line 2 is its preceding read-only storage review. Line 3 records the offline foundation. The input to `git log` is repository history and optional selection arguments; the output is historical metadata, not an instruction to rerun those operations. A title saying “verify” does not turn offline tests into real paid authorization.

## A safe sequence for studying

From `/Users/rahularutla/Documents/whereto`:

```sh
pwd
git status --short
git rev-parse HEAD
git log -5 --oneline
git diff --stat
git diff -- README.md
```

Each line reads state: folder, tracked/untracked changes, exact HEAD, recent commits, changed-file summary, then the README patch. `git diff` does not include untracked file contents; inspect new files explicitly. `git show HEAD:backend/main.py` reads the committed version even if the working copy differs. `git log -- path` and `git blame path` help locate when a behavior changed; blame identifies historical lines, not personal fault.

## Safe coding practice needs isolation

A **worktree** is another checkout attached to the same Git repository. A branch alone does not separate file contents from existing uncommitted owner work. For later exercises, use a separate disposable worktree based on a reviewed commit, with no copied private profiles or credentials. The exercise guide describes this optional local step; the handbook author does not create it merely for demonstration.

A focused change should have acceptance criteria, source inspection, a minimal patch, relevant offline tests and a full diff review. `git add` should name the intended files. Avoid `git add .` when unrelated work exists. A **push** uploads commits to a remote branch. A **pull request**, PR, asks reviewers to inspect a branch's change before merging. **Merge** combines histories; a conflict needs deliberate reconciliation, not automatic deletion of one side.

A **revert** adds a commit undoing a prior change. **Reset/clean** can discard work and are inappropriate beginner troubleshooting commands in this project. Do not force-push, reset owner history, delete untracked files or initialize a replacement repository to resolve confusion.

## Versioning evidence

Frozen response hashes, schemas, rubrics and build identities make historical evaluation reproducible. If a semantic expectation changes, record a new version and compare it separately. Editing an old output to fit new expectations destroys the evidence of the original failure. Git can show the difference, but history is not an excuse to overwrite financial or approval journals.

The [development commands](DEVELOPMENT_COMMANDS.md) distinguish read-only checks, offline verification, startup that may use the owner's real profile, and explicitly out-of-scope resource actions. The root [AGENTS.md](../../AGENTS.md) requires preserving unrelated work and reviewing the complete diff before completion. README remains the beginner startup guide; the course supplements it.

## Five key takeaways

1. HEAD, branch, working tree and staging area differ.
2. Untracked owner files must be preserved.
3. A branch alone does not isolate dirty files.
4. Stage explicit paths and review new-file content.
5. Historical evidence needs versioned amendments rather than rewriting.

## Check your understanding

16.Q1. What does HEAD identify?
16.Q2. Does git diff show untracked contents?
16.Q3. What does push do?
16.Q4. Why avoid git add . here?
16.Q5. Why use a separate worktree for lessons?

## Code-reading exercise — 16.R

Run git log -3 --oneline -- backend/journey.py and compare one commit message with the corresponding diff.

## Practical exercise — 16.P

Write a staging plan naming only docs/learning and README/HANDOVER. Explain why scripts/task52_ordering_v5.py is excluded.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-16).

[Previous chapter](15-testing-mocks-debugging-and-error-handling.md) · [Contents](README.md) · [Next chapter](17-task-52b-cloud-ai-evaluation-and-ordering-research.md)
