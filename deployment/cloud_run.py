"""Offline Cloud Run command compiler for the existing six roles.

No subprocess, network, credentials, apply, grant or migration executor. Output
commands are review material, never authorization. Runtime gates remain intact.
"""
from pathlib import Path
from urllib.parse import urlsplit
from decimal import Decimal
import argparse,hashlib,ipaddress,json,re
ROOT=Path(__file__).resolve().parents[1]
PROJECT='where-to-512422';REGION='us-east4';PROJECT_NUMBER='895186533714';ROLES=('frontend','backend','factory','counter','dispatcher','recovery')
PIN=ROOT/'deployment/cloud-run/source-pins-v1.json'
CANDIDATE='deployment/candidates/trixie-zlib-v2/images.json'
CALLERS={'frontend':('iap',),'backend':('frontend',),'factory':('backend','dispatcher'),'counter':('factory',),'dispatcher':('factory',),'recovery':('factory',)}
SQL={'frontend':{},'backend':{'witness':'nonce'},'factory':{'database':'runtime','issuer':'issuer','witness':'witness-factory'},'counter':{'database':'counter','witness':'witness-counter'},'dispatcher':{'database':'delivery','witness':'witness-delivery'},'recovery':{'witness':'recovery'}}
MEMORY={'frontend':'512Mi','backend':'1Gi','factory':'1Gi','counter':'512Mi','dispatcher':'1Gi','recovery':'512Mi'}
MOUNTS={'frontend':{'config':'/run/secrets/whereto-frontend.json','enrollment':'/run/secrets/whereto-frontend-enrollment.json'},**{r:{'config':'/run/secrets/whereto-private.json','witness-ca':'/run/secrets/witness-ca.pem'} for r in ROLES if r!='frontend'}}
for _r in ('factory','counter','dispatcher'):MOUNTS[_r]['operational-ca']='/run/secrets/operational-ca.pem'
for _r in ('factory','dispatcher'):MOUNTS[_r]['redis-ca']='/run/secrets/redis-ca.pem'
MOUNTS['dispatcher']['openai']='/run/secrets/whereto-openai-key.json'
REVIEW_GATES=('image-security','model-qualification','real-token-price-policy','provider-transport','google-content-use','financial-grant','storage-capacity','independent-recovery-owner','hosted-worker-replacement','iam-iap-enrollment','infrastructure-cost')
class Refused(ValueError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise Refused('duplicate JSON key')
            result[k]=v
        return result
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs)
def pins():
    p=read(PIN)
    for n,h in p['filesSHA256'].items():
        f=ROOT/n
        if f.is_symlink() or sha(f.read_bytes())!=h:raise Refused('source cohort changed: '+n)
    images=read(ROOT/CANDIDATE)
    cohort=read(ROOT/'deployment/candidates/trixie-zlib-v2/cohort.json')
    if sha((ROOT/'deployment/candidates/trixie-zlib-v2/cohort.json').read_bytes())!=images['cohort']:raise Refused('image cohort identity')
    for n,h in cohort['inputs'].items():
        if sha((ROOT/n).read_bytes())!=h:raise Refused('candidate source input changed: '+n)
    return images
def name(value):
    if type(value)is not str or not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]',value):raise Refused('resource name')
    return value
def digest(value):
    if type(value)is not str or not re.fullmatch('[0-9a-f]{64}',value):raise Refused('SHA256 required')
    return value
def url(value):
    u=urlsplit(value)
    if u.scheme!='https' or not u.hostname or not u.hostname.endswith('.run.app') or u.netloc!=u.hostname or u.path or u.query or u.fragment:raise Refused('observed canonical run.app URL required')
    return value
def hosted_host(value):
    if type(value)is not str or not re.fullmatch('[A-Za-z0-9.-]+',value) or value.lower() in ('localhost','metadata.google.internal') or value.endswith(('.localhost','.local')):raise Refused('managed hosted address required')
    try:
        address=ipaddress.ip_address(value)
    except ValueError:
        if '.' not in value:raise Refused('fully qualified managed host required')
    else:
        if address.is_loopback or address.is_unspecified or address.is_link_local:raise Refused('no local-machine or metadata address')
    return value

def no_secrets(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.lower() in ('password','token','key','signingkey','privatekey','dsn','credential','secretvalue','api_key') or k.startswith('NEXT_PUBLIC_'):raise Refused('secret value or public credential field forbidden')
            no_secrets(v)
    elif isinstance(value,list):
        for v in value:no_secrets(v)
    elif isinstance(value,str) and (re.search(r'(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',value) or value.startswith(('postgres://','postgresql://','redis://','rediss://'))):raise Refused('credential material forbidden')
def sa(role):return f'whereto-{role}@{PROJECT}.iam.gserviceaccount.com'
def service(role):return 'whereto-'+role

def validate(c):
    no_secrets(c)
    if set(c)!=set('version project region projectNumber repository subnetCidr testers workloads storage epoch approvalEvidence recoveryOperator'.split()) or c['version']!='53-private-real-demo-v1' or c['project']!=PROJECT or c['region']!=REGION:raise Refused('fixed deployment target/schema')
    name(c['repository'])
    if c['projectNumber'] is not None and str(c['projectNumber'])!=PROJECT_NUMBER:raise Refused('observed project number mismatch')
    if c['subnetCidr'] is not None:
        network=ipaddress.ip_network(c['subnetCidr'],strict=True)
        if network.version!=4 or not network.is_private or network.prefixlen>26:raise Refused('reviewed nonoverlapping private /26 or larger required')
    if set(c['workloads'])!=set(ROLES):raise Refused('exact six roles')
    for role,w in c['workloads'].items():
        if set(w)!=set('url subject registryManifest secretVersions'.split()):raise Refused('workload metadata schema')
        if w['url']is not None:url(w['url'])
        if w['subject']is not None and not re.fullmatch('[0-9]{10,30}',str(w['subject'])):raise Refused('immutable workload subject')
        if w['registryManifest']is not None:digest(w['registryManifest'])
        if set(w['secretVersions'])!=set(MOUNTS[role]):raise Refused('role-specific secret mounts')
        known=[v for v in w['secretVersions'].values() if v is not None]
        if len(known)!=len(set(known)):raise Refused('each runtime file needs its independently enrolled secret version')
        for ver in w['secretVersions'].values():
            if ver is not None and (type(ver)is not int or ver<1):raise Refused('pin numeric secret versions, never latest')
    subjects=[w['subject'] for w in c['workloads'].values() if w['subject']is not None]
    if len(set(subjects))!=len(subjects):raise Refused('distinct workload subjects required')
    for t in c['testers']:
        if set(t)!={'email','subject'} or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',t['email']) or not isinstance(t['subject'],str) or not t['subject']:raise Refused('named tester email and verified IAP subject required')
    if len(c['testers'])>5 or len({t['subject'] for t in c['testers']})!=len(c['testers']):raise Refused('bounded distinct tester list')
    operator=c['recoveryOperator']
    if set(operator)!={'email','subject'}:raise Refused('independent recovery operator')
    if operator['email']is not None and (not re.fullmatch(r'[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com',operator['email']) or operator['email'] in {sa(r) for r in ROLES}):raise Refused('separate observed recovery workload identity')
    if operator['subject']is not None and not re.fullmatch('[0-9]{10,30}',str(operator['subject'])):raise Refused('recovery immutable subject')
    if c['epoch']is not None:digest(c['epoch'])
    if set(c['approvalEvidence'])!=set(REVIEW_GATES):raise Refused('review evidence categories')
    for evidence in c['approvalEvidence'].values():
        if evidence is not None:digest(evidence)
    return c

def storage_findings(s):
    """Nonsecret enrollment constraints; not a live connection/ACL proof."""
    if set(s)!=set('operational witness redis sqlLogins'.split()):raise Refused('storage metadata schema')
    findings=[]
    for target in ('operational','witness'):
        v=s[target]
        if set(v)!=set('host port database contract caSHA256 connectionBudget administrator backupOwner'.split()):raise Refused('database schema')
        if any(v[k]is None for k in v):findings.append(target+' connection/capacity/backup enrollment missing');continue
        hosted_host(v['host'])
        if 'pooler' in v['host'].lower() or v['port']!=5432 or not re.fullmatch('[a-z][a-z0-9_]{0,62}',v['database']):raise Refused('direct session-affine PostgreSQL only')
        digest(v['contract']);digest(v['caSHA256'])
        if type(v['connectionBudget'])is not int or v['connectionBudget']<(18 if target=='operational' else 22):raise Refused('pool/overlap/operator capacity budget')
    op=s['operational'];wi=s['witness']
    if all(op[k]is not None and wi[k]is not None for k in ('host','database','administrator','backupOwner')):
        if (op['host'],op['database'])==(wi['host'],wi['database']) or op['administrator']==wi['administrator'] or op['backupOwner']==wi['backupOwner']:raise Refused('independent witness administration/restore authority required')
    expected={r:SQL[r] for r in ROLES if SQL[r]}
    if set(s['sqlLogins'])!=set(expected):raise Refused('SQL role allocation')
    for r,roles in expected.items():
        if set(s['sqlLogins'][r])!=set(roles):raise Refused('SQL purpose allocation')
        for target,login in s['sqlLogins'][r].items():
            if login is None:findings.append(r+'/'+target+' restricted login missing')
            elif not re.fullmatch('[a-z][a-z0-9_]{0,62}',login) or login in ('postgres','admin','owner','supabase_admin') or login.startswith('pg_') or login.endswith(('_owner','_admin')) or 'bootstrap' in login:raise Refused('runtime cannot use administrative SQL login')
    for domain in ('operational','witness'):
        logins=[v for r,t in s['sqlLogins'].items() for k,v in t.items() if (k=='witness')==(domain=='witness') and v is not None]
        if len(logins)!=len(set(logins)):raise Refused('distinct SQL purpose identities required')
    redis=s['redis']
    if set(redis)!=set('host port caSHA256 publisher reader acl lua noeviction maximumBytes quoteMonthlyUSD'.split()):raise Refused('Redis metadata schema')
    if any(redis[k]is None for k in redis):findings.append('Redis TLS/ACL/noeviction/regional quote enrollment missing')
    else:
        hosted_host(redis['host'])
        if type(redis['port'])is not int or not 1<=redis['port']<=65535 or redis['publisher']==redis['reader'] or any(u=='default' or not re.fullmatch('[a-z][a-z0-9_-]*',u) for u in (redis['publisher'],redis['reader'])):raise Refused('named distinct Redis ACL identities')
        if any(redis[k]is not True for k in ('acl','lua','noeviction')) or type(redis['maximumBytes'])is not int or redis['maximumBytes']!=128*1024*1024:raise Refused('existing bounded encrypted evidence contract')
        digest(redis['caSHA256'])
        if Decimal(str(redis['quoteMonthlyUSD']))<=0:raise Refused('verified paid regional Redis quote required')
    return findings

def publication_receipt(role,raw,registry_digest,config_raw):
    """Validate downloaded OCI manifest bytes, not a tag or guessed local ID."""
    images=pins()['candidateForReview'];digest(registry_digest)
    if role not in images or sha(raw)!=registry_digest:raise Refused('registry manifest content identity')
    v=json.loads(raw)
    if v.get('schemaVersion')!=2 or v.get('mediaType')not in ('application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json') or v.get('config',{}).get('digest')!=images[role]:raise Refused('registry content is not the reviewed local image config; indexes require explicit amd64 selection')
    config=json.loads(config_raw)
    if 'sha256:'+sha(config_raw)!=images[role] or config.get('architecture')!='amd64' or config.get('os')!='linux':raise Refused('exact linux amd64 config required')
    return {'role':role,'registryManifest':registry_digest,'localConfigDigest':images[role],'verified':True}

def command(*args):return ['gcloud',*args,'--project='+PROJECT]
def compile_plan(c):
    images=pins();validate(c);cohort=read(ROOT/'deployment/candidates/trixie-zlib-v2/cohort.json');fixture_modules=[n for n in cohort['outputs'] if n.endswith(('/mock_data.py','/journey_fixtures.py','/simulation.py'))];missing=storage_findings(c['storage']);number=c['projectNumber'];repo=c['repository']
    if number is None:missing.append('observed project number/IAP agent missing')
    if c['subnetCidr']is None:missing.append('account-reviewed nonoverlapping VPC subnet missing')
    if any(v is None for v in c['recoveryOperator'].values()):missing.append('independent recovery workload identity missing')
    if not c['testers']:missing.append('verified named tester allowlist missing')
    if c['epoch']is None:missing.append('independent current restore epoch missing')
    for gate,evidence in c['approvalEvidence'].items():
        if evidence is None:missing.append(gate+' disposition missing')
    # A handwritten approval hash/configuration is NOT security or grant authority.
    # This reviewed image cohort itself declares no real transport; no input flag
    # or environment variable may turn it into the owner's genuine demo.
    if images['realProviderTransport']is not True:missing.append('pinned images are synthetic-only; real counter/SQL/dispatcher and source cohort enrollment required')
    infrastructure=[command('services','enable','run.googleapis.com','artifactregistry.googleapis.com','iam.googleapis.com','iap.googleapis.com','secretmanager.googleapis.com','compute.googleapis.com'),command('artifacts','repositories','create',repo,'--repository-format=docker','--location='+REGION,'--immutable-tags')]
    infrastructure += [command('beta','services','identity','create','--service='+api) for api in ('run.googleapis.com','iap.googleapis.com')]
    for role in ROLES:infrastructure.append(command('iam','service-accounts','create','whereto-'+role,'--display-name=WhereTo '+role))
    if number:infrastructure.append(command('artifacts','repositories','add-iam-policy-binding',repo,'--location='+REGION,'--member=serviceAccount:service-'+str(number)+'@serverless-robot-prod.iam.gserviceaccount.com','--role=roles/artifactregistry.reader'))
    observations=[command('projects','describe',PROJECT,'--format=json'),command('billing','projects','describe',PROJECT,'--format=json'),command('services','list','--enabled','--format=json'),command('run','services','list','--region='+REGION,'--format=json')]
    observations += [command('iam','service-accounts','describe',sa(r),'--format=json') for r in ROLES]
    network=[]
    if c['subnetCidr']:
        network=[command('compute','networks','create','whereto-staging','--subnet-mode=custom'),command('compute','networks','subnets','create','whereto-staging','--network=whereto-staging','--region='+REGION,'--range='+c['subnetCidr'],'--enable-private-ip-google-access'),command('compute','addresses','create','whereto-staging-egress','--region='+REGION),command('compute','routers','create','whereto-staging','--network=whereto-staging','--region='+REGION),command('compute','routers','nats','create','whereto-staging','--router=whereto-staging','--region='+REGION,'--nat-all-subnet-ip-ranges','--nat-external-ip-pool=whereto-staging-egress')]
    roles={};iam=[];secret_commands=[];publications=[]
    for role in ROLES:
        w=c['workloads'][role];mounts={};grants=[]
        sid='whereto-'+role+'-runtime'
        secret_commands.append(command('secrets','create',sid,'--replication-policy=user-managed','--locations='+REGION))
        grants.append(command('secrets','add-iam-policy-binding',sid,'--member=serviceAccount:'+sa(role),'--role=roles/secretmanager.secretAccessor'))
        for kind,path in MOUNTS[role].items():
            mounts[path]={'secretId':sid,'version':w['secretVersions'][kind]}
        iam.extend(grants)
        for caller in CALLERS[role]:
            principal=('service-'+str(number)+'@gcp-sa-iap.iam.gserviceaccount.com') if caller=='iap' and number else sa(caller) if caller!='iap' else None
            if principal:iam.append(command('run','services','add-iam-policy-binding',service(role),'--region='+REGION,'--member=serviceAccount:'+principal,'--role=roles/run.invoker'))
        if role=='recovery' and c['recoveryOperator']['email']:iam.append(command('run','services','add-iam-policy-binding',service(role),'--region='+REGION,'--member=serviceAccount:'+c['recoveryOperator']['email'],'--role=roles/run.invoker'))
        image=f'{REGION}-docker.pkg.dev/{PROJECT}/{repo}/whereto-{role}'
        publications.append({'role':role,'localConfigDigest':images['candidateForReview'][role],'commands':[['docker','tag',images['candidateForReview'][role],image+':candidate-'+images['cohort'][:12]],['docker','push',image+':candidate-'+images['cohort'][:12]]],'receiptRequired':'Download exact registry manifest bytes; publication_receipt verifies config digest against local image. Never use a local config digest as a registry manifest digest.'})
        if any(w[k]is None for k in ('url','subject','registryManifest')) or any(v is None for v in w['secretVersions'].values()):missing.append(role+' observed URL/immutable SA subject/registry receipt/secret versions missing')
        args=None
        if w['registryManifest'] and all(v is not None for v in w['secretVersions'].values()):
            args=command('run','deploy',service(role),'--region='+REGION,'--image='+image+'@sha256:'+w['registryManifest'],'--service-account='+sa(role),'--execution-environment=gen2','--cpu=1','--memory='+MEMORY[role],'--concurrency='+('8' if role=='factory' else '1'),'--min=0','--max=1','--min-instances=0','--max-instances=1','--timeout=120s','--cpu-throttling','--no-allow-unauthenticated','--invoker-iam-check','--ingress='+('all' if role=='frontend' else 'internal'),'--network=whereto-staging','--subnet=whereto-staging','--vpc-egress=all-traffic','--port=8080','--no-traffic','--set-secrets='+','.join(path+'='+v['secretId']+':'+str(v['version']) for path,v in mounts.items()),'--startup-probe=tcpSocket.port=8080,periodSeconds=10,failureThreshold=24')
            if role=='frontend':args.insert(-1,'--iap')
        roles[role]={'proposedService':service(role),'proposedServiceAccount':sa(role),'observedSubject':w['subject'],'audience':w['url'],'imageByRegistryDigest':None if w['registryManifest']is None else image+'@sha256:'+w['registryManifest'],'mounts':mounts,'sqlPurposes':SQL[role],'concurrency':8 if role=='factory' else 1,'sqlPoolMaximum':2,'directVPC':'all-traffic/private-google-access/NAT-static-IP','commandForReviewOnly':args,'startupProbe':'TCP liveness only; runtime must verify identities, SQL/Redis and epoch before listening'}
    testers=[command('iap','web','add-iam-policy-binding','--resource-type=cloud-run','--service='+service('frontend'),'--region='+REGION,'--member=user:'+t['email'],'--role=roles/iap.httpsResourceAccessor') for t in c['testers']]
    return {'identity':'53-offline-cloud-run-plan-v1','provisioningAuthorized':False,'releaseEligible':False,'realDemoSupportedByCurrentImages':False,'imageContentReview':{'privateCredentialExclusionPreviouslyVerified':True,'fixtureRelatedModulesInCurrentCohort':fixture_modules,'realProfileRepackagingRequired':True,'securityInventory':'docs/task52-candidate-promotion-security.json','securityAccepted':False},'sourceBuild':images['cohort'],'iapAudience':None if number is None else f'/projects/{number}/locations/{REGION}/services/{service("frontend")}','blockers':missing,'accountObservationCommandsForSeparateAuthorization':observations,'bootstrapCommandsForReviewOnly':infrastructure,'networkCommandsForReviewOnly':network,'secretContainerCommandsForReviewOnly':secret_commands,'iamCommandsForReviewOnly':iam,'publisherCredentialHelperSetupForSeparateAuthorization':command('auth','configure-docker',REGION+'-docker.pkg.dev'),'publicationForReviewOnly':publications,'roles':roles,'providerIAMCommandsForSeparateApproval':[command('projects','add-iam-policy-binding',PROJECT,'--member=serviceAccount:'+sa('dispatcher'),'--role=roles/serviceusage.serviceUsageConsumer')],'providerBindings':{'enabled':False,'openai':{'endpoint':'https://api.openai.com/v1/responses','applicationCredentialProject':None,'modelQualifiedRevision':None,'secretMount':MOUNTS['dispatcher']['openai'],'evaluationKeyMayBeReused':False,'requiredCounterAndRatePolicySHA256':None},'google':{'credential':'assigned dispatcher workload short-lived metadata OAuth; no Mac ADC or service-account key','quotaProject':PROJECT,'requiredRole':'roles/serviceusage.serviceUsageConsumer on this project only, after separate approval','endpoints':['https://places.googleapis.com/v1/places:searchText','https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix'],'requestPolicy':'existing canonical Search Pro/Matrix profiles; no Details/Enterprise/automatic retry'},'contentRecovery':'request-local venue/route data only until approved retention; no provider snapshots or automatic re-fetch'},'testerAdmissionAfterVerificationOnly':testers,'order':['observe account/billing/quotas/scanning policy, decide costs','registry and six SAs; publish approved artifacts and verify OCI receipts','VPC/PGA/static NAT; independently enroll approved SQL/Redis','create own-role secret containers; operator enrolls exact contents/versions, no secrets in plan','reserve/observe six canonical Run URLs without a dummy/public/synthetic demo; verify IAP/OAuth bootstrap with actual account','counter/recovery, factory/dispatcher, backend, frontend; no testers yet','verify current epoch/grant/source and real providers under separately approved budget, Mac off','only then allow named testers through IAP'],'rollout':{'stopNewActions':True,'factoryDrainSeconds':8,'callbackPermitSeconds':5,'invalidateOldBuildSessions':True,'preserveFinancialEpochAndHistory':True,'noDatabaseOrRedisRestore':True,'requireObservedOwnerRoutingDuringOverlap':True,'rollback':'Only separately reviewed compatible exact prior revision; no blanket previous-image or financial snapshot rollback.'}}

def revision_command(role,revision):
    if role not in ROLES or type(revision)is not str or not re.fullmatch(service(role)+r'-[a-z0-9-]{1,40}',revision):raise Refused('observed exact revision required; never LATEST')
    return command('run','services','update-traffic',service(role),'--region='+REGION,'--to-revisions='+revision+'=100')


def estimate(redis_monthly=None):
    # Public rates checked 2026-11-18. No credits assumed; account terms unknown.
    d=Decimal
    if redis_monthly is not None:
        try:quote=d(str(redis_monthly))
        except Exception:raise Refused('invalid Redis quote') from None
        if not quote.is_finite() or quote<=0:raise Refused('positive finite regional quote required')
    fixed=d(2)*(d(25)+d('0.0055')*730)+d('0.005')*730+d('0.000082192')*730*18+d('0.000136986')*730*5
    run=d('0.000024')*3600*10+d('0.0000025')*3600*d('8.5')+d('0.40')*10000/1000000
    nat=d('0.0014')*730*8+d('0.045')
    variable=run+nat+d('0.03')+d('1')+d('2')
    base=fixed+variable
    return {'currency':'USD','hours':730,'publicRateFixedSubtotalExcludingRedis':str(fixed.quantize(d('.0001'))),'lowUseInfrastructureExcludingRedis':str(base.quantize(d('.0001'))),'redisMonthlyQuote':None if redis_monthly is None else str(d(str(redis_monthly))),'lowUseInfrastructureTotal':None if redis_monthly is None else str((base+d(str(redis_monthly))).quantize(d('.01'))),'oneTimeProviderSetupFee':'none established; metered setup/scan/transfer must be approved separately','notIncluded':['tax','real AI and Maps grants','paid artifact scanning if account-enabled','independent reviewer fees','quota/billing changes'],'assumptions':'2 Pro/Micro organizations incl compute credits + 2 IPv4; 18 secret versions; 5GiB registry; 8 NAT assignments; 10 aggregate vCPUh,8.5GiBh,10k requests,1GiB NAT; $1 logs/$2 other transfer; free GCP allowances not assumed','planningInfrastructureExcludingRedis':'95.7190','firstArtifactBatch':{'registryGiBCap':5,'images':6,'grossStorageUSDPerMonth':'0.50','initialSixScansIfEnabledUSD':'1.56','proposedOneTimeCeilingUSD':'5','proposedRecurringCeilingUSD':'1','approved':False},'accountQuoteVerified':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('configuration',type=Path);args=parser.parse_args()
    plan=compile_plan(read(args.configuration));print(json.dumps(plan,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
