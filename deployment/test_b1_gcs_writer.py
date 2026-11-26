"""Offline fictional G2 IAM checks; no cloud calls or genuine identities."""
from copy import deepcopy
import json,unittest
from deployment import b1_gcs as g,b1_gcs_writer as w
OP='user:operator@fictional.invalid'
class Tests(unittest.TestCase):
 def test_four_commands_without_recovery_or_deletion(self):
  c=w.commands(OP);self.assertEqual(len(c),4)
  self.assertEqual(c[0],g.iam_commands(OP,'user:recovery@fictional.invalid','user:deletion@fictional.invalid')[0])
  self.assertEqual(c[1],g.iam_commands(OP,'user:recovery@fictional.invalid','user:deletion@fictional.invalid')[1])
  text=json.dumps(c)
  for term in ('wheretoBackupRecovery','wheretoBackupDeletion','roles/storage.admin','keys create','signBlob','signJwt','whereto-frontend@','projects add-iam-policy-binding'):self.assertNotIn(term,text)
  self.assertIn('--permissions=iam.serviceAccounts.getAccessToken',c[1])
  self.assertIn('--role=roles/storage.objectCreator',c[3])
 def test_no_fabricated_or_public_operator(self):
  for op in (None,'','allUsers','allAuthenticatedUsers','user:<owner>','serviceAccount:'+g.WRITER,'user:x@a.invalid --role=roles/owner'):
   with self.assertRaises(g.Refused):w.commands(op)
  # Original full enrollment still refuses absent custodians.
  with self.assertRaises(g.Refused):g.iam_commands(OP,None,None)
 def test_exact_bucket_delta_preserves_observed_defaults(self):
  p=w.expected_bucket();self.assertEqual(len(p['bindings']),5);w.validate_bucket_policy(p)
  for index in range(len(p['bindings'])):
   bad=deepcopy(p);bad['bindings'].pop(index)
   with self.assertRaises(g.Refused):w.validate_bucket_policy(bad)
 def test_unreviewed_bucket_grants_or_conditions_refuse(self):
  p=w.expected_bucket()
  for member in ('allUsers','allAuthenticatedUsers','serviceAccount:whereto-frontend@'+g.PROJECT+'.iam.gserviceaccount.com','user:other@fictional.invalid'):
   bad=deepcopy(p);bad['bindings'][-1]['members'].append(member)
   with self.assertRaises(g.Refused):w.validate_bucket_policy(bad)
  for patch in ({'role':'roles/storage.admin'},{'condition':{'expression':'true'}}):
   bad=deepcopy(p);bad['bindings'][-1].update(patch)
   with self.assertRaises(g.Refused):w.validate_bucket_policy(bad)
 def test_operator_only_on_writer_account(self):
  p={'bindings':[{'role':w.ROLE,'members':[OP]}]};w.validate_operator_policy(p,OP)
  for role,member in [('roles/iam.serviceAccountTokenCreator',OP),(w.ROLE,'user:other@fictional.invalid'),('roles/owner',OP)]:
   with self.assertRaises(g.Refused):w.validate_operator_policy({'bindings':[{'role':role,'members':[member]}]},OP)
 def test_minter_permission_cannot_sign_or_delegate(self):
  role={'name':w.ROLE,'includedPermissions':['iam.serviceAccounts.getAccessToken'],'stage':'GA'};w.validate_role(role)
  for extra in ('iam.serviceAccounts.signBlob','iam.serviceAccounts.signJwt','iam.serviceAccounts.implicitDelegation','iam.serviceAccounts.getOpenIdToken'):
   bad=deepcopy(role);bad['includedPermissions'].append(extra)
   with self.assertRaises(g.Refused):w.validate_role(bad)
  for patch in ({'stage':'DISABLED'},{'deleted':True},{'name':'projects/other/roles/wheretoBackupTokenMinter'}):
   with self.assertRaises(g.Refused):w.validate_role({**role,**patch})
 def test_writer_has_no_project_roles(self):
  w.validate_no_project_grants({'bindings':[]})
  for role in ('roles/owner','roles/editor','roles/storage.objectViewer'):
   with self.assertRaises(g.Refused):w.validate_no_project_grants({'bindings':[{'role':role,'members':['serviceAccount:'+g.WRITER]}]})
 def test_source_and_completed_G1_refusal(self):
  from unittest.mock import patch
  w.source_pins()
  with patch.dict(w.PINS,{'deployment/b1_gcs.py':'0'*64}):
   with self.assertRaises(g.Refused):w.commands(OP)
