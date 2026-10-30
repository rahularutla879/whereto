"""Offline contracts/boundaries and opt-in rollback-only hosted persistence."""
from contextlib import contextmanager
import json
import os
import secrets
import unittest
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
from pydantic import ValidationError

from backend.database_check import connection_settings
from backend.models import PlanningRequest
from backend.ranking import recommend_plans
from backend.saved_plans import (SaveRequest, OpenRequest, SavedDocument, Receipts, PersistenceError,
    safe_document, digest, write_document, read_document, database, save, reopen)


def fixture():
    return recommend_plans(PlanningRequest(activities=['coffee','museum'], date='2026-11-07',
        planningMode='surprise', betweenTravel={'value':30.0,'unit':'minutes','mode':'flexible'},
        travel=120, travelExclusive=True, explicitEnd=True, endTime=1200))


def request_for(registry, result=None):
    result = registry.issue(result or fixture())
    candidates = result.plans + result.provisionalPlans
    return SaveRequest(receipt=result.saveReceipt, accessToken=result.saveAccessToken,
        candidateIds=[p.candidate.id for p in candidates], selectedId=candidates[-1].candidate.id)


class OfflinePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = Receipts()
        self.request = request_for(self.registry)

    def test_complete_server_receipt_contains_multiple_ordered_options(self):
        self.assertEqual(len(self.request.accessToken),43)
        self.assertNotEqual(self.request.receipt,self.request.accessToken)
        doc = self.registry.select(self.request)
        self.assertEqual(len(doc.itineraries), 3)
        self.assertEqual([s.activity for s in doc.itineraries[0].stops], ['coffee','museum'])
        self.assertEqual([s.position for s in doc.itineraries[0].stops], [0,1])
        self.assertEqual(doc.selectedId, doc.itineraries[-1].candidateId)
        self.assertEqual(doc.constraints.betweenTravel.mode, 'flexible')
        self.assertTrue(doc.constraints.travelExclusive)
        self.assertTrue(doc.constraints.explicitEnd)

    def test_surprise_planner_input_is_mapped_to_retained_request_fields(self):
        from backend.main import generate_plan
        from backend.real_planning import PlannerInput
        request=PlannerInput(activities=['coffee','museum'],date='2026-11-07',planningMode='surprise',
            locationFirst=True,betweenTravel={'value':30.0,'mode':'flexible'})
        result=generate_plan(request)
        save_request=request_for(self.registry,result)
        document=self.registry.select(save_request)
        self.assertNotIn('searchRadius',document.constraints.model_dump())
        self.assertNotIn('locationFirst',document.constraints.model_dump())
        self.assertEqual(document.constraints.betweenTravel.mode,'flexible')

    def test_client_cannot_submit_response_or_scores(self):
        for field,value in [('score',1),('plans',[]),('routeEvidence',[]),('constraints',{})]:
            with self.assertRaises(ValidationError):
                SaveRequest.model_validate({**self.request.model_dump(),field:value})

    def test_invalid_and_excessive_counts(self):
        for changes in ({'candidateIds':[]}, {'candidateIds':['x']*4}, {'accessToken':'guess'},
                        {'receipt':'x'*44}, {'selectedId':'x'*201}):
            with self.assertRaises(ValidationError):
                SaveRequest.model_validate({**self.request.model_dump(), **changes})

    def test_unknown_duplicate_or_changed_selection_rejected(self):
        for ids,selected in [(['unknown'],'unknown'), ([self.request.selectedId]*2,self.request.selectedId),
                             (self.request.candidateIds,'unknown')]:
            with self.assertRaises(PersistenceError):
                self.registry.select(self.request.model_copy(update={'candidateIds':ids,'selectedId':selected}))

    def test_receipt_expiry_and_missing(self):
        with patch('backend.saved_plans.monotonic', return_value=10**15):
            with self.assertRaises(PersistenceError):self.registry.select(self.request)
        with self.assertRaises(PersistenceError):
            self.registry.select(self.request.model_copy(update={'receipt':secrets.token_urlsafe(32)}))

    def test_duplicate_same_capability_allowed_new_capability_rejected(self):
        self.assertEqual(self.registry.select(self.request), self.registry.select(self.request))
        with self.assertRaises(PersistenceError):
            self.registry.select(self.request.model_copy(update={'accessToken':secrets.token_urlsafe(32)}))

    def test_receipts_bounded_and_expire(self):
        for _ in range(105): self.registry.issue(fixture())
        self.assertEqual(len(self.registry.items),100)
        with patch('backend.saved_plans.monotonic', return_value=10**15):self.registry.issue(fixture())
        self.assertEqual(len(self.registry.items),1)

    def test_mock_without_database_or_provider(self):
        with patch('psycopg.connect', side_effect=AssertionError('No DB')):
            self.assertTrue(self.registry.issue(fixture()).saveReceipt)

    def test_real_allowlist_drops_all_google_content(self):
        original = fixture()
        # Construct a server-side real fixture without invoking adapters/transports.
        plans = []
        for p in original.plans + original.provisionalPlans:
            stops = []
            for i,s in enumerate(p.stops):
                venue = s.venue.model_copy(update={'providerPlaceId':f'Place_{i}', 'name':'DO_NOT_STORE_NAME',
                    'address':'DO_NOT_STORE_ADDRESS','rating':4.9,'mapsUrl':'DO_NOT_STORE_URL'})
                stops.append(s.model_copy(update={'venue':venue}))
            plans.append(p.model_copy(update={'stops':stops,'routeEvidence':[{'DO_NOT_STORE_ROUTE':123}]}))
        result = original.model_copy(update={'dataMode':'real','plans':plans,'provisionalPlans':[]})
        safe = safe_document(result)
        serialized = json.dumps({**safe,'options':[p.model_dump() for p in safe['options']]})
        for value in ('DO_NOT_STORE', 'ranking', 'routeEvidence', 'rating', 'address'):
            self.assertNotIn(value,serialized)
        for option in safe['options']:
            self.assertIsNone(option.fictionalMetrics)
            for stop in option.stops:
                self.assertIsNone(stop.fictional)
                self.assertIsNone(stop.start)
                self.assertIsNone(stop.duration)
                self.assertEqual(stop.provider,'google_places')

    def test_no_raw_errors_or_admin_runtime(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(PersistenceError) as failure:
                with database(self.request.accessToken): pass
            self.assertNotIn('password',str(failure.exception))
        with patch('backend.saved_plans.connection_settings',return_value={'user':'postgres.secret'}),patch('psycopg.connect') as connect:
            with self.assertRaises(PersistenceError):
                with database(self.request.accessToken):pass
            connect.assert_not_called()

    def test_database_driver_error_redacted(self):
        with patch('backend.saved_plans.connection_settings',return_value={'user':'whereto_plan_runtime.test'}),patch('psycopg.connect',side_effect=psycopg.OperationalError('SECRET')):
            with self.assertRaises(PersistenceError) as failure:
                with database(self.request.accessToken):pass
            self.assertNotIn('SECRET',str(failure.exception))


@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS')=='1','Opt-in hosted rollback tests')
class HostedPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.connection=psycopg.connect(**connection_settings(os.environ))
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.connection.execute("SET LOCAL statement_timeout='15s'")
        from backend.database_migrate import migrate
        migrate(self.connection)
        self.connection.row_factory=dict_row
        self.registry=Receipts();self.request=request_for(self.registry)
        self.document=self.registry.select(self.request)

    def runtime(self,token=None):
        self.connection.execute('SET LOCAL ROLE whereto_plan_runtime')
        self.connection.execute("SELECT set_config('whereto.access_hash',%s,true)",(digest(token or self.request.accessToken),))

    def test_transactional_save_and_complete_retrieval(self):
        self.runtime()
        write_document(self.connection,self.document,self.request.accessToken)
        result=read_document(self.connection,self.request.accessToken)
        self.assertEqual(result['constraints'],self.document.constraints.model_dump(mode='json'))
        self.assertEqual(result['itineraries'],[p.model_dump(mode='json') for p in self.document.itineraries])
        self.assertEqual(result['selectedId'],self.document.selectedId)
        self.assertNotIn('access_hash',json.dumps(result))
        self.assertEqual(self.connection.execute('SELECT count(*) AS n FROM whereto.plans').fetchone()['n'],1)

    def test_duplicate_save_is_idempotent_and_mutation_denied(self):
        self.runtime()
        write_document(self.connection,self.document,self.request.accessToken)
        write_document(self.connection,self.document,self.request.accessToken)
        self.assertEqual(self.connection.execute('SELECT count(*) AS n FROM whereto.plans').fetchone()['n'],1)
        changed=self.document.model_copy(update={'selectedId':self.document.itineraries[0].candidateId})
        with self.assertRaises(PersistenceError):write_document(self.connection,changed,self.request.accessToken)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.connection.transaction(): self.connection.execute("UPDATE whereto.plans SET selected_option=0")

    def test_partial_failure_rolls_back_every_table(self):
        self.runtime()
        import backend.saved_plans as module
        real_insert=module.insert
        def fail(connection,table,values):
            if table=='itinerary_stops' and values['position']==1:
                values['position']=-1
            return real_insert(connection,table,values)
        with self.assertRaises(psycopg.IntegrityError):
            with self.connection.transaction(),patch('backend.saved_plans.insert',side_effect=fail):
                write_document(self.connection,self.document,self.request.accessToken)
        for table in ('plans','plan_constraints','generated_itineraries','itinerary_stops','source_metadata'):
            self.assertEqual(self.connection.execute(f'SELECT count(*) AS n FROM whereto.{table}').fetchone()['n'],0)

    def test_wrong_missing_expired_and_uuid_access_denied(self):
        self.runtime();write_document(self.connection,self.document,self.request.accessToken)
        self.connection.execute("SELECT set_config('whereto.access_hash',%s,true)",(digest(secrets.token_urlsafe(32)),))
        with self.assertRaises(PersistenceError):read_document(self.connection,self.request.accessToken)
        self.assertEqual(self.connection.execute('SELECT count(*) AS n FROM whereto.plans').fetchone()['n'],0)
        self.connection.execute('RESET ROLE')
        self.connection.execute("UPDATE whereto.plans SET access_expires_at=now()-interval '1 second' WHERE access_hash=%s",(digest(self.request.accessToken),))
        self.runtime()
        with self.assertRaises(PersistenceError):read_document(self.connection,self.request.accessToken)

    def test_api_operations_against_real_postgres_rollback(self):
        @contextmanager
        def same_transaction(token,readonly=False):
            self.runtime(token)
            yield self.connection
        with patch('backend.saved_plans.database',same_transaction),patch('backend.saved_plans.receipts',self.registry):
            self.assertEqual(save(self.request),{'saved':True})
            self.assertTrue(reopen(OpenRequest(accessToken=self.request.accessToken))['saved'])

    def test_real_storage_is_identifiers_only_and_reopens_without_provider(self):
        options=[]
        for option in self.document.itineraries:
            stops=[stop.model_copy(update={'provider':'google_places','reference':f'Place_{stop.position}',
                'fictional':None,'start':None,'end':None,'duration':None,'timingBasis':'unknown'}) for stop in option.stops]
            options.append(option.model_copy(update={'stops':stops,'fictionalMetrics':None}))
        document=SavedDocument.model_validate({**self.document.model_dump(), 'dataMode':'real',
            'itineraries':[o.model_dump() for o in options]})
        self.runtime();write_document(self.connection,document,self.request.accessToken)
        with patch('backend.main.generate_plan',side_effect=AssertionError('No regeneration')):
            result=read_document(self.connection,self.request.accessToken)
        self.assertFalse(result['liveDetailsAvailable'])
        self.assertEqual(result['dataMode'],'real')
        for option in result['itineraries']:
            self.assertIsNone(option['fictionalMetrics'])
            self.assertTrue(all(s['fictional'] is None and s['start'] is None for s in option['stops']))
        rows=self.connection.execute('SELECT ranking_score,travel_classification FROM whereto.generated_itineraries').fetchall()
        self.assertTrue(all(r['ranking_score'] is None and r['travel_classification']=='unverified' for r in rows))

    def test_runtime_no_ledger_ddl_delete_or_cross_capability_write(self):
        self.runtime()
        for query in ('SELECT * FROM whereto.schema_migrations','DELETE FROM whereto.plans',
                      'CREATE TABLE whereto.forbidden(id int)'):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with self.connection.transaction():self.connection.execute(query)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.connection.transaction():
                self.connection.execute("INSERT INTO whereto.plans(data_mode,access_hash) VALUES ('mock',%s)",(digest('other'),))
