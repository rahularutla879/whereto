# 05 — Backend Python FastAPI and Pydantic

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Three tools, three jobs

**Python** is the language containing the planner. **FastAPI** maps incoming HTTP requests to Python functions and serializes responses. **Pydantic** validates structured values and defines their schemas. A **schema** describes allowed fields, types, bounds and relationships. These tools let Where To? reject malformed requests before an expensive provider call.

[backend/main.py](../../backend/main.py) creates the application and registers endpoints. [models.py](../../backend/models.py) defines shared planning types; [interpretation.py](../../backend/interpretation.py) defines interpretation and clarification contracts; [real_planning.py](../../backend/real_planning.py) extends final requests with transient origin/search context. A **model** here means a Pydantic data contract; it does not always mean an AI model.

## Read the real final-request contract

From `backend/models.py`:

```python
class PlanningRequest(OutingRequest):
    """Public/final planning requires a date; partial candidate analysis may not."""
    date: OutingDate = Field(...)
    transport: Literal[TransportationMode.driving, TransportationMode.walking] = TransportationMode.driving
```

Line 1 creates a class inheriting fields and validators from `OutingRequest`; **inheritance** reuses a parent contract. Line 2 states why the stricter subtype exists. Line 3 requires a date: `...` means no default. Line 4 permits only driving or walking and defaults to driving. The input is a proposed dictionary or model instance; successful validation produces a typed request. Missing dates, unsupported modes and inconsistent inherited windows raise validation errors. This is stronger than the more general `OutingRequest`, whose date may be absent for partial analysis.

An additional validator in this class turns `None` transport into driving and rejects other modes. `OutingRequest.validate_activities` checks valid timezones, dinner indexes and end-after-start. Its activities field has one to four entries. The AI extraction can contain up to 32 source occurrences; advanced execution still supports at most four. Representation capacity and executable capacity are different limits.

## Strictness and extra fields

`ContractModel` supplies shared settings, and Journey models explicitly forbid unknown fields and nonfinite numbers. **Validation** checks shape and rules; **normalization** transforms an accepted value into a standard representation. They should not silently erase user intent. Strict integer fields reject unsuitable types instead of relying on convenient coercion.

`model_validate` reads proposed values into the contract. `model_dump(mode="json")` turns a model into JSON-compatible values, such as converting dates to strings. `model_copy(deep=True)` copies nested structures so later normalization need not mutate an original response. `Field(repr=False)` hides a field from ordinary object representations; it is not the same as excluding it from serialization. For private origins, `PlannerInput.startingLocation` also uses `exclude=True` so ordinary public dumping omits coordinates. This distinction matters to privacy.

## Endpoints and failure

FastAPI uses annotations such as `request: PlannerInput` to validate before entering `generate_endpoint`. Pydantic errors at the HTTP boundary become status 422, with sanitized issue fields. [main.invalid_request](../../backend/main.py) avoids echoing raw bodies. `generate_plan` then rechecks calendar validity and beginning requirements; a once-valid date can expire while someone edits the form.

Some endpoints are `async def`, others are ordinary `def`. Synchronous provider work is managed by [provider_work.run_work](../../backend/provider_work.py); do not conclude that all blocking work automatically becomes nonblocking because FastAPI supports asynchronous routes. **Uvicorn** is the server process that runs the FastAPI application; [dev_start.py](../../backend/dev_start.py) and the Node launcher control local startup.

The output of the ordinary planner is `RankingResult`: public request, confirmed/provisional plans, errors, notes and scoped continuation/save capabilities. The advanced output is `AdvancedResult`: status, questions, at most three options and an opaque session token. A **response model** documents and checks serialization shape, but a JSONResponse error can deliberately take a different error shape. Consult [API_REFERENCE.md](API_REFERENCE.md) rather than assuming all successful HTTP replies contain plans.

Python dependencies are pinned in [requirements.txt](../../backend/requirements.txt): for example FastAPI `0.150.0`, Pydantic `2.14.1` and psycopg `3.3.3`. These are repository declarations, not a new claim about upstream releases.

## Five key takeaways

1. FastAPI handles HTTP; Pydantic validates data.
2. A data model differs from an AI model.
3. Final requests require a date.
4. Hiding repr output is different from excluding serialized fields.
5. Validation failures should stop planning safely.

## Check your understanding

05.Q1. Why inherit OutingRequest?
05.Q2. What does Field(...) mean?
05.Q3. Can 32 extracted stops all execute?
05.Q4. Does repr=False remove a JSON field?
05.Q5. What status represents invalid structured request input?

## Code-reading exercise — 05.R

Compare OutingRequest, PlanningRequest and PlannerInput. Identify one field or rule added at each level.

## Practical exercise — 05.P

Use rg -n "class (OutingRequest|PlanningRequest|PlannerInput)" backend/models.py backend/real_planning.py. Do not submit a request.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-05).

[Previous chapter](04-frontend-react-next-js-typescript-and-tailwind.md) · [Contents](README.md) · [Next chapter](06-apis-http-json-and-frontend-backend-communication.md)
