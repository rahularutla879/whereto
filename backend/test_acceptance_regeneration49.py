"""Offline regeneration with shared admission, new immutable contexts and no network."""
from backend.testing_clock import calendar_clock
import json
import os
import unittest
from unittest.mock import patch
from backend import main
from backend.models import RankingResult
from backend.provider_budget import ProviderBudget,ProviderSettings
from backend.real_planning import real_plans,more_real_plans,PlannerInput
from backend.test_real_planning import ENV,outing
from backend.real_fixtures import search_fixture
from backend.travel_mode_fixtures import matrix
from backend.failures import provider_code
from backend.routes import RouteError
from backend.provider_budget import ProviderLimitError

class Regeneration(unittest.TestCase):
 def setUp(self):
  self.enterContext(calendar_clock())
  self.clock=1000
  for item in (patch.dict(os.environ,ENV,clear=True),patch('requests.Session.send',side_effect=AssertionError('No live Google')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix),patch('backend.provider_budget.monotonic',side_effect=lambda:self.clock)):
   item.start();self.addCleanup(item.stop)
  self.budget=ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3))
 def plan(self,**changes):
  # Separate deliberate actions in a simulated clock; never alter an owner ledger.
  self.clock+=61
  overrides={k:changes.pop(k) for k in ('location','date') if k in changes}
  request=outing(**changes)
  request=PlannerInput.model_validate({**request.model_dump(), 'startingLocation':request.startingLocation.model_dump(),**overrides})
  result=real_plans(request,self.budget)
  self.assertEqual(result.request.transport,request.transport)
  self.assertEqual(result.request.firstTravel,request.firstTravel)
  self.assertEqual(result.request.date,request.date)
  self.assertEqual(result.request.location,request.location)
  for p in result.provisionalPlans:
   for e in p.routeEvidence:self.assertEqual(e['route']['mode'],'walk' if request.transport=='walking' else 'drive')
  return result
 def test_repeated_preference_transitions_create_new_sessions_and_route_evidence(self):
  sessions=set()
  for mode in ('driving','walking'):
   for flexibility,amount in [('strict',10),('flexible',10),('strict',20),('flexible',20),('strict',None),('strict',10)]:
    with self.subTest(mode=mode,flexibility=flexibility,amount=amount):
     r=self.plan(transport=mode,firstTravel=None if amount is None else dict(value=amount,unit='minutes',mode=flexibility))
     if r.optionsToken:
      self.assertNotIn(r.optionsToken,sessions);sessions.add(r.optionsToken)
     if mode=='walking' and flexibility=='strict' and amount==10:self.assertFalse(r.provisionalPlans);self.assertTrue(r.canShowBeyond)
  self.assertGreater(len(sessions),5)
 def test_total_limit_and_date_edits_are_new_requests(self):
  for changes in ({},{'travel':3},{'travel':20},{'date':'2026-11-08'},{'betweenTravel':{'value':10,'unit':'minutes','mode':'flexible'}}):
   with self.subTest(changes=changes):self.plan(**changes)
 def test_regeneration_after_recombination_discovery_and_exception_view(self):
  for explore,beyond in [(False,False),(True,False),(False,True)]:
   initial=self.plan()
   self.clock+=61
   more_real_plans(initial.optionsToken,expand_discovery=explore,show_beyond=beyond)
   fresh=self.plan(transport='walking',firstTravel={'value':10,'unit':'minutes','mode':'flexible'})
   self.assertNotEqual(initial.optionsToken,fresh.optionsToken);self.assertTrue(fresh.provisionalPlans+fresh.explorationPlans)
 def test_shared_limit_reproduces_identically_after_refresh_and_recovers_only_after_window(self):
  self.budget._search_window=[self.clock]*10
  request=outing(firstTravel={'value':10,'unit':'minutes','mode':'flexible'})
  with patch.object(main,'provider_budget',self.budget):
   for action in ('regenerate','same payload after refresh'):
    with self.subTest(action=action):
     response=main.generate_plan(request);body=json.loads(response.body)
     self.assertEqual(response.status_code,429);self.assertEqual(body['code'],'provider_local_rate_limit')
     self.assertNotIn('service could not complete',body['message']);self.assertEqual(self.budget._requests,0)
   self.clock+=61
   self.assertIsInstance(main.generate_plan(request),RankingResult)
 def test_true_provider_failure_stays_distinct_and_is_not_retried(self):
  with patch.object(main,'provider_budget',self.budget),patch('backend.places_transport.text_search',side_effect=RouteError('provider','Synthetic service failure')) as call:
   response=main.generate_plan(outing());body=json.loads(response.body)
   self.assertEqual(body['code'],'provider_service_error');self.assertEqual(call.call_count,1)
 def test_local_admission_cloud_and_service_categories_are_distinct(self):
  self.assertEqual(provider_code(ProviderLimitError('safe',reason='local_shared_minute')),'provider_local_rate_limit')
  self.assertEqual(provider_code(ProviderLimitError('safe')),'provider_local_admission')
  self.assertEqual(provider_code(RouteError('quota','safe')),'provider_quota_rejected')
  self.assertEqual(provider_code(RouteError('provider','safe')),'provider_service_error')

 def test_oversized_minute_batch_has_no_invented_reset_time(self):
  with self.assertRaises(ProviderLimitError) as caught:
   with self.budget.outing().reserve("matrix","oversized",origins=13,destinations=13):self.fail("No dispatch")
  self.assertEqual(caught.exception.reason,"batch_limit");self.assertIsNone(caught.exception.retry_after)
  self.assertEqual(provider_code(caught.exception),"provider_local_admission")
