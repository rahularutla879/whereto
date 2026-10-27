"""Exploration is tested entirely with invented responses and a network tripwire."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread, Barrier
import unittest
from unittest.mock import patch

from backend.development_cost import DevelopmentCost, AccountingError, dispatch
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.places import DiscoveryRequest, PlacesDiscovery, SearchArea, DiscoveryError
from backend.real_planning import real_plans, more_real_plans
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.test_real_planning import ENV, outing
from backend.option_sessions import option_sessions


class ExplorationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.env={**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.temp.name+'/usage.json'}
        self.p=patch.dict(os.environ,self.env,clear=True);self.p.start();self.addCleanup(self.p.stop)
        self.network=patch('requests.sessions.Session.send',side_effect=AssertionError('No provider requests permitted'))
        self.network.start();self.addCleanup(self.network.stop)
        self.addCleanup(option_sessions.entries.clear)

    def test_flag_requires_explicit_local_real_configuration(self):
        for extra in ({'VENUE_DATA_MODE':'mock'}, {'WHERETO_REAL_DEV':'0'}, {'NODE_ENV':'production'}, {'NODE_ENV':'staging'}, {'WHERETO_ENV':'staging'}, {'VERCEL':'1'}, {'CI':'1'}, {'WHERETO_EXPLORATION_DEV':'yes'}):
            with self.subTest(extra=extra),patch.dict(os.environ,extra):
                with self.assertRaises(ValueError):ProviderSettings.from_env()
        with patch.dict(os.environ,{},clear=True):
            s=ProviderSettings.from_env();self.assertFalse(s.exploration);self.assertEqual(s.ceiling('searches_per_outing'),10)
        self.assertTrue(ProviderSettings.from_env().exploration)
        self.assertFalse(any(os.getenv(k)=='1' for k in ('WHERETO_RATINGS_DEV','WHERETO_CONTACT_DETAILS_DEV','WHERETO_START_LOOKUP_DEV')))

    def test_exact_guard_boundary_shared_outings_and_restart(self):
        with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':'0.064'}):
            for _ in range(2):
                b=ProviderBudget();o=b.outing()
                with o.reserve('search','different outing same query allowed'):dispatch('search')
            b=ProviderBudget()
            with self.assertRaisesRegex(ProviderLimitError,'daily estimated'):
                with b.outing().reserve('search','third'):self.fail('Should not dispatch')
            d=DevelopmentCost().snapshot()
            self.assertEqual(d['estimatedDayGrossUsd'],.064);self.assertEqual(d['estimatedAllowanceRemainingUsd'],0)
            self.assertEqual(json.loads(Path(self.env['WHERETO_DEV_COST_LEDGER']).read_text())['days'][DevelopmentCost.day()]['dispatched'],{'search_pro':2})

    def test_corruption_and_unavailable_state_fail_closed(self):
        c=DevelopmentCost();c.snapshot()
        Path(self.env['WHERETO_DEV_COST_LEDGER']).write_text('{broken')
        with self.assertRaises(AccountingError): c.snapshot()
        with self.assertRaises(ProviderLimitError):
            with ProviderBudget().outing().reserve('search','x'):self.fail()
        with patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':self.temp.name}):
            with self.assertRaises(AccountingError):DevelopmentCost().snapshot()
        for value in ('NaN','-1','0','not money','0.0000001'):
            with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':value}):
                with self.assertRaises(AccountingError): DevelopmentCost()

    def test_concurrent_admission_cannot_overspend(self):
        with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':'0.032'}):
            DevelopmentCost().snapshot()
            barrier=Barrier(2);out=[]
            def run():
                barrier.wait()
                try:
                    with DevelopmentCost().reserve({'search_pro':1}):out.append('admitted')
                except AccountingError:out.append('refused')
            threads=[Thread(target=run) for _ in range(2)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(sorted(out),['admitted','refused'])
            self.assertEqual(DevelopmentCost().snapshot()['estimatedDayGrossUsd'],.032)

    def test_skus_failures_and_content_free_ledger(self):
        with patch.dict(os.environ,{'WHERETO_RATINGS_DEV':'1'}):
            b=ProviderBudget();o=b.outing()
            with o.reserve('search','private secret search identity'): dispatch('search')
            with o.reserve('lookup','private location'):dispatch('search')
            with o.reserve('details','private place ID'):dispatch('details')
            with o.reserve('matrix','private route',origins=2,destinations=3):dispatch('matrix',6)
            with self.assertRaises(RuntimeError):
                with o.reserve('search','failed operation'):raise RuntimeError('invented failure')
            self.assertAlmostEqual(o.usage()['estimatedOutingGrossUsd'],.035+.032+.020+.030+.035)
            self.assertEqual(o.usage()['dispatched'],{'search':2,'details':1,'matrix':1,'matrixElements':6})
            text=Path(self.env['WHERETO_DEV_COST_LEDGER']).read_text()
            self.assertNotIn('private',text);self.assertNotIn('location',text)

    def test_shared_minute_guard_survives_restart_no_retries(self):
        for i in range(10):
            with ProviderBudget().outing().reserve('search',str(i)):pass
        with self.assertRaisesRegex(ProviderLimitError,'minute'):
            with ProviderBudget().outing().reserve('search','11'):self.fail()
        with patch('backend.development_cost.time',return_value=10**12):
            with ProviderBudget().outing().reserve('search','later deliberate action'):pass

    def test_duplicate_page_and_search_suppressed(self):
        o=ProviderBudget().outing();adapter=PlacesDiscovery(o)
        def same(body):
            dispatch('search');return {**search_fixture(body),'nextPageToken':'same-token'}
        with patch('backend.places_transport.text_search',side_effect=same) as search:
            req=DiscoveryRequest(activity='bowling',destination=SearchArea(name='Baltimore'))
            adapter.discover(req)
            adapter.discover(req.model_copy(update={'page_token':'same-token'}))
            with self.assertRaises(ProviderLimitError):adapter.discover(req.model_copy(update={'page_token':'same-token'}))
            self.assertEqual(search.call_count,2)

    def test_rich_fixture_exceeds_old_ceilings_and_fifteen_actions(self):
        def invented(body):
            dispatch('search')
            # Four ten-result pages per strategy, same parameters on pagination.
            page=int(body.get('pageToken','0'))
            d=search_fixture(body)
            for i,p in enumerate(d['places']):
                p['id']+=f'_page_{page}'
                p['displayName']['text']+=f' page {page}'
                p['location']['latitude']+=page*.001
            if page<3:d['nextPageToken']=str(page+1)
            return d
        def routes(body):
            dispatch('matrix',len(body['origins'])*len(body['destinations']));return matrix_fixture(body)
        clock=[1000]
        with patch('backend.places_transport.text_search',side_effect=invented) as searches,patch('backend.routes_transport.compute_matrix',side_effect=routes),patch('backend.provider_budget.monotonic',side_effect=lambda:clock[0]),patch('backend.development_cost.time',side_effect=lambda:clock[0]):
            b=ProviderBudget();r=real_plans(outing(),b)
            context,_=option_sessions.get(r.optionsToken);seen=set()
            def collect(result):
                for plans in [result.provisionalPlans,*result.alternativeBatches]:
                    for p in plans:
                        key=tuple(v.id for v in p.candidate.venues)
                        self.assertNotIn(key,seen);seen.add(key)
            collect(r)
            for _ in range(11):
                clock[0]+=61
                if r.canDiscover:
                    r=more_real_plans(r.optionsToken,expand_discovery=True);collect(r)
            self.assertGreater(searches.call_count,10)
            self.assertGreater(r.diagnostics['discoveredCounts'][0],20)
            self.assertFalse(r.canDiscover)
            for _ in range(15):
                clock[0]+=61
                r=more_real_plans(r.optionsToken);collect(r)
                self.assertEqual(len(r.provisionalPlans),3, {k:r.diagnostics.get(k) for k in ("discoveredCounts","shortlistedCounts","eligibleCombinations","unseenEligibleCombinations","reservedMatrixElements","routingCapacity","estimatedOutingGrossUsd")})
            self.assertGreater(b._elements,300)
            self.assertIs(context['outing']._session,b)
            self.assertLessEqual(b._elements,1500) # fixture work is modest, no need to exhaust $10
            self.assertGreaterEqual(len(seen),48)
            self.assertTrue(all(c.args[0]['pageSize']==10 for c in searches.call_args_list))
            print('EXPLORATION_FIXTURE_SUMMARY', {'searches':searches.call_count,'retained':r.diagnostics['discoveredCounts'],'routeElements':b._elements,'uniqueOffered':len(seen),'grossUsd':r.diagnostics['estimatedOutingGrossUsd']})

    def test_merge_does_not_resurrect_rejected_mixed_venue_activity(self):
        from backend.real_planning import expand_venue_discovery
        def response(body):
            if body['textQuery'].startswith('bowling alleys'):
                return search_fixture(body)
            # One shared cafe ID in both alternative queries: food is valid,
            # bowling is explicitly rejected by the refinement evidence policy.
            d=search_fixture({'textQuery':'cafes in Baltimore','pageSize':1})
            return d
        with patch('backend.places_transport.text_search',side_effect=response),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            r=real_plans(outing(),ProviderBudget())
            context,_=option_sessions.get(r.optionsToken)
            expand_venue_discovery(context)
            cafe=next(v for v in context['discovery'].venues if v.facts.id=='Fixture_coffee_0')
            self.assertIn('food',cafe.activities)
            self.assertNotIn('bowling',cafe.activities)
            self.assertTrue(any(s.activity=='bowling' for s in cafe.sources))
            self.assertTrue(cafe.facts.attributions)

    def test_removed_process_ceilings_accounting_not_reset(self):
        b=ProviderBudget();o=b.outing()
        clock=[1000]
        with patch('backend.provider_budget.monotonic',side_effect=lambda:clock[0]),patch('backend.development_cost.time',side_effect=lambda:clock[0]):
            for i in range(55):
                clock[0]+=61
                with o.reserve('matrix',str(i),origins=1,destinations=30):pass
        self.assertEqual(b._elements,1650);self.assertEqual(b._requests,55)
        self.assertAlmostEqual(o.usage()['estimatedOutingGrossUsd'],8.25)

    def test_hard_travel_and_authorized_origin_remain_enforced(self):
        def search(body):
            dispatch('search'); return search_fixture(body)
        def matrix(body):
            dispatch('matrix',len(body['origins'])*len(body['destinations']))
            return matrix_fixture(body)
        with patch('backend.places_transport.text_search',side_effect=search),patch('backend.routes_transport.compute_matrix',side_effect=matrix):
            start={'point':{'id':'start','place_id':'Invented_start'},'explicitly_authorized':True}
            result=real_plans(outing(maxLegTravel=5,maxFirstLegTravel=5,startingLocation=start),ProviderBudget())
            self.assertTrue(result.provisionalPlans)
            self.assertTrue(all(p.firstLeg and p.firstLeg['minutes']<=5 for p in result.provisionalPlans))
            self.assertTrue(all(e['route']['origin_id']!=e['route']['destination_id'] for p in result.provisionalPlans for e in p.routeEvidence))
            result=real_plans(outing(maxLegTravel=0),ProviderBudget())
            self.assertFalse(result.provisionalPlans)

    def test_unsupported_arcade_and_outside_area_still_rejected(self):
        from backend.real_fixtures import bowling_diagnostic_fixture
        from backend.places import PlacesDiscovery
        with patch('backend.places_transport.text_search',side_effect=bowling_diagnostic_fixture):
            result=PlacesDiscovery(ProviderBudget().outing()).discover(DiscoveryRequest(activity='bowling',destination=SearchArea(name='Washington, DC'),search_variant='alternative'))
            self.assertEqual(result.audit['bowling']['eligibleRetained'],6)
            self.assertGreater(result.audit['bowling']['geographyRejected'],0)
            self.assertGreater(result.audit['bowling']['relevanceRejected'],0)

    def test_provider_quota_stops_continuation_without_retry(self):
        with patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            r=real_plans(outing(),ProviderBudget())
        with patch('backend.places_transport.text_search',side_effect=DiscoveryError('quota','Invented quota exhausted')) as searches:
            with self.assertRaises(DiscoveryError):more_real_plans(r.optionsToken,expand_discovery=True)
            with self.assertRaises(DiscoveryError):more_real_plans(r.optionsToken,expand_discovery=True)
            self.assertEqual(searches.call_count,1)

    def test_unreserved_dispatch_and_relative_accounting_path_refused(self):
        with self.assertRaises(ProviderLimitError):dispatch('search')
        with DevelopmentCost().reserve({'search_pro':1}):
            dispatch('search')
            with self.assertRaises(ProviderLimitError):dispatch('search')
        with patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':'relative.json'}):
            with self.assertRaises(AccountingError):DevelopmentCost()

if __name__=='__main__':unittest.main()
