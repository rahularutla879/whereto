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


@app.middleware("http")
async def exploration_local_only(request: Request, call_next):
    # Capability/session tokens still apply. Reject public hosts, proxy forwarding
    # and cross-origin callers even if a development process is misbound.
    if provider_budget.settings.exploration:
        from urllib.parse import urlparse
        local = {"localhost", "127.0.0.1", "::1", "testserver"}
        origin = request.headers.get("origin")
        proxy_host = request.headers.get("x-whereto-client-host")
        proxy_origin = request.headers.get("x-whereto-client-origin")
        try:
            proxy_local = not proxy_host or urlparse("http://" + proxy_host).hostname in local
            proxy_origin_local = not proxy_origin or urlparse(proxy_origin).hostname in local
        except ValueError:
            proxy_local = proxy_origin_local = False
        if (not proxy_local or not proxy_origin_local or request.headers.get("x-whereto-proxied") == "1"
                or request.url.hostname not in local or not request.client or request.client.host not in local
                or any(k in request.headers for k in ("x-forwarded-for", "forwarded", "x-forwarded-host"))
                or (origin and urlparse(origin).hostname not in local)):
            return JSONResponse(status_code=403, content={"message":"Development exploration accepts local requests only."})
    return await call_next(request)


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
    from backend.surprise import validate_beginning
    try:validate_beginning(request)
    except DiscoveryError as error:return JSONResponse(status_code=422,content={"code":error.code,"message":str(error)})
    if provider_budget.settings.mode == "real":
        if not local_real_enabled():
            return JSONResponse(status_code=422, content={"code": "real_disabled", "message": "Real planning is disabled. Enable the local development switches or restart in mock mode."})
        try:
            return real_plans(request, provider_budget)
        except ValidationError:
            return JSONResponse(status_code=422, content={"code": "invalid_provider_data", "message": "Google returned incomplete or invalid venue or route information. No fictional fallback was used."})
        except (ProviderLimitError, DiscoveryError, RouteError) as error:
            return JSONResponse(status_code=422, content={"code": getattr(error, "code", "application_limit"), "message": str(error) + " No fictional fallback was used.", "diagnostics": getattr(error, "diagnostics", {})})
    if request.requireWheelchairAccess:
        return JSONResponse(status_code=422,content={"code":"unsupported_request","message":"Mock venues cannot verify required wheelchair access. No fictional accessibility claim was made."})
    if request.geography.strictDestination or request.geography.excludedRegions:
        return JSONResponse(status_code=422,content={"code":"unsupported_request","message":"Geographic boundary and regional exclusion checks require deliberately enabled real mode. No fictional itinerary was generated with an ignored constraint."})
    if any(value is not None for value in (request.searchRadius, request.manualStartingPlace)):
        return JSONResponse(status_code=422, content={"code": "unsupported_request", "message": "Starting-point travel and search-radius checks require deliberately enabled real mode. No fictional itinerary was generated with an ignored limit."})
    if request.startingLocation and request.startingLocation.source!='mock' and (request.firstTravel or request.maxFirstLegTravel is not None):
        return JSONResponse(status_code=422,content={'code':'unsupported_request','message':'Mock venues cannot verify travel from real coordinates. Choose a clearly fictional mock reference or use deliberately enabled real mode.'})
    from backend.mock_origin import apply_mock_origin
    if request.betweenTravel and request.betweenTravel.unit=='miles':
        return JSONResponse(status_code=422,content={'code':'unsupported_request','message':'Mock travel has no road-mile evidence. Choose between-activity minutes or deliberately enabled real mode.'})
    if request.planningMode=='surprise':
        from backend.mock_surprise import mock_surprise
        return mock_surprise(request)
    return apply_mock_origin(recommend_plans(PlanningRequest.model_validate(request.model_dump(exclude={"searchRadius", "maxFirstLegTravel", "locationFirst"}))),request)


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
            "explorationEnabled": provider_budget.settings.exploration,
            "startingLookupEnabled": local_real_enabled() and os.environ.get("WHERETO_START_LOOKUP_DEV") == "1",
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
        return JSONResponse(status_code=422, content={"message": str(error),"diagnostics":getattr(error,"diagnostics",{})}, headers={"Cache-Control": "no-store"})


class OptionsRequest(BaseModel):
    expandDiscovery: bool = Field(default=False, strict=True)
    token: str = Field(min_length=1, max_length=100)


def more_options(request: OptionsRequest):
    from backend.real_planning import more_real_plans
    try:
        if provider_budget.settings.mode=='mock':
            from backend.mock_surprise import more_mock_surprise
            return JSONResponse(content=more_mock_surprise(request.token).model_dump(mode="json"),headers={"Cache-Control":"no-store"})
        provider_budget.settings.require_live_provider()
        return JSONResponse(content=more_real_plans(request.token, expand_discovery=request.expandDiscovery).model_dump(mode="json"), headers={"Cache-Control": "no-store"})
    except (ProviderLimitError, DiscoveryError, RouteError, ValidationError) as error:
        message = "Provider data could not be verified." if isinstance(error, ValidationError) else str(error)
        return JSONResponse(status_code=422, content={"message": message + " No fictional fallback was used.","diagnostics":getattr(error,"diagnostics",{})}, headers={"Cache-Control": "no-store"})


from backend.starting_places import StartingPlaceQuery, lookup_starting_places


@app.post("/api/starting-places")
def starting_places(request: StartingPlaceQuery):
    try:
        return JSONResponse(content=lookup_starting_places(request, provider_budget), headers={"Cache-Control": "no-store"})
    except (ProviderLimitError, DiscoveryError) as error:
        return JSONResponse(status_code=422, content={"message": str(error),"diagnostics":getattr(error,"diagnostics",{})}, headers={"Cache-Control": "no-store"})


from backend.starting_areas import StartingAreaQuery, suggest_starting_areas


@app.post('/api/starting-areas')
def starting_areas(request: StartingAreaQuery):
    try:
        return JSONResponse(content=suggest_starting_areas(request,provider_budget),headers={'Cache-Control':'no-store'})
    except (ProviderLimitError, DiscoveryError, RouteError, ValidationError) as error:
        return JSONResponse(status_code=422,content={'message':'Starting-area information could not be verified.' if isinstance(error,ValidationError) else str(error),'diagnostics':getattr(error,'diagnostics',{})},headers={'Cache-Control':'no-store'})


@app.post("/api/plans/generate", response_model=RankingResult)
async def generate_endpoint(request: PlannerInput, http: Request):
    from backend.provider_work import run_work
    return await run_work(http, lambda: generate_plan(request))


@app.post("/api/plans/options")
async def options_endpoint(request: OptionsRequest, http: Request):
    from backend.provider_work import run_work
    return await run_work(http, lambda: more_options(request))
