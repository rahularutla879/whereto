"""Task 50A offline semantic and public-boundary regressions. No providers/SQL."""
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError
from backend.ai import Interpretation, parse_interpretation
from backend.interpretation import InterpretationInput, interpret_request, activity_category
from backend.journey import Journey, LIMITATION, REPHRASE
from backend.journey_fixtures import CASES, FixtureAI, reply

NOW=datetime(2026,11,2,15,tzinfo=timezone.utc)

class JourneyTests(unittest.TestCase):
    def run_case(self,text,data=None,preferences=None):
        p=Mock();p.interpret.return_value=Interpretation.model_validate(data) if data else FixtureAI().interpret(text)
        with patch('requests.sessions.Session.send',side_effect=AssertionError('No network')):
            return interpret_request(InterpretationInput(text=text,preferences=preferences or {}),p,now=NOW)

    def test_all_25_required_scenarios(self):
        self.assertEqual(len(CASES),25)
        for text,data,outcome in CASES:
            with self.subTest(text=text):
                r=self.run_case(text)
                j=r.interpretation.journey
                self.assertEqual(r.interpretation.activities,data['activities'])
                self.assertEqual([s.source for s in j.stops],data['activities'])
                self.assertEqual([s.requirement for s in j.stops],[s.get('requirement','required') for s in data['journey']['stops']])
                self.assertEqual([s.kind for s in j.stops],[s.get('kind','activity') for s in data['journey']['stops']])
                self.assertEqual(j.ordering,data['journey']['ordering'])
                self.assertEqual([(e.before,e.after) for e in j.order],[(e['before'],e['after']) for e in data['journey']['order']])
                self.assertEqual(j.endpoint.model_dump() if j.endpoint else None,data['journey']['endpoint'])
                self.assertEqual(j.total_duration.model_dump() if j.total_duration else None,data['journey']['total_duration'])
                for got,want in zip(j.stops,data['journey']['stops']):
                    self.assertEqual(got.duration.model_dump() if got.duration else None,({'relation':'exact',**want['duration']} if want.get('duration') else None))
                if outcome=='simple': self.assertIsNotNone(r.request,r.issues)
                else: self.assertIsNone(r.request)
                if outcome=='advanced': self.assertEqual(r.unsupported,[LIMITATION]);self.assertFalse(r.questions)
                if outcome=='clarify': self.assertTrue(r.issues);self.assertFalse(r.unsupported)
                if j.deadline: self.assertEqual(j.deadline.minute,1080)

    def test_identity_normalization_preserves_errands_and_meals(self):
        for source,expected in [('get food','food'),('Play a movie','movie'),('groceries','custom:supermarket'),('supermarket','custom:supermarket'),('ATM','custom:atm'),('pharmacy','custom:pharmacy')]:
            self.assertEqual(activity_category(source),expected)

    def test_schema_rejects_bad_references_unknown_keys_and_types(self):
        invalid=[dict(ordering='constrained',order=[{'before':0,'after':3,'source':'then'}]),
            dict(stops=[{'source':'bank','kind':'named_place','place_id':'invented'}]),
            dict(total_duration={'minutes':True,'source':'one minute'}),
            dict(total_duration={'minutes':-30,'source':'30 minutes'}),
            dict(deadline={'source':'by 6 PM','minute':1440})]
        for fields in invalid:
            with self.subTest(fields=fields),self.assertRaises(ValidationError):
                Journey.model_validate({'stops':[{'source':'bank'},{'source':'coffee'}],**fields})

    def test_source_grounding_and_semantic_omissions_block(self):
        for index,mutation in [(2,{'stops':[{'source':'SUNY College of Optometry'}]}),
            (5,{'stops':[{'source':'groceries'},{'source':'coffee'}]}),
            (9,{'endpoint':None}),(11,{'total_duration':None}),
            (13,{'deadline':None}), (7,{'ordering':'unspecified'}),
            (3,{'order':[],'ordering':'unspecified'})]:
            text,data,_=CASES[index]; data=deepcopy(data);data['journey'].update(mutation)
            r=self.run_case(text,data);self.assertIsNone(r.request);self.assertTrue(r.issues)
        text,data,_=CASES[15];data=deepcopy(data)
        data['journey']['stops'][0]['duration']['minutes']=30
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_wrong_duration_assignment_and_invented_endpoints_block(self):
        text,data,_=CASES[14];data=deepcopy(data)
        a,b=data['journey']['stops'];a['duration'],b['duration']=b['duration'],a['duration']
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])
        text,data,_=CASES[7];data=deepcopy(data)
        data['journey']['endpoint']={'kind':'origin','source':'whichever is closer first'}
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_partial_reverse_and_flexible_order_do_not_enter_linear_planner(self):
        for text,data in [
            ('Coffee and museum, dinner after coffee.',reply(['Coffee','museum','dinner'],order=[(0,2,'dinner after coffee')])),
            ('Get dinner before the movie.',reply(['dinner','movie'],order=[(0,1,'dinner before the movie')])),
            ('Movie after dinner.',reply(['Movie','dinner'],order=[(1,0,'Movie after dinner')]))]:
            r=self.run_case(text,data,{'location':'Baltimore','date':'2026-11-07'})
            if len(data['activities'])==2 and data['activities'][0]=='dinner': self.assertIsNotNone(r.request,r.issues)
            else:self.assertEqual(r.unsupported,[LIMITATION])

    def test_ordinary_no_journey_contract_still_works(self):
        r=self.run_case('Coffee in Baltimore tomorrow.',dict(activities=['Coffee'],budget_per_person=None,date=None,location='Baltimore',preferences=[]))
        self.assertIsNotNone(r.request,r.issues)
        self.assertIsNone(r.interpretation.journey)  # Legacy required-list semantics.

    def test_no_missing_advanced_object_is_repaired_into_a_simple_plan(self):
        for index in (2,5,9,11,13,14,15):
            text,data,_=CASES[index];data=deepcopy(data);data.pop('journey')
            self.assertIsNone(self.run_case(text,data).request)

    def test_total_time_is_not_travel_or_an_invented_start(self):
        text='Go to an ATM and return to my starting point in under half an hour tomorrow in Hyderabad.'
        data=reply(['ATM'],location='Hyderabad',dates=['tomorrow'],endpoint={'kind':'origin','source':'return to my starting point'},total={'minutes':30,'relation':'under','source':'in under half an hour'})
        r=self.run_case(text,data)
        self.assertEqual(r.unsupported,[LIMITATION]);self.assertIsNone(r.interpretation.start_time)
        self.assertIsNone(r.interpretation.travel_total_minutes)
        self.assertEqual(r.context.date.isoformat(),'2026-11-03');self.assertEqual(r.context.timezone,'Asia/Kolkata')

    def test_approximate_maximum_and_quick_requests(self):
        for phrase,minutes,relation in [('about two hours',120,'approximate'),('at most 20 minutes',20,'maximum')]:
            text=f'Spend {phrase} at the museum.'
            r=self.run_case(text,reply(['museum'],durations={0:{'minutes':minutes,'relation':relation,'source':phrase}}))
            self.assertEqual(r.unsupported,[LIMITATION])
        r=self.run_case('Have a quick coffee tomorrow in Baltimore.',reply(['quick coffee'],location='Baltimore',dates=['tomorrow']))
        self.assertIsNone(r.interpretation.journey.stops[0].duration)

    def test_named_branch_brand_and_prescription_no_inventory_claim(self):
        text='Go to the Walmart on Route 440.'
        r=self.run_case(text,reply(['Walmart on Route 440'],kinds={0:'named_place'}))
        self.assertEqual(r.unsupported,[LIMITATION])
        text='I want to stop at the pharmacy and definitely pick up my prescription.'
        r=self.run_case(text,reply(['pharmacy']))
        self.assertEqual(r.interpretation.journey.stops[0].requirement,'required')
        self.assertIsNone(r.request)
        self.assertNotIn('available',' '.join(r.notes))

    def test_duplicate_keys_remain_rejected_inside_journey(self):
        with self.assertRaises(ValueError):parse_interpretation('{"journey":{"stops":[],"stops":[]}}')

    def test_home_origin_requires_explicit_establishment(self):
        for prefix,kind in [('', 'home'),('Starting from home, ', 'origin')]:
            text=prefix+'get coffee and return home.'
            r=self.run_case(text,reply(['coffee'],endpoint={'kind':'home','source':'return home'}))
            self.assertEqual(r.interpretation.journey.endpoint.kind,kind)
            self.assertIsNone(r.request)
            self.assertEqual(bool(r.unsupported),kind=='origin')

    def test_generic_final_destination_is_distinct_from_exact_endpoint(self):
        r=self.run_case('Go to the bank and finish at a train station.',reply(['bank'],endpoint={'kind':'activity','source':'finish at a train station'}))
        self.assertEqual(r.interpretation.journey.endpoint.kind,'activity')
        self.assertEqual(r.unsupported,[LIMITATION])

    def test_simple_activity_followup_keeps_source_journey_and_explicit_correction(self):
        text,data,_=CASES[24]
        initial=self.run_case(text,data)
        self.assertIsNotNone(initial.pending)
        r=interpret_request(InterpretationInput(text=text,pending=initial.pending,
            answers={'activities':'Coffee','location':'Baltimore'}),Mock(),now=NOW)
        self.assertIsNotNone(r.request,r.issues)
        self.assertEqual(r.interpretation.activities,['Coffee'])
        self.assertEqual([s.source for s in r.interpretation.journey.stops],['Coffee'])
        self.assertEqual(r.pending.interpretation.journey.stops[0].source,'somewhere nice')
        self.assertEqual(r.pending.answers.activities,'Coffee')

    def test_clock_windows_are_not_stop_order_constraints(self):
        text='Coffee and dinner in Baltimore tomorrow after 6 PM before 10 PM.'
        data=reply(['Coffee','dinner'],location='Baltimore',dates=['tomorrow'])
        data['time_expressions']=['after 6 PM','before 10 PM']
        r=self.run_case(text,data)
        self.assertIsNotNone(r.request,r.issues)
        self.assertEqual(r.interpretation.journey.order,[])

    def test_arrival_time_cannot_become_whole_trip_deadline(self):
        r=self.run_case('Coffee at 6 PM in Baltimore tomorrow.',reply(['Coffee'],location='Baltimore',dates=['tomorrow'],deadline={'source':'6 PM'}))
        self.assertEqual(r.issues,[REPHRASE])

    def test_grounded_endpoint_and_generic_label_normalization(self):
        text='Go to the museum, then get coffee, then go home.'
        data=reply(['museum','coffee','go home'],order=[(0,1,text),(1,2,text)])
        r=self.run_case(text,data)
        self.assertEqual(r.interpretation.activities,['museum','coffee'])
        self.assertEqual(r.interpretation.journey.endpoint.kind,'home')
        self.assertEqual([(e.before,e.after) for e in r.interpretation.journey.order],[(0,1)])
        self.assertIsNone(r.request)
        text='Visit the bank and grocery store, whichever is closer first.'
        r=self.run_case(text,reply(['bank','grocery store'],kinds={1:'brand'},ordering='flexible'))
        self.assertEqual(r.interpretation.journey.stops[1].kind,'activity')
        self.assertEqual(r.unsupported,[LIMITATION])

    def test_nested_provider_instances_are_revalidated(self):
        ai=Interpretation.model_validate(reply(['coffee']))
        ai.journey.stops[0].source=None
        with self.assertRaises(ValidationError):Interpretation.model_validate(ai)
        with self.assertRaises(ValidationError):
            Journey.model_validate({'stops':[{'source':'Zara'},{'source':'Nike'}],'shared_place':{'stops':[True,0],'source':'same mall'}})

    def test_required_optional_defaults_and_partial_assignment(self):
        text='I need groceries and lunch, and if there is time, coffee.'
        data=reply(['groceries','lunch','coffee'],optional={2:'if there is time, coffee'})
        r=self.run_case(text,data)
        self.assertEqual([s.requirement for s in r.interpretation.journey.stops],['required','required','optional'])
        self.assertEqual(r.unsupported,[LIMITATION])
        data['journey']['stops'][0].update(requirement='optional',evidence='if there is time, coffee')
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_conflicting_order_retains_both_requirements_and_never_executes(self):
        text='Visit the pharmacy before the bank, but the bank before the pharmacy.'
        data=reply(['pharmacy','bank'],order=[(0,1,text),(1,0,text)])
        r=self.run_case(text,data)
        self.assertIsNone(r.request)
        self.assertEqual(r.issues,[REPHRASE])
        self.assertTrue(r.interpretation.journey.order_conflict)
        self.assertEqual(len(r.interpretation.journey.order),2)
        for mode in ('unspecified','flexible'):
            data['journey'].update(ordering=mode,order=[{'before':0,'after':1,'source':text}])
            self.assertTrue(self.run_case(text,data).interpretation.journey.order_conflict)

    def test_afternoon_keeps_the_day_and_clarifies_only_the_window(self):
        text,data,_=CASES[21]
        r=self.run_case(text,data)
        self.assertFalse(any(q.field=='date' for q in r.questions))
        self.assertTrue(any(q.field=='time' for q in r.questions))
        self.assertEqual(r.pending.interpretation.date_expressions,['tomorrow afternoon','tomorrow'])

    def test_named_stop_is_not_an_invented_city_or_generic_geographic_activity(self):
        text,data,_=CASES[2]
        data=deepcopy(data);data['location']='SUNY College of Optometry'
        r=self.run_case(text,data)
        self.assertIsNone(r.interpretation.location)
        self.assertEqual(r.interpretation.journey.stops[0].kind,'named_place')
        self.assertEqual(r.unsupported,[LIMITATION])

    def test_qualified_deadline_keeps_date_and_destination_timezone(self):
        text='Coffee and return to my starting point by 6 PM tomorrow in Hyderabad.'
        data=reply(['Coffee'],location='Hyderabad',dates=['tomorrow'],endpoint={'kind':'origin','source':'return to my starting point'},deadline={'source':'by 6 PM'})
        r=self.run_case(text,data)
        self.assertEqual(r.context.date.isoformat(),'2026-11-03')
        self.assertEqual(r.context.timezone,'Asia/Kolkata')
        self.assertEqual(r.interpretation.journey.deadline.minute,1080)
        self.assertIsNone(r.interpretation.start_time)
        self.assertEqual(r.unsupported,[LIMITATION])

    def test_original_named_place_capitalization_is_restored_from_source(self):
        text='Go to SUNY College of Optometry.'
        data=reply(['suny college of optometry'],kinds={0:'named_place'})
        r=self.run_case(text,data)
        self.assertEqual(r.interpretation.activities,['SUNY College of Optometry'])
        self.assertEqual(r.interpretation.journey.stops[0].source,'SUNY College of Optometry')
        self.assertEqual(r.unsupported,[LIMITATION])

    def test_bare_brand_cannot_bypass_existing_brand_verification(self):
        r=self.run_case('Visit Zara.',reply(['Zara'],kinds={0:'brand'}))
        self.assertEqual(r.unsupported,[LIMITATION])
        text='Zara outlet tomorrow in Jersey City.'
        r=self.run_case(text,reply(['Zara outlet'],kinds={0:'brand'},location='Jersey City',dates=['tomorrow']))
        self.assertIsNotNone(r.request,r.issues)
        self.assertEqual(r.request.activityIntents['custom:zara outlet'],'Zara outlet')

    def test_branching_partial_order_is_not_mistaken_for_a_full_sequence(self):
        text='Coffee, museum after coffee, dinner after coffee.'
        data=reply(['Coffee','museum','dinner'],order=[(0,1,'museum after coffee'),(0,2,'dinner after coffee')])
        r=self.run_case(text,data)
        self.assertEqual(r.unsupported,[LIMITATION])
        self.assertEqual(len(r.interpretation.journey.order),2)

    def test_explicit_home_address_is_a_transient_exact_endpoint(self):
        text='Coffee, then return home at 123 Synthetic Street.'
        r=self.run_case(text,reply(['Coffee'],endpoint={'kind':'named_place','source':'return home at 123 Synthetic Street'}))
        self.assertEqual(r.unsupported,[LIMITATION])
        self.assertEqual(r.interpretation.journey.endpoint.source,'return home at 123 Synthetic Street')
        self.assertIsNone(r.pending)

    def test_same_final_home_reference_cannot_be_both_a_stop_and_endpoint(self):
        text='Go to the museum, then get coffee, then go home.'
        data=reply(['museum','coffee','go home'],order=[(0,1,text),(1,2,text)],endpoint={'kind':'home','source':'go home'})
        r=self.run_case(text,data)
        self.assertEqual(r.interpretation.activities,['museum','coffee'])
        self.assertEqual(len(r.interpretation.journey.stops),2)
        self.assertEqual(r.interpretation.journey.endpoint.source,'go home')

    def test_advanced_mode_validation_reuses_negation_and_mixed_mode_policy(self):
        r=self.run_case('Drive to the bank, not walking, then return to my starting point.',reply(['bank'],transport='driving',endpoint={'kind':'origin','source':'return to my starting point'}))
        self.assertEqual(r.unsupported,[LIMITATION])
        r=self.run_case('Drive to the bank, then walk to a café.',reply(['bank','café'],transport='driving',order=[(0,1,'Drive to the bank, then walk to a café')]))
        self.assertIsNone(r.interpretation.transport)
        self.assertIsNone(r.request)
        self.assertIn('mixed travel modes',r.issues[0])
        r=self.run_case('Walk to a grocery store and return home.',reply(['grocery store'],endpoint={'kind':'home','source':'return home'}))
        self.assertEqual(r.interpretation.transport,'walking')

    def test_advanced_context_retains_existing_origin_geography_and_travel_preferences(self):
        text='Coffee and return to my starting point tomorrow in Washington, DC. First stop within 10 minutes, between stops about 5 miles. No Virginia. Starting from Synthetic Park.'
        data=reply(['Coffee'],location='Washington, DC',dates=['tomorrow'],endpoint={'kind':'origin','source':'return to my starting point'})
        r=self.run_case(text,data,{'transport':'walking'})
        self.assertEqual(r.unsupported,[LIMITATION])
        self.assertEqual(r.context.date.isoformat(),'2026-11-03')
        self.assertEqual(r.context.timezone,'America/New_York')
        self.assertEqual((r.context.firstTravel.value,r.context.firstTravel.mode),(10,'strict'))
        self.assertEqual((r.context.betweenTravel.value,r.context.betweenTravel.unit,r.context.betweenTravel.mode),(5,'miles','flexible'))
        self.assertEqual(r.context.geography.excludedRegions,['VA'])
        self.assertEqual(r.context.originText,'Synthetic Park')
        self.assertEqual(r.context.transport,'walking')
        self.assertIsNone(r.request)

    def test_dropped_errands_and_coalesced_errands_cannot_produce_partial_plans(self):
        text='Buy groceries and stop at an ATM tomorrow in Baltimore.'
        r=self.run_case(text,reply(['groceries'],location='Baltimore',dates=['tomorrow']))
        self.assertIsNone(r.request)
        self.assertEqual(r.issues,[REPHRASE])
        text='Buy groceries and stop at an ATM, then return to my starting point.'
        r=self.run_case(text,reply(['groceries'],endpoint={'kind':'origin','source':'return to my starting point'}))
        self.assertEqual(r.issues,[REPHRASE])
        self.assertIsNone(activity_category('pharmacy and grocery store'))

    def test_order_references_and_geographic_names_are_not_extra_activities(self):
        text='Pharmacy before bank, bank before coffee in Baltimore tomorrow.'
        data=reply(['Pharmacy','bank','coffee'],location='Baltimore',dates=['tomorrow'],order=[(0,1,'Pharmacy before bank'),(1,2,'bank before coffee')])
        r=self.run_case(text,data)
        self.assertIsNotNone(r.request,r.issues)
        self.assertEqual(len(r.request.activities),3)
        text='Coffee in Central Park tomorrow.'
        r=self.run_case(text,reply(['Coffee'],location='Central Park',dates=['tomorrow']))
        self.assertFalse(any('omitted' in issue for issue in r.issues))

    def test_maybe_bookstore_after_lunch_keeps_optionality_on_the_bookstore(self):
        text='Maybe visit a bookstore after lunch.'
        data=reply(['bookstore','lunch'],order=[(1,0,text)],optional={0:text})
        r=self.run_case(text,data)
        self.assertEqual(r.unsupported,[LIMITATION])
        self.assertEqual([s.requirement for s in r.interpretation.journey.stops],['optional','required'])
        data=reply(['bookstore','lunch'],order=[(1,0,text)],optional={1:text})
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_final_named_place_words_are_not_extra_discoverable_activities(self):
        text='Coffee and finish at the Museum of Modern Art.'
        r=self.run_case(text,reply(['Coffee'],endpoint={'kind':'named_place','source':'finish at the Museum of Modern Art'}))
        self.assertEqual(r.unsupported,[LIMITATION])
        self.assertEqual(len(r.interpretation.journey.stops),1)

    def test_origin_reference_cannot_hide_a_dropped_required_errand(self):
        text='Coffee in Baltimore tomorrow, starting from Synthetic Park and stop at an ATM.'
        r=self.run_case(text,reply(['Coffee'],location='Baltimore',dates=['tomorrow']))
        self.assertIsNone(r.request)
        self.assertEqual(r.issues,[REPHRASE])

    def test_explicit_duration_recovery_requires_unambiguous_source_scope(self):
        text='Get groceries and return home within 45 minutes.'
        data=reply(['groceries'],endpoint={'kind':'home','source':'return home'})
        r=self.run_case(text,data)
        self.assertEqual((r.interpretation.journey.total_duration.minutes,r.interpretation.journey.total_duration.relation),(45,'maximum'))
        text='Spend 20 minutes shopping and five minutes at an ATM.'
        r=self.run_case(text,reply(['shopping','ATM']))
        self.assertEqual([s.duration.minutes for s in r.interpretation.journey.stops],[20,5])
        text='I have about two hours for groceries and lunch.'
        r=self.run_case(text,reply(['groceries','lunch']))
        self.assertEqual((r.interpretation.journey.total_duration.minutes,r.interpretation.journey.total_duration.relation),(120,'approximate'))
        self.assertEqual(r.unsupported,[LIMITATION])
        for text in ['Spend -5 minutes at the museum.','Spend negative five minutes at the museum.','Spend 20000 minutes at the museum.','Museum in 20 minutes.']:
            self.assertEqual(self.run_case(text,reply(['museum'])).issues,[REPHRASE])

    def test_indefinite_generic_venue_is_not_an_exact_establishment(self):
        text='Walk to a grocery store and return home.'
        r=self.run_case(text,reply(['grocery store'],kinds={0:'named_place'},endpoint={'kind':'home','source':'return home'}))
        self.assertEqual(r.interpretation.journey.stops[0].kind,'activity')
        self.assertEqual(r.interpretation.transport,'walking')
        from backend.retail import intent
        self.assertIsNone(intent(activity_category('groceries')))

    def test_whole_journey_minutes_cannot_also_be_invented_travel_or_dwell(self):
        text='I have about two hours for groceries and lunch.'
        data=reply(['groceries','lunch'],total={'minutes':120,'relation':'approximate','source':'about two hours'})
        data['travel_total_minutes']=120
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])
        data['travel_total_minutes']=None
        data['journey']['stops'][0]['duration']={'minutes':120,'relation':'approximate','source':'about two hours'}
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_strict_return_clock_deadline_cannot_become_a_generic_window(self):
        text='Be back home before 6 PM.'
        data=reply([],endpoint={'kind':'home','source':'back home'},deadline={'source':'before 6 PM','relation':'before'})
        r=self.run_case(text,data)
        self.assertEqual(r.interpretation.journey.deadline.minute,1080)
        self.assertEqual(r.interpretation.time_expressions,[])
        data['journey']['deadline']=None
        self.assertEqual(self.run_case(text,data).issues,[REPHRASE])

    def test_full_deadline_clause_preserves_dates_and_explicit_timezone_wording(self):
        for suffix,day in [('on 2026-11-07','2026-11-07'),('PST tomorrow','2026-11-03')]:
            text=f'Coffee and return to my starting point by 6 PM {suffix} in Hyderabad.'
            data=reply(['Coffee'],location='Hyderabad',endpoint={'kind':'origin','source':'return to my starting point'},deadline={'source':f'by 6 PM {suffix}'})
            r=self.run_case(text,data)
            self.assertEqual(r.context.date.isoformat(),day)
            self.assertEqual(r.interpretation.journey.deadline.minute,1080)
            if 'PST' in suffix:
                self.assertTrue(any('timezone' in issue for issue in r.context.issues))
            else:self.assertEqual(r.interpretation.time_expressions,[])
