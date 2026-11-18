"""Offline executable configuration tests; no cloud account/provider requests."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import ast,json,socket,subprocess,sys,tempfile,unittest
from deployment import cloud_run as c

class CloudRunTests(unittest.TestCase):
 def setUp(self):self.config=c.read(c.ROOT/'deployment/cloud-run/staging.example.json')
 def filled(self):
  x=deepcopy(self.config);x['projectNumber']=c.PROJECT_NUMBER;x['subnetCidr']='10.92.0.0/26';x['testers']=[{'email':'tester@example.invalid','subject':'fictional-iap-subject'}];x['epoch']='e'*64;x['recoveryOperator']={'email':'recovery@independent-example.iam.gserviceaccount.com','subject':'999999999999999999999'}
  x['approvalEvidence']={k:'a'*64 for k in c.REVIEW_GATES}
  for i,(r,w) in enumerate(x['workloads'].items()):
   w.update(url=f'https://whereto-{r}-fixture.us-east4.run.app',subject=str(111111111111111111110+i),registryManifest='b'*64,secretVersions={k:i+1 for i,k in enumerate(w['secretVersions'])})
  for n,budget in (('operational',18),('witness',22)):
   x['storage'][n].update(host=n+'.example.invalid',port=5432,database='postgres',contract='c'*64,caSHA256='d'*64,connectionBudget=budget,administrator=n+'-admin@example.invalid',backupOwner=n+'-restore@example.invalid')
  for r,targets in x['storage']['sqlLogins'].items():
   for target in targets:targets[target]='wt_'+r+'_'+target
  x['storage']['redis'].update(host='redis.example.invalid',port=15443,caSHA256='d'*64,publisher='wt_publisher',reader='wt_reader',acl=True,lua=True,noeviction=True,maximumBytes=134217728,quoteMonthlyUSD='9.99')
  return x
 def test_example_compiles_without_any_network_or_commands(self):
  with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')),patch.object(subprocess,'run',side_effect=AssertionError('No command execution')):p=c.compile_plan(self.config)
  self.assertEqual(set(p['roles']),set(c.ROLES));self.assertFalse(p['releaseEligible']);self.assertFalse(p['provisioningAuthorized']);self.assertTrue(p['blockers']);self.assertTrue(all(v['commandForReviewOnly']is None for v in p['roles'].values()))
 def test_synthetic_images_block_even_handwritten_approval_hashes(self):
  p=c.compile_plan(self.filled());self.assertFalse(p['releaseEligible']);self.assertTrue(any('synthetic-only' in s for s in p['blockers']));self.assertFalse(p['providerBindings']['enabled'])
 def test_exact_workload_and_secret_iam_graph(self):
  p=c.compile_plan(self.filled());commands=p['iamCommandsForReviewOnly']
  for role in c.ROLES:
   run=[v for v in commands if 'roles/run.invoker' in ' '.join(v) and c.service(role) in v]
   self.assertEqual(len(run),len(c.CALLERS[role])+(role=='recovery'))
   self.assertEqual(set(p['roles'][role]['mounts']),set(c.MOUNTS[role].values()))
   self.assertEqual(len({v['secretId'] for v in p['roles'][role]['mounts'].values()}),1)
   self.assertEqual(len({v['version'] for v in p['roles'][role]['mounts'].values()}),len(c.MOUNTS[role]))
  allwords=' '.join(sum(commands,[]));self.assertNotIn('allUsers',allwords);self.assertNotIn('roles/editor',allwords);self.assertNotIn('roles/owner',allwords)
  self.assertEqual(p['roles']['frontend']['sqlPurposes'],{});self.assertNotIn('/run/secrets/whereto-openai-key.json',p['roles']['frontend']['mounts']);self.assertIn('/run/secrets/whereto-openai-key.json',p['roles']['dispatcher']['mounts'])
 def test_deploy_args_private_network_and_callback_capacity(self):
  p=c.compile_plan(self.filled())
  for role,w in p['roles'].items():
   argv=w['commandForReviewOnly'];self.assertIn('--no-allow-unauthenticated',argv);self.assertIn('--invoker-iam-check',argv);self.assertIn('--no-traffic',argv);self.assertIn('--vpc-egress=all-traffic',argv);self.assertIn('--execution-environment=gen2',argv);self.assertIn('--timeout=120s',argv);self.assertIn('--max=1',argv);self.assertIn('--min=0',argv)
   self.assertIn('--concurrency='+('8' if role=='factory' else '1'),argv)
   self.assertEqual('--iap' in argv,role=='frontend');self.assertIn('--ingress='+('all' if role=='frontend' else 'internal'),argv)
   self.assertFalse(any('NEXT_PUBLIC_' in a or 'WHERETO_ENV=test' in a for a in argv))
 def test_sources_and_old_cohorts_cannot_be_substituted(self):
  original=Path.read_bytes
  for suffix in ('images.json','private_service.py','cohort.json'):
   def read(path):return b'{}' if str(path).endswith(suffix) else original(path)
   with patch.object(Path,'read_bytes',read),self.assertRaises(c.Refused):c.pins()
 def test_secret_material_and_untrusted_runtime_flags_rejected(self):
  for field,value in (('password','fictional'),('NEXT_PUBLIC_API_KEY','fictional'),('providerMode','real'),('apply',True)):
   x=deepcopy(self.config);x[field]=value
   with self.assertRaises(c.Refused):c.compile_plan(x)
  x=deepcopy(self.config);x['approvalEvidence']['image-security']='sk-proj-'+('X'*30)
  with self.assertRaises(c.Refused):c.compile_plan(x)
 def test_identity_audience_version_and_project_mismatch(self):
  for field,value in (('project','other-project'),('region','us-central1'),('version','old')):
   x=deepcopy(self.config);x[field]=value
   with self.assertRaises(c.Refused):c.compile_plan(x)
  for field,value in (('url','http://localhost'),('url','https://frontend.run.app/path'),('url','https://user:pass@frontend.run.app'),('subject','caller-email'),('registryManifest','latest')):
   x=deepcopy(self.config);x['workloads']['frontend'][field]=value
   with self.assertRaises(c.Refused):c.compile_plan(x)
  x=deepcopy(self.config);x['workloads']['frontend']['secretVersions']['config']='latest'
  with self.assertRaises(c.Refused):c.compile_plan(x)
 def test_storage_tls_role_and_independent_restore_constraints(self):
  for target,field,value in (('operational','host','abc.pooler.supabase.com'),('witness','port',6543),('operational','connectionBudget',17),('witness','connectionBudget',21),('witness','administrator','operational-admin@example.invalid'),('witness','backupOwner','operational-restore@example.invalid'),('redis','noeviction',False),('redis','lua',False),('redis','acl',False),('redis','reader','wt_publisher'),('redis','publisher','default'),('redis','maximumBytes',268435456)):
   x=self.filled();x['storage'][target][field]=value
   with self.subTest(target=target,field=field),self.assertRaises(c.Refused):c.compile_plan(x)
  x=self.filled();x['storage']['sqlLogins']['factory']['issuer']='postgres'
  with self.assertRaises(c.Refused):c.compile_plan(x)
 def test_local_machine_and_role_reuse_are_not_hosted_configuration(self):
  for host in ('localhost','127.0.0.1','169.254.169.254','owner-mac.local','metadata.google.internal'):
   x=self.filled();x['storage']['operational']['host']=host
   with self.assertRaises(c.Refused):c.compile_plan(x)
  x=self.filled();x['storage']['sqlLogins']['factory']['issuer']=x['storage']['sqlLogins']['factory']['database']
  with self.assertRaises(c.Refused):c.compile_plan(x)
  x=self.filled();x['storage']['sqlLogins']['factory']['issuer']='whereto_synthetic_owner'
  with self.assertRaises(c.Refused):c.compile_plan(x)
 def test_registry_config_vs_manifest_digest_and_platform(self):
  config=json.dumps({'architecture':'amd64','os':'linux'}).encode();id='sha256:'+c.sha(config);raw=json.dumps({'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'digest':id}}).encode()
  with patch.object(c,'pins',return_value={'candidateForReview':{'frontend':id}}):
   self.assertTrue(c.publication_receipt('frontend',raw,c.sha(raw),config)['verified'])
   with self.assertRaises(c.Refused):c.publication_receipt('frontend',raw,id.removeprefix('sha256:'),config)
   with self.assertRaises(c.Refused):c.publication_receipt('frontend',raw,c.sha(raw),b'{}')
 def test_no_rollback_financial_reset_or_latest_revision(self):
  p=c.compile_plan(self.filled());self.assertFalse(p['rollout']['noDatabaseOrRedisRestore']is False);self.assertTrue(p['rollout']['preserveFinancialEpochAndHistory'])
  for r in ('LATEST','frontend','whereto-frontend-other,evil=100'):
   with self.assertRaises(c.Refused):c.revision_command('frontend',r)
  self.assertIn('--to-revisions=whereto-frontend-reviewed-0001=100',c.revision_command('frontend','whereto-frontend-reviewed-0001'))
 def test_costs_do_not_invent_quote_or_provider_permission(self):
  x=c.estimate();self.assertIsNone(x['lowUseInfrastructureTotal']);self.assertFalse(x['accountQuoteVerified']);self.assertEqual(c.estimate('10')['lowUseInfrastructureTotal'],str((__import__('decimal').Decimal(x['lowUseInfrastructureExcludingRedis'])+10).quantize(__import__('decimal').Decimal('.01'))))
 def test_invalid_quote_and_ambiguous_secret_versions_refuse(self):
  for quote in ('NaN','Infinity','-1','0','unknown'):
   with self.assertRaises(c.Refused):c.estimate(quote)
  x=self.filled();x['workloads']['frontend']['secretVersions']={'config':1,'enrollment':1}
  with self.assertRaises(c.Refused):c.compile_plan(x)
 def test_cli_is_offline_only_and_has_no_apply(self):
  p=subprocess.run([sys.executable,'-m','deployment.cloud_run','deployment/cloud-run/staging.example.json'],cwd=c.ROOT,capture_output=True,text=True,timeout=10);self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(json.loads(p.stdout)['releaseEligible'])
  p=subprocess.run([sys.executable,'-m','deployment.cloud_run','--apply'],cwd=c.ROOT,capture_output=True,text=True,timeout=10);self.assertEqual(p.returncode,2)
  tree=ast.parse((c.ROOT/'deployment/cloud_run.py').read_text());self.assertFalse(any(isinstance(n,ast.Import) and any(a.name in ('subprocess','socket','requests','http.client') for a in n.names) for n in ast.walk(tree)))
if __name__=='__main__':unittest.main()
