"""Prepared supervisor and observation binding; fictional storage/credentials only."""
from datetime import datetime,timezone
from pathlib import Path
from functools import partial
from contextlib import redirect_stdout
import io,json,multiprocessing,os,resource,sys,tempfile,unittest
from unittest.mock import patch,Mock
from scripts import task52b_count_only as c
from scripts import task52b_run_count_once as b
from backend.test_task52b_count_only import Canned,KEY


class SupervisorTests(unittest.TestCase):
    def fixture(self):
        f=c.FictionalCount();self.addCleanup(f.close);return f.directory
    def test_default_missing_send_authorization_never_claims_or_reads_key(self):
        d=self.fixture()
        with patch.object(c,'STATE',d),patch.object(c,'validate_preparation',return_value=None),patch.object(c,'live_preconditions',side_effect=FileNotFoundError),patch.object(c.e,'read_openai_only',side_effect=AssertionError('No credential read')),patch('socket.socket',side_effect=AssertionError('No network')),patch.object(sys,'argv',['count','--execute-count-only-once']):
            with self.assertRaises(SystemExit):b.main()
        self.assertEqual({p.name for p in d.iterdir()},{'scope.json'})
    def test_wrong_cli_purpose_and_expired_evidence_refuse(self):
        for args in ([],['--get'],['--inference'],['--retry']):
            with patch.object(sys,'argv',['count']+args),patch.object(c,'validate_preparation',side_effect=AssertionError('No enrollment')):
                with self.assertRaises(SystemExit):b.main()
        with patch.object(sys,'argv',['count','--execute-count-only-once']),patch.object(c,'validate_preparation',side_effect=c.q.Refused('prior_evidence_stale')),patch.object(c,'live_preconditions',side_effect=AssertionError('No authorization')):
            with self.assertRaises(SystemExit):b.main()
    def test_supervisor_identity_refuses_wrong_parent_and_worker(self):
        d=self.fixture();s=c.e.record(d/'scope.json')
        c.private_create(d/'launcher-claim.json',{'operation':c.OPERATION,'buildSHA256':s['buildSHA256'],'supervisorPID':-1})
        with patch.object(c,'STATE',d):
            with self.assertRaises(c.q.Refused):c.verify_supervision(s)
        # Fictional mutation solely to test the second guard.
        (d/'launcher-claim.json').write_text(json.dumps({'operation':c.OPERATION,'buildSHA256':s['buildSHA256'],'supervisorPID':os.getppid()}))
        c.private_create(d/'runtime.json',{'workerPID':-1,'buildSHA256':s['buildSHA256']})
        with patch.object(c,'STATE',d):
            with self.assertRaises(c.q.Refused):c.verify_supervision(s,True)


class ObservationTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);d=Path(t.name);d.chmod(0o700);now=datetime.now(timezone.utc)
        metadata=d/'metadata.json';enroll=d/'enrollment.json';obs=d/'observation.json';receipt=d/'permission.json';binding=d/'binding.json'
        c.private_create(metadata,{'trackingId':'FICTIONAL','expiresOn':'2099-01-01'})
        c.private_create(enroll,{'trackingId':'FICTIONAL','metadataPath':str(metadata)})
        identity=c.digest(c.e.private_read(enroll));permissions={'listModels':'Read','responses':'Write','unrelated':'None'}
        facts={'project':c.PROJECT,'projectName':'WhereTo Model Evaluation','trackingId':'FICTIONAL','keyName':'WhereTo Task52B Evaluation','status':'Active','expiresOn':'2099-01-01','permissions':permissions,'credentialIdentity':identity,'observedAt':now.isoformat(),'changedPermissions':False,'secretValueAccessed':False}
        c.private_create(obs,facts);raw_hash=c.digest(c.e.private_read(obs))
        p={'project':c.PROJECT,'credentialIdentity':identity,'permissions':permissions,'independentlyEstablished':True,'basis':'independently-observed-dashboard','evidenceSHA256':raw_hash,'observer':'FICTIONAL','observedAt':now.isoformat()}
        c.private_create(receipt,p);ph=c.permission_record(p,identity,now)
        binding.write_text(json.dumps({'credentialIdentity':identity,'permissionSHA256':ph,'observationSHA256':raw_hash}))
        patches=[patch.object(c.e,'PRIVATE_ENROLLMENT',enroll),patch.object(c,'OBSERVATION',obs),patch.object(c,'PERMISSION',receipt),patch.object(c,'BINDING',binding)]
        for p in patches:p.start();self.addCleanup(p.stop)
        return now,obs,binding
    def test_independent_fictional_observation_receipt_binding(self):
        now,obs,binding=self.fixture();self.assertEqual(len(c.verified_permission(now)),64)
    def test_corrupt_or_substituted_observation_and_tracking_refuse(self):
        now,obs,binding=self.fixture();facts=c.e.record(obs);facts['trackingId']='OTHER';obs.write_text(json.dumps(facts))
        with self.assertRaises(c.q.Refused):c.verified_permission(now)
        # Even rehashing the fictional receipt cannot substitute key ownership.
        record=c.e.record(c.PERMISSION);record['evidenceSHA256']=c.digest(c.e.private_read(obs));c.PERMISSION.write_text(json.dumps(record))
        v=json.loads(binding.read_bytes());v.update(observationSHA256=record['evidenceSHA256'],permissionSHA256=c.permission_record(record,record['credentialIdentity'],now));binding.write_text(json.dumps(v))
        with self.assertRaises(c.q.Refused):c.verified_permission(now)
    def test_missing_receipt_and_owner_only_modes_refuse(self):
        now,obs,binding=self.fixture();obs.chmod(0o644)
        with self.assertRaises(c.q.Refused):c.verified_permission(now)
        obs.chmod(0o600);c.PERMISSION.unlink()  # Disposable fictional record only.
        with self.assertRaises(FileNotFoundError):c.verified_permission(now)
