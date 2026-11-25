"""Fictional GCS state/identity tests. No cloud client or genuine key enrollment."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from hashlib import sha256
import json,os,subprocess,unittest
from deployment import b1_gcs as g

class Tests(unittest.TestCase):
    def test_private_exact_bucket(self):g.validate_bucket(g.bucket_spec())
    def test_public_or_wrong_location_refused(self):
        for key,value in [('name','other-bucket'),('location','US'),('storageClass','ARCHIVE'),('projectNumber','000000000000')]:
            v=g.bucket_spec();v[key]=value
            with self.assertRaises(g.Refused):g.validate_bucket(v)
        for key,value in [('publicAccessPrevention','inherited'),('uniformBucketLevelAccess',{'enabled':False})]:
            v=g.bucket_spec();v['iamConfiguration'][key]=value
            with self.assertRaises(g.Refused):g.validate_bucket(v)
    def test_retention_and_unreviewed_features_refused(self):
        for patch in ({'versioning':{'enabled':True}},{'retentionPolicy':{'retentionPeriod':'1'}},{'retentionPolicy':{'retentionPeriod':'604800','isLocked':True}},{'softDeletePolicy':{'retentionDurationSeconds':'0'}},{'lifecycle':{'rule':[{'action':{'type':'Delete'}}]}},{'website':{'mainPageSuffix':'index.html'}},{'autoclass':{'enabled':True}}):
            v=g.bucket_spec();v.update(patch)
            with self.assertRaises(g.Refused):g.validate_bucket(v)
    def test_scoped_iam_separates_runtime_recovery_delete(self):
        commands=g.iam_commands('user:operator@fictional.invalid','user:recover@fictional.invalid','user:delete@fictional.invalid')
        self.assertEqual(len(commands),8)
        definitions={c[4]:c for c in commands if c[1:4]==['iam','roles','create']}
        self.assertIn('--permissions=storage.objects.delete',definitions['wheretoBackupDeletion'])
        self.assertIn('--permissions=storage.buckets.get,storage.objects.get,storage.objects.list',definitions['wheretoBackupRecovery'])
        text=json.dumps(commands)
        for term in ('roles/storage.admin','setIamPolicy','signBlob','keys create','whereto-frontend@','whereto-recovery@'):self.assertNotIn(term,text)
        self.assertFalse(any(c[1:3]==['projects','add-iam-policy-binding'] for c in commands))
    def test_missing_or_public_principals_refuse(self):
        for principal in (None,'allUsers','allAuthenticatedUsers','serviceAccount:'+g.WRITER):
            with self.assertRaises(g.Refused):g.iam_commands('user:operator@fictional.invalid',principal,'user:delete@fictional.invalid')
        with self.assertRaises(g.Refused):g.iam_commands('user:operator@fictional.invalid','user:same@fictional.invalid','user:same@fictional.invalid')
        with self.assertRaises(g.Refused):g.iam_commands('user:same@fictional.invalid','user:same@fictional.invalid','user:delete@fictional.invalid')
    def test_capacity_includes_deleted_objects(self):
        g.capacity(192*1024**2,512*1024**2,64*1024**2,7,3)
        for args in ((g.LIVE_LIMIT,g.PHYSICAL_LIMIT,1,0,0),(0,g.PHYSICAL_LIMIT,1,0,0),(0,0,g.MAX_GENERATION+1,0,0),(0,0,1,8,0),(0,0,1,0,4),(10,1,1,0,0)):
            with self.assertRaises(g.Refused):g.capacity(*args)
    def test_identity_precondition_and_download_generation(self):
        a=g.upload_command('/fictional/application.dump.cms','fictional-b1-0001');self.assertIn('--if-generation-match=0',a)
        name=g.object_name('fictional-b1-0001','application.dump.cms')
        with TemporaryDirectory() as tmp:
            b=g.download_command(name,123,Path(tmp)/'download.cms');self.assertIn('gs://'+g.BUCKET+'/'+name+'#123',b)
        for bad in ('../escape','https://other','SHORT'):
            with self.assertRaises(g.Refused):g.object_name(bad,'application.dump.cms')
        with self.assertRaises(g.Refused):g.object_name('fictional-b1-0001','recovery.pem')
    def test_cost_bounds_and_no_provider_hard_cap_claim(self):
        self.assertLess(float(g.monthly_cost()),.15)
        self.assertEqual(g.TRANSFER_ENV['CLOUDSDK_STORAGE_MAX_RETRIES'],'0')
    def test_cipher_shape_rejects_plaintext_and_wrong_receipt(self):
        for value in (b'PGDMP'+b'x'*50,b'-----BEGIN PRIVATE KEY-----'+b'x'*50,b'{"data":"FICTIONAL"}'):
            with self.assertRaises(g.Refused):g.cms_shape(value)
    def test_real_crypto_fake_GCS_download(self):
        with TemporaryDirectory(prefix='whereto-gcs-fictional-') as tmp:
            p=Path(tmp);key=p/'test-only-key.pem';cert=p/'test-only-cert.pem';cipher=p/'application.dump.cms';password=b'FICTIONAL-ONLY\n'
            ssl='/opt/homebrew/bin/openssl'
            r=subprocess.run([ssl,'req','-new','-x509','-newkey','rsa:3072','-cipher','aes-256-cbc','-days','1','-subj','/CN=FICTIONAL-B1-GCS','-passout','stdin','-keyout',str(key),'-out',str(cert)],input=password,capture_output=True)
            self.assertEqual(r.returncode,0);key.chmod(0o600)
            enc=subprocess.run([ssl,'cms','-encrypt','-binary','-stream','-outform','DER','-aes-256-gcm','-recip',str(cert),'-keyopt','rsa_padding_mode:oaep','-keyopt','rsa_oaep_md:sha256','-keyopt','rsa_mgf1_md:sha256'],input=b'FICTIONAL GCS BACKUP',capture_output=True)
            self.assertEqual(enc.returncode,0);cipher.write_bytes(enc.stdout);cipher.chmod(0o600)
            h=sha256(enc.stdout).hexdigest();g.artifact(cipher,h)
            # In-memory object store: create-only name and exact recorded version.
            name=g.object_name('fictional-b1-0001',cipher.name);store={(name,123):cipher.read_bytes()}
            downloaded=g.verify_download(store[(name,123)],h);self.assertEqual(downloaded,enc.stdout)
            second=p/'downloaded.cms';second.write_bytes(downloaded)
            dec=subprocess.run([ssl,'cms','-decrypt','-binary','-inform','DER','-in',str(second),'-recip',str(cert),'-inkey',str(key),'-passin','stdin'],input=password,capture_output=True)
            self.assertEqual(dec.returncode,0);self.assertEqual(dec.stdout,b'FICTIONAL GCS BACKUP')
            with self.assertRaises(g.Refused):g.verify_download(downloaded+b'x',h)
            with self.assertRaises(g.Refused):g.artifact(cipher,'0'*64)

    def test_bucket_IAM_cannot_grant_runtime_or_public_access(self):
        op='user:operator@fictional.invalid';r='user:recovery@fictional.invalid';d='user:deletion@fictional.invalid'
        bindings=[{'role':'roles/storage.objectCreator','members':['serviceAccount:'+g.WRITER]},
         {'role':'projects/'+g.PROJECT+'/roles/wheretoBackupRecovery','members':[r]},
         {'role':'projects/'+g.PROJECT+'/roles/wheretoBackupDeletion','members':[d]}]
        g.validate_bucket_bindings(bindings,op,r,d)
        for member in ('allUsers','allAuthenticatedUsers','serviceAccount:whereto-frontend@'+g.PROJECT+'.iam.gserviceaccount.com'):
            bad=deepcopy(bindings);bad[0]['members'].append(member)
            with self.assertRaises(g.Refused):g.validate_bucket_bindings(bad,op,r,d)
        with self.assertRaises(g.Refused):g.validate_bucket_bindings(bindings+[{'role':'roles/storage.admin','members':[op]}],op,r,d)

    def test_metadata_mismatch_and_missing_version_refuse(self):
        name=g.object_name('fictional-b1-0001','application.dump.cms');m=dict(bucket=g.BUCKET,name=name,generation='123',size='10')
        self.assertEqual(g.object_receipt(m,name,10)['generation'],'123')
        for key,value in [('bucket','other-bucket'),('name','other'),('generation','0'),('size','11')]:
            bad=deepcopy(m);bad[key]=value
            with self.assertRaises(g.Refused):g.object_receipt(bad,name,10)
