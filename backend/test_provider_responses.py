"""Offline response-contract fixtures, not live provider acceptance or real venues."""
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch

from backend import action_dispatch as io
from backend.ai import AIError, Interpretation, create_provider
from backend.ai.openai_candidate import OpenAICandidateProvider, request_bytes
from backend.provider_responses import (GoogleResponseAdapter, HTTPResult,
    ProviderResponseError, GoogleHTTPExchange, google_request, real_inference_accounting)
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.provider_budget import ProviderBudget, ProviderSettings
from backend.real_planning import PlannerInput, real_plans
from backend.interpretation import InterpretationInput, ClarificationAnswers, interpret_request
from backend.test_real_planning import ENV, outing
from backend.testing_clock import calendar_clock

NOW = datetime(2026, 11, 2, 13, tzinfo=timezone.utc)
TEXT = 'coffee then museum in Baltimore'


def response(data, **changes):
    # Complete source-neutral wire fixture; these defaults are TEST data, never
    # repairs applied to a provider response. No private records or live counts.
    data = {**Interpretation(activities=[],date=None,location=None,budget_per_person=None,preferences=[]).model_dump(mode='json'), **data}
    data.pop('start_time',None);data.pop('end_time',None)
    journey = data.get('journey') or dict(stops=[dict(source=a) for a in data['activities']],order=[],ordering='unspecified')
    journey = {**dict(endpoint=None,total_duration=None,deadline=None,shared_place=None,clarification=''),**journey}
    journey.pop('order_conflict',None)
    journey['stops']=[{**dict(kind='activity',requirement='required',evidence='',duration=None),**v} for v in journey['stops']]
    data['journey']=journey
    value = dict(model='gpt-6-luna',status='completed',error=None,
        output=[dict(type='message',role='assistant',status='completed',
                     content=[dict(type='output_text',text=json.dumps(data))])],
        usage=dict(input_tokens=20,output_tokens=10,total_tokens=30))
    value.update(changes)
    return HTTPResult(200, json.dumps(value).encode())


def extraction():
    from backend.journey_fixtures import reply
    return reply(['coffee','museum'],location='Baltimore',order=[(0,1,TEXT)])


class RecordedSession:
    """Source-neutral recorded HTTP responder; never a requests socket."""
    def __init__(self, reply, calls):self.reply,self.calls=reply,calls
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def mount(self,*args):self.mounted=args
    def post(self,url,**kwargs):
        self.calls.append((url,kwargs))
        self.raw=self.reply;self.status_code=self.raw.status
        self.headers={'Content-Type':self.raw.content_type,'Content-Length':str(len(self.raw.body)+(0 if self.raw.complete else 1))}
        return self
    def iter_content(self,**_):yield self.raw.body


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.send',side_effect=AssertionError('Network forbidden')))
        self.enterContext(calendar_clock(NOW))
        self.enterContext(patch.dict(os.environ, ENV, clear=True))

    def test_default_real_execution_and_unknown_accounting_refuse(self):
        with self.assertRaises(ProviderResponseError):HTTPResult(200,b'{"overflow":1e999}').decode()
        with self.assertRaises(AIError):OpenAICandidateProvider().interpret(TEXT)
        with self.assertRaises(ProviderResponseError):real_inference_accounting(input_tokens=20,price=0)
        # Normal startup still chooses local Ollama; no hosted env selector added.
        self.assertEqual(type(create_provider()).__name__, 'OllamaProvider')

    def test_google_https_exact_bytes_tls_no_retry_and_unit_binding(self):
        from backend.places import ENDPOINT,FIELD_MASK,DiscoveryRequest,SearchArea,search_body
        request=io.Request.make('search','POST',ENDPOINT,FIELD_MASK,search_body(DiscoveryRequest(activity='coffee',destination=SearchArea(name='Baltimore')),3))
        calls=[];session=RecordedSession(HTTPResult(200,b'{"places":[]}'),calls)
        exchange=GoogleHTTPExchange(lambda _: 'fictional-token',session_factory=lambda:session)
        self.assertEqual(GoogleResponseAdapter(exchange)(request.canonical),{'places':[]})
        self.assertEqual(len(calls),1);url,kw=calls[0]
        self.assertEqual(url,ENDPOINT);self.assertFalse(kw['allow_redirects'])
        self.assertEqual(kw['timeout'],(5,15));self.assertTrue(session.verify);self.assertFalse(session.trust_env)
        self.assertEqual(session.mounted[1].max_retries.total,0)
        self.assertEqual(json.loads(kw['data']),request.value()['body'])
        with self.assertRaises(ProviderResponseError):exchange(request.canonical,'search_enterprise',1)
        with self.assertRaises(ProviderResponseError):GoogleHTTPExchange()(request.canonical,'search_pro',1)
        session.reply=HTTPResult(200,b'{}',False)
        session.raw=session.reply
        with self.assertRaises(ProviderResponseError):GoogleResponseAdapter(exchange)(request.canonical)

    def test_frozen_payload_unchanged_except_actual_source_and_raw_retained(self):
        from backend.ai.openai_candidate import PROMPT_FILE
        template=json.loads(PROMPT_FILE.read_bytes())['frozenRequestTemplate']
        actual=json.loads(request_bytes(TEXT));source=actual['input'][-1]['content']
        actual['input'][-1]['content']=''
        self.assertEqual(actual,template);self.assertEqual(source,TEXT)
        raw=response(extraction());calls=[]
        ai=OpenAICandidateProvider(lambda wire:(calls.append(wire),raw)[1])
        self.assertEqual(ai.interpret(TEXT).activities,['coffee','museum'])
        self.assertEqual(calls,[request_bytes(TEXT)]);self.assertIs(ai.raw_response,raw)
        self.assertEqual(ai.raw_response.digest,raw.digest)

    def test_missing_wire_fields_and_null_journey_are_not_repaired(self):
        for field in ('journey','activities','date_expressions'):
            outer=json.loads(response(extraction()).body)
            data=json.loads(outer['output'][0]['content'][0]['text']);data.pop(field)
            outer['output'][0]['content'][0]['text']=json.dumps(data)
            with self.assertRaises(AIError):
                OpenAICandidateProvider(lambda _:HTTPResult(200,json.dumps(outer).encode())).interpret(TEXT)
        outer=json.loads(response(extraction()).body)
        data=json.loads(outer['output'][0]['content'][0]['text']);data['journey']=None
        outer['output'][0]['content'][0]['text']=json.dumps(data)
        with self.assertRaises(AIError):
            OpenAICandidateProvider(lambda _:HTTPResult(200,json.dumps(outer).encode())).interpret(TEXT)

    def test_refusals_corruption_model_usage_and_incomplete_no_retry(self):
        invalid=[response(extraction(),model='other'),response(extraction(),status='incomplete'),
                 response(extraction(),output=[dict(type='message',role='assistant',status='completed',content=[dict(type='refusal',refusal='no')])]),
                 response(extraction(),usage=dict(input_tokens=1,output_tokens=2,total_tokens=4)),
                 response(extraction(),usage=dict(input_tokens=12001,output_tokens=0,total_tokens=12001)),
                 response(extraction(),usage=dict(input_tokens=1,output_tokens=1,total_tokens=2,output_tokens_details={'reasoning_tokens':1})),
                 HTTPResult(200,b'{"status":"completed","status":"failed"}'),
                 HTTPResult(200,b'{}',complete=False),HTTPResult(429,b'{}')]
        for raw in invalid:
            with self.subTest(raw=raw.digest):
                calls=[];ai=OpenAICandidateProvider(lambda wire:(calls.append(wire),raw)[1])
                with self.assertRaises(AIError):ai.interpret(TEXT)
                self.assertEqual(len(calls),1);self.assertIs(ai.raw_response,raw)

    def test_unaltered_raw_journey_and_existing_validator_blocks_complex_path(self):
        from backend.journey_fixtures import reply
        # Existing schema validation, no new graph normalizer/repair in adapter.
        data=reply(['coffee','museum'],optional={1:'maybe museum'},order=[(0,1,'coffee then maybe museum')],location='Baltimore')
        ai=OpenAICandidateProvider(lambda _:response(data))
        raw=ai.interpret('coffee then maybe museum in Baltimore')
        self.assertEqual(raw.journey.stops[1].requirement,'optional')
        self.assertEqual((raw.journey.order[0].before,raw.journey.order[0].after),(0,1))
        self.assertIsNone(raw.date)
        # Test strict malformed graph refusal separately; never fill missing data.
        data['journey']['order']=[dict(before=0,after=99,source=TEXT)]
        with self.assertRaises(AIError):OpenAICandidateProvider(lambda _:response(data)).interpret(TEXT)

    def test_google_strict_request_sku_mask_operation_and_response_bounds(self):
        from backend.places import DiscoveryRequest,SearchArea,search_body,ENDPOINT,FIELD_MASK
        request=io.Request.make('search','POST',ENDPOINT,FIELD_MASK,search_body(DiscoveryRequest(activity='coffee',destination=SearchArea(name='Baltimore')),3))
        self.assertEqual(google_request(request.canonical)[1:],('search_pro',1))
        with self.assertRaises(ProviderResponseError):GoogleResponseAdapter()(request.canonical)
        for change in [dict(url='https://example.com'),dict(mask='*'),dict(operation='details'),dict(method='GET')]:
            v=request.value();v.update(change)
            altered=io.Request.make(v['operation'],v['method'],v['url'],v['mask'],v['body'])
            with self.assertRaises(ProviderResponseError):google_request(altered.canonical)
        for raw in [HTTPResult(302,b'{}'),HTTPResult(200,b'[]'),HTTPResult(200,b'{}',complete=False),HTTPResult(200,b'x'*1048577)]:
            calls=[];port=GoogleResponseAdapter(lambda *args:(calls.append(args),raw)[1])
            with self.assertRaises(ProviderResponseError):port(request.canonical)
            self.assertEqual(len(calls),1)

    def test_actual_interpret_pending_real_transports_planner_and_card_contract(self):
        calls=[];ai=OpenAICandidateProvider(lambda wire:(calls.append(wire),response(extraction()))[1])
        initial=interpret_request(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'),ai,now=NOW)
        self.assertIsNotNone(initial.pending)
        ready=interpret_request(InterpretationInput(text=TEXT,pending=initial.pending,answers=ClarificationAnswers(date='2026-11-07'),calendarTimezone='America/New_York'),ai,now=NOW)
        self.assertEqual(len(calls),1);self.assertIsNotNone(ready.request)
        exchanges=[]
        def exchange(payload,sku,units):
            v=json.loads(payload);exchanges.append((v,sku,units))
            data=search_fixture(v['body']) if v['operation']=='search' else matrix_fixture(v['body'])
            return GoogleHTTPExchange(lambda _: 'fictional-token',session_factory=lambda:RecordedSession(HTTPResult(200,json.dumps(data).encode()),[]))(payload,sku,units)
        codec=GoogleResponseAdapter(exchange)
        # Authority stand-in only for this unit test; SQL-backed tests use GrantBroker.
        class Owner:
            def dispatch(self,request):return codec(request.canonical)
            def reserve(self,*args):
                from contextlib import nullcontext
                return nullcontext()
        token=io._active.set(Owner())
        try:
            result=real_plans(PlannerInput(**ready.request.model_dump(),startingLocation=outing().startingLocation),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
        finally:io._active.reset(token)
        self.assertEqual(len(result.provisionalPlans),3)
        self.assertEqual({v['operation'] for v,_,_ in exchanges},{'search','matrix'})
        for card in result.provisionalPlans:
            self.assertEqual([v.activity for v in card.candidate.venues],['coffee','museum'])
            self.assertTrue(all(v.id==v.providerPlaceId for v in card.candidate.venues))
            for stop in card.stops:
                credit=stop.venue.evidenceLabels['attribution']
                self.assertTrue(credit['google_maps_required'])
                self.assertEqual(credit['brand'],'Google Maps')
                self.assertEqual(credit['third_party'][0]['provider'],'Synthetic credit')
                self.assertEqual(stop.venue.evidenceLabels['claims']['name']['certainty'],'reported')
            self.assertIsNone(card.costPerPerson)
            self.assertTrue(card.routeEvidence);self.assertGreater(card.totalTravel,0)
        type(result).model_validate_json(result.model_dump_json())

    def test_adapter_enters_existing_authenticated_dispatch_owner_boundary(self):
        config={'service':'dispatcher'};value={'payload':'unchanged-envelope'}
        adapter=GoogleResponseAdapter(lambda *args:HTTPResult(200,b'{}'))
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        dispatch=Mock(return_value={'checked':True})
        with patch.dict(sys.modules,{'private_runtime.owned_dispatch':SimpleNamespace(dispatch=dispatch)}):
            self.assertEqual(adapter.dispatch(config,value),{'checked':True})
            dispatch.assert_called_once_with(config,value,adapter)
        with self.assertRaises(ProviderResponseError):GoogleResponseAdapter().dispatch(config,value)

    def test_real_shared_evidence_and_inference_accounting_remain_closed(self):
        from experiments.shared_state.evidence_models import pack
        from experiments.shared_state.contracts import Denied
        with self.assertRaises(Denied) as refusal:
            pack({'route':{'duration':'120s'}},'google_real_v1')
        self.assertEqual(refusal.exception.code,'unreviewed_data_policy')
        with self.assertRaises(ProviderResponseError):
            real_inference_accounting(input_tokens=12000,output_tokens=2000)

    def test_matrix_mode_dimensions_and_empty_search_no_invented_results(self):
        from backend.routes import matrix_body,RoutePoint,ENDPOINT,FIELD_MASK
        p=RoutePoint(id='a',place_id='Fixture_a')
        for mode,sku in [('drive','matrix_pro_element'),('walk','matrix_element')]:
            body=matrix_body([p],[p],mode)
            wire=io.Request.make('matrix','POST',ENDPOINT,FIELD_MASK,body).canonical
            self.assertEqual(google_request(wire)[1:],(sku,1))
            body['routingPreference']='TRAFFIC_AWARE_OPTIMAL'
            with self.assertRaises(Exception):google_request(io.Request.make('matrix','POST',ENDPOINT,FIELD_MASK,body).canonical)
        from backend.places import PlacesDiscovery,DiscoveryRequest,SearchArea
        owner=type('Owner',(),{'dispatch':lambda _,request:GoogleResponseAdapter(lambda *args:HTTPResult(200,b'{"places":[]}'))(request.canonical),
                             'reserve':lambda *args:__import__('contextlib').nullcontext()})()
        token=io._active.set(owner)
        try:
            result=PlacesDiscovery(ProviderBudget(ProviderSettings(mode='real')).outing()).discover_many([DiscoveryRequest(activity='coffee',destination=SearchArea(name='Baltimore'))])
            self.assertFalse(result.candidates)
        finally:io._active.reset(token)


if __name__=='__main__':unittest.main()
