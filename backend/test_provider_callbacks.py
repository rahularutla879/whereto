"""Real callback/HTTPS fixture tests. No SQL authority or live provider acceptance.

All policy/count/grant-port values here are fictional. The original protected SQL
profile is unchanged and intentionally still cannot enroll this real callback.
"""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json, multiprocessing, os, ssl, subprocess, unittest

from backend import action_dispatch as io
from backend.ai import AIError
from backend.ai.openai_candidate import OpenAICandidateProvider, request_bytes
from backend.provider_enrollment_review import review_bound, template_digest
from backend.provider_responses import GoogleHTTPExchange, HTTPResult, ProviderResponseError
from backend.test_provider_responses import response, extraction, TEXT, NOW
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.testing_clock import calendar_clock
from backend.test_real_planning import ENV, outing
from private_runtime.provider_callbacks import (
    CounterCallback, DispatcherCallback, OpenAIHTTP, inference_response,
    count_payload, generation_source, digest, EVALUATION_PROJECT)
from private_runtime.https import HTTPS, Endpoint, Refused

PROJECT = 'proj_FICTIONALAPPLICATION'


def policy(wire, provider='openai'):
    p = dict(provider=provider, account=PROJECT, version='fictional-reviewed-v1',
             checkedAt=100, expiresAt=200, priceEvidenceSHA256='a'*64)
    if provider == 'google':
        p['rates'] = dict(search_pro=32000, matrix_element=5000, matrix_pro_element=10000)
    else:
        p.update(rates=dict(inputMicroUsdPerMillion=1000000, outputMicroUsdPerMillion=2000000),
            model='gpt-6-luna', modelRevision='fictional-revision',
            endpoint='https://api.openai.com/v1/responses', templateSHA256=template_digest(json.loads(wire)),
            counterVersion='fictional-provider-count-v1', maxInput=12000, maxOutput=2000,
            inputMargin=2048, costProfile='input-output-only-reviewed-no-extras-v1')
    return p


def count(wire):
    return dict(payloadSHA256=digest(wire), provider='openai', account=PROJECT,
        model='gpt-6-luna', modelRevision='fictional-revision',
        counterVersion='fictional-provider-count-v1', inputTokens=100, checkedAt=100, expiresAt=200)


class Accounting:
    """Authority STAND-IN, not proof of restricted SQL grants or durability."""
    def __init__(self): self.receipts={}; self.used=set()
    def approve(self, wire, provider='openai', **changes):
        p=policy(wire,provider);c=count(wire) if provider=='openai' else None
        self.receipts[digest(wire)] = dict(policy=p,count=c,
            reservedMicroUSD=review_bound(p,wire,now=150,count=c).maximum_micro_usd,**changes)
    def require(self, wire):
        h=digest(wire)
        if h in self.used or h not in self.receipts:raise RuntimeError('Unenrolled or consumed')
        self.used.add(h);return deepcopy(self.receipts[h])


class CountAuthority:
    def __init__(self, events):self.events=events;self.used=False;self.record=None
    def begin(self,cap,wire,projection,project):
        self.events.append('intent')
        if self.used:raise RuntimeError('Consumed')
        self.used=True;return 'fictional-count-operation'
    def commit(self,op,record,raw):self.events.append('attest');self.record=record;self.raw=raw
    def uncertain(self,op):self.events.append('uncertain')


class RecordedHTTP:
    def __init__(self, raw):self.raw=raw;self.calls=[]
    def request(self,*args):
        self.calls.append(args)
        if isinstance(self.raw,BaseException):raise self.raw
        return self.raw


def serve(pipe,cert,key,status=200):
    """Independent TLS process serves authored provider-shaped HTTP only."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            wire=self.rfile.read(int(self.headers['Content-Length']));body=json.loads(wire)
            if status != 200:
                raw=b'{"error":{"code":"fictional_terminal_denial"}}'
                pipe.send((self.path,digest(wire)))
                self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            if self.path=='/v1/responses/input_tokens':data={'object':'response.input_tokens','input_tokens':100}
            elif self.path=='/v1/responses':data=json.loads(response(extraction(),usage=dict(input_tokens=100,output_tokens=10,total_tokens=110)).body)
            elif self.path=='/v1/places:searchText':data=search_fixture(body)
            elif self.path=='/distanceMatrix/v2:computeRouteMatrix':data=matrix_fixture(body)
            else:self.send_error(405);return
            pipe.send((self.path,digest(wire)))
            raw=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=HTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(cert,key)
    server.socket=context.wrap_socket(server.socket,server_side=True);pipe.send(server.server_port)
    server.serve_forever()


class CallbackTests(unittest.TestCase):
    def setUp(self):self.wire=request_bytes(TEXT)
    def test_exact_count_projection_and_no_diagnostic_count_reuse(self):
        self.assertEqual(generation_source(self.wire),TEXT)
        self.assertEqual(set(json.loads(count_payload(self.wire))),{'model','input','text','reasoning'})
        self.assertNotEqual(count_payload(self.wire),count_payload(request_bytes('museum then coffee in Baltimore')))
        for body in [{**json.loads(self.wire),'model':'other'}, {**json.loads(self.wire),'max_output_tokens':2001}]:
            with self.assertRaises(Exception):count_payload(json.dumps(body,sort_keys=True,separators=(',',':')).encode())
        with self.assertRaises(Exception):count_payload(self.wire+b' ')
    def test_default_credential_missing_and_evaluation_project_refuse(self):
        for project,loader in [(EVALUATION_PROJECT,lambda:'fictional'),(PROJECT,None),('wrong',lambda:'fictional')]:
            with self.assertRaises(ProviderResponseError):OpenAIHTTP(project,loader,purpose='count')
        with self.assertRaises(ProviderResponseError):CounterCallback(None,None)
        port=OpenAIHTTP(PROJECT,lambda:'not-a-key',RecordedHTTP(b'{}'),purpose='count')
        with self.assertRaises(ProviderResponseError):port.count(self.wire)
    def test_counter_intent_before_credentials_and_attestation_after_response(self):
        events=[];authority=CountAuthority(events);http=RecordedHTTP(b'{"object":"response.input_tokens","input_tokens":100}')
        def credential():events.append('credential');return 'sk-FICTIONAL'
        counter=CounterCallback(OpenAIHTTP(PROJECT,credential,http,purpose='count'),authority)
        record=counter.count('fictional-cap',self.wire)
        self.assertEqual(events,['intent','credential','attest']);self.assertEqual(record.tokens,100)
        self.assertEqual((record.generation_sha256,record.count_sha256),(digest(self.wire),digest(count_payload(self.wire))))
        self.assertEqual(http.calls[0][1:4],('POST','/v1/responses/input_tokens',count_payload(self.wire)))
        with self.assertRaises(RuntimeError):counter.count('fictional-cap',self.wire)
        self.assertEqual(len(http.calls),1)
    def test_count_malformed_denial_and_uncertain_no_retry(self):
        for raw in [b'{}',b'{"object":"response.input_tokens","input_tokens":true}',b'{"object":"response.input_tokens","input_tokens":0}',b'{"object":"response.input_tokens","input_tokens":100001}',b'{"object":"response.input_tokens","input_tokens":3,"model":"other"}',b'{"input_tokens":1,"input_tokens":2}',Refused('response')]:
            events=[];http=RecordedHTTP(raw);counter=CounterCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',http,purpose='count'),CountAuthority(events))
            with self.assertRaises(Exception):counter.count('cap',self.wire)
            self.assertEqual(events,['intent','uncertain']);self.assertEqual(len(http.calls),1)
            with self.assertRaises(RuntimeError):counter.count('cap',self.wire)
            self.assertEqual(len(http.calls),1)
    def test_missing_authority_blocks_before_credential_or_http(self):
        class Refuse(CountAuthority):
            def begin(self,*args):raise RuntimeError('No protected count authority')
        http=RecordedHTTP(b'{}');counter=CounterCallback(OpenAIHTTP(PROJECT,lambda:(_ for _ in ()).throw(AssertionError('Key touched')),http,purpose='count'),Refuse([]))
        with self.assertRaises(RuntimeError):counter.count('cap',self.wire)
        self.assertFalse(http.calls)
    def test_dispatch_exact_quote_model_project_expiry_and_payload(self):
        for alteration in ('price','project','stale','model','count'):
            a=Accounting();a.approve(self.wire);q=a.receipts[digest(self.wire)]
            if alteration=='price':q['reservedMicroUSD']+=1
            elif alteration=='project':q['policy']['account']='other'
            elif alteration=='stale':q['policy']['expiresAt']=150
            elif alteration=='model':q['policy']['model']='other'
            else:q['count']['payloadSHA256']='f'*64
            http=RecordedHTTP(response(extraction()).body);callback=DispatcherCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',http,purpose='generation'),None,a,lambda:150)
            with self.assertRaises(Exception):callback(self.wire)
            self.assertFalse(http.calls)
    def test_dispatch_raw_rpc_decoder_and_consumed_operation(self):
        a=Accounting();a.approve(self.wire);raw=response(extraction()).body;http=RecordedHTTP(raw)
        callback=DispatcherCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',http,purpose='generation'),None,a,lambda:150)
        envelope=callback(self.wire);self.assertEqual(inference_response(envelope).body,raw)
        with self.assertRaises(RuntimeError):callback(self.wire)
        self.assertEqual(len(http.calls),1)
        for value in [{**envelope,'bodySHA256':'a'*64},{**envelope,'bodyBase64':'@@'},{**envelope,'provider':'other'}]:
            with self.assertRaises(ProviderResponseError):inference_response(value)
    def test_existing_owned_dispatch_is_the_only_network_rpc_entry(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        dispatch=Mock(return_value={'delivered':True});callback=DispatcherCallback(None,None,None,None)
        with patch.dict(sys.modules,{'private_runtime.owned_dispatch':SimpleNamespace(dispatch=dispatch)}):
            self.assertEqual(callback.dispatch({'service':'dispatcher'},{'operation':'unchanged'}),{'delivered':True})
            dispatch.assert_called_once_with({'service':'dispatcher'},{'operation':'unchanged'},callback)
    def test_provider_error_has_no_synthetic_fallback(self):
        a=Accounting();a.approve(self.wire);http=RecordedHTTP(Refused('terminal_403'))
        callback=DispatcherCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',http,purpose='generation'),None,a,lambda:150)
        with self.assertRaises(Refused):callback(self.wire)
        with self.assertRaises(RuntimeError):callback(self.wire)
        self.assertEqual(len(http.calls),1)
    def test_counter_and_dispatcher_http_purposes_are_separate(self):
        transport=RecordedHTTP(b'{}')
        counter=OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',transport,purpose='count')
        dispatcher=OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',transport,purpose='generation')
        with self.assertRaises(ProviderResponseError):counter.generate(self.wire)
        with self.assertRaises(ProviderResponseError):dispatcher.count(self.wire)
        self.assertFalse(transport.calls)

    def test_credential_echo_not_forwarded(self):
        http=RecordedHTTP(b'{"echo":"sk-FICTIONAL"}')
        with self.assertRaises(ProviderResponseError):OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',http,purpose='generation').generate(self.wire)

    def test_actual_tls_400_401_403_are_terminal_without_retry(self):
        with TemporaryDirectory(prefix='whereto-real-terminal-tls-') as directory:
            cert=Path(directory)/'cert.pem';key=Path(directory)/'key.pem'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            for status in (400,401,403):
                parent,child=multiprocessing.get_context('spawn').Pipe();process=multiprocessing.get_context('spawn').Process(target=serve,args=(child,str(cert),str(key),status));process.start()
                try:
                    self.assertTrue(parent.poll(15));port=parent.recv();local=Endpoint(f'https://localhost:{port}',f'https://localhost:{port}');tls=HTTPS(ca_file=str(cert),deadline=5)
                    class Route:
                        def request(self,endpoint,method,path,body,headers):return tls.request(local,method,path,body,headers)
                    events=[];counter=CounterCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',Route(),purpose='count'),CountAuthority(events))
                    with self.assertRaises(Refused):counter.count('cap',self.wire)
                    self.assertEqual(events,['intent','uncertain']);self.assertTrue(parent.poll(2));self.assertEqual(parent.recv()[0],'/v1/responses/input_tokens')
                    with self.assertRaises(RuntimeError):counter.count('cap',self.wire)
                    self.assertFalse(parent.poll(.1))
                finally:process.terminate();process.join(5);parent.close();child.close()

    def test_actual_planner_with_independent_local_tls_provider_process(self):
        import requests
        from backend.interpretation import InterpretationInput,ClarificationAnswers,interpret_request
        from backend.real_planning import PlannerInput,real_plans
        from backend.provider_budget import ProviderBudget,ProviderSettings
        with TemporaryDirectory(prefix='whereto-real-callback-tls-') as directory:
            cert=Path(directory)/'cert.pem';key=Path(directory)/'key.pem'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            parent,child=multiprocessing.get_context('spawn').Pipe();process=multiprocessing.get_context('spawn').Process(target=serve,args=(child,str(cert),str(key)))
            process.start()
            try:
                self.assertTrue(parent.poll(15));port=parent.recv();local=Endpoint(f'https://localhost:{port}',f'https://localhost:{port}');tls=HTTPS(ca_file=str(cert),deadline=20)
                invalid_tls_cases=((HTTPS(deadline=5),local),(HTTPS(ca_file=str(cert),deadline=5),Endpoint(f'https://127.0.0.1:{port}',f'https://127.0.0.1:{port}')))
                for bad,target in invalid_tls_cases:
                    with self.assertRaises(Refused):bad.request(target,'POST','/v1/responses/input_tokens',count_payload(self.wire),{'Content-Type':'application/json'})
                class Route:
                    def request(self,endpoint,method,path,body,headers):
                        assert endpoint.url=='https://api.openai.com'
                        return tls.request(local,method,path,body,headers)
                class Session(requests.Session):
                    def request(self,method,url,**kwargs):
                        from urllib.parse import urlsplit
                        assert urlsplit(url).hostname in ('places.googleapis.com','routes.googleapis.com')
                        kwargs['verify']=str(cert)
                        return super().request(method,local.url+urlsplit(url).path,**kwargs)
                http=OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',Route(),purpose='generation');events=[]
                counter_http=OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',Route(),purpose='count')
                record=CounterCallback(counter_http,CountAuthority(events)).count('cap',self.wire);self.assertEqual(record.tokens,100)
                authority=Accounting();authority.approve(self.wire)
                callback=DispatcherCallback(http,GoogleHTTPExchange(lambda _:'fictional-oauth',session_factory=Session),authority,lambda:150)
                ai=OpenAICandidateProvider(lambda wire:inference_response(callback(wire)))
                with calendar_clock(NOW),patch.dict(os.environ,ENV,clear=True):
                    initial=interpret_request(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'),ai,now=NOW)
                    ready=interpret_request(InterpretationInput(text=TEXT,pending=initial.pending,answers=ClarificationAnswers(date='2026-11-07'),calendarTimezone='America/New_York'),ai,now=NOW)
                    self.assertIsNotNone(initial.pending);self.assertIsNotNone(ready.request);self.assertEqual(ai.usage['input_tokens'],record.tokens)
                    class Owner:
                        def dispatch(self,request):
                            authority.approve(request.canonical,'google');return callback(request.canonical)
                        def reserve(self,*args):return nullcontext()
                    token=io._active.set(Owner())
                    try:result=real_plans(PlannerInput(**ready.request.model_dump(),startingLocation=outing().startingLocation),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
                    finally:io._active.reset(token)
                self.assertEqual(len(result.provisionalPlans),3)
                for card in result.provisionalPlans:
                    self.assertEqual([v.activity for v in card.candidate.venues],['coffee','museum']);self.assertGreater(card.totalTravel,0)
                    self.assertTrue(all(s.venue.evidenceLabels['attribution']['brand']=='Google Maps' for s in card.stops))
                calls=[]
                while parent.poll(.2):calls.append(parent.recv())
                paths=[x[0] for x in calls]
                self.assertEqual(paths.count('/v1/responses'),1);self.assertEqual(paths.count('/v1/responses/input_tokens'),1)
                self.assertIn('/v1/places:searchText',paths);self.assertIn('/distanceMatrix/v2:computeRouteMatrix',paths)
                self.assertNotEqual(process.pid,os.getpid())
            finally:process.terminate();process.join(5);parent.close();child.close()

if __name__=='__main__':unittest.main()
