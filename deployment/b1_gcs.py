"""Offline GCS backup destination policy/commands. No client, credentials or apply.

Only successful B1 CMS artifacts are admissible; bucket IAM cannot inspect payload
semantics. Normal six-role startup and the source/export deadline are untouched.
"""
from decimal import Decimal,ROUND_CEILING
from hashlib import sha256
from pathlib import Path
import os,re,stat,subprocess
PROJECT='where-to-512422';REGION='us-east4';PROJECT_NUMBER='895186533714'
BUCKET='where-to-512422-b1-backups-us-east4'
WRITER='whereto-backup-writer@'+PROJECT+'.iam.gserviceaccount.com'
FILES=('before.json.cms','application.dump.cms','after.json.cms','receipt.json.cms')
MAX_GENERATION=64*1024**2;LIVE_LIMIT=300*1024**2;PHYSICAL_LIMIT=600*1024**2
# SDK590 supported per-process overrides, never gcloud config set.
TRANSFER_ENV={'CLOUDSDK_STORAGE_MAX_RETRIES':'0','CLOUDSDK_STORAGE_PROCESS_COUNT':'1','CLOUDSDK_STORAGE_THREAD_COUNT':'1','CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_ENABLED':'False','CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_THRESHOLD':'0','CLOUDSDK_STORAGE_RESUMABLE_THRESHOLD':'67108865'}
AUTH_ENVELOPED_OID=bytes.fromhex('2a864886f70d0109100117')
class Refused(ValueError):pass

def bucket_spec():
    return dict(name=BUCKET,projectNumber=PROJECT_NUMBER,location=REGION.upper(),storageClass='STANDARD',
      iamConfiguration=dict(publicAccessPrevention='enforced',uniformBucketLevelAccess=dict(enabled=True)),
      versioning=dict(enabled=False),retentionPolicy=dict(retentionPeriod='604800',isLocked=False),
      softDeletePolicy=dict(retentionDurationSeconds='604800'),autoclass=dict(enabled=False))

def validate_bucket(v):
    expected=bucket_spec()
    for key in ('name','projectNumber','location','storageClass'):
        if v.get(key)!=expected[key]:raise Refused('bucket_identity')
    iam=v.get('iamConfiguration',{})
    if iam.get('publicAccessPrevention')!='enforced' or iam.get('uniformBucketLevelAccess',{}).get('enabled') is not True:raise Refused('public_or_acl')
    if v.get('versioning',{}).get('enabled',False) is not False:raise Refused('versioning')
    if v.get('retentionPolicy',{}).get('retentionPeriod')!='604800' or v.get('retentionPolicy',{}).get('isLocked',False) is not False:raise Refused('retention')
    if v.get('softDeletePolicy',{}).get('retentionDurationSeconds')!='604800':raise Refused('soft_delete')
    if v.get('autoclass',{}).get('enabled',False) or v.get('lifecycle',{}).get('rule') or v.get('website') or v.get('cors'):raise Refused('unreviewed_features')
    if v.get('hierarchicalNamespace',{}).get('enabled',False) or v.get('encryption',{}).get('defaultKmsKeyName'):raise Refused('unreviewed_features')

def bucket_command():
    return ['gcloud','storage','buckets','create','gs://'+BUCKET,'--project='+PROJECT,'--location='+REGION,'--default-storage-class=STANDARD','--uniform-bucket-level-access','--public-access-prevention','--soft-delete-duration=7d','--retention-period=7d','--no-enable-autoclass','--quiet']

def iam_commands(operator,recovery,deleter):
    # No placeholder, anonymous, runtime-SA, key creation or project role grant.
    if any(type(x)is not str or not re.fullmatch(r'user:[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+',x) for x in (operator,recovery,deleter)):raise Refused('named_principals_required')
    if len({operator,recovery,deleter})!=3:raise Refused('writer_operator_recovery_and_deletion_must_differ')
    role='projects/'+PROJECT+'/roles/'
    read_permissions=['storage.buckets.get','storage.objects.get','storage.objects.list']
    return [
      ['gcloud','iam','service-accounts','create','whereto-backup-writer','--project='+PROJECT,'--display-name=WhereTo encrypted backup writer','--quiet'],
      ['gcloud','iam','roles','create','wheretoBackupTokenMinter','--project='+PROJECT,'--title=WhereTo backup access-token minting only','--permissions=iam.serviceAccounts.getAccessToken','--stage=GA','--quiet'],
      ['gcloud','iam','roles','create','wheretoBackupRecovery','--project='+PROJECT,'--title=WhereTo backup read-only recovery','--permissions='+','.join(read_permissions),'--stage=GA','--quiet'],
      ['gcloud','iam','roles','create','wheretoBackupDeletion','--project='+PROJECT,'--title=WhereTo exact backup object deletion','--permissions=storage.objects.delete','--stage=GA','--quiet'],
      ['gcloud','iam','service-accounts','add-iam-policy-binding',WRITER,'--project='+PROJECT,'--member='+operator,'--role='+role+'wheretoBackupTokenMinter','--condition=None','--quiet'],
      ['gcloud','storage','buckets','add-iam-policy-binding','gs://'+BUCKET,'--member=serviceAccount:'+WRITER,'--role=roles/storage.objectCreator','--condition=None','--quiet'],
      ['gcloud','storage','buckets','add-iam-policy-binding','gs://'+BUCKET,'--member='+recovery,'--role='+role+'wheretoBackupRecovery','--condition=None','--quiet'],
      ['gcloud','storage','buckets','add-iam-policy-binding','gs://'+BUCKET,'--member='+deleter,'--role='+role+'wheretoBackupDeletion','--condition=None','--quiet']]

def validate_bucket_bindings(bindings,operator,recovery,deleter):
    iam_commands(operator,recovery,deleter) # Validate named, separated principals.
    expected={'roles/storage.objectCreator':{'serviceAccount:'+WRITER},
      'projects/'+PROJECT+'/roles/wheretoBackupRecovery':{recovery},
      'projects/'+PROJECT+'/roles/wheretoBackupDeletion':{deleter}}
    seen={}
    for binding in bindings:
        if binding.get('condition') or binding.get('role') not in expected:raise Refused('unreviewed_bucket_IAM')
        role=binding['role'];members=set(binding.get('members',[]))
        if role in seen or members!=expected[role]:raise Refused('bucket_IAM_members')
        seen[role]=members
    if seen!=expected:raise Refused('missing_bucket_IAM')
    # GCS default project convenience bindings, if returned, require explicit
    # separate review; do not silently strip/accept them or relax this check.

def object_name(generation,filename):
    if type(generation)is not str or not re.fullmatch('[a-z0-9][a-z0-9-]{7,63}',generation) or filename not in FILES:raise Refused('object_scope')
    return 'b1/'+generation+'/'+filename

def cms_shape(raw):
    # ContentInfo outer SEQUENCE, definite or BER-streamed indefinite length;
    # the first child must be the AuthEnvelopedData OID, not a payload marker.
    if len(raw)<18 or raw[0]!=0x30:raise Refused('not_authenticated_CMS')
    length=raw[1];offset=2
    if length>128:
        count=length&127
        if not 1<=count<=4 or len(raw)<2+count:raise Refused('CMS_length')
        offset+=count
    if raw[offset:offset+2]!=bytes([6,len(AUTH_ENVELOPED_OID)]) or raw[offset+2:offset+2+len(AUTH_ENVELOPED_OID)]!=AUTH_ENVELOPED_OID:raise Refused('not_authenticated_CMS')

def artifact(path,expected_sha):
    p=Path(path);s=p.lstat()
    if p.name not in FILES or not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or not 0<s.st_size<=MAX_GENERATION:raise Refused('artifact_file')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        current=os.fstat(fd)
        if (current.st_dev,current.st_ino,current.st_size,current.st_mode,current.st_uid)!=(s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_uid):raise Refused('artifact_changed')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(MAX_GENERATION+1)
    finally:os.close(fd)
    if len(raw)!=s.st_size or sha256(raw).hexdigest()!=expected_sha:raise Refused('artifact_receipt')
    cms_shape(raw)
    # Structure only: never decrypt, read a private key or claim tag verification.
    r=subprocess.run(['/opt/homebrew/bin/openssl','cms','-cmsout','-inform','DER','-noout'],input=raw,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
    if r.returncode:raise Refused('CMS_structure')
    return dict(bytes=len(raw),sha256=expected_sha)

def capacity(existing_live,existing_total,new_bytes,generations_this_month,live_generations):
    if any(type(x)is not int or x<0 for x in (existing_live,existing_total,new_bytes,generations_this_month,live_generations)):raise Refused('capacity_evidence')
    if existing_total<existing_live:raise Refused('capacity_evidence')
    if not 0<new_bytes<=MAX_GENERATION or existing_live+new_bytes>LIVE_LIMIT or existing_total+new_bytes>PHYSICAL_LIMIT or generations_this_month>=8 or live_generations>=4:raise Refused('capacity_ceiling')
    # Caller requires fresh recovery-principal inventory, including soft-deleted
    # objects/restored duplicates; no provider-enforced bucket byte quota exists.

def upload_command(path,generation):
    name=object_name(generation,Path(path).name)
    return ['gcloud','storage','cp',str(path),'gs://'+BUCKET+'/'+name,'--if-generation-match=0','--content-type=application/pkcs7-mime','--project='+PROJECT,'--impersonate-service-account='+WRITER,'--quiet']

def download_command(name,generation,destination):
    parts=name.split('/')
    if len(parts)!=3 or object_name(parts[1],parts[2])!=name or not re.fullmatch('[1-9][0-9]*',str(generation)):raise Refused('download_identity')
    target=Path(destination);parent=target.parent.lstat()
    if target.exists() or target.is_symlink() or not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=os.getuid() or parent.st_mode&0o077:raise Refused('fresh_private_download_required')
    return ['gcloud','storage','cp','gs://'+BUCKET+'/'+name+'#'+str(generation),str(destination),'--no-clobber','--project='+PROJECT,'--quiet']

def object_receipt(metadata,name,size):
    if type(size)is not int or not 0<size<=MAX_GENERATION:raise Refused('object_size')
    parts=name.split('/')
    if len(parts)!=3 or object_name(parts[1],parts[2])!=name:raise Refused('object_scope')
    if metadata.get('bucket')!=BUCKET or metadata.get('name')!=name or str(metadata.get('size'))!=str(size) or not re.fullmatch('[1-9][0-9]*',str(metadata.get('generation',''))):raise Refused('object_identity')
    # GCS provides CRC32C/MD5, not a trusted native SHA256. Pin returned version
    # here, then compute downloaded SHA256 against the independent local receipt.
    return dict(bucket=BUCKET,name=name,generation=str(metadata['generation']),bytes=size)

def verify_download(raw,expected_sha):
    if len(raw)>MAX_GENERATION or sha256(raw).hexdigest()!=expected_sha:raise Refused('download_hash')
    cms_shape(raw)
    return raw

def monthly_cost(storage_mib=600,egress_gib='1',class_a=1000,class_b=1000):
    # 31-day upper illustration using published region-hour rate; no credits.
    total=Decimal(storage_mib)/1024*Decimal('0.000031507')*744+Decimal(egress_gib)*Decimal('.12')+Decimal(class_a)/1000*Decimal('.005')+Decimal(class_b)/1000*Decimal('.0004')
    return str(total.quantize(Decimal('.000001'),rounding=ROUND_CEILING))
