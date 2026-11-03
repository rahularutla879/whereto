"""Explicit, bounded, identifier-only persistence. Never calls a provider."""
from collections import OrderedDict
from contextlib import contextmanager
from hashlib import sha256
import os
import re
import secrets
from threading import Lock, BoundedSemaphore
from time import monotonic
from typing import Annotated, Literal
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import Field, model_validator

from backend.database_check import DatabaseCheckError
from backend.persistence_config import runtime_settings as connection_settings
from backend.failures import MESSAGES
from backend.models import ContractModel, OutingRequest, RankingResult

Token = Annotated[str, Field(strict=True, min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')]
CandidateID = Annotated[str, Field(min_length=1, max_length=200)]


class SaveRequest(ContractModel):
    receipt: Token = Field(repr=False)
    accessToken: Token = Field(repr=False)
    candidateIds: list[CandidateID] = Field(min_length=1, max_length=3)
    selectedId: CandidateID


class OpenRequest(ContractModel):
    accessToken: Token = Field(repr=False)


class FictionalFacts(ContractModel):
    name: str = Field(min_length=1, max_length=300)
    neighborhood: str | None = Field(max_length=300)
    price: float | None = Field(ge=0)


class SavedStop(ContractModel):
    position: int = Field(ge=0, le=3)
    activity: str = Field(min_length=1, max_length=107)
    provider: Literal['mock', 'google_places']
    reference: str = Field(min_length=1, max_length=200)
    timingBasis: Literal['unknown', 'fictional']
    start: int | None = Field(ge=0, le=1439)
    end: int | None = Field(ge=1, le=1440)
    duration: int | None = Field(ge=1, le=1440)
    fictional: FictionalFacts | None = None


    @model_validator(mode='after')
    def valid_reference(self):
        if self.provider == 'google_places' and not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', self.reference):
            raise ValueError('Invalid provider reference')
        if not self.reference.strip() or any(ord(c) < 32 for c in self.reference):
            raise ValueError('Invalid venue reference')
        return self


class FictionalMetrics(ContractModel):
    totalTravel: int | None = Field(ge=0, le=1440)
    legs: list[int | None] = Field(max_length=3)


from backend.saved_advanced import AdvancedSaved


class SavedOption(ContractModel):
    advanced: AdvancedSaved | None = None
    candidateId: CandidateID
    stops: list[SavedStop] = Field(min_length=1, max_length=4)
    fictionalMetrics: FictionalMetrics | None = None


class SavedDocument(ContractModel):
    version: Literal[1, 2] = 1
    dataMode: Literal['mock', 'real']
    constraints: OutingRequest
    selectedId: CandidateID
    itineraries: list[SavedOption] = Field(min_length=1, max_length=3)


    @model_validator(mode='after')
    def complete_structure(self):
        ids = [option.candidateId for option in self.itineraries]
        if len(self.constraints.location) > 200 or self.constraints.destinationContext is not None:
            raise ValueError('Invalid retained constraints')
        if self.constraints.date is None or self.selectedId not in ids or len(set(ids)) != len(ids):
            raise ValueError('Incomplete saved selection')
        for option in self.itineraries:
            if (self.version == 2) != (option.advanced is not None) or self.version == 2 and self.dataMode != 'real':
                raise ValueError('Advanced document version mismatch')
            order = option.advanced.occurrenceOrder if option.advanced else list(range(len(self.constraints.activities)))
            if option.advanced and len(option.advanced.journey.stops) != len(self.constraints.activities):
                raise ValueError('Original occurrences changed')
            if [s.activity for s in option.stops] != [self.constraints.activities[i].value for i in order]:
                raise ValueError('Saved activities must match constraints')
            if [s.position for s in option.stops] != list(range(len(option.stops))):
                raise ValueError('Saved stops must preserve order')
            if self.dataMode == 'real' and (option.fictionalMetrics or any(
                    s.provider != 'google_places' or s.fictional or s.timingBasis != 'unknown'
                    or any(t is not None for t in (s.start,s.end,s.duration)) for s in option.stops)):
                raise ValueError('Real provider content must not be retained')
            if self.dataMode == 'mock' and any(s.provider != 'mock' or s.fictional is None for s in option.stops):
                raise ValueError('Mock source mismatch')
        return self


class PersistenceError(Exception):
    def __init__(self, status=503, code=None):
        self.status = status
        self.code = code or ('saved_link_unavailable' if status==404 else 'save_reference_expired' if status==409 else 'database_connection_failed')
        super().__init__(MESSAGES[self.code])


# These fields are normalized into named columns; no request/response blob.
COLUMNS = {
    'date': 'outing_date', 'calendarTimezone': 'calendar_timezone', 'location': 'location_text',
    'activities': 'activities', 'activityIntents': 'activity_intents', 'startTime': 'start_minute',
    'endTime': 'end_minute', 'explicitStart': 'explicit_start', 'explicitEnd': 'explicit_end',
    'transport': 'transport', 'planningMode': 'planning_mode', 'maxFirstLegTravel': 'max_first_leg_minutes',
    'maxFirstLegTravelExclusive': 'max_first_leg_exclusive', 'maxLegTravel': 'max_leg_minutes',
    'maxLegTravelExclusive': 'max_leg_exclusive', 'travel': 'inter_stop_minutes',
    'travelExclusive': 'inter_stop_exclusive', 'requireWheelchairAccess': 'require_wheelchair_access',
    'requireAvailability': 'require_availability', 'allowRevisits': 'allow_revisits',
    'dinner': 'dinner', 'dinnerStops': 'dinner_stops',
}
PREFERENCES = ('people', 'budget', 'groupBudget', 'cost')


def safe_document(result: RankingResult):
    """Only server-generated results enter this function, never client snapshots."""
    request = {k:v for k,v in result.request.model_dump(mode='json').items() if k in OutingRequest.model_fields}
    # Geographic verification and exact/device/provider origins are transient.
    request['transport'] = request.get('transport') or 'driving'
    request['destinationContext'] = None
    if len(request['location']) > 200 or sum(len(v) for v in request['activityIntents'].values()) > 2000:
        return None
    options = []
    for plan in result.plans + result.provisionalPlans + result.explorationPlans + [p for b in result.alternativeBatches for p in b]:
        stops = []
        for i, stop in enumerate(plan.stops):
            real = result.dataMode == 'real'
            reference = stop.venue.providerPlaceId if real else stop.venue.id
            if not reference or (not real and stop.venue.providerPlaceId):
                return None
            stops.append(SavedStop(position=i, activity=stop.venue.activity.value,
                provider='google_places' if real else 'mock', reference=reference,
                timingBasis='unknown' if real else 'fictional',
                start=None if real else stop.start, end=None if real else stop.end,
                duration=None if real else stop.duration,
                fictional=None if real else FictionalFacts(name=stop.venue.name,
                    neighborhood=stop.venue.neighborhood, price=stop.venue.price)))
        # Candidate hashes are app-owned; never store ranking/verification or Google metrics.
        options.append(SavedOption(candidateId=plan.candidate.id, stops=stops,
            fictionalMetrics=None if result.dataMode == 'real' else FictionalMetrics(
                totalTravel=plan.totalTravel, legs=[q.minutes for q in plan.legs])))
    return {'dataMode': result.dataMode, 'constraints': request, 'options': options} if options else None


class Receipts:
    """At most 100 minimized results, ten minutes, process-local and locked."""
    def __init__(self):
        self.items = OrderedDict()
        self.lock = Lock()

    def issue(self, result):
        if not isinstance(result, RankingResult):
            return result
        try:
            safe = safe_document(result)
        except ValueError:
            return result
        if safe is None:
            return result
        token = secrets.token_urlsafe(32)
        access = secrets.token_urlsafe(32)
        safe['bound'] = digest(access)
        with self.lock:
            now = monotonic()
            self.items = OrderedDict((k, v) for k, v in self.items.items() if v[0] > now)
            self.items[token] = (now + 600, safe)
            while len(self.items) > 100:
                self.items.popitem(last=False)
        return result.model_copy(update={'saveReceipt': token, 'saveAccessToken': access})

    def select(self, request):
        with self.lock:
            item = self.items.get(request.receipt)
            if not item or item[0] <= monotonic():
                raise PersistenceError(409)
            safe = item[1]
            bound = safe.get('bound')
            if not bound or not secrets.compare_digest(bound, digest(request.accessToken)):
                raise PersistenceError(409)
            ids = request.candidateIds
            if len(set(ids)) != len(ids) or request.selectedId not in ids:
                raise PersistenceError(409)
            by_id = {p.candidateId: p for p in safe['options']}
            if any(i not in by_id for i in ids):
                raise PersistenceError(409)
            return SavedDocument(version=safe.get('version',1), dataMode=safe['dataMode'], constraints=safe['constraints'],
                selectedId=request.selectedId, itineraries=[by_id[request.selectedId]] if safe.get('version')==2 else [by_id[i] for i in ids])


receipts = Receipts()
connections = BoundedSemaphore(4)


def digest(token):
    return sha256(token.encode()).hexdigest()


@contextmanager
def database(token, readonly=False):
    """One connection/transaction per explicit action, runtime role only."""
    if not connections.acquire(blocking=False):
        raise PersistenceError()
    phase = "connect"
    try:
        settings = connection_settings(os.environ)
        if not settings['user'].startswith('whereto_plan_runtime.'):
            raise PersistenceError(code="database_runtime_role_required")
        settings.update(application_name='whereto-private-plans', connect_timeout=5)
        with psycopg.connect(**settings, row_factory=dict_row) as connection:
            if not connection.pgconn.ssl_in_use:
                raise PersistenceError()
            connection.read_only = readonly
            connection.execute("SET LOCAL statement_timeout = '5s'")
            connection.execute("SET LOCAL lock_timeout = '2s'")
            role = connection.execute('SELECT current_user AS role').fetchone()['role']
            if role != 'whereto_plan_runtime':
                raise PersistenceError(code='database_runtime_role_required')
            connection.execute("SELECT set_config('whereto.access_hash', %s, true)", (digest(token),))
            phase = "transaction"
            yield connection
    except DatabaseCheckError as error:
        raise PersistenceError(code='database_runtime_role_required' if str(error)=='runtime_role_required' else 'database_not_configured') from None
    except psycopg.Error as error:
        code = ('database_authentication_failed' if error.sqlstate in ('28P01','28000') else
                'database_access_denied' if error.sqlstate=='42501' else
                'database_connection_failed' if phase=='connect' or isinstance(error,psycopg.OperationalError) else 'save_transaction_failed')
        raise PersistenceError(code=code) from None
    except (OSError, ValueError):
        raise PersistenceError(code='database_connection_failed' if phase=='connect' else 'save_validation_failed') from None
    finally:
        connections.release()


def insert(connection, table, values):
    # Identifiers come only from module constants, values always parameters.
    query = sql.SQL('INSERT INTO whereto.{} ({}) VALUES ({})').format(
        sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, values)),
        sql.SQL(',').join(sql.Placeholder() for _ in values))
    connection.execute(query, tuple(values.values()))


def write_document(connection, document, token):
    """Caller owns the atomic transaction; any stop failure aborts everything."""
    fingerprint = digest(document.model_dump_json())
    key = digest(token)
    # Serialize duplicate submissions for this capability without a retry loop.
    connection.execute('SELECT pg_advisory_xact_lock(%s)', (int(key[:15], 16),))
    prior = connection.execute('SELECT save_fingerprint FROM whereto.plans WHERE access_hash=%s', (key,)).fetchone()
    if prior:
        if prior['save_fingerprint'] != fingerprint:
            raise PersistenceError(409)
        return
    plan_id = uuid4()
    insert(connection, 'plans', dict(id=plan_id, data_mode=document.dataMode,
        access_hash=key, save_fingerprint=fingerprint, model_version=document.version,
        selected_option=next(i for i,p in enumerate(document.itineraries) if p.candidateId == document.selectedId)))
    req = document.constraints.model_dump(mode='json')
    values = {'plan_id': plan_id, **{column: req[field] for field,column in COLUMNS.items()}}
    values['activity_intents'] = Jsonb(values['activity_intents'])
    extras = {k: req[k] for k in PREFERENCES}
    for field, prefix in (('firstTravel', 'first_travel'), ('betweenTravel', 'between_travel')):
        preference = req[field]
        for suffix in ('value','unit','mode','exclusive'):
            values[prefix+'_'+suffix] = preference[suffix] if preference else (False if suffix == 'exclusive' else None)
        extras[field+'OriginText'] = preference.get('originText') if preference else None
    if document.version == 2:
        extras['advancedVersion'] = 2
        extras['advancedOptions'] = {o.candidateId:o.advanced.model_dump(mode='json') for o in document.itineraries}
    values.update(strict_destination=req['geography']['strictDestination'], excluded_regions=req['geography']['excludedRegions'], preferences=Jsonb(extras))
    insert(connection, 'plan_constraints', values)
    for i, option in enumerate(document.itineraries):
        itinerary_id = uuid4()
        insert(connection, 'generated_itineraries', dict(id=itinerary_id, plan_id=plan_id, option_position=i,
            candidate_id=option.candidateId, feasibility='provisional', travel_classification='unverified',
            generator_version='task50e-v2' if document.version==2 else 'task49-v1', fictional_metrics=Jsonb(option.fictionalMetrics.model_dump()) if option.fictionalMetrics else None))
        for stop in option.stops:
            stop_id = uuid4()
            insert(connection, 'itinerary_stops', dict(id=stop_id, itinerary_id=itinerary_id, position=stop.position,
                activity=stop.activity, timing_basis=stop.timingBasis, start_minute=stop.start,
                end_minute=stop.end, duration_minutes=stop.duration,
                fictional_snapshot=Jsonb(stop.fictional.model_dump()) if stop.fictional else None))
            insert(connection, 'source_metadata', dict(stop_id=stop_id, reference_kind='venue',
                provider=stop.provider, external_id=stop.reference, evidence_status='fictional' if document.dataMode=='mock' else 'unverified'))


def read_document(connection, token):
    plan = connection.execute('SELECT id,data_mode,selected_option,access_expires_at FROM whereto.plans WHERE access_hash=%s AND access_expires_at>now()', (digest(token),)).fetchone()
    if not plan:
        raise PersistenceError(404)
    row = connection.execute('SELECT * FROM whereto.plan_constraints WHERE plan_id=%s', (plan['id'],)).fetchone()
    if not row:
        raise PersistenceError(404)
    req = {field: row[column] for field,column in COLUMNS.items()}
    req['transport'] = req.get('transport') or 'driving'  # Legacy null means the original driving default.
    req.update({k: row['preferences'].get(k) for k in PREFERENCES})
    req['geography'] = dict(strictDestination=row['strict_destination'], excludedRegions=row['excluded_regions'])
    for field,prefix in (('firstTravel','first_travel'), ('betweenTravel','between_travel')):
        req[field] = None if row[prefix+'_value'] is None else {
            **{suffix: float(row[prefix+'_'+suffix]) if suffix=='value' else row[prefix+'_'+suffix] for suffix in ('value','unit','mode','exclusive')},
            'originText': row['preferences'].get(field+'OriginText')}
    advanced_version = row['preferences'].get('advancedVersion',1)
    advanced_options = row['preferences'].get('advancedOptions',{})
    itineraries = []
    for i,option in enumerate(connection.execute('SELECT id,candidate_id,option_position,fictional_metrics FROM whereto.generated_itineraries WHERE plan_id=%s ORDER BY option_position', (plan['id'],)).fetchall()):
        if option['option_position'] != i:
            raise PersistenceError(404)
        advanced = AdvancedSaved.model_validate(advanced_options.get(option['candidate_id'])) if advanced_version == 2 else None
        occurrence_order = advanced.occurrenceOrder if advanced else list(range(len(req['activities'])))
        stops = []
        for j,stop in enumerate(connection.execute("""SELECT s.*,m.provider,m.external_id FROM whereto.itinerary_stops s
            JOIN whereto.source_metadata m ON m.stop_id=s.id AND m.reference_kind='venue'
            WHERE s.itinerary_id=%s ORDER BY s.position""", (option['id'],)).fetchall()):
            if stop['position'] != j or j >= len(occurrence_order) or stop['activity'] != req['activities'][occurrence_order[j]]:
                raise PersistenceError(404)
            if plan['data_mode']=='real' and (stop['provider']!='google_places' or stop['fictional_snapshot'] or stop['timing_basis']!='unknown' or option['fictional_metrics']):
                raise PersistenceError(404)
            stops.append(SavedStop(position=j, activity=stop['activity'], provider=stop['provider'], reference=stop['external_id'],
                timingBasis=stop['timing_basis'], start=stop['start_minute'], end=stop['end_minute'], duration=stop['duration_minutes'], fictional=stop['fictional_snapshot']))
        if len(stops) != len(occurrence_order):
            raise PersistenceError(404)
        itineraries.append(SavedOption(candidateId=option['candidate_id'], advanced=advanced, stops=stops, fictionalMetrics=option['fictional_metrics']))
    if not 0 <= plan['selected_option'] < len(itineraries):
        raise PersistenceError(404)
    try:
        result = SavedDocument(version=advanced_version,dataMode=plan['data_mode'], constraints=req, selectedId=itineraries[plan['selected_option']].candidateId, itineraries=itineraries)
    except ValueError:
        raise PersistenceError(404) from None
    return {**result.model_dump(mode='json'), 'expiresAt': plan['access_expires_at'].isoformat(),
        'saved': True, 'liveDetailsAvailable': False}


def save(request):
    document = receipts.select(request)
    with database(request.accessToken) as connection:
        write_document(connection, document, request.accessToken)
    return {'saved': True}


def reopen(request):
    with database(request.accessToken, readonly=True) as connection:
        try:
            return read_document(connection, request.accessToken)
        except ValueError:
            # Includes nested stored-record validation, also for venue refresh.
            raise PersistenceError(404) from None
