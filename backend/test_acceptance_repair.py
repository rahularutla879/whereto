"""Task 50E owner regressions: real Qwen-shaped extraction, blocked Google."""
import json
from datetime import datetime,timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput,interpret_request
from backend.advanced_planning import AdvancedInput
from backend import test_advanced_planning as integration
from backend.test_advanced_routing import start

class InterpretationRepairTests(unittest.TestCase):
    def test_actual_owner_extractions_keep_coherent_requirements(self):
        fixtures=json.loads(Path(__file__).with_name('repair_extractions.json').read_text())
        for row in fixtures:
            with self.subTest(text=row['text']):
                class Fixed:
                    def interpret(self,text):return Interpretation.model_validate(row['raw'])
                r=interpret_request(InterpretationInput(text=row['text']),Fixed(),now=datetime(2026,11,3,15,tzinfo=timezone.utc))
                if 'be back within 3 hours' in row['text'] or 'and return within an hour' in row['text']:
                    self.assertEqual([q.field for q in r.questions],['endpoint'])
                    self.assertEqual(r.interpretation.journey.total_duration.minutes,60 if 'within an hour' in row['text'] else 180)
                    self.assertEqual(r.interpretation.journey.total_duration.relation,'maximum')
                else:self.assertNotEqual(r.executionStatus,'clarification_required',r.issues)
                if row['text'].startswith('dinner and bowling'):
                    self.assertIsNotNone(r.request);self.assertEqual(r.request.activities,['food','bowling'])
                if 'within 45' in row['text']:
                    self.assertEqual(r.interpretation.journey.stops[1].duration.minutes,5)
                    self.assertEqual(r.interpretation.journey.total_duration.relation,'maximum')

class FlowRepairTests(unittest.TestCase):
    def setUp(self):
        self.h=integration.IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def test_named_identity_establishes_local_tomorrow_without_date_question(self):
        s=self.h.session();s.text='Go to SUNY College of Optometry, then get coffee tomorrow.'
        s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.requires_date_confirmation=True
        r=self.h.run_session(s)
        self.assertEqual(r.status,'results');self.assertEqual(r.date,'2026-11-03')
        self.assertEqual(s.context.timezone,'America/New_York')
    def test_exploration_offers_further_nonduplicate_assignments(self):
        from copy import deepcopy
        for i in range(8):
            p=deepcopy(self.h.records[1]);p['id']=f'Synthetic_coffee_{i}';p['displayName']['text']=f'Synthetic coffee cafe {i}';p['formattedAddress']=f'{i+10} Fixture Road, New York';self.h.records.append(p)
        s=self.h.session();a=self.h.run_session(s)
        searches=len(self.h.searches)
        b=self.h.run_session(s,action='different')
        self.assertTrue(b.options);self.assertTrue(set(o.id for o in a.options).isdisjoint(o.id for o in b.options))
        self.assertEqual(len(self.h.searches),searches)

class ContinuationRepairTests(FlowRepairTests):
    def test_multiple_pages_reuse_routes_and_keep_fixed_college(self):
        from copy import deepcopy
        for i in range(8):
            p=deepcopy(self.h.records[1]);p['id']=f'Synthetic_extra_{i}';p['displayName']['text']=f'Invented cafe {i}';p['formattedAddress']=f'{10+i} Fixture Road, New York';self.h.records.append(p)
        s=self.h.session(endpoint={'kind':'origin','source':'return'})
        pages=[self.h.run_session(s,startingLocation=start())]
        searches=len(self.h.searches)
        for _ in range(2):pages.append(self.h.run_session(s,startingLocation=start(),action='different'))
        ids=[o.id for p in pages for o in p.options]
        self.assertEqual(len(ids),9);self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(searches,len(self.h.searches))
        for p in pages:
            self.assertLessEqual(len(p.options),3)
            for o in p.options:
                self.assertEqual(o.stops[0].placeId,'Synthetic_college');self.assertEqual(o.ending,'origin');self.assertEqual(o.legs[-1].role,'return_to_origin')
        directed=[]
        for call in self.h.calls:
            for a in call['origins']:
                for b in call['destinations']:directed.append((str(a),str(b)))
        self.assertEqual(len(directed),len(set(directed)))
    def test_explicit_discovery_adds_candidates_without_replacing_named_stop(self):
        s=self.h.session();a=self.h.run_session(s)
        from copy import deepcopy
        extra=deepcopy(self.h.records[1]);extra['id']='Synthetic_new_cafe';extra['displayName']['text']='New invented cafe';extra['formattedAddress']='20 Fixture Road, New York'
        self.h.records.append(extra)
        count=len(self.h.searches)
        b=self.h.run_session(s,action='discover')
        self.assertGreater(len(self.h.searches),count)
        self.assertTrue(b.options);self.assertEqual(b.options[0].stops[0].placeId,'Synthetic_college')
        self.assertEqual(sum('SUNY' in q['textQuery'] for q in self.h.searches),1)
    def test_explicit_exception_keeps_original_limit_and_excludes_hard_deadline_failure(self):
        s=self.h.session(endpoint={'kind':'origin','source':'return'},total_duration={'minutes':45,'relation':'maximum','source':'within 45 minutes'})
        config={'startingLocation':start(),'firstTravel':{'value':0,'unit':'minutes','mode':'strict'}}
        a=self.h.run_session(s,**config);self.assertEqual(a.options,[]);self.assertTrue(a.canShowBeyond)
        count=len(self.h.calls)
        b=self.h.run_session(s,action='beyond',**config)
        self.assertTrue(b.options[0].travelException);self.assertEqual(b.options[0].routeState,'beyond_limit');self.assertEqual(b.options[0].state,'unverified')
        self.assertEqual(count,len(self.h.calls));self.assertEqual(s.context.firstTravel.value,0)
        s=self.h.session(endpoint={'kind':'origin','source':'return'},total_duration={'minutes':1,'relation':'maximum','source':'within 1 minute'})
        a=self.h.run_session(s,**config);self.assertFalse(a.canShowBeyond)
        b=self.h.run_session(s,action='beyond',**config);self.assertFalse(b.options)
    def test_invalid_date_can_be_corrected_with_natural_answer(self):
        s=self.h.session([{'source':'coffee'}]);s.context.date=None
        a=self.h.run_session(s,date='2026-99-99');self.assertEqual(a.status,'clarification');self.assertEqual(len(self.h.searches),0)
        b=self.h.run_session(s,date='tomorrow');self.assertEqual(b.status,'results');self.assertEqual(b.date,'2026-11-03')
    def test_named_choices_and_search_area_do_not_erase_tomorrow(self):
        s=self.h.session([{'source':'grocery shopping'}],endpoint={'kind':'origin','source':'return'})
        s.text='Go grocery shopping tomorrow and return to where I started.';s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.requires_date_confirmation=True
        a=self.h.run_session(s,startingLocation=start());self.assertEqual(a.questions[0]['field'],'destination')
        b=self.h.run_session(s,startingLocation=start(),destination='New York');self.assertEqual(b.date,'2026-11-03');self.assertEqual(b.options[0].ending,'origin')
    def test_recoverable_admission_preserves_candidates_and_reuses_successful_pairs(self):
        from time import monotonic
        s=self.h.session();s.outing._session._matrix_window.append((monotonic(),150))
        self.h.run_session(s);s.outing._session._matrix_window.clear()
        a=self.h.run_session(s,action='different');self.assertTrue(a.options)
        self.assertTrue(all(l.seconds is not None for l in a.options[0].legs))
    def test_structural_authority_expiry_and_lock_remain(self):
        import secrets
        from backend.advanced_planning import sessions
        s=self.h.session();sessions.items[s.token]=s
        self.addCleanup(sessions.items.pop,s.token,None)
        s.lock.acquire()
        from backend.places import DiscoveryError
        with self.assertRaises(DiscoveryError):sessions.run(AdvancedInput(token=s.token,action='different'))
        s.lock.release();s.expires=0
        with self.assertRaises(ValueError):sessions.run(AdvancedInput(token=s.token,action='different'))
        for payload in ({'routes':[]},{'verified':True},{'journey':{}},{'action':'unlimited'}):
            with self.assertRaises(ValueError):AdvancedInput(token=secrets.token_urlsafe(32),**payload)

class OriginCalendarRepairTests(FlowRepairTests):
    def test_deliberate_nearby_choice_reuses_verified_lookup_calendar_only(self):
        from backend.starting_places import lookup_starting_places,StartingPlaceQuery,_calendars
        from backend.test_stop_resolution import place
        from backend.provider_budget import ProviderBudget,ProviderSettings
        with patch('backend.places_transport.text_search',return_value={'places':[place('Synthetic_origin','Invented public origin',types=['establishment'])]}),patch.dict('os.environ',WHERETO_START_LOOKUP_DEV='1'):
            lookup_starting_places(StartingPlaceQuery(query='Invented public origin'),ProviderBudget(ProviderSettings(mode='real')))
        s=self.h.session([{'source':'grocery shopping'}],endpoint={'kind':'origin','source':'return'})
        s.text='Go grocery shopping tomorrow and return to where I started.'
        s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.requires_date_confirmation=True
        origin=start().model_copy(update={'source':'manual'})
        a=self.h.run_session(s,startingLocation=origin,searchNearOrigin=True)
        self.assertEqual(a.status,'results');self.assertEqual(a.date,'2026-11-03');self.assertEqual(s.context.timezone,'America/New_York')
        self.assertEqual(s.context.destination,'Near confirmed starting point')
        self.assertNotIn('latitude',a.model_dump_json())
        _calendars.clear()
    def test_device_coordinates_cannot_invent_a_destination_calendar(self):
        s=self.h.session([{'source':'grocery shopping'}],endpoint={'kind':'origin','source':'return'})
        s.text='Go grocery shopping tomorrow and return to where I started.'
        s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.requires_date_confirmation=True
        from copy import deepcopy
        self.h.records=deepcopy(self.h.records)
        for record in self.h.records:
            record['formattedAddress']='Unverified calendar area'
            record.pop('timeZone',None)
        a=self.h.run_session(s,startingLocation=start(),searchNearOrigin=True)
        self.assertEqual(a.status,'clarification');self.assertEqual(a.questions[0]['field'],'date')
        self.assertGreater(len(self.h.searches),0)

class OrdinaryParityMatrixTests(unittest.TestCase):
    def test_pre50a_source_order_matrix_survives_redundant_qwen_edges(self):
        rows=[['dinner','bowling'],['dinner','drinks'],['movie'],['coffee','museum'],['bowling','drinks','movie','coffee'],['coffee','museum','coffee'],['Zara outlet'],['shopping']]
        for activities in rows:
            for mode in ('driving','walking'):
                text=' and '.join(activities)+' tomorrow in Jersey City'
                raw={'activities':activities,'people':None,'budget_per_person':None,'date':None,'location':'Jersey City','preferences':[],
                     'date_expressions':['tomorrow'],'journey':{'stops':[{'source':a,'kind':'brand' if a=='Zara outlet' else 'activity'} for a in activities],
                     'order':[{'before':i,'after':i+1,'source':text} for i in range(len(activities)-1)],'ordering':'constrained' if len(activities)>1 else 'unspecified'}}
                class Fixed:
                    def interpret(self,text):return Interpretation.model_validate(raw)
                with self.subTest(activities=activities,mode=mode):
                    r=interpret_request(InterpretationInput(text=text,preferences={'transport':mode,'travel':'20'}),Fixed(),now=datetime(2026,11,3,15,tzinfo=timezone.utc))
                    self.assertIsNotNone(r.request,r.issues);self.assertEqual(len(r.request.activities),len(activities))
                    self.assertEqual(r.request.calendarTimezone,'America/New_York');self.assertEqual(str(r.request.date),'2026-11-04')
                    self.assertEqual(r.request.transport,mode);self.assertEqual(r.request.travel,20)

class DateCorrectionRepairTests(FlowRepairTests):
    def test_corrected_date_clears_only_date_failures_not_unrelated_requirements(self):
        s=self.h.session();s.context.date=None
        s.context.dateIssues=['A year is needed.'];s.context.issues=['A year is needed.']
        a=self.h.run_session(s);self.assertIn('year',a.message)
        b=self.h.run_session(s,date='2026-11-07');self.assertEqual(b.status,'results')
        s=self.h.session();s.context.date=None;s.context.dateIssues=['A year is needed.'];s.context.issues=['A year is needed.','Mixed modes need clarification.']
        b=self.h.run_session(s,date='2026-11-07');self.assertEqual(b.status,'unsupported');self.assertIn('Mixed modes',b.message)
    def test_verified_local_calendar_clears_stale_utc_past_date_issue(self):
        s=self.h.session();s.text='Go to SUNY College of Optometry, then get coffee today.'
        s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.context.date=__import__('datetime').date(2026,11,2)
        s.context.dateIssues=['That date has already passed.'];s.context.issues=list(s.context.dateIssues);s.date_answer=True
        with patch('backend.advanced_planning.datetime',wraps=datetime) as clock:
            clock.now.side_effect=lambda tz=None:datetime(2026,11,3,2,tzinfo=timezone.utc).astimezone(tz or timezone.utc)
            a=self.h.run_session(s)
        self.assertEqual(a.status,'results');self.assertEqual(a.date,'2026-11-02')

class BeyondDiscoveryRepairTests(FlowRepairTests):
    def test_discovery_under_explicit_exception_keeps_search_and_original_limit(self):
        from copy import deepcopy
        s=self.h.session();config={'startingLocation':start(),'firstTravel':{'value':0,'mode':'strict','unit':'minutes'}}
        self.h.run_session(s,**config)
        a=self.h.run_session(s,action='beyond',**config);self.assertTrue(a.options[0].travelException)
        extra=deepcopy(self.h.records[1]);extra['id']='Synthetic_beyond_new';extra['displayName']['text']='New invented cafe';extra['formattedAddress']='50 Fixture Road, New York';self.h.records.append(extra)
        searches=len(self.h.searches)
        b=self.h.run_session(s,action='discover',includeBeyond=True,**config)
        self.assertGreater(len(self.h.searches),searches);self.assertTrue(b.options[0].travelException)
        self.assertEqual(s.context.firstTravel.value,0);self.assertEqual(b.options[0].stops[0].placeId,'Synthetic_college')
    def test_infeasible_cached_paths_do_not_stall_further_route_batches(self):
        from copy import deepcopy
        for i in range(8):
            p=deepcopy(self.h.records[1]);p['id']=f'Synthetic_coffee_{i}';p['displayName']['text']=f'Invented cafe {i}';p['formattedAddress']=f'{10+i} Fixture Road, New York';self.h.records.append(p)
        for identity in ['Synthetic_coffee','Synthetic_coffee_0','Synthetic_coffee_1','Synthetic_coffee_2']:
            self.h.values[('DRIVE','Synthetic_college',identity)]=600
        s=self.h.session([{'source':'SUNY College of Optometry','kind':'named_place','duration':{'minutes':1,'relation':'exact','source':'1 minute'}},{'source':'coffee','duration':{'minutes':1,'relation':'exact','source':'1 minute'}}],total_duration={'minutes':5,'relation':'maximum','source':'within 5 minutes'})
        a=self.h.run_session(s);self.assertFalse(a.options);self.assertTrue(a.canExpand)
        count=len(self.h.searches)
        b=self.h.run_session(s,action='different');self.assertTrue(b.options)
        self.assertEqual(count,len(self.h.searches));self.assertTrue(all(o.durationState=='feasible' for o in b.options))
    def test_flexible_preference_excess_is_visible_without_waiving_its_maximum(self):
        self.h.values[('DRIVE','origin','Synthetic_college')]=180
        s=self.h.session();a=self.h.run_session(s,startingLocation=start(),firstTravel={'value':2,'unit':'minutes','mode':'flexible'})
        self.assertTrue(a.options);self.assertFalse(a.options[0].travelException)
        self.assertIn('preferred 2',a.options[0].travelDeviations[0]);self.assertIn('maximum 4',a.options[0].travelDeviations[0])
    def test_order_optional_and_repeated_requirements_survive_further_pages(self):
        from copy import deepcopy
        for original in [self.h.records[1],self.h.records[2],self.h.records[3]]:
            for i in range(3):
                p=deepcopy(original);p['id']+=f'_extra_{i}';p['displayName']['text']+=f' branch {i}';p['formattedAddress']=f'{30+i} Fixture Road, New York';self.h.records.append(p)
        cases=[(['pharmacy','bank','grocery shopping'],'constrained',[(0,1)],None),(['bank','grocery shopping'],'flexible',[],None),(['grocery shopping','bank','coffee'],'constrained',[(0,1)],2),(['coffee','coffee'],'unspecified',[],None)]
        for labels,ordering,edges,optional in cases:
            with self.subTest(labels=labels,ordering=ordering):
                stops=[{'source':label,'requirement':'optional' if n==optional else 'required','duration':{'minutes':5,'source':'five minutes'}} for n,label in enumerate(labels)]
                s=self.h.session(stops,ordering=ordering,order=[{'before':a,'after':b,'source':'source precedence'} for a,b in edges],endpoint={'kind':'origin','source':'return'},total_duration={'minutes':45,'relation':'maximum','source':'within 45 minutes'})
                pages=[self.h.run_session(s,startingLocation=start())];count=len(self.h.searches)
                pages+=[self.h.run_session(s,startingLocation=start(),action='different') for _ in range(2)]
                offered=[p for page in pages for p in page.options]
                self.assertGreater(len(offered),3);self.assertEqual(len({p.id for p in offered}),len(offered));self.assertEqual(count,len(self.h.searches))
                for p in offered:
                    indexes=[v.occurrence for v in p.stops]
                    self.assertTrue({i for i in range(len(stops)) if i!=optional}<=set(indexes))
                    self.assertEqual(len({v.placeId for v in p.stops}),len(p.stops));self.assertEqual(p.ending,'origin');self.assertEqual(p.durationState,'feasible')
                    self.assertTrue(all(indexes.index(a)<indexes.index(b) for a,b in edges));self.assertTrue(all(o['occurrence']==optional for o in p.omitted))
