"""Strictly read-only historical-journal inspection. Never an admission issuer.

No CLI, writes, credential loader, transport or approval loader. SQL is fixed;
connections are mode=ro&immutable=1, query-only and authorizer restricted. The
immutable option is safe only after refusing SQLite side journals and holding
SH on the already-existing common lock, with full before/after evidence pins.
"""
from contextlib import closing
import fcntl
import json
import os
import sqlite3
import stat

from scripts import task52_q1 as q1
from scripts.task52_q4a import plan
from scripts.task52_q4a_identity import verify as verify_q4a, MANIFEST_SHA

IDENTITY = '52b-q4b-readonly-journal-v1'
STATE = q1.ROOT/'backend/.local/task52-model-evaluation'
DDL = {
    'attempts': 'CREATE TABLE attempts (provider TEXT, case_id TEXT, repetition INTEGER, status TEXT NOT NULL, charge INTEGER NOT NULL, record TEXT, PRIMARY KEY(provider,case_id,repetition))',
    'metadata': 'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL)',
}
READ_URI = f'file:{STATE}/journal.sqlite?mode=ro&immutable=1'
PRAGMAS = {'integrity_check','table_info','index_list','index_info','journal_mode','synchronous','query_only'}


class Incompatible(ValueError):
    """Allowlisted classification only; no private record/exception in messages."""


def _authorizer(action, first, second, database, trigger):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA:
        if first in ('table_info','index_list') and second in ('attempts','metadata'):
            return sqlite3.SQLITE_OK
        if first == 'index_info' and second == 'sqlite_autoindex_attempts_1':
            return sqlite3.SQLITE_OK
        if first in PRAGMAS-{'table_info','index_list','index_info'} and second is None:
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _snapshot(conn):
    """Private in-memory evidence. Raw rows/root are never returned in reports."""
    return {'schema': conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name').fetchall(),
            'rows': conn.execute('SELECT rowid,* FROM attempts ORDER BY rowid').fetchall(),
            'metadata': conn.execute('SELECT id,config FROM metadata ORDER BY id').fetchall(),
            'integrity': conn.execute('PRAGMA integrity_check').fetchall(),
            'index': conn.execute('PRAGMA index_info(sqlite_autoindex_attempts_1)').fetchall(),
            'journalMode': conn.execute('PRAGMA journal_mode').fetchone()[0],
            'queryOnly': conn.execute('PRAGMA query_only').fetchone()[0],
            'synchronous': conn.execute('PRAGMA synchronous').fetchone()[0]}


def _validate(snapshot):
    """Pure baseline comparison, not a writable continuation-state fold."""
    baseline = plan()['baseline']
    expected_schema = [('table','attempts','attempts',DDL['attempts']),
                       ('table','metadata','metadata',DDL['metadata']),
                       ('index','sqlite_autoindex_attempts_1','attempts',None)]
    if (snapshot['schema'] != expected_schema or snapshot['integrity'] != [('ok',)]
            or snapshot['index'] != [(0,0,'provider'),(1,1,'case_id'),(2,2,'repetition')]
            or snapshot['journalMode'] != 'delete' or snapshot['queryOnly'] != 1):
        raise Incompatible('schema_or_readonly_profile_mismatch')
    rows = snapshot['rows']
    meta = snapshot['metadata']
    if (len(meta) != 1 or meta[0][0] != 1 or q1.digest(meta[0][1]) != baseline['rootHash']):
        raise Incompatible('original_root_mismatch')
    if ([r[0] for r in rows] != list(range(1,11)) or
            [q1.digest(r[1:]) for r in rows] != [a['rowHash'] for a in baseline['rows']]):
        raise Incompatible('original_row_or_status_or_reservation_mismatch')
    counts = {p:sum(r[1]==p for r in rows) for p in ('openai','google','anthropic')}
    if counts != baseline['counts'] or sum(r[5] for r in rows) != baseline['accountedNanodollars']:
        raise Incompatible('original_accounting_mismatch')
    if [r[4] for r in rows] != ['recorded']*9+['recorded_halted']:
        raise Incompatible('historical_halt_mismatch')
    return {'identity':IDENTITY,'historicalStorageSnapshotCompatible':True,
            'continuationReady':False,'executionAuthorized':False,'liveDispatchAvailable':False,
            'q4aExecutionManifestSHA256':MANIFEST_SHA,'journalSHA256':baseline['journalSHA256'],
            'rootHash':baseline['rootHash'],'rowHashes':[a['rowHash'] for a in baseline['rows']],
            'schemaHash':q1.digest(expected_schema),'schema':expected_schema,
            'rowIDs':list(range(1,11)), 'counts':counts,'attempts':10,
            'accountedNanodollars':sum(r[5] for r in rows),'remainingNanodollars':baseline['remainingNanodollars'],
            'perProviderRetainedNanodollars':{p:sum(r[5] for r in rows if r[1]==p) for p in counts},
            'statuses':{'recorded':9,'recorded_halted':1},'persistentHistoricalHalt':True,
            'journalMode':snapshot['journalMode'],'readConnectionSynchronous':snapshot['synchronous'],
            'synchronousNote':'Connection default only; historical writer uses FULL explicitly. Not proof of every past commit or hardware durability.',
            'rowIDsAreAutoincrement':False,
            'blockers':['real authenticated owner/reviewer trust boundary unimplemented',
                        'real append-only writer/child scope and all-scope outcome fold unimplemented',
                        'independent reviews and separately authorized fresh readiness incomplete',
                        'no exact owner-approved live execution build or financial grant']}


def inspect_original():
    """Only this fixed real read path exists. Missing/changed evidence refuses."""
    verify_q4a(full=True)
    expected = plan()['baseline']
    before = q1.private_hashes()
    if len(before) != 324 or q1.digest(before) != expected['correctionAndPrivateEvidenceSetHash']:
        raise Incompatible('private_evidence_or_correction_mismatch')
    paths = (STATE,STATE/'journal.sqlite',STATE/'experiment.lock')
    if any(p.is_symlink() for p in paths):
        raise Incompatible('symlink_identity_refused')
    if stat.S_IMODE(STATE.stat().st_mode) != 0o700 or stat.S_IMODE(paths[1].stat().st_mode) != 0o600:
        raise Incompatible('private_permissions_mismatch')
    if any((STATE/f'journal.sqlite{suffix}').exists() for suffix in ('-wal','-shm','-journal')):
        raise Incompatible('side_journal_requires_review_never_recover_or_ignore')
    # Never mkdir/touch/chmod/open-a or instantiate a historical Ledger writer.
    fd = os.open(paths[2],os.O_RDONLY|os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:
            raise Incompatible('experiment_writer_locked') from None
        if q1.private_hashes() != before:
            raise Incompatible('evidence_changed_before_locked_read')
        with closing(sqlite3.connect(READ_URI,uri=True)) as conn:
            conn.execute('PRAGMA query_only=ON')  # Connection flag, no database change.
            conn.set_authorizer(_authorizer)
            report = _validate(_snapshot(conn))
        if q1.private_hashes() != before:
            raise Incompatible('evidence_changed_during_read')
        report.update({'privateFilesUnchanged':324,'correctionsUnchanged':True,'sourcePinsAndQ4ABuildVerified':True,
                       'lockMode':oct(stat.S_IMODE(os.fstat(fd).st_mode)),
                       'directoryMode':'0o700','journalFileMode':'0o600',
                       'readMode':'mode=ro&immutable=1; query_only; SQL authorizer; existing common SH lock',
                       'reportPurpose':'compatibility evidence only, never an approval or dispatch capability'})
        return report
    finally:
        os.close(fd)  # Also releases the read-only descriptor's flock.
