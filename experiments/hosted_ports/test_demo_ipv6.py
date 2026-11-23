"""Disposable IPv6-only probes; no hosted enrollment or provider requests.

Run only through run_demo_ipv6. The unchanged real SQL tests use authored policy
amounts and HTTP results; their financial/witness algorithms are not replaced.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import ipaddress,json,os,time,unittest
import psycopg
from psycopg import sql
from private_runtime.connections import PostgreSQL,SQLPool
from experiments.shared_state.contracts import Denied,Unavailable
from private_runtime.real_finance import test_sql as g

CA='/tmp/real-store-ca.pem'

class PortTests(unittest.TestCase):
    def setUp(self):
        g.fixture()
        self.configs={}
        for witness,roles in ((False,{'runtime':('whereto_real_worker','runtime','SYNTHETIC_WORKER_PASSWORD'),'issuer':('real_issuer_client','issuer','SYNTHETIC_ISSUER_PASSWORD'),'counter':('real_counter_client','counter','SYNTHETIC_COUNTER_PASSWORD')}),(True,{'witness':('real_witness_service','witness-factory','SYNTHETIC_WITNESS_SERVICE_PASSWORD'),'reader':('real_witness_reader','witness-factory','SYNTHETIC_WITNESS_READER_PASSWORD'),'counter-witness':('real_counter_witness_client','witness-counter','SYNTHETIC_COUNTER_PASSWORD')})):
            with g.admin(witness) as c:
                c.execute(g.contracts()['witness' if witness else 'operational'],prepare=False)
                for user,_,_ in roles.values():
                    c.execute(sql.SQL('GRANT USAGE ON SCHEMA private_runtime TO {}').format(sql.Identifier(user)))
                    c.execute(sql.SQL('GRANT EXECUTE ON FUNCTION private_runtime.connection_identity(),private_runtime.assert_session(integer) TO {}').format(sql.Identifier(user)))
                c.execute('SET LOCAL ROLE whereto_real_owner')
                stamp=c.execute('SELECT private_runtime.measure()').fetchone()[0]
                for user,purpose,_ in roles.values():c.execute('INSERT INTO private_runtime.enrollment VALUES(%s,%s,%s)',(user,purpose,stamp))
            for name,(user,purpose,secret) in roles.items():
                with g.admin(witness) as c:
                    memberships=tuple(r[0] for r in c.execute("SELECT parent.rolname::text FROM pg_roles r CROSS JOIN pg_roles parent WHERE r.rolname=%s AND parent.oid<>r.oid AND pg_has_role(r.oid,parent.oid,'MEMBER') ORDER BY parent.rolname",(user,)))
                self.configs[name]=PostgreSQL('localhost',5433 if witness else 5432,'whereto_witness' if witness else 'whereto_synthetic',user,g.sha((os.environ[secret]+'\0'+user).encode()),CA,stamp,memberships,2,purpose)

    def test_restricted_tls_pools_identity_deadlines_reuse_and_affinity(self):
        for name,cfg in self.configs.items():
            with self.subTest(role=name),SQLPool(cfg) as pool:
                with pool.connection() as c:
                    self.assertEqual(c.execute('SELECT host(inet_client_addr())').fetchone()[0],'::1')
                    pid=c.execute('SELECT pg_backend_pid()').fetchone()[0]
                    self.assertEqual(c.execute('SELECT session_user,current_user').fetchone(),(cfg.user,cfg.user))
                    self.assertTrue(c.execute('SELECT private_runtime.assert_session(%s)',(pid,)).fetchone()[0])
                    self.assertEqual(c.execute('SHOW statement_timeout').fetchone()[0],'1500ms')
                    self.assertEqual(c.execute('SHOW lock_timeout').fetchone()[0],'250ms')
                with pool.connection() as c:self.assertEqual(c.execute('SELECT pg_backend_pid()').fetchone()[0],pid)
                self.assertEqual(pool.created,1)

    def test_invalid_tls_contract_role_and_pooler_still_refuse(self):
        cfg=self.configs['runtime']
        for change in ({'host':'127.0.0.1'},{'contract':'0'*64},{'purpose':'issuer'}):
            with self.subTest(change=change),self.assertRaises((Denied,Unavailable)),SQLPool(replace(cfg,**change)):pass
        for change in ({'connection_mode':'session'},{'host':'fictional.pooler.supabase.com'},{'port':6543}):
            with self.assertRaises(Denied):replace(cfg,**change)
        with SQLPool(cfg) as pool:
            with self.assertRaises(Unavailable),pool.connection() as c:c.execute('DELETE FROM provider_rules.configuration')
            with g.admin() as c:c.execute('ALTER ROLE whereto_real_worker NOLOGIN')
            try:
                with self.assertRaises(Unavailable),pool.connection():pass
            finally:
                with g.admin() as c:c.execute('ALTER ROLE whereto_real_worker LOGIN')

    def test_redis_tls_named_acls_cas_absolute_expiry_and_refusal(self):
        import redis
        from private_runtime.redis_port import RedisConfiguration,EvidenceRedis
        from experiments.shared_state.redis_evidence import Keys
        from experiments.shared_state.evidence_models import VERSION
        root=redis.Redis(host='localhost',port=6380,ssl=True,ssl_ca_certs=CA,ssl_cert_reqs='required',ssl_check_hostname=True,password=os.environ['SYNTHETIC_REDIS_PASSWORD'])
        self.addCleanup(root.close)
        prefix=VERSION+':{private-staging:'+g.EPOCH+'}:*'
        commands=['+ping','+get','+set','+eval','+time','+zrangebyscore','+zcard','+zscore','+hlen','+zrem','+hdel','+hvals','+hget','+hset','+zadd','+zrevrange','+pexpireat']
        for name,allowed in (('demo-publisher',commands),('demo-reader',['+ping','+get','+time'])):
            root.execute_command('ACL','SETUSER',name,'reset','on','>fictional-test-only','~'+prefix,*allowed)
        self.assertEqual(root.config_get('maxmemory-policy')['maxmemory-policy'],'noeviction')
        cfg=RedisConfiguration('localhost',6380,'demo-publisher','fictional-test-only',CA,'private-staging',g.EPOCH)
        self.assertEqual(cfg.maximum,128*1024*1024) # Enrollment limit unchanged; not a full-capacity load test.
        with EvidenceRedis(cfg,Keys('demo',{'demo':b'd'*32})) as publisher,EvidenceRedis(replace(cfg,username='demo-reader'),Keys('demo',{'demo':b'd'*32})) as reader:
            key=publisher.path('private-staging',g.EPOCH,'a'*64);expiry=int(time.time()*1000)+3000
            publisher.publish(key,None,b'x'*28,expiry);self.assertEqual(reader.get(key),b'x'*28)
            self.assertEqual(root.pexpiretime(key),expiry)
            with self.assertRaises(Denied):publisher.publish(key,None,b'y'*28,expiry)
            with self.assertRaises(redis.RedisError):reader.client.set(key,b'forbidden')
            with self.assertRaises(redis.RedisError):publisher.client.config_set('maxmemory-policy','allkeys-lru')
            with self.assertRaises(redis.RedisError):publisher.client.get('outside-approved-prefix')
            root.delete(key)
            with self.assertRaisesRegex(Denied,'evidence_missing'):reader.get(key)
        with self.assertRaises(Unavailable),EvidenceRedis(replace(cfg,host='127.0.0.1'),Keys('demo',{'demo':b'd'*32})):pass

    def test_unchanged_statement_and_lock_deadlines_actually_cancel(self):
        with SQLPool(self.configs['runtime']) as pool:
            with self.assertRaises(Unavailable) as cancelled,pool.connection() as c:c.execute('SELECT pg_sleep(1.7)')
            self.assertEqual(cancelled.exception.__context__.sqlstate,'57014')
            with g.admin() as blocker:
                blocker.execute('SELECT pg_advisory_lock(529231)')
                try:
                    with self.assertRaises(Unavailable) as locked,pool.connection() as c:c.execute('SELECT pg_advisory_lock(529231)')
                    self.assertEqual(locked.exception.__context__.sqlstate,'55P03')
                finally:blocker.execute('SELECT pg_advisory_unlock(529231)')
            with pool.connection() as c:self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)


@contextmanager
def ipv6_connections():
    if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:
        raise RuntimeError('Disposable network-none fixture required')
    original=psycopg.connect;observed=set();opened=0
    def ipv6(*args,**kw):
        nonlocal opened
        if args or kw.get('host') not in ('127.0.0.1','localhost') or kw.get('port',5432) not in (5432,5433):raise RuntimeError('Loopback SQL only')
        # Preserve explicitly selected TLS host/CA so negative tests cannot be
        # repaired by the probe. Project only old fixture IPv4 addresses to DNS.
        if 'sslmode' not in kw:kw['host']='localhost'
        kw.update(hostaddr='::1')
        kw.setdefault('sslmode','verify-full');kw.setdefault('sslrootcert',CA)
        c=original(**kw)
        try:
            with c.cursor(row_factory=psycopg.rows.tuple_row) as cursor:
                address=cursor.execute('SELECT host(inet_client_addr())').fetchone()[0]
            if ipaddress.ip_address(address)!=ipaddress.ip_address('::1') or not c.pgconn.ssl_in_use:raise RuntimeError('IPv6/TLS required')
            observed.add((c.info.dbname,address));opened+=1;c.commit();return c
        except BaseException:c.close();raise
    with patch.object(psycopg,'connect',ipv6):
        yield lambda:dict(verifiedSQLConnections=opened,observed=[dict(database=d,address=a) for d,a in sorted(observed)])


@contextmanager
def ipv6_observer():
    # The frozen observer deliberately rejects non-IPv4 fixture hostnames and
    # would mask an expected SQL refusal with nonfixture_diagnostic. Keep it
    # frozen; this probe logs only bounded metadata and rethrows the SQL error.
    from experiments.shared_state import financial_diagnostics as fd
    execute=psycopg.Connection.execute;events=0
    def observed(c,query,params=None,**kw):
        nonlocal events
        try:return execute(c,query,params,**kw)
        except psycopg.Error as error:
            if events<128 and c.info.host in ('localhost','127.0.0.1') and c.info.dbname in ('whereto_synthetic','whereto_witness'):
                events+=1
                print(json.dumps(dict(event='ipv6_sql_refusal',sqlstate=error.sqlstate,category=fd.category(error),locations=fd.locations(error))),flush=True)
            raise
    with patch.object(psycopg.Connection,'execute',observed):yield


def concurrent_ipv6(*args):
    from experiments.shared_state import financial_diagnostics as fd
    with ipv6_connections(),patch.object(fd,'observe',ipv6_observer):g.concurrent(*args)


def crash_count_ipv6():
    with ipv6_connections():g.crash_count()


def run():
    names=['private_runtime.real_finance.test_sql.'+cls.__name__+'.'+n for cls in (g.Tests,g.AdversarialTests) for n in unittest.defaultTestLoader.getTestCaseNames(cls)]
    names.append(__name__+'.PortTests')
    start=time.monotonic()
    with ipv6_connections() as stats,ipv6_observer(),patch.object(g,'concurrent',concurrent_ipv6),patch.object(g,'crash_count',crash_count_ipv6):
        result=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    print(json.dumps(dict(event='demo_ipv6_result',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),excludedSpawnCases=[],childIPv6Guards=True,connectionCountScope='parent process only; spawned helpers independently enforce IPv6/TLS',**stats(),seconds=round(time.monotonic()-start,3),liveSupabaseVerified=False,cloudIPv6Verified=False)),flush=True)
    raise SystemExit(not result.wasSuccessful())
