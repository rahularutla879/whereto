"""Versioned in-process READ-ONLY evidence I/O port for frozen offline replays.

No source/ROOT/validator replacement. Only private-evidence path I/O is routed
from the matching checkout to the existing original files. Not an OS sandbox.
"""
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import os
from pathlib import Path
import fcntl
import sqlite3
import stat
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

VERSION = '52b-original-evidence-readonly-port-v1'
ORIGINAL_ROOT = Path('/Users/rahularutla/Documents/whereto')
RELATIVE = Path('backend/.local/task52-model-evaluation')


def require_read_mode(mode):
    if mode not in ('r','rb','rt'): raise ValueError('Evidence is read-only')


def require_read_flags(flags, dir_fd=None):
    if dir_fd is not None or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
        raise ValueError('Original evidence descriptor is read-only')


@contextmanager
def original_evidence(*, lock_owner="port"):
    if lock_owner not in ("port", "frozen_q4b"):
        raise ValueError("Unknown read lock owner")
    from scripts import task52_q1 as q1, task52_q4b as reader
    from scripts.task52_phase_b2_identity import verify
    verify()  # Never suppress or replace the frozen source gate.
    source = ORIGINAL_ROOT / RELATIVE
    virtual = q1.ROOT / RELATIVE
    if source == virtual:
        raise ValueError('A separate matching source environment is required')
    expected = reader.plan()['baseline']
    original_open, original_stat = Path.open, Path.stat
    original_rglob, original_connect = Path.rglob, sqlite3.connect
    original_os_open = os.open
    def relative(path, root):
        try: return Path(path).relative_to(root)
        except ValueError: return None
    # Resolve every component in the real path. No filesystem aliases created.
    for path in [source, *source.parents]:
        if path.is_symlink(): raise ValueError('Linked original path refused')
    if stat.S_IMODE(source.stat().st_mode) != 0o700:
        raise ValueError('Original directory permissions')
    paths = [p for p in source.rglob('*') if p.is_file()]
    if len(paths) != 324 or any(p.is_symlink() or p.stat().st_nlink != 1 for p in paths):
        raise ValueError('Original file set or links')
    identities = {p.relative_to(source): (p.stat().st_dev, p.stat().st_ino) for p in paths}
    directory_identity=(source.stat().st_dev,source.stat().st_ino)
    def inventory():
        directory_stat=original_stat(source,follow_symlinks=False)
        if ((directory_stat.st_dev,directory_stat.st_ino)!=directory_identity or
                stat.S_IMODE(directory_stat.st_mode)!=0o700):
            raise ValueError('Original directory identity or permissions changed')
        current={}
        for path in original_rglob(source,'*'):
            entry=original_stat(path,follow_symlinks=False)
            if stat.S_ISLNK(entry.st_mode): raise ValueError('Linked evidence refused')
            if stat.S_ISREG(entry.st_mode):
                if entry.st_nlink!=1: raise ValueError('Linked evidence refused')
                current[path.relative_to(source)]=(entry.st_dev,entry.st_ino)
        if current!=identities: raise ValueError('Original evidence inventory/inodes changed')
        if stat.S_IMODE(original_stat(source/'journal.sqlite').st_mode)!=0o600:
            raise ValueError('Original journal permissions changed')
    def hashes():
        inventory()
        return {str(p.relative_to(source)): sha256(p.read_bytes()).hexdigest() for p in paths}
    before = hashes()
    if q1.digest(before) != expected['correctionAndPrivateEvidenceSetHash']:
        raise ValueError('Original private evidence mismatch')
    if before['journal.sqlite'] != expected['journalSHA256']:
        raise ValueError('Original journal mismatch')
    if stat.S_IMODE((source/'journal.sqlite').stat().st_mode) != 0o600:
        raise ValueError('Original journal permissions')
    if any((source/('journal.sqlite'+s)).exists() for s in ('-wal','-shm','-journal')):
        raise ValueError('Original journal side files refused')
    lock = os.open(source/'experiment.lock', os.O_RDONLY | os.O_NOFOLLOW)
    connections = []
    opened = set()
    try:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        if (os.fstat(lock).st_dev, os.fstat(lock).st_ino) != identities[Path('experiment.lock')]:
            raise ValueError('Original lock identity')
        if hashes() != before: raise ValueError('Evidence changed before lock')
        def mapped(path):
            r = relative(path, virtual)
            if r is None: r = relative(path, source)
            if r is None: return None
            # No parent traversal, alternate paths, missing files or side journals.
            if '..' in r.parts or r not in identities and r != Path('.'):
                raise ValueError('Unapproved evidence path')
            actual = source/r
            st = original_stat(actual, follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode): raise ValueError('Linked evidence refused')
            if r in identities and (st.st_dev, st.st_ino) != identities[r]:
                raise ValueError('Original evidence inode changed')
            return actual
        def read_fd(path, flags, mode=0o777, *, dir_fd=None):
            actual = mapped(path)
            if actual is None:
                return original_os_open(path, flags, mode, dir_fd=dir_fd)
            require_read_flags(flags,dir_fd)
            return original_os_open(actual, flags | os.O_NOFOLLOW, mode)
        def read_open(path, mode='r', *args, **kwargs):
            actual = mapped(path)
            if actual is None: return original_open(path, mode, *args, **kwargs)
            require_read_mode(mode)
            # Open without following a replaced final symlink, then verify fd.
            fd = original_os_open(actual, os.O_RDONLY | os.O_NOFOLLOW)
            r = actual.relative_to(source)
            st = os.fstat(fd)
            if r not in identities or (st.st_dev, st.st_ino) != identities[r]:
                os.close(fd); raise ValueError('Evidence descriptor mismatch')
            opened.add(str(r))
            return os.fdopen(fd, mode, *args, **kwargs)
        def read_stat(path, *args, **kwargs):
            actual = mapped(path)
            return original_stat(actual if actual is not None else path, *args, **kwargs)
        def read_glob(path, pattern, *args, **kwargs):
            if Path(path) in (virtual, source):
                inventory()
                if pattern != '*' or args or kwargs: raise ValueError('Unsupported evidence enumeration')
                return iter(Path(path)/r for r in identities)
            return original_rglob(path, pattern, *args, **kwargs)
        def authorizer(action, first, second, database, trigger):
            if action == sqlite3.SQLITE_PRAGMA and first == 'query_only' and second in ('ON', '1'):
                return sqlite3.SQLITE_OK
            return reader._authorizer(action, first, second, database, trigger)
        class LockedConnection(sqlite3.Connection):
            evidence_lock = None
            def close(self):
                try: super().close()
                finally:
                    if self.evidence_lock is not None:
                        os.close(self.evidence_lock)
                        self.evidence_lock = None
        def connect(database, *args, **kwargs):
            allowed = {f'file:{root}/journal.sqlite?{query}' for root in (virtual, source)
                       for query in ('mode=ro', 'mode=ro&immutable=1')}
            if str(database) not in allowed:
                name=os.fsdecode(os.fspath(database))
                if name.startswith('file:'):
                    parsed=urlsplit(name)
                    if parsed.netloc not in ('','localhost'):
                        raise ValueError('Unknown SQLite authority')
                    name=unquote(parsed.path)
                if name.startswith(('/dev/','/proc/')):
                    raise ValueError('SQLite descriptor/device aliases refused')
                canonical=Path(name).resolve()
                if any(canonical==root or root in canonical.parents for root in (virtual,source)):
                    raise ValueError('Only exact original read-only evidence URI is permitted')
                return original_connect(database, *args, **kwargs)
            if kwargs.get('uri') is not True:
                raise ValueError('Original evidence URI required')
            if args or set(kwargs)-{'uri'}: raise ValueError('Unexpected evidence connection options')
            mapped(source/'journal.sqlite')
            lease=original_os_open(source/'experiment.lock',os.O_RDONLY|os.O_NOFOLLOW)
            try:
                fcntl.flock(lease,fcntl.LOCK_SH|fcntl.LOCK_NB)
                connection = original_connect(f'file:{source}/journal.sqlite?mode=ro&immutable=1',
                                              uri=True,factory=LockedConnection)
                connection.evidence_lock=lease
            except BaseException:
                os.close(lease)
                raise
            try:
                connection.execute('PRAGMA query_only=ON')
                connection.set_authorizer(authorizer)
            except BaseException:
                connection.close()
                raise
            connections.append(connection)
            return connection
        if lock_owner=="frozen_q4b": fcntl.flock(lock,fcntl.LOCK_UN)
        with ExitStack() as stack:
            stack.enter_context(patch.object(os, 'open', read_fd))
            stack.enter_context(patch.object(Path, 'open', read_open))
            stack.enter_context(patch.object(Path, 'stat', read_stat))
            stack.enter_context(patch.object(Path, 'rglob', read_glob))
            stack.enter_context(patch.object(sqlite3, 'connect', connect))
            stack.enter_context(patch('requests.sessions.Session.send', side_effect=AssertionError('No provider I/O')))
            stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('No sockets')))
            yield {'identity': VERSION, 'originalFiles': 324, 'sourceGateVerified': True,
                   'originalLockInodeVerified': True, 'readOnly': True, 'openedRelativeNames': opened}
        if lock_owner=="frozen_q4b": fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        if hashes() != before: raise ValueError('Original evidence changed during replay')
        verify()
    finally:
        for connection in connections: connection.close()
        os.close(lock)
