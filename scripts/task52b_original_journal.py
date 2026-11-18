"""Narrow original-journal resource port around unchanged Q4C algorithms.

The canonical experiment lock protects BOTH the existing SQL journal and the
separate child facts. No replacement lock, financial ledger or history update.
Real entry requires source-enrolled public trust; tests use a full prefix COPY.
"""
from contextlib import contextmanager,closing
from pathlib import Path
from types import SimpleNamespace
from threading import get_ident
import fcntl,json,os,sqlite3,sys,multiprocessing,resource
from scripts import task52b_real_enrollment as enrollment
from scripts import task52b_generation_candidate as parent
from scripts import task52b_generation_policy as policy
from scripts import task52b_code_identity as identity
from scripts import task52_real_integration as integration

Denied=enrollment.Denied
ROOT=policy.ROOT
MANIFEST=ROOT/'docs/task52b-original-enrollment-build-v1.json'
PREFIX='88a8f112f918f28fac185f76b08a5226aa2daa52b7b094206b7272d8b2487a5f'
METADATA='eb04c8d1ae644022ad340ec0d08c1f4db960d01f45b8c52288df0f27059afad5'
REGISTRY={}
core=parent.q.protocol.Engine


def build_sha():return policy.digest(MANIFEST.read_bytes())


def targets():
    from scripts import task52b_enrolled_transport as wire
    modules=(sys.modules[__name__],enrollment,wire)
    from types import FunctionType
    result={}
    for module in modules:
        for name,value in vars(module).items():
            if type(value)is FunctionType and value.__module__==module.__name__:
                result[module.__name__+'.'+name]=(value,module.__dict__,Path(module.__file__),name)
            elif isinstance(value,type) and value.__module__==module.__name__:
                for method,fn in vars(value).items():
                    if isinstance(fn,property):fn=fn.fget
                    if hasattr(fn,'__wrapped__'):fn=fn.__wrapped__
                    if type(fn)is FunctionType and fn.__module__==module.__name__ and fn.__code__.co_filename==module.__file__:result[module.__name__+'.'+name+'.'+method]=(fn,module.__dict__,Path(module.__file__),name+'.'+method)
    return result


def verify_build():
    b=json.loads(MANIFEST.read_bytes())
    for name,h in b['filesSHA256'].items():
        path=ROOT/name
        if path.is_symlink() or policy.digest(path.read_bytes())!=h:raise Denied('Original adapter source mismatch')
    if policy.digest(Path(sys.executable).resolve().read_bytes())!=b['pythonExecutableSHA256']:raise Denied('Original adapter interpreter')
    actual={n:identity.require(fn,path,b['filesSHA256'][str(path.relative_to(ROOT))],qual,ns) for n,(fn,ns,path,qual) in targets().items()}
    if actual!=b['loadedCodeIdentities']:raise Denied('Original adapter loaded identities')
    from scripts import task52b_enrolled_transport as wire
    if wire._SingleDial is not parent._SingleDial or wire._project is not parent._project or wire._capture_binding is not parent._capture_binding or wire.kernel is not parent.kernel:raise Denied('Reviewed transport dependency binding')
    for fn,original in ((_append,core.append),(_state,core.state),(_activate,core.activate_synthetic_scope)):
        if fn.__code__ is not original.__code__ or fn.__globals__ is not _context:raise Denied('Frozen Q4C algorithm binding')
    if OriginalEngine.append is not _append or set(_context)!=set(parent.q.protocol._context) or any(_context[k] is not v for k,v in parent.q.protocol._context.items() if k!='REGISTRY') or _context['REGISTRY'] is not REGISTRY:raise Denied('Frozen Q4C dependency namespace')
    parent.verify_build()  # Full historical/source guards retained, never cached.
    return b


def snapshot_held(receipt):
    """Caller holds the enrolled canonical lock, including the independent reader."""
    with closing(sqlite3.connect('file:'+str(receipt.journal)+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        rows=db.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall()
        meta=db.execute('SELECT id,config FROM metadata').fetchall()
    if policy.stable(rows[:10])!=PREFIX or policy.stable(meta)!=METADATA or len(rows)not in (10,11):raise Denied('Original historical prefix/metadata mismatch')
    return rows,meta


class JournalSQL(integration._JournalSQL):
    def __init__(self,connection,require_lock,receipt,engine):
        integration._JournalSQL.__init__(self,connection,require_lock);self.receipt=receipt;self.engine=engine
    def execute(self,statement,parameters=()):
        if statement==integration._APPEND:
            starts=[json.loads(enrollment.private(p)) for p in sorted(self.receipt.facts.glob('fact-*')) if json.loads(enrollment.private(p))['kind']=='START']
            if len(starts)!=1 or starts[0]['data']['rowid']!=11:raise Denied('Reservation requires exact durable START')
            slot=parent.kernel.profile.plan()['slots'][0]
            if tuple(parameters)!=(*policy.SLOT,'reserved_uncertain',policy.CEILING,self.engine.record(starts[0],slot)):raise Denied('Reservation differs from signed START')
        return integration._JournalSQL.execute(self,statement,parameters)
    def commit(self):
        integration._JournalSQL.commit(self);parent.kernel.base.fsync_dir(self.receipt.journal.parent)


class OriginalEngine(core):
    def __init__(self,receipt):
        if type(receipt)is not enrollment.Enrollment:raise Denied('Exact signed enrollment required')
        self.receipt=receipt;self.directory=receipt.facts;self._held=None
        receipt.guard();enrollment.directory(self.directory)
        self.marker=receipt.binding['marker'];self.journal_hash=receipt.journal_hash
        REGISTRY[str(self.directory)]=policy.stable(self.marker)
        with self.lock():self.state()
    def check(self):
        self.receipt.guard(active=False)
        if self.directory!=self.receipt.facts or REGISTRY.get(str(self.directory))!=policy.stable(self.marker):raise Denied('Child store binding')
        for path in self.directory.iterdir():enrollment.file_identity(path)
        return self.marker
    @contextmanager
    def lock(self):
        self.check();receipt=self.receipt;fd=os.open(receipt.lock,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            if [os.fstat(fd).st_dev,os.fstat(fd).st_ino]!=receipt.binding['lockIdentity']:raise Denied('Changed lock inode')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Denied('Concurrent original operator') from None
            self._held=(os.getpid(),get_ident(),object())
            try:yield
            finally:self._held=None;fcntl.flock(fd,fcntl.LOCK_UN)
        finally:os.close(fd)
    def db(self):
        held=self._held
        def require():
            if held is None or self._held is not held or held[:2]!=(os.getpid(),get_ident()):raise Denied('Original lock required for SQL')
            if enrollment.file_identity(self.receipt.journal)!=self.receipt.binding['journalIdentity']:raise Denied('Changed journal inode')
        require()
        db=sqlite3.connect('file:'+str(self.receipt.journal)+'?mode=rw',uri=True)
        db.execute('PRAGMA synchronous=FULL');require()
        return JournalSQL(db,require,self.receipt,self)
    def signed(self,packet,role,at):return self.receipt.signed(packet,role,at)
    def record(self,start,slot):
        return json.dumps({'version':enrollment.VERSION,'operation':start['operation'],'startHash':start['hash'],'slot':slot['slot'],'payloadHash':slot['payloadHash'],'enrollmentHash':self.receipt.binding_hash,'epoch':self.receipt.trust['epoch']},sort_keys=True)
    def state(self):
        self.check();snapshot_held(self.receipt)
        rows,facts,total,extra=_state(self)
        if len(rows)>11 or len([f for f in facts if f['kind']=='START'])>1 or any(f['kind']=='REVIEW' for f in facts):raise Denied('Technical diagnostic cannot progress/review')
        return rows,facts,total,extra
    def activate_scope(self):
        self.receipt.guard()
        authority=self.receipt.authority();path=self.directory/f'authority-seen-{authority["sequence"]}.json'
        if not path.exists():parent.kernel._once(path,authority)
        return _activate(self,{k:self.receipt.package['packets'][k] for k in enrollment.ROLES if k!='execute'},enrollment.now())
    def simulate_one(self,permission,transport,at=None,*,crash_at=None):
        from scripts import task52b_enrolled_transport as wire
        self.receipt.guard()
        if type(transport)is not wire.EnrolledTransport or wire.binding(transport).receipt!=self.receipt:raise Denied('Enrolled transport only')
        if permission!=self.receipt.package['packets']['execute']:raise Denied('Exact signed execute permission')
        with self.lock():
            rows,facts,_,_=self.state()
            if len(rows)!=10 or any(f['kind']=='START' for f in facts):raise Denied('Consumed diagnostic; never retry')
        return _send(self,permission,transport,enrollment.now(),crash_at=crash_at)
    def record_review(self,*args,**kwargs):raise Denied('Semantic review deferred; no next slot')


# Rebind ONLY resource registry / exact transport type. Code objects for Q4C's
# financial admission, START, SQL reservation, INTENT, assessment and HALT stay
# byte-identical to the independently source-verified frozen evaluator.
_context={**parent.q.protocol._context,'REGISTRY':REGISTRY}
_append=parent.q.protocol.auth.bind_function(core.append,_context)
_state=parent.q.protocol.auth.bind_function(core.state,_context)
_activate=parent.q.protocol.auth.bind_function(core.activate_synthetic_scope,_context)
OriginalEngine.append=_append


def _send(*args,**kwargs):return bind_send()(*args,**kwargs)


def bind_send():
    from scripts import task52b_enrolled_transport as wire
    context={**_context,'base':SimpleNamespace(plan=parent.kernel.profile.plan,private_create=parent.kernel.base.private_create,fsync_dir=parent.kernel.base.fsync_dir,FakeTransport=wire.EnrolledTransport)}
    return parent.q.protocol.auth.bind_function(core.simulate_one,context)


def independent_verify(engine):
    """Separate lock acquisition + full signed fold after the worker exits."""
    replacement=OriginalEngine(engine.receipt)
    with replacement.lock():
        rows,facts,total,extra=replacement.state()
        from scripts import task52b_enrolled_transport as wire
        wire.verify_captures(replacement,rows,facts)
        return {'historicalPrefixUnchanged':True,'metadataUnchanged':True,'historicalHaltPreserved':rows[9][4]=='recorded_halted','rows':len(rows),'exposureNanodollars':total,'childExposureNanodollars':extra,'factKinds':[f['kind'] for f in facts],'planningAuthorized':False,'semanticReview':'deferred'}


def worker(engine,transport,crash):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        engine.receipt.guard()
        parent.kernel._once(engine.directory/'worker.json',{'pid':os.getpid(),'parent':os.getppid(),'build':build_sha()})
        engine.simulate_one(engine.receipt.package['packets']['execute'],transport,crash_at=crash)
    except Exception as failure:
        original=failure
        while original.__context__ is not None:original=original.__context__
        tb=original.__traceback__
        while tb and tb.tb_next:tb=tb.tb_next
        parent.kernel._once(engine.directory/'refusal.json',{'category':type(original).__name__,'function':tb.tb_frame.f_code.co_name if tb else None,'line':tb.tb_lineno if tb else None})
        raise SystemExit(2) from None


def supervise(engine,transport,*,crash=None):
    from scripts import task52b_enrolled_transport as wire
    verify_build();engine.receipt.guard()
    if type(engine)is not OriginalEngine or type(transport)is not wire.EnrolledTransport or wire.binding(transport).receipt!=engine.receipt:raise Denied('Exact supervised enrollment')
    with engine.lock():
        _,facts,_,_=engine.state()
        if not facts or facts[0]['kind']!='SCOPE' or any(f['kind']=='START' for f in facts):raise Denied('Consumed/missing scope')
        operation=parent.q1.digest([engine.journal_hash,facts[0]['hash'],11,enrollment.core.digest(engine.receipt.package['packets']['execute'])])
        parent.kernel._once(engine.directory/'supervisor.json',{'pid':os.getpid(),'build':build_sha(),'operation':operation,'enrollment':engine.receipt.binding_hash})
    child=multiprocessing.get_context('fork').Process(target=worker,args=(engine,transport,crash))
    try:
        child.start();child.join(130)
        if child.is_alive():child.kill();child.join()
    except BaseException:
        if child.pid and child.is_alive():child.kill();child.join()
        raise
    report=independent_verify(engine);report['workerExit']=child.exitcode
    parent.kernel._once(engine.directory/'post-append.json',report)
    return report
