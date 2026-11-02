"""Invented Google-shaped identity fixtures. Never send network requests."""
import os
import unittest
from copy import deepcopy
from time import perf_counter
from unittest.mock import Mock, patch
from pydantic import ValidationError
from backend.journey import Journey, RequestedStop, LIMITATION
from backend.stop_resolution import StopResolver, ResolvedCandidate
from backend.places import SearchArea, DiscoveryError
from backend.provider_budget import ProviderBudget, ProviderSettings
from backend.interpretation import InterpretationInput, interpret_request
from backend.journey_fixtures import reply
from backend.ai import Interpretation
from backend.test_journey import NOW


def place(identity, name, address='1 Fixture Road, New York', types=None, parents=None, lat=40.75):
    return {'id':identity,'displayName':{'text':name},'formattedAddress':address,
        'location':{'latitude':lat,'longitude':-73.98},'types':types or ['university'],
        'addressComponents':[{'longText':'New York','types':['locality']}],
        **({'containingPlaces':[{'id':p}] for p in parents} if parents else {})}


def stop(source, kind='named_place', requirement='required'):
    return RequestedStop(source=source,kind=kind,requirement=requirement)


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'WHERETO_STOP_RESOLUTION_DEV':'1','WHERETO_PLACES_DEV':'1'})
        self.env.start();self.addCleanup(self.env.stop)
        self.network=patch('requests.sessions.Session.send',side_effect=AssertionError('No network'))
        self.network.start();self.addCleanup(self.network.stop)

    def run_resolution(self, stops, records, *, area=None, **journey):
        resolver=StopResolver(ProviderBudget(ProviderSettings()).outing())
        def search(body,**kwargs):
            data=records(body) if callable(records) else records
            if isinstance(data,Exception): raise data
            return {'places':deepcopy(data)}
        with patch('backend.places_transport.text_search',side_effect=search) as transport:
            result=resolver.resolve(Journey(stops=stops,**journey),area)
        return result,resolver,transport

    def test_exact_college(self):
        result,_,calls=self.run_resolution([stop('SUNY College of Optometry')],[place('Synthetic_suny','SUNY College of Optometry')])
        self.assertEqual(result.stops[0].status,'resolved');self.assertEqual(result.stops[0].candidates[0].place_id,'Synthetic_suny')
        self.assertEqual(calls.call_count,1);self.assertEqual(result.execution,'unavailable')

    def test_street_qualified_walmart_rejects_other_branch(self):
        result,_,_=self.run_resolution([stop('Walmart on Route 440')],[place('Synthetic_wrong','Walmart','1 Main Street', ['department_store']),place('Synthetic_right','Walmart','100 Route 440',['department_store'])])
        self.assertEqual([c.place_id for c in result.stops[0].candidates],['Synthetic_right'])

    def test_apple_world_trade_center(self):
        result,_,calls=self.run_resolution([stop('Apple Store at World Trade Center')],lambda b: [] if b['textQuery']=='World Trade Center' else [place('Synthetic_apple','Apple World Trade Center',types=['electronics_store'])])
        self.assertEqual(result.stops[0].status,'resolved');self.assertEqual(calls.call_count,2)

    def test_ambiguous_station_and_starbucks_with_context_bound_choice(self):
        for phrase,name,address,types in [('Penn Station','Penn Station','Newark',['train_station']),('Starbucks on Main Street','Starbucks','Main Street',['cafe'])]:
            with self.subTest(phrase=phrase):
                result,resolver,calls=self.run_resolution([stop(phrase),stop('coffee','activity')],lambda b:[place('Synthetic_a',name,address,types),place('Synthetic_b',name,address+' West',types)] if not b['textQuery'].startswith('cafes') else [])
                self.assertEqual(result.stops[0].status,'ambiguous')
                choices=resolver.choices();self.assertEqual(len(choices['questions'][0]['choices']),2)
                for token,index,pid in [('wrong',0,'Synthetic_a'),(choices['context'],1,'Synthetic_a'),(choices['context'],0,'foreign')]:
                    with self.assertRaises(ValueError):resolver.choose(token,index,pid)
                chosen=resolver.choose(choices['context'],0,'Synthetic_b')
                self.assertEqual(chosen.stops[0].status,'resolved');self.assertEqual(len(chosen.stops),2)
                with self.assertRaises(ValueError):resolver.choose(choices['context'],0,'Synthetic_a')
                resolver._expires=0
                with self.assertRaises(ValueError):resolver.choices()
                self.assertEqual(calls.call_count,1)
                self.assertEqual(result.stops[1].status,'unresolved')

    def test_flexible_nearest_target_and_zara_brands(self):
        for source,name in [('nearest Target','Target'),('Zara','Zara')]:
            result,_,calls=self.run_resolution([stop(source,'brand')],[place('Synthetic_a',name,types=['clothing_store']),place('Synthetic_b',name,'2 Fixture Road',['clothing_store']),place('Synthetic_wrong','Unrelated Boutique',types=['clothing_store'])],area=SearchArea(name='New York'))
            self.assertEqual(result.stops[0].status,'candidates');self.assertEqual(len(result.stops[0].candidates),2)
            self.assertEqual(calls.call_count,1)

    def test_generic_grocery_and_coffee(self):
        for source,name,types in [('grocery shopping','Synthetic supermarket',['supermarket']),('coffee','Synthetic cafe',['cafe'])]:
            result,_,_=self.run_resolution([stop(source,'activity')],[place('Synthetic_a',name,types=types)],area=SearchArea(name='New York'))
            self.assertEqual(result.stops[0].status,'candidates')

    def test_zara_branch_requires_verified_parent_not_proximity(self):
        for parents,expected in [(['Synthetic_mall'],'resolved'),(None,'unresolved')]:
            result,_,calls=self.run_resolution([stop('Zara at Newport Centre')],lambda b:[place('Synthetic_mall','Newport Centre',types=['shopping_mall'])] if b['textQuery']=='Newport Centre' else [place('Synthetic_zara','Zara','Near Newport Centre',['clothing_store'],parents)])
            self.assertEqual(result.stops[0].status,expected);self.assertEqual(calls.call_count,2)

    def test_outlet_preference_and_hard_only(self):
        for source,expected in [('Zara outlet','candidates'),('Zara outlet only','unresolved')]:
            result,_,_=self.run_resolution([stop(source,'brand')],[place('Synthetic_zara','Zara',types=['clothing_store'])],area=SearchArea(name='New York'))
            self.assertEqual(result.stops[0].status,expected)

    def test_same_mall_requires_all_tenant_ids(self):
        for parents,expected in [(['Synthetic_mall'],False),(None,True)]:
            def fixtures(body):
                query=body['textQuery']
                if query.startswith('shopping malls'):return [place('Synthetic_mall','Synthetic Mall',types=['shopping_mall'])]
                name='Nike' if query.startswith('nike') else 'Adidas'
                return [place('Synthetic_'+name,name,types=['clothing_store'],parents=parents)]
            result,_,calls=self.run_resolution([stop('Nike','brand'),stop('Adidas','brand')],fixtures,area=SearchArea(name='New York'),shared_place={'stops':[0,1],'source':'same mall'})
            self.assertEqual(bool(result.unresolved_constraints),expected);self.assertEqual(calls.call_count,3)

    def test_named_required_plus_optional_or_required_discovery(self):
        for phrase,requirement in [('coffee','optional'),('grocery shopping','required')]:
            def fixtures(body):
                return [place('Synthetic_suny','SUNY College of Optometry')] if body['textQuery'].startswith('SUNY') else [place('Synthetic_activity','Synthetic cafe supermarket',types=['cafe','supermarket'])]
            result,_,calls=self.run_resolution([stop('SUNY College of Optometry'),stop(phrase,'activity',requirement)],fixtures)
            self.assertEqual(result.stops[1].requested.requirement,requirement)
            self.assertEqual([s.occurrence for s in result.stops],[0,1]);self.assertEqual(calls.call_count,2)

    def test_repeated_occurrences_share_request_not_occurrence(self):
        result,_,calls=self.run_resolution([stop('coffee','activity'),stop('coffee','activity')],[place('Synthetic_a','Synthetic cafe',types=['cafe'])],area=SearchArea(name='New York'))
        self.assertEqual(len(result.stops),2);self.assertEqual(calls.call_count,1)
        self.assertEqual(result.diagnostics['placesSearchRequests'],1)

    def test_hard_geography_and_preferred_area(self):
        for enforce,status in [(True,'unresolved'),(False,'resolved')]:
            result,_,_=self.run_resolution([stop('SUNY College of Optometry')],[place('Synthetic_a','SUNY College of Optometry')],area=SearchArea(name='Baltimore',enforce_name=enforce))
            self.assertEqual(result.stops[0].status,status)

    def test_far_named_destination_is_not_rejected_by_nearby_radius(self):
        area=SearchArea(coordinates={'latitude':0.,'longitude':0.},radius_m=1000.)
        result,_,_=self.run_resolution([stop('SUNY College of Optometry')],[place('Synthetic_a','SUNY College of Optometry')],area=area)
        self.assertEqual(result.stops[0].status,'resolved')
        hard=area.model_copy(update={'restrict_to_area':True})
        self.assertEqual(self.run_resolution([stop('SUNY College of Optometry')],[place('Synthetic_a','SUNY College of Optometry')],area=hard)[0].stops[0].status,'unresolved')

    def test_empty_similar_incorrect_and_wrong_type_never_substitute(self):
        for records in [[],[place('Synthetic_a','SUNY College of Dentistry')],[place('Synthetic_a','SUNY College of Optometry',types=['clothing_store'])],[place('Synthetic_a','SUNY College of Optometry Annex')]]:
            result,_,_=self.run_resolution([stop('SUNY College of Optometry')],records)
            self.assertEqual(result.stops[0].status,'unresolved');self.assertEqual(result.stops[0].candidates,[])

    def test_missing_provider_identity_fields(self):
        for field in ['id','displayName','formattedAddress','location','types']:
            raw=place('Synthetic_a','SUNY College of Optometry');raw.pop(field)
            result,_,_=self.run_resolution([stop('SUNY College of Optometry')],[raw])
            self.assertIn(result.stops[0].status,['unresolved','provider_failure']);self.assertFalse(result.stops[0].candidates)

    def test_provider_quota_failure_and_conservative_accounting(self):
        for code in ['quota','provider']:
            result,_,calls=self.run_resolution([stop('SUNY College of Optometry')],DiscoveryError(code,'Synthetic provider failure'))
            self.assertEqual(result.stops[0].error_code,code);self.assertEqual(result.diagnostics['placesSearchRequests'],1);self.assertEqual(calls.call_count,1)
        resolver=StopResolver(ProviderBudget(ProviderSettings(searches_per_outing=0)).outing())
        with patch('backend.places_transport.text_search') as transport:
            result=resolver.resolve(Journey(stops=[stop('SUNY College of Optometry')]))
        self.assertEqual(result.stops[0].error_code,'application_limit');transport.assert_not_called()

    def test_invalid_ids_and_duplicates(self):
        for identity,status in [('places/bad','unresolved'),('bad?query','unresolved'),('Synthetic_a','resolved')]:
            raw=place(identity,'SUNY College of Optometry')
            result,_,_=self.run_resolution([stop('SUNY College of Optometry')],[raw,raw])
            self.assertEqual(result.stops[0].status,status);self.assertLessEqual(len(result.stops[0].candidates),1)

    def test_hours_provenance_transient_no_new_operations(self):
        raw=place('Synthetic_a','SUNY College of Optometry')
        raw.update(currentOpeningHours={'openNow':True},regularOpeningHours={'weekdayDescriptions':['Synthetic hours']},timeZone={'id':'America/New_York'})
        result,_,calls=self.run_resolution([stop('SUNY College of Optometry')],[raw])
        facts=result.stops[0].candidates[0].facts
        self.assertTrue(facts.currentOpeningHours.openNow);self.assertEqual(facts.timeZone.id,'America/New_York')
        self.assertIn('currentOpeningHours.openNow',facts.observedAt)
        self.assertEqual(facts.provider,'google_places');self.assertEqual(facts.id,'Synthetic_a')
        self.assertEqual(calls.call_count,1);self.assertEqual(result.diagnostics['placesDetailsRequests'],0);self.assertEqual(result.diagnostics['reservedMatrixElements'],0)

    def test_order_return_deadline_contract_preserved(self):
        j=Journey(stops=[stop('SUNY College of Optometry')],endpoint={'kind':'home','source':'return home'},deadline={'source':'by 6 PM','minute':1080},total_duration={'minutes':45,'source':'within 45 minutes'})
        r=StopResolver(ProviderBudget(ProviderSettings()).outing())
        with patch('backend.places_transport.text_search',return_value={'places':[place('Synthetic_a','SUNY College of Optometry')]}):result=r.resolve(j)
        self.assertEqual(j.model_dump(),result.journey.model_dump());self.assertTrue(result.unresolved_constraints)

    def test_gate_off_and_malformed_contract(self):
        with patch.dict(os.environ,{'WHERETO_STOP_RESOLUTION_DEV':'0'}),self.assertRaises(DiscoveryError):StopResolver(ProviderBudget().outing())
        with self.assertRaises(ValidationError):ResolvedCandidate(place_id='foreign',eligibility='identity_verified',reason='invented',facts={})

    def test_context_geography_and_travel_survive_and_exclusions_apply_without_area(self):
        from backend.interpretation import InterpretationContext
        context=InterpretationContext(transport='walking',firstTravel={'value':10.,'mode':'flexible'},
            geography={'excludedRegions':['MD']},originText='Synthetic private origin')
        resolver=StopResolver(ProviderBudget().outing())
        raw=place('Synthetic_a','SUNY College of Optometry')
        raw['addressComponents'].append({'longText':'Maryland','shortText':'MD','types':['administrative_area_level_1']})
        with patch('backend.places_transport.text_search',return_value={'places':[raw]}):
            result=resolver.resolve(Journey(stops=[stop('SUNY College of Optometry')]),context=context)
        self.assertEqual(result.stops[0].status,'unresolved')
        self.assertEqual(result.context,context)
        self.assertNotIn('Synthetic private origin',str(resolver.choices()))

    def test_private_address_and_area_only_types_are_not_establishment_choices(self):
        for types in [['street_address'],['locality'],['point_of_interest','establishment']]:
            result,_,_=self.run_resolution([stop('Synthetic Residence')],[place('Synthetic_a','Synthetic Residence',types=types)])
            self.assertEqual(result.stops[0].status,'unresolved')

    def test_repeated_failed_exact_lookup_never_retries(self):
        result,_,calls=self.run_resolution([stop('SUNY College of Optometry'),stop('SUNY College of Optometry')],DiscoveryError('quota','Synthetic quota'))
        self.assertEqual(calls.call_count,1);self.assertEqual(result.diagnostics['placesSearchRequests'],1)
        self.assertEqual([s.error_code for s in result.stops],['quota','quota'])

    def test_named_final_endpoint_and_order_remain_separate(self):
        result,_,calls=self.run_resolution([stop('SUNY College of Optometry')],
            lambda body:[place('Synthetic_station','Penn Station',types=['train_station'])] if body['textQuery']=='Penn Station' else [place('Synthetic_suny','SUNY College of Optometry')],
            endpoint={'kind':'named_place','source':'finish at Penn Station'})
        self.assertEqual(result.endpoint.status,'resolved');self.assertEqual(result.endpoint.occurrence,1)
        self.assertEqual(result.journey.endpoint.source,'finish at Penn Station');self.assertEqual(calls.call_count,2)

    def test_resolution_benchmark_separate_from_ai(self):
        times=[]
        for _ in range(20):
            start=perf_counter();result,_,calls=self.run_resolution([stop('SUNY College of Optometry')],[place('Synthetic_a','SUNY College of Optometry')]);times.append(perf_counter()-start)
            self.assertEqual(calls.call_count,1)
        print(f'Offline exact resolution 20 iterations median={sorted(times)[10]*1000:.3f}ms max={max(times)*1000:.3f}ms; simulated provider latency only.')


class EndpointClarificationTests(unittest.TestCase):
    def test_owner_exact_college_then_coffee_is_valid_advanced(self):
        from backend.journey_fixtures import FixtureAI
        text='Go to SUNY College of Optometry then get coffee today.'
        r=interpret_request(InterpretationInput(text=text),FixtureAI(),now=NOW)
        self.assertEqual(r.unsupported,[LIMITATION]);self.assertEqual(r.executionStatus,'advanced_unavailable')
        self.assertEqual(len(r.interpretation.journey.stops),2)

    def test_field_only_answers_without_qwen_or_places(self):
        text='Go grocery shopping, then return home today.'
        ai=Mock();ai.interpret.return_value=Interpretation.model_validate(reply(['grocery shopping'],dates=['today'],endpoint={'kind':'home','source':'return home'}))
        with patch('backend.places_transport.text_search') as search:
            initial=interpret_request(InterpretationInput(text=text,preferences={'transport':'walking','date':'2026-11-07'}),ai,now=NOW)
            self.assertEqual(initial.questions[0].field,'endpoint');self.assertIsNotNone(initial.pending)
            for answer,expected in [('home','clarification_required'),('Return to my starting point','advanced_unavailable'),('123 Fictional Lane, Baltimore','advanced_unavailable')]:
                r=interpret_request(InterpretationInput(text=text,pending=initial.pending,answers={'endpoint':answer},preferences={'transport':'walking','date':'2026-11-07'}),ai,now=NOW)
                self.assertEqual(r.executionStatus,expected);self.assertIsNone(r.request)
                self.assertEqual(r.interpretation.journey,initial.interpretation.journey)
                self.assertEqual(r.context.transport,'walking');self.assertEqual(r.context.date.isoformat(),'2026-11-07')
                if expected=='advanced_unavailable':
                    self.assertIsNotNone(r.pending)
                    again=interpret_request(InterpretationInput(text=text,pending=r.pending),ai,now=NOW)
                    self.assertEqual(again.context.endpointAnswer,answer)
            ai.interpret.assert_called_once();search.assert_not_called()
