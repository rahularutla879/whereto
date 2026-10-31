import os
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
import unittest
from unittest.mock import patch
from backend.retail import intent,verdict
from backend.venue_normalization import normalize_google_place
from backend.refinement_fixtures import place,search_fixture
from backend.places import PlacesDiscovery,DiscoveryRequest,SearchArea,DiscoveryError
from backend.provider_budget import ProviderBudget,ProviderLimitError
from backend.real_planning import real_plans,PlannerInput,more_real_plans
from backend.real_fixtures import matrix_fixture
from backend.test_real_planning import ENV

class RetailTests(unittest.TestCase):
 def setUp(self):
  for item in (patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('Live Google forbidden')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture)):
   value=item.start();self.addCleanup(item.stop)
   if getattr(item,'attribute',None)=='text_search':self.search=value
 def venue(self,name='Zara',kind='clothing_store',parent=None):return normalize_google_place(place('fixture',name,kind,parent), 'custom:zara outlet')
 def test_brand_format_matrix(self):
  cases=[('zara outlet','Zara',True),('zara outlet','Zara Outlet',True),('zara outlet','Zara Flagship',True),('only zara outlets','Zara',False),('only zara outlets','Zara Outlet',True),('zara outlet','Zara inspired boutique',False),('zara outlet','Zaragoza',False),('zara outlet','Other brand',False)]
  for phrase,name,expected in cases:
   with self.subTest(phrase=phrase,name=name):self.assertEqual(verdict(self.venue(name),intent(phrase))[0],expected)
 def test_brand_evidence_and_tenant_are_required(self):
  self.assertFalse(verdict(self.venue('Zara','establishment').model_copy(update={'providerTypes':['establishment']}),intent('zara store'))[0])
  self.assertFalse(verdict(self.venue('Zara','shopping_mall'),intent('zara store'))[0])
  self.assertFalse(verdict(self.venue(parent='mall'),intent('zara store inside Newport Centre'))[0])
 def test_other_brands_not_hardcoded(self):
  for brand in ('Nike','Adidas','Apple','Sephora','Independent Novel Retailer'):
   self.assertTrue(verdict(self.venue(brand),intent(brand+' store'))[0])
 def test_normalization_preserves_retail_constraints(self):
  from backend.interpretation import activity_category
  for phrase in ('Zara outlet','Only Zara outlets','Nike store','shopping malls','electronics stores','bookstores','clothing stores'):
   self.assertEqual(activity_category(phrase),'custom:'+phrase.casefold())
 def test_store_and_mall_discovery_and_verified_membership(self):
  for activity in ('custom:zara outlet','custom:shopping malls','custom:mall with zara','custom:mall with nike and adidas','custom:zara store inside synthetic shopping mall'):
   with self.subTest(activity=activity):
    result=PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity=activity,destination=SearchArea(name='Jersey City')))
    self.assertTrue(result.venues,result.diagnostics)
    if activity=='custom:zara outlet':self.assertEqual({v.facts.name for v in result.venues},{'Zara','Zara Outlet'})
    if activity=='custom:mall with zara':self.assertTrue(all(v.facts.id.startswith('Refine49_') for v in result.venues))
 def test_no_membership_inferred_from_proximity(self):
  def without_parents(body,**kwargs):return {'places':[{**p,'containingPlaces':[]} for p in search_fixture(body,**kwargs)['places']]}
  self.search.side_effect=without_parents
  result=PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='custom:mall with zara',destination=SearchArea(name='Jersey City')))
  self.assertFalse(result.venues)
 def test_single_retail_and_multi_stop_preserve_activities(self):
  for activities in (['custom:zara outlet'],['custom:shopping malls','coffee'],['custom:clothing stores','food'],['custom:nike stores in same mall','custom:adidas stores in same mall']):
   with self.subTest(activities=activities):
    result=real_plans(PlannerInput(activities=activities,location='Jersey City',date='2026-11-14',planningMode='surprise'),ProviderBudget())
    self.assertTrue(result.provisionalPlans,result.message)
    self.assertTrue(all([s.venue.activity.value for s in p.stops]==activities for p in result.provisionalPlans))
 def test_different_malls_cannot_satisfy_shared_mall(self):
  def different(body,**kwargs):
   data=search_fixture(body,**kwargs)
   if 'adidas' in body['textQuery'].casefold():
    data={'places':[{**p,'containingPlaces':[{'id':'unknown-other-mall','name':'places/unknown-other-mall'}]} for p in data['places']]}
   return data
  self.search.side_effect=different
  result=real_plans(PlannerInput(activities=['custom:nike stores in same mall','custom:adidas stores in same mall'],location='Jersey City',date='2026-11-14',planningMode='surprise'),ProviderBudget())
  self.assertFalse(result.provisionalPlans)
 def test_strict_geography_and_first_travel(self):
  outside=place('outside','Zara',city='Manhattan',lat=40.76)
  self.search.return_value={'places':[outside]};self.search.side_effect=None
  self.assertFalse(PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='custom:zara outlet',destination=SearchArea(name='Jersey City'))).venues)
  nearby=PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='custom:zara outlet',destination=SearchArea(name='Jersey City',enforce_name=False,anchor_verified=True,coordinates={'latitude':40.73,'longitude':-74.05},radius_m=10000.0)))
  self.assertTrue(nearby.venues)
  self.assertIn('Manhattan',nearby.venues[0].facts.address)
 def test_brand_fallback_one_bounded_search(self):
  def preferred_empty(body,**kwargs):return {'places':[]} if 'outlets' in body['textQuery'] else search_fixture(body,**kwargs)
  self.search.side_effect=preferred_empty
  outing=ProviderBudget().outing()
  result=PlacesDiscovery(outing).discover(DiscoveryRequest(activity='custom:zara outlet',destination=SearchArea(name='Jersey City')))
  self.assertTrue(result.venues);self.assertEqual(outing.usage()['placesSearchRequests'],2)
 def test_no_brand_case_does_not_fill_unrelated_stores(self):
  self.search.return_value={'places':[place('wrong','Other retailer')]};self.search.side_effect=None
  result=PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='custom:zara outlet',destination=SearchArea(name='Jersey City')))
  self.assertFalse(result.venues)

 def test_strict_ten_minutes_and_flexible_twenty(self):
  def routing(body):return [{**leg,'duration':'601s'} for leg in matrix_fixture(body)]
  start={'point':{'id':'fixture_origin','coordinates':{'latitude':40.73,'longitude':-74.05}},'source':'manual','label':'Synthetic Jersey City start','precision':'address_or_place','explicitly_authorized':True}
  with patch('backend.routes_transport.compute_matrix',side_effect=routing):
   strict=real_plans(PlannerInput(activities=['custom:zara outlet'],location='Jersey City',date='2026-11-14',startingLocation=start,firstTravel={'value':10.0,'mode':'strict'}),ProviderBudget())
   flexible=real_plans(PlannerInput(activities=['custom:zara outlet'],location='Jersey City',date='2026-11-14',startingLocation=start,firstTravel={'value':10.0,'mode':'flexible'}),ProviderBudget())
  self.assertFalse(strict.provisionalPlans)
  self.assertTrue(flexible.provisionalPlans)
  self.assertTrue(all(p.travelClassification=='outside_preference' for p in flexible.provisionalPlans))

 def test_late_options_classify_new_discovery_without_repeating_complete_plans(self):
  request=PlannerInput(activities=['custom:zara outlet'],location='Jersey City',date='2026-11-14',planningMode='surprise')
  result=real_plans(request,ProviderBudget());seen={p.candidate.id for p in result.provisionalPlans}
  def new_branches(body,**kwargs):
   return {'places':[{**p,'id':p['id']+'_new'} for p in search_fixture(body,**kwargs)['places']]}
  self.search.side_effect=new_branches
  continued=more_real_plans(result.optionsToken,expand_discovery=True)
  self.assertFalse(seen&{p.candidate.id for p in continued.provisionalPlans})
  self.assertGreater(continued.diagnostics['rankingAudit']['newVenuesSincePreviousResponse'],0)
  self.assertTrue(all(item['lateReason']=='new_discovery' for item in continued.diagnostics['rankingAudit']['selected']))

class RefreshTests(unittest.TestCase):
 def document(self):return {'dataMode':'real','itineraries':[{'candidateId':'chosen','stops':[{'reference':'one'},{'reference':'two'}]}]}
 def test_capability_checked_before_refresh_and_no_retries(self):
  from backend.saved_refresh import RefreshSessions,RefreshRequest
  session=RefreshSessions();request=RefreshRequest(refreshId='12345678-1234-4234-8234-123456789abc',accessToken='A'*43,candidateId='chosen')
  with patch.dict(os.environ,ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1'},clear=True),patch('backend.saved_refresh.reopen',return_value=self.document()) as read,patch('backend.saved_refresh.fetch_saved_details',side_effect=[{'name':'Actual fixture name'},DiscoveryError('provider','PRIVATE')]) as fetch:
   result=session.refresh(request,ProviderBudget())
   self.assertEqual(result['venues']['one']['name'],'Actual fixture name');self.assertEqual(result['venues']['two']['status'],'unavailable')
   self.assertNotIn('PRIVATE',str(result));self.assertEqual(result['diagnostics']['placesDetailsRequests'],2)
   session.refresh(request,ProviderBudget());self.assertEqual(fetch.call_count,2);self.assertEqual(read.call_count,2)
 def test_invalid_and_expired_capability_never_dispatch(self):
  from backend.saved_refresh import RefreshSessions,RefreshRequest
  from backend.saved_plans import PersistenceError
  with patch('backend.saved_refresh.reopen',side_effect=PersistenceError(404)),patch('backend.saved_refresh.fetch_saved_details') as fetch:
   with self.assertRaises(PersistenceError):RefreshSessions().refresh(RefreshRequest(refreshId='12345678-1234-4234-8234-123456789abc',accessToken='A'*43,candidateId='chosen'),ProviderBudget())
   fetch.assert_not_called()
 def test_minimal_pro_mask_and_transport(self):
  from backend.saved_refresh import fetch_saved_details,REFRESH_MASK
  from unittest.mock import MagicMock
  session=MagicMock();session.__enter__.return_value=session
  session.get.return_value.status_code=200
  session.get.return_value.json.return_value={'id':'one','displayName':{'text':'Fixture name'},'businessStatus':'CLOSED_PERMANENTLY','attributions':[]}
  with patch.dict(os.environ,ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1'},clear=True),patch('requests.Session',return_value=session),patch('backend.places_transport.access_token',return_value='private'):
   result=fetch_saved_details('one')
  self.assertEqual(result['businessStatus'],'CLOSED_PERMANENTLY')
  self.assertEqual(session.get.call_args.kwargs['headers']['X-Goog-FieldMask'],REFRESH_MASK)
  self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
 def test_arbitrary_option_does_not_dispatch(self):
  from backend.saved_refresh import RefreshSessions,RefreshRequest
  from backend.saved_plans import PersistenceError
  with patch('backend.saved_refresh.reopen',return_value=self.document()),patch('backend.saved_refresh.fetch_saved_details') as fetch:
   with self.assertRaises(PersistenceError):RefreshSessions().refresh(RefreshRequest(refreshId='12345678-1234-4234-8234-123456789abc',accessToken='A'*43,candidateId='guess'),ProviderBudget())
   fetch.assert_not_called()

class StartupCalendarRanking(unittest.TestCase):
 def test_private_profile_safe_defaults_mock_and_restricted_identity(self):
  from backend.dev_start import environment
  with TemporaryDirectory() as directory:
   profile=Path(directory)/'profile';runtime=Path(directory)/'runtime'
   self.assertNotIn('WHERETO_REAL_DEV',environment({},profile=profile,runtime=runtime))
   profile.write_text('VENUE_DATA_MODE=real\nWHERETO_REAL_DEV=1\n');profile.chmod(0o644)
   with self.assertRaises(ValueError):environment({},profile=profile,runtime=runtime)
   profile.chmod(0o600)
   self.assertEqual(environment({},mock=True,profile=profile,runtime=runtime)['VENUE_DATA_MODE'],'mock')
   with self.assertRaises(ValueError):environment({'CI':'1'},profile=profile,runtime=runtime)
   runtime.write_text('WHERETO_DB_USER=postgres.administrator\n');runtime.chmod(0o600)
   with self.assertRaises(ValueError):environment({},profile=profile,runtime=runtime)
 def test_known_destination_timezones_and_midnight(self):
  from backend.date_resolution import resolve_datetime
  clock=datetime(2026,11,1,0,30,tzinfo=timezone.utc)
  for city,zone,day in [('Jersey City','America/New_York','2026-11-01'),('New York','America/New_York','2026-11-01'),('Hyderabad','Asia/Kolkata','2026-11-02'),('London','Europe/London','2026-11-02')]:
   result=resolve_datetime('tomorrow',['tomorrow'],[],city,now=clock)
   self.assertEqual(result.timezone,zone);self.assertEqual(result.date.isoformat(),day)
  self.assertTrue(resolve_datetime('tomorrow',['tomorrow'],[],'Unknown fixture destination',now=clock).issues)
 def test_verified_journey_includes_origin_without_cap(self):
  from backend.ranking import score_candidates
  from backend.test_saved_plans import fixture
  from backend.models import OutingRequest
  plans=fixture().provisionalPlans[:2]
  for p in plans:
   for v in p.candidate.venues:v.providerPlaceId=v.id
   p.totalTravel=5;p.firstLeg={'minutes':30}
  plans[1].firstLeg={'minutes':2}
  ranked=score_candidates(OutingRequest(activities=['coffee','museum'],date='2026-11-14'),plans)
  self.assertIs(ranked[0],plans[1]);self.assertGreater(plans[1].components['convenience'],plans[0].components['convenience'])
  plans[1].firstLeg={'minutes':None}
  self.assertEqual(score_candidates(OutingRequest(activities=['coffee','museum'],date='2026-11-14'),plans)[1].components['convenience'],0)
