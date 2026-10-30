"""Kothapet reproduction uses invented places/routes, never actual supply claims."""
import os
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from backend.real_planning import real_plans,more_real_plans
from backend.provider_budget import ProviderBudget
from backend.test_real_planning import ENV,outing
from backend.option_sessions import option_sessions
from backend.development_cost import dispatch
from backend.location_policy import FirstTravel
from backend.sequential_discovery import search_area

class StrictLocal(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.dict(os.environ,{**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.tmp.name+'/usage.json'},clear=True);p.start();self.addCleanup(p.stop)
        p=patch('requests.sessions.Session.send',side_effect=AssertionError('No live provider requests'));p.start();self.addCleanup(p.stop)
        self.addCleanup(option_sessions.entries.clear)
        self.searches=[];self.first_seconds=600;self.distant_only=False
    def request(self,**changes):
        origin={'point':{'id':'Synthetic_Kothapet_origin','place_id':'Synthetic_Kothapet_origin'},'reference_coordinates':{'latitude':17.36,'longitude':78.54},'explicitly_authorized':True,'source':'manual','precision':'neighborhood','geographicDescription':'Synthetic Kothapet reference, Hyderabad','label':'Synthetic Kothapet reference'}
        return outing(activities=['food','drinks'],locationFirst=True,startingLocation=origin,firstTravel=FirstTravel(value=10.,mode='strict'),**changes).model_copy(update={'location':'Hyderabad'})
    def search(self,body,**_):
        dispatch('search');self.searches.append(body)
        from backend.strict_local_fixtures import local_places
        return local_places(body,distant_only=self.distant_only)
    def matrix(self,body):
        dispatch('matrix',len(body['origins'])*len(body['destinations']))
        from backend.strict_local_fixtures import local_matrix
        return local_matrix(body,self.first_seconds)
    def run_plan(self,request=None):
        with patch('backend.places_transport.text_search',side_effect=self.search),patch('backend.routes_transport.compute_matrix',side_effect=self.matrix):
            return real_plans(request or self.request(),ProviderBudget())
    def test_initial_far_routes_are_withheld_and_nearby_pagination_finds_local(self):
        result=self.run_plan()
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertFalse(result.explorationPlans)
        self.assertTrue(all(p.firstLeg['minutes']<=10 for p in result.provisionalPlans))
        self.assertTrue(any(b.get('pageToken') for b in self.searches))
        self.assertTrue(all('locationRestriction' in b for b in self.searches))
        self.assertNotIn('in Hyderabad',self.searches[0]['textQuery'])
        self.assertGreater(result.diagnostics['firstStopVerification']['overMaximum'],0)
        self.assertEqual(result.request.firstTravel.value,10)
    def test_explicit_beyond_choice_and_return_do_not_change_requirement(self):
        self.distant_only=True
        result=self.run_plan()
        self.assertFalse(result.provisionalPlans+result.explorationPlans)
        self.assertTrue(result.canShowBeyond)
        self.assertIn('10-minute travel limit',result.message)
        searches=len(self.searches)
        with patch('backend.places_transport.text_search',side_effect=self.search),patch('backend.routes_transport.compute_matrix',side_effect=self.matrix):
            beyond=more_real_plans(result.optionsToken,show_beyond=True)
            self.assertTrue(beyond.explorationPlans)
            self.assertTrue(all(p.travelClassification=='beyond_limit' and p.firstLeg['minutes']==30 for p in beyond.explorationPlans))
            back=more_real_plans(result.optionsToken)
            self.assertFalse(back.explorationPlans)
        self.assertEqual(len(self.searches),searches)
        self.assertEqual(back.request.firstTravel.mode,'strict')
        self.assertEqual(back.request.firstTravel.value,10)
    def test_strict_and_flexible_exact_seconds(self):
        from backend.routes import RouteLeg
        from backend.location_policy import exceeds
        for mode,exclusive,seconds,expected in [('strict',False,600,False),('strict',True,600,True),('strict',False,601,True),('flexible',False,1200,False),('flexible',False,1201,True)]:
            preference=FirstTravel(value=10.,mode=mode,exclusive=exclusive)
            leg=RouteLeg(origin_id='a',destination_id='b',mode='drive',status='ok',estimate_type='traffic_unaware',duration_seconds=float(seconds),duration_minutes=seconds/60,distance_meters=1000)
            self.assertEqual(exceeds(leg,preference),expected)
    def test_geographic_search_does_not_expand_travel_requirement(self):
        request=self.request();area=search_area(request,request.startingLocation.reference_coordinates,True,10)
        self.assertLess(area.radius_m,12000)
        self.assertTrue(area.restrict_to_area)
        self.assertEqual(request.firstTravel.value,10)

    def test_real_numeric_cost_intent_never_filters_unknown_prices(self):
        from backend.ai import Interpretation
        from backend.interpretation import InterpretationInput,interpret_request
        from types import SimpleNamespace
        from datetime import datetime,timezone
        ai=Interpretation(activities=['dinner','drinks'],location='Hyderabad',date=None,preferences=[],budget_per_person=5,currency='INR',uncertainties=['Budget currency is unknown'])
        interpreted=interpret_request(InterpretationInput(text='Dinner and drinks in Hyderabad tomorrow under 5 INR each'),SimpleNamespace(interpret=lambda _:ai),now=datetime(2026,10,30,12,tzinfo=timezone.utc))
        self.assertIsNotNone(interpreted.request,interpreted.issues)
        self.assertFalse(interpreted.questions)
        fabricated=interpret_request(InterpretationInput(text='Dinner and drinks in Hyderabad tomorrow'),SimpleNamespace(interpret=lambda _:ai),now=datetime(2026,10,30,12,tzinfo=timezone.utc))
        self.assertIsNone(fabricated.request.budget)
        self.assertIsNone(fabricated.request.groupBudget)
        self.assertTrue(any('not verified' in note for note in interpreted.notes))
        result=self.run_plan(self.request(budget=0))
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertTrue(all(p.costPerPerson is None and p.travelClassification!='beyond_limit' for p in result.provisionalPlans))

    def test_exact_model_uncertainties_preserve_origin_and_required_access(self):
        from backend.ai import Interpretation
        from backend.interpretation import InterpretationInput,interpret_request
        from types import SimpleNamespace
        from datetime import datetime,timezone
        for text,uncertainty,activities in [
            ('Dinner in Manhattan tomorrow. Start from my hotel in Jersey City.','Start from my hotel in Jersey City',['dinner']),
            ('Museum and dinner in Manhattan tomorrow. We require wheelchair access.','wheelchair access',['museum','dinner'])]:
            ai=Interpretation(activities=activities,location='Manhattan',date=None,preferences=[],budget_per_person=None,uncertainties=[uncertainty])
            result=interpret_request(InterpretationInput(text=text),SimpleNamespace(interpret=lambda _:ai),now=datetime(2026,10,30,12,tzinfo=timezone.utc))
            self.assertIsNotNone(result.request,result.issues)
            self.assertEqual(result.request.location,'Manhattan')
            self.assertEqual(result.request.requireWheelchairAccess,'wheelchair' in text)
            self.assertFalse(result.questions)

    def test_confirmed_coordinate_origin_uses_actual_first_leg(self):
        request=self.request()
        origin=request.startingLocation.model_copy(update={'point':request.startingLocation.point.model_copy(update={'place_id':None,'coordinates':request.startingLocation.reference_coordinates})})
        result=self.run_plan(request.model_copy(update={'startingLocation':origin}))
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertTrue(all(p.firstLeg['minutes']==10 for p in result.provisionalPlans))
