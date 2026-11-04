"""Bounded first-page work, original Unicode provenance, safe errors; no Google."""
import json,unittest
from pathlib import Path
from io import BytesIO
from datetime import datetime,timezone
from unittest.mock import Mock,patch
from pydantic import ValidationError
from backend import test_advanced_planning as fixture
from backend.test_stop_resolution import place
from backend.test_advanced_routing import start
from backend.test_advanced_timing import duration
from backend.ai import Interpretation,AIError,AISettings
from backend.ai.ollama import OllamaProvider
from backend.interpretation import InterpretationInput,interpret_request

class InitialCoverage(unittest.TestCase):
    def setUp(self):
        self.h=fixture.IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def prepare(self,count=8,slow=2):
        self.h.records=[self.h.records[0]]+[place(f'Synthetic_cafe_{i}',f'Invented cafe {i}',types=['cafe'],lat=40.75+i*.0001) for i in range(count)]
        for i in range(slow):self.h.values['DRIVE','Synthetic_college',f'Synthetic_cafe_{i}']=11000
        return self.h.session(endpoint={'kind':'origin','source':'return to starting point'},total_duration=duration(180,'maximum'))
    def test_underfilled_initial_stage_uses_remaining_original_allowance(self):
        s=self.prepare();r=self.h.run_session(s,startingLocation=start())
        self.assertEqual(len(r.options),3);self.assertEqual(s.initial_fill_elements,8)
        self.assertEqual(s.outing.usage()['reservedMatrixElements'],17);self.assertEqual(len(self.h.searches),2)
        self.assertEqual(s.selection_counts['checked'],8);self.assertEqual(s.selection_counts['eligible'],6)
        self.assertEqual(len({o.id for o in r.options}),3);self.assertTrue(r.canExpand and r.canDiscover)
        for o in r.options:
            self.assertEqual(o.stops[0].placeId,'Synthetic_college');self.assertEqual(o.ending,'origin');self.assertEqual(o.totalConstraint.minutes,180)
            self.assertEqual(o.state,'unverified');self.assertEqual(len(o.legs),3)
        before=len(self.h.searches);seen={o.id for o in r.options}
        r=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertEqual(before,len(self.h.searches));self.assertTrue(seen.isdisjoint(o.id for o in r.options))
        print('Initial fill fixture:',s.selection_counts,'usage',s.outing.usage(),'latency',s.latencies)
    def test_checked_third_is_not_held_back_or_routed_again(self):
        s=self.prepare(slow=1);r=self.h.run_session(s,startingLocation=start())
        self.assertEqual(len(r.options),3);self.assertEqual(s.selection_counts['eligible'],3)
        self.assertEqual(s.initial_fill_elements,0);self.assertEqual(s.outing.usage()['reservedMatrixElements'],9)
    def test_only_two_identities_no_padding_discovery_remains(self):
        s=self.prepare(count=2,slow=0);r=self.h.run_session(s,startingLocation=start())
        self.assertEqual(len(r.options),2);self.assertEqual(s.initial_fill_elements,0)
        self.assertFalse(r.canExpand);self.assertTrue(r.canDiscover)
        self.assertEqual(r.exploration['combination'],'checked_pool_exhausted')
    def test_duplicate_ids_collapse(self):
        s=self.prepare(count=2,slow=0);self.h.records+=self.h.records[1:]
        r=self.h.run_session(s,startingLocation=start());self.assertEqual(len(r.options),2)
    def test_local_admission_does_not_discard_two_valid_options(self):
        from backend.provider_budget import ProviderBudget,ProviderSettings
        s=self.prepare();s.outing=ProviderBudget(ProviderSettings(matrix_elements_per_outing=9)).outing()
        r=self.h.run_session(s,startingLocation=start());self.assertEqual(len(r.options),2)
        self.assertEqual(r.code,'provider_local_admission');self.assertEqual(s.outing.usage()['reservedMatrixElements'],9)
        self.assertTrue(r.canExpand)
    def test_failed_initial_transport_is_not_automatically_retried(self):
        from backend.routes import RouteError
        for code in ('quota','application_limit','provider'):
            s=self.prepare();self.h.route_error=RouteError(code,'invented')
            before=len(self.h.calls);r=self.h.run_session(s,startingLocation=start())
            self.assertEqual(s.initial_fill_elements,0);self.assertEqual(len(self.h.calls)-before,1)
            if code=='quota':self.assertFalse(r.canExpand or r.canDiscover)

class UnicodeSources(unittest.TestCase):
    def run_row(self,row):
        p=Mock();p.interpret.return_value=Interpretation.model_validate(row['raw'])
        r=interpret_request(InterpretationInput(text=row['text']),p,now=datetime(2026,11,4,15,tzinfo=timezone.utc))
        self.assertEqual(p.interpret.call_count,1);return r
    def test_actual_recorded_unicode_and_then_keep_stops_order_endpoint_budget(self):
        for row in json.loads(Path(__file__).with_name('unicode_extractions.json').read_text()):
            r=self.run_row(row);j=r.interpretation.journey
            self.assertEqual(len(j.stops),2);self.assertEqual(j.ordering,'constrained')
            self.assertEqual([(e.before,e.after) for e in j.order],[(0,1)])
            self.assertTrue(all(s.requirement=='required' for s in j.stops));self.assertIsNotNone(j.endpoint)
            if '90' in row['text']:self.assertEqual((j.total_duration.minutes,j.total_duration.relation),(90,'maximum'))
            if row['text'].startswith('College'):self.assertIn('Which college',r.issues[0])
            else:self.assertTrue(r.context or r.questions)
    def test_common_punctuation_restores_exact_accented_name_not_transliteration(self):
        text='Visit Café l’Étoile → coffee tomorrow.'
        raw={'activities':["Café l'Étoile",'coffee'],'budget_per_person':None,'date':None,'location':None,'preferences':[],
             'journey':{'stops':[{'source':"Café l'Étoile",'kind':'named_place'},{'source':'coffee'}],
             'order':[{'before':0,'after':1,'source':"Café l'Étoile → coffee"}]}}
        r=self.run_row({'text':text,'raw':raw});self.assertEqual(r.interpretation.journey.stops[0].source,'Café l’Étoile')
        self.assertEqual(r.interpretation.journey.stops[0].kind,'named_place')
    def test_arrows_whitespace_and_missing_or_reversed_order(self):
        row=json.loads(Path(__file__).with_name('unicode_extractions.json').read_text())[2]
        for arrow in ('→','->','⇒','➜','⟶'):
            changed=json.loads(json.dumps(row));changed['text']=changed['text'].replace('→',arrow)
            changed['raw']['journey']['order'][0]['source']=changed['text']
            r=self.run_row(changed);self.assertEqual(r.interpretation.journey.ordering,'constrained')
        changed=json.loads(json.dumps(row));changed['text']=changed['text'].replace(' → ','\u00a0→\u2009');changed['raw']['journey']['order'][0]['source']=changed['text']
        self.assertEqual(self.run_row(changed).interpretation.journey.ordering,'constrained')
        for edit in ('missing','reverse','dropped'):
            changed=json.loads(json.dumps(row))
            if edit=='missing':changed['raw']['journey']['order']=[]
            if edit=='reverse':changed['raw']['journey']['order'][0].update(before=1,after=0)
            if edit=='dropped':changed['raw']['activities'].pop(1);changed['raw']['journey']['stops'].pop(1);changed['raw']['journey']['order']=[]
            r=self.run_row(changed);self.assertIsNone(r.request);self.assertEqual(r.executionStatus,'clarification_required')
    def test_controls_length_and_original_whitespace(self):
        self.assertEqual(InterpretationInput(text='  coffee\u00a0tomorrow  ').text,'  coffee\u00a0tomorrow  ')
        self.assertEqual(len(InterpretationInput(text='coffee'+' '*3994).text),4000)
        for text in ('coffee\0','coffee\x1b','coffee\u202e','coffee'+' '*4000):
            with self.assertRaises(ValidationError):InterpretationInput(text=text)

class SafeInterpreterErrors(unittest.TestCase):
    def test_adapter_distinguishes_timeout_bad_json_schema_and_unavailable(self):
        for response,code in ((TimeoutError(),'llm_timeout'),(b'not json','llm_invalid_response'),(json.dumps({'done':True,'message':{'content':'{}'}}).encode(),'llm_invalid_response')):
            p=OllamaProvider(AISettings());p._opener.open=Mock()
            if isinstance(response,Exception):p._opener.open.side_effect=response
            else:p._opener.open.return_value=BytesIO(response)
            with self.assertRaises(AIError) as caught:p.interpret('coffee')
            self.assertEqual(caught.exception.code,code)
    def test_public_failure_never_exposes_private_adapter_details(self):
        from backend.main import interpret_outing
        for code in ('llm_timeout','llm_invalid_response','llm_unavailable'):
            with patch('backend.main.interpret_request',side_effect=AIError('private SQL GPS token payload',code=code)):
                with self.assertLogs('whereto.failures') as log:r=interpret_outing(InterpretationInput(text='coffee'))
                data=json.loads(r.body);self.assertEqual(data['code'],code)
                self.assertNotIn('private SQL',str(data));self.assertNotIn('GPS',' '.join(log.output))
                self.assertNotRegex(data['message'],r'Ollama|Qwen|Python|JSON|backend')
