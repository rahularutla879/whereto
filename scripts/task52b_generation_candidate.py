"""Versioned supervised first-slot candidate over the existing append kernel.

Real construction/enrollment is CLOSED. Only the explicit frozen-source lab can
bind a loopback peer, fictional secret and fictional approval/journal. No live
CLI, credential lookup, source repin or real journal opener is installed.
"""
from base64 import b64decode,b64encode
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from weakref import WeakKeyDictionary
import json,os,http.client,ssl,multiprocessing,resource,sys
from time import monotonic
from scripts import task52b_first_slot as q
from scripts import task52b_generation_policy as policy
from scripts import task52b_code_identity as code_identity

kernel=q.kernel;q1=q.q1;parent_identity=q.parent_identity;identity=q.identity
Denied=q.Denied;MODEL=policy.MODEL;SLOT=policy.SLOT;PAYLOAD_SHA=policy.PAYLOAD_SHA;ENDPOINT=policy.ENDPOINT;VERSION=q.VERSION
_BINDINGS=WeakKeyDictionary()
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/task52b-generation-build-v1.json'
_capture_binding=q._capture_binding
_project=q._project
sqlite_connect=q.sqlite_connect
_SingleDial=q._SingleDial


def operational_enrollment(_packet=None):
    raise Denied('Real generation remains unenrolled: purpose/security/writer/financial/operator approvals required')


def build_sha():return policy.digest(MANIFEST.read_bytes())


def targets():
    return {'build_guard':(verify_build,globals(),Path(__file__),'verify_build'),'wire':(PreparedTransport.exchange,globals(),Path(__file__),'PreparedTransport.exchange'),
            'supervisor':(supervise,globals(),Path(__file__),'supervise'),
            'worker':(worker,globals(),Path(__file__),'worker'),
            'financial':(policy.quote,policy.__dict__,Path(policy.__file__),'quote'),
            'authorization':(policy.validate_packet,policy.__dict__,Path(policy.__file__),'validate_packet'),
            'payload':(policy.payload,policy.__dict__,Path(policy.__file__),'payload'),
            'freshness':(policy.fresh,policy.__dict__,Path(policy.__file__),'fresh'),
            'dial':(_SingleDial.connect,q.__dict__,Path(q.__file__),'_SingleDial.connect'),
            'writer':(kernel.base.private_create,kernel.base.__dict__,Path(kernel.base.__file__),'private_create')}


def identities():
    return {k:code_identity.compiled(path,policy.digest(path.read_bytes()),name) for k,(_,_,path,name) in targets().items()}


def verify_build():
    b=json.loads(MANIFEST.read_bytes())
    for n,h in b['filesSHA256'].items():
        p=ROOT/n
        if p.is_symlink() or policy.digest(p.read_bytes())!=h:raise Denied('Generation source mismatch')
    if b['identityScheme']!=code_identity.VERSION:raise Denied('Generation identity scheme')
    actual={k:code_identity.require(fn,path,b['filesSHA256'][str(path.relative_to(ROOT if path.is_relative_to(ROOT) else q.q1.ROOT))],name,ns) for k,(fn,ns,path,name) in targets().items()}
    if actual!=b['loadedCodeIdentities']:raise Denied('Generation loaded code mismatch')
    if policy.digest(Path(sys.executable).resolve().read_bytes())!=b['pythonExecutableSHA256']:raise Denied('Generation interpreter identity')
    identity.verify(full=True)
    return b


@dataclass(frozen=True)
class _LabBinding:
    host:str
    port:int
    context:ssl.SSLContext
    secret:object
    deadline:float
    crash_before_capture:bool
    packet:dict


class PreparedTransport(q.OpenAIResponsesTransport):
    def __init__(self,enrollment=None,*,credential=None):operational_enrollment(enrollment)
    def exchange(self,directory,operation,payload_hash):
        verify_build()
        policy.validate_packet(_BINDINGS[self].packet,datetime.now(timezone.utc),expected_build=build_sha())
        binding=_BINDINGS.get(self)
        if binding is None or str(directory) not in kernel.REGISTRY:
            raise Denied('No reviewed operational enrollment; closed local fixture required')
        if operation!=binding.packet['operationID'] or binding.packet['writerIdentity']!=json.loads(MANIFEST.read_bytes())['loadedCodeIdentities']['writer'] or binding.packet['credentialIdentity']!=policy.digest(binding.secret.secret_id.encode()):raise Denied('Operation or credential/writer binding')
        runtime=json.loads((directory/'generation-worker.json').read_bytes());supervisor=json.loads((directory/'generation-supervisor.json').read_bytes())
        if runtime['pid']!=os.getpid() or runtime['parentPID']!=os.getppid() or supervisor['pid']!=os.getppid() or runtime['buildSHA256']!=build_sha() or supervisor['packetSHA256']!=policy.stable(binding.packet):raise Denied('Generation supervisor identity')
        payload=policy.payload()  # Immutable local bytes; never reread mutable caller state.
        if (self.payload!=payload or payload_hash!=PAYLOAD_SHA or
                (self.provider,self.method,self.endpoint)!=('openai','POST','/v1/responses')):
            raise Denied('Exact first-slot request required')
        facts=[json.loads(p.read_bytes()) for p in sorted(directory.glob('fact-*'))]
        intents=[f for f in facts if f['kind']=='INTENT' and f['operation']==operation]
        if len(intents)!=1 or intents[0]['data']['payloadHash']!=PAYLOAD_SHA:
            raise Denied('Durable first-slot INTENT required')
        with closing(sqlite_connect(directory)) as db:
            rows=db.execute('SELECT * FROM attempts WHERE provider=? AND case_id=? AND repetition=?',SLOT).fetchall()
        if (len(rows)!=1 or rows[0][3:5]!=('reserved_uncertain',2500000) or
                json.loads(rows[0][5])['operation']!=operation):raise Denied('Committed reservation required')
        kernel._once(directory/f'dispatch-{operation}.json',{'version':kernel.VERSION,
            'build':parent_identity.MANIFEST_SHA,'operation':operation,'payloadHash':PAYLOAD_SHA,
            'intentHash':intents[0]['hash'],'syntheticOnly':True})
        kernel._once(directory/f'http-intent-{operation}.json',{'version':VERSION,
            'build':identity.MANIFEST_SHA,'operation':operation,'payloadHash':PAYLOAD_SHA,
            'method':'POST','endpoint':ENDPOINT,'credentialIdentity':binding.secret.secret_id,
            'networkPeer':'loopback_fixture_only','actualOrigin':f'https://127.0.0.1:{binding.port}',
            'localFixtureOnly':True})
        kernel._once(directory/f'generation-binding-{operation}.json',{'buildSHA256':build_sha(),'packetSHA256':policy.stable(binding.packet),'credentialIdentity':binding.packet['credentialIdentity'],'writerIdentity':binding.packet['writerIdentity'],'slot':policy.SLOT})
        # The loopback gate never accepts a real API key or a remote peer.
        policy.validate_packet(binding.packet,datetime.now(timezone.utc),expected_build=build_sha())
        key=binding.secret.read()
        if not key.startswith('FICTIONAL-OPENAI-'):raise Denied('Real credentials unavailable in local fixtures')
        context=binding.context
        if (not context.check_hostname or context.verify_mode!=ssl.CERT_REQUIRED or
                context.minimum_version<ssl.TLSVersion.TLSv1_2):
            raise Denied('Verified TLS and hostname required')
        began=monotonic();connection=None;body=bytearray();status=None;headers={};complete=False;error=None
        try:
            connection=_SingleDial(binding.host,binding.port,context=context,timeout=min(10,binding.deadline))
            connection.auto_open=False
            connection.connect();stream=connection.sock
            def remaining():
                value=binding.deadline-(monotonic()-began)
                if value<=0:raise TimeoutError('Bounded response deadline')
                stream.settimeout(value)
            remaining()
            policy.validate_packet(binding.packet,datetime.now(timezone.utc),expected_build=build_sha())
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
                value=binding.deadline-(monotonic()-began)
                if value<=0:raise TimeoutError('Bounded response deadline')
                stream.settimeout(value)
                try:chunk=response.read1(min(65536,1048577-len(body)))
                except http.client.IncompleteRead as truncated:
                    body.extend(truncated.partial[:1048577-len(body)]);raise
                if not chunk:break
                body.extend(chunk)
                if len(body)>1048576:raise Denied('Response byte bound')
            if response.length not in (None,0):raise Denied('Truncated response')
            if monotonic()-began>binding.deadline:raise TimeoutError('Late complete response')
            if response.getheader('content-type','').split(';')[0]!='application/json':
                raise Denied('Response media type')
            complete=True
            if binding.crash_before_capture:os._exit(73)
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


# Reuse the exact frozen reservation/INTENT/outcome algorithms, changing only
# the closed transport type. No gold review or historical evaluator is changed.
_context={**q._context,'base':SimpleNamespace(plan=kernel.profile.plan,private_create=kernel.base.private_create,fsync_dir=kernel.base.fsync_dir,FakeTransport=PreparedTransport)}
_core=q.protocol.auth.bind_function(q.protocol.Engine.simulate_one,_context)
_send=q.protocol.auth.bind_function(kernel.AppendEngine.simulate_one,{**vars(kernel),'identity':identity,'SyntheticSend':PreparedTransport,'_simulate':_core})


class PreparedEngine(q.FirstSlotEngine):
    def __init__(self,directory,trust,packet):
        self.packet=deepcopy(packet)
        super().__init__(directory,trust)
    def simulate_one(self,permission,transport,now,*,crash_at=None):
        verify_build();policy.validate_packet(self.packet,datetime.now(timezone.utc),expected_build=build_sha())
        if type(transport)is not PreparedTransport or _BINDINGS.get(transport) is None or _BINDINGS[transport].packet!=self.packet:raise Denied('Exact source-bound enrollment required')
        envelope=q.protocol.auth.parse(permission['envelope'].encode())
        if envelope['data']['slot']!=policy.SLOT:raise Denied('Only first slot')
        with self.lock():
            rows,facts,_,_=self.state()
            if len(rows)!=10 or any(f['kind']=='START' for f in facts):raise Denied('First operation consumed')
        return _send(self,permission,transport,now,crash_at=crash_at)


def lab_transport(port,ca,secret,packet,*,deadline=2,crash=False):
    verify_build();policy.validate_packet(packet,datetime.now(timezone.utc),expected_build=build_sha())
    if packet['writerIdentity']!=json.loads(MANIFEST.read_bytes())['loadedCodeIdentities']['writer'] or packet['credentialIdentity']!=policy.digest(secret.secret_id.encode()):raise Denied('Lab credential/writer mismatch')
    if type(port)is not int or not 1<=port<=65535 or type(secret)is not q.ServerSecretFD or not secret.secret_id.startswith('fictional-') or not 0<deadline<=120:raise Denied('Fictional loopback enrollment only')
    context=ssl.create_default_context(cafile=str(ca));context.minimum_version=ssl.TLSVersion.TLSv1_2
    obj=object.__new__(PreparedTransport);obj.payload=policy.payload()
    _BINDINGS[obj]=_LabBinding('127.0.0.1',port,context,secret,float(deadline),bool(crash),deepcopy(packet))
    return obj


def worker(engine,permission,transport,clock,crash_at):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    directory=engine.directory
    try:
        verify_build();policy.validate_packet(engine.packet,datetime.now(timezone.utc),expected_build=build_sha())
        kernel._once(directory/'generation-worker.json',{'pid':os.getpid(),'parentPID':os.getppid(),'buildSHA256':build_sha(),'loadedCodeIdentities':identities()})
        engine.simulate_one(permission,transport,clock,crash_at=crash_at)
    except Exception as failure:
        original=failure
        while original.__context__ is not None:original=original.__context__
        tb=original.__traceback__
        while tb and tb.tb_next:tb=tb.tb_next
        kernel._once(directory/'generation-refusal.json',{'category':type(original).__name__,'function':tb.tb_frame.f_code.co_name if tb else None,'line':tb.tb_lineno if tb else None})
        raise SystemExit(2) from None


def supervise(engine,permission,transport,clock,*,crash_at=None):
    """Lab-only inherited fictional journal; no real writer can be enrolled."""
    verify_build();policy.validate_packet(engine.packet,datetime.now(timezone.utc),expected_build=build_sha())
    if type(engine)is not PreparedEngine or str(engine.directory)not in kernel.REGISTRY or type(transport)is not PreparedTransport:raise Denied('No real writer enrollment')
    directory=engine.directory
    if _BINDINGS.get(transport) is None or _BINDINGS[transport].packet!=engine.packet:raise Denied('Bound enrollment mismatch')
    # Validate exact request BEFORE reservation and parent claim.
    if transport.payload!=policy.payload() or (transport.provider,transport.method,transport.endpoint)!=('openai','POST','/v1/responses'):raise Denied('Request substitution')
    with engine.lock():
        _,facts,_,_=engine.state()
        expected_operation=q.q1.digest([engine.journal_hash,facts[0]['hash'],11,q.protocol.auth.digest(permission)])
    if engine.packet['operationID']!=expected_operation:raise Denied('Bound execute permission identity')
    before=policy.journal_snapshot(directory)
    kernel._once(directory/'generation-supervisor.json',{'pid':os.getpid(),'buildSHA256':build_sha(),'packetSHA256':policy.stable(engine.packet)})
    p=multiprocessing.get_context('fork').Process(target=worker,args=(engine,permission,transport,clock,crash_at));p.start();p.join(130)
    if p.is_alive():p.kill();p.join()
    # Independent read-only fold; no lower reported usage ever refunds reserve.
    after=policy.journal_snapshot(directory)
    operation=json.loads(after['rows'][10][6])['operation'] if len(after['rows'])==11 else 'none'
    checked=policy.post_append(directory,before,operation)
    with engine.lock():engine.state()
    kernel._once(directory/'generation-terminal.json',{'exit':p.exitcode,'verification':checked,'retryAuthorized':False})
    return checked|{'workerExit':p.exitcode,'sendAuthorized':False}
