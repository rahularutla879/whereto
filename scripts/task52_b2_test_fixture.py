"""Explicit fake-unit/reference-data fixtures, NEVER paid evaluator readiness.

Original corpus() is saved and exercised unmodified before fixture injection.
Only unittest suites/current-runtime reconstruction enter this context. No CLI,
scorer, credentials, model client, public receipt or dispatch entry is provided.
"""
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import cloud_model52 as e

ORIGINAL_CORPUS=e.corpus
PAID_STATE=e.STATE.resolve()
_ACTIVE=ContextVar('b2_offline_reference_fixture',default=False)


def reference_data():
    raw=e.CORPUS.read_bytes()
    import hashlib
    if hashlib.sha256(raw).hexdigest()!=e.CORPUS_SHA:raise ValueError('Reference corpus bytes changed')
    data=json.loads(raw)
    if len(data['cases'])!=66 or len({r['id'] for r in data['cases']})!=66:
        raise ValueError('Reference corpus identity/count mismatch')
    return data


@contextmanager
def reference_scope(*, fake_unit_state=False):
    if _ACTIVE.get():
        yield;return
    from scripts.task52_phase_b2_identity import verify
    verify()
    # No silent relaxation: the real paid source gate MUST reject this checkout.
    try:ORIGINAL_CORPUS()
    except ValueError as exc:
        if str(exc)!='Reference source changed; review required: backend/journey.py':raise
    else:raise AssertionError('B2 must not satisfy the original paid source identity')
    data=reference_data()
    original_connect=sqlite3.connect;original_open=Path.open;original_os_open=os.open
    def protected(path):
        p=Path(os.fsdecode(path)).resolve()
        return p.is_relative_to(PAID_STATE) or (p.parent==e.ROOT/'backend' and p.name.startswith('.env.') and p.name!='.env.example')
    def connect(database,*a,**kw):
        name=os.fsdecode(database)
        if name.startswith('file:'):
            path=name[5:].split('?',1)[0]
            if protected(path) and not (kw.get('uri') and 'mode=ro' in name):raise AssertionError('Paid state is read-only')
        elif name!=':memory:' and protected(name):raise AssertionError('Paid state is read-only')
        return original_connect(database,*a,**kw)
    def opened(path,mode='r',*a,**kw):
        if protected(path) and (any(c in mode for c in 'wax+') or Path(path).name.startswith('.env.')):
            raise AssertionError('Protected evaluation state/config access')
        return original_open(path,mode,*a,**kw)
    def os_opened(path,flags,*a,**kw):
        if protected(path) and (flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            raise AssertionError('Protected evaluation state write')
        return original_os_open(path,flags,*a,**kw)
    with ExitStack() as stack:
        stack.enter_context(patch.object(e,'corpus',side_effect=lambda:deepcopy(data)))
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('Offline fixture: no HTTP')))
        stack.enter_context(patch('socket.socket.connect',side_effect=AssertionError('Offline fixture: no sockets')))
        stack.enter_context(patch.object(sqlite3,'connect',connect))
        stack.enter_context(patch.object(Path,'open',opened))
        stack.enter_context(patch.object(os,'open',os_opened))
        if fake_unit_state:
            directory=stack.enter_context(tempfile.TemporaryDirectory(prefix='whereto-fake-unit-'))
            stack.enter_context(patch.object(e,'STATE',Path(directory)))
        token=_ACTIVE.set(True)
        try:yield
        finally:_ACTIVE.reset(token)


class OfflineUnitSuite(unittest.TestSuite):
    """Only ephemeral fake-provider contract fixtures; test assertions unchanged.

    Historical config strings in these tests are literal sample data, not actual
    B2 approval. STATE is a temporary unit-test directory, never another experiment.
    """
    def run(self,result,debug=False):
        with reference_scope(fake_unit_state=True):
            return super().run(result,debug)
