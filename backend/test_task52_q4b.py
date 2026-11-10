"""Read-only real inspection and exact-DDL fictional SQL boundary tests.

All write/attack/crash tests use temporary fictional state. No original database
copy, owner keys, real grant, credentials or HTTP transport is constructed.
"""
from contextlib import closing
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import task52_q1 as q1
from scripts import task52_q4a as old
from scripts import task52_q4b as q


class RealShapeFiction:
    """Schema/accounting test fixture only; no transport or live activation."""
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='whereto-q4b-fictional-')
        self.directory=Path(self.temp.name);os.chmod(self.directory,0o700)
        self.db=sqlite3.connect(self.directory/'journal.sqlite')
        self.db.execute('PRAGMA synchronous=FULL')
        for sql in q.DDL.values():self.db.execute(sql)
        self.db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'FICTIONAL':True}),))
        # Synthetic amounts (NOT copied historical finances). Real status labels
        # and original consumed slot IDs exercise the actual existing schema.
        for i,a in enumerate(old.plan()['baseline']['rows']):
            self.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(*a['slot'],
                'recorded_halted' if i==9 else 'recorded',1000000,json.dumps({'FICTIONAL':True,'n':i})))
        self.db.commit();os.chmod(self.directory/'journal.sqlite',0o600)
        (self.directory/'experiment.lock').touch(mode=0o600)
        self.anchors=self.rows();self.root=self.db.execute('SELECT config FROM metadata').fetchone()[0]

    def rows(self):return self.db.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall()

    def close(self):self.db.close();self.temp.cleanup()

    def reserve_fictional(self,slot,*,global_cap=594,provider_cap=198,spend_cap=12000000000,extra_cap=12500000):
        """No owner authority. Just the exact-schema accounting transaction."""
        if self.rows()[:10]!=self.anchors or self.db.execute('SELECT config FROM metadata').fetchone()[0]!=self.root:
            raise ValueError('Fictional historical anchors changed')
        added=self.rows()[10:];plan=old.plan()['slots']
        if len(added)>=5 or slot!=plan[len(added)]['slot']:
            raise ValueError('Wrong/duplicate fictional slot')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows=self.rows()
            if any(list(r[1:4])==slot for r in rows):raise ValueError('Consumed')
            if len(rows)>=global_cap or sum(r[1]==slot[0] for r in rows)>=provider_cap:
                raise ValueError('Attempt ceiling')
            if sum(r[5] for r in rows)+2500000>spend_cap or (len(added)+1)*2500000>extra_cap:
                raise ValueError('Cost ceiling')
            record={'FICTIONAL':True,'payloadHash':plan[len(added)]['payloadHash'],
                    'operation':q1.digest([self.root,11+len(added),slot,plan[len(added)]['payloadHash']])}
            self.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',(*slot,'reserved_uncertain',2500000,json.dumps(record)))
        return self.rows()[-1]


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=q1.private_hashes();cls.report=q.inspect_original()
        with closing(sqlite3.connect(q.READ_URI,uri=True)) as db:
            db.execute('PRAGMA query_only=ON');db.set_authorizer(q._authorizer)
            cls.snapshot=q._snapshot(db)

    @classmethod
    def tearDownClass(cls):
        assert cls.before==q1.private_hashes()
        assert len(cls.before)==324

    def fixture(self):
        f=RealShapeFiction();self.addCleanup(f.close);return f

    def test_actual_schema_root_rows_accounting_halt_and_build(self):
        r=self.report
        self.assertTrue(r['historicalStorageSnapshotCompatible']);self.assertFalse(r['continuationReady'])
        self.assertFalse(r['executionAuthorized']);self.assertFalse(r['liveDispatchAvailable'])
        self.assertEqual(r['counts'],{'openai':7,'google':2,'anthropic':1})
        self.assertEqual(r['accountedNanodollars'],47366625);self.assertEqual(r['remainingNanodollars'],11952633375)
        self.assertEqual(r['statuses'],{'recorded':9,'recorded_halted':1})
        self.assertEqual(r['privateFilesUnchanged'],324);self.assertEqual(r['lockMode'],'0o644')
        self.assertNotIn('metadata',r);self.assertNotIn('rows',r)
        self.assertEqual(r['q4aExecutionManifestSHA256'],'8406905232a36726c17960d56cf66527edd79111750530871502378c711275c1')

    def test_only_fixed_ro_immutable_connection_is_opened(self):
        original=sqlite3.connect;seen=[]
        def connect(database,*args,**kwargs):
            self.assertEqual(database,q.READ_URI);self.assertIs(kwargs.get('uri'),True)
            seen.append(database);return original(database,*args,**kwargs)
        with patch.object(q.sqlite3,'connect',connect):q.inspect_original()
        self.assertEqual(seen,[q.READ_URI])

    def test_root_row_hash_status_reservation_rowid_and_missing_history_rejected(self):
        bads=[]
        s=deepcopy(self.snapshot);s['metadata']=[(1,'forged')];bads.append(s)
        for field,value in ((0,999),(4,'recorded'),(5,0),(6,'forged')):
            s=deepcopy(self.snapshot);r=list(s['rows'][-1]);r[field]=value;s['rows'][-1]=tuple(r);bads.append(s)
        s=deepcopy(self.snapshot);s['rows'].pop();bads.append(s)
        s=deepcopy(self.snapshot);s['rows'].append(s['rows'][0]);bads.append(s)
        for bad in bads:
            with self.assertRaises(q.Incompatible):q._validate(bad)

    def test_schema_unknown_trigger_index_and_read_profile_rejected(self):
        for key,value in (('schema',[]),('index',[]),('journalMode','wal'),('queryOnly',0),('integrity',[('bad',)])):
            s=deepcopy(self.snapshot);s[key]=value
            with self.assertRaises(q.Incompatible):q._validate(s)
        s=deepcopy(self.snapshot);s['schema'].append(('trigger','unknown','attempts','fake'))
        with self.assertRaises(q.Incompatible):q._validate(s)

    def test_real_private_evidence_mismatch_never_opens_database(self):
        with patch.object(q.q1,'private_hashes',return_value={}),patch.object(q.sqlite3,'connect',side_effect=AssertionError('must not open')):
            with self.assertRaises(q.Incompatible):q.inspect_original()

    def test_existing_lock_excludes_read_adapter_without_creating_files(self):
        # Lock on an existing read-only fd; no byte/permission modification.
        fd=os.open(q.STATE/'experiment.lock',os.O_RDONLY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(q.Incompatible):q.inspect_original()
        finally:os.close(fd)
        self.assertEqual(self.before,q1.private_hashes())

    def test_sql_authorizer_denies_writes_attach_and_pragma_setters_on_fiction_only(self):
        f=self.fixture();uri=f'file:{f.directory}/journal.sqlite?mode=ro&immutable=1'
        with closing(sqlite3.connect(uri,uri=True)) as db:
            db.execute('PRAGMA query_only=ON');db.set_authorizer(q._authorizer)
            self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone(),(10,))
            for sql in ("UPDATE attempts SET charge=0",'DELETE FROM attempts',
                        "INSERT INTO metadata VALUES(2,'forged')",'CREATE TABLE attack(x)',
                        "ATTACH DATABASE ':memory:' AS attack",'PRAGMA writable_schema=ON',
                        'PRAGMA query_only=OFF','PRAGMA journal_mode=WAL'):
                with self.assertRaises(sqlite3.DatabaseError):db.execute(sql)
        self.assertEqual(f.rows(),f.anchors)

    def test_exact_sql_constraints_do_not_supply_semantic_or_financial_authority(self):
        f=self.fixture()
        with self.assertRaises(sqlite3.IntegrityError),f.db:
            f.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',f.anchors[0][1:])
        with self.assertRaises(sqlite3.IntegrityError),f.db:
            f.db.execute("INSERT INTO metadata VALUES(2,'bad')")
        # Characterize actual weaknesses without changing real data: composite
        # nullable PK, no charge/status/cap checks, and ordinary rowid reuse.
        with f.db:
            f.db.execute("INSERT INTO attempts VALUES(NULL,NULL,NULL,'arbitrary',-1,NULL)")
            f.db.execute("INSERT INTO attempts VALUES(NULL,NULL,NULL,'arbitrary',-1,NULL)")
        self.assertEqual(len(f.rows()),12)
        with f.db:f.db.execute('DELETE FROM attempts WHERE rowid>10')
        first=f.reserve_fictional(old.plan()['slots'][0]['slot']);self.assertEqual(first[0],11)
        # Deletion is allowed by SQLite but forbidden by successor protocol.
        with f.db:f.db.execute('DELETE FROM attempts WHERE rowid=11')
        again=f.reserve_fictional(old.plan()['slots'][0]['slot']);self.assertEqual(again[0],11)

    def test_real_status_shaped_fictional_reservations_keep_anchors_halt_and_full_charge(self):
        f=self.fixture();operations=[]
        for slot in old.plan()['slots']:
            row=f.reserve_fictional(slot['slot']);operations.append(json.loads(row[6])['operation'])
            self.assertEqual(row[4:6],('reserved_uncertain',2500000))
        self.assertEqual(len(set(operations)),5);self.assertEqual(f.rows()[:10],f.anchors)
        self.assertEqual(f.rows()[9][4],'recorded_halted')
        self.assertEqual(sum(r[5] for r in f.rows()[10:]),12500000)
        # This is a SQL boundary fixture, not a runner: no sends or semantic
        # review bypass. Q4A end-to-end tests separately require per-step review.
        for slot in old.plan()['slots']:
            with self.assertRaises(ValueError):f.reserve_fictional(slot['slot'])

    def test_real_status_shaped_fictional_original_and_child_ceilings(self):
        for kw in ({'global_cap':10},{'provider_cap':7},{'spend_cap':10000000},{'extra_cap':2499999}):
            f=self.fixture()
            with self.assertRaises(ValueError):f.reserve_fictional(old.plan()['slots'][0]['slot'],**kw)
            self.assertEqual(f.rows(),f.anchors)
        f=self.fixture()
        for slot in old.plan()['baseline']['rows']:
            with self.assertRaises(ValueError):f.reserve_fictional(slot['slot'])

    def test_fake_old_or_missing_approval_cannot_authorize_a_real_run(self):
        for grant in (None,{}, {'force':True}, {'resume':True},
                      {'owner':'FICTIONAL-OWNER','reviewer':'FICTIONAL-INDEPENDENT-REVIEWER'},
                      {'configurationHash':old.plan()['successorVersionSpecification']['originalV4ConfigurationHash']}):
            with self.assertRaises(old.Refused):old.live_dispatch(grant)
        with self.assertRaises(old.Refused):old.Engine(q.STATE)
        self.assertEqual(self.before,q1.private_hashes())

    def test_hot_side_journal_is_refused_not_ignored_or_recovered(self):
        real=Path.exists
        def exists(path):
            return True if path==q.STATE/'journal.sqlite-journal' else real(path)
        with patch.object(Path,'exists',exists),patch.object(q.sqlite3,'connect',side_effect=AssertionError('must not open')):
            with self.assertRaises(q.Incompatible):q.inspect_original()
        self.assertEqual(self.before,q1.private_hashes())
