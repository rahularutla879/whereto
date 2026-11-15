"""Unenrolled first-slot OpenAI wire implementation; loopback fixtures only today.

No real credential loader/enrollment issuer, account probes, retries or live CLI.
Reuse the pinned Q4C transition kernel. No original-journal writable constructor.
"""
from base64 import b64decode,b64encode
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
import http.client
import fcntl
import ipaddress
import json
import os
import socket
import ssl
import stat
from time import monotonic
from types import SimpleNamespace
from weakref import WeakKeyDictionary

from scripts import task52b_execution_boundary as kernel
from scripts import task52b_execution_identity as parent_identity
from scripts import task52b_first_slot_identity as identity
from scripts import task52_diag_protocol as protocol
from scripts import task52_real_integration as existing
from scripts import task52_q1 as q1

VERSION='52b-first-slot-https-preparation-v1'
MODEL='gpt-6-luna'
SLOT=['openai','extension-repeated',2]
PAYLOAD_SHA='5c2ad0aa457ae84497f489a1ca155ce805c8f160fd5260f59e0a4a3e8a078c02'
ENDPOINT='https://api.openai.com/v1/responses'
Denied=kernel.Denied
_BINDINGS=WeakKeyDictionary()


def operational_enrollment(_packet=None):
    # No configuration, browser header or unsigned approval can open real state.
    raise Denied('Operational enrollment unavailable; purpose/security/readiness/financial approval required')


def quote(counted_input,input_nano,output_nano,fees_nano):
    """Pure conditional arithmetic, not pricing evidence or spending permission.

    Rates are worst-case applicable integer nanodollars/token, including cache
    writes/reasoning as applicable. Unknown categories/fees must stay unknown.
    """
    values=(counted_input,input_nano,output_nano,fees_nano)
    if any(type(n)is not int or n<0 for n in values) or counted_input==0:
        raise Denied('Exact count/rates/fees unavailable')
    bound=counted_input+2048
    if bound>12000:raise Denied('Original input cap')
    maximum=bound*input_nano+2000*output_nano+fees_nano
    if maximum>2500000:raise Denied('Conditional single-operation ceiling exceeded')
    return {'inputBound':bound,'maxOutputTokens':2000,'calculatedNanodollars':maximum,
            'reservationNanodollars':2500000,'approved':False}


class ServerSecretFD:
    """Server-owned read-only descriptor, not a browser/env-selected file path.

    Future real use requires separately reviewed enrollment. Tests use only a
    private fictional secret; no repository credential file is opened here.
    """
    def __init__(self,fd,secret_id):
        if type(secret_id)is not str or not secret_id.startswith('fictional-') or len(secret_id)>100:
            raise Denied('Unenrolled credential identity')
        self.fd=fd;self.secret_id=secret_id;self.reads=0
    def read(self):
        st=os.fstat(self.fd)
        if (fcntl.fcntl(self.fd,fcntl.F_GETFL)&os.O_ACCMODE!=os.O_RDONLY or not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o600 or
                st.st_uid!=os.getuid() or st.st_nlink!=1):raise Denied('Private server secret descriptor required')
        # pread preserves descriptor position and never writes/duplicates a key.
        raw=os.pread(self.fd,4097,0)
        if not 16<=len(raw)<=4096 or not raw.isascii() or any(c<=32 or c>=127 for c in raw):
            raise Denied('Secret format refused')
        self.reads+=1
        return raw.decode('ascii')


@dataclass(frozen=True)
class _LocalBinding:
    host:str
    port:int
    context:ssl.SSLContext
    secret:ServerSecretFD
    deadline:float
    crash_before_capture:bool


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


def _capture_binding(directory,operation):
    return {name:q1.sha((directory/f'{name}-{operation}.json').read_bytes())
            for name in ('raw','http','http-intent','dispatch')}


def _project(raw,status,binding):
    value=kernel._json(raw)
    if type(value)is not dict or '_http_status' in value or '_task52_http_evidence' in value:raise Denied('Provider JSON envelope refused')
    # HTTP metadata is decoder input, not a modification of preserved raw bytes.
    result=deepcopy(value)
    result['_task52_http_evidence']=deepcopy(binding)
    if status!=200:result['_http_status']=status
    elif value.get('model')!=MODEL:raise Denied('Response model mismatch')
    return result


class OpenAIResponsesTransport:
    provider='openai';method='POST';endpoint='/v1/responses'
    def __init__(self,enrollment=None,*,credential=None):
        operational_enrollment(enrollment)  # Before credential read or networking.

    def exchange(self,directory,operation,payload_hash):
        identity.verify()
        binding=_BINDINGS.get(self)
        if binding is None or str(directory) not in kernel.REGISTRY:
            raise Denied('No reviewed operational enrollment; closed local fixture required')
        payload=identity.first_request()  # Immutable local bytes; never reread mutable caller state.
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
        # The loopback gate never accepts a real API key or a remote peer.
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
            connection.request('POST','/v1/responses',payload,{
                'Authorization':'Bearer '+key,'Content-Type':'application/json',
                'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'})
            remaining();response=connection.getresponse();status=response.status
            headers={name:response.getheader(name) for name in ('content-type','content-length','x-request-id')
                     if response.getheader(name)is not None}
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
            kernel._once(directory/f'raw-{operation}.json',{'bytesBase64':b64encode(bytes(body)).decode(),
                'sha256':q1.sha(bytes(body))})
            kernel._once(directory/f'http-{operation}.json',{'status':status,'headers':headers,
                'complete':complete,'errorCategory':error,'rawSHA256':q1.sha(bytes(body))})
        if not complete:raise Denied('Uncertain/incomplete HTTPS operation; retained, no retry')
        value=_project(bytes(body),status,_capture_binding(directory,operation))
        content,usage,stop=kernel.decoder.Adapter('openai',None).decode(value)
        kernel._once(directory/f'decoded-{operation}.json',{'rawSHA256':q1.sha(bytes(body)),
            'responseHash':q1.digest(value),'content':content,'usage':usage,'status':stop})
        return value


def sqlite_connect(directory):
    import sqlite3
    db=sqlite3.connect(f'file:{directory}/journal.sqlite?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON');return db


def local_fixture_transport(port,ca_file,secret,*,deadline=2,crash_before_capture=False):
    """Only test bootstrap. It cannot select a remote address or OpenAI peer."""
    identity.verify()
    if (type(port)is not int or not 1<=port<=65535 or type(secret)is not ServerSecretFD or
            type(deadline)not in (int,float) or not 0<deadline<=120 or type(crash_before_capture)is not bool):
        raise Denied('Local fixture limits')
    context=ssl.create_default_context(cafile=str(ca_file));context.minimum_version=ssl.TLSVersion.TLSv1_2
    instance=object.__new__(OpenAIResponsesTransport);instance.payload=identity.first_request()
    _BINDINGS[instance]=_LocalBinding('127.0.0.1',port,context,secret,float(deadline),crash_before_capture)
    return instance


_context={**kernel._context,'base':SimpleNamespace(plan=kernel.profile.plan,
    private_create=kernel.base.private_create,fsync_dir=kernel.base.fsync_dir,FakeTransport=OpenAIResponsesTransport)}
_core_send=protocol.auth.bind_function(protocol.Engine.simulate_one,_context)
_context_send={**vars(kernel),'identity':identity,'SyntheticSend':OpenAIResponsesTransport,'_simulate':_core_send}
_send=protocol.auth.bind_function(kernel.AppendEngine.simulate_one,_context_send)


class FirstSlotEngine(kernel.AppendEngine):
    def check(self):identity.verify();return super().check()
    def state(self):
        rows,facts,total,child=existing._AppendEngine.state(self)
        if len(rows)>11:raise Denied('First slot only')
        for outcome in (f for f in facts if f['kind']=='OUTCOME'):
            op=outcome['operation']
            try:
                raw=json.loads((self.directory/f'raw-{op}.json').read_bytes())
                metadata=json.loads((self.directory/f'http-{op}.json').read_bytes())
                intent=json.loads((self.directory/f'http-intent-{op}.json').read_bytes())
                dispatch=json.loads((self.directory/f'dispatch-{op}.json').read_bytes())
                durable_intent=next(f for f in facts if f['kind']=='INTENT' and f['operation']==op)
                original=b64decode(raw['bytesBase64'],validate=True)
                projected=_project(original,metadata['status'],_capture_binding(self.directory,op))
                decoded=json.loads((self.directory/f'decoded-{op}.json').read_bytes())
                grading=json.loads((self.directory/f'grading-{op}.json').read_bytes())
                content,usage,stop=kernel.decoder.Adapter('openai',None).decode(projected)
                if (not metadata['complete'] or metadata['errorCategory'] is not None or
                        intent['build']!=identity.MANIFEST_SHA or intent['payloadHash']!=PAYLOAD_SHA or
                        intent['operation']!=op or intent['endpoint']!=ENDPOINT or
                        dispatch!={'version':kernel.VERSION,'build':parent_identity.MANIFEST_SHA,'operation':op,
                                  'payloadHash':PAYLOAD_SHA,'intentHash':durable_intent['hash'],'syntheticOnly':True} or
                        q1.sha(original)!=raw['sha256'] or metadata['rawSHA256']!=raw['sha256'] or
                        projected!=outcome['data']['response'] or
                        decoded!={'rawSHA256':raw['sha256'],'responseHash':q1.digest(projected),
                                  'content':content,'usage':list(usage) if usage else None,'status':stop} or
                        grading!={'outcomeHash':outcome['hash'],'assessment':outcome['data']['assessment']}):
                    raise Denied('HTTP capture/decoding/grading mismatch')
            except (OSError,ValueError,TypeError,KeyError):raise Denied('Incomplete immutable HTTP evidence') from None
        return rows,facts,total,child
    def simulate_one(self,permission,transport,now,*,crash_at=None):
        with self.lock():
            rows,facts,_,_=self.state()
            if len(rows)!=10 or any(f['kind']=='START' for f in facts):raise Denied('First operation already consumed')
        envelope=protocol.auth.parse(permission['envelope'].encode())
        if envelope['data']['slot']!=SLOT:raise Denied('No other slot authorization')
        return _send(self,permission,transport,now,crash_at=crash_at)
