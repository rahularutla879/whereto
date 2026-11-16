"""Disposable SQL/Redis tests of real response codecs at the protected Maps seam.

Source-neutral authored response shapes, never captured owner/provider data.
OpenAI parsing is exercised; its real financial profile remains unavailable.
"""
import json
import os
import unittest
from unittest.mock import patch
from backend.ai.openai_candidate import OpenAICandidateProvider
from backend.provider_responses import GoogleResponseAdapter,GoogleHTTPExchange,HTTPResult
from backend.test_provider_responses import response,extraction,TEXT,NOW,RecordedSession
from backend.real_fixtures import search_fixture,matrix_fixture
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.provider_budget import ProviderBudget,ProviderSettings
from backend.test_real_planning import ENV,outing
from backend.testing_clock import calendar_clock
from experiments.shared_state import test_application_grants as g
from experiments.shared_state import test_financial as f,test_store as core
from experiments.shared_state.application_grants import GrantBroker,GrantIssuer
from experiments.shared_state.contracts import Denied
from experiments.shared_state.evidence_models import canonical


@unittest.skipUnless(os.environ.get('SYNTHETIC_WITNESS_ADMIN_PASSWORD'),'disposable SQL/Redis fixture required')
class RealResponseIntegrationTests(unittest.TestCase):
    def setUp(self):
        g.fixture();self.s=g.store();self.calls=[];self.sent=[];self.model_calls=[]
        self.enterContext(calendar_clock(NOW))
        self.enterContext(patch.dict(os.environ,ENV))
        self.enterContext(patch('requests.sessions.Session.send',side_effect=AssertionError('Network forbidden')))
        self.codec=GoogleResponseAdapter(self.exchange)
        candidate=OpenAICandidateProvider(lambda wire:(self.model_calls.append(wire),response(extraction()))[1])
        # Only the existing FICTIONAL profile can be reserved in this fixture.
        # Its reply exercises Luna decoding offline; it does not attest Luna cost.
        model=g.FakeInference(self.s,g.issuer_connection,g.counter_connection,f.ROOT,
            lambda payload:g.reply(payload,data=candidate.interpret(json.loads(payload)['input']).model_dump(mode='json')))
        issuer=GrantIssuer(g.issuer_connection,f.ROOT,lambda:({'ordinary':core.ordinary()},'synthetic_fresh'))
        self.broker=GrantBroker(self.s,issuer,model,ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)),lambda v:self.codec(canonical(v)),now=NOW)
        model.broker=self.broker
        original=self.s.service.send
        def observed(store,reservation,ordinal,payload,callback):
            self.sent.append((reservation,ordinal,payload))
            return original(store,reservation,ordinal,payload,callback)
        self.enterContext(patch.object(self.s.service,'send',side_effect=observed))

    def exchange(self,payload,sku,units):
        value=json.loads(payload);self.calls.append((value,sku,units))
        data=search_fixture(value['body']) if value['operation']=='search' else matrix_fixture(value['body'])
        return GoogleHTTPExchange(lambda _: 'fictional-token',session_factory=lambda:RecordedSession(HTTPResult(200,json.dumps(data).encode()),[]))(payload,sku,units)

    def ready(self):
        token,result=self.broker.interpret(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'),execution={'startingLocation':outing().startingLocation})
        self.assertIsNotNone(result.pending)
        result=self.broker.answer(token,ClarificationAnswers(date='2026-11-07'))
        self.assertIsNotNone(result.request);self.assertEqual(len(self.model_calls),1)
        self.assertGreater(self.s.snapshot()['gross'],0) # Fictional envelope only; NOT a Luna quote.
        return token

    def test_native_pending_planner_protected_maps_response_and_replay(self):
        token=self.ready();result=self.broker.plan(token)
        self.assertEqual(len(result.provisionalPlans),3)
        for card in result.provisionalPlans:
            self.assertEqual([v.activity for v in card.candidate.venues],['coffee','museum'])
            for stop in card.stops:
                credit=stop.venue.evidenceLabels['attribution']
                self.assertTrue(credit['google_maps_required'])
                self.assertEqual(credit['brand'],'Google Maps')
                self.assertEqual(credit['third_party'][0]['provider'],'Synthetic credit')
                self.assertEqual(stop.venue.evidenceLabels['claims']['name']['certainty'],'reported')
            self.assertIsNone(card.costPerPerson);self.assertTrue(card.routeEvidence)
        gross=self.s.snapshot()['gross'];self.assertGreater(gross,0)
        self.assertEqual(g.witness().call('status')['gross'],gross)
        with self.assertRaises(Denied):self.broker.plan(token)
        reservation,ordinal,payload=self.sent[0]
        with self.assertRaises(Denied):self.s.service.send(self.s,reservation,ordinal,payload,lambda _:self.fail('Replay reached I/O'))
        self.assertEqual(self.s.snapshot()['gross'],gross)
        self.assertEqual(len(self.model_calls),1)

    def test_missing_shared_evidence_blocks_existing_reservation(self):
        lease,cap,payload=g.maps(self.s)
        self.s.evidence.client.flushdb()
        from uuid import uuid4
        with self.assertRaises(Denied):self.s.reserve(lease,cap,str(uuid4()))
        self.assertFalse(self.calls);self.assertEqual(self.s.snapshot()['gross'],0)

    def test_interrupted_response_retains_charge_and_cannot_continue(self):
        token=self.ready()
        def interrupted(*args):raise TimeoutError('fictional interrupted exchange')
        self.codec=GoogleResponseAdapter(interrupted)
        with self.assertRaises(TimeoutError):self.broker.plan(token)
        gross=self.s.snapshot()['gross'];self.assertGreater(gross,0)
        self.assertEqual(g.witness().call('status')['gross'],gross)
        self.assertTrue(g.witness().call('status')['quarantined'])
        with self.assertRaises(Denied):self.broker.plan(token)
