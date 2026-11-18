"""Prepared one-model GET only. No live authorization or credential read now."""
from pathlib import Path
from datetime import datetime,timezone
from tempfile import TemporaryDirectory
from time import monotonic
from base64 import b64encode
import json,re,http.client,resource
from scripts import task52b_count_only as previous
from scripts import task52b_code_identity as code_identity
from backend.provider_responses import HTTPResult

e=previous.e;q=e.q
ROOT=e.ROOT;PROJECT=e.PROJECT
OPERATION='52b-model-get-owner-3e2ba62-v1'
STATE=e.BASE/OPERATION
AUTHORIZATION=e.BASE/(OPERATION+'.send-authorization.json')
BUILD=ROOT/'docs/task52b-model-get-build-v3.json'
BOOTSTRAP=ROOT/'scripts/task52b_run_model_get_once.py'
ENDPOINT='https://api.openai.com/v1/models/gpt-6-luna'
private_create=e.private_create;digest=e.digest;stamp=e.stamp
_SingleDial=e._SingleDial;MAX_RESPONSE=e.MAX_RESPONSE;DEADLINE=e.DEADLINE
_FIXTURES={}


def request():
    r=q.requests()[0]
    if (r.method,r.url,r.body)!=('GET',ENDPOINT,b''):raise q.Refused('get_request_identity')
    return r


def proposed_scope():
    return {'operation':OPERATION,'project':PROJECT,'model':q.MODEL,'method':'GET','endpoint':ENDPOINT,
            'bodySHA256':digest(b''),'getMaximum':1,'postMaximum':0,'inferenceMaximum':0,'retries':0}


def validate_scope(s):
    for k,v in proposed_scope().items():
        if type(s.get(k))is not type(v) or s[k]!=v:raise q.Refused('get_scope_binding')


def original_integrity():
    """Integrity only: expired original evidence never becomes fresh authority."""
    old=json.loads((ROOT/'docs/task52b-authorized-readiness-result-v1.json').read_bytes())
    e.verify_build(old['buildSHA256']);e.private_directory(e.STATE)
    pins=old['privateEvidence']['fileSHA256']
    if {p.name for p in e.STATE.iterdir()}!=set(pins):raise q.Refused('prior_scope_inventory')
    for name,h in pins.items():
        if digest(e.private_read(e.STATE/name))!=h:raise q.Refused('prior_scope_integrity')
    scope=e.record(e.STATE/'scope.json');consumed=e.record(e.STATE/'consumed.json');result=e.record(e.STATE/'result.json')
    if (scope['operation']!=e.OPERATION or not result['authorizationConsumed'] or
            consumed['scopeSHA256']!=digest(e.private_read(e.STATE/'scope.json')) or
            result['operations'][0]['status']!=200 or result['operations'][1]['status']!=401):
        raise q.Refused('prior_consumption_integrity')
    return digest(json.dumps(pins,sort_keys=True).encode())


def loaded_targets():
    writer=e.sys.modules['scripts.task52_q4a']
    return {
        'wire':(GetOnlyHTTPS.exchange,globals(),Path(__file__),'GetOnlyHTTPS.exchange'),
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
        'worker':(execute_get_only,globals(),Path(__file__),'execute_get_only'),
        'runner':(run_get,globals(),Path(__file__),'run_get'),
        'preconditions':(live_preconditions,globals(),Path(__file__),'live_preconditions'),
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
                private_create is not e.private_create or GetOnlyHTTPS.__bases__!=(e.FixedReadinessHTTPS,) or
                GetOnlyHTTPS.__init__ is not e.FixedReadinessHTTPS.__init__ or
                type(GetOnlyHTTPS) is not type or GetOnlyHTTPS.__getattribute__ is not object.__getattribute__ or
                GetOnlyHTTPS.__new__ is not object.__new__ or GetOnlyHTTPS.__setattr__ is not object.__setattr__ or
                set(GetOnlyHTTPS.__dict__)!={'__module__','__doc__','exchange'}):
            raise code_identity.IdentityRefused('transport_binding')
        values={}
        for name,(function,namespace,path,qualname) in loaded_targets().items():
            relative=str(path.relative_to(Path(__file__).resolve().parents[1]))
            values[name]=code_identity.require(function,path,b['filesSHA256'][relative],qualname,namespace)
        if values!=b['loadedCodeIdentities']:raise code_identity.IdentityRefused('manifest_code_identity')
        return values['wire']
    except (code_identity.IdentityRefused,KeyError,ValueError):
        raise q.Refused('get_loaded_code_identity') from None


def verify_build(expected):
    raw=BUILD.read_bytes()
    if digest(raw)!=expected:raise q.Refused('get_build_identity')
    b=json.loads(raw)
    for name,h in b['filesSHA256'].items():
        p=ROOT/name
        if p.is_symlink() or digest(p.read_bytes())!=h:raise q.Refused('get_source_identity')
    if (digest(Path(e.sys.executable).resolve().read_bytes())!=b['pythonExecutableSHA256'] or
            digest(Path(e.certifi.where()).read_bytes())!=b['caBundleSHA256']):raise q.Refused('get_runtime_identity')
    boot=BOOTSTRAP.read_text();m=re.search(r"(?m)^MANIFEST_SHA = '([0-9a-f]{64})'$",boot)
    if m is None or m.group(1)!=expected:raise q.Refused('get_bootstrap_identity')
    if digest((boot[:m.start(1)]+'__BUILD_SHA__'+boot[m.end(1):]).encode())!=b['bootstrapTemplateSHA256']:
        raise q.Refused('get_bootstrap_source')
    if e.os.environ.get('SSLKEYLOGFILE') or e.os.environ.get('PYTHONINSPECT'):raise q.Refused('unsafe_runtime_environment')
    verified_wire_identity(b)
    return b


def validate_preparation(expected):
    b=verify_build(expected);original=original_integrity()
    enrollment=e.record(e.PRIVATE_ENROLLMENT);old=json.loads(e.AUTHORIZATION.read_bytes())
    e.metadata(enrollment,old['credentialMetadataSHA256'])  # Existing List models Read receipt/stat, not secret bytes.
    request()
    return b,original,digest(e.private_read(e.PRIVATE_ENROLLMENT))


def live_preconditions(directory,now=None):
    if directory!=STATE:raise q.Refused('fixed_get_scope')
    now=now or datetime.now(timezone.utc)
    auth=e.record(AUTHORIZATION)  # No creation: absent authorization refuses.
    if auth.get('operation')!=OPERATION or auth.get('explicitOwnerSendConfirmation') is not True:
        raise q.Refused('separate_get_confirmation_required')
    expiry=previous.fresh(auth['approvedAt'],now)
    if auth.get('expiresAt')!=expiry.isoformat():raise q.Refused('get_authorization_expiry')
    b,original,identity=validate_preparation(auth.get('buildSHA256'))
    s=e.record(STATE/'scope.json');validate_scope(s)
    if (s['buildSHA256']!=digest(BUILD.read_bytes()) or auth.get('scopeSHA256')!=digest(e.private_read(STATE/'scope.json')) or
            s.get('credentialIdentity')!=identity or auth.get('credentialIdentity')!=identity or
            s.get('originalEvidenceBundleSHA256')!=original or auth.get('originalEvidenceBundleSHA256')!=original or
            s.get('supervisorIdentity')!=b['filesSHA256']['scripts/task52b_model_get.py']):
        raise q.Refused('get_enrollment_binding')
    e.private_directory(STATE)
    return s


def verify_supervision(s,require_runtime=False):
    launch=e.record(STATE/'launcher-claim.json')
    if (launch.get('operation')!=OPERATION or launch.get('buildSHA256')!=s['buildSHA256'] or
            launch.get('supervisorPID')!=e.os.getppid()):raise q.Refused('get_supervisor_identity')
    if require_runtime:
        rt=e.record(STATE/'runtime.json')
        if (rt.get('workerPID')!=e.os.getpid() or rt.get('buildSHA256')!=s['buildSHA256'] or
                rt.get('identityScheme')!=code_identity.VERSION or rt.get('loadedWireIdentitySHA256')!=verified_wire_identity()):
            raise q.Refused('get_worker_identity')


def verify_intent(directory):
    if str(directory) in _FIXTURES:s=e.record(directory/'scope.json');validate_scope(s)
    else:
        s=live_preconditions(directory);verify_supervision(s,True)
    if (e.record(directory/'consumed.json')['scopeSHA256']!=digest(e.private_read(directory/'scope.json')) or
            e.record(directory/'intent.json')!={'operation':OPERATION,'method':'GET','endpoint':ENDPOINT,'bodySHA256':digest(b''),'buildSHA256':s['buildSHA256']}):
        raise q.Refused('get_intent')
    return s


class GetOnlyHTTPS(e.FixedReadinessHTTPS):
    """Existing reviewed dial/TLS/capture body, one fixed empty GET only."""
    def exchange(self,key):
        verify_intent(self.directory)
        if str(self.directory) in _FIXTURES:
            if not key.startswith('FICTIONAL-'):raise q.Refused('fictional_key_required')
            peer,port=_FIXTURES[str(self.directory)]
        else:peer,port='api.openai.com',443
        private_create(self.directory/'wire-consumed.json',{'intentSHA256':digest(e.private_read(self.directory/'intent.json')),'at':stamp()})
        request=globals()['request']();path='/v1/models/gpt-6-luna';index=1
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



def run_get(directory,key_loader,transport):
    if str(directory) not in _FIXTURES:live_preconditions(directory)
    e.private_directory(directory);s=e.record(directory/'scope.json');validate_scope(s)
    try:
        private_create(directory/'supervisor-claim.json',{'operation':OPERATION,'supervisorIdentity':s['supervisorIdentity']})
        private_create(directory/'consumed.json',{'scopeSHA256':digest(e.private_read(directory/'scope.json')),'at':stamp()})
    except FileExistsError:raise q.Refused('get_scope_already_claimed') from None
    result={'operation':OPERATION,'inference':0,'postRequests':0,'getMaximum':1,'retries':0,'result':'stopped'}
    try:
        private_create(directory/'intent.json',{'operation':OPERATION,'method':'GET','endpoint':ENDPOINT,'bodySHA256':digest(b''),'buildSHA256':s['buildSHA256']})
        reply=transport.exchange(key_loader());result.update(status=reply.status,rawSHA256=reply.digest)
        value=q.validate_response(request(),reply)
        observed=e.record(directory/'response-1.json')['at']
        expiry=previous.fresh(observed,datetime.now(timezone.utc)).isoformat()
        private_create(directory/'validated.json',{'value':value,'rawSHA256':reply.digest,'observedAt':observed,'expiresAt':expiry,'at':stamp()})
        result.update(result='completed',model=value['model'],observedAt=observed,expiresAt=expiry)
    except Exception as why:
        result['reason']=str(why) if type(why)is q.Refused and re.fullmatch('[a-z0-9_]+',str(why)) else type(why).__name__
        if (directory/'response-1.json').exists():
            try:
                raw=e.record(directory/'response-1.json');result.update(status=raw['status'],rawSHA256=raw['bodySHA256'])
            except (OSError,ValueError,KeyError):result['responseEvidenceRefused']=True
    private_create(directory/'result.json',result);return result


class FictionalGet:
    def __init__(self,port=1):
        self.temp=TemporaryDirectory(prefix='whereto-get-fixture-');self.directory=Path(self.temp.name);self.directory.chmod(0o700)
        private_create(self.directory/'scope.json',proposed_scope()|{'buildSHA256':digest(BUILD.read_bytes()),'supervisorIdentity':digest(Path(__file__).read_bytes()),'fixtureOnly':True})
        _FIXTURES[str(self.directory)]=('127.0.0.1',port)
    def close(self):_FIXTURES.pop(str(self.directory),None);self.temp.cleanup()


def execute_get_only(expected=None):
    s=live_preconditions(STATE)
    if expected!=s['buildSHA256']:raise q.Refused('supervised_build_identity')
    verify_supervision(s)
    if resource.getrlimit(resource.RLIMIT_CORE)!=(0,0):raise q.Refused('core_dump_protection')
    private_create(STATE/'runtime.json',{'workerPID':e.os.getpid(),'buildSHA256':expected,'identityScheme':code_identity.VERSION,'loadedWireIdentitySHA256':verified_wire_identity(),'at':stamp()})
    def key():
        live_preconditions(STATE);verify_supervision(s,True)
        return e.read_openai_only(e.record(e.PRIVATE_ENROLLMENT),json.loads(e.AUTHORIZATION.read_bytes())['credentialMetadataSHA256'])
    return run_get(STATE,key,GetOnlyHTTPS(STATE))
