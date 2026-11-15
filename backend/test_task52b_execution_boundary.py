"""Composite frozen B2 runtime + new boundary; fictional keys/state/providers."""
from contextlib import closing
from copy import deepcopy
import fcntl
import json
import multiprocessing
import os
import sqlite3
import unittest
from unittest.mock import patch

# Normal backend discovery must not import any frozen privileged profile.
OPT_IN = __name__=='_task52b_execution_tests'
if OPT_IN:
    from backend import test_task52_diagnostic_progression as fake
    from scripts import task52b_execution_boundary as q
    from scripts import task52b_execution_identity as identity
    from scripts import task52b_evidence_access as evidence
    from scripts import task52_q4b as reader
    NOW=fake.NOW



def die_child(directory,trust,permission,raw,payload,point):
    engine=q.AppendEngine(directory,trust)
    engine.simulate_one(permission,q.SyntheticSend(raw,payload,
        failure='crash_before_raw' if point=='before_raw' else None),NOW,
        crash_at=None if point=='before_raw' else point)


def lock_child(directory,trust):
    try:
        with q.AppendEngine(directory,trust).lock():pass
    except q.Denied:os._exit(0)
    os._exit(99)


@unittest.skipUnless(__name__=='_task52b_execution_tests','Use the pinned frozen-B2 offline launcher')
class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=fake.SyntheticKeys()
        cls.responses=fake.fake_responses()
        cls.requests=identity.requests()

    @classmethod
    def tearDownClass(cls):cls.keys.close()

    def fixture(self,active=True):
        fixture=q.SyntheticExecution(self.keys.trust)
        self.addCleanup(fixture.close)
        packets=fake.scope(self.keys,fixture.fixture)
        if active:fixture.engine.activate_synthetic_scope(packets,NOW)
        return fixture,packets

    def send(self,fixture,packets,*,response=None,failure=None,permission=None,payload=None):
        response=self.responses[0] if response is None else response
        return fixture.engine.simulate_one(permission or fake.execute(self.keys,fixture.fixture,packets),
            q.SyntheticSend(json.dumps(response,indent=2).encode(),payload or self.requests[0]['bytes'],failure=failure),NOW)

    def state(self,f):
        with f.engine.lock():return f.engine.state()

    def test_success_preserves_raw_bytes_and_distinct_evidence(self):
        f,p=self.fixture();o=self.send(f,p)
        rows,facts,exposure,child=self.state(f)
        self.assertEqual((len(rows),child),(11,2500000))
        self.assertEqual([x['kind'] for x in facts],['SCOPE','START','INTENT','OUTCOME'])
        op=o['operation'];raw=json.loads((f.fixture.directory/f'raw-{op}.json').read_bytes())
        self.assertEqual(q.b64decode(raw['bytesBase64']),json.dumps(self.responses[0],indent=2).encode())
        self.assertTrue((f.fixture.directory/f'decoded-{op}.json').exists())
        self.assertTrue((f.fixture.directory/f'grading-{op}.json').exists())
        self.assertIsNone(o['data']['assessment']['raw']['fullyCorrectIndependent'])
        self.assertFalse(o['data']['assessment']['diagnostic']['planningAuthorized'])

    def test_no_next_operation_without_independent_review(self):
        f,p=self.fixture();self.send(f,p)
        with self.assertRaises(q.Denied):self.send(f,p)
        self.assertEqual(len(self.state(f)[0]),11)

    def test_duplicate_operation_and_operator_permission(self):
        f,p=self.fixture();permission=fake.execute(self.keys,f.fixture,p);self.send(f,p,permission=permission)
        with self.assertRaises(q.Denied):self.send(f,p,permission=permission)
        self.assertEqual(len(list(f.fixture.directory.glob('dispatch-*'))),1)

    def test_duplicate_review_and_scope_permissions(self):
        f,p=self.fixture();o=self.send(f,p);review=fake.review(self.keys,f.fixture,o)
        f.engine.record_review(review,NOW)
        with self.assertRaises(q.Denied):f.engine.record_review(review,NOW)
        with self.assertRaises(q.Denied):f.engine.activate_synthetic_scope(p,NOW)

    def test_provider_refusal_is_not_success(self):
        response={'model':'gpt-6-luna','output':[{'content':[{'type':'refusal'}]}]}
        f,p=self.fixture();self.send(f,p,response=response)
        self.assertEqual(self.state(f)[1][-1]['kind'],'HALT')
        self.assertEqual(self.state(f)[3],2500000)

    def test_schema_failure_retains_raw_and_halts(self):
        response=deepcopy(self.responses[0]);response['output'][0]['content'][0]['text']='{}'
        f,p=self.fixture();self.send(f,p,response=response)
        self.assertEqual(self.state(f)[1][-1]['kind'],'HALT')
        self.assertEqual(self.state(f)[3],2500000)

    def test_uncertain_timeouts_keep_full_charge_and_never_retry(self):
        for failure in ('before_send','possible_send'):
            with self.subTest(failure=failure):
                f,p=self.fixture()
                with self.assertRaises(q.Denied):self.send(f,p,failure=failure)
                self.assertEqual(self.state(f)[3],2500000)
                with self.assertRaises(q.Denied):self.send(f,p)
                self.assertEqual(len(list(f.fixture.directory.glob('dispatch-*'))),1)

    def test_real_process_crashes_and_restart_never_resend(self):
        for point in ('after_reserve','after_intent','before_raw','after_send'):
            with self.subTest(point=point):
                f,p=self.fixture();permission=fake.execute(self.keys,f.fixture,p)
                process=multiprocessing.get_context('fork').Process(target=die_child,args=(
                    f.fixture.directory,self.keys.trust,permission,json.dumps(self.responses[0]).encode(),self.requests[0]['bytes'],point))
                process.start();process.join(45)
                if process.is_alive():process.terminate();process.join();self.fail('Crash child timed out')
                self.assertEqual(process.exitcode,73)
                engine=q.AppendEngine(f.fixture.directory,self.keys.trust)
                with engine.lock():self.assertEqual(engine.state()[3],2500000)
                with self.assertRaises(q.Denied):self.send(f,p,permission=permission)
                self.assertLessEqual(len(list(f.fixture.directory.glob('dispatch-*'))),1)

    def test_competing_process_refuses_common_experiment_lock(self):
        f,p=self.fixture()
        with f.engine.lock():
            process=multiprocessing.get_context('fork').Process(target=lock_child,args=(f.fixture.directory,self.keys.trust))
            process.start();process.join(30)
            if process.is_alive():process.terminate();process.join();self.fail('Lock child timed out')
            self.assertEqual(process.exitcode,0)
        self.assertEqual(len(self.state(f)[0]),10)

    def test_source_model_provider_payload_and_build_substitution_refuse(self):
        f,p=self.fixture()
        for field in ('sourceHash','payloadHash'):
            packet=fake.execute(self.keys,f.fixture,p,change=lambda e,k=field:e['data'].__setitem__(k,'0'*64))
            with self.assertRaises((q.Denied,ValueError)):self.send(f,p,permission=packet)
        for kwargs in ({'provider':'google'},{'endpoint':'/v1/other'},{'method':'GET'}):
            with self.assertRaises(q.Denied):
                f.engine.simulate_one(fake.execute(self.keys,f.fixture,p),q.SyntheticSend(b'{}',self.requests[0]['bytes'],**kwargs),NOW)
        with self.assertRaises(q.Denied):self.send(f,p,payload=self.requests[1]['bytes'])
        with patch.object(identity,'MANIFEST_SHA','0'*64),self.assertRaises(ValueError):self.send(f,p)
        self.assertEqual(len(self.state(f)[0]),10)

    def test_missing_captured_evidence_or_journal_blocks(self):
        f,p=self.fixture();o=self.send(f,p)
        (f.fixture.directory/f'raw-{o["operation"]}.json').unlink()
        with f.engine.lock(),self.assertRaises(q.Denied):f.engine.state()
        f2,p2=self.fixture();(f2.fixture.directory/'journal.sqlite').unlink()
        with self.assertRaises((q.Denied,sqlite3.Error)):self.send(f2,p2)

    def test_altered_capture_or_unknown_response_model_halts(self):
        f,p=self.fixture();o=self.send(f,p)
        path=f.fixture.directory/f'dispatch-{o["operation"]}.json'
        data=json.loads(path.read_bytes());data['payloadHash']='0'*64;path.write_text(json.dumps(data))
        with f.engine.lock(),self.assertRaises(q.Denied):f.engine.state()
        f2,p2=self.fixture();response=deepcopy(self.responses[0]);response['model']='wrong-model'
        with self.assertRaises(q.Denied):self.send(f2,p2,response=response)
        self.assertEqual(self.state(f2)[3],2500000)

    def test_missing_model_and_duplicate_raw_response_keys_halt(self):
        for raw in (b'{"status":"completed"}',b'{"model":"gpt-6-luna","model":"other"}'):
            with self.subTest(rawKind=len(raw)):
                f,p=self.fixture()
                with self.assertRaises(q.Denied):
                    f.engine.simulate_one(fake.execute(self.keys,f.fixture,p),
                        q.SyntheticSend(raw,self.requests[0]['bytes']),NOW)
                self.assertEqual(self.state(f)[3],2500000)
                self.assertEqual(self.state(f)[1][-1]['kind'],'HALT')

    def test_sql_update_delete_replacement_and_unbound_insert_refuse(self):
        f,p=self.fixture()
        with f.engine.lock(),closing(f.engine.db()) as db:
            for query in ('UPDATE attempts SET charge=0','DELETE FROM attempts','DROP TABLE attempts',
                          "UPDATE metadata SET config='forged'",'PRAGMA synchronous=OFF'):
                with self.subTest(query=query),self.assertRaises(q.Denied):db.execute(query)
            with self.assertRaises(q.Denied):db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',('openai','journey-01',3,'reserved_uncertain',0,'{}'))
        self.assertEqual(len(self.state(f)[0]),10)

    def test_real_journal_and_live_transport_always_refuse(self):
        with self.assertRaises(q.Denied):q.AppendEngine(reader.STATE,self.keys.trust)
        with self.assertRaises(base_error()):q.live_dispatch()


def base_error():
    from scripts.task52_q4a import Refused
    return Refused


@unittest.skipUnless(__name__=='_task52b_execution_tests','Use the pinned frozen-B2 offline launcher')
class ReadOnlyEvidenceTests(unittest.TestCase):
    def test_encoded_normalized_and_authority_aliases_refuse(self):
        # Only read-only URIs are attempted, so a guard bug cannot write data.
        source=evidence.ORIGINAL_ROOT/evidence.RELATIVE/'journal.sqlite'
        aliases=[f'file:{str(source).replace("/Users/","/%55sers/")}?mode=ro',
                 f'file://localhost{source}?mode=ro',
                 f'file:{source.parent}/../task52-model-evaluation/journal.sqlite?mode=ro']
        for uri in aliases:
            with self.subTest(aliasKind=aliases.index(uri)),self.assertRaises(ValueError):
                sqlite3.connect(uri,uri=True)

    def test_original_path_inodes_read_only_and_sql_mutation_refused(self):
        # The suite is run inside the separately versioned evidence context.
        before=reader.q1.private_hashes()
        with sqlite3.connect(reader.READ_URI,uri=True) as db:
            with self.assertRaises(sqlite3.Error):db.execute('DELETE FROM attempts')
        with (reader.STATE/'journal.sqlite').open('rb') as fd:
            self.assertEqual(fcntl.fcntl(fd.fileno(),fcntl.F_GETFL)&os.O_ACCMODE,os.O_RDONLY)
        # Exercise the shared rejection guards without ever requesting a
        # writable OS descriptor to the original journal, even on a test bug.
        for mode in ('w','a','r+'):
            with self.assertRaises(ValueError):evidence.require_read_mode(mode)
        for flags in (os.O_RDWR,os.O_WRONLY|os.O_TRUNC):
            with self.assertRaises(ValueError):evidence.require_read_flags(flags)
        self.assertEqual(before,reader.q1.private_hashes())
        self.assertEqual(len(before),324)
