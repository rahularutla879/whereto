"""Offline v3 blockers, lossless compaction and original-journal continuation."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.ai import Interpretation
from scripts import cloud_model52 as e
from scripts import cloud_model52_live as live


class RevisionTests(unittest.TestCase):
    def test_all_examples_lossless_and_system_unchanged(self):
        examples, audit = e.compact_examples()
        self.assertEqual(len(examples), 19)
        self.assertEqual(e.messages('')[0]['content'], e.SYSTEM_PROMPT)
        for (text, original), (newtext, reduced), removed in zip(e.EXAMPLES, examples, audit):
            self.assertEqual(text, newtext)
            self.assertEqual(Interpretation.model_validate(original), Interpretation.model_validate(reduced))
            self.assertEqual({**reduced, **removed['removedDefaults']}, original)
            self.assertEqual(reduced.get('activities'), original.get('activities'))
            self.assertEqual(reduced.get('journey'), original.get('journey'))

    def test_schema_only_titles_removed_in_common_projection(self):
        def strip(node):
            if isinstance(node, dict):
                return {k:strip(v) for k,v in node.items() if k != 'title'}
            if isinstance(node, list):
                return [strip(v) for v in node]
            return node
        self.assertEqual(e.wire_schema('google'),strip(e.schema()))
        self.assertEqual(e.wire_schema('openai'),strip(e.schema()))
        self.assertEqual(e.metadata()['schemaHash'],'7ca1ed2e2701d4adc4735bc523abba1c7eb09060c5fa61b07da37673d8aec965')

    def test_google_exact_outgoing_json_and_invalid_enum(self):
        for case in e.corpus()['cases']:
            payload=json.loads(json.dumps(e.Adapter('google',None).payload(case['text'])))
            self.assertTrue(live.validate_google_request(payload))
        for change in ('enum','legacy','cap','tool'):
            bad=copy.deepcopy(payload)
            if change=='enum': bad['generationConfig']['thinkingConfig']['thinkingLevel']='low'
            if change=='legacy': bad['generationConfig']['responseSchema']={}
            if change=='cap': bad['generationConfig']['maxOutputTokens']=2001
            if change=='tool': bad['tools']=[]
            with self.assertRaises(e.AdmissionError): live.validate_google_request(bad)

    def test_openai_counts_exact_responses_representation(self):
        payload=e.Adapter('openai',None).payload(e.corpus()['cases'][0]['text'])
        path,body=live.count_body('openai',payload)
        self.assertEqual(path,'/responses/input_tokens')
        self.assertEqual(body,{k:payload[k] for k in ('model','input','text')})
        self.assertEqual(live.inference_path('openai'),'/responses')
        self.assertEqual(payload['max_output_tokens'],2000)
        self.assertFalse(payload['store'])

    def test_complete_count_caps_malformed_permission_and_original_12408(self):
        for count, http_status, expected_ready in ((12408,200,False),(11488,200,True),(11489,200,False),(True,200,False),(0,200,False),(None,200,False),(10931,401,False)):
            def reply(_self, method, path, body=None):
                if method=='GET': return {'_http_status':200}
                return {'_http_status':http_status,'input_tokens':count,'totalTokens':count}
            with self.subTest(count=count,status=http_status), tempfile.TemporaryDirectory() as directory, \
                 patch.object(live,'credentials',return_value={p:'fake' for p in e.CANDIDATES}), \
                 patch.object(live.HTTP,'request',reply), patch.object(live.time,'sleep'), \
                 patch.object(live,'PREP',Path(directory)/'readiness.json'), patch.object(e,'STATE',Path(directory)):
                report=live.prepare()
                self.assertEqual(report['providers']['anthropic']['ready'],expected_ready)
                self.assertFalse(report['providers']['openai']['ready'])
                self.assertFalse((Path(directory)/'journal.sqlite').exists())

    def test_original_rows_metadata_and_allowance_survive_revision_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.sqlite'
            original=e.metadata(); original['promptVersion']='legacy-test'
            ledger=e.Ledger(path,original)
            case=e.corpus()['cases'][0]
            e.run_one(ledger,e.Adapter('google',lambda _: {'error':{'type':'synthetic_400'}}),case,1,1000)
            saved=ledger.db.execute('SELECT * FROM attempts').fetchall()
            root=ledger.db.execute('SELECT config FROM metadata').fetchone()
            ledger.close()
            record_hash=e.digest(json.loads(saved[0][5]))
            with patch.object(live,'LEGACY_CONFIG_HASH',e.digest(original)),patch.object(live,'LEGACY_RECORD_HASH',record_hash):
                continued=live.continuation_ledger(path)
                self.assertEqual(continued.db.execute('SELECT config FROM metadata').fetchone(),root)
                self.assertEqual(continued.db.execute('SELECT * FROM attempts').fetchall(),saved)
                self.assertFalse(continued.reserve('google',case['id'],1))
                self.assertTrue(continued.reserve('google',e.corpus()['cases'][1]['id'],1))
                self.assertEqual(continued.db.execute('SELECT count(*),sum(charge) FROM attempts').fetchone(),(2,33000000))
                continued.close()
                resumed=live.continuation_ledger(path)
                self.assertFalse(resumed.reserve('google',e.corpus()['cases'][1]['id'],1))
                self.assertEqual(resumed.db.execute('SELECT config FROM metadata').fetchone(),root)
                self.assertEqual(resumed.db.execute("SELECT * FROM attempts WHERE case_id=?",(case['id'],)).fetchall(),saved)
                resumed.close()
                with patch.object(e,'SPEND_CAP',13_000_000_000):
                    with self.assertRaises(e.AdmissionError): live.continuation_ledger(path)
            with self.assertRaises(e.AdmissionError): live.continuation_ledger(path)
            with self.assertRaises(e.AdmissionError): live.continuation_ledger(Path(directory)/'missing.sqlite')

    def test_http_failure_is_not_inference_latency_or_semantic_success(self):
        report=e.summarize([{'status':'provider_error','latencyMs':1149.79,'usage':None}])
        self.assertIsNone(report['p50Ms'])
        self.assertIsNone(report['fullyCorrect'])
        self.assertEqual(report['successfulInferenceLatencyDenominator'],0)
        self.assertEqual(report['maxOperationLatencyMs'],1149.79)

    def test_review_template_contains_original_source_and_all_judgments_pending(self):
        record={'caseId':e.corpus()['cases'][0]['id'],'repetition':1}
        review=e.review_template([record])['reviews'][0]
        self.assertEqual(review['sourceScenario'],e.corpus()['cases'][0])
        self.assertEqual(set(review['fields']),set(e.SEMANTIC_FIELDS))
        self.assertTrue(all(v=={'applicable':None,'correct':None} for v in review['fields'].values()))
        self.assertIsNone(review['outcome'])

    def test_review_corpus_covers_all_66_original_gold_sources(self):
        review=e.corpus_review_template()
        self.assertEqual([c['sourceScenario'] for c in review['cases']],e.corpus()['cases'])
        self.assertEqual(review['corpusHash'],e.CORPUS_SHA)
        self.assertEqual(len(review['cases']),66)
        self.assertTrue(all(set(c['fields'])==set(e.SEMANTIC_FIELDS) for c in review['cases']))

    def test_subset_prepare_never_refreshes_other_provider_expired_readiness(self):
        class Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026,11,7,1,tzinfo=timezone.utc)
        def reply(_self, method, path, body=None):
            return {'_http_status':200,'input_tokens':1000} if method=='POST' else {'_http_status':200}
        with tempfile.TemporaryDirectory() as directory, patch.object(e,'STATE',Path(directory)), \
             patch.object(live,'PREP',Path(directory)/'readiness.json'), \
             patch.object(live,'credentials',return_value={p:'fake' for p in e.CANDIDATES}), \
             patch.object(live.HTTP,'request',reply), patch.object(live.time,'sleep'), \
             patch.object(live,'datetime',Frozen):
            old='2020-01-01T00:00:00+00:00'
            live.private_json(live.PREP,{'configHash':e.digest(e.metadata()),'preparedAt':old,
                'providers':{'google':{'ready':True,'inputUpperBound':1000,'accountGatesReviewed':True}}})
            merged=live.prepare(('anthropic',))
            self.assertEqual(merged['providers']['google']['preparedAt'],old)
            self.assertNotEqual(merged['preparedAt'],old)
            with patch.object(live,'continuation_ledger',side_effect=lambda p:e.Ledger(p,e.metadata())), \
                 patch.object(live,'HTTP') as send:
                with self.assertRaisesRegex(e.AdmissionError,'Provider-specific readiness expired'):
                    live.live(max_new_attempts=1)
                send.assert_not_called()

    def test_completed_responses_error_null_and_failed_http_classification(self):
        from backend.test_cloud_model52 import response, output
        case=e.corpus()['cases'][0]
        saved=response('openai',output(case))
        saved.update(error=None,_http_status=200)
        adapter=e.Adapter('openai',None)
        text,usage,status=adapter.decode(saved)
        self.assertEqual(status,'complete')
        self.assertEqual(usage,(100,20))
        self.assertTrue(e.score(case,text)['structuredValid'])
        self.assertFalse(e.score(case,text)['automatedFailures'])
        for error,http in (({'type':'invalid_request_error'},200),(None,400),({},400)):
            failed=copy.deepcopy(saved);failed.update(error=error,_http_status=http)
            self.assertEqual(adapter.decode(failed),(None,None,'provider_error'))

    def test_credentials_fail_closed_and_no_other_provider_key_in_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'keys'
            path.write_text('OPENAI_API_KEY=fake-one\nANTHROPIC_API_KEY=fake-two\nGEMINI_API_KEY=fake-three\n')
            path.chmod(0o600)
            with patch.object(live,'ENV',path):
                self.assertEqual(live.credentials()['google'],'fake-three')
                path.chmod(0o644)
                with self.assertRaises(e.AdmissionError): live.credentials()
        with patch.object(live.requests.Session,'request') as send:
            send.return_value.content=b'{"error":{"status":"INVALID_ARGUMENT","details":[]}}'
            send.return_value.status_code=400; send.return_value.headers={}
            result=live.HTTP('google','fake-three').request('POST',live.inference_path('google'),{})
            self.assertEqual(result['_http_status'],400)
            self.assertEqual(send.call_args.kwargs['headers'],{'Content-Type':'application/json','x-goog-api-key':'fake-three'})
            self.assertEqual(send.call_count,1)


if __name__=='__main__': unittest.main()
