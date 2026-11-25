"""Explicit fictional-only B1 check. Cached image, network-none, no host mounts.

No Supabase connections, credential discovery, genuine key or software download.
Requires the existing disposable Colima profile already running; never starts it.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json,os,subprocess,uuid,time
from deployment.b1_pipeline import stream
ROOT=Path(__file__).resolve().parents[1]
D=['/opt/homebrew/bin/docker','--context','colima-whereto-task52']
PG='postgres:17-bookworm@sha256:665dc7b37ac52a17e298511414c21d23ffa4e6a6ef6225b3e5d59c7afb35e994'
SSL='/opt/homebrew/bin/openssl'

def run(argv,*,data=None):
    r=subprocess.run(argv,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    if r.returncode:raise RuntimeError('fixture command failed: '+r.stderr.decode(errors='replace')[-1400:])
    return r.stdout

def inventory():
    return {k:set(run(D+a).decode().splitlines()) for k,a in {'volumes':['volume','ls','-q'],'containers':['ps','-aq'],'images':['image','ls','-q','--no-trunc']}.items()}

def main():
    before=inventory();created=[];result={'fictionalOnly':True,'liveDatabaseConnections':0,'genuineKeysAccessed':False,'image':PG}
    run(D+['image','inspect',PG]) # --pull=never below; refuse missing cache.
    def create():
        name='whereto-b1-fixture-'+uuid.uuid4().hex[:12]
        run(D+['run','--pull=never','-d','--name',name,'--network','none','--user','postgres','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--memory-swap','512m','--cpus','1','--tmpfs','/var/lib/postgresql/data:rw,uid=999,gid=999,mode=0700','--tmpfs','/var/run/postgresql:rw,uid=999,gid=999,mode=0700','--tmpfs','/tmp:rw,mode=1777','-e','POSTGRES_USER=b1_restore_admin','-e','POSTGRES_DB=whereto_b1_verify','-e','POSTGRES_HOST_AUTH_METHOD=trust',PG,'postgres','-c',"listen_addresses=",'-c','log_min_error_statement=panic','-c','log_error_verbosity=terse'])
        created.append(name)
        for _ in range(30):
            if subprocess.run(D+['exec',name,'pg_isready','-U','b1_restore_admin','-d','whereto_b1_verify'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return name
            time.sleep(.2)
        raise RuntimeError('fixture readiness')
    def sql(c,text,user='b1_restore_admin'):
        return run(D+['exec','-i',c,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U',user,'-d','whereto_b1_verify'],data=text.encode())
    try:
        source=create();target=create()
        sql(source,'CREATE ROLE postgres LOGIN INHERIT NOSUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS; CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN; GRANT CREATE ON DATABASE whereto_b1_verify TO postgres;')
        migrations='\n'.join((ROOT/'backend/migrations'/n).read_text() for n in ('0001_initial_planning.sql','0002_private_saved_plans.sql'))
        sql(source,'SET ROLE postgres;\n'+migrations)
        sql(source,"""INSERT INTO whereto.plans(id,original_request,data_mode,access_hash) VALUES('00000000-0000-4000-8000-000000000001','FICTIONAL ONLY','mock',repeat('a',64));
INSERT INTO whereto.plan_constraints(plan_id,outing_date,location_text,activities) VALUES('00000000-0000-4000-8000-000000000001','2030-01-01','FICTIONAL',ARRAY['coffee']);
INSERT INTO whereto.generated_itineraries(id,plan_id,option_position,candidate_id,feasibility) VALUES('00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001',0,'FICTIONAL','provisional');
INSERT INTO whereto.itinerary_stops(id,itinerary_id,position,activity) VALUES('00000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000002',0,'coffee');
INSERT INTO whereto.source_metadata(id,stop_id,reference_kind,provider,external_id,evidence_status) VALUES('00000000-0000-4000-8000-000000000004','00000000-0000-4000-8000-000000000003','venue','mock','FICTIONAL','fictional');
INSERT INTO whereto.schema_migrations(version,checksum) VALUES('FICTIONAL',repeat('f',64));""",user='postgres')
        baseline=(ROOT/'deployment/sql/b1-application-baseline-readonly-v2.sql').read_text()
        initial=[json.loads(l) for l in sql(source,baseline,user='postgres').splitlines()]
        with TemporaryDirectory(prefix='whereto-b1-fictional-') as tmp:
            p=Path(tmp);key=p/'fictional-private.pem';cert=p/'fictional-public.pem';cipher=p/'fictional.cms';plain=p/'fictional.dump';password=b'FICTIONAL-ONLY-NOT-OWNER-SECRET\n'
            run([SSL,'req','-new','-x509','-newkey','rsa:3072','-cipher','aes-256-cbc','-sha256','-days','1','-subj','/CN=FICTIONAL-B1-ONLY','-passout','stdin','-keyout',str(key),'-out',str(cert)],data=password)
            key.chmod(0o600);assert b'ENCRYPTED PRIVATE KEY' in key.read_bytes().splitlines()[0]
            enc=[SSL,'cms','-encrypt','-binary','-stream','-outform','DER','-aes-256-gcm','-recip',str(cert),'-keyopt','rsa_padding_mode:oaep','-keyopt','rsa_oaep_md:sha256','-keyopt','rsa_mgf1_md:sha256']
            receipt=stream(D+['exec',source,'pg_dump','-U','postgres','-d','whereto_b1_verify','--format=custom','--schema=whereto','--strict-names','--lock-wait-timeout=250ms','--no-password'],enc,cipher,producer_env={'HOME':str(Path.home()),'PATH':os.defpath})
            dec=[SSL,'cms','-decrypt','-binary','-inform','DER','-in',str(cipher),'-recip',str(cert),'-inkey',str(key),'-passin','stdin']
            decrypted=run(dec,data=password);plain.write_bytes(decrypted);plain.chmod(0o600)
            # Authentication failure must never reach pg_restore.
            changed=bytearray(cipher.read_bytes());changed[-12]^=1;bad=p/'tampered.cms';bad.write_bytes(changed)
            baddec=dec.copy();baddec[baddec.index('-in')+1]=str(bad)
            tamper=subprocess.run(baddec,input=password,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15);assert tamper.returncode!=0
            wrong=subprocess.run(dec,input=b'FICTIONAL-WRONG\n',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15);assert wrong.returncode!=0
            sql(target,(ROOT/'deployment/sql/b1-fixture-roles-v1.sql').read_text())
            run(D+['exec','-i',target,'pg_restore','--exit-on-error','--single-transaction','--no-password','-U','b1_restore_admin','-d','whereto_b1_verify'],data=decrypted)
            restored=[json.loads(l) for l in sql(target,baseline,user='postgres').splitlines()]
            facts=lambda rows:[r for r in rows if r['fact'] in ('table','coverage','schema_fingerprint','external_dependencies','application_roles')]
            if facts(initial)!=facts(restored):
                print(json.dumps({'differingFacts':[(a,b) for a,b in zip(facts(initial),facts(restored)) if a!=b]}),flush=True)
                begin=baseline.index('WITH metadata AS (');end=baseline.index('-- Order by fixed-length',begin)
                query=baseline[begin:end];query=query[:query.index("SELECT jsonb_build_object('fact','schema_fingerprint'")]+"SELECT jsonb_build_object('kind',kind,'identity',identity,'value',value) FROM metadata ORDER BY kind,identity;"
                a=sql(source,query,user='postgres').splitlines();b=sql(target,query,user='postgres').splitlines()
                print(json.dumps({'metadataOnlyInSource':[json.loads(x) for x in a if x not in b],'metadataOnlyInTarget':[json.loads(x) for x in b if x not in a]}),flush=True)
                raise AssertionError('restored baseline mismatch')
            reference=next(r['sha256'] for r in restored if r['fact']=='schema_fingerprint')
            sql(target,'GRANT SELECT ON whereto.schema_migrations TO whereto_plan_runtime;',user='postgres')
            altered=[json.loads(l) for l in sql(target,baseline,user='postgres').splitlines()]
            assert next(r['sha256'] for r in altered if r['fact']=='schema_fingerprint')!=reference
            sql(target,'REVOKE SELECT ON whereto.schema_migrations FROM whereto_plan_runtime; ALTER TABLE whereto.plans NO FORCE ROW LEVEL SECURITY;',user='postgres')
            altered=[json.loads(l) for l in sql(target,baseline,user='postgres').splitlines()]
            assert next(r['sha256'] for r in altered if r['fact']=='schema_fingerprint')!=reference
            sql(target,'ALTER TABLE whereto.plans FORCE ROW LEVEL SECURITY;',user='postgres')
            restored=[json.loads(l) for l in sql(target,baseline,user='postgres').splitlines()]
            assert facts(initial)==facts(restored)
            assert all(r['count']==1 for r in restored if r['fact']=='table')
            assert sql(target,"SELECT count(*) FROM whereto.plans",user='whereto_plan_runtime').strip()==b'0'
            after=[json.loads(l) for l in sql(source,baseline,user='postgres').splitlines()];assert initial==after
            result.update(cryptoRoundTrip=True,ACLMutationDetected=True,forcedRLSMutationDetected=True,tamperRefused=True,wrongPassphraseRefused=True,PG17Version=run(D+['exec',source,'pg_dump','--version']).decode().strip(),tablesRestored=6,rowsPerTable=1,metadataAndContentEqual=True,forcedRLSAndUncredentialedRefusal=True,sourceBeforeAfterEqual=True,ciphertextBytes=receipt['bytes'])
    finally:
        for c in reversed(created):run(D+['rm','-f',c])
        after=inventory();assert before==after,'pre-existing resources changed'
    result.update(originalVolumesPreserved=len(before['volumes']),newVolumes=0,newContainers=0)
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
