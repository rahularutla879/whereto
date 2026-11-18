"""Fixed Responses transport enrolled only after signed original-journal authority.
No CLI, inference startup hook, endpoint argument, proxy, redirect or retry.
"""
from base64 import b64encode,b64decode
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace,FunctionType,CodeType
from weakref import WeakKeyDictionary
from time import monotonic
import ast,json,os,stat,re,ssl,http.client,certifi,tempfile
from scripts import task52b_generation_candidate as parent
from scripts import task52b_generation_policy as policy
from scripts import task52b_real_enrollment as enrollment
from scripts import task52b_original_journal as journal

Denied=enrollment.Denied
_BINDINGS=WeakKeyDictionary()
kernel=parent.kernel;q1=parent.q1
PAYLOAD_SHA=policy.PAYLOAD_SHA;ENDPOINT=policy.ENDPOINT
_SingleDial=parent._SingleDial
_project=parent._project
_capture_binding=parent._capture_binding


def binding(transport):
    value=_BINDINGS.get(transport)
    if value is None:raise Denied('Unenrolled transport')
    return value


def credential_loader(receipt):
    # Independently compile ONLY the three unchanged approved loader functions.
    # No import of legacy readiness wire, credential fallback or module startup.
    path=policy.ROOT/'scripts/task52b_readiness_enrolled.py'
    expected=json.loads(journal.MANIFEST.read_bytes())['filesSHA256'][str(path.relative_to(policy.ROOT))]
    raw=path.read_bytes()
    if policy.digest(raw)!=expected:raise Denied('Credential loader source')
    names=('private_read','metadata','read_openai_only')
    module=compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
    codes={c.co_name:c for c in module.co_consts if type(c)is CodeType and c.co_name in names}
    if set(codes)!=set(names):raise Denied('Exact credential loader selection')
    root=Path(receipt.binding['fixtureCredentialRoot']) if receipt.fixture else policy.ROOT
    if receipt.fixture and (root==policy.ROOT or not root.is_relative_to(Path(tempfile.gettempdir()).resolve())):raise Denied('Fictional credential root')
    namespace={'__builtins__':__builtins__,'__name__':'scripts.task52b_readiness_enrolled','os':os,'stat':stat,'Path':Path,'json':json,'date':date,'re':re,'ROOT':root,'PROJECT':policy.PROJECT,'q':SimpleNamespace(Refused=Denied),'digest':policy.digest}
    for name in names:namespace[name]=FunctionType(codes[name],namespace,name,(1048576,) if name=='private_read' else None)
    for name in names:parent.code_identity.require(namespace[name],path,expected,name,namespace)
    return namespace


@dataclass(frozen=True)
class Bound:
    receipt:object
    host:str
    port:int
    context:object
    deadline:float
    crash_before_capture:bool


class EnrolledTransport:
    provider='openai';method='POST';endpoint='/v1/responses'
    def __init__(self):raise Denied('Use exact protected enrollment; no caller configuration')
    def exchange(self,directory,operation,payload_hash):
        journal.verify_build();bound=binding(self);receipt=bound.receipt
        receipt.guard()
        if (not receipt.fixture and (bound.host,bound.port)!=('api.openai.com',443)) or (receipt.fixture and bound.host!='127.0.0.1'):raise Denied('Exact authenticated peer')
        if directory!=receipt.facts or self.payload!=policy.payload() or payload_hash!=PAYLOAD_SHA or (self.provider,self.method,self.endpoint)!=('openai','POST','/v1/responses'):raise Denied('Exact enrolled operation')
        supervisor=json.loads(enrollment.private(directory/'supervisor.json'));worker=json.loads(enrollment.private(directory/'worker.json'))
        if supervisor!={'pid':os.getppid(),'build':journal.build_sha(),'operation':operation,'enrollment':receipt.binding_hash} or worker!={'pid':os.getpid(),'parent':os.getppid(),'build':journal.build_sha()}:raise Denied('Supervised process identity')
        rows,meta=journal.snapshot_held(receipt)
        if len(rows)!=11 or rows[10][4:6]!=('reserved_uncertain',policy.CEILING) or json.loads(rows[10][6])['operation']!=operation:raise Denied('Committed financial reservation')
        facts=[json.loads(enrollment.private(p)) for p in sorted(directory.glob('fact-*'))]
        intents=[f for f in facts if f['kind']=='INTENT' and f['operation']==operation]
        if len(intents)!=1 or intents[0]['data']['payloadHash']!=PAYLOAD_SHA:raise Denied('Durable exact INTENT')
        kernel._once(directory/f'dispatch-{operation}.json',{'version':enrollment.VERSION,'build':journal.build_sha(),'operation':operation,'payloadHash':PAYLOAD_SHA,'intentHash':intents[0]['hash'],'enrollmentHash':receipt.binding_hash,'epoch':receipt.trust['epoch']})
        kernel._once(directory/f'http-intent-{operation}.json',{'operation':operation,'method':'POST','endpoint':ENDPOINT,'payloadHash':PAYLOAD_SHA,'credentialIdentity':receipt.binding['credentialIdentity'],'fixtureOnly':receipt.fixture})
        receipt.guard()  # Still before credential loading and before any socket.
        loader=credential_loader(receipt)
        credential=json.loads(enrollment.private(Path(receipt.trust['credentialEnrollment'])))
        if policy.stable(credential)!=receipt.binding['credentialEnrollmentSHA256']:raise Denied('Credential enrollment changed')
        loader['metadata'](credential,receipt.trust['credentialMetadataSHA256'])
        key=loader['read_openai_only'](credential,receipt.trust['credentialMetadataSHA256'])
        if receipt.fixture and key!='sk-proj-'+('FICTIONAL'*6):raise Denied('Fixture never accepts real credentials')
        context=bound.context;payload=policy.payload()
        if not context.check_hostname or context.verify_mode!=ssl.CERT_REQUIRED or context.minimum_version<ssl.TLSVersion.TLSv1_2 or context.keylog_filename is not None:raise Denied('Verified TLS required')
        began=monotonic();connection=None;body=bytearray();status=None;headers={};complete=False;error=None
        try:
            connection=_SingleDial(bound.host,bound.port,context=context,timeout=min(10,bound.deadline))
            connection.auto_open=False
            connection.connect();stream=connection.sock
            def remaining():
                value=bound.deadline-(monotonic()-began)
                if value<=0:raise TimeoutError('Bounded response deadline')
                stream.settimeout(value)
            remaining()
            receipt.recheck_current()
            remaining()
            connection.request('POST','/v1/responses',payload,{
                'Authorization':'Bearer '+key,'OpenAI-Project':policy.PROJECT,'Content-Type':'application/json',
                'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'})
            remaining();response=connection.getresponse();status=response.status
            headers={name:response.getheader(name) for name in ('content-type','content-length','x-request-id')
                     if response.getheader(name)is not None}
            if response.getheader('openai-project') not in (None,policy.PROJECT):raise Denied('Response project mismatch')
            length=response.getheader('content-length');encoding=response.getheader('content-encoding','identity')
            if (length is not None and (not length.isdigit() or int(length)>1048576) or
                    encoding!='identity' or length is not None and response.chunked):
                raise Denied('Response framing/bound refused')
            if any(len(v)>1024 for v in headers.values()):raise Denied('Response header bound')
            while not response.isclosed():
                value=bound.deadline-(monotonic()-began)
                if value<=0:raise TimeoutError('Bounded response deadline')
                stream.settimeout(value)
                try:chunk=response.read1(min(65536,1048577-len(body)))
                except http.client.IncompleteRead as truncated:
                    body.extend(truncated.partial[:1048577-len(body)]);raise
                if not chunk:break
                body.extend(chunk)
                if len(body)>1048576:raise Denied('Response byte bound')
            if response.length not in (None,0):raise Denied('Truncated response')
            if monotonic()-began>bound.deadline:raise TimeoutError('Late complete response')
            if response.getheader('content-type','').split(';')[0]!='application/json':
                raise Denied('Response media type')
            complete=True
            if bound.crash_before_capture:os._exit(73)
        except Exception as failure:
            error=type(failure).__name__  # Never exception text, headers or key.
        finally:
            if connection:connection.close()
            if any(key.encode() in value or b'sk-' in value or b'Bearer ' in value for value in (bytes(body),json.dumps(headers).encode())):
                body=bytearray();headers={};complete=False;error='CredentialEchoRefused'
            kernel._once(directory/f'raw-{operation}.json',{'bytesBase64':b64encode(bytes(body)).decode(),
                'sha256':q1.sha(bytes(body))})
            kernel._once(directory/f'http-{operation}.json',{'status':status,'headers':headers,
                'complete':complete,'errorCategory':error,'rawSHA256':q1.sha(bytes(body))})
        if not complete:raise Denied('Uncertain/incomplete HTTPS operation; retained, no retry')
        value=_project(bytes(body),status,_capture_binding(directory,operation))
        content,usage,stop=kernel.decoder.Adapter('openai',None).decode(value)
        if usage is None or any(type(n)is not int or n<0 for n in usage) or usage[0]>7752 or usage[1]>2000:raise Denied('Unbounded or contradictory usage; no refund')
        kernel._once(directory/f'decoded-{operation}.json',{'rawSHA256':q1.sha(bytes(body)),
            'responseHash':q1.digest(value),'content':content,'usage':usage,'status':stop})
        return value

def enroll_transport(receipt):
    receipt.guard()
    if receipt.fixture:raise Denied('Real entry rejects fixture receipts')
    b=json.loads(journal.MANIFEST.read_bytes())
    if policy.digest(Path(certifi.where()).read_bytes())!=b['caBundleSHA256']:raise Denied('CA source identity')
    context=ssl.create_default_context(cafile=certifi.where());context.minimum_version=ssl.TLSVersion.TLSv1_2
    obj=object.__new__(EnrolledTransport);obj.payload=policy.payload()
    _BINDINGS[obj]=Bound(receipt,'api.openai.com',443,context,120.0,False)
    return obj


def fixture_transport(receipt,port,ca,*,deadline=2,crash=False):
    receipt.guard()
    if not receipt.fixture or type(port)is not int or not 1<=port<=65535 or not 0<deadline<=120:raise Denied('Explicit local fixture only')
    context=ssl.create_default_context(cafile=str(ca));context.minimum_version=ssl.TLSVersion.TLSv1_2
    obj=object.__new__(EnrolledTransport);obj.payload=policy.payload()
    _BINDINGS[obj]=Bound(receipt,'127.0.0.1',port,context,float(deadline),bool(crash))
    return obj


def verify_captures(engine,rows,facts):
    d=engine.directory
    for path in sorted(d.glob('dispatch-*.json')):
        op=path.stem.removeprefix('dispatch-')
        intent=next((f for f in facts if f['kind']=='INTENT' and f['operation']==op),None)
        if intent is None:raise Denied('Orphan dispatch')
        expected={'version':enrollment.VERSION,'build':journal.build_sha(),'operation':op,'payloadHash':PAYLOAD_SHA,'intentHash':intent['hash'],'enrollmentHash':engine.receipt.binding_hash,'epoch':engine.receipt.trust['epoch']}
        if json.loads(enrollment.private(path))!=expected:raise Denied('Dispatch integrity')
        hi=json.loads(enrollment.private(d/f'http-intent-{op}.json'))
        if hi!={'operation':op,'method':'POST','endpoint':ENDPOINT,'payloadHash':PAYLOAD_SHA,'credentialIdentity':engine.receipt.binding['credentialIdentity'],'fixtureOnly':engine.receipt.fixture}:raise Denied('HTTP intent integrity')
        rp=d/f'raw-{op}.json';hp=d/f'http-{op}.json'
        if rp.exists():
            raw=json.loads(enrollment.private(rp));body=b64decode(raw['bytesBase64'],validate=True)
            if len(body)>1048576 or policy.digest(body)!=raw['sha256']:raise Denied('Uncertain raw integrity')
        if hp.exists() and (not rp.exists() or json.loads(enrollment.private(hp))['rawSHA256']!=raw['sha256']):raise Denied('Uncertain HTTP integrity')
    outcomes=[f for f in facts if f['kind']=='OUTCOME']
    for fact in outcomes:
        op=fact['operation'];d=engine.directory
        raw=json.loads(enrollment.private(d/f'raw-{op}.json'));http=json.loads(enrollment.private(d/f'http-{op}.json'))
        body=b64decode(raw['bytesBase64'],validate=True)
        if policy.digest(body)!=raw['sha256'] or http['rawSHA256']!=raw['sha256'] or http['complete']is not True:raise Denied('Independent raw capture')
        dispatch=json.loads(enrollment.private(d/f'dispatch-{op}.json'));intent=next(f for f in facts if f['kind']=='INTENT' and f['operation']==op)
        if dispatch!={'version':enrollment.VERSION,'build':journal.build_sha(),'operation':op,'payloadHash':PAYLOAD_SHA,'intentHash':intent['hash'],'enrollmentHash':engine.receipt.binding_hash,'epoch':engine.receipt.trust['epoch']}:raise Denied('Independent dispatch binding')
        projected=_project(body,http['status'],_capture_binding(d,op))
        if fact['data']['response']!=projected:raise Denied('Independent outcome binding')
        decoded=json.loads(enrollment.private(d/f'decoded-{op}.json'))
        content,usage,stop=kernel.decoder.Adapter('openai',None).decode(projected)
        if decoded!={'rawSHA256':raw['sha256'],'responseHash':q1.digest(projected),'content':content,'usage':list(usage),'status':stop}:raise Denied('Independent decoding')
        grade={'outcomeHash':fact['hash'],'assessment':fact['data']['assessment'],'semanticReview':'deferred','independentlyCorrect':None}
        path=d/f'grading-{op}.json'
        if path.exists():
            if json.loads(enrollment.private(path))!=grade:raise Denied('Independent grading integrity')
        else:kernel._once(path,grade)
