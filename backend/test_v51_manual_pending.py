"""Local source ownership through the existing API, no external providers."""
from copy import deepcopy
import json
from unittest import TestCase

from backend.interpretation import InterpretationInput
from backend.test_v51_application_fixture import post
from scripts.task52_v51_application_fixture import application_fixture, CASES, REFERENCE
from scripts.task52_v51_local_continuation import LocalContinuation

SOURCE='Buy groceries and maybe stop for coffee.'


class ManualPendingTests(TestCase):
    def test_manual_context_and_walking_routes_leave_extraction_untouched(self):
        with application_fixture() as (_app,fixture,counts,_store):
            r=post('/api/interpret',{'text':SOURCE,'preferences':{
                'date':'2026-11-20','location':'New York','transport':'walking'}})
            self.assertEqual(r['context']['date'],'2026-11-20')
            self.assertEqual(r['context']['transport'],'walking')
            self.assertIsNone(r['interpretation']['location'])
            self.assertEqual(r['interpretation']['date_expressions'],[])
            out=post('/api/plans/advanced',{'token':r['advancedToken']})
            self.assertTrue(out['options'])
            self.assertTrue(all(l['mode']=='walk' for o in out['options'] for l in o['legs']))
            self.assertEqual(counts['extractions'],1)
            self.assertTrue(all(b['travelMode']=='WALK' for b in fixture.calls))

    def test_issued_pending_date_area_answers_preserve_graph_without_extraction(self):
        with application_fixture() as (_app,_fixture,counts,_store):
            r=post('/api/interpret',{'text':SOURCE})
            unlocated=post('/api/interpret',{'text':SOURCE,'pending':r['pending'],'answers':{'date':'tomorrow'}})
            self.assertIsNone(unlocated['advancedToken'])
            answered=post('/api/interpret',{'text':SOURCE,'pending':r['pending'],
                'answers':{'date':'tomorrow','location':'New York'}})
            self.assertIsNotNone(answered['advancedToken'])
            self.assertEqual(answered['context']['date'],'2026-11-06')
            self.assertEqual(answered['interpretation'],r['interpretation'])
            manual_area=post('/api/interpret',{'text':SOURCE,'pending':r['pending'],
                'preferences':{'location':'New York'},'answers':{'date':'tomorrow'}})
            exact=post('/api/interpret',{'text':SOURCE,'pending':manual_area['pending'],
                'preferences':{'date':'2026-11-20'}})
            self.assertIsNotNone(exact['advancedToken'])
            self.assertEqual(exact['context']['date'],'2026-11-20')
            self.assertIsNone(exact['context']['destination'])
            self.assertEqual(counts['extractions'],1)
            self.assertTrue(post('/api/plans/advanced',{'token':answered['advancedToken']})['options'])

    def test_tampered_pending_and_semantic_answers_never_reach_providers(self):
        with application_fixture() as (_app,fixture,_counts,_store):
            r=post('/api/interpret',{'text':SOURCE})
            for field in ('reference','graph','optionality','answers','source'):
                p=deepcopy(r['pending'])
                if field=='reference':p['referenceTime']='2026-11-04T15:00:00Z'
                if field=='graph':p['interpretation']['journey']['order']=[]
                if field=='optionality':p['interpretation']['journey']['stops'][1]['requirement']='required'
                if field=='answers':p['answers']['date']='2026-11-20'
                if field=='source':p['text']='Coffee, then groceries.'
                out=post('/api/interpret',{'text':SOURCE,'pending':p})
                self.assertIsNone(out['advancedToken'],field)
            for answer in ({'activities':'coffee, groceries'},{'endpoint':'return to my starting point'}):
                out=post('/api/interpret',{'text':SOURCE,'pending':r['pending'],'answers':answer})
                self.assertIsNone(out['advancedToken'])
            self.assertFalse(fixture.searches);self.assertFalse(fixture.calls)

    def test_changed_text_gets_new_occurrences_and_optionality(self):
        with application_fixture() as (_app,_fixture,counts,_store):
            old=post('/api/interpret',{'text':SOURCE})
            changed='Coffee, then groceries.'
            self.assertIsNone(post('/api/interpret',{'text':changed,'pending':old['pending']})['advancedToken'])
            fresh=post('/api/interpret',{'text':changed,'preferences':{'location':'New York','date':'2026-11-20'}})
            self.assertEqual(fresh['interpretation']['activities'],['Coffee','groceries'])
            self.assertNotEqual(fresh['advancedToken'],old['advancedToken'])
            required=post('/api/interpret',{'text':'Buy groceries and coffee.'})
            self.assertEqual([s['requirement'] for s in required['interpretation']['journey']['stops']],['required','required'])
            self.assertEqual(counts['externalSends'],0)

    def test_contradiction_only_resolves_by_new_source(self):
        with application_fixture() as (_app,fixture,_counts,_store):
            old=post('/api/interpret',{'text':'Visit the pharmacy before the bank, but the bank before the pharmacy.'})
            self.assertIsNone(old['pending']);self.assertIsNone(old['advancedToken'])
            self.assertFalse(fixture.searches);self.assertFalse(fixture.calls)
            fixed=post('/api/interpret',{'text':'Visit the pharmacy before the bank.'})
            self.assertIsNotNone(fixed['advancedToken'])

    def test_pending_expiration_restarts_and_raw_identity_fail_closed(self):
        raw=next(c['extraction'] for c in json.loads(CASES.read_text())['cases'] if c['text']==SOURCE)
        clock=[100.0];bridge=LocalContinuation(clock=lambda:clock[0])
        first=bridge.interpret(InterpretationInput(text=SOURCE),raw,REFERENCE)
        value=InterpretationInput(text=SOURCE,pending=first.pending,answers={'location':'New York'})
        clock[0]=699
        followup=bridge.interpret(value,raw,REFERENCE)
        self.assertIsNotNone(followup.pending)
        clock[0]=700
        self.assertIsNone(bridge.interpret(value,raw,REFERENCE).pending)
        self.assertIsNone(LocalContinuation().interpret(value,raw,REFERENCE).pending)
        clock[0]=101
        altered=deepcopy(raw);altered['journey']['order'][0]['source']='groceries and maybe stop for coffee'
        self.assertIsNone(bridge.interpret(value,altered,REFERENCE).pending)
        from unittest.mock import patch
        from scripts.task52_ordering_preservation_dev import interpret_for_development
        def finish_after_expiry(*args,**kwargs):
            result=interpret_for_development(*args,**kwargs)
            clock[0]=701
            return result
        clock[0]=699
        with patch('scripts.task52_v51_local_continuation.interpret_for_development',side_effect=finish_after_expiry):
            self.assertIsNone(bridge.interpret(value,raw,REFERENCE).pending)

    def test_unsupported_manual_fields_do_not_disappear(self):
        with application_fixture() as (_app,fixture,_counts,_store):
            for prefs in ({'budget':'20'},{'people':'2'},{'travel':'invalid'},{'date':'yesterday'},{'costExplicit':True}):
                self.assertIsNone(post('/api/interpret',{'text':SOURCE,'preferences':prefs})['advancedToken'])
            self.assertFalse(fixture.searches);self.assertFalse(fixture.calls)

    def test_expired_session_and_receipt_refuse_before_new_work(self):
        from backend.advanced_planning import sessions
        from backend.saved_plans import receipts
        with application_fixture() as (_app,fixture,_counts,store):
            r=post('/api/interpret',{'text':SOURCE,'preferences':{'date':'2026-11-20','location':'New York'}})
            out=post('/api/plans/advanced',{'token':r['advancedToken']})
            self.assertTrue(out['options'])
            calls=(len(fixture.searches),len(fixture.calls))
            sessions.items[r['advancedToken']].expires=0
            expired=post('/api/plans/advanced',{'token':r['advancedToken']},status=422)
            self.assertEqual(expired['code'],'advanced_session_expired')
            receipt=out['saveReceipt'];_,document=receipts.items[receipt]
            receipts.items[receipt]=(0,document)
            post('/api/plans/save',{'receipt':receipt,'accessToken':out['saveAccessToken'],
                'candidateIds':[o['id'] for o in out['options']],'selectedId':out['options'][0]['id']},status=409)
            self.assertFalse(store.documents)
            self.assertEqual(calls,(len(fixture.searches),len(fixture.calls)))


    def test_relative_advanced_date_without_calendar_refuses_before_work(self):
        with application_fixture() as (_app,fixture,_counts,_store):
            r=post('/api/interpret',{'text':SOURCE})
            refused=post('/api/plans/advanced',{'token':r['advancedToken'],'date':'tomorrow'},status=422)
            self.assertEqual(refused['code'],'advanced_answer_invalid')
            self.assertFalse(fixture.searches);self.assertFalse(fixture.calls)
            accepted=post('/api/plans/advanced',{'token':r['advancedToken'],
                'date':'2026-11-20','destination':'New York'})
            self.assertTrue(accepted['options'])
