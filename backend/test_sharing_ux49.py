"""Shared-view admission and contact fixtures, no live provider sends."""
import os
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from unittest.mock import patch,MagicMock
from uuid import uuid4
from backend.test_real_planning import ENV
from backend.saved_refresh import RefreshSessions,RefreshRequest,fetch_saved_details,REFRESH_MASK,CONTACT_REFRESH_MASK
from backend.provider_budget import ProviderBudget
from backend.venue_details import contact_links
from backend.places import DiscoveryError

class SharedViews(unittest.TestCase):
 def setUp(self):
  self.directory=TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.clock=[1000000.0]
  env=ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1','WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.directory.name+'/ledger'}
  self.doc={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'one'},{'reference':'two'}]},{'candidateId':'alternative','stops':[{'reference':'never'}]}]}
  for p in (patch.dict(os.environ,env,clear=True),patch('requests.Session.send',side_effect=AssertionError('Google forbidden')),patch('backend.saved_refresh.reopen',return_value=self.doc),patch('backend.provider_budget.monotonic',side_effect=lambda:self.clock[0]),patch('backend.saved_refresh.monotonic',side_effect=lambda:self.clock[0]),patch('backend.development_cost.time',side_effect=lambda:self.clock[0])):
   p.start();self.addCleanup(p.stop)
  self.calls=[]
  def details(identity,**kwargs):
   from backend.development_cost import dispatch
   dispatch('details',1);self.calls.append(identity)
   return {'name':'Invented '+identity,'website':None}
  self.provider=patch('backend.saved_refresh.fetch_saved_details',side_effect=details);self.fetch=self.provider.start();self.addCleanup(self.provider.stop)
  self.sessions=RefreshSessions();self.budget=ProviderBudget()
 def open(self,key='A',uid=None):return self.sessions.refresh(RefreshRequest(accessToken=key*43,candidateId='chosen',refreshId=uid or uuid4()),self.budget)
 def test_ten_viewers_same_link_receive_identities_across_shared_windows(self):
  for viewer in range(10):
   result=self.open();self.assertEqual([v['name'] for v in result['venues'].values()],['Invented one','Invented two'])
   self.clock[0]+=13
  self.assertEqual(len(self.calls),20);self.assertEqual(self.budget.cost.snapshot()['estimatedDayGrossUsd'],.4)
  self.assertTrue(all(isinstance(v,float) for v in self.sessions.entries.values())) # replay metadata only
  self.assertNotIn('Invented',str(self.sessions.entries));self.assertNotIn('A'*43,str(self.sessions.entries))
 def test_ten_immediate_opens_hit_shared_minute_not_capability(self):
  for _ in range(5):self.assertEqual(len(self.open()['venues']),2)
  result=self.open()['venues']['one'];self.assertEqual(result['reason'],'local_minute');self.assertEqual(len(self.calls),10)
  self.clock[0]+=61
  self.assertIn('name',self.open()['venues']['one'])
 def test_ten_concurrent_opens_are_bounded_and_have_no_cross_response_cache(self):
  started=threading.Event();release=threading.Event();original=self.fetch.side_effect
  def slow(identity,**kwargs):started.set();release.wait(3);return original(identity,**kwargs)
  self.fetch.side_effect=slow
  with ThreadPoolExecutor(max_workers=10) as pool:
   first=pool.submit(self.open);self.assertTrue(started.wait(2))
   other=[pool.submit(self.open) for _ in range(9)]
   blocked=[f.result(timeout=2) for f in other]
   self.assertTrue(all(r['venues']['one']['reason']=='concurrent_request' for r in blocked))
   release.set();result=first.result(timeout=3)
  self.assertEqual(len(self.calls),2);self.assertEqual(result['venues']['one']['name'],'Invented one')
 def test_two_links_concurrent_use_their_own_verified_references(self):
  def document(request):return {**self.doc,'itineraries':[{'candidateId':'chosen','stops':[{'reference':('alpha' if request.accessToken.startswith('A') else 'beta')}]}]}
  with patch('backend.saved_refresh.reopen',side_effect=document),ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(self.open,['A','B']))
  for key,result in zip(('alpha','beta'),results):
   self.assertEqual(set(result['venues']),{key})
   if result['venues'][key]['status']=='refreshed':self.assertEqual(result['venues'][key]['name'],'Invented '+key)
 def test_restart_preserves_shared_ledger_and_old_link(self):
  for _ in range(5):self.open()
  self.sessions=RefreshSessions();self.budget=ProviderBudget()
  self.assertEqual(self.open()['venues']['one']['reason'],'local_shared_minute')
  self.clock[0]+=61
  self.assertEqual(self.open()['venues']['two']['name'],'Invented two')
 def test_uuid_replay_and_four_selected_stop_maximum(self):
  uid=uuid4();self.open(uid=uid);self.open(uid=uid);self.assertEqual(len(self.calls),2)
  self.doc['itineraries'][0]['stops']=[{'reference':str(i)} for i in range(4)]
  self.assertEqual(len(self.open()['venues']),4);self.assertEqual(len(self.calls),6)
  self.doc['itineraries'][0]['stops'].append({'reference':'excess'})
  from backend.saved_plans import PersistenceError
  with self.assertRaises(PersistenceError):self.open()
 def test_provider_failure_after_first_stop_preserves_partial_and_charges_attempt(self):
  original=self.fetch.side_effect
  def failure(identity,**kwargs):
   if identity=='two':raise DiscoveryError('authentication','sensitive provider message')
   return original(identity,**kwargs)
  self.fetch.side_effect=failure
  result=self.open();self.assertEqual(result['venues']['one']['name'],'Invented one');self.assertEqual(result['venues']['two']['reason'],'provider_authentication')
  self.assertEqual(self.budget._requests,2);self.assertNotIn('sensitive',str(result))
 def test_cloud_daily_quota_does_not_expire_saved_access(self):
  error=DiscoveryError('quota','private');error.diagnostics={'quotaBoundary':'daily'};self.fetch.side_effect=error
  result=self.open();self.assertEqual(result['venues']['one']['reason'],'cloud_daily_quota');self.assertFalse(result['venues']['one']['retryable'])
  from backend.saved_plans import PersistenceError
  with patch('backend.saved_refresh.reopen',side_effect=PersistenceError(404)):
   with self.assertRaises(PersistenceError):self.open()

class WebsiteTests(unittest.TestCase):
 def test_phone_website_independent_and_safe(self):
  for phone,website in [(None,None),('+1 202 555 0100',None),(None,'https://example.com'),('+1 202 555 0100','https://example.com'),(None,'http://example.com')]:
   with self.subTest(phone=bool(phone),website=website):
    result=contact_links({'id':'one','internationalPhoneNumber':phone,'websiteUri':website},'one')
    self.assertEqual(result['phone'],phone);self.assertEqual(result['website'],website)
  for website in ('javascript:alert(1)','data:text/html,x','https://u:p@example.com','https://example.com/\nprivate','https://example.com:bad','https://','https://exa mple.com','https://example.com/\x7f'):
   self.assertIsNone(contact_links({'id':'one','websiteUri':website},'one')['website'])
 def test_actual_refresh_normalization_and_masks_pro_then_enterprise(self):
  session=MagicMock();session.__enter__.return_value=session;session.get.return_value.status_code=200
  for website in ('https://example.com','http://example.com',None):
   session.get.return_value.json.return_value={'id':'one','displayName':{'text':'Invented venue'},'formattedAddress':'Invented address','internationalPhoneNumber':'+1 202 555 0100','websiteUri':website,'attributions':[]}
   with patch.dict(os.environ,ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1'},clear=True),patch('requests.Session',return_value=session),patch('backend.places_transport.access_token',return_value='never logged'):
    pro=fetch_saved_details('one');self.assertNotIn('website',pro);self.assertEqual(session.get.call_args.kwargs['headers']['X-Goog-FieldMask'],REFRESH_MASK)
    enterprise=fetch_saved_details('one',include_contacts=True);self.assertEqual(enterprise['website'],website);self.assertTrue(enterprise['phone']);self.assertEqual(session.get.call_args.kwargs['headers']['X-Goog-FieldMask'],CONTACT_REFRESH_MASK)
 def test_registry_matches_canonical_model_without_second_list(self):
  from pathlib import Path
  from backend.models import ActivityType,EVENT_ACTIVITIES
  registry=json.loads((Path(__file__).parent.parent/'data/mock-venues.json').read_text())['catalog']
  self.assertEqual(set(registry),{a.value for a in ActivityType})
  self.assertEqual({k for k,v in registry.items() if 'eventStart' in v},{a.value for a in EVENT_ACTIVITIES})
