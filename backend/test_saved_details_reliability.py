"""Isolated admission tests: never Google sends or owner ledger writes."""
import os
import unittest
from uuid import uuid4
from unittest.mock import patch
from tempfile import TemporaryDirectory
from backend.provider_budget import ProviderBudget,ProviderLimitError
from backend.saved_refresh import RefreshSessions,RefreshRequest,refresh_issue,automatic_details_enabled
from backend.places import DiscoveryError
from backend.test_real_planning import ENV

class RefreshReliability(unittest.TestCase):
 def setUp(self):
  self.env=patch.dict(os.environ,ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1'},clear=True);self.env.start();self.addCleanup(self.env.stop)
  self.document={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'one'},{'reference':'two'}]}]}
  self.read=patch('backend.saved_refresh.reopen',return_value=self.document);self.read.start();self.addCleanup(self.read.stop)
  self.fetch=patch('backend.saved_refresh.fetch_saved_details',return_value={'name':'Invented venue'});self.send=self.fetch.start();self.addCleanup(self.fetch.stop)
  self.sessions=RefreshSessions();self.budget=ProviderBudget()
 def action(self,key='A',refresh_id=None):return self.sessions.refresh(RefreshRequest(accessToken=key*43,candidateId='chosen',refreshId=refresh_id or uuid4()),self.budget)
 def test_three_independent_plans_and_older_link(self):
  for key in ('A','B','C','A'):
   self.assertTrue(all(v['status']=='refreshed' for v in self.action(key)['venues'].values()))
  self.assertEqual(self.send.call_count,8)
 def test_fourth_viewer_has_fresh_action_allowance(self):
  for _ in range(4):
   self.assertTrue(all(v['status']=='refreshed' for v in self.action()['venues'].values()))
  self.assertEqual(self.send.call_count,8)
 def test_shared_minute_not_new_capability_failure_and_no_charge_before_admission(self):
  for key in 'ABCDE':self.action(key)
  blocked=self.action('F')['venues']['one']
  self.assertEqual(blocked['reason'],'local_minute');self.assertLessEqual(blocked['retryAfterSeconds'],60)
  self.assertEqual(self.budget._requests,10)
  self.assertEqual(len(self.sessions.entries),5) # Rejected actions leave no replay record.
  with patch('backend.provider_budget.monotonic',return_value=10**12):
   self.assertTrue(all(v['status']=='refreshed' for v in self.action('F')['venues'].values()))
 def test_uuid_replay_multitab_and_failed_dispatch_remains_charged(self):
  uid=uuid4();self.send.side_effect=DiscoveryError('provider','secret response')
  first=self.action(refresh_id=uid);self.action(refresh_id=uid)
  self.assertEqual(self.send.call_count,1);self.assertEqual(first['diagnostics']['placesDetailsRequests'],1)
  self.send.side_effect=None
  self.assertEqual(self.action()['venues']['one']['status'],'refreshed')
 def test_pre_admission_uuid_can_be_used_after_limit_clears(self):
  self.budget._active=1;uid=uuid4()
  self.assertEqual(self.action(refresh_id=uid)['venues']['one']['reason'],'concurrent_request')
  self.budget._active=0
  self.assertEqual(self.action(refresh_id=uid)['venues']['one']['status'],'refreshed')
 def test_session_expiry_resets_capability_not_shared_budget(self):
  for _ in range(3):self.action()
  with patch('backend.saved_refresh.monotonic',return_value=10**12):
   self.assertEqual(self.action()['venues']['one']['status'],'refreshed')
  self.assertEqual(self.budget._requests,8)
 def test_database_failure_does_not_consume_provider_allowance(self):
  from backend.saved_plans import PersistenceError
  with patch('backend.saved_refresh.reopen',side_effect=PersistenceError(503)):
   with self.assertRaises(PersistenceError):self.action()
  self.assertEqual(self.budget._requests,0);self.send.assert_not_called()
 def test_partial_success_retains_specific_provider_reason(self):
  error=DiscoveryError('quota','sensitive');error.diagnostics={'quotaBoundary':'daily'}
  self.send.side_effect=[{'name':'First'},error]
  data=self.action()['venues'];self.assertEqual(data['one']['name'],'First');self.assertEqual(data['two']['reason'],'cloud_daily_quota');self.assertFalse(data['two']['retryable']);self.assertNotIn('sensitive',str(data))
 def test_cloud_auth_rate_and_place_failure_categories(self):
  for code,reason in [('authentication','provider_authentication'),('permission','provider_authorization'),('not_found','place_unavailable'),('timeout','provider_timeout')]:
   self.assertEqual(refresh_issue(DiscoveryError(code,'secret'))['reason'],reason)
  for boundary in ('daily','minute','unknown'):
   error=DiscoveryError('quota','secret');error.diagnostics={'quotaBoundary':boundary}
   self.assertEqual(refresh_issue(error)['reason'],'cloud_'+boundary+'_quota');self.assertNotIn('retryAfterSeconds',refresh_issue(error))
 def test_persistent_minute_survives_backend_restart(self):
  from backend.development_cost import DevelopmentCost,AccountingError
  with TemporaryDirectory() as directory,patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':directory+'/ledger','WHERETO_EXPLORATION_DEV':'1'}):
   cost=DevelopmentCost(enforce_limit=False)
   for _ in range(10):
    with cost.reserve({'details':1}):pass
   restarted=DevelopmentCost(enforce_limit=False)
   with self.assertRaises(AccountingError) as caught:
    with restarted.reserve({'details':1}):pass
   self.assertEqual(caught.exception.reason,'local_shared_minute');self.assertGreater(caught.exception.retry_after,0)
   self.assertEqual(restarted.snapshot()['estimatedDayGrossUsd'],.2)
 def test_daily_application_guard_remains_shared_and_failed_admission_uncharged(self):
  from backend.development_cost import DevelopmentCost,AccountingError
  with TemporaryDirectory() as directory,patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':directory+'/ledger','WHERETO_DEV_DAILY_USD':'0.02'}):
   cost=DevelopmentCost()
   with cost.reserve({'details':1}):pass
   with self.assertRaises(AccountingError):
    with DevelopmentCost().reserve({'details':1}):pass
   self.assertEqual(cost.snapshot()['estimatedDayGrossUsd'],.02)
 def test_long_permitted_reference_has_bounded_accounting_identity(self):
  self.document['itineraries'][0]['stops']=[{'reference':'A'*200}]
  self.assertEqual(self.action()['venues']['A'*200]['status'],'refreshed')
 def test_auto_open_separately_authorized_default_off_production_off(self):
  self.assertFalse(automatic_details_enabled())
  with patch.dict(os.environ,{'WHERETO_SAVED_AUTO_DETAILS_DEV':'1'}):
   self.assertTrue(automatic_details_enabled())
   with patch.dict(os.environ,{'NODE_ENV':'production'}):self.assertFalse(automatic_details_enabled())

class ReadinessTests(unittest.TestCase):
 def test_one_local_preparation_no_health_block_and_no_google(self):
  from backend import ai_readiness as readiness
  with patch.dict(os.environ,ENV|{'WHERETO_AI_WARMUP_DEV':'1'},clear=True),patch.object(readiness,'_started',False),patch('backend.ai_readiness.Thread') as thread:
   readiness.start();readiness.start();self.assertEqual(thread.call_count,1)
   self.assertTrue(thread.call_args.kwargs['daemon'])
   with patch('backend.ai.ollama.OllamaProvider.interpret') as ai,patch('requests.Session.send',side_effect=AssertionError('Google forbidden')):
    thread.call_args.kwargs['target']();ai.assert_called_once_with('Coffee in Jersey City')
 def test_mock_ci_remote_no_warmup(self):
  from backend import ai_readiness as readiness
  for extra in ({'VENUE_DATA_MODE':'mock'},{'CI':'1'},{'AI_BASE_URL':'https://example.com'}):
   with patch.dict(os.environ,ENV|{'WHERETO_AI_WARMUP_DEV':'1'}|extra,clear=True),patch.object(readiness,'_started',False),patch('backend.ai_readiness.Thread') as thread:
    readiness.start();thread.assert_not_called()

 def test_invalid_ai_config_does_not_break_health_preparation(self):
  from backend import ai_readiness as readiness
  for extra in ({'AI_TIMEOUT_SECONDS':'invalid'},{'AI_BASE_URL':'http://[invalid'}):
   with patch.dict(os.environ,ENV|{'WHERETO_AI_WARMUP_DEV':'1'}|extra,clear=True),patch('backend.ai_readiness.Thread') as thread:
    readiness.start();thread.assert_not_called();self.assertEqual(readiness.snapshot()['state'],'unavailable')
