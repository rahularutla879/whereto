"""Q4A OFFLINE fixture engine. No live runner, HTTP adapter or approval issuer.

Only factory-created TemporaryDirectory fixtures registered in this process (or
an explicitly forked test child) are writable. The SQLite schema resembles the
original, but its baseline rows are FICTIONAL, NOT a copy of the paid journal.
Hashes anchor reviewed evidence; they do not authenticate human reviewers.
"""
from contextlib import contextmanager, closing
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from scripts import task52_q1 as q1
from scripts import task52_q3 as q3
from scripts.task52_q4a_scoring import assess

IDENTITY = '52b-q4a-openai-b2-v4-OFFLINE-v1'
PROPOSAL_DIGEST = '66a026921cfbc9f9a983b94c717e633150a74854006051d7f429b0efee15b3f7'
REGISTRY = {}  # Test capabilities only. Lost registry always refuses recovery.
FACT_KINDS = {'APPROVAL', 'START', 'INTENT', 'OUTCOME', 'REVIEW', 'HALT'}
CRASH_POINTS = {'before_start', 'before_reserve', 'before_commit', 'after_reserve',
                'after_intent', 'after_send', 'after_outcome'}


class Refused(ValueError):
    """Safe bounded classification; no raw exception/provider body logging."""


def live_dispatch(*args, **kwargs):
    raise Refused('Live activation/operator authentication/transport are NOT implemented')


def plan():
    p = json.loads((q1.ROOT/'docs/task52-q3-openai-proposal-v1.json').read_text())
    if q1.digest(p) != PROPOSAL_DIGEST:
        raise Refused('Frozen parent proposal mismatch')
    return p


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private_create(path, value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        fsync_dir(path.parent)
    except BaseException:
        # An incomplete file is intentionally not removed/retried. Fold refuses.
        raise


def crash(point, selected):
    if point == selected:
        os._exit(72)  # Called ONLY by explicit forked-process failure tests.


class FakeTransport:
    """Fixed recorded response or allowlisted simulated failure. No callbacks."""
    def __init__(self, response=None, *, failure=None):
        if failure not in (None, 'http_error', 'uncertain_send', 'response_loss'):
            raise Refused('Unknown fictional failure')
        self.response = deepcopy(response)
        self.failure = failure

    def exchange(self, directory, operation, payload_hash):
        private_create(directory/('fake-send-'+operation+'.json'),
                       {'FICTIONAL': True, 'operation': operation, 'payloadHash': payload_hash})
        if self.failure in ('uncertain_send', 'response_loss'):
            raise Refused('Fictional uncertain send; never retry')
        if self.failure == 'http_error':
            return {'model': 'gpt-6-luna', '_http_status': 400, 'error': {'type': 'FICTIONAL'}}
        return deepcopy(self.response)


class FictionalFixture:
    """Not an initializer for a real journal. No caller-supplied directory."""
    def __init__(self):
        from scripts.task52_q4a_identity import verify
        self.build = verify(full=True)
        self.temp = tempfile.TemporaryDirectory(prefix='whereto-q4a-fictional-')
        self.directory = Path(self.temp.name).resolve()
        os.chmod(self.directory, 0o700)
        self.p = plan()
        # Deliberately synthetic financial records; only consumed slot IDs and
        # opaque original hash anchors are retained as comparison evidence.
        rows = [(a['slot'][0], a['slot'][1], a['slot'][2],
                 'FICTIONAL_historical_halt' if i == 9 else 'FICTIONAL_historical',
                 47366625 if i == 0 else 0,
                 json.dumps({'FICTIONAL': True, 'ordinal': i+1}))
                for i,a in enumerate(self.p['baseline']['rows'])]
        db = self.directory/'journal.sqlite'
        with closing(sqlite3.connect(db)) as conn:
            conn.executescript('CREATE TABLE metadata(id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL);'
                'CREATE TABLE attempts(provider TEXT,case_id TEXT,repetition INTEGER,status TEXT NOT NULL,charge INTEGER NOT NULL,record TEXT,PRIMARY KEY(provider,case_id,repetition));')
            conn.execute('INSERT INTO metadata VALUES(1,?)', (json.dumps({'FICTIONAL': True, 'historicalEvidence': self.p['baseline']}),))
            conn.executemany('INSERT INTO attempts VALUES(?,?,?,?,?,?)', rows)
            conn.commit()
            root = conn.execute('SELECT config FROM metadata').fetchone()[0]
        os.chmod(db, 0o600)
        marker = {'purpose': IDENTITY, 'fictionalOnly': True, 'nonce': uuid.uuid4().hex,
                  'executionBuildHash': q1.digest(self.build), 'parentDigest': PROPOSAL_DIGEST,
                  'root': q1.digest(root), 'rows': [q1.digest(r) for r in rows],
                  'limits': {'global': 594, 'provider': 198, 'spend': 12000000000,
                             'extra': 12500000, 'attempts': 5}}
        private_create(self.directory/'fixture.json', marker)
        private_create(self.directory/'experiment.lock', {'FICTIONAL': True})
        REGISTRY[str(self.directory)] = q1.digest(marker)

    def close(self):
        REGISTRY.pop(str(self.directory), None)
        self.temp.cleanup()

    def engine(self):
        return Engine(self.directory)


class Engine:
    """One-step fictional execution; no loop, retry, arbitrary DB or transport."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self._check_directory()
        self.p = plan()

    def _check_directory(self):
        directory = self.directory
        if (str(directory) not in REGISTRY or directory.is_symlink() or directory.resolve() != directory
                or not directory.name.startswith('whereto-q4a-fictional-')):
            raise Refused('Only registered temporary fictional state is writable')
        if any(p.is_symlink() for p in directory.iterdir()):
            raise Refused('Symlink fixture refused')
        try:
            marker = json.loads((directory/'fixture.json').read_text())
        except (OSError, ValueError):
            raise Refused('Missing/corrupt fixture identity') from None
        if q1.digest(marker) != REGISTRY[str(directory)]:
            raise Refused('Fixture/root/build/limits identity changed')
        return marker

    @contextmanager
    def locked(self):
        self._check_directory()
        with (self.directory/'experiment.lock').open('rb') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused('Concurrent runner') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def db(self):
        self._check_directory()
        conn = sqlite3.connect(f'file:{self.directory}/journal.sqlite?mode=rw', uri=True)
        conn.execute('PRAGMA synchronous=FULL')
        return conn

    def state(self):
        marker = self._check_directory()
        from scripts.task52_q4a_identity import verify
        if q1.digest(verify()) != marker['executionBuildHash']:
            raise Refused('Unknown execution build')
        with closing(self.db()) as conn:
            if conn.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise Refused('Fictional database integrity')
            rows = conn.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall()
            root = conn.execute('SELECT config FROM metadata').fetchone()[0]
        if q1.digest(root) != marker['root'] or [q1.digest(r[1:]) for r in rows[:10]] != marker['rows']:
            raise Refused('Historical fictional root/ten anchors changed')
        if rows[9][4] != 'FICTIONAL_historical_halt':
            raise Refused('Historical halt missing')
        paths = sorted(self.directory.glob('fact-*'))
        if len(paths) > 22 or any(p.stat().st_size > 1048576 for p in paths):
            raise Refused('Bounded fact count/size exceeded')
        facts = []
        chain = marker['executionBuildHash']
        for i, path in enumerate(paths, 1):
            try:
                fact = json.loads(path.read_text())
            except (OSError, ValueError):
                raise Refused('Corrupt append-only fact') from None
            if (path.name != f'fact-{i:04d}.json' or set(fact) != {'kind','operation','data','previous','hash'}
                    or fact['kind'] not in FACT_KINDS or fact['previous'] != chain
                    or fact['hash'] != q1.digest({k:v for k,v in fact.items() if k != 'hash'})):
                raise Refused('Fact chain/sequence mismatch')
            facts.append(fact)
            chain = fact['hash']
        # Verify the entire allowed state grammar, not just the last status.
        approvals = [f for f in facts if f['kind'] == 'APPROVAL']
        if approvals and (len(approvals) != 1 or facts[0] != approvals[0] or approvals[0]['operation'] != 'FICTIONAL-SCOPE' or approvals[0]['data'] != self.approval_data()):
            raise Refused('Unapproved/forged/mismatched fictional grant')
        starts = [f for f in facts if f['kind'] == 'START']
        if len(starts) > 5 or any(f['kind'] == 'HALT' for f in facts[:-1]):
            raise Refused('Persistent child halt/attempt limit')
        consumed = {tuple(r[1:4]) for r in rows[:10]}
        if len(rows) > 10+len(starts):
            raise Refused('Orphan financial anchor')
        for i, start in enumerate(starts):
            slot = self.p['slots'][i]
            op = start['operation']
            if not approvals or start['data'] != self.binding(slot, rows[10+i][0] if len(rows)>10+i else 11+i):
                raise Refused('Start scope/order/source mismatch')
            if op != q1.digest({'approval': approvals[0]['hash'], 'binding': start['data']}):
                raise Refused('Operation identity mismatch')
            if tuple(slot['slot']) in consumed:
                raise Refused('Consumed slot')
            if len(rows)>10+i:
                row = rows[10+i]
                record = json.loads(row[6])
                if row[0] != 11+i or list(row[1:4]) != slot['slot'] or row[4:6] != ('reserved_uncertain',2500000) or record != {'FICTIONAL': True,'operation':op,'binding':start['data']}:
                    raise Refused('Reservation/source/charge mismatch')
            group = [f for f in facts if f['operation'] == op and f['kind'] != 'HALT']
            kinds = [f['kind'] for f in group]
            if kinds not in (['START'],['START','INTENT'],['START','INTENT','OUTCOME'],['START','INTENT','OUTCOME','REVIEW']):
                raise Refused('Operation fact grammar')
            if len(kinds)>1 and len(rows)<=10+i:
                raise Refused('Intent without committed reservation')
            if len(kinds)>1 and group[1]['data'] != {'rowid':11+i,'payloadHash':slot['payloadHash']}:
                raise Refused('Intent binding mismatch')
            if len(kinds)>2:
                outcome = group[2]['data']
                if set(outcome) != {'response','responseHash','assessment','latencyNs','liabilityNanodollars'} or q1.digest(outcome['response']) != outcome['responseHash']:
                    raise Refused('Response identity')
                if type(outcome['liabilityNanodollars']) is not int or outcome['liabilityNanodollars'] < 0:
                    raise Refused('Invalid liability')
                # Recompute mechanical decisions, never trust a stored pass flag.
                if outcome['assessment'] != assess(slot['slot'], outcome['response']):
                    raise Refused('Changed assessment')
            if len(kinds)>3 and (group[3]['data'] != self.review_data(group[2]) or group[2]['data']['assessment']['raw']['mechanicalFailures']):
                raise Refused('Forged/stale/incomplete fictional review')
            if i < len(starts)-1 and kinds != ['START','INTENT','OUTCOME','REVIEW']:
                raise Refused('Progress before complete review')
        if any(f['kind'] not in ('APPROVAL','START','HALT') and not any(s['operation']==f['operation'] for s in starts) for f in facts):
            raise Refused('Unknown operation')
        exposures = {f['operation']:f['data']['liabilityNanodollars'] for f in facts if f['kind']=='OUTCOME'}
        total = sum(r[5] for r in rows[:10]) + sum(max(r[5], exposures.get(json.loads(r[6])['operation'], 0)) for r in rows[10:])
        return marker, rows, facts, total

    def append(self, kind, operation, data, facts):
        # Private internal primitive: all callers hold the common OS lock.
        previous = facts[-1]['hash'] if facts else self._check_directory()['executionBuildHash']
        value = {'kind': kind, 'operation': operation, 'data': deepcopy(data), 'previous': previous}
        value['hash'] = q1.digest(value)
        private_create(self.directory/f'fact-{len(facts)+1:04d}.json', value)
        facts.append(value)
        return value

    def approval_data(self):
        marker = self._check_directory()
        return {'fictionalOnly': True, 'owner': 'FICTIONAL-OWNER', 'reviewer': 'FICTIONAL-INDEPENDENT-REVIEWER',
                'parent': PROPOSAL_DIGEST, 'build': marker['executionBuildHash'],
                'baseline': q1.digest(self.p['baseline']), 'slots': q1.digest(self.p['slots']),
                'rubricsReviewed': True, 'historicalFailuresReviewed': True,
                'limits': marker['limits']}

    def simulate_approval(self, *, owner='FICTIONAL-OWNER', reviewer='FICTIONAL-INDEPENDENT-REVIEWER'):
        with self.locked():
            _, _, facts, _ = self.state()
            if facts or owner != 'FICTIONAL-OWNER' or reviewer != 'FICTIONAL-INDEPENDENT-REVIEWER':
                raise Refused('Missing/duplicate/forged fictional owner or reviewer')
            self.append('APPROVAL', 'FICTIONAL-SCOPE', self.approval_data(), facts)

    def binding(self, slot, rowid):
        return {'rowid': rowid, 'slot': slot['slot'], 'payloadHash': slot['payloadHash'],
                'sourceHash': slot['sourceSHA256'], 'rubricHash': slot['rubricCaseDigest'],
                'build': self._check_directory()['executionBuildHash'], 'parent': PROPOSAL_DIGEST}

    def simulate_next(self, slot, transport, *, readiness, now, input_bound=12000, output_bound=2000,
                      charge=2500000, candidate=None, crash_at=None):
        if type(transport) is not FakeTransport or crash_at not in (None, *CRASH_POINTS):
            raise Refused('Only fixed fake transport/failure points; no callbacks')
        with self.locked():
            marker, rows, facts, exposure = self.state()
            if candidate is not None and candidate != self.p:
                raise Refused('Wrong model/prompt/schema/runtime/source/rubric')
            if not facts or facts[0]['kind'] != 'APPROVAL' or any(f['kind']=='HALT' for f in facts):
                raise Refused('Missing approval or persistent halt')
            if any(tuple(r[1:4]) == tuple(slot) for r in rows):
                raise Refused('Consumed slot, never retry')
            starts = [f for f in facts if f['kind']=='START']
            if starts and (facts[-1]['kind'] != 'REVIEW' or facts[-1]['operation'] != starts[-1]['operation']):
                raise Refused('Incomplete/uncertain/unreviewed previous operation')
            n = len(starts)
            if n >= 5 or slot != self.p['slots'][n]['slot']:
                raise Refused('Unexpected slot order/child attempt ceiling')
            if not self.valid_readiness(readiness, now) or input_bound < readiness['completeCounts'][n]+2048:
                raise Refused('Stale/missing/unknown fictional readiness')
            if type(input_bound) is not int or not 1 <= input_bound <= 12000 or type(output_bound) is not int or output_bound != 2000 or type(charge) is not int or charge != 2500000:
                raise Refused('Input/output/full charge limit')
            limits = marker['limits']
            if (len(rows)>=limits['global'] or sum(r[1]=='openai' for r in rows)>=limits['provider'] or
                    exposure+charge>limits['spend'] or (n+1)*charge>limits['extra'] or n>=limits['attempts']):
                raise Refused('Original or incremental admission ceiling')
            crash('before_start', crash_at)
            selected = self.p['slots'][n]
            binding = self.binding(selected, 11+n)
            operation = q1.digest({'approval': facts[0]['hash'], 'binding': binding})
            self.append('START', operation, binding, facts)
            crash('before_reserve', crash_at)
            with closing(self.db()) as conn:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)', (*slot,'reserved_uncertain',charge,
                    json.dumps({'FICTIONAL': True,'operation': operation,'binding': binding})))
                crash('before_commit', crash_at)
                conn.commit()
            fsync_dir(self.directory)
            crash('after_reserve', crash_at)
            self.append('INTENT', operation, {'rowid':11+n,'payloadHash':selected['payloadHash']}, facts)
            crash('after_intent', crash_at)
            began = time.perf_counter_ns()
            try:
                # Explicit class dispatch: subclasses/instance callback overrides
                # are not a configurable transport or an accidental HTTP hook.
                response = FakeTransport.exchange(transport, self.directory, operation, selected['payloadHash'])
                crash('after_send', crash_at)
                elapsed = time.perf_counter_ns()-began
                assessment = assess(slot, response)
                liability = assessment.get('estimatedNanodollars', charge)
                self.append('OUTCOME', operation, {'response': response, 'responseHash': q1.digest(response),
                    'assessment': assessment,'latencyNs':elapsed,'liabilityNanodollars':liability}, facts)
                if assessment['raw']['mechanicalFailures'] or liability>charge:
                    self.append('HALT', operation, {'reason':'mechanical_critical_or_provider_failure'}, facts)
                crash('after_outcome', crash_at)
            except Exception:
                if facts[-1]['kind'] != 'HALT':
                    self.append('HALT', operation, {'reason':'uncertain_or_internal_failure'}, facts)
                raise Refused('Fictional send/evaluation uncertain; retained, halted') from None
            return deepcopy(facts[-2] if facts[-1]['kind']=='HALT' else facts[-1])

    def fake_readiness(self, now):
        return {'fictionalOnly': True, 'stamp': now.isoformat(), 'build':self._check_directory()['executionBuildHash'],
                'payloads': [s['payloadHash'] for s in self.p['slots']], 'completeCounts':[5100]*5,
                'allAccountAndTermsChecks':'FICTIONAL-PASS-NOT-CURRENT-ACCOUNT-EVIDENCE'}

    def valid_readiness(self, value, now):
        try:
            stamp = datetime.fromisoformat(value['stamp'])
            expected = self.fake_readiness(stamp)
            return (value==expected and now.utcoffset() is not None and stamp.utcoffset() is not None and
                    stamp.astimezone(timezone.utc).date()==now.astimezone(timezone.utc).date() and
                    0 <= (now-stamp).total_seconds() <= 86400 and all(n+2048<=12000 for n in value['completeCounts']))
        except (KeyError, TypeError, ValueError):
            return False

    def review_data(self, outcome):
        return {'fictionalOnly':True,'reviewer':'FICTIONAL-INDEPENDENT-REVIEWER',
                'outcomeHash':outcome['hash'],'responseHash':outcome['data']['responseHash'],
                'fields':{k:'FICTIONAL-AGREES' for k in self.p['slots'][0]['Q1FieldExpectations']},
                'rawCorrect':'FICTIONAL-AGREES', 'disagreement':False}

    def simulate_review(self, outcome_hash, *, reviewer='FICTIONAL-INDEPENDENT-REVIEWER', disagreement=False):
        with self.locked():
            _, _, facts, _ = self.state()
            if not facts or facts[-1]['kind'] != 'OUTCOME' or facts[-1]['hash'] != outcome_hash or reviewer != 'FICTIONAL-INDEPENDENT-REVIEWER':
                raise Refused('Missing/forged/replayed/critical/stale review')
            last = facts[-1]
            if disagreement:
                self.append('HALT', last['operation'], {'reason':'independent_review_disagreement'}, facts)
                raise Refused('Review disagreement; child halted')
            if last['data']['assessment']['raw']['mechanicalFailures']:
                raise Refused('Cannot review away a critical raw error')
            self.append('REVIEW', last['operation'], self.review_data(last), facts)
