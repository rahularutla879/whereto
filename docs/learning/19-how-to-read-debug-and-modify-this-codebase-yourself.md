# 19 — How to Read Debug and Modify This Codebase Yourself

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Start with a question small enough to answer

**Code reading** is tracing a value and its decisions, not memorizing every file. Start with a concrete question: “Why was exactly five minutes rejected?”, “Why does Surprise Me refuse a return?”, or “Why did a saved plan reopen without routes?” Define acceptance criteria before changing anything. This project's [AGENTS.md](../../AGENTS.md) explicitly requires focused work, source inspection, preserved functionality, relevant tests and full diff review.

A useful path is: visible wording → component/event → client helper → Next route → Python endpoint → validator/orchestrator → pure algorithm → output adapter. [DATA_FLOW_REFERENCE.md](DATA_FLOW_REFERENCE.md) provides the cross-layer index. The file map lists actual symbols, so you can search a function instead of guessing a directory.

## Work a real boundary question

[components/location-controls.tsx](../../components/location-controls.tsx) contains this line in `prepareSurprise`:

```typescript
if(originInput.current?.requireOrigin){setNotice("This journey must return to a confirmed starting point. Choose current location or a manual starting place.");return null;}
```

Read the expression in pieces: `originInput.current` is retained preparation input; `?.` safely reads `requireOrigin` if input exists; the condition checks a mandatory confirmed start; `setNotice` explains the conflict; `return null` refuses to construct a surprise origin. Input is current preparation context, output is either refusal here or later valid configuration. The caller `generateOuting` handles the missing configuration by keeping source text and requesting a start. The backend router has a corresponding no-origin return check.

The line is dense but its behavior is simple. Reformat it in a personal note if helpful; do not change production formatting merely to learn it. This question is answered by tracing data ownership, not by removing the guard until cards appear.

## Read types before large functions

Start with `InterpretationInput`, `Journey`, `PlannerInput` and `AdvancedInput`. Identify required fields, nullable fields, defaults and excluded/private data. Then read the receiving function's early returns before the longest success block. Early exits often explain the owner's observed behavior: missing date, disabled gate, unresolved identity, stale session, known closure or admission pause.

A **call graph** records which function invokes which. An **invariant** is a fact that must remain true throughout an operation, such as each required occurrence being visited once or every real saved stop containing only allowed retained data. Search validators for these invariants before editing the algorithm. A **regression** is working behavior broken by a change; existing tests document many invariants worth preserving.

## A practical investigation loop

1. Record the symptom using safe message/code/status and current commit; never paste a private token or full origin payload.
2. Find the literal message with `rg -n` and inspect the surrounding condition.
3. Follow callers and input types; distinguish missing data from a known violation.
4. Find the closest fixture/test and understand what it proves and what it mocks.
5. If modification is needed, isolate it in a reviewed disposable worktree without secrets, write the smallest justified change, and run relevant offline checks.
6. Review the full diff, new files and unrelated state. Document actual outcomes and remaining uncertainty.

A **minimal reproduction** is the smallest safe input/fixture retaining the failure. For Hitech matching, fictional provider address components reproduced a spelling mismatch without rerunning the owner's failed Maps request. That proved a defect but did not establish the original incident's exact cause. This is good investigative precision.

## Change the right layer

Presentation wording usually belongs in components/formatters, not the Python ranking algorithm. A bad model extraction belongs at prompt/interpretation/source checks, not venue discovery. A missing Google route is provider evidence, not permission to replace it with a straight-line guess. A corrupted local ledger is an accounting failure, not permission to reset costs. A source hash refusal in historical evaluation is an identity boundary, not a test inconvenience.

Changing an ordering policy affects raw semantics, validators, admission, session creation, downstream topology and evaluation rubrics; it is not a one-line UI preference. The owner's V5 intent illustrates why a technically simple phrase can require a carefully versioned change. This course makes no such runtime modification.

## Learn by proposing a patch before applying one

For an early exercise, describe a change in prose: affected function, exact input/output difference, failure handling, invariants and test. Later use the [exercise isolation instructions](LEARNING_EXERCISES.md). Do not copy private `.env` profiles into a learning checkout. Do not open production gates, run paid evaluation scripts or start infrastructure as a lesson.

Use [DEBUGGING_PLAYBOOK.md](DEBUGGING_PLAYBOOK.md) to decide where to look and [DEVELOPMENT_COMMANDS.md](DEVELOPMENT_COMMANDS.md) to classify a command before running it. Ask for help with a bounded question and safe evidence: “At commit X this offline fixture reaches condition Y; I expected Z because of rule W.” That is enough to reason independently without pretending uncertainty has disappeared.

## Five key takeaways

1. Trace values across boundaries instead of reading randomly.
2. Types and early returns explain large functions.
3. Invariants define what a safe patch must preserve.
4. A fixture can prove a defect without proving an old incident cause.
5. Isolate later edits and keep private configuration out.

## Check your understanding

19.Q1. What is an invariant?
19.Q2. Why search literal error wording?
19.Q3. What makes a reproduction minimal?
19.Q4. Should a missing route become a guessed distance?
19.Q5. Which evidence helps a focused help request?

## Code-reading exercise — 19.R

Find the Surprise Me notice and follow requireOrigin back to generateOuting. Then locate the backend return-origin refusal.

## Practical exercise — 19.P

Write a hypothetical patch proposal to improve an error explanation. Specify affected file, acceptance criteria and one existing check; do not apply it.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-19).

[Previous chapter](18-cloud-hosting-deployment-and-scalability.md) · [Contents](README.md) · [Next chapter](20-complete-project-glossary-and-technical-reference.md)
