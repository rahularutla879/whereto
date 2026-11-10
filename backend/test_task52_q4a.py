"""Q4A fake-state tests. No live transport or approval authentication claimed."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from scripts import task52_q1 as q1
from scripts import task52_q3 as q3
from scripts import task52_q4a as q
from scripts.task52_q4a_scoring import assess
from scripts import task52_q4a_identity as identity
from backend.ai import Interpretation

NOW = datetime(2026,11,10,12,tzinfo=timezone.utc)


def wire(value):
    """Fictional canonical examples expanded into the unchanged wire schema."""
    value = Interpretation.model_validate(value).model_dump(mode='json')
    value.pop('start_time'); value.pop('end_time')
    value['journey'].pop('order_conflict')
    if value['journey']['deadline']:
        value['journey']['deadline'].pop('minute')
    return value


def envelope(value):
    return {'model':'gpt-6-luna','status':'completed','error':None,
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}],
            'usage':{'input_tokens':5100,'output_tokens':500,'output_tokens_details':{'reasoning_tokens':0}}}


def fake_responses():
    """Authored fictional positives; no recorded model output is edited."""
    corpus = json.loads((q1.ROOT/'docs/task52-evaluation-corpus.json').read_text())['cases']
    result = []
    for case, repeat in q3.SLOTS:
        original = next(c for c in corpus if c['id'] == case)
        if 'expectedExtraction' in original:
            value = wire(original['expectedExtraction'])
        else:
            repeated = case == 'extension-repeated'
            labels = ['Coffee','museum','coffee'] if repeated else ['pharmacy','bank','coffee']
            value = wire({'activities':labels, 'budget_per_person':None, 'date':None,
                'location':'Jersey City', 'preferences':[], 'date_expressions':['tomorrow'],
                'journey': {'stops':[{'source':x} for x in labels], 'ordering':'constrained',
                    'order':[{'before':1,'after':2,'source':'museum, then coffee'}] if repeated else
                            [{'before':0,'after':1,'source':'pharmacy before the bank'}],
                    'endpoint':{'kind':'origin','source':'return to the starting point'} if repeated else None,
                    'total_duration':{'minutes':180,'relation':'maximum','source':'within three hours'} if repeated else None}})
        result.append(envelope(value))
    return result


def child_crash(directory, response, point):
    # Fork inherits only the already-created fictional capability. Credentials
    # are not read or passed; transport is a closed fake, no provider client.
    os.environ.clear()
    e=q.Engine(directory)
    with patch('socket.socket.connect',side_effect=AssertionError('No network')):
        e.simulate_next(q.plan()['slots'][0]['slot'],q.FakeTransport(response),
                        now=NOW,readiness=e.fake_readiness(NOW),crash_at=point)


def child_compete(directory, pipe):
    os.environ.clear()
    try:
        with q.Engine(directory).locked():
            pipe.send('unexpected-lock')
    except q.Refused:
        pipe.send('refused')
    finally:
        pipe.close()


class SuccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=q3.baseline();cls.before=q1.private_hashes()
        cls.responses=fake_responses();cls.p=q.plan()

    @classmethod
    def tearDownClass(cls):
        assert q1.private_hashes()==cls.before
        assert q3.baseline()==cls.baseline

    def fixture(self,approved=True):
        f=q.FictionalFixture();self.addCleanup(f.close)
        e=f.engine()
        if approved:e.simulate_approval()
        return f,e

    def step(self,e,index=0,response=None,**kwargs):
        return e.simulate_next(self.p['slots'][index]['slot'],q.FakeTransport(self.responses[index] if response is None else response),
                               now=NOW,readiness=e.fake_readiness(NOW),**kwargs)

    def change(self,index,mutate):
        response=deepcopy(self.responses[index]);v=json.loads(response['output'][0]['content'][0]['text'])
        mutate(v);response['output'][0]['content'][0]['text']=json.dumps(v)
        return response

    def test_manifest_parent_and_source_allowlist(self):
        m=identity.verify(full=True)
        self.assertFalse(m['liveDispatchAvailable']);self.assertFalse(m['paidApproval'])
        self.assertEqual(m['parentDigest'],q1.digest(self.p))
        self.assertEqual(m['parentConfigurationHash'],self.p['successorConfigurationHash'])
        self.assertIsNone(m['configuration']['futureEvaluatorImplementationHash'])
        for field in ('model','promptHash','wireSchemaHash','runtime','Q1RubricHash','orderingPolicyHash'):
            self.assertEqual(m['configuration'][field],self.p['successorVersionSpecification'][field])
        with patch.object(identity,'MANIFEST_SHA','0'*64),self.assertRaises(ValueError):identity.verify()
        for field in ('model','promptVersion','wireSchemaHash','runtime','originalCorpusHash','Q1RubricHash'):
            f,e=self.fixture();bad=deepcopy(self.p);bad['successorVersionSpecification'][field]='wrong'
            with self.assertRaises(q.Refused):self.step(e,candidate=bad)

    def test_no_live_path_arbitrary_directory_transport_or_environment_activation(self):
        for arg in (None,{'force':True},os.environ):
            with self.assertRaises(q.Refused):q.live_dispatch(arg)
        with self.assertRaises(q.Refused):q.Engine(q1.ROOT/'backend/.local/task52-model-evaluation')
        f,e=self.fixture()
        for arg in (lambda payload: {},object()):
            with self.assertRaises(q.Refused):e.simulate_next(self.p['slots'][0]['slot'],arg,now=NOW,readiness=e.fake_readiness(NOW))
        for name in ('scripts/task52_q4a.py','scripts/task52_q4a_scoring.py','scripts/task52_q4a_identity.py'):
            import ast
            tree=ast.parse((q1.ROOT/name).read_text())
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertNotIn('scripts.cloud_model52_live',imports)
        marker=f.directory/'fixture.json';marker.unlink()
        with self.assertRaises(q.Refused):e.state()

    def test_missing_forged_and_duplicate_owner_or_reviewer(self):
        f,e=self.fixture(False)
        with self.assertRaises(q.Refused):self.step(e)
        for kw in ({'owner':'owner'},{'reviewer':'Codex'},{'reviewer':None}):
            with self.assertRaises(q.Refused):e.simulate_approval(**kw)
        e.simulate_approval()
        with self.assertRaises(q.Refused):e.simulate_approval()
        self.assertEqual(len(e.state()[1]),10)

    def test_all_ten_consumed_slots_and_wrong_next_slot(self):
        f,e=self.fixture()
        for anchor in self.p['baseline']['rows']:
            with self.assertRaises(q.Refused):e.simulate_next(anchor['slot'],q.FakeTransport(self.responses[0]),now=NOW,readiness=e.fake_readiness(NOW))
        with self.assertRaises(q.Refused):self.step(e,1)
        self.assertEqual(len(e.state()[1]),10)

    def test_root_anchors_source_and_fact_tampering(self):
        for query in ("UPDATE metadata SET config='wrong'", "UPDATE attempts SET record='wrong' WHERE rowid=10"):
            f,e=self.fixture()
            with closing(e.db()) as db:db.execute(query);db.commit()
            with self.assertRaises(q.Refused):self.step(e)
        for key in ('sourceSHA256','payloadHash','rubricCaseDigest'):
            f,e=self.fixture();bad=deepcopy(self.p);bad['slots'][0][key]='wrong'
            with self.assertRaises(q.Refused):self.step(e,candidate=bad)
        f,e=self.fixture();(f.directory/'fact-0002.json').write_text('{')
        with self.assertRaises(q.Refused):self.step(e)

    def test_token_readiness_and_reservation_boundaries(self):
        for kw in ({'input_bound':12001},{'output_bound':2001},{'output_bound':0},{'input_bound':1},{'input_bound':True},{'charge':1},{'charge':2500001}):
            f,e=self.fixture()
            with self.assertRaises(q.Refused):self.step(e,**kw)
            self.assertEqual(len(e.state()[1]),10)
        f,e=self.fixture()
        for stamp in (NOW-timedelta(days=1),NOW+timedelta(seconds=1),NOW.replace(tzinfo=None)):
            with self.assertRaises(q.Refused):e.simulate_next(self.p['slots'][0]['slot'],q.FakeTransport(self.responses[0]),now=NOW,readiness=e.fake_readiness(stamp))
        value=e.fake_readiness(NOW);value['completeCounts'][0]=12000
        with self.assertRaises(q.Refused):e.simulate_next(self.p['slots'][0]['slot'],q.FakeTransport(self.responses[0]),now=NOW,readiness=value)

    def test_original_and_incremental_ceilings_with_fictional_lowered_limits(self):
        # Deliberately separate low-cap fixtures, never altered paid counters.
        for key,limit in (('global',10),('provider',7),('spend',47366625),('extra',2499999),('attempts',0)):
            f,e=self.fixture(False);path=f.directory/'fixture.json';marker=json.loads(path.read_text())
            marker['limits'][key]=limit;path.write_text(json.dumps(marker));q.REGISTRY[str(f.directory)]=q1.digest(marker)
            e.simulate_approval()
            with self.assertRaises(q.Refused):self.step(e)
            self.assertEqual(len(e.state()[1]),10)

    def test_complete_five_fake_steps_review_and_financial_anchors(self):
        f,e=self.fixture();baseline=e.state()[1][:10]
        for i in range(5):
            outcome=self.step(e,i)
            self.assertEqual(outcome['kind'],'OUTCOME')
            a=outcome['data']['assessment'];self.assertTrue(a['structuredValid'])
            self.assertEqual(a['raw']['mechanicalFailures'],[])
            self.assertIsNone(a['raw']['fullyCorrectIndependent'])
            self.assertFalse(a['planningAuthorized'])
            if i==4:
                self.assertFalse(a['legacy']['accepted']);self.assertEqual(a['guarded']['disposition'],'blocked')
            if i<4:
                with self.assertRaises(q.Refused):self.step(e,i+1)
            e.simulate_review(outcome['hash'])
            with self.assertRaises(q.Refused):e.simulate_review(outcome['hash'])
        marker,rows,facts,exposure=e.state()
        self.assertEqual(rows[:10],baseline)
        self.assertEqual([r[0] for r in rows[10:]],list(range(11,16)))
        self.assertTrue(all(r[4:6]==('reserved_uncertain',2500000) for r in rows[10:]))
        self.assertEqual(exposure,59866625);self.assertEqual(len(list(f.directory.glob('fake-send-*'))),5)
        with self.assertRaises(q.Refused):self.step(e)

    def test_raw_critical_failures_stop_even_when_safely_guarded(self):
        mutations=[lambda v:v['journey']['order'].append({'before':0,'after':1,'source':'Coffee, museum, then'}),
                   lambda v:v['journey'].update(order=[]),
                   lambda v:v['journey']['stops'].pop(),
                   lambda v:v['journey']['stops'][0].update(requirement='optional'),
                   lambda v:v['journey']['endpoint'].update(kind='home'),
                   lambda v:v['journey']['total_duration'].update(relation='under'),
                   lambda v:v.update(location='Hyderabad'),
                   lambda v:v.update(date_expressions=[])]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                f,e=self.fixture();outcome=self.step(e,response=self.change(0,mutate))
                self.assertEqual(e.state()[2][-1]['kind'],'HALT')
                self.assertTrue(outcome['data']['assessment']['raw']['mechanicalFailures'])
                with self.assertRaises(q.Refused):self.step(e,1)
                with self.assertRaises(q.Refused):e.simulate_review(outcome['hash'])
                self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_optional_named_identity_partial_order_and_provenance_failures(self):
        for i,mutate in ((1,lambda v:v['journey']['stops'][0].update(source='Other College')),
                         (2,lambda v:v['journey']['order'].append({'before':1,'after':2,'source':'the bank; get coffee whenever convenient'})),
                         (3,lambda v:v['journey']['stops'][1].update(requirement='required')),
                         (1,lambda v:v['journey']['order'][0].update(source='and then'))):
            a=assess(self.p['slots'][i]['slot'],self.change(i,mutate))
            self.assertTrue(a['raw']['mechanicalFailures'])
        self.assertEqual(assess(self.p['slots'][4]['slot'],self.responses[4])['raw']['mechanicalFailures'],[])

    def test_provider_http_incomplete_malformed_duplicate_and_unknown_usage(self):
        for response in ({'model':'gpt-6-luna','error':{}},
                         dict(self.responses[0],status='incomplete'),dict(self.responses[0],model='other'),
                         dict(self.responses[0],usage={}),dict(self.responses[0],usage={'input_tokens':12001,'output_tokens':3000})):
            f,e=self.fixture();outcome=self.step(e,response=response)
            self.assertEqual(e.state()[2][-1]['kind'],'HALT')
            self.assertFalse(outcome['data']['assessment']['structuredValid'])
        for content in ('{', '{"activities":[],"activities":[]}', '{}'):
            response=deepcopy(self.responses[0]);response['output'][0]['content'][0]['text']=content
            self.assertFalse(assess(self.p['slots'][0]['slot'],response)['structuredValid'])

    def test_uncertain_send_response_loss_and_restart_retain_reservation(self):
        for failure in ('uncertain_send','response_loss','http_error'):
            f,e=self.fixture()
            try:e.simulate_next(self.p['slots'][0]['slot'],q.FakeTransport(failure=failure),now=NOW,readiness=e.fake_readiness(NOW))
            except q.Refused:pass
            e=q.Engine(f.directory);self.assertEqual(len(e.state()[1]),11)
            self.assertGreaterEqual(e.state()[3],49866625)
            with self.assertRaises(q.Refused):self.step(e,1)
            with self.assertRaises(q.Refused):self.step(e)
            self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_review_disagreement_and_stale_review_halt_or_refuse(self):
        f,e=self.fixture();outcome=self.step(e)
        for reviewer,digest in (('Codex',outcome['hash']),('FICTIONAL-INDEPENDENT-REVIEWER','wrong')):
            with self.assertRaises(q.Refused):e.simulate_review(digest,reviewer=reviewer)
        with self.assertRaises(q.Refused):e.simulate_review(outcome['hash'],disagreement=True)
        with self.assertRaises(q.Refused):self.step(e,1)

    def test_process_crash_at_seven_durable_boundaries(self):
        ctx=multiprocessing.get_context('fork')
        for point in sorted(q.CRASH_POINTS):
            with self.subTest(point=point):
                f,e=self.fixture();proc=ctx.Process(target=child_crash,args=(f.directory,self.responses[0],point))
                proc.start();proc.join(20)
                self.assertFalse(proc.is_alive());self.assertEqual(proc.exitcode,72)
                state=q.Engine(f.directory).state()
                count=10 if point in ('before_start','before_reserve','before_commit') else 11
                self.assertEqual(len(state[1]),count)
                sends=len(list(f.directory.glob('fake-send-*')))
                self.assertEqual(sends,1 if point in ('after_send','after_outcome') else 0)
                if point=='before_start':
                    self.assertEqual([f['kind'] for f in state[2]],['APPROVAL'])
                    # No admitted operation and no automatic restart; explicit
                    # test invocation may reserve the still-unused first slot.
                else:
                    with self.assertRaises(q.Refused):self.step(q.Engine(f.directory))
                    with self.assertRaises(q.Refused):self.step(q.Engine(f.directory),1)
                self.assertEqual(len(list(f.directory.glob('fake-send-*'))),sends)

    def test_process_lock_and_lost_registry(self):
        ctx=multiprocessing.get_context('fork');f,e=self.fixture();a,b=ctx.Pipe(False)
        with e.locked():
            proc=ctx.Process(target=child_compete,args=(f.directory,b));proc.start();proc.join(10)
            self.assertEqual(proc.exitcode,0);self.assertTrue(a.poll(1));self.assertEqual(a.recv(),'refused')
        a.close();b.close()
        capability=q.REGISTRY.pop(str(f.directory))
        try:
            with self.assertRaises(q.Refused):q.Engine(f.directory)
        finally:q.REGISTRY[str(f.directory)]=capability

    def test_intent_must_match_reservation_and_review_cannot_edit_assessment(self):
        f,e=self.fixture();out=self.step(e)
        path=f.directory/'fact-0003.json';v=json.loads(path.read_text());v['data']['payloadHash']='wrong'
        # Even a recomputed chain cannot change semantic bindings.
        v['hash']=q1.digest({k:x for k,x in v.items() if k!='hash'});path.write_text(json.dumps(v))
        with self.assertRaises(q.Refused):e.state()

    def test_overage_is_retained_without_refunding_lower_usage(self):
        f,e=self.fixture();response=deepcopy(self.responses[0]);response['usage']['output_tokens']=8000
        self.step(e,response=response)
        self.assertEqual(e.state()[3],47366625+5100*125+8000*500)
        self.assertEqual(e.state()[1][-1][5],2500000)
        with self.assertRaises(q.Refused):self.step(e,1)

    def test_unknown_effective_mapping_stops_without_repairing_raw(self):
        from scripts import task52_q4a_scoring as scoring
        real = scoring.interpret_request
        def changed(*args, **kwargs):
            r=real(*args, **kwargs)
            r.interpretation.journey.stops[0].source='changed effective occurrence'
            return r
        raw=deepcopy(self.responses[0])
        with patch.object(scoring,'interpret_request',changed):
            a=assess(self.p['slots'][0]['slot'],raw)
        self.assertFalse(a['mappingKnown'])
        self.assertIn('unresolved_or_changed_effective_mapping',a['raw']['mechanicalFailures'])
        self.assertEqual(raw,self.responses[0]);self.assertIsNone(a['raw']['fullyCorrectIndependent'])

    def test_partial_or_forged_field_review_facts_never_admit_next_slot(self):
        f,e=self.fixture();out=self.step(e)
        with e.locked():
            data=e.review_data(out);data['fields'].pop('source_provenance')
            e.append('REVIEW',out['operation'],data,e.state()[2])
        with self.assertRaises(q.Refused):self.step(e,1)
        self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_dependency_and_source_build_mismatch_fail_closed(self):
        with patch.object(identity,'version',return_value='unknown'),self.assertRaises(ValueError):identity.verify()
        real=Path.read_bytes
        def read(path):
            return real(path)+b' ' if path==q1.ROOT/'scripts/task52_q4a_scoring.py' else real(path)
        with patch.object(Path,'read_bytes',read),self.assertRaises(ValueError):identity.verify()
