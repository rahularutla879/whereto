"""Disposable-cohort observer; logs state flags, never SQL parameters/content."""
from contextlib import contextmanager
import json
from unittest.mock import patch

@contextmanager
def observe():
    import psycopg
    from .test_native import g
    original=psycopg.Connection.execute
    def execute(connection,query,params=None,**kwargs):
        try:return original(connection,query,params,**kwargs)
        except psycopg.Error as error:
            if (query=='SELECT provider_state.native_protocol(%s,%s,%s,%s,%s) AS result'
                and connection.info.host=='127.0.0.1' and connection.info.dbname=='whereto_synthetic'
                and params and getattr(error.diag,'message_primary',None)=='session_revision'):
                p=params[1].obj
                with g.admin() as c:
                    c.execute('SET TRANSACTION READ ONLY');c.execute("SET LOCAL statement_timeout='1500ms'")
                    state=c.execute('SELECT revoked,revision=%s,expires<=provider_state.protocol_now(),round(extract(epoch FROM (expires-provider_state.protocol_now())))::integer FROM provider_state.sessions WHERE id=%s',(p.get('revision'),p.get('session'))).fetchone()
                    clocks=c.execute('SELECT value IS NOT NULL FROM provider_state.test_clock').fetchone()
                print(json.dumps(dict(event='real_fixture_session_refusal',verb=params[0],sqlstate=error.sqlstate,present=state is not None,revoked=state[0] if state else None,revisionMatches=state[1] if state else None,expired=state[2] if state else None,secondsRemaining=state[3] if state else None,testClockEnabled=clocks[0] if clocks else None)),flush=True)
            raise
    with patch.object(psycopg.Connection,'execute',execute):yield
