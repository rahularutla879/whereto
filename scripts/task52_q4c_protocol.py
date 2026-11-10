"""Signed Q4C continuation over exact-schema SYNTHETIC databases only.

No real-path writer, signing utility, credentials, HTTP or live activation.
Fixture registry is a test containment boundary, not independent OS authority.
"""
from contextlib import closing, contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from scripts import task52_q1 as q1
from scripts import task52_q4a as base
from scripts.task52_q4b import DDL
from scripts import task52_q4c_auth as auth
from scripts.task52_q4a_scoring import assess

VERSION='52b-q4c-signed-real-schema-OFFLINE-v1'
REGISTRY={}
KINDS={'SCOPE','START','INTENT','OUTCOME','REVIEW','HALT'}
CRASHES={'before_start','before_reserve','before_commit','after_reserve','after_intent','after_send','after_outcome'}


def utc(now):return now.strftime('%Y-%m-%dT%H:%M:%SZ')


def die(point,selected):
    if point==selected:os._exit(73)


def admission(total,provider,exposure,child_attempts,child_exposure):
    values=(total,provider,exposure,child_attempts,child_exposure)
    if any(type(n)is not int or n<0 for n in values):raise auth.Denied('Invalid accounting')
    if total>=594 or provider>=198 or child_attempts>=5 or exposure+2500000>12000000000 or child_exposure+2500000>12500000:
        raise auth.Denied('Original/child attempt or exposure cap')


class SyntheticJournal:
    """Factory-only new fictional DB, never a copy or replacement paid journal."""
    def __init__(self,trust,*,base_charge=1000000):
        from scripts.task52_q4c_identity import verify_build
        verify_build(full=True);trust.checked()
        if type(base_charge)is not int or not 0<=base_charge<=12000000000:raise auth.Denied('Synthetic charge')
        self.temp=tempfile.TemporaryDirectory(prefix='whereto-q4c-fictional-')
        self.directory=Path(self.temp.name).resolve();os.chmod(self.directory,0o700)
        self.trust=trust
        with closing(sqlite3.connect(self.directory/'journal.sqlite')) as db:
            db.execute('PRAGMA synchronous=FULL')
            for sql in DDL.values():db.execute(sql)
            root=json.dumps({'FICTIONAL':True,'purpose':VERSION,'nonce':uuid.uuid4().hex})
            db.execute('INSERT INTO metadata VALUES(1,?)',(root,))
            for i,a in enumerate(base.plan()['baseline']['rows']):
                db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(*a['slot'],
                    'recorded_halted' if i==9 else 'recorded',base_charge,json.dumps({'FICTIONAL':True,'n':i})))
            db.commit();rows=db.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall()
        os.chmod(self.directory/'journal.sqlite',0o600)
        self.scope=uuid.uuid4().hex+uuid.uuid4().hex
        marker={'identity':VERSION,'root':q1.digest(root),'prefix':[q1.digest(r) for r in rows],
                'scope':self.scope,'trustHash':trust.document_hash,'revocationHash':trust.revocation_hash}
        base.private_create(self.directory/'fixture.json',marker)
        base.private_create(self.directory/'experiment.lock',{'FICTIONAL':True})
        REGISTRY[str(self.directory)]=q1.digest(marker)
        self.journal_hash=q1.digest({'root':marker['root'],'prefix':marker['prefix']})

    def engine(self):return Engine(self.directory,self.trust)

    def close(self):REGISTRY.pop(str(self.directory),None);self.temp.cleanup()


class Engine:
    def __init__(self,directory,trust):
        self.directory=Path(directory);self.trust=trust;self.marker=self.check()
        self.journal_hash=q1.digest({'root':self.marker['root'],'prefix':self.marker['prefix']})

    def check(self):
        d=self.directory
        if str(d)not in REGISTRY or d.resolve()!=d or not d.name.startswith('whereto-q4c-fictional-'):
            raise auth.Denied('Registered synthetic state only')
        if any(p.is_symlink() or (p.is_file() and p.stat().st_nlink!=1) for p in d.iterdir()):raise auth.Denied('Linked state refused')
        m=json.loads((d/'fixture.json').read_text())
        if q1.digest(m)!=REGISTRY[str(d)] or type(self.trust)is not auth.Trust:
            raise auth.Denied('Synthetic marker/trust mismatch')
        if (m['trustHash'],m['revocationHash'])!=(self.trust.document_hash,self.trust.revocation_hash):raise auth.Denied('Unenrolled trust')
        return m

    @contextmanager
    def lock(self):
        self.check()
        with (self.directory/'experiment.lock').open('rb') as fd:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise auth.Denied('Concurrent operator') from None
            try:yield
            finally:fcntl.flock(fd,fcntl.LOCK_UN)

    def db(self):
        self.check();db=sqlite3.connect(f'file:{self.directory}/journal.sqlite?mode=rw',uri=True)
        db.execute('PRAGMA synchronous=FULL');return db

    def signed(self,packet,role,now):
        verified=auth.verify(packet,role,self.trust,now);e=auth.parse(verified.envelope)
        auth.exact([e['scope'],e['journal']],[self.marker['scope'],self.journal_hash])
        return e,verified.packet_hash

    def append(self,kind,op,data,facts,now):
        value={'kind':kind,'operation':op,'data':deepcopy(data),'checkedAt':utc(now),
               'previous':facts[-1]['hash'] if facts else REGISTRY[str(self.directory)]}
        value['hash']=q1.digest(value)
        if len(json.dumps(value).encode())>1048576:raise auth.Denied('Fact size')
        base.private_create(self.directory/f'fact-{len(facts)+1:04d}.json',value);facts.append(value)
        return value

    def state(self):
        from scripts.task52_q4c_identity import verify_build
        verify_build();self.check()
        with closing(self.db()) as db:
            if db.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise auth.Denied('DB integrity')
            schema=dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall())
            if schema!=DDL or len(db.execute('SELECT * FROM sqlite_master').fetchall())!=3:raise auth.Denied('Exact historical SQL schema')
            rows=db.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall()
            meta=db.execute('SELECT id,config FROM metadata').fetchall()
        if len(meta)!=1 or meta[0][0]!=1 or q1.digest(meta[0][1])!=self.marker['root'] or [q1.digest(r) for r in rows[:10]]!=self.marker['prefix']:
            raise auth.Denied('Historical prefix/root edited or missing')
        corpus=json.loads((q1.ROOT/'docs/task52-evaluation-corpus.json').read_text());ids={c['id'] for c in corpus['cases']}
        for n,r in enumerate(rows,1):
            if (r[0]!=n or r[1]not in ('openai','google','anthropic') or r[2]not in ids or type(r[3])is not int or r[3]not in (1,2,3)
                or r[4]not in ('recorded','recorded_halted','reserved_uncertain') or type(r[5])is not int or r[5]<0):
                raise auth.Denied('Invalid row/identity/status/charge')
        if rows[9][4]!='recorded_halted' or len({tuple(r[1:4]) for r in rows})!=len(rows):raise auth.Denied('Halt or slot uniqueness')
        paths=sorted(self.directory.glob('fact-*'));facts=[];previous=REGISTRY[str(self.directory)]
        if len(paths)>32:raise auth.Denied('Fact count')
        for i,path in enumerate(paths,1):
            raw=path.read_bytes()
            if len(raw)>1048576:raise auth.Denied('Fact size')
            f=json.loads(raw)
            if (path.name!=f'fact-{i:04d}.json' or set(f)!={'kind','operation','data','checkedAt','previous','hash'}
                or f['kind']not in KINDS or f['previous']!=previous or f['hash']!=q1.digest({k:v for k,v in f.items() if k!='hash'})
                or raw!=json.dumps(f,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()):raise auth.Denied('Corrupt fact chain')
            facts.append(f);previous=f['hash']
        scopes=[f for f in facts if f['kind']=='SCOPE'];starts=[f for f in facts if f['kind']=='START'];nonces=set()
        def check_packet(packet,role,f):
            e,h=self.signed(packet,role,auth.stamp(f['checkedAt']))
            if e['nonce']in nonces:raise auth.Denied('Replayed permission nonce')
            nonces.add(e['nonce']);return e,h
        if scopes:
            if len(scopes)!=1 or facts[0]!=scopes[0]:raise auth.Denied('Duplicate/conflicting scope')
            self.scope_packets(scopes[0]['data'],auth.stamp(scopes[0]['checkedAt']))
            for role,packet in scopes[0]['data'].items():check_packet(packet,role,scopes[0])
        if len(starts)>5 or len(rows)>10+len(starts) or any(f['kind']=='HALT' for f in facts[:-1]):raise auth.Denied('Orphan/extra/halted operations')
        for i,start in enumerate(starts):
            if not scopes:raise auth.Denied('No signed child scope')
            auth.fields(start['data'],'permission rowid')
            e,permission_hash=check_packet(start['data']['permission'],'execute',start);slot=base.plan()['slots'][i]
            self.execute_binding(e['data'],scopes[0]['data'],facts,start_index=facts.index(start))
            if start['data']['rowid']!=11+i or e['data']['slot']!=slot['slot']:
                raise auth.Denied('Wrong operation slot/rowid')
            op=q1.digest([self.journal_hash,scopes[0]['hash'],11+i,permission_hash])
            if start['operation']!=op:raise auth.Denied('Operation identity')
            group=[f for f in facts if f['operation']==op and f['kind']!='HALT'];k=[f['kind'] for f in group]
            if k not in (['START'],['START','INTENT'],['START','INTENT','OUTCOME'],['START','INTENT','OUTCOME','REVIEW']):raise auth.Denied('Operation grammar')
            if len(rows)>10+i:
                r=rows[10+i]
                if list(r[1:4])!=slot['slot'] or r[4:6]!=('reserved_uncertain',2500000) or r[6]!=self.record(start,slot):raise auth.Denied('Immutable reservation mismatch')
            elif len(k)>1:raise auth.Denied('Intent without reservation')
            if len(k)>1 and group[1]['data']!={'startHash':start['hash'],'payloadHash':slot['payloadHash']}:raise auth.Denied('Intent mismatch')
            if len(k)>2:
                o=group[2]['data'];auth.fields(o,'response responseHash assessment liability latencyNs')
                if o['responseHash']!=q1.digest(o['response']) or o['assessment']!=assess(slot['slot'],o['response']):raise auth.Denied('Outcome evidence mismatch')
                if type(o['liability'])is not int or o['liability']<0 or o['liability']!=o['assessment'].get('estimatedNanodollars',2500000):raise auth.Denied('Liability mismatch')
            if len(k)>3:
                review,_=check_packet(group[3]['data'],'review',group[3]);self.review_binding(review['data'],group[2])
                if i<len(starts)-1 and not self.agrees(review['data']):raise auth.Denied('Disagreement cannot progress')
            if i<len(starts)-1 and (len(k)!=4 or group[2]['data']['assessment']['raw']['mechanicalFailures'] or group[2]['data']['liability']>2500000):raise auth.Denied('Unreviewed/critical previous operation')
        if any(f['kind']not in ('SCOPE','HALT') and not any(s['operation']==f['operation'] for s in starts) for f in facts):raise auth.Denied('Unknown operation fact')
        liabilities={f['operation']:f['data']['liability'] for f in facts if f['kind']=='OUTCOME'}
        extra=sum(max(r[5],liabilities.get(json.loads(r[6])['operation'],0)) for r in rows[10:])
        return rows,facts,sum(r[5] for r in rows[:10])+extra,extra

    def scope_packets(self,packets,now):
        auth.fields(packets,'owner rubric readiness_permission readiness')
        verified={role:self.signed(packet,role,now)[1] for role,packet in packets.items()}
        ready=auth.parse(packets['readiness']['envelope'].encode())
        auth.exact(ready['data']['permissionHash'],verified['readiness_permission'])
        return verified

    def execute_binding(self,data,scope,facts,*,start_index=None):
        before=facts if start_index is None else facts[:start_index]
        reviews=[f for f in before if f['kind']=='REVIEW']
        previous=reviews[-1]['hash'] if reviews else auth.ZERO
        auth.exact([data['ownerHash'],data['readinessHash'],data['previousReviewHash']],
                   [auth.digest(scope['owner']),auth.digest(scope['readiness']),previous])

    def record(self,start,slot):
        return json.dumps({'version':VERSION,'operation':start['operation'],'startHash':start['hash'],
                           'slot':slot['slot'],'payloadHash':slot['payloadHash']},sort_keys=True)

    def activate_synthetic_scope(self,packets,now):
        with self.lock():
            rows,facts,_,_=self.state()
            if facts or len(rows)!=10:raise auth.Denied('Scope already exists')
            self.scope_packets(packets,now)
            if len({auth.parse(p['envelope'].encode())['nonce'] for p in packets.values()})!=4:raise auth.Denied('Duplicate grant nonce')
            self.append('SCOPE',self.marker['scope'],packets,facts,now)

    def simulate_one(self,permission,transport,now,*,crash_at=None):
        if type(transport)is not base.FakeTransport or crash_at not in (None,*CRASHES):raise auth.Denied('Closed fake transport only')
        with self.lock():
            rows,facts,exposure,extra=self.state()
            if not facts or facts[0]['kind']!='SCOPE' or any(f['kind']=='HALT' for f in facts):raise auth.Denied('Missing scope/halted')
            self.scope_packets(facts[0]['data'],now)  # Fresh current checks, separate from historical verification.
            e,h=self.signed(permission,'execute',now);starts=[f for f in facts if f['kind']=='START']
            if starts and (facts[-1]['kind']!='REVIEW' or not self.agrees(auth.parse(facts[-1]['data']['envelope'].encode())['data'])):raise auth.Denied('Incomplete/disagreed operation/review; never retry')
            if e['nonce'] in self.used_nonces(facts):raise auth.Denied('Permission replay')
            if len(starts)>=5 or e['data']['slot']!=base.plan()['slots'][len(starts)]['slot']:raise auth.Denied('Unexpected next slot')
            self.execute_binding(e['data'],facts[0]['data'],facts)
            slot=base.plan()['slots'][len(starts)];admission(len(rows),sum(r[1]=='openai' for r in rows),exposure,len(starts),extra)
            die('before_start',crash_at)
            op=q1.digest([self.journal_hash,facts[0]['hash'],11+len(starts),h])
            start=self.append('START',op,{'permission':permission,'rowid':11+len(starts)},facts,now)
            die('before_reserve',crash_at)
            with closing(self.db()) as db:
                db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',
                    (*slot['slot'],'reserved_uncertain',2500000,self.record(start,slot)))
                die('before_commit',crash_at);db.commit()
            base.fsync_dir(self.directory);die('after_reserve',crash_at)
            self.append('INTENT',op,{'startHash':start['hash'],'payloadHash':slot['payloadHash']},facts,now);die('after_intent',crash_at)
            began=time.perf_counter_ns()
            try:
                response=base.FakeTransport.exchange(transport,self.directory,op,slot['payloadHash']);die('after_send',crash_at)
                elapsed=time.perf_counter_ns()-began;assessment=assess(slot['slot'],response)
                outcome=self.append('OUTCOME',op,{'response':response,'responseHash':q1.digest(response),'assessment':assessment,
                    'liability':assessment.get('estimatedNanodollars',2500000),'latencyNs':elapsed},facts,now)
                if assessment['raw']['mechanicalFailures'] or outcome['data']['liability']>2500000:
                    self.append('HALT',op,{'reason':'raw_critical_provider_or_guard_error'},facts,now)
                die('after_outcome',crash_at);return outcome
            except Exception:
                if facts[-1]['kind']!='HALT':self.append('HALT',op,{'reason':'uncertain_send_or_evaluation'},facts,now)
                raise auth.Denied('Uncertain fake operation; retained/halted') from None

    def review_binding(self,data,outcome):
        auth.exact([data['operationID'],data['outcomeHash'],data['responseHash']],
                   [outcome['operation'],outcome['hash'],outcome['data']['responseHash']])

    def used_nonces(self,facts):
        packets=[]
        for f in facts:
            if f['kind']=='SCOPE':packets.extend(f['data'].values())
            elif f['kind']=='START':packets.append(f['data']['permission'])
            elif f['kind']=='REVIEW':packets.append(f['data'])
        return {auth.parse(p['envelope'].encode())['nonce'] for p in packets}

    def agrees(self,data):return data['decision']=='agree' and all(v=='agree' for v in data['judgments'].values())

    def record_review(self,packet,now):
        with self.lock():
            _,facts,_,_=self.state()
            if not facts or facts[-1]['kind']!='OUTCOME':raise auth.Denied('No reviewable outcome/halted')
            e,_=self.signed(packet,'review',now);outcome=facts[-1];self.review_binding(e['data'],outcome)
            if outcome['data']['assessment']['raw']['mechanicalFailures']:raise auth.Denied('Critical raw failure cannot be reviewed away')
            if e['nonce'] in self.used_nonces(facts):raise auth.Denied('Review nonce replay')
            self.append('REVIEW',outcome['operation'],packet,facts,now)
            if not self.agrees(e['data']):self.append('HALT',outcome['operation'],{'reason':'independent_review_disagreement'},facts,now)
