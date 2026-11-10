"""Q4C synthetic keys and fake execution ONLY. No personal SSH or real grants."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
import uuid
from unittest.mock import patch

from scripts import task52_q1 as q1
from scripts import task52_q4a as base
from scripts import task52_q4c_auth as a
from scripts import task52_q4c_protocol as p
from scripts import task52_q4c_identity as identity
from scripts.task52_q4b import inspect_original
from backend.test_task52_q4a import fake_responses

NOW=datetime(2026,11,10,12,tzinfo=timezone.utc)


class SyntheticKeys:
    """Test-only signer. Always generates NEW disposable keys, never enrolls real keys."""
    def __init__(self,revoked=()):
        self.temp=tempfile.TemporaryDirectory(prefix='whereto-q4c-synthetic-keys-')
        self.directory=Path(self.temp.name);os.chmod(self.directory,0o700);self.paths={};pub={};self.n=0
        for name in ('owner','reviewer','operator'):
            key=self.directory/name
            subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-C','FICTIONAL-Q4C-TEST-ONLY','-f',str(key)],
                           check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin'},timeout=5)
            self.paths[name]=key;pub[name]=' '.join(key.with_suffix('.pub').read_text().split()[:2])
            assert key.stat().st_mode & 0o777 == 0o600
        self.public=pub;self.make_trust(revoked)

    def make_trust(self,revoked=()):
        r={'version':'52b-q4c-revocations-v1','revokedKeyHashes':sorted(a.public_key(self.public[n]) for n in revoked)}
        rev=a.canonical(r);roles={}
        for role,ns in a.ROLES.items():
            name=self.name(role);roles[role]={'principal':'q4c-'+name,'key':self.public[name],'namespace':'whereto.task52b.'+ns}
        t={'version':'52b-q4c-trust-v1','audience':a.AUDIENCE,'syntheticOnly':True,'revocationHash':q1.sha(rev),'roles':roles}
        raw=a.canonical(t);self.trust=a.Trust(raw,q1.sha(raw),rev,q1.sha(rev))

    def name(self,role):return 'owner' if role in ('owner','readiness_permission') else 'reviewer' if role in ('rubric','review') else 'operator'

    def sign_bytes(self,raw,role,*,signer=None,namespace=None):
        self.n+=1;path=self.directory/f'fictional-message-{self.n}'
        path.write_bytes(raw);os.chmod(path,0o600)
        subprocess.run(['/usr/bin/ssh-keygen','-Y','sign','-f',str(self.paths[signer or self.name(role)]),
            '-n',namespace or 'whereto.task52b.'+a.ROLES[role],str(path)],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin'},timeout=5)
        return {'envelope':raw.decode(),'signature':Path(str(path)+'.sig').read_text()}

    def packet(self,role,data,fixture,*,now=NOW,change=None,signer=None,namespace=None):
        e={'version':a.VERSION,'audience':a.AUDIENCE,'purpose':'synthetic_evaluation_only','role':role,
           'principal':'q4c-'+self.name(role),'namespace':'whereto.task52b.'+a.ROLES[role],
           'scope':fixture.scope,'journal':fixture.journal_hash,'nonce':uuid.uuid4().hex+uuid.uuid4().hex,
           'issuedAt':p.utc(now),'expiresAt':p.utc(now+timedelta(hours=1)),
           'trustHash':self.trust.document_hash,'revocationHash':self.trust.revocation_hash,
           'binding':identity.binding(),'data':deepcopy(data)}
        if change:change(e)
        return self.sign_bytes(a.canonical(e),role,signer=signer,namespace=namespace)

    def close(self):self.temp.cleanup()


def scope(keys,f,now=NOW):
    packets={role:keys.packet(role,data,f,now=now) for role,data in (
        ('owner',a.owner_data()),('rubric',a.rubric_data()),('readiness_permission',a.permission_data()))}
    ready={'permissionHash':a.digest(packets['readiness_permission']),'observedAt':p.utc(now),'counts':[5100]*5,'outputCap':2000,
           'checks':{k:True for k in ('key','keyExpiry','credits','rechargeOff','prices','processing','rates','model')}}
    packets['readiness']=keys.packet('readiness',ready,f,now=now)
    return packets


def execute(keys,f,packets,index=0,previous=a.ZERO,**kw):
    s=base.plan()['slots'][index]
    data={'slot':s['slot'],'sourceHash':s['sourceSHA256'],'payloadHash':s['payloadHash'],'inputBound':12000,'outputBound':2000,
          'reservation':2500000,'ownerHash':a.digest(packets['owner']),'readinessHash':a.digest(packets['readiness']),'previousReviewHash':previous}
    return keys.packet('execute',data,f,**kw)


def review(keys,f,o,*,disagree=False,**kw):
    data={'operationID':o['operation'],'outcomeHash':o['hash'],'responseHash':o['data']['responseHash'],
          'judgments':{k:'agree' for k in base.plan()['slots'][0]['Q1FieldExpectations']},'decision':'disagree' if disagree else 'agree'}
    return keys.packet('review',data,f,**kw)


def crash_child(directory,trust,permission,response,point):
    os.environ.clear()
    with patch('socket.socket.connect',side_effect=AssertionError('No provider/network')):
        p.Engine(directory,trust).simulate_one(permission,base.FakeTransport(response),NOW,crash_at=point)


def competitor(directory,trust,pipe):
    os.environ.clear()
    try:
        with p.Engine(directory,trust).lock():pipe.send('unsafe')
    except a.Denied:pipe.send('refused')
    finally:pipe.close()


class Q4CTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=q1.private_hashes();cls.baseline=inspect_original();cls.keys=SyntheticKeys();cls.responses=fake_responses()

    @classmethod
    def tearDownClass(cls):
        cls.keys.close();assert q1.private_hashes()==cls.before;assert inspect_original()==cls.baseline

    def fixture(self,*,active=True,keys=None,base_charge=1000000):
        keys=keys or self.keys;f=p.SyntheticJournal(keys.trust,base_charge=base_charge);self.addCleanup(f.close)
        e=f.engine();packets=scope(keys,f)
        if active:e.activate_synthetic_scope(packets,NOW)
        return f,e,packets

    def test_positive_six_roles_openssh_signatures_and_offline_authority(self):
        f,e,s=self.fixture()
        o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        packets={**s,'execute':execute(self.keys,f,s),'review':review(self.keys,f,o)}
        for role,packet in packets.items():
            v=a.verify(packet,role,self.keys.trust,NOW)
            self.assertEqual(v.role,role);self.assertFalse(v.execution_authorized)
        self.assertFalse(identity.verify_build()['liveDispatchAvailable'])

    def test_unsigned_forged_signature_wrong_signer_namespace_and_role(self):
        f,_,_=self.fixture(active=False)
        good=self.keys.packet('owner',a.owner_data(),f)
        for bad in ({'envelope':good['envelope'],'signature':''},dict(good,signature='x'*200)):
            with self.assertRaises(a.Denied):a.verify(bad,'owner',self.keys.trust,NOW)
        for kw in ({'signer':'operator'},{'namespace':'wrong.namespace'}):
            with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',a.owner_data(),f,**kw),'owner',self.keys.trust,NOW)
        with self.assertRaises(a.Denied):a.verify(good,'rubric',self.keys.trust,NOW)
        wrong=self.keys.packet('rubric',a.rubric_data(),f,signer='owner')
        with self.assertRaises(a.Denied):a.verify(wrong,'rubric',self.keys.trust,NOW)

    def test_canonical_exact_signed_bytes_duplicate_json_float_unknown_fields(self):
        f,_,_=self.fixture(active=False);good=self.keys.packet('owner',a.owner_data(),f);raw=good['envelope'].encode()
        for raw in (b' '+raw,raw+b'\n',raw.replace(b'"attempts":5',b'"attempts":5,"attempts":5'),
                    raw.replace(b'"attempts":5',b'"attempts":5.0')):
            with self.assertRaises(a.Denied):a.verify(self.keys.sign_bytes(raw,'owner'),'owner',self.keys.trust,NOW)
        changed=deepcopy(good);changed['envelope']=changed['envelope'].replace('"attempts":5','"attempts":4')
        with self.assertRaises(a.Denied):a.verify(changed,'owner',self.keys.trust,NOW)
        with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',a.owner_data(),f,change=lambda e:e.update(extra=True)),'owner',self.keys.trust,NOW)

    def test_wrong_binding_model_prompt_schema_proposal_build_root_slots_and_amounts(self):
        f,_,_=self.fixture(active=False)
        mutations=[lambda e:e['binding'].update(executionBuildHash='0'*64),
                   lambda e:e['binding'].update(parentProposalHash='0'*64),
                   lambda e:e['binding']['parentSpecification'].update(model='other'),
                   lambda e:e['binding']['parentSpecification'].update(promptHash='0'*64),
                   lambda e:e['binding']['parentSpecification'].update(wireSchemaHash='0'*64),
                   lambda e:e['binding']['originalBaseline'].update(rootHash='0'*64),
                   lambda e:e['binding']['orderedSlots'][0].update(slot=['openai','journey-01',1]),
                   lambda e:e['data'].update(childCap=12500001),lambda e:e['data'].update(attempts=True)]
        for mutate in mutations:
            with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',a.owner_data(),f,change=mutate),'owner',self.keys.trust,NOW)

    def test_expiry_future_time_and_scope_journal_binding(self):
        f,e,s=self.fixture(active=False)
        for change in (lambda v:v.update(issuedAt=p.utc(NOW+timedelta(seconds=1))),
                       lambda v:v.update(expiresAt=p.utc(NOW)),lambda v:v.update(expiresAt='bad')):
            with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',a.owner_data(),f,change=change),'owner',self.keys.trust,NOW)
        s['owner']=self.keys.packet('owner',a.owner_data(),f,change=lambda v:v.update(journal='0'*64))
        with self.assertRaises(a.Denied):e.activate_synthetic_scope(s,NOW)

    def test_trust_revocation_pins_and_owner_cannot_enroll_reviewer_key(self):
        f,_,_=self.fixture(active=False);good=self.keys.packet('owner',a.owner_data(),f)
        bad=a.Trust(self.keys.trust.document,'0'*64,self.keys.trust.revocations,self.keys.trust.revocation_hash)
        with self.assertRaises(a.Denied):a.verify(good,'owner',bad,NOW)
        t=a.parse(self.keys.trust.document)
        t['roles']['rubric']['key']=t['roles']['review']['key']=self.keys.public['owner']
        raw=a.canonical(t);bad=a.Trust(raw,q1.sha(raw),self.keys.trust.revocations,self.keys.trust.revocation_hash)
        with self.assertRaises(a.Denied):bad.checked()
        keys=SyntheticKeys(revoked=('owner',));self.addCleanup(keys.close)
        f,_,_=self.fixture(active=False,keys=keys)
        with self.assertRaises(a.Denied):a.verify(keys.packet('owner',a.owner_data(),f),'owner',keys.trust,NOW)

    def test_five_signed_steps_require_reviews_and_retain_original_halt_and_money(self):
        f,e,s=self.fixture();prefix=e.state()[0][:10];previous=a.ZERO
        for i in range(5):
            op=execute(self.keys,f,s,i,previous)
            o=e.simulate_one(op,base.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(o['data']['assessment']['raw']['mechanicalFailures'],[])
            self.assertIsNone(o['data']['assessment']['raw']['fullyCorrectIndependent'])
            if i<4:
                with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,i+1),base.FakeTransport(self.responses[i+1]),NOW)
            e.record_review(review(self.keys,f,o),NOW);previous=e.state()[1][-1]['hash']
            with self.assertRaises(a.Denied):e.simulate_one(op,base.FakeTransport(self.responses[i]),NOW)
        rows,facts,total,extra=e.state();self.assertEqual(rows[:10],prefix);self.assertEqual(extra,12500000);self.assertEqual(total,22500000)
        self.assertTrue(all(r[4:6]==('reserved_uncertain',2500000) for r in rows[10:]));self.assertEqual(rows[9][4],'recorded_halted')
        self.assertEqual(len(list(f.directory.glob('fake-send-*'))),5)

    def test_missing_duplicate_conflicting_scope_and_wrong_slot(self):
        f,e,s=self.fixture(active=False)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        e.activate_synthetic_scope(s,NOW)
        with self.assertRaises(a.Denied):e.activate_synthetic_scope(s,NOW)
        with self.assertRaises(a.Denied):e.activate_synthetic_scope(scope(self.keys,f),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)
        bad=execute(self.keys,f,s,change=lambda v:v['data'].update(slot=['openai','journey-01',1]))
        with self.assertRaises(a.Denied):e.simulate_one(bad,base.FakeTransport(self.responses[0]),NOW)

    def test_edited_prefix_negative_null_unknown_rows_and_schema_fail_closed(self):
        for sql in ("UPDATE attempts SET record='changed' WHERE rowid=1",'UPDATE attempts SET charge=-1 WHERE rowid=1',
                    "UPDATE attempts SET status='unknown' WHERE rowid=1",'UPDATE attempts SET provider=NULL WHERE rowid=1',
                    'DELETE FROM attempts WHERE rowid=10',"INSERT INTO attempts VALUES(NULL,NULL,NULL,'unknown',-1,NULL)",
                    'CREATE TABLE unknown(x)'):
            f,e,s=self.fixture()
            with closing(e.db()) as db:db.execute(sql);db.commit()
            with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
            self.assertFalse(list(f.directory.glob('fake-send-*')))

    def test_rowid_deletion_and_reuse_cannot_erase_operation_identity(self):
        f,e,s=self.fixture();o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        e.record_review(review(self.keys,f,o),NOW)
        with closing(e.db()) as db:db.execute('DELETE FROM attempts WHERE rowid=11');db.commit()
        with self.assertRaises(a.Denied):e.state()
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_admission_caps_and_aggregate_synthetic_exhaustion(self):
        for args in ((594,7,0,0,0),(10,198,0,0,0),(10,7,12000000000,0,0),(10,7,0,5,0),(10,7,0,0,12500000),(-1,7,0,0,0)):
            with self.assertRaises(a.Denied):p.admission(*args)
        f,e,s=self.fixture(base_charge=1200000000)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        self.assertEqual(len(e.state()[0]),10)

    def test_stale_readiness_payload_and_incorrect_full_token_reservation(self):
        f,e,s=self.fixture(active=False)
        old=a.parse(s['readiness']['envelope'].encode())['data'];old['observedAt']=p.utc(NOW-timedelta(days=1))
        s['readiness']=self.keys.packet('readiness',old,f)
        with self.assertRaises(a.Denied):e.activate_synthetic_scope(s,NOW)
        f,e,s=self.fixture()
        for change in (lambda v:v['data'].update(payloadHash='0'*64),lambda v:v['data'].update(inputBound=12001),
                       lambda v:v['data'].update(outputBound=2001),lambda v:v['data'].update(reservation=1)):
            with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,change=change),base.FakeTransport(self.responses[0]),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,now=NOW+timedelta(hours=2)),base.FakeTransport(self.responses[0]),NOW+timedelta(hours=2))

    def test_uncertain_send_provider_error_missing_outcome_and_child_halt_restart(self):
        for failure in ('uncertain_send','response_loss','http_error'):
            f,e,s=self.fixture();op=execute(self.keys,f,s)
            try:e.simulate_one(op,base.FakeTransport(failure=failure),NOW)
            except a.Denied:pass
            e=p.Engine(f.directory,f.trust);self.assertEqual(len(e.state()[0]),11)
            self.assertGreaterEqual(e.state()[3],2500000)
            for i in (0,1):
                with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,i),base.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_review_disagreement_wrong_signer_and_critical_raw_order_error(self):
        f,e,s=self.fixture();o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o,signer='owner'),NOW)
        e.record_review(review(self.keys,f,o,disagree=True),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)
        f,e,s=self.fixture();bad=deepcopy(self.responses[0]);v=json.loads(bad['output'][0]['content'][0]['text'])
        v['journey']['order'].append({'before':0,'after':1,'source':'Coffee, museum, then'});bad['output'][0]['content'][0]['text']=json.dumps(v)
        o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(bad),NOW)
        self.assertIn('unsupported_missing_or_unproven_order',o['data']['assessment']['raw']['mechanicalFailures'])
        self.assertEqual(o['data']['assessment']['guarded']['disposition'],'blocked')
        with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)

    def test_process_crashes_seven_boundaries_never_retry_consumed_or_progress(self):
        ctx=multiprocessing.get_context('fork')
        for point in sorted(p.CRASHES):
            f,e,s=self.fixture();op=execute(self.keys,f,s)
            proc=ctx.Process(target=crash_child,args=(f.directory,f.trust,op,self.responses[0],point));proc.start();proc.join(20)
            self.assertFalse(proc.is_alive());self.assertEqual(proc.exitcode,73)
            rows,facts,_,_=e.state();self.assertEqual(len(rows),10 if point in ('before_start','before_reserve','before_commit') else 11)
            count=len(list(f.directory.glob('fake-send-*')))
            if point!='before_start':
                for i in (0,1):
                    with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,i),base.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(len(list(f.directory.glob('fake-send-*'))),count)

    def test_two_process_operators_excluded_and_real_path_registry_loss_refused(self):
        f,e,_=self.fixture();ctx=multiprocessing.get_context('fork');rx,tx=ctx.Pipe(False)
        with e.lock():
            proc=ctx.Process(target=competitor,args=(f.directory,f.trust,tx));proc.start();proc.join(10)
            self.assertEqual(proc.exitcode,0);self.assertTrue(rx.poll(1));self.assertEqual(rx.recv(),'refused')
        rx.close();tx.close()
        with self.assertRaises(a.Denied):p.Engine(q1.ROOT/'backend/.local/task52-model-evaluation',f.trust)
        for grant in (None,{},a.owner_data()):
            with self.assertRaises(base.Refused):base.live_dispatch(grant)
        saved=p.REGISTRY.pop(str(f.directory))
        try:
            with self.assertRaises(a.Denied):p.Engine(f.directory,f.trust)
        finally:p.REGISTRY[str(f.directory)]=saved

    def test_global_nonce_collision_rejected_before_reservation_or_send(self):
        f,e,s=self.fixture();nonce=a.parse(s['owner']['envelope'].encode())['nonce']
        bad=execute(self.keys,f,s,change=lambda v:v.update(nonce=nonce))
        with self.assertRaises(a.Denied):e.simulate_one(bad,base.FakeTransport(self.responses[0]),NOW)
        self.assertEqual(len(e.state()[0]),10);self.assertFalse(list(f.directory.glob('fake-send-*')))

    def test_missing_outcome_and_reused_deleted_rowid_do_not_restore_permission(self):
        for attack in ('missing_outcome','reused_rowid'):
            f,e,s=self.fixture();op=execute(self.keys,f,s);e.simulate_one(op,base.FakeTransport(self.responses[0]),NOW)
            if attack=='missing_outcome':
                paths=sorted(f.directory.glob('fact-*'));paths[-1].unlink()
            else:
                with closing(e.db()) as db:
                    row=list(db.execute('SELECT * FROM attempts WHERE rowid=11').fetchone())
                    db.execute('DELETE FROM attempts WHERE rowid=11');row[-1]='{"FICTIONAL":"wrong operation"}'
                    db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',row);db.commit()
            for i in (0,1):
                with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,i),base.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)

    def test_partial_or_unresolved_signed_review_cannot_progress(self):
        f,e,s=self.fixture();o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        partial=review(self.keys,f,o,change=lambda v:v['data']['judgments'].pop('source_provenance'))
        with self.assertRaises(a.Denied):e.record_review(partial,NOW)
        unresolved=review(self.keys,f,o,change=lambda v:v['data']['judgments'].update(source_provenance='unresolved'))
        e.record_review(unresolved,NOW)
        # Even removal of the terminal HALT does not make a disagreement pass.
        sorted(f.directory.glob('fact-*'))[-1].unlink()
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1,e.state()[1][-1]['hash']),base.FakeTransport(self.responses[1]),NOW)

    def test_malformed_envelopes_and_changed_build_fail_closed(self):
        f,_,_=self.fixture(active=False)
        for mutate in (lambda v:v.update(nonce='short'),lambda v:v.update(audience='LIVE'),
                       lambda v:v.update(principal='q4c-other'),lambda v:v.update(namespace='whereto.task52b.execute-one.v1')):
            with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',a.owner_data(),f,change=mutate),'owner',self.keys.trust,NOW)
        good=self.keys.packet('owner',a.owner_data(),f)
        with patch.object(identity,'MANIFEST_SHA','0'*64),self.assertRaises(a.Denied):
            a.verify(good,'owner',self.keys.trust,NOW)

    def test_verifier_timeout_and_revocation_document_tamper_never_fallback(self):
        f,_,_=self.fixture(active=False);good=self.keys.packet('owner',a.owner_data(),f)
        with patch.object(a.subprocess,'run',side_effect=subprocess.TimeoutExpired('ssh-keygen verify',5)),self.assertRaises(a.Denied):
            a.verify(good,'owner',self.keys.trust,NOW)
        trust=self.keys.trust
        bad=a.Trust(trust.document,trust.document_hash,trust.revocations+b' ',trust.revocation_hash)
        with self.assertRaises(a.Denied):a.verify(good,'owner',bad,NOW)

    def test_input_count_bounds_and_stale_response_binding_reject(self):
        f,e,s=self.fixture(active=False)
        for count in (0,9953,True):
            data=a.parse(s['readiness']['envelope'].encode())['data'];data['counts'][0]=count
            wrong={**s,'readiness':self.keys.packet('readiness',data,f)}
            with self.assertRaises(a.Denied):e.activate_synthetic_scope(wrong,NOW)
        e.activate_synthetic_scope(s,NOW)
        o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        bad=review(self.keys,f,o,change=lambda v:v['data'].update(responseHash='0'*64))
        with self.assertRaises(a.Denied):e.record_review(bad,NOW)
        self.assertEqual(e.state()[1][-1]['kind'],'OUTCOME')
