"""Manual acceptance regressions. Invented provider responses; live sends forbidden."""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.real_planning import real_plans, more_real_plans
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.test_real_planning import ENV, outing
from backend.option_sessions import option_sessions
from backend.routes import RouteError

PROMPT = 'Plan bowling and dinner in Baltimore on Saturday, November 7, 2026, for 2 people. Keep driving between venues under 5 minutes.'


class TravelAcceptance(unittest.TestCase):
    def interpret(self, phrase, leg=None, total=None, uncertainties=None, transport="driving"):
        text = PROMPT if phrase is None else 'Bowling and dinner in Baltimore on 2026-11-07 for 2 people. ' + phrase
        ai = Interpretation(activities=['bowling', 'dinner'], people=2, location='Baltimore', date=None,
                            budget_per_person=None, preferences=[], transport=transport, travel_leg_minutes=leg,
                            travel_total_minutes=total, uncertainties=uncertainties or [])
        provider = Mock(); provider.interpret.return_value = ai
        return interpret_request(InterpretationInput(text=text), provider, now=datetime(2026,10,26,12,tzinfo=timezone.utc))

    def test_exact_prompt_and_scoped_boundaries(self):
        cases = [(None,5,None,True,False),('At most 5 minutes between places, driving.',5,None,False,False),
                 ('No more than 10 minutes between stops, driving.',10,None,False,False),
                 ('Under 20 minutes total driving.',None,20,False,True)]
        for phrase,leg,total,exclusive_leg,exclusive_total in cases:
            r=self.interpret(phrase,leg,total)
            self.assertFalse(r.issues, r.issues)
            self.assertEqual((r.request.maxLegTravel,r.request.travel,r.request.maxLegTravelExclusive,r.request.travelExclusive,r.request.transport),
                             (leg,total,exclusive_leg,exclusive_total,'driving'))
        r=self.interpret('15 minutes from my starting point, driving.')
        self.assertFalse(r.issues,r.issues)
        self.assertEqual(r.request.maxFirstLegTravel,15)
        self.assertIsNone(r.request.maxLegTravel)
        self.assertIsNone(r.request.travel)

    def test_verbatim_model_uncertainty_only_resolves_with_verified_scope_and_amount(self):
        r=self.interpret(None,5,uncertainties=['between venues under 5 minutes'])
        self.assertFalse(r.issues,r.issues)
        self.assertTrue(r.request.maxLegTravelExclusive)
        for leg,total,label in [(None,5,'between venues under 5 minutes'),(4,None,'between venues under 5 minutes'),
                                (5,None,'between venues under 5 minutes if traffic allows'),(5,None,'Quiet bowling lanes required')]:
            self.assertTrue(self.interpret(None,leg,total,[label]).issues,(leg,total,label))

    def test_model_verbatim_cap_can_normalize_missing_values_but_not_guesses(self):
        r=self.interpret(None,uncertainties=['between venues under 5 minutes'],transport=None)
        self.assertFalse(r.issues,r.issues)
        self.assertEqual((r.request.maxLegTravel,r.request.maxLegTravelExclusive,r.request.transport),(5,True,'driving'))
        for phrase,label in [('Maybe keep driving between venues under 5 minutes.','between venues under 5 minutes'),
                             ('Driving between venues under 5 minutes if traffic allows.','between venues under 5 minutes'),
                             ('Driving and walking between venues under 5 minutes.','between venues under 5 minutes'),
                             ('Driving between venues under 5 minutes or walking.','between venues under 5 minutes'),
                             ('Not driving between venues under 5 minutes.','between venues under 5 minutes')]:
            self.assertTrue(self.interpret(phrase,uncertainties=[label],transport=None).issues)
        self.assertTrue(self.interpret(None,uncertainties=[],transport=None).issues)

    def test_null_optional_schema_labels_do_not_block_or_hide_stated_caps(self):
        r=self.interpret(None,5,uncertainties=['budget_per_person','budget_group','travel_total_minutes'])
        self.assertFalse(r.issues,r.issues)
        self.assertTrue(r.request.maxLegTravelExclusive)
        missing=self.interpret('Under 5 minutes between venues, driving.',None,uncertainties=['travel_leg_minutes'])
        self.assertTrue(missing.issues)
        missing_budget=self.interpret('Under $20 per person, driving.',uncertainties=['budget_per_person'])
        self.assertTrue(missing_budget.issues)

    def test_ambiguous_wrong_scope_minimum_and_missing_extraction_still_block(self):
        for phrase,leg,total in [('Keep driving under 5 minutes.',5,None),('5 minutes nearby, driving.',5,None),
                                 ('At least 5 minutes between stops, driving.',5,None),
                                 ('5 minutes between venues, driving.',None,5),('15 miles from my starting point, driving.',None,None),('Under 5 minutes between venues, driving.',None,None)]:
            self.assertTrue(self.interpret(phrase,leg,total).issues,phrase)


class OptionsAcceptance(unittest.TestCase):
    def setUp(self):
        for p in (patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('No live sends'))):
            p.start();self.addCleanup(p.stop)
        self.search=patch('backend.places_transport.text_search',side_effect=search_fixture).start()
        self.matrix=patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture).start()
        self.addCleanup(patch.stopall);self.addCleanup(option_sessions.entries.clear)

    def test_fifteen_clicks_three_new_pairs_each_with_original_budget(self):
        session=ProviderBudget(); result=real_plans(outing(),session)
        seen=set();primaries=set(); queued=list(result.alternativeBatches)
        def check(plans):
            self.assertEqual(len(plans),3)
            for p in plans:
                pair=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(pair,seen);seen.add(pair);primaries.add(pair[0])
        check(result.provisionalPlans)
        for _ in range(15):
            if queued:batch=queued.pop(0)
            else:
                result=more_real_plans(result.optionsToken);batch=result.provisionalPlans;queued=list(result.alternativeBatches)
            check(batch)
        self.assertEqual(len(seen),48);self.assertEqual(len(primaries),10)
        context,_=option_sessions.get(result.optionsToken)
        self.assertEqual(context['outing'].usage()['placesSearchRequests'],2)
        self.assertEqual(context['outing'].usage()['reservedMatrixElements'],100)
        self.assertEqual(self.search.call_count,2)
        self.assertIs(context['session'],session)
        # Exhaust the entire invented 10×10 pool, including the last partial batch.
        while queued or result.canExpand:
            if queued: batch=queued.pop(0)
            else:
                result=more_real_plans(result.optionsToken);batch=result.provisionalPlans;queued=list(result.alternativeBatches)
            for p in batch:
                pair=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(pair,seen);seen.add(pair)
        self.assertEqual(len(seen),100)
        self.assertEqual(self.search.call_count,2)
        self.assertEqual(session._elements,100)

    def test_explicit_sparse_discovery_refills_without_widening_or_reset(self):
        def responses(body):
            data=search_fixture(body)
            if body['textQuery'].startswith('bowling alleys'):data['places']=data['places'][:2]
            return data
        self.search.side_effect=responses
        session=ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=10));r=real_plans(outing(),session)
        context,_=option_sessions.get(r.optionsToken);budget=context['outing']
        self.assertTrue(r.canDiscover);self.assertEqual(self.search.call_count,2)
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(self.search.call_count,3)  # dinner is already at its cap
        self.assertIs(context['outing'],budget)
        self.assertEqual(r.diagnostics['discoveredCounts'],[10,10])
        self.assertEqual(r.diagnostics['discoveryStages']['retainedCounts'],{'bowling':10,'food':10})
        self.assertFalse(r.canDiscover)
        self.assertTrue(all('Baltimore' in c.args[0]['textQuery'] for c in self.search.call_args_list))
        self.assertLessEqual(budget.usage()['reservedMatrixElements'],150)
        self.assertGreaterEqual(r.diagnostics['discoveryStages']['newAssociations'],8)

    def test_small_pool_exhaustion_and_no_implicit_search_refill(self):
        def response(body):
            data=search_fixture(body);data['places']=data['places'][:2];return data
        self.search.side_effect=response
        r=real_plans(outing(),ProviderBudget());token=r.optionsToken
        while r.canExpand:r=more_real_plans(token)
        self.assertEqual(self.search.call_count,2)
        r=more_real_plans(token,expand_discovery=True)
        self.assertFalse(r.canDiscover)
        self.assertEqual(r.diagnostics['placesSearchRequests'],4)
        self.assertEqual(r.diagnostics['matrixElements'],4)
        self.assertFalse(r.provisionalPlans)
        self.assertIn('checked',r.errors[0].message)
        with self.assertRaisesRegex(Exception,'budget|limit'):more_real_plans(token,expand_discovery=True)
        self.assertEqual(self.search.call_count,4)

    def test_empty_initial_pool_can_explicitly_search_once(self):
        def response(body):
            data=search_fixture(body)
            if body['textQuery'].startswith('bowling alleys'):data['places']=[]
            return data
        self.search.side_effect=response
        r=real_plans(outing(),ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=10)))
        self.assertFalse(r.provisionalPlans);self.assertTrue(r.canDiscover)
        self.assertEqual(self.matrix.call_count,0)
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertTrue(r.provisionalPlans);self.assertFalse(r.canDiscover)
        self.assertEqual(self.search.call_count,3)

    def test_expansion_provider_failure_is_charged_and_never_retried(self):
        from backend.places import DiscoveryError
        def response(body):
            if body['textQuery'].startswith('bowling centers'):
                raise DiscoveryError('quota','Provider quota reached. Stop and review usage.')
            data=search_fixture(body);data['places']=data['places'][:2];return data
        self.search.side_effect=response
        r=real_plans(outing(),ProviderBudget());context,_=option_sessions.get(r.optionsToken)
        with self.assertRaisesRegex(DiscoveryError,'quota'):more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(context['outing'].usage()['placesSearchRequests'],3)
        with self.assertRaisesRegex(DiscoveryError,'stopped'):more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(self.search.call_count,3)

    def test_stage_diagnostics_explain_geography_dedup_and_relevance_without_content(self):
        from copy import deepcopy
        def response(body):
            data=search_fixture(body)
            if body['textQuery'].startswith('bowling'):
                data['places'][1]=deepcopy(data['places'][0])
                data['places'][2]['types']=['dentist']
                data['places'][2]['primaryType']='dentist'
                data['places'][3]['addressComponents'][0]['longText']='Other City'
                data['places'][3]['addressComponents'][0]['shortText']='Other City'
            return data
        self.search.side_effect=response
        r=real_plans(outing(),ProviderBudget());stage=r.diagnostics['discoveryStages']['bowling']
        self.assertEqual((stage['returned'],stage['afterGeography'],stage['afterNormalization'],stage['afterMealFilter'],stage['afterDeduplication'],stage['afterRelevance']), (10,9,9,9,8,7))
        self.assertGreater(r.diagnostics['discoveryReasons']['unrelated_business_type'],0)
        self.assertGreater(r.diagnostics['discoveryReasons']['duplicate_place_id'],0)
        for private in ('Other City','Fixture_', 'latitude', 'longitude'):
            self.assertNotIn(private,str(r.diagnostics))

    def test_expansion_retains_original_ids_and_caps_inventory_and_contact_budget(self):
        def response(body):
            data=search_fixture(body)
            if body['textQuery'].startswith('bowling alleys'):data['places']=data['places'][:5]
            if body['textQuery'].startswith('bowling centers'):
                for place in data['places']:place['id']+='New'
            return data
        self.search.side_effect=response
        r=real_plans(outing(),ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=10)));context,_=option_sessions.get(r.optionsToken)
        original={v.facts.id for v in context['discovery'].venues if 'bowling' in v.activities}
        token=r.detailsToken;budget=context['outing']
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        retained={v.facts.id for v in context['discovery'].venues if 'bowling' in v.activities}
        self.assertEqual(len(retained),10);self.assertTrue(original<=retained)
        self.assertEqual(r.diagnostics['discoveryStages']['candidateCapExcludedAssociations'],5)
        from backend.venue_details import details_sessions
        self.assertEqual(r.detailsToken,token)
        self.assertIs(details_sessions.entries[token][2],budget)
        self.assertTrue(retained<=details_sessions.entries[token][1])

    def test_unconfirmed_exact_manual_string_stays_backend_guarded(self):
        r=real_plans(outing(manualStartingPlace='union station, washington dc'),ProviderBudget())
        self.assertFalse(r.provisionalPlans)
        self.assertIn('Find and confirm',r.message)
        self.assertEqual(self.search.call_count,0)
        self.assertEqual(self.matrix.call_count,0)

    def test_strict_seconds_and_unknown_route_evidence(self):
        for seconds,exclusive,expected in [(299,True,True),('299.999999999',True,True),('300.000000001',False,False),(300,True,False),(300,False,True),(301,False,False)]:
            def matrix(body):
                data=matrix_fixture(body)
                for leg in data:leg['duration']=str(seconds)+'s'
                return data
            self.matrix.side_effect=matrix
            r=real_plans(outing(maxLegTravel=5,maxLegTravelExclusive=exclusive),ProviderBudget())
            self.assertEqual(bool(r.provisionalPlans),expected,(seconds,exclusive))
        self.matrix.side_effect=lambda body:[]
        r=real_plans(outing(maxLegTravel=5,maxLegTravelExclusive=True),ProviderBudget())
        self.assertTrue(all(any(i.status=='unknown' and i.field=='travel' for i in p.issues) for p in r.provisionalPlans))

    def test_cumulative_limits_and_aggregate_diagnostics(self):
        session=ProviderBudget(ProviderSettings(mode='real',matrix_elements_per_outing=36))
        r=real_plans(outing(),session)
        self.assertEqual(r.diagnostics['discoveryStages']['bowling']['returned'],10)
        self.assertEqual(r.diagnostics['primaryCandidates'],6)
        for _ in range(6):
            if not r.canExpand: break
            r=more_real_plans(r.optionsToken)
        self.assertFalse(r.canExpand)
        self.assertEqual(session._elements,36)
        self.assertEqual(self.search.call_count,2)
        self.assertNotIn('latitude',str(r.diagnostics));self.assertNotIn('Fixture_',str(r.diagnostics))
