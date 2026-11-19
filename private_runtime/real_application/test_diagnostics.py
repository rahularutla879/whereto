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

@contextmanager
def hosted(role):
    """Sanitized SQL/TLS cause tracing in independently spawned fixture roles."""
    import psycopg
    from private_runtime.connections import SQLPool
    from private_runtime.https import HTTPS,Refused
    original=psycopg.Connection.execute;take=SQLPool._take;request=HTTPS.request
    def execute(c,q,params=None,**kw):
        try:return original(c,q,params,**kw)
        except psycopg.Error as e:
            if c.info.host in ('localhost','127.0.0.1') and c.info.dbname in ('whereto_synthetic','whereto_witness'):
                from experiments.shared_state.financial_diagnostics import category,locations
                print(json.dumps(dict(event='real_hosted_sql_refusal',role=role,sqlstate=e.sqlstate,reason=category(e),locations=locations(e))),flush=True)
            raise
    def acquire(pool):
        try:return take(pool)
        except BaseException as e:
            print(json.dumps(dict(event='real_hosted_pool_refusal',role=role,purpose=pool.c.purpose,count=pool._count,idle=pool._idle.qsize(),category=type(e).__name__)),flush=True);raise
    def send(http,endpoint,method,path,body,headers):
        try:return request(http,endpoint,method,path,body,headers)
        except Refused as e:
            print(json.dumps(dict(event='real_hosted_tls_refusal',role=role,path=path,reason=str(e),underlying=type(e.__context__).__name__ if e.__context__ else None,errno=getattr(e.__context__,'errno',None))),flush=True);raise
    with patch.object(psycopg.Connection,'execute',execute),patch.object(SQLPool,'_take',acquire),patch.object(HTTPS,'request',send):yield
