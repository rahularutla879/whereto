from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.date_resolution import resolve_datetime
from backend.models import PlanningRequest, RankingResult
from backend.ranking import recommend_plans
from backend.ai import AIError
from backend.interpretation import InterpretationInput, InterpretationResult, interpret_request

from backend.provider_budget import ProviderBudget

# One process-wide session for future venue/travel adapters; mock pipeline is unchanged.
provider_budget = ProviderBudget()

app = FastAPI(title="Where To? backend")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Do not echo arbitrary request bodies or raw exception internals.
    issues = [{"field": ".".join(str(part) for part in e["loc"] if part != "body"),
               "message": e["msg"]} for e in exc.errors()]
    unsupported = any(e["type"] == "enum" and "activities" in e["loc"] for e in exc.errors())
    return JSONResponse(status_code=422, content={
        "code": "unsupported_request" if unsupported else "invalid_request",
        "message": ("An activity is unsupported; choose from the supported activities. No partial plan was created."
                    if unsupported else "Invalid outing request. Check activities, date, group size and limits."),
        "issues": issues,
    })


@app.post("/api/plans/generate", response_model=RankingResult)
def generate_plan(request: PlanningRequest) -> RankingResult:
    # Recheck the calendar at publication too: a validated browser request may
    # have waited across midnight or a selected start before being submitted.
    start = f"{request.startTime // 60:02d}:{request.startTime % 60:02d}"
    end = "midnight" if request.endTime == 1440 else f"{request.endTime // 60:02d}:{request.endTime % 60:02d}"
    calendar = resolve_datetime("", [], [f"from {start} to {end}"], request.location,
                                manual_date=request.date.isoformat())
    if calendar.issues:
        return JSONResponse(status_code=422, content={
            "code": "invalid_request",
            "message": "The outing date or time window is no longer valid. Choose a future date and a valid same-day time window, then retry. No plan was generated.",
        })
    return recommend_plans(request)


@app.post("/api/interpret", response_model=InterpretationResult)
def interpret_outing(request: InterpretationInput):
    try:
        return interpret_request(request)
    except (AIError, ValidationError, TimeoutError):
        return JSONResponse(status_code=503, content={
            "code": "ai_unavailable",
            "message": "AI interpretation unavailable, timed out, or returned invalid output. Check the local AI service and settings, then retry. No plan was generated.",
        })
