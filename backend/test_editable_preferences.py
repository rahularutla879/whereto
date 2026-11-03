"""Task50E structured edits; invented provider evidence, real sends forbidden."""
import unittest
from unittest.mock import patch
from backend import test_advanced_planning as fixtures
from backend.journey import Duration
from backend.test_advanced_routing import start
from backend.test_advanced_timing import duration
from backend.saved_plans import receipts,SaveRequest,SavedDocument
from backend.advanced_planning import AdvancedInput

class EditablePreferencesTests(unittest.TestCase):
    def setUp(self):
        self.h=fixtures.IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def session(self,**kwargs):
        return self.h.session([{'source':'grocery shopping'},{'source':'ATM','duration':duration(5,'exact')}],endpoint={'kind':'origin','source':'return to where I started'},total_duration=duration(45,'maximum'),**kwargs)
    def run_edit(self,s,**edits):return self.h.run_session(s,startingLocation=start(),edits=edits)
    def counts(self):return len(self.h.searches),len(self.h.calls)
    def test_twenty_to_ten_same_session_no_model_or_provider_and_original_preserved(self):
        s=self.session();self.h.run_session(s,startingLocation=start());before=self.counts()
        with patch('backend.interpretation.create_provider',side_effect=AssertionError('No second model')):
            twenty=self.run_edit(s,dwell=[dict(occurrence=0,minutes=20,relation='exact')])
            ten=self.run_edit(s,dwell=[dict(occurrence=0,minutes=10,relation='exact')])
        self.assertEqual(self.counts(),before)
        for r,expected in [(twenty,20),(ten,10)]:
            p=r.options[0];self.assertEqual([x.duration.minutes for x in p.stops],[expected,5]);self.assertEqual(p.ending,'origin')
            self.assertEqual(p.totalConstraint.minutes,45);self.assertEqual(p.budgetScope,'outing');self.assertEqual(p.durationState,'feasible')
            self.assertEqual(p.elapsedLowerSeconds,360+(expected+5)*60)
            self.assertEqual(r.preferences['stops'][0]['duration']['minutes'],expected)
        self.assertIsNone(s.journey.stops[0].duration);self.assertEqual(s.journey.stops[1].duration.minutes,5)
    def test_travel_only_preserves_required_visits_with_unknown_dwell(self):
        s=self.session();self.h.run_session(s,startingLocation=start());before=self.counts()
        r=self.run_edit(s,budgetScope='travel');p=r.options[0]
        self.assertEqual(p.durationState,'feasible');self.assertIsNone(p.elapsedUpperSeconds)
        self.assertEqual([v.occurrence for v in p.stops],[0,1]);self.assertFalse(any(q['field']=='dwell' for q in r.questions))
        self.assertTrue(r.preferences['scopeOverride']);self.assertEqual(self.counts(),before)
    def test_recalculation_filters_old_cards_then_recovers_without_io(self):
        s=self.session();self.h.run_session(s,startingLocation=start());before=self.counts()
        self.assertEqual(self.run_edit(s,dwell=[dict(occurrence=0,minutes=80,relation='exact')]).status,'no_results')
        r=self.run_edit(s,dwell=[dict(occurrence=0,minutes=10,relation='exact')]);self.assertTrue(r.options)
        self.assertEqual(r.options[0].elapsedUpperSeconds,1260);self.assertEqual(self.counts(),before)
    def test_all_duration_relations_and_inclusive_exclusive_boundary(self):
        for relation,expected in [('exact','feasible'),('maximum','feasible'),('under','feasible'),('minimum','unverified'),('approximate','unverified')]:
            with self.subTest(relation=relation):
                s=self.session();self.h.run_session(s,startingLocation=start())
                r=self.run_edit(s,dwell=[dict(occurrence=0,minutes=34,relation=relation)])
                self.assertEqual(r.options[0].durationState,expected)
        s=self.session();s.journey.total_duration=Duration.model_validate(duration(45,'under'));self.h.run_session(s,startingLocation=start())
        self.assertEqual(self.run_edit(s,dwell=[dict(occurrence=0,minutes=34,relation='exact')]).status,'no_results')
        self.assertTrue(self.run_edit(s,dwell=[dict(occurrence=0,minutes=34,relation='under')]).options)
    def test_travel_budget_all_legs_and_exact_boundary(self):
        for relation,seconds,status in [('maximum',900,'results'),('under',900,'no_results'),('under',899.999,'results')]:
            with self.subTest(relation=relation,seconds=seconds):
                s=self.session();s.journey.total_duration=Duration.model_validate(duration(45,relation))
                self.h.values.update({('DRIVE','origin','Synthetic_grocery'):seconds,('DRIVE','Synthetic_grocery','Synthetic_bank'):seconds,('DRIVE','Synthetic_bank','origin'):seconds})
                self.h.run_session(s,startingLocation=start());r=self.run_edit(s,budgetScope='travel')
                self.assertEqual(r.status,status)
    def test_zero_requires_explicit_travel_scope_ack_and_never_drops_stop(self):
        s=self.session();self.h.run_session(s,startingLocation=start())
        for edit in [dict(dwell=[dict(occurrence=0,minutes=0,relation='exact')]),dict(budgetScope='travel',dwell=[dict(occurrence=0,minutes=0,relation='exact')])]:
            with self.assertRaises(ValueError):self.run_edit(s,**edit)
        r=self.run_edit(s,budgetScope='travel',dwell=[dict(occurrence=0,minutes=0,relation='exact',zeroCountedTime=True)])
        self.assertEqual(len(r.options[0].stops),2);self.assertEqual(r.options[0].stops[1].duration.minutes,5)
        with self.assertRaises(ValueError):self.run_edit(s,budgetScope='outing')
        self.assertEqual(s.budget_scope,'travel')
        self.assertTrue(self.run_edit(s,budgetScope='outing',dwell=[dict(occurrence=0,minutes=10,relation='exact')]).options)
        with self.assertRaises(ValueError):AdvancedInput(token=s.token,edits={'dwell':[dict(occurrence=0,minutes=0,relation='under',zeroCountedTime=True)]})
    def test_independent_deadline_still_needs_visits_and_departure(self):
        s=self.session(deadline={'source':'by 6 PM','minute':1080});self.h.run_session(s,startingLocation=start())
        r=self.run_edit(s,budgetScope='travel');self.assertEqual({q['field'] for q in r.questions},{'dwell','departure'})
        with self.assertRaises(ValueError):self.run_edit(s,dwell=[dict(occurrence=0,minutes=0,zeroCountedTime=True)])
        r=self.run_edit(s,dwell=[dict(occurrence=0,minutes=40,relation='exact')],departure='17:00')
        self.assertEqual(r.options[0].durationState,'feasible');self.assertEqual(r.options[0].deadlineState,'feasible')
    def test_original_atm_and_departure_are_explicitly_editable_and_resettable(self):
        s=self.session();s.context.departureMinute=600;s.context.departureSource='depart at 10 AM'
        self.h.run_session(s,startingLocation=start())
        r=self.run_edit(s,dwell=[dict(occurrence=1,minutes=8,relation='maximum')],departure='11:00')
        self.assertEqual(r.preferences['stops'][1]['originalDuration']['minutes'],5);self.assertTrue(r.preferences['stops'][1]['override'])
        self.assertEqual(r.preferences['departure'],'11:00');self.assertTrue(r.preferences['departureOverride'])
        r=self.run_edit(s,resetDwell=[1],resetDeparture=True)
        self.assertEqual(r.preferences['stops'][1]['duration']['minutes'],5);self.assertEqual(r.preferences['departure'],'10:00')
    def test_configuration_change_rejected_before_edit_mutates_state(self):
        s=self.session();self.h.run_session(s,startingLocation=start());before=self.counts()
        with self.assertRaises(ValueError):self.h.run_session(s,edits={'budgetScope':'travel'})
        self.assertEqual(s.budget_scope,'outing');self.assertEqual(self.counts(),before)
        for invalid in [True,'0',-1,4]:
            with self.assertRaises(ValueError):AdvancedInput(token=s.token,edits={'resetDwell':[invalid]})
    def test_receipt_scope_original_provenance_and_legacy_v2_compatibility(self):
        s=self.session();self.h.run_session(s,startingLocation=start())
        r=self.run_edit(s,budgetScope='travel',dwell=[dict(occurrence=0,minutes=10,relation='exact')])
        d=receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[r.options[0].id],selectedId=r.options[0].id))
        a=d.itineraries[0].advanced;self.assertEqual(a.budgetScope,'travel');self.assertEqual(a.durationOverrides,[0])
        self.assertIsNone(a.originalJourney.stops[0].duration);self.assertEqual(a.journey.stops[0].duration.minutes,10)
        payload=d.model_dump();saved=payload['itineraries'][0]['advanced']
        self.assertNotIn('latitude',d.model_dump_json());self.assertNotIn('Synthetic grocery supermarket',d.model_dump_json())
        for key in ['originalJourney','budgetScope','durationOverrides','departureOverride']:saved.pop(key)
        self.assertEqual(SavedDocument.model_validate(payload).itineraries[0].advanced.budgetScope,'outing')
    def test_verified_named_choice_edit_preserves_identity_and_reroutes_only_new_pairs(self):
        from backend.test_stop_resolution import place
        self.h.records.append(place('Synthetic_other','Penn Station','2 Fixture Road, New York',['train_station']))
        s=self.h.session([{'source':'Penn Station','kind':'named_place'},{'source':'coffee'}])
        first=self.h.run_session(s);self.assertEqual(first.status,'clarification')
        r=self.h.run_session(s,edits={'choices':[dict(occurrence=0,placeId='Synthetic_station')]})
        self.assertEqual(r.options[0].stops[0].placeId,'Synthetic_station')
        searches=len(self.h.searches);calls=len(self.h.calls)
        r=self.h.run_session(s,edits={'choices':[dict(occurrence=0,placeId='Synthetic_other')]})
        self.assertEqual(r.options[0].stops[0].placeId,'Synthetic_other');self.assertEqual(len(self.h.searches),searches)
        self.assertEqual(len(self.h.calls),calls+1)
        calls=len(self.h.calls)
        r=self.h.run_session(s,edits={'choices':[dict(occurrence=0,placeId='Synthetic_station')]})
        self.assertEqual(len(self.h.calls),calls);self.assertEqual(r.options[0].stops[0].placeId,'Synthetic_station')
        with self.assertRaises(ValueError):self.h.run_session(s,edits={'choices':[dict(occurrence=0,placeId='unverified')]})
    def test_source_zero_cannot_claim_an_entire_outing_fit(self):
        s=self.session();s.journey.stops[0].duration=Duration.model_validate(duration(0,'exact'))
        r=self.h.run_session(s,startingLocation=start());self.assertEqual(r.status,'clarification');self.assertEqual(r.options,[])
        r=self.run_edit(s,budgetScope='travel');self.assertEqual(r.status,'clarification')
        r=self.run_edit(s,dwell=[dict(occurrence=0,minutes=0,relation='exact',zeroCountedTime=True)])
        self.assertEqual(len(r.options[0].stops),2)
    def test_one_policy_no_departure_time_sent_and_missing_evidence_not_passed(self):
        s=self.session();self.h.run_session(s,startingLocation=start());self.run_edit(s,budgetScope='travel')
        self.assertTrue(self.h.calls)
        self.assertTrue(all(c['travelMode']=='DRIVE' and c['routingPreference']=='TRAFFIC_UNAWARE' and 'departureTime' not in c for c in self.h.calls))
        self.h.values['DRIVE','Synthetic_bank','origin']=None;s=self.session();r=self.h.run_session(s,startingLocation=start(),edits={'budgetScope':'travel'})
        self.assertTrue(all(p.durationState=='unverified' for p in r.options))

if __name__=='__main__':unittest.main()

import os
@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS')=='1','Opt-in committed editable preference PostgreSQL check')
class HostedEditablePreferencesTests(unittest.TestCase):
    def test_committed_overrides_original_provenance_restart_read_and_exact_cleanup(self):
        import json,subprocess,secrets
        import psycopg
        from backend.database_check import connection_settings
        from backend.saved_plans import save,reopen,OpenRequest,digest
        h=fixtures.IntegrationTests('test_named_roundtrip_dto_and_receipt');h.setUp()
        try:
            s=h.session([{'source':'groceries'},{'source':'ATM','duration':duration(5,'exact')}],endpoint={'kind':'origin','source':'return to start'},total_duration=duration(45,'maximum'))
            r=h.run_session(s,startingLocation=start(),edits={'dwell':[dict(occurrence=0,minutes=10,relation='exact')],'budgetScope':'travel'})
            req=SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[p.id for p in r.options],selectedId=r.options[0].id)
            key=digest(req.accessToken)
            with psycopg.connect(**connection_settings(os.environ),autocommit=True) as admin:
                try:
                    self.assertEqual(save(req),{'saved':True})
                    script='import json,sys;from backend.saved_plans import reopen,OpenRequest;print(json.dumps(reopen(OpenRequest(accessToken=sys.stdin.read()))))'
                    process=subprocess.run(['backend/.venv/bin/python','-c',script],input=req.accessToken,text=True,capture_output=True,check=True)
                    value=json.loads(process.stdout);self.assertEqual(value,reopen(OpenRequest(accessToken=req.accessToken)))
                    self.assertEqual(len(value['itineraries']),1);self.assertEqual(value['selectedId'],r.options[0].id)
                    a=value['itineraries'][0]['advanced'];self.assertEqual(a['budgetScope'],'travel');self.assertEqual(a['durationOverrides'],[0])
                    self.assertIsNone(a['originalJourney']['stops'][0]['duration']);self.assertEqual(a['journey']['stops'][0]['duration']['minutes'],10)
                    self.assertEqual(a['journey']['stops'][1]['duration']['minutes'],5);self.assertEqual(a['journey']['total_duration']['minutes'],45)
                    self.assertEqual(a['ending'],'origin');self.assertNotIn('latitude',json.dumps(value))
                finally:
                    admin.execute('DELETE FROM whereto.plans WHERE access_hash=%s',(key,))
            with psycopg.connect(**connection_settings(os.environ),autocommit=True) as verify:
                self.assertEqual(verify.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(key,)).fetchone()[0],0)
        finally:h.doCleanups()
