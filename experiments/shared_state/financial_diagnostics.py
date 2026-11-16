"""Offline-only observer for unchanged disposable financial/recovery tests.

Never imported by an application or image. No credential discovery, provider I/O,
SQL mutation, policy changes or retry. Raw SQL, params and messages are not logged.
"""
from contextlib import contextmanager,nullcontext
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import threading
import unittest
from unittest.mock import patch

_test = None
_guard = threading.local()
_events = 0


def category(error):
    value = getattr(getattr(error, 'diag', None), 'message_primary', None)
    if value == 'canceling statement due to statement timeout':return 'statement_timeout'
    if value == 'canceling statement due to user request':return 'user_cancellation'
    return value if isinstance(value, str) and re.fullmatch(r'[a-z_]{1,80}', value) else 'redacted'


def locations(error):
    context = getattr(getattr(error, 'diag', None), 'context', '') or ''
    return [dict(function=name, line=int(line)) for name,line in
            re.findall(r'(?:PL/pgSQL|SQL) function ([a-z_][a-z_0-9.]*)\([^\n]*?\) line ([0-9]+)',context)]


def snapshot():
    """Aggregate metadata only, using disposable fixture admin read-only access."""
    from experiments.shared_state.test_store import admin
    out={}
    queries={
      'clock':"SELECT round(extract(epoch FROM (clock_timestamp()-last_seen))*1000)::bigint FROM synthetic_state.finance_time WHERE id=1",
      'policy':"SELECT version,rate_version,accounting_identity,profile FROM synthetic_state.finance_policy WHERE id=1",
      'evidence_version':"SELECT environment,epoch,version FROM synthetic_state.evidence_policy WHERE id=1",
      'sessions':"SELECT count(*),count(*) FILTER(WHERE revoked),count(*) FILTER(WHERE expires<=clock_timestamp()),max(revision),max(fence) FROM synthetic_state.sessions",
      'anchors':"SELECT count(*),min(generation),max(generation),count(*) FILTER(WHERE expires_ms<=floor(extract(epoch FROM clock_timestamp())*1000)) FROM synthetic_state.evidence_anchors",
      'financial':"SELECT count(*),coalesce(sum(charge),0) FROM synthetic_state.operations",
      'attestations':"SELECT count(*),count(*) FILTER(WHERE expires<=clock_timestamp()) FROM synthetic_state.evidence_attestations"
    }
    for key,sql in queries.items():
        try:
            with admin() as c:
                c.execute('SET TRANSACTION READ ONLY');c.execute("SET LOCAL statement_timeout='1500ms'")
                out[key]=list(c.execute(sql).fetchone())
        except Exception:out[key]='unavailable'
    return out


@contextmanager
def observe():
    import psycopg
    original=psycopg.Connection.execute
    def execute(connection,query,params=None,**kwargs):
        global _events
        try:return original(connection,query,params,**kwargs)
        except psycopg.Error as error:
            if not getattr(_guard,'busy',False) and _events<600:
                _guard.busy=True
                try:
                    # Only known fixture databases and local TCP, never an owner DB.
                    if connection.info.dbname not in ('whereto_synthetic','whereto_witness') or connection.info.host!='127.0.0.1':raise RuntimeError('nonfixture_diagnostic')
                    _events+=1
                    # Log identifiers only, never SQL statements or bound values.
                    statement=str(query) if type(query) is str else ''
                    function=re.search(r'SELECT (synthetic_state|witness|grant_rules)\.([a-z_]+)\(',statement)
                    record=dict(event='synthetic_sql_refusal',test=_test,sqlstate=error.sqlstate,
                                reason=category(error),locations=locations(error),
                                statementFunction='.'.join(function.groups()) if function else 'other_statement',
                                protectedState=snapshot())
                    print(json.dumps(record,sort_keys=True,default=str),flush=True)
                finally:_guard.busy=False
            raise
    with patch.object(psycopg.Connection,'execute',execute):yield


class Result(unittest.TextTestResult):
    def startTest(self,test):
        global _test
        _test=test.id()
        super().startTest(test)


def benchmark():
    """Read-only catalog lookup, same1500ms deadline; no policy or grant mutation."""
    from time import monotonic
    from experiments.shared_state.test_store import admin
    for index in range(5):
        began=monotonic();state=None
        try:
            with admin() as c:
                c.execute('SET TRANSACTION READ ONLY')
                c.execute("SET LOCAL statement_timeout='1500ms'")
                began=monotonic()
                row=c.execute("SELECT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name='UTC')").fetchone()
                if row!=(True,):raise RuntimeError('catalog_lookup_refused')
        except Exception as error:state=getattr(error,'sqlstate','non_sql_failure')
        print(json.dumps(dict(event='timezone_catalog_benchmark',sample=index,elapsedMs=round((monotonic()-began)*1000,3),sqlstate=state)),flush=True)


def child(names):
    if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:
        raise RuntimeError('isolated_fixture_required')
    benchmark()
    if not names:return
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names)
    with observe():result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)


def host(cohort):
    from experiments.shared_state import run_grants as fixture
    root=fixture.ROOT
    paths=list((root/'experiments/shared_state').glob('*.py'))+list((root/'experiments/shared_state').glob('*.sql'))
    pins={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in paths}
    print('Diagnostic source pins '+json.dumps(pins,sort_keys=True),flush=True)
    original=fixture.run;checked=fixture.subprocess.check_output;volumes=[]
    def capture(command,**kwargs):
        value=checked(command,**kwargs)
        if list(command)[:len(fixture.D)+2]==fixture.D+['run','-d'] and fixture.REDIS in command:
            container=value.strip().decode() if isinstance(value,bytes) else value.strip()
            data=json.loads(checked(fixture.D+['inspect',container]))[0]
            volumes.extend(m['Name'] for m in data['Mounts'] if m['Type']=='volume' and m['Destination']=='/data')
        return value
    def run(*args,**kwargs):
        if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','unittest'):
            if cohort=='recovery':return subprocess.CompletedProcess(args,0)
            if cohort=='benchmark':return original('exec',args[1],'python','-m','experiments.shared_state.financial_diagnostics','--child')
            names={'targeted':['ApplicationGrantTests.test_pending_date','GrantTests.test_calendar_rollover_never_renews_total_and_revocation_stops'],
                   'remaining':['GrantTests','InferenceTests','ApplicationGrantTests.test_refresh'],
                   'all':['ApplicationGrantTests','GrantTests','InferenceTests']}[cohort]
            return original('exec',args[1],'python','-m','experiments.shared_state.financial_diagnostics','--child',*['experiments.shared_state.test_application_grants.'+n for n in names])
        return original(*args,**kwargs)
    fixture.run=run
    try:
        with patch.object(fixture.subprocess,'check_output',capture):fixture.main(recovery=cohort in ('all','recovery'))
    finally:
        fixture.run=original
        for volume in volumes:original('volume','rm',volume,stdout=subprocess.DEVNULL)
        if any(sha256((root/n).read_bytes()).hexdigest()!=h for n,h in pins.items()):raise RuntimeError('diagnostic_source_mutation')
        print('Diagnostic source pin preservation: PASS',flush=True)


if __name__=='__main__':
    import argparse,signal
    parser=argparse.ArgumentParser();parser.add_argument('--cohort',choices=('targeted','remaining','all','recovery','benchmark'),default='all');parser.add_argument('--child',nargs='*');parser.add_argument('--native-resources',action='store_true')
    args=parser.parse_args()
    if args.child is not None:child(args.child)
    else:
        def deadline(*_):raise TimeoutError('Bounded offline diagnostic deadline')
        signal.signal(signal.SIGALRM,deadline);signal.alarm(1200)
        from experiments.shared_state.run_native import local_resources
        with local_resources() if args.native_resources else nullcontext():host(args.cohort)
