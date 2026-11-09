"""Task 46 geographic and lifecycle regressions; all providers are invented."""
from backend.testing_clock import calendar_clock
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from backend.ai import Interpretation
from backend.date_resolution import resolve_datetime
from backend.interpretation import InterpretationInput, interpret_request
from backend.location_context import DestinationContext, outing_problem, relative_destination
from backend.option_sessions import OptionSessions, option_sessions
from backend.places import DiscoveryError, SearchArea, parse_response
from backend.provider_budget import ProviderBudget
from backend.real_fixtures import matrix_fixture
from backend.real_planning import real_plans, more_real_plans
from backend.sequential_discovery import search_area
from backend.test_real_planning import ENV, outing

ORIGIN = {'point':{'id':'authorized-start','coordinates':{'latitude':40.75,'longitude':-73.98}},
    'explicitly_authorized':True,'source':'manual','precision':'address_or_place',
    'label':'Synthetic public park','geographicDescription':'Synthetic reference, New York, NY'}
NOW = datetime(2026,10,28,17,48,tzinfo=timezone.utc)


from backend.location_fixtures import neighborhood_fixture


class GeographyLifecycle(unittest.TestCase):
    def setUp(self):
        self.enterContext(calendar_clock())
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.clock=1000
        env={**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.temp.name+'/cost.json'}
        for stub in (patch.dict(os.environ,env,clear=True),
            patch('backend.development_cost.time',side_effect=lambda:self.clock),
            patch('backend.provider_budget.monotonic',side_effect=lambda:self.clock),
            patch('requests.sessions.Session.send',side_effect=AssertionError('Live network forbidden')),
            patch('backend.places_transport.text_search',side_effect=neighborhood_fixture),
            patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture)):
            stub.start();self.addCleanup(stub.stop)
        self.addCleanup(option_sessions.entries.clear)

    def request(self, destination='Midtown Manhattan', **kw):
        return outing(activities=['food','drinks'],locationFirst=True,startingLocation=ORIGIN,**kw).model_copy(update={'location':destination})

    def test_neighborhood_address_mismatch_reproduced_and_anchor_corrected(self):
        # Historical include-name check would enforce text despite actual anchor.
        old=SearchArea(name='Midtown Manhattan',coordinates=ORIGIN['point']['coordinates'],
            radius_m=12000,include_name=True,enforce_name=False)
        response=neighborhood_fixture({'textQuery':'restaurants','pageSize':10})
        self.assertEqual(len(parse_response(response,old,10).candidates),0)
        area=search_area(self.request(),old.coordinates,True)
        fixed=parse_response(response,area,10)
        self.assertEqual(len(fixed.candidates),9)
        self.assertEqual(fixed.excluded_count,1)
        self.assertEqual(fixed.stages['geographyRejectedByReason'],{'outside_radius':1})
        self.assertTrue(area.anchor_verified)

    def test_manhattan_midtown_and_general_qualified_neighborhood(self):
        for destination in ('Manhattan','Midtown Manhattan','Shoreditch London'):
            origin={**ORIGIN,'point':{'id':'authorized-start','coordinates':{'latitude':51.52,'longitude':-.08}},'geographicDescription':'Synthetic reference, London'} if destination.endswith('London') else ORIGIN
            request=self.request(destination).model_copy(update={'startingLocation':type(self.request().startingLocation)(**origin)})
            for limit in (None,5,10):
                self.clock+=61
                request=type(request).model_validate({**request.model_dump(), 'startingLocation':origin,
                    'firstTravel':None if limit is None else {'value':limit,'mode':'flexible'}})
                result=real_plans(request,ProviderBudget())
                self.assertEqual(len(result.provisionalPlans),3,result.message)
                self.assertEqual(result.diagnostics['discoveredCounts'],[8,8])
                self.assertEqual(result.diagnostics['locationContext']['resolution'],'representative_point')
        print('NEIGHBORHOOD_FIXTURE: each search returned 10, geography retained 9, unique retained 8/activity; 3 initial plans.')

    def test_explicit_boundary_not_broadened_and_unresolved_recovery(self):
        for destination,strict in (('Only Unknown Area',False),('Midtown Manhattan',True)):
            with self.assertRaises(DiscoveryError) as caught:
                real_plans(self.request(destination,geography={'strictDestination':strict}),ProviderBudget())
            self.assertEqual(caught.exception.code,'geographic_verification' if strict else 'destination_unresolved')
        # Deliberate consent permits approximate anchor, never changes the name.
        request=self.request('Unknown Area',useOriginAsSearchAnchor=True)
        result=real_plans(request,ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertEqual(result.request.location,'Unknown Area')
        with self.assertRaises(DiscoveryError):
            real_plans(self.request('Unknown Area',useOriginAsSearchAnchor=True,geography={'strictDestination':True}),ProviderBudget())

    def test_relative_destination_and_manual_route_origin_are_separate(self):
        request=self.request('near me',currentArea={'coordinates':{'latitude':40.8,'longitude':-73.98}})
        with patch('backend.places_transport.text_search',side_effect=neighborhood_fixture) as search:
            result=real_plans(request,ProviderBudget())
        box=search.call_args_list[0].args[0]['locationRestriction']['rectangle']
        self.assertAlmostEqual((box['low']['latitude']+box['high']['latitude'])/2,40.8)
        self.assertTrue(all(p.firstLeg['source']=='manual' for p in result.provisionalPlans))
        self.assertNotIn('geographicDescription',result.model_dump_json())
        self.assertNotIn('"latitude":',result.model_dump_json())

    def test_ambiguous_distant_provider_matches_are_not_arbitrarily_resolved(self):
        data=neighborhood_fixture({'textQuery':'restaurants','pageSize':2})
        for p in data['places']:
            p['addressComponents']=[{'longText':'Springfield','types':['locality']}]
        data['places'][1]['location']={'latitude':39.,'longitude':-89.}
        with self.assertRaises(DiscoveryError) as caught:
            parse_response(data,SearchArea(name='Springfield',enforce_name=False),10)
        self.assertEqual(caught.exception.code,'destination_ambiguous')

    def test_missing_or_unresolved_surprise_never_manufactures_an_origin(self):
        request=outing(activities=['food','drinks'],planningMode='surprise',startingLocation=None,locationFirst=True).model_copy(update={'location':'Unknown Area'})
        with self.assertRaisesRegex(DiscoveryError,'Clarify the destination'):
            real_plans(request,ProviderBudget())
        self.assertIsNone(request.startingLocation)

    def test_pagination_continuations_keep_context_and_no_repeats(self):
        result=real_plans(self.request(),ProviderBudget())
        signatures=set()
        for i in range(16):
            signatures.update(tuple(v.id for v in p.candidate.venues) for p in result.provisionalPlans)
            self.assertEqual(len(signatures),(i+1)*3)
            if i<15:result=more_real_plans(result.optionsToken,expand_discovery=i==0)
        self.assertEqual(result.request.date,date(2026,11,7))
        self.assertEqual(result.request.location,'Midtown Manhattan')
        print('NEIGHBORHOOD_CONTINUATIONS',{'pages':16,'uniqueCombinations':len(signatures),'pools':result.diagnostics['discoveredCounts'],'searches':result.diagnostics['placesSearchRequests'],'matrixElements':result.diagnostics['matrixElements'],'date':result.request.date.isoformat()})

    def test_empty_unverified_destination_retains_expansion_and_recovery(self):
        with patch('backend.places_transport.text_search',return_value={'places':[]}):
            result=real_plans(self.request('Unknown Area'),ProviderBudget())
        self.assertEqual(result.errors[0].code,'destination_verification_unavailable')
        self.assertTrue(result.canDiscover)
        self.assertEqual(result.request.location,'Unknown Area')
        self.assertIn('Search coverage may also be limited',result.message)

    def test_provider_failure_not_disguised_as_destination_recovery(self):
        with patch('backend.places_transport.text_search',side_effect=DiscoveryError('quota','Provider quota unavailable')):
            with self.assertRaises(DiscoveryError) as caught:real_plans(self.request(),ProviderBudget())
        self.assertEqual(caught.exception.code,'quota')

    def test_nearby_paraphrases_through_actual_interpreter(self):
        for wording in ('around me','near me','nearby','around here','close to me','in my area','near my current location','around my location'):
            text=f'Plan dinner and drinks {wording} today for 2 people.'
            provider=SimpleNamespace(interpret=lambda _:Interpretation(activities=['dinner','drinks'],people=2,
                location=None,date=None,budget_per_person=None,preferences=[]))
            result=interpret_request(InterpretationInput(text=text,calendarTimezone='Asia/Kolkata'),provider,now=NOW)
            self.assertIsNotNone(result.request,result.issues)
            self.assertEqual(result.request.location,'near me')
            self.assertFalse(any(q.field=='location' for q in result.questions))
            self.assertEqual(result.request.calendarTimezone,'Asia/Kolkata')
        for text in ('Dinner near my friend','Dinner near me in manhattan','Dinner in Midtown Manhattan','Dinner near me in the Bronx'):
            self.assertFalse(relative_destination(text))
        self.assertTrue(relative_destination('Dinner near me, starting from Bryant Park.'))
        self.assertTrue(relative_destination('Dinner near me in the evening.'))

    def test_hyderabad_date_only_late_evening_and_explicit_bounds(self):
        for instant in (NOW.replace(hour=12,minute=30),NOW,NOW.replace(hour=18,minute=29)):
            resolved=resolve_datetime('today',[],[],'Hyderabad',now=instant)
            self.assertFalse(resolved.issues)
            request=self.request('Hyderabad').model_copy(update={'date':resolved.date,'startTime':resolved.start,
                'endTime':resolved.end,'calendarTimezone':resolved.timezone,
                'explicitStart':resolved.explicit_start,'explicitEnd':resolved.explicit_end})
            self.assertIsNone(outing_problem(request,instant+timedelta(seconds=1)))
            self.assertEqual(request.date,date(2026,10,28))
            self.assertEqual(outing_problem(request,NOW.replace(hour=18,minute=31))[0],'outing_date_expired')
        tomorrow=resolve_datetime('tomorrow',[],[],'Hyderabad',now=NOW)
        self.assertEqual(tomorrow.date,date(2026,10,29))
        for phrase,valid in (('today at 11:30 PM',True),('today at 6 PM',False),('today from 6 PM to 10 PM',False)):
            self.assertEqual(not bool(resolve_datetime(phrase,[],[],'Hyderabad',now=NOW).issues),valid)
        # Explicit end-only is not an explicit beginning.
        end=resolve_datetime('today until midnight',[],[],'Hyderabad',now=NOW)
        self.assertFalse(end.explicit_start);self.assertTrue(end.explicit_end)

    def test_continuation_uses_saved_date_and_distinct_validity_before_calls(self):
        result=real_plans(self.request(),ProviderBudget())
        original,_=option_sessions.get(result.optionsToken)
        with patch('backend.location_context.outing_problem',return_value=('outing_time_expired','Explicit time passed in Asia/Kolkata')) as check,patch('backend.places_transport.text_search') as search:
            with self.assertRaises(DiscoveryError) as caught:more_real_plans(result.optionsToken,expand_discovery=True)
            self.assertEqual(caught.exception.code,'outing_time_expired')
            self.assertEqual(check.call_args.args[0].date,original['request'].date)
            search.assert_not_called()
        sessions=OptionSessions()
        with patch('backend.option_sessions.monotonic',return_value=0):token=sessions.create({})
        with patch('backend.option_sessions.monotonic',return_value=601):
            with self.assertRaisesRegex(DiscoveryError,'does not mean your outing date'):sessions.get(token)

    def test_old_synthesized_window_reproduces_false_expiry(self):
        # Old continuation reclassified a date-only default as an explicit start.
        first=resolve_datetime('today',[],[],'Hyderabad',now=NOW,calendar_timezone='UTC')
        synthetic=f"from {first.start//60:02d}:{first.start%60:02d} to midnight"
        legacy=resolve_datetime('',[],[synthetic],'Hyderabad',manual_date=first.date.isoformat(),
            now=NOW+timedelta(minutes=1),calendar_timezone='UTC')
        self.assertTrue(any('passed' in issue for issue in legacy.issues))
        request=self.request('Hyderabad').model_copy(update={'date':date(2026,10,28),
            'startTime':1398,'calendarTimezone':'Asia/Kolkata','explicitStart':False,'explicitEnd':False})
        self.assertIsNone(outing_problem(request,NOW+timedelta(minutes=1)))
        explicit=request.model_copy(update={'explicitStart':True})
        self.assertEqual(outing_problem(explicit,NOW+timedelta(minutes=1))[0],'outing_time_expired')

    def test_timezone_contracts_and_cross_city_dst(self):
        for model,fields in ((DestinationContext,{'originalText':'x','timezone':'bad/zone'}),(InterpretationInput,{'text':'outing','calendarTimezone':'bad/zone'})):
            with self.assertRaises(ValidationError):model(**fields)
        with self.assertRaises(ValueError):outing_problem(self.request(),datetime(2026,10,28))
        ny=resolve_datetime('today',[],[],'New York',now=NOW)
        india=resolve_datetime('today',[],[],'Hyderabad',now=NOW)
        self.assertEqual((ny.timezone,india.timezone),('America/New_York','Asia/Kolkata'))
        other=resolve_datetime('today',[],[],'London',now=NOW,calendar_timezone='Europe/London')
        self.assertEqual(other.timezone,'Europe/London')
        later=NOW.replace(hour=21)
        self.assertEqual(resolve_datetime('today',[],[],'Hyderabad',now=later).date,date(2026,10,29))
        self.assertEqual(resolve_datetime('today',[],[],'Manhattan',now=later).date,date(2026,10,28))
        dst=resolve_datetime('2027-03-14 at 2:30 AM',[],[],'Manhattan',now=NOW)
        self.assertTrue(dst.issues)


class LifecycleAPI(unittest.TestCase):
    def test_options_preserve_safe_recovery_classification(self):
        import json
        from backend import main as api
        for code in ('expired','outing_date_expired','outing_time_expired'):
            with patch.object(api,'provider_budget',SimpleNamespace(settings=SimpleNamespace(mode='real',require_live_provider=lambda:None))),patch(
                    'backend.real_planning.more_real_plans',side_effect=DiscoveryError(code,'Safe recovery explanation')):
                response=api.more_options(api.OptionsRequest(token='synthetic-token'))
                self.assertEqual(response.status_code,422)
                self.assertEqual(json.loads(response.body)['code'],code)
