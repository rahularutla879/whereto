"""Real interpretation/ASGI boundary, fake model only, no external transport."""
import asyncio
from contextlib import nullcontext
from datetime import datetime,timezone
import json
import threading
import time
import unittest
from unittest.mock import Mock,patch

from backend import ordering_shadow as shadow
from backend.interpretation import InterpretationInput,interpret_request
from backend.main import app,interpret_outing
from scripts.cloud_model52_ordering_compatibility import fixture_reply

NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)
CASE={'text':'Dinner and bowling tomorrow in Jersey City.','stops':['Dinner','bowling'],
      'location':'Jersey City','expectedRelationships':[[0,1]]}


async def post_asgi(payload):
    body=json.dumps(payload).encode();sent=[];delivered=False
    async def receive():
        nonlocal delivered
        if not delivered:
            delivered=True;return {'type':'http.request','body':body,'more_body':False}
        await asyncio.Future()
    async def send(message):sent.append(message)
    scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
        'method':'POST','scheme':'http','path':'/api/interpret','raw_path':b'/api/interpret',
        'query_string':b'','root_path':'','server':('localhost',8000),'client':('127.0.0.1',1234),
        'headers':[(b'host',b'localhost:8000'),(b'content-type',b'application/json')]}
    await app(scope,receive,send)
    status=next(m['status'] for m in sent if m['type']=='http.response.start')
    return status,json.loads(b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body'))


class ShadowIsolationTests(unittest.TestCase):
    def run_interpretation(self,enabled,case=CASE):
        ai=fixture_reply(case);provider=Mock();provider.interpret.return_value=ai
        with patch('backend.interpretation.create_provider',return_value=provider):
            with shadow.capture_local_test() if enabled else nullcontext([]) as diagnostics:
                result=shadow.interpret_observed(InterpretationInput(text=case['text']),
                    lambda value,**kw:interpret_request(value,now=NOW,**kw))
        self.assertEqual(provider.interpret.call_count,1)
        return result.model_dump(mode='json'),diagnostics

    def test_default_off_never_computes_and_restores_after_scope(self):
        with patch.object(shadow,'_compute',side_effect=AssertionError('Must remain off')) as compute:
            self.run_interpretation(False);compute.assert_not_called()
        _,diag=self.run_interpretation(True)
        self.assertEqual(diag[0]['status'],'observed')
        self.assertEqual(diag[0]['rawEdges'],1);self.assertTrue(diag[0]['normalized'])
        with patch.object(shadow,'_compute') as compute:
            self.run_interpretation(False);compute.assert_not_called()

    def test_all_declared_cases_have_identical_interpretation_and_questions(self):
        from backend.test_cloud_model52_ordering_v4 import cases
        for c in cases():
            a,_=self.run_interpretation(False,c);b,d=self.run_interpretation(True,c)
            self.assertEqual(a,b,c['id']);self.assertLessEqual(len(d),1)
            if c['id']=='three-global':
                # Observer saw both raw global edges; legacy still removes
                # them from the active response. Shadow is NOT enforcement.
                self.assertEqual(d[0]['rawEdges'],2)
                self.assertEqual(b['interpretation']['journey']['order'],[])

    def test_observer_receives_raw_before_legacy_and_cannot_mutate_active_object(self):
        ai=fixture_reply(CASE);before=ai.model_dump(mode='json');seen=[]
        def destructive(source,snapshot):
            seen.append(len(snapshot.journey.order));snapshot.activities=['Invented']
            raise RuntimeError('PRIVATE SOURCE MUST NOT BE LOGGED')
        baseline,_=self.run_interpretation(False)
        with patch.object(shadow,'_compute',side_effect=destructive):
            actual,diag=self.run_interpretation(True)
        self.assertEqual(seen,[1]);self.assertEqual(actual,baseline)
        self.assertEqual(diag,[{'status':'error'}]);self.assertEqual(ai.model_dump(mode='json'),before)
        self.assertEqual(actual['interpretation']['journey']['order'],[])

    def test_exception_import_failure_and_timeout_do_not_change_response(self):
        baseline,_=self.run_interpretation(False)
        for error in (TimeoutError('private'),ImportError('private'),ValueError('private')):
            with patch.object(shadow,'_compute',side_effect=error):
                actual,diag=self.run_interpretation(True)
            self.assertEqual(actual,baseline);self.assertEqual(diag,[{'status':'error'}])
        with patch.object(shadow,'observe',side_effect=RuntimeError('private')):
            actual,_=self.run_interpretation(True)
        self.assertEqual(actual,baseline)

    def test_stuck_worker_times_out_no_queue_and_eventually_recovers(self):
        entered=threading.Event();release=threading.Event();finished=threading.Event()
        def blocked(*args):
            entered.set()
            try:release.wait(2);raise TimeoutError('not logged')
            finally:finished.set()
        try:
            with patch.object(shadow,'_compute',side_effect=blocked):
                baseline,_=self.run_interpretation(False)
                start=time.perf_counter();actual,diag=self.run_interpretation(True)
                self.assertTrue(entered.is_set());self.assertLess(time.perf_counter()-start,.5)
                self.assertEqual(actual,baseline);self.assertEqual(diag,[{'status':'timeout'}])
                actual,diag=self.run_interpretation(True)
                self.assertEqual(actual,baseline);self.assertEqual(diag,[{'status':'busy'}])
        finally:
            release.set();self.assertTrue(finished.wait(1))
        # Wait for the worker's finally block to release the one global slot.
        self.assertTrue(shadow._worker_slot.acquire(timeout=1));shadow._worker_slot.release()

    def test_input_diagnostic_and_concurrency_bounds(self):
        ai=fixture_reply(CASE)
        with shadow.capture_local_test() as diagnostics:
            for _ in range(40):shadow.observe('x'*8001,ai)
            self.assertEqual(len(diagnostics),16)
            self.assertTrue(all(d=={'status':'bounded_skip'} for d in diagnostics))
        with shadow.capture_local_test() as diagnostics:
            shadow.observe(CASE['text'],ai)
        self.assertLess(len(json.dumps(diagnostics)),512)
        self.assertNotIn(CASE['text'],json.dumps(diagnostics))
        self.assertFalse({'source','sourceHash','rawHash','span','quote','response'} & set(diagnostics[0]))

    def test_real_asgi_http_status_body_sessions_and_admission_are_identical(self):
        outputs=[]
        for enabled in (False,True):
            provider=Mock();provider.interpret.return_value=fixture_reply(CASE)
            with patch('backend.interpretation.create_provider',return_value=provider), \
                 patch('backend.interpretation.datetime',wraps=datetime) as clock, \
                 patch('backend.advanced_planning.sessions.create',return_value=None) as sessions, \
                 patch('backend.main.save') as save,patch('backend.main.recommend_plans') as routes, \
                 patch('requests.sessions.Session.send',side_effect=AssertionError('No external HTTP')):
                clock.now.return_value=NOW
                with shadow.capture_local_test() if enabled else nullcontext([]) as diagnostics:
                    result=asyncio.run(post_asgi({'text':CASE['text']}))
                outputs.append((result,sessions.call_args[0][1].model_dump(mode='json')))
                self.assertEqual(provider.interpret.call_count,1);self.assertEqual(sessions.call_count,1)
                save.assert_not_called();routes.assert_not_called()
                if enabled:self.assertEqual(diagnostics[0]['status'],'observed')
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[0][0][0],200)

    def test_strict_parser_still_rejects_bad_input_before_observer(self):
        with patch.object(shadow,'_compute') as compute:
            with shadow.capture_local_test():status,_=asyncio.run(post_asgi({'text':7}))
        self.assertEqual(status,422);compute.assert_not_called()

    def test_actual_advanced_session_state_and_ordinary_handoff_are_unchanged(self):
        from backend.advanced_planning import Sessions
        source={'text':'Go to SUNY College of Optometry, then get coffee in New York tomorrow.',
            'stops':['SUNY College of Optometry','coffee'],'kinds':['named_place','activity'],
            'location':'New York','expectedRelationships':[[0,1]]}
        outputs=[]
        for enabled in (False,True):
            sessions=Sessions();provider=Mock();provider.interpret.return_value=fixture_reply(source)
            with patch('backend.interpretation.create_provider',return_value=provider), \
                 patch('backend.interpretation.datetime',wraps=datetime) as clock, \
                 patch('backend.advanced_planning.sessions',sessions), \
                 patch('backend.advanced_planning.enabled',return_value=True), \
                 patch('backend.advanced_planning.secrets.token_urlsafe',return_value='s'*43), \
                 patch('requests.sessions.Session.send',side_effect=AssertionError('No external HTTP')):
                clock.now.return_value=NOW
                with shadow.capture_local_test() if enabled else nullcontext([]):
                    result=interpret_outing(InterpretationInput(text=source['text']))
                state=[(s.journey.model_dump(mode='json'),s.context.model_dump(mode='json')) for s in sessions.items.values()]
                outputs.append((result.model_dump(mode='json'),state))
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(len(outputs[0][1]),1)

    def test_saved_followup_skips_instead_of_claiming_raw_model_evidence(self):
        first,_=self.run_interpretation(False)
        self.assertIsNotNone(first['pending'])
        value=InterpretationInput(text=CASE['text'],pending=first['pending'])
        off=shadow.interpret_observed(value,lambda v:interpret_request(v,now=NOW))
        with patch('backend.interpretation.create_provider',side_effect=AssertionError('No second model')):
            with shadow.capture_local_test() as diagnostics:
                on=shadow.interpret_observed(value,lambda v:interpret_request(v,now=NOW))
        self.assertEqual(off,on);self.assertEqual(diagnostics,[{'status':'saved_snapshot_skip'}])

    def test_optional_module_import_failure_falls_back_before_any_model_dispatch(self):
        import builtins
        original_import=builtins.__import__
        def unavailable(name,*args,**kwargs):
            if name=='backend.ordering_shadow':raise ImportError('private detail')
            return original_import(name,*args,**kwargs)
        provider=Mock();provider.interpret.return_value=fixture_reply(CASE)
        with patch('backend.interpretation.create_provider',return_value=provider), \
             patch('backend.interpretation.datetime',wraps=datetime) as clock, \
             patch('backend.advanced_planning.sessions.create',return_value=None):
            clock.now.return_value=NOW
            baseline=interpret_outing(InterpretationInput(text=CASE['text']))
            provider.reset_mock()
            with patch('builtins.__import__',side_effect=unavailable):
                actual=interpret_outing(InterpretationInput(text=CASE['text']))
        self.assertEqual(actual,baseline);self.assertEqual(provider.interpret.call_count,1)
