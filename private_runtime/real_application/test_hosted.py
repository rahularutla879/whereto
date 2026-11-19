"""Disposable installer for the real Ports path; never projected into images."""
from hashlib import sha256
from copy import deepcopy
from dataclasses import asdict
from psycopg import sql
from .test_native import g
from private_runtime.real_finance.profile import contracts
from private_runtime.registry import PURPOSES
from experiments.service_isolation.auth import b64
from experiments.shared_state.evidence_models import canonical

CA='/tmp/real-store-ca.pem'
def enroll(configs,credentials):
    from .identity import verify_application
    source=verify_application()
    redis=g.cache().client
    for name,commands in [('real-publisher',['+ping','+get','+set','+eval','+time','+zrangebyscore','+zcard','+zrem','+hlen','+hdel','+hvals','+hget','+hset','+zadd','+zscore','+zrevrange','+pexpireat']),('real-reader',['+ping','+get'])]:
        import os
        password=sha256((os.environ['SYNTHETIC_REDIS_PASSWORD']+'\0'+name).encode()).hexdigest()
        redis.execute_command('ACL','SETUSER',name,'reset','on','>'+password,'~52-real-source:*',*commands)
    users={False:{},True:{}}
    for name,c in configs.items():
        if name=='frontend':continue
        role=c['service'];c.update(runtimeProfile='52-real-native-six-role-v4',sourceBuild=source,openaiProject=g.PROJECT,sql={})
        for key,raw in credentials[name].items():
            key={'runtime':'database','counter':'database','delivery':'database'}.get(key,key);wit=raw['port']==5433
            with g.admin(wit) as conn:members=tuple(row[0] for row in conn.execute("SELECT parent.rolname::text FROM pg_roles r CROSS JOIN pg_roles parent WHERE r.rolname=%s AND parent.oid<>r.oid AND pg_has_role(r.oid,parent.oid,'MEMBER') ORDER BY parent.rolname",(raw['user'],)))
            purpose=PURPOSES[role][key];users[wit][raw['user']]=purpose
            c['sql'][key]=dict(host='localhost',port=raw['port'],database=raw['dbname'],user=raw['user'],password=raw['password'],ca_file=CA,contract='0'*64,memberships=members,maximum=4,purpose=purpose)
        if role in ('factory','dispatcher'):
            c.update(authorityKey=b64(g.KEY),limits=asdict(g.LIMITS),evidenceKeyId='real-fixture',encryptionKey=b64(b'f'*32))
            username='real-publisher' if role=='factory' else 'real-reader'
            c['redis']=dict(host='localhost',port=6380,username=username,password=sha256((os.environ['SYNTHETIC_REDIS_PASSWORD']+'\0'+username).encode()).hexdigest(),ca_file=CA,environment='private-staging',epoch=g.EPOCH)
        if role=='dispatcher':c['dispatchOwners']=[dict(slot=n,build=c['build'],epoch=c['epoch'],principal=n) for n in configs if n.startswith('factory-')]
        if role=='factory':c.update(locatorKey=b64(b'l'*32),financialRoot=g.ROOT)
    for wit in (False,True):
        with g.admin(wit) as conn:
            conn.execute(contracts()['witness' if wit else 'operational'],prepare=False)
            conn.execute('SET LOCAL ROLE whereto_real_owner')
            for user in users[wit]:
                conn.execute(sql.SQL('GRANT USAGE ON SCHEMA private_runtime TO {}').format(sql.Identifier(user)))
                conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION private_runtime.connection_identity(),private_runtime.assert_session(integer) TO {}').format(sql.Identifier(user)))
            stamp=conn.execute('SELECT private_runtime.measure()').fetchone()[0]
            for user,purpose in users[wit].items():conn.execute('INSERT INTO private_runtime.enrollment VALUES(%s,%s,%s)',(user,purpose,stamp))
        for c in configs.values():
            for cfg in c.get('sql',{}).values():
                if (cfg['port']==5433)==wit:cfg['contract']=stamp
    # Only the fixture controller/independent witness admin can enroll these rows.
    # Both factories use the same login but different instance URLs/signing keys;
    # enroll each exact permitted configuration under that principal.
    with g.admin(True) as conn:
        conn.execute('SET LOCAL ROLE whereto_real_owner')
        financial=conn.execute("SELECT encode(sha256(convert_to(grant_doc::text,'UTF8')),'hex') FROM provider_rules.configuration WHERE id=1").fetchone()[0]
        approved=list(configs.items())
        replacement=deepcopy(configs['backend']);replacement['networkTargets']['factory']['url']=configs['dispatcher']['networkTargets']['factory-b']['url'];approved.append(('backend-replacement',replacement))
        for name,c in approved:
            if name=='frontend':continue
            user=c['sql']['witness']['user']
            conn.execute('INSERT INTO provider_witness.runtime_enrollment VALUES(%s,%s,%s,%s,clock_timestamp()+interval \'1 hour\',%s)',(user,sha256(canonical(c)).hexdigest(),c['build'],c['epoch'],__import__('psycopg').types.json.Jsonb(dict(qualification='b'*64,pricing='a'*64,financial=financial,credentials='c'*64,content='e'*64,security='f'*64,source=source))))
