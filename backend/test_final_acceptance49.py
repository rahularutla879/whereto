"""Final acceptance repairs; provider transports are always offline."""
import os
import socket
import unittest
from unittest.mock import patch,MagicMock
from backend.continuation_status import continuation_status
from backend.test_refinements49 import ENV

class ContinuationTests(unittest.TestCase):
 def test_six_distinct_states(self):
  for kwargs,kind in [({'combinations':True},'available'),({'discovery':True},'discovery_remaining'),({},'search_exhausted'),({'limited':True},'provider_limited'),({'constrained':True},'constraints'),({'pending':True},'pending_routes')]:
   with self.subTest(kind=kind):self.assertEqual(continuation_status(**kwargs)['kind'],kind)
 def test_no_global_absence_claim(self):
  self.assertIn('for this outing right now',continuation_status()['message'])
  self.assertIn('routes still need checking',continuation_status(pending=True)['message'])
 def test_repeated_exhausted_action_does_no_work(self):
  from backend.real_planning import more_real_plans
  from backend.test_saved_plans import fixture
  from threading import Lock
  previous=fixture().model_copy(update={'canExpand':False,'canDiscover':False,'continuationStatus':None})
  request=MagicMock();request.startingLocation=True;request.planningMode='origin'
  context={'lastContinuation':previous,'request':request,'session':MagicMock()}
  with patch('backend.option_sessions.option_sessions.get',return_value=(context,Lock())),patch('backend.location_context.outing_problem',return_value=None),patch('backend.real_planning.real_plans') as planner,patch('backend.real_planning.expand_venue_discovery') as discovery:
   for expand in (False,False,True,True):
    result=more_real_plans('opaque',expand_discovery=expand)
    self.assertFalse(result.plans or result.provisionalPlans)
   planner.assert_not_called();discovery.assert_not_called()
 def test_quota_failure_keeps_recoverable_session(self):
  from backend.real_planning import more_real_plans
  from backend.places import DiscoveryError
  from threading import Lock
  request=MagicMock();request.startingLocation=True;request.planningMode='origin'
  context={'request':request,'session':MagicMock(),'outing':MagicMock(),'expanded':False}
  context['outing'].usage.return_value={}
  with patch('backend.option_sessions.option_sessions.get',return_value=(context,Lock())),patch('backend.location_context.outing_problem',return_value=None),patch('backend.real_planning.expand_venue_discovery',side_effect=DiscoveryError('quota','Synthetic quota')):
   with self.assertRaises(DiscoveryError):more_real_plans('opaque',expand_discovery=True)
  self.assertTrue(context['stopped'])
  self.assertIn('request',context) # Capability/context retained; failed provider work is never retried.

 def test_finite_discovery_and_known_combinations_exhaust_without_new_calls(self):
  from backend.refinement_fixtures import search_fixture
  from backend.real_fixtures import matrix_fixture
  from backend.real_planning import real_plans,PlannerInput,more_real_plans,can_discover
  from backend.provider_budget import ProviderBudget
  from backend.option_sessions import option_sessions
  with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('Live Google forbidden')),patch('backend.places_transport.text_search',side_effect=search_fixture) as search,patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
   request=PlannerInput(activities=['custom:zara store'],location='Jersey City',date='2026-11-14',planningMode='surprise')
   first=real_plans(request,ProviderBudget());context,_=option_sessions.get(first.optionsToken)
   self.assertEqual(len(first.provisionalPlans),2)
   for job in context['jobs']:job['done']=True
   context['regionSteps']={a:32 for a in request.activities}
   self.assertFalse(can_discover(context));before=search.call_count
   result=real_plans(request,context['session'],context=context)
   self.assertFalse(result.canExpand or result.canDiscover)
   self.assertEqual(result.continuationStatus.kind,'search_exhausted')
   for expand in (False,True,True):more_real_plans(first.optionsToken,expand_discovery=expand)
   self.assertEqual(search.call_count,before);self.assertEqual(len(context['seen']),2)

 def test_expired_http_session_disables_provider_actions(self):
  import json
  from backend import main as api
  from backend.places import DiscoveryError
  budget=MagicMock();budget.settings.mode='real'
  with patch.object(api,'provider_budget',budget),patch('backend.real_planning.more_real_plans',side_effect=DiscoveryError('expired','Search session expired')):
   response=api.more_options(api.OptionsRequest(token='opaque'))
  self.assertEqual(response.status_code,422)
  self.assertEqual(json.loads(response.body)['continuation'],{'canExpand':False,'canDiscover':False})

 def test_irrelevant_far_pairs_do_not_keep_route_check_action_alive(self):
  from types import SimpleNamespace as NS
  from backend.venue_models import Coordinates
  from backend.continuation_status import known_route_work
  request=NS(betweenTravel=None,maxLegTravel=None,startingLocation=None)
  pools=[[NS(id='a')],[NS(id='b')]]
  facts={'a':NS(coordinates=Coordinates(latitude=40.0,longitude=-74.0)), 'b':NS(coordinates=Coordinates(latitude=42.0,longitude=-74.0))}
  self.assertFalse(known_route_work({'locationFirst':True},request,pools,facts,{},'drive'))
  self.assertTrue(known_route_work({'locationFirst':True,'spatialEdges':{(0,'a','b')}},request,pools,facts,{},'drive'))
  self.assertFalse(known_route_work({'locationFirst':True,'spatialEdges':{(0,'a','b')}},request,pools,facts,{('a','b'):object()},'drive'))

class SelectedRefreshTests(unittest.TestCase):
 def test_nonselected_original_option_cannot_dispatch(self):
  from backend.saved_refresh import RefreshSessions,RefreshRequest
  from backend.saved_plans import PersistenceError
  document={'dataMode':'real','selectedId':'selected','itineraries':[{'candidateId':'other','stops':[{'reference':'fixture'}]}]}
  with patch('backend.saved_refresh.reopen',return_value=document),patch('backend.saved_refresh.fetch_saved_details') as fetch:
   with self.assertRaises(PersistenceError):RefreshSessions().refresh(RefreshRequest(accessToken='A'*43,candidateId='other',refreshId='12345678-1234-4234-8234-123456789abc'),MagicMock())
   fetch.assert_not_called()
 def test_pro_and_explicit_existing_contact_masks(self):
  from backend.saved_refresh import fetch_saved_details,REFRESH_MASK,CONTACT_REFRESH_MASK
  session=MagicMock();session.__enter__.return_value=session
  session.get.return_value.status_code=200
  session.get.return_value.json.return_value={'id':'fixture','displayName':{'text':'Invented store'},'formattedAddress':'Invented address','businessStatus':'OPERATIONAL','googleMapsUri':'https://maps.google.com/?cid=123','internationalPhoneNumber':'+1 202 555 0149','websiteUri':'https://example.com','attributions':[]}
  with patch.dict(os.environ,ENV|{'WHERETO_CONTACT_DETAILS_DEV':'1'},clear=True),patch('requests.Session',return_value=session),patch('backend.places_transport.access_token',return_value='test-only'):
   basic=fetch_saved_details('fixture');self.assertEqual(session.get.call_args.kwargs['headers']['X-Goog-FieldMask'],REFRESH_MASK)
   self.assertNotIn('website',basic);self.assertEqual(basic['mapsUrl'],'https://maps.google.com/?cid=123')
   full=fetch_saved_details('fixture',include_contacts=True);self.assertEqual(session.get.call_args.kwargs['headers']['X-Goog-FieldMask'],CONTACT_REFRESH_MASK)
   self.assertEqual(full['telephoneUrl'],'tel:+12025550149');self.assertEqual(full['website'],'https://example.com')
  self.assertNotIn('rating',CONTACT_REFRESH_MASK);self.assertNotIn('*',CONTACT_REFRESH_MASK)
 def test_maps_links_are_provider_supplied_and_allowlisted(self):
  from backend.saved_refresh import verified_maps_url
  for url in ('https://evil.example/maps','javascript:alert(1)','https://user:password@maps.google.com/',None):self.assertIsNone(verified_maps_url(url))
  self.assertEqual(verified_maps_url('https://www.google.com/maps/place/?cid=123'),'https://www.google.com/maps/place/?cid=123')

class StartupTests(unittest.TestCase):
 def test_occupied_port_fails_with_actionable_guidance(self):
  from backend.dev_start import port_available
  with socket.socket() as listener:
   listener.bind(('127.0.0.1',0));listener.listen()
   with self.assertRaisesRegex(ValueError,'Control.C before restarting'):port_available(listener.getsockname()[1])

  with socket.socket() as server:
   server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);server.bind(('127.0.0.1',0));server.listen()
   port=server.getsockname()[1]
   with socket.create_connection(('127.0.0.1',port)) as client:
    connection,_=server.accept();connection.close();server.close();client.recv(1)
  port_available(port) # A closed TCP connection must not prevent the next startup.
