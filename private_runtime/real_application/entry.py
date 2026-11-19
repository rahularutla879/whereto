"""Image-selected real entry. No ordinary startup/config flag selects this code."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import http.client,json,os,signal,stat,threading,time
from experiments.shared_state.contracts import Denied
from experiments.shared_state.evidence_models import strict_json
from private_runtime.provider_callbacks import OpenAIHTTP
from private_runtime.real_finance.runtime import GoogleWorkloadExchange
from .ports import Ports
from .startup import compose
from .service import backend_app,privileged_server

SECRET='/run/secrets/whereto-openai-key.json'
def credential(c):
    # Construct only for dispatcher. Reading occurs AFTER protected dispatch use.
    if c.get('service')!='dispatcher':raise Denied('provider_credential_role')
    def load():
        fd=os.open(SECRET,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o222 or not 1<=s.st_size<=16384:raise Denied('provider_secret_mount')
            raw=os.read(fd,16385)
        finally:os.close(fd)
        if sha256(raw).hexdigest()!=c['openaiSecretSHA256']:raise Denied('provider_secret_binding')
        v=strict_json(raw)
        if set(v)!={'version','project','credentialId','key','expires','permissionEvidence'} or v['version']!='52-application-openai-key-v1' or v['project']!=c['openaiProject'] or v['credentialId']!=c['openaiCredentialId'] or v['permissionEvidence']!=c['openaiPermissionEvidence'] or type(v['expires'])is not int or v['expires']<=time.time():raise Denied('provider_credential_enrollment')
        if type(v['key'])is not str or not v['key'].startswith('sk-') or any(x.isspace() for x in v['key']):raise Denied('provider_credential_value')
        return v['key']
    return load

class OAuth:
    """Assigned dispatcher metadata only. No ADC, user key, proxy or retry."""
    def __call__(self,_session):
        c=http.client.HTTPConnection('metadata.google.internal',timeout=2)
        try:
            c.request('GET','/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
            r=c.getresponse();raw=r.read(16385)
            if r.status!=200 or r.getheader('Metadata-Flavor')!='Google' or len(raw)>16384:raise Denied('workload_oauth')
            v=strict_json(raw)
            if set(v)!={'access_token','expires_in','token_type'} or v['token_type']!='Bearer' or type(v['expires_in'])is not int or not 60<=v['expires_in']<=3600 or type(v['access_token'])is not str or not v['access_token'] or any(x.isspace() for x in v['access_token']):raise Denied('workload_oauth')
            return v['access_token']
        finally:c.close()

def serve(role,*,tls=None):
    c=role.c
    if role.role=='backend':
        import uvicorn
        uvicorn.run(backend_app(role),host='0.0.0.0',port=c['port'],access_log=False,log_level='warning',**(dict(ssl_certfile=tls[0],ssl_keyfile=tls[1]) if tls else {}));return
    server=privileged_server(role,tls=tls)
    def stop(*_):
        if role.owner is not None:role.owner.drain(8)
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close()

def main():
    if os.getuid()==0 or any(os.environ.get(k) for k in ('SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE','GOOGLE_APPLICATION_CREDENTIALS','OPENAI_API_KEY','OPENAI_ORG_ID','OPENAI_PROJECT')):raise Denied('unsafe_real_environment')
    from private_runtime.image_build import ROLE,PROFILE
    from private_runtime.image_identity import verify
    from .identity import verify_application
    if PROFILE!='52-real-native-six-role-v4' or not os.environ.get('K_SERVICE'):raise Denied('real_image_enrollment')
    build=verify();verify_application();p=Path('/run/secrets/whereto-private.json');s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o222 or s.st_size>131072:raise Denied('real_configuration_mount')
    c=strict_json(p.read_bytes())
    if c.get('build')!=build or c.get('identityBuild')!=build or c.get('ordinaryBuild')!=build or c.get('service')!=ROLE or c.get('identityEnvironment')!='private-staging' or c.get('transportTermination')!='cloud-run' or c.get('providerMode')!='real' or c.get('realProviderTransport') is not True:raise Denied('real_image_configuration')
    if any(k in c for k in ('referenceTime','savedRecords','googleKeys','oidcTokens','admin','bootstrap','certificate','tlsKey')):raise Denied('fixture_enrollment')
    with Ports(ROLE,c) as ports:
        ports.identity.token(c['audiences'][ROLE]) # Independently verified assigned subject/email.
        provider=google=None
        if ROLE=='dispatcher':
            key=credential(c);key();provider={purpose:OpenAIHTTP(c['openaiProject'],key,purpose=purpose) for purpose in ('count','generation')};google=GoogleWorkloadExchange(OAuth())
        serve(compose(ports,provider=provider,google=google))
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:print('Real private startup refused: reviewed enrollment required.');raise SystemExit(78)
