"""Owner-authorized hours masks, dated filtering and transient saved enrichment."""
import os
import unittest
from datetime import datetime,timedelta,timezone,date
from unittest.mock import patch,MagicMock
from tempfile import TemporaryDirectory
from uuid import uuid4
from backend.test_real_planning import ENV,outing
from backend.hours_fixtures49 import fixture_hours
from backend.venue_normalization import normalize_google_place
from backend.planning_hours import venue_hours
from backend.search_fields import search_mask,HOURS_FIELDS,enterprise_search
from backend.places import FIELD_MASK,DiscoveryError
from backend.provider_budget import ProviderBudget,ProviderSettings,ProviderLimitError
from backend.real_planning import real_plans
from backend.real_fixtures import search_fixture
from backend.travel_mode_fixtures import matrix
from backend.saved_refresh import fetch_saved_details,RefreshRequest,RefreshSessions,REFRESH_MASK
from backend.saved_plans import Receipts,SaveRequest
from backend.test_feasibility import stop,period,NOW

class SearchHours(unittest.TestCase):
 def setUp(self):
  for guard in (patch.dict(os.environ,ENV|{'WHERETO_HOURS_DEV':'1','WHERETO_CONTACT_DETAILS_DEV':'1','WHERETO_SAVED_HOURS_DEV':'1'},clear=True),patch('requests.Session.send',side_effect=AssertionError('No live Google'))):guard.start();self.addCleanup(guard.stop)
 def test_mask_and_accounting_without_ratings_and_lookup_stays_pro(self):
  self.assertEqual(search_mask(FIELD_MASK),FIELD_MASK+','+HOURS_FIELDS);self.assertTrue(enterprise_search())
  with TemporaryDirectory() as folder,patch.dict(os.environ,{'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':folder+'/ledger'}):
   budget=ProviderBudget()
   with budget.outing().reserve('search','hours'):pass
   with budget.outing().reserve('lookup','origin'):pass
   self.assertEqual(budget.cost.snapshot()['estimatedDayGrossUsd'],.067)
  with patch.dict(os.environ,{'WHERETO_RATINGS_DEV':'1'}):self.assertIn('places.rating',search_mask(FIELD_MASK));self.assertEqual(search_mask(FIELD_MASK).count('places.currentOpeningHours'),1)
  with patch.dict(os.environ,{'NODE_ENV':'production'}):self.assertEqual(search_mask(FIELD_MASK),FIELD_MASK)
 def test_transport_exact_mask_and_no_retry(self):
  response=MagicMock(status_code=200);response.json.return_value={'places':[]}
  with patch('backend.places_transport.access_token',return_value='offline'),patch('requests.Session.post',return_value=response) as send:
   from backend.places_transport import text_search
   text_search({'textQuery':'invented cafe'})
   self.assertEqual(send.call_count,1);self.assertEqual(send.call_args.kwargs['headers']['X-Goog-FieldMask'],search_mask(FIELD_MASK)+',places.containingPlaces')
  with patch.dict(os.environ,{'WHERETO_HOURS_DEV':'0'}):
   with self.assertRaises(DiscoveryError):text_search({},field_mask=FIELD_MASK+','+HOURS_FIELDS)
 def test_closed_window_default_window_and_partial_overlap(self):
  fact=stop(periods=[period(opening=9,closing=11)]).venue
  for start,end,expected in [(None,None,'unverified'),(12*60,15*60,'closed'),(10*60,12*60,'unverified')]:
   view=venue_hours(fact,date(2026,10,24),start=start,end=end,evaluated_at=NOW)
   self.assertEqual(view['status'],expected);self.assertEqual(view['periods'],[{'start':540,'end':660}])
  exact=venue_hours(fact,date(2026,10,24),evaluated_at=NOW,arrival='2026-10-24T14:00:00Z',departure='2026-10-24T15:00:00Z')
  self.assertEqual(exact['status'],'open')
 def test_weekly_indicative_future_timezone_and_missing_evidence(self):
  raw={'id':'test','displayName':{'text':'Invented'},**fixture_hours(now=NOW)}
  fact=normalize_google_place(raw,'food',observed_at=NOW)
  view=venue_hours(fact,date(2026,11,7),evaluated_at=NOW)
  self.assertEqual(view['basis'],'unavailable');self.assertEqual(view['status'],'unverified');self.assertTrue(view['typicalPeriods'])
  fact.timeZone=None;view=venue_hours(fact,date(2026,10,24),evaluated_at=NOW);self.assertEqual(view['status'],'unverified')
 def test_midnight_24_hour_and_sparse_protobuf_points(self):
  fact=stop(periods=[period(opening=22,end='2026-10-25',closing=3)]).venue
  v=venue_hours(fact,date(2026,10,24),evaluated_at=NOW);self.assertEqual(v['periods'],[{'start':1320,'end':1620}])
  fact=normalize_google_place({'id':'all','displayName':{'text':'All day'},'timeZone':{'id':'America/New_York'},'currentOpeningHours':{'periods':[{'open':{'day':0}}]}},'food',observed_at=NOW)
  self.assertEqual(venue_hours(fact,date(2026,10,24),evaluated_at=NOW)['periods'],[{'start':0,'end':1440}])
  from backend.venue_normalization import NormalizationError
  with self.assertRaises(NormalizationError):normalize_google_place({'id':'empty','displayName':{'text':'Invented'},'currentOpeningHours':{'periods':[{'open':{}}]}},'food',observed_at=NOW)
 def test_planner_excludes_closed_candidates_without_extra_search_or_details(self):
  now=datetime.now(timezone.utc)
  def search(body,**kwargs):
   data=search_fixture(body,**kwargs)
   for index,p in enumerate(data.get('places',[])):p.update(fixture_hours(now=now,closed=index==0))
   return data
  with patch('backend.places_transport.text_search',side_effect=search) as searched,patch('backend.routes_transport.compute_matrix',side_effect=matrix):
   request=outing().model_copy(update={'date':now.date()+timedelta(days=1)})
   budget=ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3))
   result=real_plans(request,budget)
   self.assertTrue(result.provisionalPlans);self.assertEqual(searched.call_count,2);self.assertGreater(result.diagnostics['hoursExcludedCandidates'],0)
   for p in result.provisionalPlans:
    for s in p.stops:self.assertEqual(s.venue.hoursEvidence.status,'unverified');self.assertTrue(s.venue.hoursEvidence.periods)
   issued=Receipts();r=issued.issue(result)
   document=issued.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[p.candidate.id for p in r.provisionalPlans],selectedId=r.provisionalPlans[0].candidate.id))
   self.assertNotIn('hoursEvidence',document.model_dump_json());self.assertNotIn('OpeningHours',document.model_dump_json())
 def test_saved_pro_stays_pro_and_manual_hours_is_independently_gated(self):
  response=MagicMock(status_code=200);response.json.return_value={'id':'test','displayName':{'text':'Invented'},'formattedAddress':'Invented address',**fixture_hours()}
  with patch('backend.places_transport.access_token',return_value='offline'),patch('requests.Session.get',return_value=response) as sent:
   fetch_saved_details('test');self.assertEqual(sent.call_args.kwargs['headers']['X-Goog-FieldMask'],REFRESH_MASK)
   details=fetch_saved_details('test',include_hours=True,outing_date=datetime.now().date().isoformat())
   self.assertIn('hoursEvidence',details);self.assertNotIn('websiteUri',sent.call_args.kwargs['headers']['X-Goog-FieldMask'])
   self.assertIn('currentOpeningHours',sent.call_args.kwargs['headers']['X-Goog-FieldMask'])
   with patch.dict(os.environ,{'WHERETO_SAVED_HOURS_DEV':'0'}):
    with self.assertRaises(DiscoveryError):fetch_saved_details('test',include_hours=True)
 def test_ten_consecutive_actions_respect_shared_windows_and_no_quota_bypass(self):
  from backend.test_sharing_ux49 import SharedViews
  fixture=SharedViews();fixture.setUp()
  try:
   for i in range(10):
    result=fixture.open();self.assertTrue(all(v.get('name') for v in result['venues'].values()));fixture.clock[0]+=13
   self.assertEqual(len(fixture.calls),20)
   # Ten independent search actions across actual simulated admission windows.
   for i in range(10):
    fixture.clock[0]+=7
    with fixture.budget.outing().reserve('search',str(i)):pass
   self.assertEqual(fixture.budget.cost.snapshot()['estimatedDayGrossUsd'],.66) # 20 Pro Details × $0.017 + 10 Pro searches × $0.032
  finally:fixture.doCleanups()

 def test_saved_manual_hours_is_selected_bounded_replay_safe_and_uses_saved_window(self):
  from backend.test_sharing_ux49 import SharedViews
  fixture=SharedViews();fixture.setUp()
  try:
   fixture.doc['constraints']={'date':'2026-11-07','startTime':600,'endTime':1440,'explicitStart':False,'explicitEnd':False,'calendarTimezone':'America/New_York'}
   for i,stop_value in enumerate(fixture.doc['itineraries'][0]['stops']):stop_value['activity']='food' if i==0 else 'coffee'
   fixture.open()
   with patch.dict(os.environ,{'WHERETO_SAVED_HOURS_DEV':'1'}):
    request=RefreshRequest(accessToken='A'*43,candidateId='chosen',refreshId=uuid4(),includeHours=True)
    result=fixture.sessions.refresh(request,fixture.budget)
    self.assertEqual(len(result['venues']),2);self.assertEqual(fixture.fetch.call_args.kwargs['outing_date'],'2026-11-07')
    self.assertIsNone(fixture.fetch.call_args.kwargs['window_start']);self.assertIsNone(fixture.fetch.call_args.kwargs['window_end'])
    self.assertTrue(fixture.fetch.call_args.kwargs['include_hours']);self.assertFalse(fixture.fetch.call_args.kwargs['include_contacts'])
    fixture.sessions.refresh(request,fixture.budget);self.assertEqual(len(fixture.calls),4)
    fixture.doc['itineraries'][0]['stops']*=3
    from backend.saved_plans import PersistenceError
    with self.assertRaises(PersistenceError):fixture.sessions.refresh(request,fixture.budget)
  finally:fixture.doCleanups()
 def test_timezone_mismatch_dst_and_bad_coverage_never_prove_open_or_closed(self):
  fact=stop(periods=[]).venue
  self.assertEqual(venue_hours(fact,date(2026,10,24),calendar_timezone='Asia/Kolkata',evaluated_at=NOW)['status'],'unverified')
  fact=stop(periods=[period(start='2027-01-01',end='2027-01-01')]).venue
  self.assertEqual(venue_hours(fact,date(2026,10,24),evaluated_at=NOW)['status'],'unverified')
  for day in ('2026-03-08','2026-11-01'):
   instant=datetime.fromisoformat(day+'T04:00:00Z')
   fact=normalize_google_place({'id':'dst','displayName':{'text':'Invented'},'timeZone':{'id':'America/New_York'},'currentOpeningHours':{'periods':[{'open':{'day':0,'hour':0,'minute':0}}]}},'food',observed_at=instant)
   view=venue_hours(fact,date.fromisoformat(day),evaluated_at=instant)
   self.assertEqual(view['periods'],[{'start':0,'end':1440}]);self.assertEqual(view['status'],'unverified')
