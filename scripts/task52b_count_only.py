"""Prepared count-only continuation. No live authorization or credential read now.

The old GET/count scope is read-only and remains consumed. Real execution needs
separate owner send confirmation AND independently established Write evidence.
"""
from base64 import b64decode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import http.client
from time import monotonic
from base64 import b64encode
from scripts import task52b_readiness_enrolled as e
from scripts import task52b_code_identity as code_identity
from scripts import task52b_get_evidence as get_evidence
from backend.provider_responses import HTTPResult

q=e.q
ROOT=Path(__file__).resolve().parents[1]
OPERATION='52b-count-only-owner-3ec6b68-v1'
STATE=e.BASE/OPERATION  # Proposed only: this checkpoint never creates it.
AUTHORIZATION=e.BASE/(OPERATION+'.send-authorization.json')
PERMISSION=e.BASE/(OPERATION+'.permission-evidence-v2.json')
PROFILE=ROOT/'docs/task52b-count-only-PROPOSED-v1.json'
BUILD=ROOT/'docs/task52b-count-only-build-v4.json'
BINDING=ROOT/'docs/task52b-count-only-dashboard-binding-v2.json'
OBSERVATION=e.BASE/(OPERATION+'.dashboard-observation-v2.json')
GET_BINDING=ROOT/'docs/task52b-count-get-binding-v1.json'
BOOTSTRAP=ROOT/'scripts/task52b_run_count_once.py'
ENDPOINT='https://api.openai.com/v1/responses/input_tokens'
PROJECT=e.PROJECT
_SingleDial=e._SingleDial
private_create=e.private_create
digest=e.digest
stamp=e.stamp
MAX_RESPONSE=e.MAX_RESPONSE
DEADLINE=e.DEADLINE
_FIXTURES={}


def request():
    r=q.requests()[1]
    if (r.method,r.url,e.digest(r.body))!=('POST',ENDPOINT,q.COUNT_SHA):raise q.Refused('count_request_identity')
    return r


def utc(value):
    try:t=datetime.fromisoformat(value)
    except (ValueError,TypeError):raise q.Refused('evidence_timestamp') from None
    if t.tzinfo is None or t.utcoffset()!=timedelta(0):raise q.Refused('evidence_timezone')
    return t


def fresh(when,now):
    t=utc(when)
    if now.tzinfo is None or now.utcoffset()!=timedelta(0) or not 0 <= (now-t).total_seconds() <= 86400 or now.date()!=t.date():
        raise q.Refused('prior_evidence_stale')
    return min(t+timedelta(days=1),t.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1))


def validate_get_record(raw,validated,expected,now):
    if raw['status']!=200 or raw['complete'] is not True or raw.get('credentialEchoRefused') is not False:
        raise q.Refused('prior_get_incomplete')
    body=b64decode(raw['bodyBase64'],validate=True)
    if e.digest(body)!=expected or raw['bodySHA256']!=expected or validated['rawSHA256']!=expected:
        raise q.Refused('prior_get_integrity')
    value=q.validate_response(q.requests()[0],HTTPResult(200,body,True,raw['contentType']))
    if validated['value']!=value or utc(validated['at'])<utc(raw['at']):raise q.Refused('prior_get_validation')
    expires=fresh(raw['at'],now);fresh(validated['at'],now)
    return {'model':q.MODEL,'rawSHA256':expected,'observedAt':raw['at'],'expiresAt':expires.isoformat()}


def prior_get(now):
    """Read-only verification of the successful GET's original immutable chain."""
    return get_evidence.verify(GET_BINDING,now,fresh)


def permission_record(record,identity,now):
    """Validate evidence shape, never certify an unobserved dashboard/API state."""
    if type(record)is not dict or record.get('project')!=PROJECT or record.get('credentialIdentity')!=identity:
        raise q.Refused('permission_identity')
    if record.get('permissions')!={'listModels':'Read','responses':'Write','unrelated':'None'}:
        raise q.Refused('responses_write_required')
    if record.get('independentlyEstablished') is not True or record.get('basis') not in ('independently-observed-dashboard','verified-permission-receipt'):
        raise q.Refused('write_permission_record_pending')
    if not re.fullmatch('[0-9a-f]{64}',record.get('evidenceSHA256','')) or not record.get('observer'):
        raise q.Refused('permission_evidence')
    fresh(record['observedAt'],now)
    return e.digest(json.dumps(record,sort_keys=True).encode())


def verified_permission(now):
    """Verify the separately observed dashboard transcript and pinned receipt.

    Owner-only observer evidence is not a provider-signed permission guarantee.
    Neither this record nor Write capability authorizes a provider send.
    """
    identity=e.digest(e.private_read(e.PRIVATE_ENROLLMENT))
    record=e.record(PERMISSION);binding=json.loads(BINDING.read_bytes())
    raw=e.private_read(OBSERVATION);observed=json.loads(raw)
    value=permission_record(record,identity,now)
    if (binding['credentialIdentity']!=identity or binding['permissionSHA256']!=value or
            binding['observationSHA256']!=e.digest(raw) or record['evidenceSHA256']!=e.digest(raw)):
        raise q.Refused('permission_observation_binding')
    enrollment=e.record(e.PRIVATE_ENROLLMENT)
    original=json.loads(e.private_read(Path(enrollment['metadataPath'])))
    if (observed['project']!=PROJECT or observed['projectName']!='WhereTo Model Evaluation' or
            observed['trackingId']!=enrollment['trackingId'] or observed['trackingId']!=original['trackingId'] or
            observed['keyName']!='WhereTo Task52B Evaluation' or observed['status']!='Active' or
            observed['expiresOn']!=original['expiresOn'] or observed['permissions']!=record['permissions'] or
            observed['credentialIdentity']!=identity or observed['observedAt']!=record['observedAt'] or
            observed['changedPermissions'] is not False or observed['secretValueAccessed'] is not False):
        raise q.Refused('observed_key_identity')
    fresh(observed['observedAt'],now)
    return value


def proposed_scope():
    return {'operation':OPERATION,'project':PROJECT,'model':q.MODEL,'method':'POST','endpoint':ENDPOINT,
            'countSHA256':q.COUNT_SHA,'getMaximum':0,'postMaximum':1,'inferenceMaximum':0,'retries':0}


def validate_scope(s):
    for k,v in proposed_scope().items():
        if type(s.get(k))is not type(v) or s[k]!=v:raise q.Refused('count_scope_binding')


def inspect_preparation(now=None):
    now=now or datetime.now(timezone.utc);proof=None;blockers=[];permission_verified=False
    try:proof=prior_get(now)
    except q.Refused as why:blockers.append(str(why))
    # Only metadata/stat, never the credential descriptor or value.
    enrollment=e.record(e.PRIVATE_ENROLLMENT)
    original=json.loads(e.private_read(Path(enrollment['metadataPath'])))
    old_auth=json.loads(e.AUTHORIZATION.read_bytes());e.metadata(enrollment,old_auth['credentialMetadataSHA256'])
    if not PERMISSION.exists():blockers.append('independently_established_write_record_missing')
    else:
        try:verified_permission(now);permission_verified=True
        except q.Refused as why:blockers.append(str(why))
    if not AUTHORIZATION.exists():blockers.append('separate_explicit_send_confirmation_missing')
    return {'operation':OPERATION,'priorGET':proof,'storedHistoricalPermissions':original['permissions'],
            'ownerReportedWriteChange':True,'permissionIndependentlyVerified':permission_verified,'blockers':blockers,
            'liveScopeExists':STATE.exists(),'liveAuthorizationExists':AUTHORIZATION.exists(),'sendAuthorized':False}


def loaded_targets():
    writer=e.sys.modules['scripts.task52_q4a']
    return {
        'wire':(CountOnlyHTTPS.exchange,globals(),Path(__file__),'CountOnlyHTTPS.exchange'),
        'dial':(_SingleDial.connect,e.__dict__,Path(e.__file__),'_SingleDial.connect'),
        'tls':(e.FixedReadinessHTTPS.__init__,e.__dict__,Path(e.__file__),'FixedReadinessHTTPS.__init__'),
        'writer':(private_create,writer.__dict__,Path(writer.__file__),'private_create'),
        'fsync':(e.fsync_dir,writer.__dict__,Path(writer.__file__),'fsync_dir'),
        'reader':(e.read_openai_only,e.__dict__,Path(e.__file__),'read_openai_only'),
        'metadata':(e.metadata,e.__dict__,Path(e.__file__),'metadata'),
        'private_read':(e.private_read,e.__dict__,Path(e.__file__),'private_read'),
        'request':(request,globals(),Path(__file__),'request'),
        'intent_guard':(verify_intent,globals(),Path(__file__),'verify_intent'),
        'supervision':(verify_supervision,globals(),Path(__file__),'verify_supervision'),
        'worker':(execute_count_only,globals(),Path(__file__),'execute_count_only'),
        'runner':(run_count,globals(),Path(__file__),'run_count'),
        'preconditions':(live_preconditions,globals(),Path(__file__),'live_preconditions'),
        'prior_get':(prior_get,globals(),Path(__file__),'prior_get'),
        'get_evidence':(get_evidence.verify,get_evidence.__dict__,Path(get_evidence.__file__),'verify'),
        'get_archive':(get_evidence.archived_build,get_evidence.__dict__,Path(get_evidence.__file__),'archived_build'),
        'get_blob':(get_evidence.blobs,get_evidence.__dict__,Path(get_evidence.__file__),'blobs'),
        'permission':(verified_permission,globals(),Path(__file__),'verified_permission'),
        'permission_record':(permission_record,globals(),Path(__file__),'permission_record'),
        'freshness':(fresh,globals(),Path(__file__),'fresh'),
        'utc':(utc,globals(),Path(__file__),'utc'),
    }


def identity_manifest():
    """Build-time identities compiled independently; never trust live self hashes."""
    identities={}
    for name,(_,_,path,qualname) in loaded_targets().items():
        identities[name]=code_identity.compiled(path,digest(path.read_bytes()),qualname)
    return {'loadedIdentityScheme':code_identity.VERSION,'loadedCodeIdentities':identities}


def verified_wire_identity(build=None):
    b=build or json.loads(BUILD.read_bytes())
    try:
        if (b['loadedIdentityScheme']!=code_identity.VERSION or _SingleDial is not e._SingleDial or
                private_create is not e.private_create or CountOnlyHTTPS.__bases__!=(e.FixedReadinessHTTPS,) or
                CountOnlyHTTPS.__init__ is not e.FixedReadinessHTTPS.__init__ or
                type(CountOnlyHTTPS) is not type or CountOnlyHTTPS.__getattribute__ is not object.__getattribute__ or
                CountOnlyHTTPS.__new__ is not object.__new__ or CountOnlyHTTPS.__setattr__ is not object.__setattr__ or
                set(CountOnlyHTTPS.__dict__)!={'__module__','__doc__','exchange'}):
            raise code_identity.IdentityRefused('transport_binding')
        values={}
        for name,(function,namespace,path,qualname) in loaded_targets().items():
            relative=str(path.relative_to(Path(__file__).resolve().parents[1]))
            values[name]=code_identity.require(function,path,b['filesSHA256'][relative],qualname,namespace)
        if values!=b['loadedCodeIdentities']:raise code_identity.IdentityRefused('manifest_code_identity')
        return values['wire']
    except (code_identity.IdentityRefused,KeyError,ValueError):
        raise q.Refused('count_loaded_code_identity') from None


def verify_count_build(expected):
    raw=BUILD.read_bytes()
    if expected!=e.digest(raw):raise q.Refused('count_build_identity')
    b=json.loads(raw)
    for name,h in b['filesSHA256'].items():
        path=ROOT/name
        if path.is_symlink() or e.digest(path.read_bytes())!=h:raise q.Refused('count_source_identity')
    # Same frozen interpreter/CA checks as the prior transport; normalize only
    # the bootstrap's manifest literal to avoid a self-referential source hash.
    if (e.digest(Path(e.sys.executable).resolve().read_bytes())!=b['pythonExecutableSHA256'] or
            e.digest(Path(e.certifi.where()).read_bytes())!=b['caBundleSHA256']):
        raise q.Refused('count_runtime_identity')
    boot=BOOTSTRAP.read_text();match=re.search(r"(?m)^MANIFEST_SHA = '([0-9a-f]{64})'$",boot)
    if match is None or match.group(1)!=expected:raise q.Refused('count_bootstrap_identity')
    normalized=boot[:match.start(1)]+'__BUILD_SHA__'+boot[match.end(1):]
    if e.digest(normalized.encode())!=b['bootstrapTemplateSHA256']:raise q.Refused('count_bootstrap_source')
    if e.os.environ.get('SSLKEYLOGFILE') or e.os.environ.get('PYTHONINSPECT'):
        raise q.Refused('unsafe_runtime_environment')
    verified_wire_identity(b)
    return b


def validate_preparation(expected,now=None):
    """Read-only readiness. Never creates a scope, authorization or INTENT."""
    now=now or datetime.now(timezone.utc)
    b=verify_count_build(expected);proof=prior_get(now);p=verified_permission(now)
    enrollment=e.record(e.PRIVATE_ENROLLMENT)
    e.metadata(enrollment,json.loads(e.AUTHORIZATION.read_bytes())['credentialMetadataSHA256'])
    request()
    return b,proof,p


def live_preconditions(directory,now):
    if directory!=STATE:raise q.Refused('fixed_count_scope')
    # Absent authorization stops BEFORE creating/consuming any live scope.
    auth=e.record(AUTHORIZATION)
    if auth.get('explicitOwnerSendConfirmation') is not True or auth.get('operation')!=OPERATION:
        raise q.Refused('separate_explicit_send_confirmation_required')
    b,proof,p=validate_preparation(auth.get('buildSHA256'),now)
    s=e.record(STATE/'scope.json');validate_scope(s)
    raw=BUILD.read_bytes()
    if s['buildSHA256']!=e.digest(raw) or auth.get('scopeSHA256')!=e.digest(e.private_read(STATE/'scope.json')):
        raise q.Refused('count_build_or_scope_identity')
    identity=e.digest(e.private_read(e.PRIVATE_ENROLLMENT))
    if auth.get('permissionSHA256')!=p or auth.get('priorGETBundleSHA256')!=proof['bundleSHA256']:
        raise q.Refused('owner_authorization_evidence_binding')
    enrollment=e.record(e.PRIVATE_ENROLLMENT)
    e.metadata(enrollment,json.loads(e.AUTHORIZATION.read_bytes())['credentialMetadataSHA256'])
    if auth.get('credentialIdentity')!=identity or s.get('credentialIdentity')!=identity or s.get('permissionSHA256')!=p or s.get('priorGETBundleSHA256')!=proof['bundleSHA256']:
        raise q.Refused('count_evidence_binding')
    if s.get('supervisorIdentity')!=b['filesSHA256']['scripts/task52b_count_only.py']:raise q.Refused('supervisor_identity')
    e.private_directory(STATE)
    return s


def verify_intent(directory):
    if str(directory) in _FIXTURES:
        s=e.record(directory/'scope.json');validate_scope(s)
    else:
        s=live_preconditions(directory,datetime.now(timezone.utc));verify_supervision(s,require_runtime=True)
    if (e.record(directory/'consumed.json')['scopeSHA256']!=e.digest(e.private_read(directory/'scope.json')) or
        e.record(directory/'intent.json')!={'operation':OPERATION,'method':'POST','endpoint':ENDPOINT,'bodySHA256':q.COUNT_SHA,'buildSHA256':s['buildSHA256']}):
        raise q.Refused('count_intent')
    return s


class CountOnlyHTTPS(e.FixedReadinessHTTPS):
    """Same reviewed TLS/framing/capture code, but only one fixed POST path."""
    def exchange(self,key):
        verify_intent(self.directory)
        if str(self.directory) in _FIXTURES:
            if not key.startswith('FICTIONAL-'):raise q.Refused('fictional_key_required')
            peer,port=_FIXTURES[str(self.directory)]
        else:peer,port='api.openai.com',443
        private_create(self.directory/'wire-consumed.json',{'intentSHA256':e.digest(e.private_read(self.directory/'intent.json')),'at':e.stamp()})
        request=q.requests()[1];path='/v1/responses/input_tokens';index=1
        if request!=globals()['request']():raise q.Refused('count_request_identity')
        # NETWORK_TAIL: verbatim prior exchange body except pinned peer/port binding.
        began=monotonic();c=None;body=bytearray();status=None;media='';complete=False;category=None;started=False;request_id=None
        try:
            c=_SingleDial(peer,port,context=self.context,timeout=10)
            c.auto_open=False;c.connect();stream=c.sock
            def deadline():
                left=DEADLINE-(monotonic()-began)
                if left<=0:raise TimeoutError()
                stream.settimeout(left)
            deadline()
            verify_intent(self.directory)  # Recheck absolute evidence expiry after TLS, before HTTP.
            started=True
            c.request(request.method,path,request.body,{'Authorization':'Bearer '+key,
                'OpenAI-Project':PROJECT,'Content-Type':'application/json','Accept':'application/json',
                'Accept-Encoding':'identity','Connection':'close'})
            deadline();response=c.getresponse();status=response.status
            media=response.getheader('content-type','');length=response.getheader('content-length')
            rid=response.getheader('x-request-id')
            if rid and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',rid):request_id=rid
            project=response.getheader('openai-project')
            if project is not None and project!=PROJECT:raise q.Refused('response_project')
            if (len(media)>128 or response.getheader('content-encoding','identity')!='identity' or
                    length is not None and (not re.fullmatch(r'[0-9]{1,10}',length) or int(length)>MAX_RESPONSE) or
                    length is not None and response.chunked):raise q.Refused('response_framing')
            while not response.isclosed():
                deadline()
                try:chunk=response.read1(min(8192,MAX_RESPONSE+1-len(body)))
                except http.client.IncompleteRead as error:body.extend(error.partial[:MAX_RESPONSE+1-len(body)]);raise
                if not chunk:break
                body.extend(chunk)
                if len(body)>MAX_RESPONSE:raise q.Refused('response_bound')
            if response.length not in (None,0):raise q.Refused('truncated')
            deadline()
            if media.split(';')[0].strip()!='application/json':raise q.Refused('response_media')
            complete=True
        except Exception as error:category=type(error).__name__  # Never exception text/key.
        finally:
            if c:c.close()
        raw=bytes(body)
        # Refuse rather than persist any credential-like response echo.
        values=(raw,media.encode(errors='replace'),(request_id or '').encode())
        safe=all(key.encode() not in v and b'sk-' not in v and b'Bearer ' not in v for v in values)
        data={'at':stamp(),'status':status,'contentType':media if safe and len(media)<=128 else '',
              'complete':complete,'errorCategory':category,'sendStarted':started,'requestId':request_id if safe else None,
              'bodySHA256':digest(raw),'bodyBytes':len(raw),'bodyBase64':b64encode(raw).decode() if safe else None,
              'credentialEchoRefused':not safe}
        private_create(self.directory/f'response-{index}.json',data)
        if not safe:raise q.Refused('credential_echo_not_persisted')
        if not complete:raise q.Refused('uncertain_or_incomplete_no_retry')
        return HTTPResult(status,raw,True,media)


def run_count(directory,key_loader,transport,now=None):
    now=now or datetime.now(timezone.utc)
    if str(directory) not in _FIXTURES:live_preconditions(directory,now)
    e.private_directory(directory);s=e.record(directory/'scope.json');validate_scope(s)
    # A separate source-bound supervisor identity is durably claimed first.
    try:
        private_create(directory/'supervisor-claim.json',{'operation':OPERATION,'supervisorIdentity':s['supervisorIdentity']})
        private_create(directory/'consumed.json',{'scopeSHA256':e.digest(e.private_read(directory/'scope.json')),'at':e.stamp()})
    except FileExistsError:raise q.Refused('count_scope_already_claimed') from None
    result={'operation':OPERATION,'inference':0,'getRequests':0,'postMaximum':1,'retries':0,'count':None,'result':'stopped'}
    try:
        private_create(directory/'intent.json',{'operation':OPERATION,'method':'POST','endpoint':ENDPOINT,'bodySHA256':q.COUNT_SHA,'buildSHA256':s['buildSHA256']})
        reply=transport.exchange(key_loader())
        result['status']=reply.status;result['rawSHA256']=reply.digest
        value=q.validate_response(request(),reply)
        private_create(directory/'validated.json',{'value':value,'rawSHA256':reply.digest,'at':e.stamp()})
        result.update(result='completed',count=value['inputTokens'])
    except Exception as why:
        result['reason']=str(why) if type(why)is q.Refused and re.fullmatch('[a-z0-9_]+',str(why)) else type(why).__name__
    private_create(directory/'result.json',result);return result


class FictionalCount:
    """No real root, credential or authorization. Canned or loopback tests only."""
    def __init__(self,port=1):
        self.temp=TemporaryDirectory(prefix='whereto-count-fixture-');self.directory=Path(self.temp.name);self.directory.chmod(0o700)
        b=e.digest(BUILD.read_bytes())
        s=proposed_scope()|{'buildSHA256':b,'supervisorIdentity':e.digest(Path(__file__).read_bytes()),'fixtureOnly':True}
        private_create(self.directory/'scope.json',s);_FIXTURES[str(self.directory)]=('127.0.0.1',port)
    def close(self):_FIXTURES.pop(str(self.directory),None);self.temp.cleanup()


def verify_supervision(scope,require_runtime=False):
    launcher=e.record(STATE/'launcher-claim.json')
    if (launcher.get('operation')!=OPERATION or launcher.get('buildSHA256')!=scope['buildSHA256'] or
            launcher.get('supervisorPID')!=e.os.getppid()):
        raise q.Refused('count_supervisor_identity')
    if require_runtime:
        runtime=e.record(STATE/'runtime.json')
        if (runtime.get('workerPID')!=e.os.getpid() or runtime.get('buildSHA256')!=scope['buildSHA256'] or
                runtime.get('identityScheme')!=code_identity.VERSION or runtime.get('loadedWireIdentitySHA256')!=verified_wire_identity()):
            raise q.Refused('count_worker_identity')


def execute_count_only(expected=None):
    """Prepared real worker. Missing live authorization refuses before any write."""
    scope=live_preconditions(STATE,datetime.now(timezone.utc))
    if expected!=scope['buildSHA256']:raise q.Refused('supervised_build_identity')
    verify_supervision(scope)
    import resource
    if resource.getrlimit(resource.RLIMIT_CORE)!=(0,0):raise q.Refused('core_dump_protection')
    private_create(STATE/'runtime.json',{'workerPID':e.os.getpid(),'buildSHA256':expected,
        'identityScheme':code_identity.VERSION,'loadedWireIdentitySHA256':verified_wire_identity(),'at':e.stamp()})
    def key():
        live_preconditions(STATE,datetime.now(timezone.utc));verify_supervision(scope,True)
        enrollment=e.record(e.PRIVATE_ENROLLMENT)
        return e.read_openai_only(enrollment,json.loads(e.AUTHORIZATION.read_bytes())['credentialMetadataSHA256'])
    return run_count(STATE,key,CountOnlyHTTPS(STATE))
