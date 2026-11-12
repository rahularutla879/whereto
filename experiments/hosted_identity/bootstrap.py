"""Trusted synthetic Google-shaped signer: exists only inside disposable bootstrap."""
from contextlib import redirect_stdout
from io import StringIO
from copy import deepcopy
from pathlib import Path
import json,time,secrets,os
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa,ec,ed25519
from cryptography.hazmat.primitives import serialization,hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime,timezone,timedelta
from experiments.service_isolation import bootstrap as parent
from experiments.service_isolation.auth import b64
from experiments.shared_state.test_application_grants import witness_admin


def main():
    if any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or os.environ.get('WHERETO_ENV')=='production' or os.environ.get('NODE_ENV')=='production':raise RuntimeError('Offline bootstrap unavailable in hosting')
    capture=StringIO()
    with redirect_stdout(capture):parent.main()
    configs=json.loads(capture.getvalue());new=__import__('experiments.hosted_identity.identity',fromlist=['verify']).verify()
    front=deepcopy(configs['worker-other']);front.update(principal='frontend',service='frontend',role='frontend');front.pop('signingKey');front['signingKey']=b64(ed25519.Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()))
    configs['frontend']=front
    # Distinct TLS leaves, signed by a NEW synthetic CA; never installs Google trust.
    now=datetime.now(timezone.utc);cak=rsa.generate_private_key(public_exponent=65537,key_size=2048);subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Task52 hosted identity OFFLINE CA')])
    ca=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(cak.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True,path_length=0),True).sign(cak,hashes.SHA256())
    ports={'factory':8091,'counter':8092,'dispatcher':8093,'recovery':8094,'frontend':8095,'worker-a':8096,'worker-b':8097}
    targets={n:dict(port=p,hostname=n+'.task52.invalid',service='backend' if n.startswith('worker') else n) for n,p in ports.items()}
    audiences={n:'https://'+n+'-task52-offline.run.app' for n in ('frontend','backend','factory','counter','dispatcher','recovery')}
    backendpw=secrets.token_hex(24)
    with witness_admin() as db:
        for name,pw in [('synthetic_backend_auth',backendpw)]:
            db.execute('CREATE ROLE '+name+" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+pw+"'");db.execute('GRANT CONNECT ON DATABASE whereto_witness TO '+name)
        db.execute('SET LOCAL ROLE whereto_synthetic_owner');db.execute(Path(__file__).with_name('nonce.sql').read_text(),prepare=False)
    for name in ('worker-a','worker-b'):
        configs[name].update(service='backend',witness=dict(user='synthetic_backend_auth',password=backendpw,port=5433,dbname='whereto_witness'))
    public=b64(ed25519.Ed25519PrivateKey.from_private_bytes(__import__('experiments.service_isolation.auth',fromlist=['unb64']).unb64(front['signingKey'])).public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    trust=deepcopy(front['trust']);trust['frontend']=dict(publicKey=public,role='frontend')
    for v in trust.values():v.pop('owner',None) # Workload identity NEVER establishes user ownership.
    enrollment={name:dict(sub='10000000000000000000'+str(i),email=(('backend' if name.startswith('worker-') and name!='worker-other' else name)+'@offline-project.iam.gserviceaccount.com')) for i,name in enumerate(configs)}
    enrollment['worker-b']=enrollment['worker-a'].copy()
    signing={'workload':rsa.generate_private_key(public_exponent=65537,key_size=2048),'iap':ec.generate_private_key(ec.SECP256R1())}
    docs={}
    for kind,k in signing.items():
        j=json.loads((jwt.algorithms.RSAAlgorithm if kind=='workload' else jwt.algorithms.ECAlgorithm).to_jwk(k.public_key()));j.update(kid='task52-offline-'+kind,alg='RS256' if kind=='workload' else 'ES256',use='sig');docs[kind]={'keys':[j],'fixture':True}
    iap_aud='/projects/000000000000/locations/us-central1/services/whereto-frontend'
    def token(kind,claims):return jwt.encode(claims,signing[kind],algorithm='RS256' if kind=='workload' else 'ES256',headers={'kid':'task52-offline-'+kind})
    from experiments.hosted_identity.tokens import ISSUERS
    stamp=int(time.time());users={name:token('iap',dict(iss=ISSUERS['iap'],aud=iap_aud,sub='accounts.google.com:synthetic-'+name,email=name+'@example.invalid',iat=stamp,exp=stamp+600)) for name in ('alice','bob','revoked')}
    for name,c in configs.items():
        c.update(identityBuild=new,identityEnvironment='offline-hosted-contract',googleKeys=docs,iapAudience=iap_aud,testers=['accounts.google.com:synthetic-alice','accounts.google.com:synthetic-bob'],enrollment=enrollment,revoked=[],trust=trust,targets=targets,audiences=audiences)
        c['oidcTokens']={aud:token('workload',dict(iss=ISSUERS['workload'],aud=aud,sub=enrollment[name]['sub'],email=enrollment[name]['email'],email_verified=True,iat=stamp,exp=stamp+3600)) for aud in audiences.values()}
        if name in ports:
            c['port']=ports[name];k=rsa.generate_private_key(public_exponent=65537,key_size=2048);sn=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,targets[name]['hostname'])]);cert=x509.CertificateBuilder().subject_name(sn).issuer_name(subject).public_key(k.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(targets[name]['hostname'])]),False).sign(cak,hashes.SHA256());c.update(certificate=cert.public_bytes(serialization.Encoding.PEM).decode(),tlsKey=k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode())
        c['caPem']=ca.public_bytes(serialization.Encoding.PEM).decode()
    configs['worker-a']['allow']={p:['frontend'] for p in ('/interpret','/lookup','/continue','/select','/refresh')};configs['worker-b']['allow']=configs['worker-a']['allow']
    configs['frontend']['backends']=['worker-a','worker-b']
    ingress=token('workload',dict(iss=ISSUERS['workload'],aud=audiences['frontend'],sub='synthetic-iap-service-agent',email='iap-agent@offline-project.iam.gserviceaccount.com',email_verified=True,iat=stamp,exp=stamp+3600))
    configs['frontend']['ingressIdentity']={'sub':'synthetic-iap-service-agent','email':'iap-agent@offline-project.iam.gserviceaccount.com'}
    for path in ('/interpret','/lookup','/continue','/select','/refresh'):configs['factory']['allow'][path]=['worker-a','worker-b']
    # Signer keys/tokens never appear in ordinary service configuration.
    control={'configs':configs,'users':users,'ingress':ingress,'fixtureSigners':{kind:k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode() for kind,k in signing.items()}}
    print(json.dumps(control))

if __name__=='__main__':main()
