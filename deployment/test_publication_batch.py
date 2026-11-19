import unittest
from deployment.publication_batch import render
class Tests(unittest.TestCase):
 def test_six_pushes_only_after_one_signature_snapshot(self):
  text=render('/tmp/FICTIONAL-owner-not-enrolled')
  self.assertEqual(text.count('colima-whereto-task52 push '),6)
  self.assertEqual(text.count('publication-images'),1)
  self.assertNotIn('gcloud ',text)
  self.assertNotIn('eval ',text)
 def test_no_repository_or_endpoint_override(self):
  text=render('/tmp/FICTIONAL-owner-not-enrolled')
  self.assertEqual(text.count('us-east4-docker.pkg.dev/where-to-512422/whereto-private/'),6)
  self.assertIn('5*1024**3',text)
 def test_missing_owner_signature_cannot_compile_deployment(self):
  from deployment.publication_batch import enrolled_plan
  from deployment.cloud_run_real import original
  with self.assertRaises(ValueError):enrolled_plan(original.read('deployment/cloud-run/staging.example.json'),'/tmp/NO-GENUINE-OWNER-TRUST')
 def test_owner_bound_plan_reuses_compiler_without_activating_any_resource(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import json
  from deployment.publication_batch import enrolled_plan
  from deployment.cloud_run_real import original,pins
  m=pins();fixture=dict(images=m['candidateForReview'],configDigests=m['configDigests'],securityDecisionSHA256='a'*64)
  # Only the subprocess port is fictional; no real owner proof is represented.
  with patch('deployment.publication_batch.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(fixture))):
   p=enrolled_plan(original.read('deployment/cloud-run/staging.example.json'),'/tmp/FICTIONAL')
  self.assertFalse(p['releaseEligible']);self.assertFalse(p['provisioningAuthorized'])
  self.assertTrue(p['imageContentReview']['frontendTrustEnrolled'])
  self.assertTrue(all(v['commandForReviewOnly']is None for v in p['roles'].values()))

 def test_documented_urls_are_predictions_only_not_resource_observations(self):
  from deployment.publication_batch import proposed_service_urls
  p=proposed_service_urls();self.assertFalse(p['observed']);self.assertEqual(len(p['urls']),6)
  self.assertEqual(p['urls']['frontend'],'https://whereto-frontend-895186533714.us-east4.run.app')
 def test_rendered_shell_and_embedded_preflight_are_syntax_valid_without_execution(self):
  import subprocess,shlex
  text=render('/tmp/FICTIONAL-no-publication')
  result=subprocess.run(['sh','-n'],input=text,text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
  for line in text.splitlines():
   if line.startswith('python3 -c '):compile(shlex.split(line)[2],'<publication-size-preflight>','exec')
