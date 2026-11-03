import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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

from backend.failures import MESSAGES, evidence, provider_code

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    from backend.ai_readiness import start
    start() # Daemon preparation does not block health or require Google/SQL.
    yield

app = FastAPI(title="Where To? backend",lifespan=lifespan)


@app.middleware('http')
async def local_request_timing(request: Request, call_next):
    from time import perf_counter
    started=perf_counter()
    response=await call_next(request)
    if local_real_enabled() and os.environ.get('WHERETO_DIAGNOSTICS_DEV')=='1':
        response.headers['Server-Timing']=f'backend;dur={(perf_counter()-started)*1000:.3f}'
    return response


def failure(code, status=503, operation='planning', *, message=None, diagnostics=None, error=None):
    reference = evidence(code, operation, exception=error)
    return JSONResponse(status_code=status, content={
        'code': code, 'message': MESSAGES.get(code, message or 'This operation could not be completed.'),
        'correlationId': reference, 'diagnostics': diagnostics or {},
    }, headers={'Cache-Control':'no-store', 'X-Correlation-ID':reference})


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
            return failure("local_request_required",403,operation="development_boundary")
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
    if request.url.path == '/api/plans/advanced':
        return failure('invalid_request',422,operation='advanced_validation',message='Check the advanced answer format. Your request and current itinerary are kept.')
    if request.url.path in {"/api/plans/save", "/api/plans/reopen", "/api/plans/refresh", "/api/development-diagnostics", "/api/plans/advanced"}:
        return failure("save_validation_failed",422,operation="persistence_validation")
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
    from backend.location_context import outing_problem
    problem=outing_problem(request)
    if problem:
        return JSONResponse(status_code=422,content={"code":problem[0],"message":problem[1]})
    from backend.surprise import validate_beginning
    try:validate_beginning(request)
    except DiscoveryError as error:return JSONResponse(status_code=422,content={"code":error.code,"message":str(error)})
    if provider_budget.settings.mode == "real":
        if not local_real_enabled():
            return JSONResponse(status_code=422, content={"code": "real_disabled", "message": "Real planning is disabled. Enable the local development switches or restart in mock mode."})
        try:
            return real_plans(request, provider_budget)
        except ValidationError as error:
            return failure('internal_application_error',500,operation='planning_model',error=error)
        except (ProviderLimitError, DiscoveryError, RouteError) as error:
            return failure(provider_code(error),422,operation="venue_or_route",message=str(error),diagnostics=getattr(error,"diagnostics",{}),error=error)
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
        result = interpret_request(request)
        from backend.advanced_planning import sessions
        result.advancedToken = sessions.create(request.text, result, provider_budget, request.preferences)
        return result
    except (AIError, ValidationError, TimeoutError):
        return failure('llm_interpretation_failed',503,operation='interpretation')


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
    showBeyond: bool = Field(default=False, strict=True)
    expandDiscovery: bool = Field(default=False, strict=True)
    token: str = Field(min_length=1, max_length=100)


def more_options(request: OptionsRequest):
    from backend.real_planning import more_real_plans
    try:
        if provider_budget.settings.mode=='mock':
            from backend.mock_surprise import more_mock_surprise
            return JSONResponse(content=receipts.issue(more_mock_surprise(request.token)).model_dump(mode="json"),headers={"Cache-Control":"no-store"})
        provider_budget.settings.require_live_provider()
        return JSONResponse(content=receipts.issue(more_real_plans(request.token, expand_discovery=request.expandDiscovery, show_beyond=request.showBeyond)).model_dump(mode="json"), headers={"Cache-Control": "no-store"})
    except (ProviderLimitError, DiscoveryError, RouteError, ValidationError) as error:
        message = "Provider data could not be verified." if isinstance(error, ValidationError) else str(error)
        return JSONResponse(status_code=422, content={"code":getattr(error,"code","invalid_provider_data"),"message": message + " No fictional fallback was used.","diagnostics":getattr(error,"diagnostics",{}),"continuation":getattr(error,"continuation",{ "canExpand":False,"canDiscover":False } if getattr(error,"code",None) in ("expired","stopped","mode_changed") else None)}, headers={"Cache-Control": "no-store"})


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
    def generate():
        result=generate_plan(request)
        from backend.development_diagnostics import record
        record(result)
        return receipts.issue(result)
    return await run_work(http,generate)


@app.post("/api/plans/options")
async def options_endpoint(request: OptionsRequest, http: Request):
    from backend.provider_work import run_work
    def options():
        result=more_options(request)
        from backend.development_diagnostics import record
        record(result)
        return result
    return await run_work(http,options)


from backend.saved_plans import SaveRequest, OpenRequest, PersistenceError, receipts, save, reopen


@app.middleware("http")
async def private_plan_boundary(request: Request, call_next):
    if request.url.path in {"/api/plans/save", "/api/plans/reopen", "/api/plans/refresh", "/api/development-diagnostics", "/api/plans/advanced"}:
        from urllib.parse import urlparse
        local = {"localhost", "127.0.0.1", "::1", "testserver"}
        # Local-development MVP only; no cross-origin browser or forwarded public traffic.
        try:
            valid = request.url.hostname in local and request.client and request.client.host in local
            for header in ("origin", "x-whereto-client-origin"):
                value = request.headers.get(header)
                valid = valid and (not value or urlparse(value).hostname in local)
            host = request.headers.get("x-whereto-client-host")
            valid = valid and (not host or urlparse("http://" + host).hostname in local)
        except ValueError:
            valid = False
        if not valid or request.headers.get("x-whereto-proxied") == "1" or request.headers.get("sec-fetch-site") == "cross-site" or any(h in request.headers for h in ("forwarded", "x-forwarded-for", "x-forwarded-host")):
            return JSONResponse(status_code=403, content={"message": "Private plans accept local requests only."}, headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"})
        # Stream bound applies even without Content-Length or with a dishonest header.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return JSONResponse(status_code=413, content={"message": "Save request is too large."}, headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer"})
        if request.method == 'POST':
            import json
            def unique_object(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('Duplicate JSON key')
                    result[key] = value
                return result
            def invalid_constant(value):
                raise ValueError('Nonfinite JSON value')
            try:
                payload = json.loads(bytes(body), object_pairs_hook=unique_object, parse_constant=invalid_constant)
                if not isinstance(payload, dict):
                    raise ValueError('Expected object')
            except (ValueError, UnicodeError, RecursionError):
                response = failure('save_validation_failed',422,operation='persistence_json')
                response.headers['Referrer-Policy'] = 'no-referrer'
                return response
        request._body = bytes(body)
    response = await call_next(request)
    if request.url.path in {"/api/plans/save", "/api/plans/reopen", "/api/plans/refresh", "/api/development-diagnostics", "/api/plans/advanced"}:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response


def persistence_response(operation, request):
    try:
        return JSONResponse(content=operation(request), headers={"Cache-Control": "no-store"})
    except ValidationError:
        return failure('save_validation_failed',422,operation='save_validation')
    except PersistenceError as error:
        return failure(error.code,error.status,operation='save' if operation is save else 'reopen',error=error)


@app.post("/api/plans/save")
def save_endpoint(request: SaveRequest):
    return persistence_response(save, request)


@app.post("/api/plans/reopen")
def reopen_endpoint(request: OpenRequest):
    def with_policy(value):
        from backend.saved_refresh import automatic_details_enabled, saved_hours_enabled
        return {**reopen(value), 'automaticVenueDetails': automatic_details_enabled(), 'hoursRefreshAvailable': saved_hours_enabled()}
    return persistence_response(with_policy, request)


@app.middleware('http')
async def safe_application_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as error:
        return failure('internal_application_error',500,operation='http',error=error)


from backend.saved_refresh import RefreshRequest, refresh_sessions

@app.post('/api/plans/refresh')
def refresh_saved_plan(request: RefreshRequest):
    try:
        return JSONResponse(content=refresh_sessions.refresh(request,provider_budget),headers={'Cache-Control':'no-store'})
    except PersistenceError as error:
        return failure(error.code,error.status,operation='saved_refresh')
    except (DiscoveryError,ProviderLimitError) as error:
        return failure('venue_refresh_disabled' if getattr(error,'code',None)=='disabled' else provider_code(error),422,operation='saved_refresh',error=error)


@app.get('/api/development-diagnostics')
def development_diagnostics():
    if not local_real_enabled() or os.environ.get('WHERETO_DIAGNOSTICS_DEV')!='1':
        return JSONResponse(status_code=404,content={},headers={'Cache-Control':'no-store'})
    from backend.development_diagnostics import snapshot
    from backend.performance import snapshot as ai_timings, provider_snapshot
    from backend.ai_readiness import snapshot as readiness
    return JSONResponse(content={'dataMode':os.environ.get('VENUE_DATA_MODE','mock'),**snapshot(),'localAiTiming':ai_timings(),'providerStageTiming':provider_snapshot(),'localAiReadiness':readiness(),'advanced':advanced_sessions.diagnostics()},headers={'Cache-Control':'no-store'})


from backend.advanced_planning import AdvancedInput, AdvancedAnswerError, sessions as advanced_sessions

@app.post('/api/plans/advanced')
async def advanced_endpoint(value: AdvancedInput, http: Request):
    from backend.provider_work import run_work
    def execute():
        try:
            return JSONResponse(content=advanced_sessions.run(value).model_dump(mode='json'), headers={'Cache-Control':'no-store'})
        except AdvancedAnswerError as error:
            return failure(error.code,422,operation='advanced',message=str(error))
        except ValueError:
            return failure('advanced_answer_invalid',422,operation='advanced',message='This answer cannot be applied to the current outing. Check the requested field; your text and itinerary are kept.')
        except (DiscoveryError, ProviderLimitError, RouteError) as error:
            return failure(provider_code(error),422,operation='advanced',error=error)
    return await run_work(http,execute)
