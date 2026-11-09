"""Mode behavior through interpretation, actual planner and persistence mapping."""
from backend.testing_clock import calendar_clock
import os
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from pydantic import ValidationError
from backend.ai import Interpretation
from backend.models import TransportationMode
from backend.interpretation import InterpretationInput,interpret_request
from backend.real_planning import real_plans,more_real_plans,PlannerInput
from backend.provider_budget import ProviderBudget,ProviderSettings
from backend.real_fixtures import search_fixture
from backend.travel_mode_fixtures import matrix
from backend.test_real_planning import ENV,outing
from backend.option_sessions import option_sessions
from backend.routes import RouteError,matrix_body,RoutePoint
from backend.routes_transport import _validate_basic_body
from backend.saved_plans import Receipts,SaveRequest

NOW=datetime(2026,11,2,15,tzinfo=timezone.utc)
class AI:
 def __init__(self,location='Baltimore',transport=None,uncertainties=None):self.location=location;self.transport=transport;self.uncertainties=uncertainties or [];self.calls=0
 def interpret(self,text):
  self.calls+=1
  return Interpretation(activities=['dinner','coffee'],location=self.location,transport=self.transport,uncertainties=self.uncertainties,budget_per_person=None,date=None,preferences=[])

class InterpretationModes(unittest.TestCase):
 def test_default_manual_invalid_and_explicit_null(self):
  for chosen,expected in [('', 'driving'),('driving','driving'),('walking','walking')]:
   result=interpret_request(InterpretationInput(text='Dinner and coffee in Baltimore tomorrow',preferences={'transport':chosen}),AI(),now=NOW)
   self.assertIsNotNone(result.request,result.issues);self.assertEqual(result.request.transport,expected)
  for invalid in ('cycling','transit','teleport','',123):
   with self.assertRaises(ValidationError):outing(transport=invalid)
  self.assertEqual(outing().transport,'driving');self.assertEqual(outing(transport=None).transport,'driving')
  self.assertEqual(PlannerInput.model_json_schema()['properties']['transport']['enum'],['driving','walking'])
  with self.assertRaises(ValidationError):InterpretationInput(text='Dinner tomorrow',preferences={'transport':'cycling'})
 def test_natural_mode_and_conflict_are_explicit(self):
  for suffix,manual,expected in [('walking between stops','','walking'),('driving','','driving'),('walking between stops, not driving','','walking'),('walking between stops','driving',None),('driving','walking',None),('walking between stops and driving to the first stop','',None),('by bus','walking',None)]:
   result=interpret_request(InterpretationInput(text='Dinner and coffee in Baltimore tomorrow, '+suffix,preferences={'transport':manual}),AI(),now=NOW)
   if expected:self.assertIsNotNone(result.request,result.issues);self.assertEqual(result.request.transport,expected)
   else:self.assertIsNone(result.request);self.assertTrue(any('mode' in i or 'Travel mode' in i for i in result.issues))
 def test_manual_mode_does_not_require_model_transport_and_survives_followup(self):
  provider=AI(location=None)
  first=interpret_request(InterpretationInput(text='Dinner and coffee tomorrow',preferences={'transport':'walking'}),provider,now=NOW)
  self.assertTrue(first.pending);self.assertIsNone(first.request)
  second=interpret_request(InterpretationInput(text=first.pending.text,pending=first.pending,answers={'location':'Baltimore'},preferences={'transport':'walking'}),provider,now=NOW)
  self.assertIsNotNone(second.request,second.issues);self.assertEqual(second.request.transport,'walking');self.assertEqual(provider.calls,1)
 def test_optional_mode_uncertainty_does_not_require_another_model_guess(self):
  for selected in ('','walking'):
   result=interpret_request(InterpretationInput(text='Dinner and coffee in Baltimore tomorrow',preferences={'transport':selected}),AI(uncertainties=['transport mode unspecified']),now=NOW)
   self.assertIsNotNone(result.request,result.issues);self.assertEqual(result.request.transport,selected or 'driving')
 def test_travel_mode_does_not_hide_an_omitted_walk_activity(self):
  for selected in ('walking','driving'):
   result=interpret_request(InterpretationInput(text='Dinner and coffee and a walk in Baltimore tomorrow',preferences={'transport':selected}),AI(),now=NOW)
   self.assertIsNone(result.request);self.assertTrue(any(q.field=='activities' for q in result.questions))
 def test_hallucinated_transport_stays_blocked(self):
  result=interpret_request(InterpretationInput(text='Dinner and coffee in Baltimore tomorrow'),AI(transport='walking'),now=NOW)
  self.assertIsNone(result.request);self.assertIn('could not be verified',' '.join(result.issues))

class PlannerModes(unittest.TestCase):
 def setUp(self):
  self.enterContext(calendar_clock())
  for item in (patch.dict(os.environ,ENV,clear=True),patch('requests.Session.send',side_effect=AssertionError('No live Google')),patch('backend.places_transport.text_search',side_effect=search_fixture)):
   item.start();self.addCleanup(item.stop)
  self.matrix=patch('backend.routes_transport.compute_matrix',side_effect=matrix).start();self.addCleanup(patch.stopall)
 def run_mode(self,mode='driving',**kwargs):
  budget=ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3,matrix_elements_per_outing=27,matrix_elements_per_session=300))
  return real_plans(outing(transport=mode,**kwargs),budget),budget
 def test_same_venues_different_directional_origin_and_interstop_times(self):
  seen={}
  for mode,wire in [('driving','DRIVE'),('walking','WALK')]:
   self.matrix.reset_mock();result,budget=self.run_mode(mode)
   self.assertEqual(len(result.provisionalPlans),3)
   self.assertTrue(all(call.args[0]['travelMode']==wire for call in self.matrix.call_args_list))
   for call in self.matrix.call_args_list:_validate_basic_body(call.args[0])
   plans=result.provisionalPlans;first=plans[0]
   self.assertTrue(all(p.firstLeg['mode']==('walk' if mode=='walking' else 'drive') for p in plans))
   self.assertTrue(all(e['route']['mode']==('walk' if mode=='walking' else 'drive') for p in plans for e in p.routeEvidence))
   self.assertTrue(all(p.firstLeg['minutes']>=(12 if mode=='walking' else 4) for p in plans))
   self.assertTrue(all(p.totalTravel>=(15 if mode=='walking' else 5) for p in plans))
   self.assertEqual(result.diagnostics['matrixElements'],12);self.assertEqual(budget._elements,12)
   seen[mode]={tuple(v.id for v in p.candidate.venues):p for p in plans}
  common=set(seen['driving'])&set(seen['walking']);self.assertTrue(common)
  for key in common:self.assertGreater(seen['walking'][key].totalTravel,seen['driving'][key].totalTravel)
 def test_strict_ten_minutes_applies_to_selected_mode(self):
  pref={'value':10,'unit':'minutes','mode':'strict'}
  driving,_=self.run_mode(firstTravel=pref);walking,_=self.run_mode('walking',firstTravel=pref)
  self.assertTrue(driving.provisionalPlans);self.assertFalse(walking.plans+walking.provisionalPlans+walking.explorationPlans)
  self.assertTrue(walking.canShowBeyond)
  driving,_=self.run_mode(maxLegTravel=10);walking,_=self.run_mode('walking',maxLegTravel=10)
  self.assertTrue(driving.provisionalPlans);self.assertFalse(walking.provisionalPlans+walking.explorationPlans)
 def test_flexible_ten_minutes_keeps_double_max_and_exact_excess(self):
  pref={'value':10,'unit':'minutes','mode':'flexible'}
  driving,_=self.run_mode(firstTravel=pref);walking,_=self.run_mode('walking',firstTravel=pref)
  self.assertTrue(driving.provisionalPlans);self.assertFalse(driving.explorationPlans)
  options=walking.provisionalPlans+walking.explorationPlans
  self.assertTrue(options)
  self.assertTrue(all(p.travelClassification=='outside_preference' and p.travelDeviations and 12<=p.firstLeg['minutes']<=20 for p in options))
  driving,_=self.run_mode(betweenTravel=pref);walking,_=self.run_mode('walking',betweenTravel=pref)
  self.assertTrue(driving.provisionalPlans);self.assertTrue(all(p.travelClassification=='outside_preference' for p in walking.provisionalPlans));self.assertTrue(walking.provisionalPlans)
 def test_distance_based_strict_and_flexible_use_mode_route_distance(self):
  for kind in ('strict','flexible'):
   pref={'value':.8,'unit':'miles','mode':kind}
   driving,_=self.run_mode(firstTravel=pref);walking,_=self.run_mode('walking',firstTravel=pref)
   self.assertTrue(driving.provisionalPlans)
   options=walking.provisionalPlans+walking.explorationPlans
   self.assertEqual(bool(options),kind=='flexible')
   if options:self.assertTrue(all(p.travelClassification=='outside_preference' for p in options))
 def test_missing_walk_routes_do_not_fall_back_or_become_zero(self):
  self.matrix.side_effect=lambda body:[] if body['travelMode']=='WALK' else matrix(body)
  result,_=self.run_mode('walking')
  for p in result.provisionalPlans+result.explorationPlans:
   self.assertEqual(p.travelClassification,'unverified');self.assertIsNone(p.firstLeg['minutes']);self.assertIsNone(p.totalTravel)
  context,_=option_sessions.get(result.optionsToken)
  self.assertTrue(all(leg.duration_minutes is None and leg.mode=='walk' for leg in context['routes'].values()))
  self.assertTrue(all(call.args[0]['travelMode']=='WALK' for call in self.matrix.call_args_list))
 def test_continuation_discovery_and_cache_scope_retain_mode(self):
  result,budget=self.run_mode('walking')
  context,_=option_sessions.get(result.optionsToken)
  self.assertEqual(context['routeMode'],'walk')
  before=self.matrix.call_count
  with self.assertRaises(RouteError):real_plans(context['request'].model_copy(update={'transport':TransportationMode.driving}),budget,context=context)
  self.assertEqual(self.matrix.call_count,before)
  shown=set(p.candidate.id for p in result.provisionalPlans)
  for discover in (False,True):
   next_result=more_real_plans(result.optionsToken,expand_discovery=discover)
   self.assertEqual(next_result.request.transport,'walking')
   new={p.candidate.id for p in next_result.provisionalPlans};self.assertFalse(shown&new);shown|=new
  self.assertTrue(all(call.args[0]['travelMode']=='WALK' for call in self.matrix.call_args_list))
 def test_matrix_reservation_identity_includes_mode_and_persistence_keeps_selection(self):
  from hashlib import sha256
  import json
  a=RoutePoint(id='a',place_id='a');b=RoutePoint(id='b',place_id='b')
  hashes=[sha256(json.dumps(matrix_body([a],[b],mode),sort_keys=True).encode()).hexdigest() for mode in ('drive','walk')]
  self.assertNotEqual(*hashes)
  result,_=self.run_mode('walking');registry=Receipts();issued=registry.issue(result)
  document=registry.select(SaveRequest(receipt=issued.saveReceipt,accessToken=issued.saveAccessToken,candidateIds=[p.candidate.id for p in issued.provisionalPlans],selectedId=issued.provisionalPlans[1].candidate.id))
  self.assertEqual(document.constraints.transport,'walking');self.assertEqual(document.selectedId,issued.provisionalPlans[1].candidate.id)
  self.assertNotIn('duration_seconds',document.model_dump_json());self.assertNotIn('Fixture food venue',document.model_dump_json())
