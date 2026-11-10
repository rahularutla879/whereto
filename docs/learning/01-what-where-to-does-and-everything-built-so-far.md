# 01 — What Where To Does and Everything Built So Far

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Begin with the product, then its evidence

Where To? turns a written outing request into a small set of venue itineraries. An **itinerary** is a sequence of visits and travel between them. The application interprets the words, checks what they mean, finds candidate venues, estimates travel, and shows options with uncertainty. It does not book a table, reserve a cricket court, purchase a movie ticket, or guarantee arrival.

A **repository** is the project's collection of source files and recorded history. This course was researched against tracked HEAD `a7ed1066fe3c082dd6e9b48dbfdfa58f53b610f8` on November 10, 2026. Ten pre-existing untracked Ordering V5 research files were initially present. Independent work committed that offline prototype as `b1efe96` during authoring; this course was reconciled to it. V5 remains outside active application behavior. Do not assume an offline research commit means runtime activation.

The project's implementation has grown in layers:

| Layer | What exists | What this does not establish |
|---|---|---|
| Browser interface | Mobile-oriented form, preferences, clarification, cards, directions, options and selected saving | A public deployed service |
| Local interpretation | Qwen3 4B through Ollama; strict Python validation and deterministic dates | Arbitrary-language correctness |
| Mock planning | Fictional Baltimore catalog, generation, scheduling, filtering and scoring | Real venues in Sydney or Hyderabad |
| Local real planning | Gated Google Places/Routes, confirmed origins, finite discovery and alternatives | Verified prices, tickets or reservations |
| Advanced local planning | Named identities, partial orders, optional stops, repeated occurrences, returns and duration checks | An exhaustive optimizer or universal ordering safety |
| Persistence | Restricted PostgreSQL access to private Supabase saved plans | User accounts, link revocation or live saved routes |
| Operations | Local admission, accounting, privacy-safe events, production startup refusal | Shared multi-server safety |
| Task 52 research | Cloud proposals, recorded evaluation, offline ordering policies and signed fictional protocol | A production-qualified cloud model |

The status table is grounded in [the runtime entry points](../../backend/main.py), [ordinary orchestration](../../backend/real_planning.py), [advanced orchestration](../../backend/advanced_planning.py), [saving](../../backend/saved_plans.py), and [the production guard](../../backend/admission.py). Task 51 is implemented locally; Task 52 remains in progress; Task 53 is outside this course's work. Older “Task 51 unstarted” notes in the root README describe previous checkpoints.

## Read a small real feature

From `backend/main.py`:

```python
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

Line 1 registers an HTTP (Hypertext Transfer Protocol) GET route: it tells FastAPI which function answers this address. Line 2 defines an asynchronous function called `health`, with a hint that its result maps strings to strings. Line 3 returns a Python dictionary; FastAPI serializes it into JSON (JavaScript Object Notation), a text format for exchanging structured values. There is no request body input and the output is `{"status":"ok"}`. If the backend cannot start, this function cannot answer. A successful health response says the process answers; it does not prove the model, Google, or saving works. This distinction prevents “the homepage loads” from becoming an unsupported claim that planning works.

## What counts as evidence?

**Implemented** means code exists on the relevant path. **Automated verification** means a named test exercised behavior under stated conditions. **Browser verification** means someone actually used the interface. **Live verification** means a real external service was contacted. These categories do not imply one another. This handbook uses source inspection and historical checked-in evidence; it does not report fresh browser, inference, Google, database, or deployment acceptance.

Start with [the file map](PROJECT_FILE_MAP.md). Keep [the glossary](GLOSSARY.md) beside you. Chapters 2–6 explain the vocabulary; chapter 7 follows requests; chapters 8–14 explain the mechanisms; chapters 15–20 teach investigation and safe change.

## Documentation disagreements to recognize

[CONSTRAINTS.md](../../CONSTRAINTS.md) retains early travel-scope and capacity language. Current ordinary inter-stop caps remain separate from first-leg limits; advanced whole-trip constraints include the confirmed return. Party size is no longer an active planning filter. Read the dated superseding sections and the code, rather than applying an old paragraph globally. [Verification notes](VERIFICATION.md) collect these discrepancies and evidence limits.

## Five key takeaways

1. An itinerary is a proposed outing, not a booking.
2. Mock and real planning have different evidence.
3. Advanced planning is a separate gated path.
4. Local implementation is not public deployment.
5. Source, tests, browser use and live calls establish different facts.

## Check your understanding

01.Q1. What does an itinerary contain?
01.Q2. Why can a healthy backend still fail to plan?
01.Q3. Can the mock catalog prove a Sydney plan exists?
01.Q4. Is an offline ordering policy active production enforcement?
01.Q5. Which task remains outside this work?

## Code-reading exercise — 01.R

Open backend/main.py and locate health and generate_plan. List two dependencies used only by planning.

## Practical exercise — 01.P

Run pwd, git status --short, and git log -3 --oneline from the repository. Do not edit anything.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-01).

[Learning path](README.md) · [Contents](README.md) · [Next chapter](02-programming-and-web-development-fundamentals.md)
