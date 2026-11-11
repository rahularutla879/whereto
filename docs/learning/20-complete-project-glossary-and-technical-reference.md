# 20 — Complete Project Glossary and Technical Reference

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## A reference is a map back to evidence

A **technical reference** is organized for lookup rather than continuous reading. A **glossary** defines vocabulary consistently. Developers use them so terms such as “session,” “token,” “model” and “verified” do not change meaning between interface, backend and evaluation. Where To? needs explicit distinctions because the same ordinary word can name several very different mechanisms.

The comprehensive alphabetical reference is [GLOSSARY.md](GLOSSARY.md). The other durable lookup tools are [PROJECT_FILE_MAP.md](PROJECT_FILE_MAP.md), [API_REFERENCE.md](API_REFERENCE.md), [DATA_FLOW_REFERENCE.md](DATA_FLOW_REFERENCE.md), [DEBUGGING_PLAYBOOK.md](DEBUGGING_PLAYBOOK.md), [DEVELOPMENT_COMMANDS.md](DEVELOPMENT_COMMANDS.md), [LEARNING_EXERCISES.md](LEARNING_EXERCISES.md) and [EXERCISE_SOLUTIONS.md](EXERCISE_SOLUTIONS.md). Each serves a different input question; none replaces source when behavior changes.

## Four words that deserve special care

**Model:** `Interpretation` is a Pydantic data model; `qwen3:4b` is an AI model; `model_version` in saved data identifies the saved document representation. Changing one does not automatically update the others.

**Token:** a language-model token is a unit of text processing; an OAuth token authenticates service access; an options/advanced token selects scoped transient context; a saved access token grants bearer read access. These have different issuers, expiries and powers. A **receipt** is also purpose-specific: save membership is not new semantic or spending authority.

**Session:** browser submission ownership, a backend outing continuation, a psycopg database connection/session, and a proposed anonymous cloud session are different. Specify which one failed before applying a fix. Backend session expiry is not an expired outing date.

**Verified:** venue identity, source quote membership, current route observation, timing feasibility and independent model qualification are different evidence claims. `DataStatus.verified` on identity does not verify prices, opening hours, session availability or every extracted relationship.

## Read a real evidence type

From [backend/models.py](../../backend/models.py), inside `DataQuality`:

```python
identity: DataStatus = DataStatus.unknown
price: DataStatus = DataStatus.unknown
capacity: DataStatus = DataStatus.unknown
```

Line 1 defaults identity evidence to unknown. Line 2 independently defaults price evidence. Line 3 independently defaults capacity evidence. These are class field declarations, not a complete executable program. Input is per-field producer evidence; output is a typed status record with conservative defaults. A missing value remains missing even if a producer supplies a misleading status; downstream validators/evaluators still decide usefulness. Real venue construction can verify identity while retaining unknown pricing/duration. Fictional fixtures must use fictional labels rather than borrow real verification.

## Contract and scope lookup

| Question | Start here | Follow to |
|---|---|---|
| What words did the model extract? | `Interpretation` | `OllamaProvider`, `parse_interpretation` |
| What user constraints were accepted? | `InterpretationResult.request/context` | `interpret_request`, `validate_journey` |
| How did a proved edge survive legacy normalization in development? | `validate_for_development` | Compare its raw snapshot, legacy snapshot and final result. [Adapter](../../scripts/task52_ordering_preservation_dev.py) |
| What does stop 2 mean? | `Journey.stops[2]` | Source ownership and occurrence constraints |
| Why did a plan fail? | Constraint issues / advanced reasons | Ranking or timing evaluator |
| Which route was measured? | RouteLeg | Directed endpoints, mode and observation time |
| Why is a continuation refused? | Options/advanced token state | Expiry, lock, evidence and allowance |
| What was saved? | SavedDocument and migrations | safe_document / saved_advanced |
| Can evaluation resume? | Frozen build/source and journal authority | Q1–Q4C review gates, not budget alone |

## Units and representations

A minute-after-midnight integer represents a local clock position: 1020 is 17:00. Duration seconds represent elapsed time; they cannot be added to a local clock across daylight saving changes without an appropriate timezone conversion. Meters describe route distance; miles conversion uses 1609.344 meters per mile. Money caps and microdollar/nanodollar accounting are different scales, so always write units.

`null`, absent, empty array and zero must be read in context: unknown windows, known closed windows, no numeric cap and a zero hard cap have different behavior. A boolean flag is not evidence a service exists. A hash binds bytes; a signature authenticates bytes under trusted keys; independent review evaluates meaning. One does not replace another.

## Keeping the course accurate

The handbook began from the a7ed106 and b1efe96 checkpoints. The standing development rule requires checking affected contracts, callers, failure handling, tests and historical claims when implementation changes. Preserve the chapter structure and earlier evaluation evidence, verify links and examples, and record which chapters changed. [Development rules](../../AGENTS.md) · [Original verification snapshot](VERIFICATION.md)

After chapter 20, repeat the chapter 7 traces using source searches alone, then explain the chapter 10 worked examples without looking at their answers. The goal is the ability to identify what you know, what the code checks, and what evidence is still missing before making a safe change.

## Five key takeaways

1. References support lookup and must stay tied to source.
2. Model, token, session and verified have multiple meanings.
3. Evidence is field-specific.
4. Units and missing-value semantics affect correctness.
5. Updating a lesson must not rewrite historical evaluation evidence.

## Check your understanding

20.Q1. Name two meanings of model.
20.Q2. Does verified identity verify price?
20.Q3. Is a hash equivalent to a signature?
20.Q4. What does 1020 represent in ordinary schedules?
20.Q5. What should happen to old outputs after a policy change?

## Code-reading exercise — 20.R

Compare DataQuality fields with the real Venue construction in real_planning.py. Identify which values remain unknown.

## Practical exercise — 20.P

Choose ten glossary terms and explain each using a different repository file. Check your explanations against the reference.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-20).

[Previous chapter](19-how-to-read-debug-and-modify-this-codebase-yourself.md) · [Contents](README.md) · [Reference index](README.md)
