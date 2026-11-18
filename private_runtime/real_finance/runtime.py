"""Trusted connection-only adapters for the isolated real financial profile.

No credential discovery, app startup, policy insertion, migration or network send.
Callers supply existing restricted SQL/TLS pools and encrypted evidence ports.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from threading import RLock
from uuid import uuid4
import ast,inspect,json,os,re,secrets
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from experiments.shared_state import application_grants as parent,redis_evidence as evidence
from experiments.shared_state.contracts import Denied,Unavailable,VERSION,digest,types
from experiments.shared_state.evidence_models import canonical,plain,no_credentials,model_types,strict_json,MAX_BYTES
from backend.ai.openai_candidate import request_bytes
from private_runtime.provider_callbacks import count_payload,CountRecord
from .profile import verify,VERSION as PROFILE

_CONTEXT=ContextVar('real_committed_delivery',default=None)

class Connection:
    """Namespace the fixed inherited SQL strings, never alter bound parameters."""
    def __init__(self,cm):self.cm=cm
    def __enter__(self):self.c=self.cm.__enter__();return self
    def __exit__(self,*args):return self.cm.__exit__(*args)
    @property
    def autocommit(self):return self.c.autocommit
    @autocommit.setter
    def autocommit(self,v):self.c.autocommit=v
    def execute(self,query,args=None,**kw):
        if type(query)is not str:raise Denied('real_sql_statement')
        query=query.replace('synthetic_state.','provider_state.').replace('witness.','provider_witness.')
        return self.c.execute(query,args,**kw)

def namespaced(factory):return lambda **kw:Connection(factory(**kw))

def _pack(records,provenance):
    if provenance!='real-source-v1' or type(records)is not dict or not 1<=len(records)<=4 or set(records)-{'request','raw','context','interpretation_result'}:raise Denied('real_source_evidence_only')
    out={}
    for k,v in records.items():
        if type(v)is not model_types()[k]:raise Denied('real_evidence_type')
        out[k]=plain(v);no_credentials(out[k])
    raw=canonical(dict(version='52-real-source-evidence-v1',provenance=provenance,records=out))
    if len(raw)>MAX_BYTES:raise Denied('evidence_capacity')
    return raw

def _unpack(raw):
    value=strict_json(raw)
    if type(value)is not dict or set(value)!={'version','provenance','records'} or value['version']!='52-real-source-evidence-v1':raise Denied('real_evidence_version')
    try:
        records={k:model_types()[k].model_validate_json(canonical(v)) for k,v in value['records'].items()}
        if _pack(records,value['provenance'])!=raw:raise Denied('real_evidence_encoding')
        return records
    except (KeyError,TypeError,ValueError):raise Denied('real_evidence_type') from None

def _methods():
    """Reuse exact reviewed encryption/CAS algorithms with fixed namespace only."""
    verify();tree=ast.parse((Path(__file__).resolve().parents[2]/'experiments/shared_state/redis_evidence.py').read_text())
    original=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EvidenceStore')
    methods=[m for m in original.body if isinstance(m,ast.FunctionDef) and m.name in ('recover','publish','_aad')]
    class Scoped(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value)is str:
                node.value=node.value.replace('synthetic_state.','provider_state.')
                if node.value=='synthetic':node.value='real'
            return node
    cls=ast.ClassDef(name='RealEvidence',bases=[],keywords=[],body=methods,decorator_list=[])
    node=ast.fix_missing_locations(Scoped().visit(ast.Module(body=[cls],type_ignores=[])))
    ns={**vars(evidence),'pack':_pack,'unpack':_unpack,'VERSION':'52-real-source-evidence-v1'}
    exec(compile(node,str(__file__)+':reviewed-evidence','exec'),ns)
    return ns['RealEvidence']
RealEvidence=_methods()

def _send():
    verify();source=(Path(__file__).resolve().parents[2]/'experiments/shared_state/application_grants.py').read_text()
    module=ast.parse(source);original=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='GrantService');fn=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='send')
    # Exact narrow source-binding change, not a substitute financial algorithm.
    text=ast.unparse(fn)
    old="body.get('input') != records['request'].text"
    if text.count(old)!=1:raise Denied('real_send_projection')
    text=text.replace(old,"request_bytes(records['request'].text) != payload")
    ns={**vars(parent),'request_bytes':request_bytes};exec(compile(text,str(__file__)+':reviewed-send','exec'),ns)
    return ns['send']
_send_parent=_send()

class Service(parent.GrantService):
    def __init__(self,witness,issuer):super().__init__(witness,namespaced(issuer))
    def send(self,store,reservation,ordinal,payload,responder):
        token=_CONTEXT.set((store,reservation,ordinal,sha256(payload).hexdigest()))
        try:return _send_parent(self,store,reservation,ordinal,payload,responder)
        except BaseException:
            try:
                with self.witness.serial():self.witness.call('quarantine')
            except (Denied,Unavailable):pass # No retry; full reserved exposure remains.
            raise
        finally:_CONTEXT.reset(token)

class Verifier:
    def __init__(self,issuer,service):self.issuer,self.service=issuer,service
    def authorize(self,store,lease,verb,args):
        if verb not in ('reserve','dispatch') or store._lease(lease)!={k:args[k] for k in ('session','revision','worker','fence')}:raise Denied('evidence_command')
        store.recover(lease);self.service.prepare(store,verb,args)
        _,commitment=store.recover(lease);nonce=secrets.token_hex(32)
        with self.issuer() as c:c.execute('SELECT provider_state.evidence_attest(%s,%s,%s,%s,%s,%s)',(nonce,verb,Jsonb(args),commitment,'real',store.current_epoch()))
        return nonce

class EvidenceNamespace:
    """Reuse the actual hosted Redis TLS/CAS port; isolate this profile's keys."""
    def __init__(self,port):self.port=port;self.keys=port.keys
    def path(self,environment,epoch,sid):
        actual=getattr(getattr(self.port,'c',None),'environment','real')
        if environment not in ('real',actual) or not re.fullmatch('[0-9a-f]{64}',sid):raise Denied('real_evidence_namespace')
        scoped=sha256((PROFILE+'\0'+sid).encode()).hexdigest()
        return self.port.path(actual,epoch,scoped)
    def get(self,path):return self.port.get(path)
    def publish(self,*args):return self.port.publish(*args)
    @property
    def c(self):return self.port.c
    @property
    def client(self):return self.port.client
    def _run(self,*args):return self.port._run(*args)

class Store(RealEvidence,parent.GrantStore):
    def __init__(self,*,connection,issuer,service,evidence,key,limits):
        verify()
        if type(key)is not bytes or len(key)!=32:raise Denied('real_key')
        self.connection,self._issuer=connection,issuer;self.service=service
        self.evidence=EvidenceNamespace(evidence);self.current_epoch=service.witness.epoch;self._verifier=Verifier(issuer,service)
        self._proof=None;self._dispatch_lock=RLock();self._epoch_context=ContextVar('real_transaction_epoch',default=None)
        self._key,self._limits=key,limits;self._pid,self._worker=os.getpid(),str(uuid4());types()
        with self._tx():pass
    @contextmanager
    def _tx(self):
        if os.getpid()!=self._pid:raise Denied('worker_instance')
        epoch=self._epoch_context.set(self.current_epoch())
        try:
            with self.connection(row_factory=dict_row) as c:
                c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
                c.execute("SET LOCAL statement_timeout='1500ms'");c.execute("SET LOCAL lock_timeout='250ms'")
                self._invoke(c,'check',dict(version=VERSION,limits=asdict(self._limits),fingerprint=digest(self._key,'key',VERSION)))
                yield c
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException,psycopg.errors.NoDataFound) as error:
            failure=Denied('real_database_protocol');failure.add_note('sqlstate='+str(error.sqlstate));raise failure from error
        except psycopg.Error:raise Unavailable() from None
        finally:self._epoch_context.reset(epoch)
    def _invoke(self,c,a,p):
        return c.execute('SELECT provider_state.app_protocol(%s,%s,%s,%s,%s) AS result',(a,Jsonb(p),'real',self._epoch_context.get(),self._proof)).fetchone()['result']

class CounterAuthority:
    """Counter-role connections only. Uses SAME witness prefix/claims, no new ledger."""
    def __init__(self,connection,witness,project):
        if type(witness)is not CounterWitness:raise Denied('counter_role_witness_required')
        self.connection,self.witness,self.project=connection,witness,project;self._operations={}
    def _call(self,fn,args):
        allowed={'real_count_quote':4,'real_count_phase':2,'real_count_commit':3,'real_count_finish':2,'real_counter_observed':0}
        if fn not in allowed or len(args)!=allowed[fn]:raise Denied('real_counter_method')
        try:
            with self.connection() as c:return c.execute('SELECT provider_state.'+fn+'('+','.join(['%s']*len(args))+')',args).fetchone()[0]
        except psycopg.OperationalError:raise Unavailable() from None
        except psycopg.Error as error:
            denied=Denied('real_counter_sql');denied.add_note('sqlstate='+str(error.sqlstate));raise denied from error
    def observed(self):return self._call('real_counter_observed',())
    def sync(self):return self.witness.call('confirm',observed=self.observed())
    def begin(self,capability,wire,projection_digest,project):
        if project!=self.project or projection_digest!=sha256(count_payload(wire)).hexdigest():raise Denied('real_counter_scope')
        w=self.witness;op=str(uuid4())
        with w.serial():
            try:
                self.sync();q=self._call('real_count_quote',(capability,wire,count_payload(wire),op))
                if q['account']!=project:raise Denied('real_counter_account')
                for phase in ('reserve','dispatch','deliver'):
                    params=dict(id=phase+':'+op+('' if phase=='reserve' else ':1'),quote=q,observed=self.observed())
                    if phase!='reserve':params['ordinal']=1
                    w.call(phase,**params)
                    self._call('real_count_phase',(op,phase));self.sync()
                self._operations[op]=q;return op
            except BaseException:
                try:
                    if w.call('status')['pending']:w.call('quarantine')
                except (Denied,Unavailable):pass
                raise
    def commit(self,op,record,raw):
        q=self._operations[op]
        if type(record)is not CountRecord or record.generation_sha256!=q['lines'][0]['request_digest'] or record.count_sha256!=q['lines'][0]['count_digest'] or record.raw_response_sha256!=raw.digest:raise Denied('real_count_record')
        with self.witness.serial():
            self._call('real_count_commit',(op,record.tokens,raw.body));self._finish(op,'SUCCEEDED')
    def _finish(self,op,state):
        self._call('real_count_finish',(op,state))
        self.witness.call('outcome',operation=op,state=state,observed=self.observed());self.sync()
        if state=='UNCERTAIN':self.witness.call('quarantine')
    def uncertain(self,op):
        with self.witness.serial():
            try:self._finish(op,'UNCERTAIN')
            finally:self.witness.call('quarantine')

class CounterWitness(parent.Witness):
    def epoch(self):return self.call('epoch')['epoch']
    def call(self,a,**p):
        try:
            with self.serial():r=self._active.get().execute('SELECT provider_witness.counter_protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException,psycopg.errors.NoDataFound):raise Denied('real_counter_witness') from None
        except psycopg.Error:raise Unavailable() from None
        if 'denied' in r:raise Denied('grant_quarantined_or_stopped')
        return r

class Accounting:
    profile=PROFILE
    def __init__(self):self._receipt=ContextVar("real_price_receipt",default=None)
    def require(self,wire):
        active=_CONTEXT.get()
        if active is None:raise Denied('real_delivery_context')
        store,reservation,ordinal,h=active
        if sha256(wire).hexdigest()!=h:raise Denied('real_payload_substitution')
        store.recover(reservation.lease)
        args=dict(**store._lease(reservation.lease),capability=store._hash(reservation.capability.token,'cap'),operation=reservation.operation,ordinal=ordinal,payload_digest=h)
        with store._tx() as c:
            receipt=c.execute('SELECT provider_state.real_accounting(%s) AS receipt',(Jsonb(args),)).fetchone()['receipt']
        r,q,line,amount=[receipt[k] for k in ('rates','quote','line','amount')]
        self._receipt.set((wire,r,q,line,amount))
        # This is a read-only projection of protected SQL, not unsigned enrollment.
        return dict(policy=dict(provider='google' if line['kind']=='maps' else 'openai',account=q['account']),count=None,reservedMicroUSD=amount)
    def bound(self,wire,enrolled,now):
        from backend.provider_enrollment_review import ReviewBound
        if _CONTEXT.get() is None or self._receipt.get() is None or self._receipt.get()[0]!=wire:raise Denied('real_quote_context')
        _,r,q,line,amount=self._receipt.get();self._receipt.set(None)
        if enrolled!=dict(policy=dict(provider='google' if line['kind']=='maps' else 'openai',account=q['account']),count=None,reservedMicroUSD=amount):raise Denied('real_quote_substitution')
        return ReviewBound(enrolled['policy']['provider'],sha256(wire).hexdigest(),r['version'],line.get('input_tokens',line.get('units')),amount,line.get('model',line.get('sku')))

class GoogleWorkloadExchange:
    """Fixed account of the existing Google transport; no project/endpoint override."""
    from backend.places import PROJECT as account
    def __init__(self,token_provider):
        from backend.provider_responses import GoogleHTTPExchange
        self._exchange=GoogleHTTPExchange(token_provider)
    def __call__(self,*args):return self._exchange(*args)
