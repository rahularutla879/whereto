"""Task 46 acceptance: synthetic venues only; never dispatch Google traffic."""
import fcntl
import json
import os
import random
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread, Event
from time import sleep
from types import SimpleNamespace
from unittest.mock import patch
from backend.development_cost import DevelopmentCost,AccountingError,dispatch
from backend.provider_budget import ProviderBudget,ProviderLimitError
from backend.venue_details import DetailsSessions,contact_links
from backend.test_real_planning import ENV
from backend.real_planning import PlannerInput,real_plans,more_real_plans
from backend.option_sessions import option_sessions
from backend.location_fixtures import place
from backend.interpretation import InterpretationInput,interpret_request
from backend.ai import Interpretation
from backend.models import ActivityType
from backend.places import SearchArea,DiscoveryError
from backend.venue_geography import geographic_reason

class Accounting(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'usage.json'
        for guard in (patch.dict(os.environ,{**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_CONTACT_DETAILS_DEV':'1','WHERETO_DEV_COST_LEDGER':str(self.path)},clear=True),
                      patch('requests.sessions.Session.send',side_effect=AssertionError('No Google calls'))):
            guard.start();self.addCleanup(guard.stop)

    def test_nested_snapshot_contacts_and_restart_preserve_usage(self):
        outing=ProviderBudget().outing()
        with outing.reserve('search','invented'):
            dispatch('search')
            self.assertEqual(outing.usage()['estimatedDayGrossUsd'],.032)
        sessions=DetailsSessions();token=sessions.create(['Synthetic_A','Synthetic_B'],outing)
        def contacts(identity):
            dispatch('details')
            return contact_links({'id':identity,'internationalPhoneNumber':'+1 202 555 0100','websiteUri':'https://example.com/venue'},identity)
        with patch('backend.venue_details.fetch_details',side_effect=contacts) as transport:
            for identity in ['Synthetic_A','Synthetic_B']:
                result=sessions.get(token,identity)
                self.assertEqual(result['telephoneUrl'],'tel:+12025550100')
                self.assertEqual(result['website'],'https://example.com/venue')
                self.assertFalse(result['diagnostics'].get('accountingUnavailable',False))
            self.assertEqual(transport.call_count,2)
        self.assertAlmostEqual(DevelopmentCost().snapshot()['estimatedDayGrossUsd'],.072)
        self.assertEqual(ProviderBudget().cost.snapshot()["estimatedDayGrossUsd"],DevelopmentCost().snapshot()["estimatedDayGrossUsd"])

    def test_temporary_lock_serializes_and_releases_without_history_reset(self):
        c=DevelopmentCost();c.snapshot()
        ready=Event()
        def holder():
            with c.locked():ready.set();sleep(.08)
        thread=Thread(target=holder);thread.start();ready.wait()
        with DevelopmentCost().reserve({'details':1}):dispatch('details')
        thread.join()
        self.assertEqual(c.snapshot()['estimatedDayGrossUsd'],.02)

    def test_corruption_permissions_and_explicit_safe_recovery(self):
        sessions=DetailsSessions();o=ProviderBudget().outing();token=sessions.create(['Synthetic_A'],o)
        DevelopmentCost().snapshot();good=self.path.read_bytes()
        self.path.write_text('{broken')
        with patch('backend.venue_details.fetch_details') as transport:
            with self.assertRaisesRegex(ProviderLimitError,'invalid'):
                sessions.get(token,'Synthetic_A')
            transport.assert_not_called()
        self.assertEqual(self.path.read_text(),'{broken')
        # Test-only explicit recovery of a known valid backup; never auto-reset.
        self.path.write_bytes(good)
        self.path.chmod(0o644)
        with self.assertRaisesRegex(AccountingError,'permissions'):DevelopmentCost().snapshot()
        self.path.chmod(0o600)
        with patch('backend.venue_details.fetch_details',return_value=contact_links({'id':'Synthetic_A'},'Synthetic_A')):
            self.assertIsNone(sessions.get(token,'Synthetic_A')['phone'])
        with self.assertRaisesRegex(DiscoveryError,'already attempted'):sessions.get(token,'Synthetic_A')

    def test_parallel_reservations_exact_guard_and_failed_io_remain_charged(self):
        with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':'0.04'}):
            DevelopmentCost().snapshot();results=[]
            def work():
                try:
                    with DevelopmentCost().reserve({'details':1}):dispatch('details');sleep(.02)
                    results.append('sent')
                except AccountingError:results.append('refused')
            threads=[Thread(target=work) for _ in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(results.count('sent'),2)
            self.assertEqual(DevelopmentCost().snapshot()['estimatedDayGrossUsd'],.04)
        with self.assertRaises(RuntimeError):
            with DevelopmentCost().reserve({'details':1}):raise RuntimeError('invented provider failure')
        self.assertEqual(DevelopmentCost().snapshot()['estimatedDayGrossUsd'],.06)

class Geography(unittest.TestCase):
    def test_neighborhood_source_qualification_and_ambiguous_destination(self):
        for destination,model in [('Midtown Manhattan','Manhattan'),('Midtown East','Midtown East'),('Midtown West','Midtown West'),
                                  ('Chelsea','Chelsea'),("Hell\'s Kitchen","Hell\'s Kitchen"),('Financial District','Financial District'),('Jersey City','Jersey City'),('Manhattan','Manhattan')]:
            ai=SimpleNamespace(interpret=lambda _,model=model:Interpretation(activities=['dinner','drinks'],location=model,people=3,budget_per_person=None,date=None,preferences=[]))
            r=interpret_request(InterpretationInput(text=f'Plan dinner and drinks in {destination}, tomorrow, for 3 people.'),ai)
            self.assertIsNotNone(r.request,r.issues)
            self.assertEqual(r.request.location,destination)
        ai=SimpleNamespace(interpret=lambda _:Interpretation(activities=['dinner'],location=None,people=3,budget_per_person=None,date=None,preferences=[]))
        r=interpret_request(InterpretationInput(text='Dinner somewhere tomorrow for 3 people'),ai)
        self.assertIsNone(r.request)

    def test_qualified_components_strict_boundary_and_flexible_nearby(self):
        from backend.venue_models import Coordinates
        point=Coordinates(latitude=40.75,longitude=-73.98)
        components=[{'longText':'Midtown','types':['neighborhood']},{'longText':'Manhattan','types':['sublocality_level_1']},{'longText':'New York','types':['locality']}]
        self.assertIsNone(geographic_reason(SearchArea(name='Midtown Manhattan'),point,components))
        self.assertIsNotNone(geographic_reason(SearchArea(name='Chelsea'),point,components))
        self.assertIsNone(geographic_reason(SearchArea(name='Jersey City',enforce_name=False),point,components))
        from backend.places import parse_response
        outside=place('Synthetic_outside','Synthetic restaurant',40.75,-73.98,types=['restaurant'])
        outside['addressComponents']=components
        result=parse_response({'places':[outside]},SearchArea(name='Jersey City',enforce_name=False),10)
        self.assertFalse(result.candidates,'Unverified destination with no provider-backed anchor must stay closed.')


class Discovery(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.clock=1000;self.calls=[];self.first_ids=set();self.counter=0
        self.random=random.Random(91)
        for guard in (patch.dict(os.environ,{**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.tmp.name+'/usage.json'},clear=True),
                      patch('requests.sessions.Session.send',side_effect=AssertionError('No Google calls')),
                      patch('backend.provider_budget.monotonic',side_effect=lambda:self.clock),
                      patch('backend.development_cost.time',side_effect=lambda:self.clock),
                      patch('backend.surprise.SystemRandom',return_value=self.random),
                      patch('backend.places_transport.text_search',side_effect=self.search),
                      patch('backend.routes_transport.compute_matrix',side_effect=self.routes)):
            guard.start();self.addCleanup(guard.stop)
        self.addCleanup(option_sessions.entries.clear)

    def request(self,city='Manhattan',surprise=False,**changes):
        return PlannerInput(activities=['food','drinks'],dinnerStops=[0],date='2026-11-14',people=3,location=city,locationFirst=True,
            planningMode='surprise' if surprise else 'origin',
            startingLocation=None if surprise else {'point':{'id':'authorized-start','coordinates':{'latitude':40.75,'longitude':-73.98}},'explicitly_authorized':True,'source':'manual','label':'Synthetic public park','precision':'address_or_place'},
            **changes)

    def search(self,body,**kwargs):
        dispatch('search');self.calls.append(body)
        first='restaurant' in body['textQuery']
        box=body.get('locationRestriction',{}).get('rectangle')
        lat=(box['low']['latitude']+box['high']['latitude'])/2 if box else 40.75
        lon=(box['low']['longitude']+box['high']['longitude'])/2 if box else -73.98
        self.counter+=1
        # Every user-triggered new query discovers a distinct, valid fixture pool.
        prefix='first' if first else 'later'
        records=[]
        for i in range(10):
            identity=f'Synthetic_{prefix}_{self.counter}_{i}'
            if first:self.first_ids.add(identity)
            p=place(identity,f'Synthetic {prefix} {self.counter} {i}',lat+i*.00005,lon,types=['restaurant' if first else 'bar'])
            p['formattedAddress']='Synthetic address, Manhattan, New York'
            p['addressComponents']=[{'longText':'Manhattan','types':['sublocality_level_1']},{'longText':'New York','types':['locality']},{'longText':'NY','types':['administrative_area_level_1']}]
            p['rating']=4.5+i*.001;p['userRatingCount']=100
            records.append(p)
        return {'places':records}

    def routes(self,body):
        dispatch('matrix',len(body['origins'])*len(body['destinations']))
        return [{'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS','duration':'540s' if 'location' in a['waypoint'] else '180s','distanceMeters':1200}
                for i,a in enumerate(body['origins']) for j,_ in enumerate(body['destinations'])]

    def test_dense_manhattan_three_primary_venues_exact_origin_limit_and_no_search_alternatives(self):
        r=real_plans(self.request(firstTravel={'value':5,'mode':'flexible'}),ProviderBudget())
        self.assertEqual(len({p.candidate.venues[0].id for p in r.provisionalPlans}),3)
        self.assertTrue(all(p.firstLeg['minutes']==9 for p in r.provisionalPlans))
        print('INITIAL_MANHATTAN_STAGES',r.diagnostics['venuePipeline'],r.diagnostics['discoveryBottlenecks'])
        qualities=[p.components['quality'] for p in r.provisionalPlans]
        self.assertLess(max(qualities)-min(qualities),.01)
        context,_=option_sessions.get(r.optionsToken)
        self.assertEqual(context['request'].location,'Manhattan');self.assertEqual(context['request'].startingLocation.label,'Synthetic public park')
        searches=len(self.calls);seen=set()
        for action in range(8):
            for p in r.provisionalPlans:
                signature=tuple(v.id for v in p.candidate.venues);self.assertNotIn(signature,seen);seen.add(signature)
            self.clock+=61;r=more_real_plans(r.optionsToken)
            self.assertEqual(len(self.calls),searches)
        d=r.diagnostics['discoveryBottlenecks']
        self.assertGreaterEqual(d['firstRouteCompliant'],3)
        self.assertEqual(d['firstRouteNoncompliant'],0)
        print('DENSE_DISCOVERY_SUMMARY',r.diagnostics['venuePipeline'],d)

    def test_fifteen_geographic_explorations_share_history_origin_and_budgets(self):
        r=real_plans(self.request(firstTravel={'value':5,'mode':'flexible'}),ProviderBudget());seen=set();first=set();areas=set()
        for action in range(16):
            for p in r.provisionalPlans:
                signature=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(signature,seen);seen.add(signature);first.add(signature[0])
                self.assertLessEqual(p.firstLeg['minutes'],10)
            if action==15:break
            self.clock+=61
            previous=len(self.calls)
            r=more_real_plans(r.optionsToken,expand_discovery=r.canDiscover)
            self.assertGreaterEqual(len(self.calls),previous)
            self.assertLessEqual(len(self.calls)-previous,2)
            self.assertTrue(r.provisionalPlans,r.message)
            for call in self.calls[previous:]:areas.add(json.dumps(call.get('locationRestriction'),sort_keys=True))
        context,_=option_sessions.get(r.optionsToken)
        self.assertGreaterEqual(len(areas),5)
        self.assertGreater(len(first),15)
        self.assertEqual(len(context['positionIds'][0]),100)
        self.assertEqual(len(seen),48)
        self.assertEqual(context['request'].firstTravel.value,5)
        self.assertEqual(context['request'].startingLocation.point.coordinates.latitude,40.75)
        print('EXPLORE_FARTHER_SUMMARY',{'actions':16,'uniqueFirst':len(first),'uniqueFull':len(seen),'areas':len(areas),'usage':context['outing'].usage()})

    def test_jersey_city_three_stops_mixed_bowling_and_stage_exclusions(self):
        original=self.search
        def jersey(body,**kwargs):
            bowling='bowling' in body['textQuery']
            d=original({**body,'textQuery':body['textQuery'].replace('bowling alleys','restaurants').replace('bowling centers','restaurants').replace('entertainment centers with bowling','restaurants')},**kwargs)
            for p in d['places']:
                p['addressComponents']=[{'longText':'Jersey City','types':['locality']},{'longText':'NJ','types':['administrative_area_level_1']}]
                if bowling:p['types']=['bowling_alley','video_arcade']
            if bowling:
                d['places'][6]['types']=['video_arcade'];d['places'][6]['displayName']['text']='Synthetic racing arcade'
                d['places'][7]['addressComponents'][0]['longText']='New York'
                d['places'][8]=d['places'][0].copy()
            return d
        with patch('backend.places_transport.text_search',side_effect=jersey):
            request=self.request(city='Jersey City',firstTravel={'value':5,'mode':'flexible'},
                geography={'strictDestination':True}).model_copy(update={'activities':[ActivityType.bowling,ActivityType.food,ActivityType.drinks],'dinnerStops':[1]})
            r=real_plans(request,ProviderBudget())
        self.assertEqual(len({p.candidate.venues[0].id for p in r.provisionalPlans}),3)
        row=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual(row['googleResultsReceived'],10)
        self.assertEqual(row['geographyRejected'],1)
        self.assertEqual(row['duplicatesRemoved'],1)
        self.assertEqual(row['relevanceRejected'],1)
        self.assertEqual(row['eligibleRetained'],7)
        self.assertTrue(all([v.activity for v in p.candidate.venues]==['bowling','food','drinks'] for p in r.provisionalPlans))
        print('JERSEY_CITY_STAGES',row,r.diagnostics['discoveryBottlenecks'])

    def test_concurrent_actions_refused_without_duplicate_history(self):
        r=real_plans(self.request(),ProviderBudget());context,lock=option_sessions.get(r.optionsToken)
        before=set(context['seen']);searches=len(self.calls)
        lock.acquire()
        try:
            with self.assertRaisesRegex(DiscoveryError,'running'):more_real_plans(r.optionsToken,expand_discovery=True)
        finally:lock.release()
        self.assertEqual(context['seen'],before);self.assertEqual(len(self.calls),searches)

    def test_no_limit_heuristics_walking_and_drive_are_not_hard_caps(self):
        from backend.location_policy import radius
        self.assertEqual(radius(None,None,'drive'),12000)
        self.assertEqual(radius(None,None,'walk'),1200)
        r=real_plans(self.request(),ProviderBudget())
        self.assertTrue(r.provisionalPlans)
        self.assertIsNone(r.request.firstTravel)
        context,_=option_sessions.get(r.optionsToken)
        from backend.sequential_discovery import next_region
        first=next_region(context,commit=True);second=next_region(context,commit=True)
        self.assertNotEqual(first.coordinates,second.coordinates)
        self.assertGreater(first.radius_m,12000)
        with patch.dict(os.environ,{'WHERETO_DISCOVERY_DRIVE_MINUTES':'25'}):
            self.assertEqual(radius(None,None,'drive'),15000)

    def test_sparse_supply_adaptive_search_never_invents_primary_diversity(self):
        original=self.search
        def sparse(body,**kwargs):
            d=original(body,**kwargs)
            if 'restaurant' in body['textQuery']:
                d['places']=d['places'][:1];d['places'][0]['id']='Synthetic_only_first'
            return d
        with patch('backend.places_transport.text_search',side_effect=sparse):
            r=real_plans(self.request(),ProviderBudget())
        self.assertEqual(len({p.candidate.venues[0].id for p in r.provisionalPlans}),1)
        self.assertIn('limited_discovered_primary_supply',r.diagnostics['discoveryBottlenecks']['reasonCodes'])
        self.assertLessEqual(len(self.calls),5)

if __name__=='__main__':unittest.main()
