from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.models import PlanningRequest, RankingResult
from backend.ranking import recommend_plans
from backend.ai import AIError
from backend.interpretation import InterpretationInput, InterpretationResult, interpret_request

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
