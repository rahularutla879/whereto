"""Acceptance regressions: zero live Google; hosted tests remain explicit opt-in."""
from datetime import datetime,timezone
import io,json,os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from backend.acceptance_fixtures import FixtureAI,search_fixture,matrix_fixture
from backend.interpretation import InterpretationInput,interpret_request
from backend.provider_budget import ProviderBudget
from backend.real_planning import PlannerInput,real_plans,more_real_plans
from backend.test_real_planning import ENV
from backend.saved_plans import Receipts,SaveRequest,PersistenceError,database
from backend.persistence_config import runtime_settings
from backend.database_check import DatabaseCheckError

START={'point':{'id':'test-origin','coordinates':{'latitude':17.44,'longitude':78.36}},'source':'manual',
    'label':'Synthetic My Home Bhooja fixture','precision':'address_or_place','explicitly_authorized':True}


class CinemaAcceptance(unittest.TestCase):
    def setUp(self):
        for item in (patch.dict(os.environ,ENV,clear=True),
            patch('requests.sessions.Session.send',side_effect=AssertionError('Live Google forbidden')),
            patch('backend.places_transport.text_search',side_effect=search_fixture),
            patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture)):
            mock=item.start();self.addCleanup(item.stop)
            if getattr(item,'attribute',None)=='text_search': self.search=mock
            if getattr(item,'attribute',None)=='compute_matrix': self.matrix=mock

    def request(self,activities=None,**kwargs):
        return PlannerInput(activities=activities or ['movie'],location='Hyderabad',calendarTimezone='Asia/Kolkata',
            date='2026-11-14',locationFirst=True,startingLocation=START,**kwargs)

    def test_full_one_stop_cinema_origin_routes_and_persistence(self):
        result=real_plans(self.request(),ProviderBudget())
        self.assertEqual(len(result.provisionalPlans),3)
        self.assertTrue(all(len(p.stops)==1 and p.legs==[] and p.firstLeg['minutes'] is not None for p in result.provisionalPlans))
        self.assertTrue(all(p.stops[0].venue.activity=='movie' for p in result.provisionalPlans))
        self.assertIn('movie',self.search.call_args.args[0]['textQuery'])
        issued=Receipts();r=issued.issue(result)
        document=issued.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,
            candidateIds=[p.candidate.id for p in r.provisionalPlans],selectedId=r.provisionalPlans[0].candidate.id))
        self.assertEqual(len(document.itineraries[0].stops),1)
        self.assertNotIn('Synthetic cinema',document.model_dump_json())
        more=more_real_plans(result.optionsToken)
        self.assertTrue(more.provisionalPlans)
        self.assertFalse(set(p.candidate.id for p in result.provisionalPlans)&set(p.candidate.id for p in more.provisionalPlans))

    def test_required_wordings_and_destination_calendar(self):
        now=datetime(2026,11,1,0,30,tzinfo=timezone.utc)
        for text,expected in [('movie tomorrow in hyderabad',['movie']),('show movies in Hyderabad tomorrow',['movie']),
            ('find a cinema near My Home Bhooja',['movie']),('movie theater in Manhattan tonight',['movie']),
            ('bowling tomorrow',['bowling']),('pottery class tomorrow',['custom:pottery class'])]:
            with self.subTest(text=text):
                value=InterpretationInput(text=text,preferences={'location':'Hyderabad','date':'2026-11-02'} if 'Bhooja' in text else {'location':'Hyderabad'} if text in ('bowling tomorrow','pottery class tomorrow') else {})
                result=interpret_request(value,FixtureAI(),now=now)
                self.assertIsNotNone(result.request,result.issues)
                self.assertEqual([a.value for a in result.request.activities],expected)
                if 'Hyderabad' in result.request.location:
                    self.assertEqual(result.request.calendarTimezone,'Asia/Kolkata')
                    self.assertEqual(result.request.date.isoformat(),'2026-11-02')
                else:
                    self.assertEqual(result.request.calendarTimezone,'America/New_York')
                    self.assertEqual(result.request.date.isoformat(),'2026-10-31')

    def test_restaurant_movie_dinner_and_drinks_remain_complete(self):
        for activities in (['food'],['movie','food'],['food','drinks'],['bowling'],['custom:pottery class']):
            with self.subTest(activities=activities):
                result=real_plans(self.request(activities),ProviderBudget())
                self.assertTrue(result.provisionalPlans,result.message)
                self.assertTrue(all([s.venue.activity.value for s in p.stops]==activities for p in result.provisionalPlans))

    def test_missing_routes_are_distinct_from_missing_venues(self):
        self.matrix.return_value=[];self.matrix.side_effect=None
        result=real_plans(self.request(),ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertTrue(all(p.firstLeg['minutes'] is None and p.travelClassification=='unverified' for p in result.provisionalPlans))
        self.assertTrue(all(p.firstLeg['miles'] is None for p in result.provisionalPlans))

    def test_no_relevant_venues(self):
        self.search.return_value={'places':[]};self.search.side_effect=None
        result=real_plans(self.request(),ProviderBudget())
        self.assertFalse(result.provisionalPlans)
        self.assertTrue(any(e.code=='no_relevant_venues' for e in result.errors),result.errors)

    def test_actual_provider_quota_classification(self):
        from types import SimpleNamespace
        from backend.provider_errors import classify
        from backend.places import DiscoveryError
        response=SimpleNamespace(status_code=429,json=lambda:{'error':{'details':[{'metadata':{'quota_limit':'SearchTextRequestPerDayPerProject'},'reason':'RATE_LIMIT_EXCEEDED'}]}})
        code,message,diagnostics=classify(response,'search')
        error=DiscoveryError(code,message);error.diagnostics=diagnostics
        self.search.side_effect=error
        with self.assertRaises(DiscoveryError) as failure:real_plans(self.request(),ProviderBudget())
        self.assertEqual(failure.exception.code,'quota')
        self.assertEqual(failure.exception.diagnostics['quotaBoundary'],'daily')

    def test_strict_first_leg_never_relaxes_for_single_stop(self):
        result=real_plans(self.request(firstTravel={'value':0.0,'unit':'minutes','mode':'strict'}),ProviderBudget())
        self.assertFalse(result.provisionalPlans)


class RuntimeConfiguration(unittest.TestCase):
    def test_admin_environment_uses_only_private_restricted_file(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'.env.persistence'
            path.write_text("WHERETO_DB_USER='whereto_plan_runtime.fixture'\nWHERETO_DB_PASSWORD='not-a-real-password'\n");path.chmod(0o600)
            with patch('backend.persistence_config.RUNTIME_FILE',path),patch('backend.persistence_config.connection_settings',side_effect=lambda value:value):
                result=runtime_settings({'WHERETO_DB_USER':'postgres.fixture','WHERETO_DB_PASSWORD':'admin-do-not-use'})
                self.assertTrue(result['WHERETO_DB_USER'].startswith('whereto_plan_runtime.'))
                self.assertNotIn('admin-do-not-use',str(result))
                path.chmod(0o644)
                with self.assertRaises(DatabaseCheckError):runtime_settings({'WHERETO_DB_USER':'postgres.fixture'})

    def test_configuration_does_not_execute_shell(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'.env.persistence';path.write_text('WHERETO_DB_USER=x\nsource /tmp/anything\n');path.chmod(0o600)
            with patch('backend.persistence_config.RUNTIME_FILE',path):
                with self.assertRaises(DatabaseCheckError):runtime_settings({'WHERETO_DB_USER':'postgres.fixture'})

    def test_database_failure_codes_and_redaction(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(PersistenceError) as failure:
                with database('A'*43):pass
            self.assertEqual(failure.exception.code,'database_not_configured')
        import psycopg
        for error,code in [(psycopg.errors.InvalidPassword('SECRET'),'database_authentication_failed'),(psycopg.OperationalError('SECRET'),'database_connection_failed')]:
            with patch('backend.saved_plans.connection_settings',return_value={'user':'whereto_plan_runtime.test'}),patch('psycopg.connect',side_effect=error):
                with self.assertRaises(PersistenceError) as failure:
                    with database('A'*43):pass
                self.assertEqual(failure.exception.code,code);self.assertNotIn('SECRET',str(failure.exception))


class SafeDiagnostics(unittest.TestCase):
    def test_internal_failure_has_reference_without_exception_content(self):
        from backend.main import failure
        with self.assertLogs('whereto.failures',level='WARNING') as logs:
            response=failure('internal_application_error',500,error=RuntimeError('PRIVATE_TOKEN_SQL_PASSWORD'))
        payload=json.loads(response.body)
        self.assertEqual(payload['code'],'internal_application_error')
        self.assertRegex(payload['correlationId'],r'^[a-f0-9]{16}$')
        self.assertNotIn('PRIVATE',str(payload)+str(logs.output))

    def test_transaction_failure_is_not_misclassified_as_venue_scarcity(self):
        import psycopg
        from unittest.mock import MagicMock
        connection=MagicMock();connection.pgconn.ssl_in_use=True
        connection.execute.return_value.fetchone.return_value={'role':'whereto_plan_runtime'}
        connection.__enter__.return_value=connection
        connection.__exit__.return_value=False
        with patch('backend.saved_plans.connection_settings',return_value={'user':'whereto_plan_runtime.test'}),patch('psycopg.connect',return_value=connection):
            with self.assertRaises(PersistenceError) as failure:
                with database('A'*43):raise psycopg.IntegrityError('PRIVATE SQL')
            self.assertEqual(failure.exception.code,'save_transaction_failed')
            self.assertNotIn('PRIVATE',str(failure.exception))
