"""Approved Task 46 application ceilings. Every provider response is invented."""
import os
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.real_planning import real_plans, more_real_plans
from backend.real_fixtures import paginated_search_fixture, matrix_fixture, details_fixture
from backend.test_real_planning import ENV, outing
from backend.option_sessions import option_sessions
from backend.venue_details import details_sessions
from backend.places import DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea


class ExpandedLimits(unittest.TestCase):
    def setUp(self):
        for p in (patch.dict(os.environ, {**ENV, 'WHERETO_RATINGS_DEV':'1', 'WHERETO_CONTACT_DETAILS_DEV':'1', 'WHERETO_START_LOOKUP_DEV':'1'}, clear=True),
                  patch('requests.sessions.Session.send', side_effect=AssertionError('Live requests forbidden'))):
            p.start(); self.addCleanup(p.stop)
        self.search = patch('backend.places_transport.text_search', side_effect=paginated_search_fixture).start()
        self.matrix = patch('backend.routes_transport.compute_matrix', side_effect=matrix_fixture).start()
        self.clock = patch('backend.provider_budget.monotonic', return_value=1000).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(option_sessions.entries.clear)
        self.addCleanup(details_sessions.entries.clear)

    def test_configuration_ceiling_and_downward_overrides(self):
        s = ProviderSettings()
        self.assertEqual((s.searches_per_outing,s.candidates_per_activity,s.matrix_elements_per_outing,s.requests_per_outing,s.requests_per_session),(10,100,300,30,50))
        for k,v in [('searches_per_outing',11),('candidates_per_activity',101),('matrix_elements_per_outing',301),('requests_per_outing',31)]:
            with self.assertRaises(ValidationError): ProviderSettings(**{k:v})
        with patch.dict(os.environ, {'WHERETO_SEARCHES_OUTING':'7','WHERETO_REQUESTS_OUTING':'25'}):
            s=ProviderSettings.from_env()
            self.assertEqual((s.searches_per_outing,s.requests_per_outing),(7,25))

    def expanded(self, activities=None, **kw):
        session=ProviderBudget(ProviderSettings(mode="real",candidates_per_activity=20))
        r=real_plans(outing(activities=activities or ['bowling','food'], **kw),session)
        self.assertTrue(all(c.args[0]['pageSize']==10 and 'pageToken' not in c.args[0] for c in self.search.call_args_list))
        while r.canDiscover:
            r=more_real_plans(r.optionsToken,expand_discovery=True)
        return session,r

    def test_twenty_inventory_two_three_four_stops_and_optional_origin(self):
        for activities in (['bowling','food'],['coffee','bowling','food'],['coffee','museum','bowling','food']):
            with self.subTest(stops=len(activities)):
                self.search.reset_mock(); self.matrix.reset_mock()
                start={'point':{'id':'start','place_id':'Synthetic_Start'},'explicitly_authorized':True}
                session,r=self.expanded(activities,startingLocation=start,maxFirstLegTravel=15)
                self.assertEqual(r.diagnostics['discoveredCounts'],[20]*len(activities))
                self.assertEqual(self.search.call_count,2*len(activities))
                self.assertLessEqual(session._elements,150)
                self.assertTrue(r.provisionalPlans)
                self.assertTrue(all(len(p.routeEvidence)==len(activities)-1 and p.firstLeg for p in r.provisionalPlans))
                for initial,later in zip(self.search.call_args_list[:len(activities)],self.search.call_args_list[len(activities):]):
                    self.assertEqual({k:v for k,v in later.args[0].items() if k!='pageToken'},initial.args[0])
                self.assertNotIn('synthetic-next-page',r.model_dump_json())

    def test_fifteen_alternative_actions_share_search_route_and_contact_budget(self):
        session,r=self.expanded()
        context,_=option_sessions.get(r.optionsToken); original=context['outing']
        seen=set(); primary=set(); queued=list(r.alternativeBatches)
        def check(plans):
            self.assertEqual(len(plans),3)
            for p in plans:
                key=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(key,seen);seen.add(key);primary.add(key[0])
                self.assertTrue(all(e['route']['status']=='ok' for e in p.routeEvidence))
        check(r.provisionalPlans)
        for i in range(15):
            if queued: plans=queued.pop(0)
            else:
                r=more_real_plans(r.optionsToken);plans=r.provisionalPlans;queued=list(r.alternativeBatches)
            check(plans)
            self.assertIs(context['outing'],original)
        self.assertEqual(len(seen),48)
        self.assertGreater(len(primary),6)
        self.assertEqual(self.search.call_count,4)
        self.assertLessEqual(session._elements,150)
        with patch('backend.venue_details.fetch_details',side_effect=details_fixture) as contacts:
            ids=list(details_sessions.entries[r.detailsToken][1])[:6]
            for place_id in ids:details_sessions.get(r.detailsToken,place_id)
            self.assertEqual(contacts.call_count,6)
        self.assertEqual(original.usage()['placesDetailsRequests'],6)
        self.assertLessEqual(original.usage()['providerAttempts'],30)

    def test_three_hundred_boundary_minute_pause_and_cumulative_stop(self):
        session,r=self.expanded()
        seen=set(); iterations=0; paused=False
        while r.canExpand and iterations<100:
            for batch in [r.provisionalPlans,*r.alternativeBatches]:
                for p in batch:
                    key=p.candidate.id;self.assertNotIn(key,seen);seen.add(key)
            old=session._elements
            r=more_real_plans(r.optionsToken);iterations+=1
            if not r.provisionalPlans and r.canExpand:
                self.assertEqual(session._elements,old)
                self.assertIn('temporary routing limit',r.message)
                paused=True;self.clock.return_value+=61  # no sleep, retry or counter reset
        self.assertTrue(paused)
        self.assertLessEqual(session._elements,300)
        self.assertGreater(session._elements,200)
        self.assertFalse(r.canExpand)
        self.assertEqual(r.diagnostics['candidateCombinations'],400)
        self.assertLessEqual(r.diagnostics['evaluatedCombinations'],session._elements)
        self.assertGreater(r.diagnostics['uncheckedCombinations'],0)
        self.assertEqual(self.search.call_count,4)
        for _,n in session._matrix_window:self.assertLessEqual(n,150)
        context,_=option_sessions.get(r.optionsToken)
        before=context['outing'].usage()
        with self.assertRaisesRegex(ProviderLimitError,'(?:element|request) limit'):
            with context['outing'].reserve('matrix','over300',origins=1,destinations=301-session._elements):self.fail('No I/O')
        self.assertEqual(context['outing'].usage(),before)

    def test_initial_minute_pause_has_resumable_capability_without_new_searches(self):
        session=ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=10))
        session._matrix_window.append((self.clock.return_value,150))
        r=real_plans(outing(),session)
        self.assertFalse(r.provisionalPlans);self.assertTrue(r.canExpand);self.assertFalse(r.canDiscover)
        self.assertIn('temporary routing limit',r.message);self.matrix.assert_not_called()
        self.clock.return_value+=61
        r=more_real_plans(r.optionsToken)
        self.assertTrue(r.provisionalPlans);self.assertEqual(self.search.call_count,2)
        self.assertLessEqual(session._elements,64)

    def test_ten_searches_ratings_manual_lookup_and_six_contacts_fit_thirty(self):
        session=ProviderBudget(ProviderSettings(mode="real",candidates_per_activity=20));budget=session.outing()
        # Lookup is a separately bounded explicit pre-planning operation. It
        # shares process/search-minute accounting, never consumes a venue slot.
        from backend.starting_places import StartingPlaceQuery, lookup_starting_places
        matches=lookup_starting_places(StartingPlaceQuery(query='Synthetic Station'),session)
        self.assertTrue(matches['matches'])
        self.assertEqual(self.search.call_count,1)
        for i in range(10):
            if i==9:self.clock.return_value+=61
            with budget.reserve('search',str(i)):pass
        self.assertEqual(budget.routing_capacity()['attempts'],14)
        for i in range(14):
            with budget.reserve('matrix',str(i),origins=1,destinations=1):pass
        for i in range(6):
            with budget.reserve('details',str(i)):pass
        self.assertEqual((budget.usage()['providerAttempts'],session._requests),(30,31))
        with self.assertRaises(ProviderLimitError):
            with budget.reserve('route','31st'):self.fail('Over limit')
        self.assertEqual(budget.usage()['placesSearchRequests'],10)

    def test_explicit_discovery_exhausts_ten_shared_searches_not_fresh_budgets(self):
        def rejected(body):
            data=paginated_search_fixture(body)
            for p in data['places']:p['types']=['dentist'];p['primaryType']='dentist'
            # Unique opaque pages; no repeated provider request identity.
            data['nextPageToken']=body.get('pageToken','')+'x'
            return data
        self.search.side_effect=rejected
        session=ProviderBudget(ProviderSettings(mode="real",candidates_per_activity=20));r=real_plans(outing(),session)
        original,_=option_sessions.get(r.optionsToken)
        for _ in range(4):r=more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(self.search.call_count,10);self.assertFalse(r.canDiscover)
        self.assertEqual(original['outing'].usage()['placesSearchRequests'],10)
        with self.assertRaises(DiscoveryError):more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(self.search.call_count,10);self.matrix.assert_not_called()

    def test_quota_stops_new_work_without_retries_or_fake_fallback(self):
        session=ProviderBudget(ProviderSettings(mode="real",candidates_per_activity=20));r=real_plans(outing(),session)
        self.search.side_effect=DiscoveryError('quota','Google quota exhausted. Stop and review usage.')
        with self.assertRaises(DiscoveryError):more_real_plans(r.optionsToken,expand_discovery=True)
        count=self.search.call_count
        with self.assertRaisesRegex(DiscoveryError,'stopped'):more_real_plans(r.optionsToken)
        self.assertEqual(self.search.call_count,count)

    def test_pagination_validation_and_no_automatic_page_fetch(self):
        budget=ProviderBudget().outing()
        result=PlacesDiscovery(budget).discover(DiscoveryRequest(activity='bowling',destination=SearchArea(name='Baltimore')))
        self.assertEqual(self.search.call_count,1);self.assertEqual(len(result.venues),10)
        self.assertTrue(result.paging['bowling']['next'])
        self.assertNotIn('synthetic-next-page',result.model_dump_json())
        self.search.side_effect=lambda body:{'places':[],'nextPageToken':42}
        with self.assertRaisesRegex(DiscoveryError,'pagination'):PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='bowling',destination=SearchArea(name='Baltimore')))
