"""Owner-authorized exploration/intent regressions. Invented providers only."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from backend.ai import Interpretation
from backend.development_cost import DevelopmentCost, AccountingError, dispatch
from backend.interpretation import InterpretationInput, interpret_request
from backend.models import OutingRequest
from backend.places import DiscoveryRequest, SearchArea, search_body
from backend.provider_budget import ProviderBudget, ProviderLimitError
from backend.test_real_planning import ENV, outing
from backend.real_planning import real_plans, more_real_plans
from backend.real_fixtures import matrix_fixture
from backend.location_fixtures import neighborhood_fixture
from backend.option_sessions import option_sessions
from backend.venue_quality import relevance
from backend.venue_normalization import normalize_google_place

NOW=datetime(2026,10,28,12,tzinfo=timezone.utc)

class OpenExploration(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=self.temp.name+'/usage.json'
        self.clock=1000
        for p in (patch.dict(os.environ,{**ENV,'WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.path},clear=True),
                  patch('requests.sessions.Session.send',side_effect=AssertionError('Billable network forbidden')),
                  patch('backend.development_cost.time',side_effect=lambda:self.clock),
                  patch('backend.provider_budget.monotonic',side_effect=lambda:self.clock)):
            p.start();self.addCleanup(p.stop)
        self.addCleanup(option_sessions.entries.clear)

    def extract(self,text,activities,location='Manhattan',**extra):
        ai=Interpretation(activities=activities,location=location,date=None,budget_per_person=None,preferences=[],**extra)
        return interpret_request(InterpretationInput(text=text),SimpleNamespace(interpret=lambda _:ai),now=NOW)

    def test_open_activity_queries_grounding_and_no_invalid_google_types(self):
        for phrase in ('pottery class','painting workshop','go-karting','aquarium','swimming','laser tag','cooking workshop','origami studio'):
            result=self.extract(phrase+' followed by dinner in Manhattan tomorrow',[phrase,'dinner'])
            self.assertIsNotNone(result.request,result.issues)
            self.assertEqual(result.request.activities[0].value,'custom:'+phrase)
            self.assertEqual(result.request.activityIntents['custom:'+phrase],phrase)
            body=search_body(DiscoveryRequest(activity=result.request.activities[0],destination=SearchArea(name='Manhattan')),10)
            self.assertIn(phrase,body['textQuery']);self.assertNotIn('includedType',body)
            self.assertIsNone(result.request.people)
        ungrounded=self.extract('Dinner in Manhattan tomorrow',['origami studio','dinner'])
        self.assertIsNone(ungrounded.request)
        ambiguous=self.extract('something fun then dinner in Manhattan tomorrow',['something fun','dinner'])
        self.assertEqual([q.field for q in ambiguous.questions],['activities'])

    def test_movies_synonyms_and_unknown_acronym_are_separate(self):
        for wording in ('show movies','watch a movie','watch a film','go to the movies','see a film','cinema'):
            result=self.extract(wording+' in GSIW today for 3 people',[wording],location='GSIW',people=3)
            self.assertIsNotNone(result.request,result.issues)
            self.assertEqual(result.request.activities,['movie'])
            self.assertEqual(result.request.location,'GSIW')
            self.assertIsNone(result.request.people)
            self.assertFalse(any(q.field=='people' for q in result.questions))

    def test_inflection_and_combined_model_phrases_never_drop_a_stop(self):
        from backend.interpretation import activity_category
        self.assertEqual(activity_category('pottery classes'),activity_category('a pottery class'))
        self.assertEqual(activity_category('origami studios'),activity_category('origami studio'))
        for phrase in ('movies and dinner','pottery class followed by dinner'):
            r=self.extract(phrase+' in Manhattan tomorrow',[phrase])
            self.assertIsNone(r.request)
            self.assertEqual([q.field for q in r.questions],['activities'])

    def test_custom_relevance_and_mixed_three_stop_pipeline(self):
        from backend.location_fixtures import place
        def supplied(body, **_):
            dispatch('search')
            phrase='pottery class' if 'pottery' in body['textQuery'] else 'restaurant' if 'restaurant' in body['textQuery'] else 'cafe'
            types=['establishment'] if phrase=='pottery class' else [phrase]
            return {'places':[place('Synthetic_'+phrase.replace(' ','_')+str(i), 'Synthetic '+phrase+' '+str(i), types=types) for i in range(10)]}
        with patch('backend.places_transport.text_search',side_effect=supplied),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            r=real_plans(outing(activities=['custom:pottery class','food','coffee']).model_copy(update={'location':'Washington, DC'}),ProviderBudget())
        self.assertEqual(len(r.provisionalPlans),3,r.message)
        self.assertTrue(all([v.activity for v in p.candidate.venues]==['custom:pottery class','food','coffee'] for p in r.provisionalPlans))
        self.assertTrue(all(any(i.code=='session_not_verified' for i in p.issues) for p in r.provisionalPlans))
        for name,types,expected in [('Synthetic pottery studio',['establishment'],'uncertain'),('Synthetic laser tag',['establishment'],'mismatch'),('Synthetic dentist',['dentist'],'mismatch')]:
            facts=normalize_google_place(place('Synthetic_evidence',name,types=types),'custom:pottery class')
            self.assertEqual(relevance(facts).status,expected)

    def test_independent_custom_pools_reach_100_without_a_new_whitelist(self):
        from backend.location_fixtures import place
        from backend.sequential_discovery import initialize,expand,can_expand
        activities=['custom:origami studio','custom:pottery class','food']
        counts=dict.fromkeys(activities,0)
        def supplied(body,**_):
            dispatch('search')
            activity=next((a for a in activities[:2] if a.removeprefix('custom:') in body['textQuery']),'food')
            offset=counts[activity];counts[activity]+=10
            phrase=activity.removeprefix('custom:') if activity!='food' else 'restaurant'
            box=body.get('locationRestriction',{}).get('rectangle')
            lat=(box['low']['latitude']+box['high']['latitude'])/2 if box else 38.9
            lon=(box['low']['longitude']+box['high']['longitude'])/2 if box else -77.02
            result={'places':[place('Synthetic_'+str(activities.index(activity))+'_'+str(n),'Synthetic '+phrase+' '+str(n),lat,lon,types=['restaurant'] if activity=='food' else ['establishment']) for n in range(offset,offset+10)]}
            if offset%30<20:result['nextPageToken']='synthetic-page-'+str(offset+10)
            return result
        with patch('backend.places_transport.text_search',side_effect=supplied):
            context=initialize(outing(activities=activities).model_copy(update={"location":"Washington, DC"}),ProviderBudget().outing())
            for _ in range(60):
                if not can_expand(context):break
                self.clock+=61
                expand(context)
            actual={a:sum(a in v.activities for v in context['discovery'].venues) for a in activities}
            self.assertEqual(actual,dict.fromkeys(activities,100))

    def test_clarification_preserves_concrete_custom_activity(self):
        r=self.extract('pottery class then something fun in Manhattan tomorrow',['pottery class','something fun'])
        ai=SimpleNamespace(interpret=lambda _:self.fail('No extra model call'))
        fixed=interpret_request(InterpretationInput(text=r.pending.text,pending=r.pending,answers={'activities':'coffee'}),ai,now=NOW)
        self.assertEqual(fixed.request.activities,['custom:pottery class','coffee'])

    def test_specific_movie_or_concert_is_venue_intent_not_confirmed_session(self):
        for phrase,category in [('watch a Dune movie','movie'),('a named performer concert','concert')]:
            r=self.extract(phrase+' in Manhattan tomorrow',[phrase])
            self.assertEqual(r.request.activities,[category])
            self.assertEqual(r.request.activityIntents[category],phrase)

    def test_lookup_lifetime_ceiling_removed_only_in_exploration(self):
        budget=ProviderBudget().outing()
        for i in range(12):
            self.clock+=61
            with budget.reserve('lookup',str(i)):dispatch('search')
        self.assertEqual(budget._searches,12)

    def test_independent_processes_record_all_usage_without_a_cost_cap(self):
        import subprocess
        import sys
        code="from backend.development_cost import DevelopmentCost,dispatch\nwith DevelopmentCost(enforce_limit=False).reserve({'search_pro':1}): dispatch('search')"
        processes=[subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
        for process in processes:
            _,error=process.communicate(timeout=10)
            self.assertEqual(process.returncode,0,error.decode())
        row=json.loads(Path(self.path).read_text())['days'][DevelopmentCost.day()]
        self.assertEqual(row['grossMicrousd'],128000)
        self.assertEqual(row['dispatched'],{'search_pro':4})

    def test_sizes_absent_null_and_volunteered_never_change_planning(self):
        for suffix in ('',' for 2 people',' for 3 people',' for 6 people',' for six of us'):
            result=self.extract('dinner and drinks in Manhattan tomorrow'+suffix,['dinner','drinks'],people=6,uncertainties=['group size is unknown'])
            self.assertIsNotNone(result.request,result.issues)
            self.assertIsNone(result.request.people)
        for count in (None,2,3,6):
            payload={'activities':['coffee'],'date':'2026-11-14'}
            if count is not None:payload['people']=count
            request=OutingRequest(**payload)
            from backend.planner import generate_candidates
            from backend.ranking import rank_candidates
            generated=generate_candidates(request)
            result=rank_candidates(request,generated.candidates)
            selected=result.plans+result.provisionalPlans
            self.assertTrue(selected)
            identities=[p.candidate.id for p in selected]
            if count is None:expected=identities
            self.assertEqual(identities,expected)
            self.assertFalse(any(i.field=='people' for p in selected for i in p.issues))
            self.assertTrue(all(p.groupCost is None for p in selected))

    def test_warning_is_nonblocking_but_direct_guard_and_integrity_remain(self):
        with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':'0.032','WHERETO_DEV_WARN_USD':'0.032'}):
            for _ in range(3):
                o=ProviderBudget().outing()
                with o.reserve('search','new outing'):dispatch('search')
            snapshot=o.usage()
            self.assertEqual(snapshot['estimatedDayGrossUsd'],.096)
            self.assertTrue(snapshot['estimatedUsageWarning'])
            self.assertFalse(snapshot['costAdmissionEnforced'])
            with self.assertRaises(AccountingError):
                with DevelopmentCost().reserve({'search_pro':1}):self.fail()
            Path(self.path).write_text('{broken')
            with self.assertRaises(ProviderLimitError):
                with ProviderBudget().outing().reserve('search','no lost visibility'):self.fail()

    def test_shared_quota_is_actual_lower_project_limit_not_published_3000(self):
        for n in (64,64,22):
            with ProviderBudget().outing().reserve('matrix','per outing',origins=1,destinations=n):pass
        self.assertEqual(DevelopmentCost().minute_capacity(),0)
        with self.assertRaises(ProviderLimitError):
            with ProviderBudget().outing().reserve('matrix','too early',origins=1,destinations=1):self.fail()
        self.clock+=61
        with ProviderBudget().outing().reserve('matrix','later explicit action',origins=1,destinations=1):pass

    def test_fifteen_actions_above_ten_dollars_reuse_pools_and_full_history(self):
        # Invented prior day's-same-calendar usage, preserved rather than reset.
        cost=DevelopmentCost(enforce_limit=False)
        for _ in range(16):
            self.clock+=61
            with cost.reserve({'matrix_element':128}):dispatch('matrix',128)
        before=cost.snapshot()['estimatedDayGrossUsd']
        self.assertGreater(before,10)
        origin={'point':{'id':'authorized-start','coordinates':{'latitude':40.75,'longitude':-73.98}},
            'explicitly_authorized':True,'source':'manual','precision':'address_or_place',
            'geographicDescription':'Synthetic park, New York, NY'}
        with patch('backend.places_transport.text_search',side_effect=neighborhood_fixture) as search,patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            self.clock+=61
            r=real_plans(outing(activities=['food','drinks'],locationFirst=True,startingLocation=origin).model_copy(update={'location':'Midtown Manhattan'}),ProviderBudget())
            seen=set();coverage=[set(),set()];initial_searches=search.call_count
            for action in range(16):
                if action:
                    self.clock+=61
                    r=more_real_plans(r.optionsToken,expand_discovery=False)
                plans=r.plans+r.provisionalPlans+r.explorationPlans
                self.assertEqual(len(plans),3,r.message)
                for p in plans:
                    signature=tuple(v.id for v in p.candidate.venues)
                    self.assertNotIn(signature,seen);seen.add(signature)
                    for i,v in enumerate(p.candidate.venues):coverage[i].add(v.id)
            self.assertEqual(search.call_count,initial_searches)
            self.assertEqual(len(seen),48)
            print('OPEN_EXPLORATION_15',{'first':len(coverage[0]),'later':len(coverage[1]),'complete':len(seen),
                'searches':r.diagnostics['placesSearchRequests'],'elements':r.diagnostics['reservedMatrixElements'],
                'outingGross':r.diagnostics['estimatedOutingGrossUsd'],'dayGross':r.diagnostics['estimatedDayGrossUsd']})
