"""Test-only isolated configuration; never imported by a real readiness launcher.

Only fixture constants, DNS and trusted CA are replaced. No validator, writer,
credential loader, supervisor, worker or exchange implementation is replaced.
"""
import json,os,re,socket,sys,subprocess
from pathlib import Path
from datetime import datetime,timezone
from scripts import task52b_model_get as g
from scripts import task52b_run_model_get_once as boot

ROOT=Path(__file__).resolve().parents[1]
KEY='sk-proj-'+('FICTIONAL'*6)

def build_fixture(root,port,ca,mode='ok'):
    root=Path(root);root.mkdir(mode=0o700);(root/'backend').mkdir();(root/'scripts').mkdir();(root/'docs').mkdir()
    original=json.loads(g.BUILD.read_bytes())
    files=set(original['filesSHA256'])
    for n in files:
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    for n in ('scripts/task52b_run_readiness_once.py','scripts/task52b_run_model_get_once.py'):
        (root/n).write_bytes((ROOT/n).read_bytes())
    base=root/'backend/.local/task52b-readiness';base.mkdir(parents=True,mode=0o700)
    old=base/g.e.OPERATION;g.e.make_directory(old)
    state=base/'FICTIONAL-supervised-get';g.e.make_directory(state)
    key=root/'backend/.env.cloud-evaluation.openai-replacement-FICTIONAL';key.write_text('OPENAI_API_KEY='+KEY+'\nUNRELATED=FICTIONAL-DO-NOT-READ\n');key.chmod(0o600)
    meta=key.with_name(key.name+'.metadata.json')
    g.private_create(meta,{'projectId':g.PROJECT,'projectName':'WhereTo Model Evaluation','credentialFile':str(key),'trackingId':'FICTIONAL','permissions':{'listModels':'Read','responses':'Read','unrelated':'None'},'expiresOn':'2099-01-01'})
    st=key.stat();enroll=base/'credential-enrollment-v1.json'
    g.private_create(enroll,{'metadataPath':str(meta),'credentialPath':str(key),'trackingId':'FICTIONAL','credentialDevice':st.st_dev,'credentialInode':st.st_ino,'credentialSize':st.st_size,'credentialMtimeNS':st.st_mtime_ns})
    old_auth=root/'docs/task52b-readiness-owner-authorization-v1.json';a=json.loads(old_auth.read_bytes());a['credentialMetadataSHA256']=g.digest(meta.read_bytes());a['fixtureOnly']=True;old_auth.write_text(json.dumps(a))
    old_build=root/'docs/task52b-readiness-live-build-v1.json';b=json.loads(old_build.read_bytes());b['filesSHA256']={n:g.digest((root/n).read_bytes()) for n in b['filesSHA256']};b['caBundleSHA256']=g.digest(Path(ca).read_bytes());old_build.write_text(json.dumps(b));old_sha=g.digest(old_build.read_bytes())
    p=root/'scripts/task52b_run_readiness_once.py';p.write_text(re.sub(r"(?m)^MANIFEST_SHA = '[0-9a-f]{64}'$","MANIFEST_SHA = '"+old_sha+"'",p.read_text()))
    g.private_create(old/'scope.json',{'operation':g.e.OPERATION,'fixtureOnly':True})
    g.private_create(old/'consumed.json',{'scopeSHA256':g.digest((old/'scope.json').read_bytes()),'fixtureOnly':True})
    g.private_create(old/'result.json',{'authorizationConsumed':True,'operations':[{'status':200},{'status':401}],'fixtureOnly':True})
    for n in ('intent-1.json','intent-2.json','response-1.json','response-2.json','runtime.json','supervisor-claim.json','supervisor.json','validated-1.json','wire-consumed-1.json','wire-consumed-2.json'):
        g.private_create(old/n,{'fixtureOnly':True,'name':n})
    pins={p.name:g.digest(p.read_bytes()) for p in old.iterdir()}
    result=root/'docs/task52b-authorized-readiness-result-v1.json';result.write_text(json.dumps({'buildSHA256':old_sha,'privateEvidence':{'fileSHA256':pins},'fixtureOnly':True}))
    if mode=='original_defect':
        (root/'scripts/task52b_model_get.py').write_bytes(subprocess.check_output(['git','show','1d994c2dd8f2727d01e3df7ed1bd9ba2ef1c6404:scripts/task52b_model_get.py'],cwd=ROOT))
    original['filesSHA256']={n:g.digest((root/n).read_bytes()) for n in files};original['caBundleSHA256']=g.digest(Path(ca).read_bytes());original['fixtureOnly']=True
    # The new version adds independent compiled-source identities. Old code does
    # not require them, allowing this identical harness to reproduce the defect.
    if hasattr(g,'identity_manifest'):
        original.update(g.identity_manifest())
    build=root/'docs/FICTIONAL-get-build.json';build.write_text(json.dumps(original));sha=g.digest(build.read_bytes())
    p=root/'scripts/task52b_run_model_get_once.py';p.write_text(re.sub(r"(?m)^MANIFEST_SHA = '[0-9a-f]{64}'$","MANIFEST_SHA = '"+sha+"'",p.read_text()))
    op='FICTIONAL-supervised-get';scope=g.proposed_scope()|{'operation':op,'buildSHA256':sha,'credentialIdentity':g.digest(enroll.read_bytes()),'originalEvidenceBundleSHA256':g.digest(json.dumps(pins,sort_keys=True).encode()),'supervisorIdentity':original['filesSHA256']['scripts/task52b_model_get.py'],'fixtureOnly':True}
    g.private_create(state/'scope.json',scope);now=datetime.now(timezone.utc)
    auth=base/(op+'.send-authorization.json')
    g.private_create(auth,{'operation':op,'explicitOwnerSendConfirmation':True,'approvedAt':now.isoformat(),'expiresAt':g.previous.fresh(now.isoformat(),now).isoformat(),'buildSHA256':sha,'scopeSHA256':g.digest((state/'scope.json').read_bytes()),'credentialIdentity':scope['credentialIdentity'],'originalEvidenceBundleSHA256':scope['originalEvidenceBundleSHA256'],'fixtureOnly':True})
    config={'root':str(root),'port':port,'ca':str(ca),'mode':mode,'buildSHA256':sha,'build':str(build),'state':str(state),'authorization':str(auth),'enrollment':str(enroll),'key':str(key),'original':str(old),'diagnostic':str(root/'diagnostic.json'),'oldBuild':str(old_build),'oldAuthorization':str(old_auth),'oldSHA256':old_sha}
    cfg=root/'config.json';cfg.write_text(json.dumps(config));cfg.chmod(0o600)
    historical=''
    if mode=='original_defect':
        historical='import importlib.util,scripts\nspec=importlib.util.spec_from_file_location("scripts.task52b_model_get",'+repr(str(root/'scripts/task52b_model_get.py'))+')\nm=importlib.util.module_from_spec(spec)\nsys.modules[spec.name]=m\nscripts.task52b_model_get=m\nspec.loader.exec_module(m)\n'
    driver=root/'driver.py';driver.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\n'+historical+'from backend.task52b_get_tls_fixture import configure\nconfigure('+repr(str(cfg))+')\nfrom scripts import task52b_run_model_get_once as b\nif __name__=="__main__":\n sys.argv=["supervisor","--execute-model-get-once"]\n b.main()\n')
    if mode=='changed_source':(root/'scripts/task52b_model_get.py').write_text((root/'scripts/task52b_model_get.py').read_text()+'\n# FICTIONAL altered source\n')
    if mode=='bad_bootstrap':p.write_text(p.read_text()+'\n# FICTIONAL altered bootstrap\n')
    if mode=='bad_metadata':meta.write_text(meta.read_text()+' ')
    if mode=='missing_authorization':auth.unlink()  # Disposable fictional authority only.
    if mode=='expired_authorization':
        a=json.loads(auth.read_bytes());a['approvedAt']='2000-01-01T00:00:00+00:00';auth.write_text(json.dumps(a))
    return config,driver


def configure(path):
    cfg=json.loads(Path(path).read_bytes());root=Path(cfg['root']);state=Path(cfg['state']);op='FICTIONAL-supervised-get'
    g.ROOT=root;g.STATE=state;g.OPERATION=op;g.AUTHORIZATION=Path(cfg['authorization']);g.BUILD=Path(cfg['build']);g.BOOTSTRAP=root/'scripts/task52b_run_model_get_once.py'
    e=g.e;e.ROOT=root;e.BASE=state.parent;e.STATE=Path(cfg['original']);e.PRIVATE_ENROLLMENT=Path(cfg['enrollment']);e.MANIFEST=Path(cfg['oldBuild']);e.AUTHORIZATION=Path(cfg['oldAuthorization'])
    e.certifi.core._CACERT_PATH=cfg['ca']
    boot.MANIFEST_SHA='0'*64 if cfg['mode']=='bad_build' else cfg['buildSHA256']
    real_dns=socket.getaddrinfo;real_socket=socket.socket
    def dns(host,port,**kw):
        if (host,port)!=('api.openai.com',443):raise AssertionError('Nonfixture destination prohibited')
        return real_dns('127.0.0.1',cfg['port'],**kw)
    class GuardedSocket(real_socket):
        def connect(self,address):
            if address[:2]!=('127.0.0.1',cfg['port']):raise AssertionError('Nonloopback socket prohibited')
            return super().connect(address)
    socket.getaddrinfo=dns;socket.socket=GuardedSocket
    def audit(event,args):
        if event!='open':return
        p=str(args[0])
        if p==cfg['key']:
            assert (state/'intent.json').exists() and (state/'consumed.json').exists()
            marker=root/('key-boundary-'+str(os.getpid())+'.json')
            if not marker.exists():e.private_create(marker,{'fixtureOnly':True,'intentBeforeKey':True,'pid':os.getpid()})
            if cfg['mode']=='after_intent':os._exit(73)
        if p==str(state/'intent.json') and args[2]&os.O_CREAT and cfg['mode']=='before_intent':os._exit(73)
        if p==str(state/'response-1.json') and args[2]&os.O_CREAT and cfg['mode']=='after_send':os._exit(73)
    sys.addaudithook(audit)
    # Only sanitized, allowlisted exception classifications from FICTIONAL runs.
    def trace(frame,event,arg):
        if event=='exception' and frame.f_code.co_name in ('verify_supervision','verified_wire_identity','verify_build') and frame.f_globals is g.__dict__:
            kind,value,_=arg
            if kind is g.q.Refused and str(value) in ('get_worker_identity','get_loaded_code_identity','get_source_identity','get_build_identity','get_bootstrap_identity','get_bootstrap_source'):
                p=Path(cfg['diagnostic'])
                if not p.exists():e.private_create(p,{'fixtureOnly':True,'code':str(value),'function':frame.f_code.co_name,'line':frame.f_lineno,'wireClaim':(state/'wire-consumed.json').exists(),'sourceFile':'scripts/task52b_model_get.py'})
        return trace
    sys.settrace(trace)
    if cfg['mode']=='monkeypatch_wire':
        ns={};exec('def exchange(self,key):\n return None\n',g.__dict__,ns);g.GetOnlyHTTPS.exchange=ns['exchange']
    if cfg['mode']=='changed_constant':
        fn=g.GetOnlyHTTPS.exchange;fn.__code__=fn.__code__.replace(co_consts=tuple('FICTIONAL-MODIFIED' if x=='/v1/models/gpt-6-luna' else x for x in fn.__code__.co_consts))

    if cfg['mode']=='monkeypatch_dial':g._SingleDial.connect=lambda self:None

    if cfg['mode']=='monkeypatch_class':g.GetOnlyHTTPS.__getattribute__=lambda self,name:object.__getattribute__(self,name)

    if cfg['mode']=='monkeypatch_constructor':g.e.FixedReadinessHTTPS.__new__=staticmethod(lambda cls,*a,**kw:object.__new__(cls))
