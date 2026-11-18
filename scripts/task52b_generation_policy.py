"""First-slot mechanical preparation. Quotes/fixtures are never live authority."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from base64 import b64decode
import json,sqlite3,os,stat,fcntl

ROOT=Path(__file__).resolve().parents[1]
PROJECT='proj_E4EfEvC5uQYN4nqFaYZoo3I4'
MODEL='gpt-6-luna'
SLOT=['openai','extension-repeated',2]
OPERATION='52b-generation-extension-repeated-r2-v1'
PAYLOAD_SHA='5c2ad0aa457ae84497f489a1ca155ce805c8f160fd5260f59e0a4a3e8a078c02'
COUNT_SHA='70939877e0df3fca79fb68cab25d5449ae2533ec31892ed91b762ddbd2c8e6d1'
ENDPOINT='https://api.openai.com/v1/responses'
CEILING=2_500_000
RATES={'input':100_000_000,'cached_input':10_000_000,'cache_write_30m':125_000_000,'cache_write_12h':250_000_000,'output':500_000_000}
class Refused(ValueError):pass

def digest(raw):return sha256(raw).hexdigest()
def stable(value):return digest(json.dumps(value,sort_keys=True,separators=(',',':')).encode())

def fresh(observed,expires,now):
    try:a=datetime.fromisoformat(observed);b=datetime.fromisoformat(expires)
    except (TypeError,ValueError):raise Refused('freshness') from None
    if any(t.tzinfo is None or t.utcoffset()!=timedelta(0) for t in (a,b,now)) or not a<=now<b or a.date()!=now.date() or b>min(a+timedelta(days=1),a.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)):
        raise Refused('stale_evidence')

def payload():
    p=ROOT/'docs/task52b-openai-diagnostic-prepared-v1/01-extension-repeated-r2.request.json';raw=p.read_bytes()
    if digest(raw)!=PAYLOAD_SHA:raise Refused('generation_payload')
    body=json.loads(raw)
    if set(body)!={'model','input','temperature','reasoning','service_tier','max_output_tokens','store','text'} or (body['model'],body['max_output_tokens'],body['service_tier'],body['reasoning'],body['store'])!=(MODEL,2000,'default',{'effort':'none'},False):raise Refused('generation_configuration')
    return raw

def quote(tokens,rates,extras,uplift_bps,*,output=2000):
    """Same retained margin/ceiling as the prepared first-slot quote; round up."""
    payload()
    if type(tokens)is not int or not 1<=tokens<=9952 or rates!=RATES or any(type(x)is not int for x in rates.values()) or type(output)is not int or output!=2000:raise Refused('count_rates_or_output')
    if type(extras)is not dict or set(extras)!={'tools','separate_reasoning','other_fees'} or any(type(x)is not int or x<0 for x in extras.values()):raise Refused('unknown_fees')
    if type(uplift_bps)is not int or not 0<=uplift_bps<=10000:raise Refused('unknown_premium')
    up=lambda x,y:(x+y-1)//y
    n=tokens+2048;i=up(n*max(rates[k] for k in ('input','cached_input','cache_write_30m')),1_000_000);o=up(output*rates['output'],1_000_000);subtotal=i+o+sum(extras.values());premium=up(subtotal*uplift_bps,10000);total=subtotal+premium
    if total>CEILING:raise Refused('ceiling_exceeded')
    return {'inputTokens':tokens,'inputBound':n,'maxOutputTokens':output,'inputNanodollars':i,'outputNanodollars':o,'extraNanodollars':sum(extras.values()),'premiumNanodollars':premium,'maximumNanodollars':total,'reservationNanodollars':CEILING,'approved':False}

def validate_packet(p,now,*,expected_build):
    fixed={'project':PROJECT,'model':MODEL,'slot':SLOT,'operation':OPERATION,'payloadSHA256':PAYLOAD_SHA,'countSHA256':COUNT_SHA,'endpoint':ENDPOINT,'method':'POST','operationMaximum':1,'retries':0,'planningAuthorized':False,'semanticReview':'deferred','independentlyCorrect':None,'reservationNanodollars':CEILING}
    if type(p)is not dict or any(type(p.get(k))is not type(v) or p.get(k)!=v for k,v in fixed.items()):raise Refused('scope_identity')
    if p.get('sourceBuildSHA256')!=expected_build:raise Refused('source_build_binding')
    for k in ('ownerOperationApproved','technicalPurposeApproved','securityReviewApproved','writerEnrollmentApproved','independentPostAppendVerifier','accountTermsAndFeesApproved','modelAliasDiagnosticApproved'):
        if p.get(k)is not True:raise Refused('missing_'+k)
    for k in ('operationID','credentialIdentity','sourceBuildSHA256','countBundleSHA256','modelGETBundleSHA256','writerIdentity'):
        if type(p.get(k))is not str or len(p[k])!=64 or any(x not in '0123456789abcdef' for x in p[k]):raise Refused('bound_identity')
    for name in ('modelEvidence','countEvidence','permissionEvidence','priceEvidence','authorization'):
        if name not in p:raise Refused('missing_evidence')
        fresh(p[name]['observedAt'],p[name]['expiresAt'],now)
    if p['countEvidence'].get('inputTokens')!=5704 or p['countEvidence'].get('generationSHA256')!=PAYLOAD_SHA or p['countEvidence'].get('countSHA256')!=COUNT_SHA:raise Refused('count_binding')
    cost=quote(p['countEvidence']['inputTokens'],p['priceEvidence']['ratesNanoPerMillion'],p['extraFeesNanodollars'],p['premiumBps'])
    if p.get('quotedMaximumNanodollars')!=cost['maximumNanodollars']:raise Refused('financial_binding')
    payload();return cost

def inspect_readiness():
    """Actual owner-only records: read-only, no key value, clock override or HTTP."""
    from scripts import task52b_count_only as c
    from backend.provider_responses import HTTPResult
    now=datetime.now(timezone.utc)
    _,get_proof,permission=c.validate_preparation(c.digest(c.BUILD.read_bytes()),now)
    outcome=json.loads((ROOT/'docs/task52b-authorized-count-only-result-v1.json').read_bytes());p=outcome['evidence'];directory=c.STATE;c.e.private_directory(directory)
    pins=p['privateFilesSHA256']
    if set(pins)!={f.name for f in directory.iterdir()} or any(c.digest(c.e.private_read(directory/n))!=h for n,h in pins.items()):raise Refused('count_immutable_inventory')
    if c.digest(c.e.private_read(c.AUTHORIZATION))!=p['authorizationSHA256']:raise Refused('count_authorization')
    scope=c.e.record(directory/'scope.json');consumed=c.e.record(directory/'consumed.json');wire=c.e.record(directory/'wire-consumed.json');intent=c.e.record(directory/'intent.json');raw=c.e.record(directory/'response-1.json');validated=c.e.record(directory/'validated.json');result=c.e.record(directory/'result.json')
    if (scope['credentialIdentity']!=get_proof['credentialIdentity'] or scope['project']!=PROJECT or scope['model']!=MODEL or consumed['scopeSHA256']!=pins['scope.json'] or wire['intentSHA256']!=pins['intent.json'] or intent['bodySHA256']!=COUNT_SHA or scope['buildSHA256']!=p['buildSHA256'] or result['result']!='completed' or result['count']!=5704):raise Refused('count_authority')
    body=b64decode(raw['bodyBase64'],validate=True)
    value=c.q.validate_response(c.request(),HTTPResult(raw['status'],body,raw['complete'],raw['contentType']))
    if value!=validated['value'] or value['inputTokens']!=5704 or digest(body)!=p['responseSHA256'] or raw.get('credentialEchoRefused')is not False:raise Refused('count_response')
    fresh(raw['at'],get_proof['expiresAt'],now)
    payload()
    return {'model':MODEL,'project':PROJECT,'inputTokens':5704,'generationSHA256':PAYLOAD_SHA,'countSHA256':COUNT_SHA,'credentialIdentity':get_proof['credentialIdentity'],'modelGETBundleSHA256':get_proof['bundleSHA256'],'countBundleSHA256':stable(pins),'permissionSHA256':permission,'observedAt':raw['at'],'expiresAt':get_proof['expiresAt'],'realKeyValueRead':False,'financialAuthorization':False}

def journal_snapshot(directory):
    """New fold over the unchanged Q4C schema; never opens a writable journal."""
    directory=Path(directory);lock=directory/'experiment.lock';journal=directory/'journal.sqlite'
    for p in (lock,journal):
        st=p.lstat()
        if p.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1:raise Refused('journal_identity')
    fd=os.open(lock,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        db=sqlite3.connect('file:'+str(journal)+'?mode=ro',uri=True)
        try:
            db.execute('PRAGMA query_only=ON');rows=db.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall();metadata=db.execute('SELECT id,config FROM metadata').fetchall()
        finally:db.close()
        return {'prefix':stable(rows[:10]),'metadata':stable(metadata),'rows':rows,'lockIdentity':[os.fstat(fd).st_dev,os.fstat(fd).st_ino]}
    finally:os.close(fd)

def post_append(directory,before,operation):
    after=journal_snapshot(directory)
    if any(after[k]!=before[k] for k in ('prefix','metadata','lockIdentity')) or len(after['rows'])not in (10,11):raise Refused('post_append_prefix')
    charge=0
    if len(after['rows'])==11:
        row=after['rows'][10]
        if list(row[:6])!=[11,*SLOT,'reserved_uncertain',CEILING] or json.loads(row[6]).get('operation')!=operation:raise Refused('post_append_reservation')
        charge=CEILING
    return {'historicalPrefixUnchanged':True,'historicalMetadataUnchanged':True,'sameLockIdentity':True,'childConservativeExposureNanodollars':charge,'rowCount':len(after['rows']),'refundAuthorized':False,'planningAuthorized':False}
