import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.date_resolution import resolve_datetime
from backend.models import PlanningRequest, RankingResult
from backend.ranking import recommend_plans
from backend.ai import AIError
from backend.interpretation import InterpretationInput, InterpretationResult, interpret_request

from backend.provider_budget import ProviderBudget, ProviderLimitError, local_real_enabled
from backend.real_planning import PlannerInput, real_plans
from backend.places import DiscoveryError
from backend.routes import RouteError, PlaceID
from backend.venue_details import details_sessions
from pydantic import BaseModel, Field

# One shared process budget across planning and on-demand contact requests.
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
def generate_plan(request: PlannerInput) -> RankingResult:
    if not isinstance(request, PlannerInput):
        request = PlannerInput.model_validate(request.model_dump())
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
    if provider_budget.settings.mode == "real":
        if not local_real_enabled():
            return JSONResponse(status_code=422, content={"code": "real_disabled", "message": "Real planning is disabled. Enable the local development switches or restart in mock mode."})
        try:
            return real_plans(request, provider_budget)
        except ValidationError:
            return JSONResponse(status_code=422, content={"code": "invalid_provider_data", "message": "Google returned incomplete or invalid venue or route information. No fictional fallback was used."})
        except (ProviderLimitError, DiscoveryError, RouteError) as error:
            return JSONResponse(status_code=422, content={"code": getattr(error, "code", "application_limit"), "message": str(error) + " No fictional fallback was used.", "diagnostics": getattr(error, "diagnostics", {})})
    if any(value is not None for value in (request.startingLocation, request.currentArea, request.searchRadius, request.maxFirstLegTravel)):
        return JSONResponse(status_code=422, content={"code": "unsupported_request", "message": "Starting-point travel and search-radius checks require deliberately enabled real mode. No fictional itinerary was generated with an ignored limit."})
    return recommend_plans(PlanningRequest.model_validate(request.model_dump(exclude={"searchRadius", "maxFirstLegTravel"})))


@app.post("/api/interpret", response_model=InterpretationResult)
def interpret_outing(request: InterpretationInput):
    try:
        return interpret_request(request)
    except (AIError, ValidationError, TimeoutError):
        return JSONResponse(status_code=503, content={
            "code": "ai_unavailable",
            "message": "AI interpretation unavailable, timed out, or returned invalid output. Check the local AI service and settings, then retry. No plan was generated.",
        })


@app.get("/api/planning-mode")
def planning_mode():
    return {"mode": provider_budget.settings.mode, "enabled": provider_budget.settings.mode == "mock" or local_real_enabled(),
            "contactDetailsEnabled": local_real_enabled() and os.environ.get("WHERETO_CONTACT_DETAILS_DEV") == "1"}


class ContactRequest(BaseModel):
    placeId: PlaceID
    token: str = Field(min_length=1, max_length=100)


@app.post("/api/venues/details")
def venue_details(request: ContactRequest):
    try:
        provider_budget.settings.require_live_provider()
        return JSONResponse(content=details_sessions.get(request.token, request.placeId), headers={"Cache-Control": "no-store"})
    except (ProviderLimitError, DiscoveryError) as error:
        return JSONResponse(status_code=422, content={"message": str(error)}, headers={"Cache-Control": "no-store"})
