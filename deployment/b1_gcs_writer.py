"""G2 writer-only v1: offline command/policy checks, no apply or secret loader.

The original all-three-principal renderer and G1 evidence remain unchanged.
"""
from pathlib import Path
from hashlib import sha256
import json,re
from deployment import b1_gcs as g
ROOT=Path(__file__).resolve().parents[1]
VERSION='53-B1-G2-writer-only-v1'
PINS={
 'deployment/b1_gcs.py':'30d23a182a9841cb5bbda9392ff3ae2569f7e6a7875f9c69e3d6ab96216aa8f4',
 'deployment/cloud-run/b1-gcs-G1-created-verification-stopped-v2.json':'529a7b0a786c679b54b6d3a806f96b23bdbf208005602bfc3fd8085cb4087cae',
 'deployment/cloud-run/b1-gcs-G1-verification-complete-v1.json':'18acfb60c00a7bd693ee2abd7f547974214888ada37f6349340f4c1785666cf9'}
ROLE='projects/'+g.PROJECT+'/roles/wheretoBackupTokenMinter'
def source_pins():
 for name,h in PINS.items():
  p=ROOT/name
  if p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h:raise g.Refused('writer_source_identity')
 if json.loads((ROOT/'deployment/cloud-run/b1-gcs-G1-verification-complete-v1.json').read_bytes()).get('G1FullyVerified') is not True:raise g.Refused('G1_not_complete')
def principal(operator):
 if type(operator)is not str or not re.fullmatch(r'user:[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+',operator):raise g.Refused('named_writer_operator_required')
def commands(operator):
 source_pins();principal(operator)
 return [
  ['gcloud','iam','service-accounts','create','whereto-backup-writer','--project='+g.PROJECT,'--display-name=WhereTo encrypted backup writer','--quiet'],
  ['gcloud','iam','roles','create','wheretoBackupTokenMinter','--project='+g.PROJECT,'--title=WhereTo backup access-token minting only','--permissions=iam.serviceAccounts.getAccessToken','--stage=GA','--quiet'],
  ['gcloud','iam','service-accounts','add-iam-policy-binding',g.WRITER,'--project='+g.PROJECT,'--member='+operator,'--role='+ROLE,'--condition=None','--quiet'],
  ['gcloud','storage','buckets','add-iam-policy-binding','gs://'+g.BUCKET,'--member=serviceAccount:'+g.WRITER,'--role=roles/storage.objectCreator','--condition=None','--quiet']]
def bindings(policy):
 result={}
 for binding in policy.get('bindings',[]):
  role=binding.get('role');members=binding.get('members',[])
  if type(role)is not str or not members or role in result or 'condition' in binding or len(set(members))!=len(members):raise g.Refused('writer_IAM_shape')
  result[role]=set(members)
 return result
def expected_bucket():
 source_pins()
 policy=json.loads((ROOT/'deployment/cloud-run/b1-gcs-G1-created-verification-stopped-v2.json').read_bytes())['bucketIAM']
 policy['bindings'].append({'role':'roles/storage.objectCreator','members':['serviceAccount:'+g.WRITER]})
 return policy
def validate_bucket_policy(policy):
 if bindings(policy)!=bindings(expected_bucket()):raise g.Refused('writer_bucket_IAM')
def validate_operator_policy(policy,operator):
 source_pins();principal(operator)
 if bindings(policy)!={ROLE:{operator}}:raise g.Refused('writer_operator_IAM')
def validate_role(role):
 source_pins()
 if role.get('name')!=ROLE or role.get('includedPermissions')!=['iam.serviceAccounts.getAccessToken'] or role.get('stage')!='GA' or role.get('deleted',False):raise g.Refused('writer_minter_role')
def validate_no_project_grants(policy):
 source_pins()
 if any('serviceAccount:'+g.WRITER in b.get('members',[]) for b in policy.get('bindings',[])):raise g.Refused('writer_project_grant')
