"""Fictional role/schema enrollment only in an independently disposable fixture."""
import unittest,json,time,os
from pathlib import Path
from dataclasses import replace
from contextlib import ExitStack
from psycopg import sql
import psycopg,redis
from private_runtime.connections import PostgreSQL,SQLPool
from private_runtime.registry import PURPOSES
from private_runtime.redis_port import RedisConfiguration,EvidenceRedis
from experiments.shared_state.redis_evidence import Keys
from experiments.shared_state import test_store as t,test_application_grants as g
from experiments.shared_state.contracts import Denied,Unavailable

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.private=json.loads(Path('/tmp/ports-control.json').read_text());cls.cfg=cls.private['configs'];cls.ca='/tmp/hosted-ports-ca.pem';cls.contracts={}
  for domain,admin in [('operational',t.admin),('witness',g.witness_admin)]:
   with admin() as c:
    c.execute(Path('/app/deployment/sql/hosted-'+domain+'-contract-v1.sql').read_text(),prepare=False)
    users=sorted({v[k]['user'] for v in cls.cfg.values() for k in ('database','issuer','witness') if k in v and (v[k]['port']==5432)==(domain=='operational')})
    c.execute('SET LOCAL ROLE whereto_synthetic_owner')
    for user in users:
     c.execute(sql.SQL('GRANT USAGE ON SCHEMA private_runtime TO {}').format(sql.Identifier(user)))
     c.execute(sql.SQL('GRANT EXECUTE ON FUNCTION private_runtime.connection_identity(),private_runtime.assert_session(integer) TO {}').format(sql.Identifier(user)))
    stamp=c.execute('SELECT private_runtime.measure()').fetchone()[0]
    for user in users:
     purpose=next(PURPOSES['backend' if role.startswith('worker') else role][key] for role,v in cls.cfg.items() for key in ('database','issuer','witness') if key in v and v[key]['user']==user)
     c.execute('INSERT INTO private_runtime.enrollment VALUES(%s,%s,%s)',(user,purpose,stamp))
    cls.contracts[domain]=stamp
 def config(self,role='factory',kind='database',maximum=2):
  d=self.cfg[role][kind]
  with (t.admin() if d['port']==5432 else g.witness_admin()) as c:
   memberships=tuple(r[0] for r in c.execute("SELECT parent.rolname::text FROM pg_roles r CROSS JOIN pg_roles parent WHERE r.rolname=%s AND parent.oid<>r.oid AND pg_has_role(r.oid,parent.oid,'MEMBER') ORDER BY parent.rolname",(d['user'],)))
  return PostgreSQL('localhost',d['port'],d['dbname'],d['user'],d['password'],self.ca,self.contracts['operational' if d['port']==5432 else 'witness'],memberships,maximum,PURPOSES['backend' if role.startswith('worker') else role][kind])
 def test_01_persistent_reuse_exact_role_transaction_reset(self):
  with SQLPool(self.config()) as pool:
   with pool.connection() as c:
    pid=c.execute('SELECT pg_backend_pid()').fetchone()[0];c.execute("SET application_name='untrusted-state'");c.execute('SET statement_timeout=0');c.execute('SET lock_timeout=0')
   with pool.connection() as c:
    self.assertEqual(c.execute('SELECT pg_backend_pid()').fetchone()[0],pid);self.assertNotEqual(c.execute('SHOW application_name').fetchone()[0],'untrusted-state');self.assertTrue(c.pgconn.ssl_in_use);self.assertEqual(c.execute('SHOW statement_timeout').fetchone()[0],'1500ms');self.assertEqual(c.execute('SHOW lock_timeout').fetchone()[0],'250ms')
   self.assertEqual(pool.created,1)
  with self.assertRaises(Denied),pool.connection():pass
 def test_02_runtime_direct_writes_and_admin_roles_refused(self):
  with SQLPool(self.config()) as pool:
   for query in ('DELETE FROM synthetic_state.operations','UPDATE grant_rules.configuration SET rates=\'{}\'','DROP SCHEMA private_runtime CASCADE'):
    with self.assertRaises(Unavailable),pool.connection() as c:c.execute(query)
   with pool.connection() as c:self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
  with self.assertRaises(Denied),SQLPool(replace(self.config(),user='whereto_synthetic_admin',password=os.environ['SYNTHETIC_ADMIN_PASSWORD'])):pass
 def test_03_wrong_host_ca_identity_membership_and_contract(self):
  for change in ({'host':'127.0.0.1'},{'contract':'0'*64},{'user':'synthetic_issuer_client','password':self.cfg['factory']['issuer']['password']},{'database':'whereto_witness'}):
   with self.assertRaises((Denied,Unavailable)),SQLPool(replace(self.config(),**change)):pass
 def test_04_pool_exhaustion_does_not_queue_or_fallback(self):
  with SQLPool(self.config(maximum=1)) as pool,pool.connection():
   with self.assertRaises(Unavailable),pool.connection():pass
   self.assertEqual(pool.created,1)
 def test_05_issuer_counter_delivery_recovery_roles_all_validate(self):
  for role,key in [('factory','issuer'),('counter','database'),('dispatcher','database'),('recovery','witness'),('worker-a','witness')]:
   with SQLPool(self.config(role,key)) as pool,pool.connection() as c:self.assertEqual(c.execute('SELECT current_user').fetchone()[0],self.cfg[role][key]['user'])
 def test_06_sql_clock_override_is_not_admitted(self):
  with t.admin() as c:c.execute("UPDATE synthetic_state.test_clock SET value=clock_timestamp()")
  try:
   with self.assertRaises(Unavailable),SQLPool(self.config()):pass
  finally:
   with t.admin() as c:c.execute('UPDATE synthetic_state.test_clock SET value=NULL')
 def test_07_changed_schema_and_policy_refuse(self):
  with t.admin() as c:c.execute('CREATE TABLE synthetic_state.unreviewed(id int)')
  try:
   with self.assertRaises(Unavailable),SQLPool(self.config()):pass
  finally:
   with t.admin() as c:c.execute('DROP TABLE synthetic_state.unreviewed')
 def test_08_redis_tls_cas_absolute_expiry(self):
  # Bootstrap only: create restricted role before the runtime port is constructed.
  root=redis.Redis(host='localhost',port=6380,ssl=True,ssl_ca_certs=self.ca,ssl_cert_reqs='required',ssl_check_hostname=True,password=os.environ['SYNTHETIC_REDIS_PASSWORD'])
  password='fictional-port-password';root.execute_command('ACL','SETUSER','port_runtime','on','>'+password,'~52-encrypted-evidence-local-v1:*','+get','+set','+ping','+eval','+time','+zrangebyscore','+zcard','+zscore','+hlen','+zrem','+hdel','+hvals','+hget','+hset','+zadd','+zrevrange','+pexpireat')
  # Use the actual versioned evidence namespace, not a fabricated schema prefix.
  from experiments.shared_state.evidence_models import VERSION
  root.execute_command('ACL','SETUSER','port_runtime','~'+VERSION+':*')
  self.assertEqual(root.config_get('maxmemory-policy')['maxmemory-policy'],'noeviction')
  cfg=RedisConfiguration('localhost',6380,'port_runtime',password,self.ca,'private-staging','e'*64)
  with EvidenceRedis(cfg,Keys('key1',{'key1':b'k'*32})) as r:
   key=r.path('private-staging','e'*64,'1'*64);expires=int(time.time()*1000)+1000;r.publish(key,None,b'x'*28,expires);self.assertEqual(r.get(key),b'x'*28)
   with self.assertRaises(Denied):r.publish(key,None,b'y'*28,expires)
   with self.assertRaises(Denied):r.path('private-staging','f'*64,'1'*64)
   with self.assertRaises(redis.RedisError):r.client.config_set('maxmemory-policy','allkeys-lru')
  with self.assertRaises(Denied):r.get(key)
  with self.assertRaises(Unavailable),EvidenceRedis(replace(cfg,host='127.0.0.1'),Keys('key1',{'key1':b'k'*32})):pass
  root.close()
 def test_09_wrong_purpose_and_session_affinity_refuse(self):
  for change in ({'connection_mode':'transaction'},{'host':'reviewed-pooler.invalid'},{'port':6543}):
   with self.assertRaises(Denied):replace(self.config(),**change)
  with self.assertRaises(Denied),SQLPool(replace(self.config(),purpose='issuer')):pass
  with SQLPool(self.config('factory','witness')) as pool:
   with pool.connection() as c:
    pid=c.execute('SELECT pg_backend_pid()').fetchone()[0]
    self.assertTrue(c.execute('SELECT private_runtime.assert_session(%s)',(pid,)).fetchone()[0])
   with self.assertRaises(Unavailable),pool.connection() as c:c.execute('SELECT private_runtime.assert_session(%s)',(pid+1,))
 def test_10_role_revocation_blocks_reused_connection(self):
  cfg=self.config()
  with SQLPool(cfg) as pool:
   with t.admin() as c:c.execute(sql.SQL('ALTER ROLE {} NOLOGIN').format(sql.Identifier(cfg.user)))
   try:
    with self.assertRaises(Denied),pool.connection():pass
   finally:
    with t.admin() as c:c.execute(sql.SQL('ALTER ROLE {} LOGIN').format(sql.Identifier(cfg.user)))
   with pool.connection() as c:self.assertEqual(c.execute('SELECT current_user').fetchone()[0],cfg.user)
 def test_11_equivalent_readonly_pool_reuse_measurement(self):
  from time import perf_counter
  cfg=self.config();values={}
  for mode in ('fresh','reused'):
   rows=[];pool=SQLPool(cfg)
   try:
    for _ in range(12):
     start=perf_counter()
     with pool.connection() as c:self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
     rows.append(round((perf_counter()-start)*1000,3))
     if mode=='fresh':pool.close();pool=SQLPool(cfg)
    values[mode]={'milliseconds':rows,'scope':'Restricted TLS checkout, full enrollment verification, SELECT 1 and reset only; not user request/cloud latency'}
   finally:pool.close()
  Path('/tmp/hosted-port-pool-timing.json').write_text(json.dumps(values))
if __name__=='__main__':unittest.main()
