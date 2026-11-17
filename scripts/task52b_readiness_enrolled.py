"""One owner-authorized readiness pair; no inference or credential fallback.

Separate from the frozen halted experiment. Same-user operator/filesystem trust,
not a sandbox against a compromised Mac administrator. All live paths are fixed.
"""
from base64 import b64encode
from datetime import datetime, timezone, date
from hashlib import sha256
from pathlib import Path
from time import monotonic
import http.client
import json
import os
import re
import ssl
import stat
import sys
import marshal
import certifi

from scripts import task52b_readiness as q
import socket
from scripts.task52_q4a import private_create, fsync_dir
from backend.provider_responses import HTTPResult

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'proj_E4EfEvC5uQYN4nqFaYZoo3I4'
OPERATION = '52b-readiness-owner-63ecdbb-first-v1'
BASE = ROOT / 'backend/.local/task52b-readiness'
STATE = BASE / OPERATION
PRIVATE_ENROLLMENT = BASE / 'credential-enrollment-v1.json'
MANIFEST = ROOT / 'docs/task52b-readiness-live-build-v1.json'
AUTHORIZATION = ROOT / 'docs/task52b-readiness-owner-authorization-v1.json'
# Verbatim reviewed class; AST equality is tested without importing frozen inference.
Denied = q.Refused


class _SingleDial(http.client.HTTPSConnection):
    def connect(self):
        if self._tunnel_host:raise Denied('No proxy tunnel')
        addresses=socket.getaddrinfo(self.host,self.port,type=socket.SOCK_STREAM)
        if not addresses:raise Denied('No endpoint address')
        family,kind,proto,_,address=addresses[0]  # No alternate address retry.
        raw=socket.socket(family,kind,proto)
        try:
            raw.settimeout(self.timeout);raw.connect(address)
            self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:
            raw.close();raise


MAX_RESPONSE = 65536
DEADLINE = 20


def stamp(): return datetime.now(timezone.utc).isoformat()
def digest(raw): return sha256(raw).hexdigest()


def private_read(path, maximum=1048576):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1 or s.st_size > maximum:
            raise q.Refused('private_file_identity')
        data = os.read(fd, maximum+1)
        if len(data) != s.st_size: raise q.Refused('private_file_size')
        return data
    finally: os.close(fd)


def private_directory(path):
    s = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
        raise q.Refused('private_directory')


def make_directory(path):
    os.mkdir(path, 0o700);fsync_dir(path.parent);private_directory(path)


def record(path): return json.loads(private_read(path))


def verify_build(expected):
    raw = MANIFEST.read_bytes()
    if digest(raw) != expected: raise q.Refused('readiness_build')
    build = json.loads(raw)
    for name, h in build['filesSHA256'].items():
        p = ROOT/name
        if p.is_symlink() or digest(p.read_bytes()) != h: raise q.Refused('readiness_source')
    a = json.loads(AUTHORIZATION.read_bytes())
    if (a['operation'] != OPERATION or a['project'] != PROJECT or a['model'] != q.MODEL or
            a['countSHA256'] != q.COUNT_SHA or a['inferenceMaximum'] != 0 or
            a['getMaximum'] != 1 or a['postMaximum'] != 1 or a['retries'] != 0 or
            a['permissionChangesAuthorized'] is not False or a['historicalHaltPreserved'] is not True):
        raise q.Refused('readiness_owner_scope')
    if digest(Path(sys.executable).resolve().read_bytes()) != build['pythonExecutableSHA256']:
        raise q.Refused('interpreter_identity')
    boot=(ROOT/'scripts/task52b_run_readiness_once.py').read_text()
    match=re.search(r"(?m)^MANIFEST_SHA = '([0-9a-f]{64})'$",boot)
    if match is None or match.group(1)!=expected:
        raise q.Refused('bootstrap_identity')
    normalized=boot[:match.start(1)]+'__BUILD_SHA__'+boot[match.end(1):]
    if digest(normalized.encode()) != build['bootstrapTemplateSHA256']:
        raise q.Refused('bootstrap_source')
    if digest(Path(certifi.where()).read_bytes()) != build['caBundleSHA256']:
        raise q.Refused('ca_identity')
    if os.environ.get('SSLKEYLOGFILE') or os.environ.get('PYTHONINSPECT'):
        raise q.Refused('unsafe_runtime_environment')
    q.requests()
    return build, a


def metadata(enrollment, expected_metadata):
    p = Path(enrollment['metadataPath'])
    f = Path(enrollment['credentialPath'])
    if (p.parent != ROOT/'backend' or f.parent != ROOT/'backend' or
            not f.name.startswith('.env.cloud-evaluation.openai-replacement-') or
            p.name != f.name+'.metadata.json'):
        raise q.Refused('credential_location')
    raw = private_read(p, 8192)
    if digest(raw) != expected_metadata: raise q.Refused('credential_metadata_changed')
    m = json.loads(raw)
    if (m['projectId'] != PROJECT or m['projectName'] != 'WhereTo Model Evaluation' or
            m['credentialFile'] != str(f) or m['trackingId'] != enrollment['trackingId'] or
            m['permissions'] != {'listModels':'Read','responses':'Read','unrelated':'None'} or
            date.fromisoformat(m['expiresOn']) <= date.today()):
        raise q.Refused('credential_scope_or_expiry')
    s = f.lstat()
    if (f.is_symlink() or not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or
            stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1 or
            [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns] != [enrollment[k] for k in ('credentialDevice','credentialInode','credentialSize','credentialMtimeNS')]):
        raise q.Refused('credential_file_changed')
    return f


def read_openai_only(enrollment, expected_metadata):
    """Approved mode0600 dotenv, first OpenAI line only; other keys NOT read."""
    f = metadata(enrollment, expected_metadata)
    fd = os.open(f, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1 or
                [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns] != [enrollment[k] for k in ('credentialDevice','credentialInode','credentialSize','credentialMtimeNS')]):
            raise q.Refused('credential_descriptor_changed')
        if os.read(fd,15) != b'OPENAI_API_KEY=': raise q.Refused('approved_openai_first_line_required')
        value=bytearray()
        while len(value)<=1024:
            b=os.read(fd,1)
            if b in (b'',b'\n'):break
            value.extend(b)
        if not re.fullmatch(rb'sk-proj-[A-Za-z0-9_-]{20,1016}',value): raise q.Refused('project_key_format')
        # No env export, alternate key, historical file or unrelated credential.
        metadata(enrollment, expected_metadata)
        return value.decode('ascii')
    finally: os.close(fd)


def intent_value(scope,index,request):
    return {'operation':scope['operation'],'buildSHA256':scope['buildSHA256'],
            'project':PROJECT,'index':index,'method':request.method,'url':request.url,
            'bodySHA256':digest(request.body),'credentialIdentity':scope['credentialIdentity']}


def verify_intent(directory,index,pair):
    private_directory(directory)
    s=record(directory/'scope.json');consumed=record(directory/'consumed.json')
    if (s['operation']!=OPERATION or s['project']!=PROJECT or s['countSHA256']!=q.COUNT_SHA or
            consumed['scopeSHA256']!=digest(private_read(directory/'scope.json')) or index not in (1,2) or
            record(directory/f'intent-{index}.json')!=intent_value(s,index,pair[index-1])):
        raise q.Refused('durable_readiness_intent')
    if index==2:
        v=record(directory/'validated-1.json');raw=record(directory/'response-1.json')
        from base64 import b64decode
        body=b64decode(raw['bodyBase64'],validate=True)
        if digest(body)!=raw['bodySHA256'] or v['rawSHA256']!=raw['bodySHA256'] or v['value']!=q.validate_response(pair[0],HTTPResult(raw['status'],body,raw['complete'],raw['contentType'])):
            raise q.Refused('model_precondition')
    return s


class FixedReadinessHTTPS:
    """Only the fixed indexed pair, after durable intent and one-use wire claim."""
    def __init__(self, directory, context=None):
        self.directory=directory
        self.context=context if context is not None else ssl.create_default_context(cafile=certifi.where())
        self.context.minimum_version=ssl.TLSVersion.TLSv1_2
        if not self.context.check_hostname or self.context.verify_mode!=ssl.CERT_REQUIRED or self.context.keylog_filename is not None:
            raise q.Refused('verified_tls_required')
    def exchange(self,index,pair,key):
        if pair!=q.requests() or index not in (1,2):raise q.Refused('exact_pair')
        scope=verify_intent(self.directory,index,pair)
        verify_build(scope['buildSHA256'])
        private_create(self.directory/f'wire-consumed-{index}.json',
                       {'intentSHA256':digest(private_read(self.directory/f'intent-{index}.json')),'at':stamp()})
        # No arbitrary origin, redirects, proxy/netrc, SDK retries or address retry.
        request=pair[index-1];path=('/v1/models/'+q.MODEL) if index==1 else '/v1/responses/input_tokens'
        if request.url!='https://api.openai.com'+path or len(request.body)>100000:raise q.Refused('wire_endpoint')
        began=monotonic();c=None;body=bytearray();status=None;media='';complete=False;category=None;started=False;request_id=None
        try:
            c=_SingleDial('api.openai.com',443,context=self.context,timeout=10)
            c.auto_open=False;c.connect();stream=c.sock
            def deadline():
                left=DEADLINE-(monotonic()-began)
                if left<=0:raise TimeoutError()
                stream.settimeout(left)
            deadline();started=True
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
                except http.client.IncompleteRead as e:body.extend(e.partial[:MAX_RESPONSE+1-len(body)]);raise
                if not chunk:break
                body.extend(chunk)
                if len(body)>MAX_RESPONSE:raise q.Refused('response_bound')
            if response.length not in (None,0):raise q.Refused('truncated')
            deadline()
            if media.split(';')[0].strip()!='application/json':raise q.Refused('response_media')
            complete=True
        except Exception as e:category=type(e).__name__  # Never exception text/key.
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


def run_scope(directory,scope,key_loader,transport):
    """Shared state transitions; fixtures inject only fictional key/transports."""
    pair=q.requests();private_directory(directory)
    if record(directory/'scope.json')!=scope:raise q.Refused('scope_changed')
    try:private_create(directory/'consumed.json',{'scopeSHA256':digest(private_read(directory/'scope.json')),'at':stamp()})
    except FileExistsError:raise q.Refused('readiness_scope_already_consumed') from None
    summary={'operation':OPERATION,'project':PROJECT,'model':q.MODEL,'countSHA256':q.COUNT_SHA,
             'authorizationConsumed':True,'supportZeroCountFeeAccepted':True,'billingIndependentlyVerified':False,
             'operations':[],'inputTokens':None,'inference':0,'retries':0}
    try:
        key=key_loader()  # After consumed scope, before any wire operation.
        for index,request in enumerate(pair,1):
            intent=intent_value(scope,index,request);private_create(directory/f'intent-{index}.json',intent)
            outcome={'index':index,'method':request.method,'url':request.url,'intentSHA256':digest(private_read(directory/f'intent-{index}.json')),'status':None,'validated':False}
            summary['operations'].append(outcome)
            reply=transport.exchange(index,pair,key)
            outcome['status']=reply.status;outcome['rawSHA256']=reply.digest
            value=q.validate_response(request,reply)
            private_create(directory/f'validated-{index}.json',{'rawSHA256':reply.digest,'value':value,'at':stamp()})
            outcome['validated']=True
            if index==2:summary['inputTokens']=value['inputTokens']
        summary['result']='completed'
    except Exception as e:
        summary['result']='stopped';summary['reason']=str(e) if type(e) is q.Refused and re.fullmatch('[a-z0-9_]+',str(e)) else type(e).__name__
        if summary['operations']:
            i=summary['operations'][-1]['index'];p=directory/f'response-{i}.json'
            if p.exists():
                h=record(p);summary['operations'][-1].update(status=h['status'],rawSHA256=h['bodySHA256'],sendStarted=h['sendStarted'],complete=h['complete'])
    private_create(directory/'result.json',summary)
    return summary


def execute_authorized(expected_manifest):
    build,a=verify_build(expected_manifest)
    private_directory(BASE);private_directory(STATE)
    e=record(PRIVATE_ENROLLMENT)
    metadata(e,a['credentialMetadataSHA256'])  # Metadata/stat checks only, no key yet.
    scope=record(STATE/'scope.json')
    expected={'operation':OPERATION,'project':PROJECT,'model':q.MODEL,'countSHA256':q.COUNT_SHA,
        'buildSHA256':expected_manifest,'authorizationSHA256':digest(AUTHORIZATION.read_bytes()),
        'writerSHA256':build['filesSHA256']['scripts/task52_q4a.py'],
        'credentialIdentity':digest(private_read(PRIVATE_ENROLLMENT)),
        'getMaximum':1,'postMaximum':1,'inferenceMaximum':0,'retries':0}
    if scope!=expected:raise q.Refused('enrollment_scope')
    private_create(STATE/'runtime.json',{'buildSHA256':expected_manifest,'loadedWireBytecodeSHA256':digest(marshal.dumps(FixedReadinessHTTPS.exchange.__code__)),'at':stamp()})
    wire=FixedReadinessHTTPS(STATE)
    return run_scope(STATE,scope,lambda:read_openai_only(e,a['credentialMetadataSHA256']),wire)
