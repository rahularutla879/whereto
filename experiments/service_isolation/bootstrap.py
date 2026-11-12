"""Trusted disposable fixture bootstrap. Never imported by a service or worker."""
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
import base64,json,os,secrets
from pathlib import Path
from unittest.mock import patch
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import ed25519,rsa
from cryptography.hazmat.primitives import serialization,hashes
from psycopg.types.json import Jsonb
from experiments.shared_state import test_native_sessions as n,test_application_grants as g,test_store as core,test_financial as f
from experiments.service_isolation.auth import b64
from experiments.service_isolation.identity import verify


def main():
    from experiments.shared_state.contracts import Denied
    if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:raise Denied('disposable_bootstrap_only')
    build=verify();key=secrets.token_bytes(32);encrypted=secrets.token_bytes(32)
    passwords={name:secrets.token_hex(24) for name in ['dispatcher','factoryWitness','dispatchWitness','counterWitness','recovery']}
    with patch.object(core,'KEY',key):n.fixture()
    with core.admin() as c:
        c.execute("CREATE ROLE synthetic_dispatch_client LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+passwords['dispatcher']+"'")
        c.execute('GRANT CONNECT ON DATABASE whereto_synthetic TO synthetic_dispatch_client')
        c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path(__file__).with_name('protocol.sql').read_text(),prepare=False)
        c.execute('INSERT INTO synthetic_state.service_profile VALUES(1,%s,%s)',(build,g.EPOCH))
    wroles={'factoryWitness':'synthetic_factory_witness','dispatchWitness':'synthetic_dispatch_witness','counterWitness':'synthetic_counter_witness','recovery':'synthetic_recovery_client'}
    with g.witness_admin() as c:
        for k,name in wroles.items():
            c.execute("CREATE ROLE "+name+" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+passwords[k]+"'")
            c.execute('GRANT CONNECT ON DATABASE whereto_witness TO '+name)
        c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path(__file__).with_name('witness.sql').read_text(),prepare=False)
    names=['factory','counter','dispatcher','recovery','worker-a','worker-b','worker-other','operator']
    keys={name:ed25519.Ed25519PrivateKey.generate() for name in names}
    trust={name:dict(publicKey=b64(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)),role='backend' if name.startswith('worker') else name,
        **({'owner':'synthetic-other' if name=='worker-other' else 'synthetic-owner'} if name.startswith('worker') else {})) for name,k in keys.items()}
    ca_key=rsa.generate_private_key(public_exponent=65537,key_size=2048);now=datetime.now(timezone.utc)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Task52 synthetic disposable CA')])
    ca=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).sign(ca_key,hashes.SHA256())
    ca_pem=ca.public_bytes(serialization.Encoding.PEM).decode();targets={name:dict(port=8091+i,hostname=name+'.task52.invalid') for i,name in enumerate(names[:4])}
    def db(user,password,w=False):return dict(user=user,password=password,port=5433 if w else 5432,dbname='whereto_witness' if w else 'whereto_synthetic')
    configs={}
    for name in names:
        c=dict(principal=name,role=trust[name]['role'],service=name,build=build,environment='synthetic-isolated-services',epoch=g.EPOCH,
            signingKey=b64(keys[name].private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())),trust=trust,targets=targets,caPem=ca_pem,
            referenceTime='2026-11-02T13:00:00+00:00')
        if name in targets:
            k=rsa.generate_private_key(public_exponent=65537,key_size=2048);sn=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,targets[name]['hostname'])])
            cert=x509.CertificateBuilder().subject_name(sn).issuer_name(subject).public_key(k.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(targets[name]['hostname'])]),critical=False).sign(ca_key,hashes.SHA256())
            c.update(port=targets[name]['port'],certificate=cert.public_bytes(serialization.Encoding.PEM).decode(),tlsKey=k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode())
        configs[name]=c
    factory=configs['factory'];factory.update(database=db('whereto_synthetic_worker',os.environ['SYNTHETIC_WORKER_PASSWORD']),issuer=db('synthetic_issuer_client',os.environ['SYNTHETIC_ISSUER_PASSWORD']),
        witness=db(wroles['factoryWitness'],passwords['factoryWitness'],True),hashKey=b64(key),encryptionKey=b64(encrypted),redisUsername='source_factory',redisPassword=os.environ['SYNTHETIC_FACTORY_REDIS_PASSWORD'],limits=asdict(f.LIMITS),root=f.ROOT,
        allow={**{path:['worker-a','worker-b','worker-other'] for path in ['/interpret','/lookup','/continue','/select','/refresh']},'/dispatch-check':['dispatcher']},
        savedRecords={'A'*43:{'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'Synthetic_one'},{'reference':'Synthetic_two'}]}]}})
    configs['counter'].update(database=db('synthetic_counter_client',os.environ['SYNTHETIC_COUNTER_PASSWORD']),witness=db(wroles['counterWitness'],passwords['counterWitness'],True),allow={'/count':['factory']})
    configs['dispatcher'].update(database=db('synthetic_dispatch_client',passwords['dispatcher']),witness=db(wroles['dispatchWitness'],passwords['dispatchWitness'],True),hashKey=b64(key),encryptionKey=b64(encrypted),redisUsername='source_delivery',redisPassword=os.environ['SYNTHETIC_DELIVERY_REDIS_PASSWORD'],limits=asdict(f.LIMITS),allow={'/send':['factory']})
    configs['recovery'].update(witness=db(wroles['recovery'],passwords['recovery'],True),allow={'/recover':['operator']})
    print(json.dumps(configs)) # Captured privately by the trusted harness, never user output/log/Git.

if __name__=='__main__':main()
