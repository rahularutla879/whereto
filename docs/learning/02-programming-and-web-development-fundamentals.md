# 02 — Programming and Web Development Fundamentals

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Values become a program

A **program** is a set of instructions a computer executes. **Source code** is the human-readable form. Where To? uses TypeScript for browser/server interface code and Python for interpretation, planning and saving. A **runtime** executes a program: the browser executes delivered JavaScript, Node.js executes Next.js, and Python executes FastAPI. TypeScript adds development-time checks but ultimately runs as JavaScript.

A **variable** gives a value a name. A **string** holds text (`"Sydney"`), a **number** holds a quantity (`180`), a **boolean** holds true/false, a **list/array** holds ordered values, and an **object/dictionary** holds named fields. `null` in JSON and `None` in Python represent missing values; neither means zero. In this project a missing travel cap means no cap, while zero is a genuine hard limit.

A **function** receives inputs, performs work and returns an output. An **argument** is a supplied input. A **condition** selects a branch. A **loop** repeats work. A **class** groups a kind of data or behavior; a Pydantic model class describes allowed fields. A **module** is an importable file. These mechanisms let one project reuse its travel rules across generation, alternatives and saving instead of copying rules into every button.

## Follow a real helper

From [backend/planner.py](../../backend/planner.py), `supports_location`:

```python
def supports_location(location: str) -> bool:
    return re.fullmatch(r"baltimore(?:\s*,?\s*(?:md|maryland))?", location, re.IGNORECASE) is not None
```

Line 1 names the function, takes a string `location`, and declares a boolean result. Line 2 uses `re`, Python's regular-expression module, to match the **whole** string against the supported fictional destination. The pattern accepts Baltimore and optional Maryland/MD suffixes; `IGNORECASE` allows differing letter case. `is not None` converts “a match was found” into true. Input `"Baltimore, MD"` yields true; `"Sydney"` yields false. This is mock coverage validation, not a real geocoder. If a caller passes invalid input types, the public Pydantic boundary should reject them first; this helper itself is not a complete request validator.

A **regular expression** describes a bounded text pattern. It is useful for recognizing constrained wording, but it cannot establish that all natural-language meanings were understood. The larger [journey checks](../../backend/journey.py) use patterns for particular safety checks and still have documented gaps.

## The web introduces another computer

The **client** is the browser asking for work. A **server** answers requests. A **port** distinguishes services on one machine: the normal frontend uses 3000, FastAPI 8000 and Ollama 11434. `127.0.0.1` is the loopback address pointing at this same computer. A **URL**, Uniform Resource Locator, identifies a location such as `http://127.0.0.1:8000/health`. The path `/health` selects the operation.

**HTTP**, Hypertext Transfer Protocol, carries requests and responses. **HTTPS** adds encrypted transport. **JSON**, JavaScript Object Notation, is a common body format. An **API**, Application Programming Interface, is the agreed way one program asks another for work. None of these terms means artificial intelligence; AI is one service behind this application's API.

## Waiting without confusing ownership

**Asynchronous** code can wait for I/O—input/output such as a network response—without treating the waiting result as already available. JavaScript `await fetch(...)` waits for a response; Python `async def` declares a coroutine. A coroutine does not automatically make blocking Python computation parallel. [provider_work.py](../../backend/provider_work.py) manages worker ownership around synchronous planning, cancellation and admission.

**Concurrency** means work can overlap in time. It creates races: two clicks could both spend money unless a shared guard admits only allowed work. A **lock** makes a small critical operation exclusive. A **timeout** bounds how long to wait; it does not prove an external request was never sent. These ideas become concrete in chapter 14.

## Files, dependencies and configuration

A **dependency** is reusable software from another package. [package.json](../../package.json) declares JavaScript packages and commands; [backend/requirements.txt](../../backend/requirements.txt) pins Python packages. An **environment variable** supplies process configuration, for example the backend URL, without editing source. Secret values must stay outside Git and browser-delivered variables. Never learn configuration by printing every environment variable.

An **exception** signals failed work. Callers may catch it and convert it into a safe response. The owner should follow values from input to output and ask which layer catches failure, rather than assuming every function succeeds.

## Five key takeaways

1. Types describe kinds of values.
2. Missing and zero have different meanings.
3. Functions connect explicit inputs to outputs.
4. Clients and servers communicate over HTTP.
5. Waiting, concurrency and cancellation require separate reasoning.

## Check your understanding

02.Q1. How does None differ from zero here?
02.Q2. What executes TypeScript after transformation?
02.Q3. What does a port identify?
02.Q4. Does async mean unlimited parallel work?
02.Q5. What is a dependency?

## Code-reading exercise — 02.R

Read supports_location and _pools in backend/planner.py. Find where a false coverage result becomes a PlanningError.

## Practical exercise — 02.P

Use rg -n "def supports_location|unsupported_location" backend/planner.py. Explain the two matches aloud.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-02).

[Previous chapter](01-what-where-to-does-and-everything-built-so-far.md) · [Contents](README.md) · [Next chapter](03-overall-application-architecture.md)
