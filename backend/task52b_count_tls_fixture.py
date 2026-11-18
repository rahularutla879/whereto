"""Test-only count composition: actual runner/gates/loader, fictional records/TLS."""
from pathlib import Path
from datetime import datetime,timezone
from base64 import b64encode
import json,os,re,socket,sys,subprocess
from backend.task52b_get_tls_fixture import build_fixture as get_fixture,KEY,ROOT
from scripts import task52b_count_only as c
from scripts import task52b_run_count_once as boot
from backend.provider_responses import HTTPResult


def replace_fixture(path,value):
    # Fixture generation only, before the operation; never a protected real file.
    Path(path).write_text(json.dumps(value));Path(path).chmod(0o600)


def build_fixture(root,port,ca,mode='ok'):
    cfg,_=get_fixture(root,port,ca);root=Path(root);base=Path(cfg['state']).parent;old=Path(cfg['original']);now=datetime.now(timezone.utc).isoformat()
    identity=c.digest(Path(cfg['enrollment']).read_bytes());get_time='2000-01-01T00:00:00+00:00' if mode=='stale_get' else now;raw=json.dumps({'object':'model','id':c.q.MODEL,'created':1,'owned_by':'FICTIONAL'}).encode();raw_sha=c.digest(raw)
    replace_fixture(old/'scope.json',{'operation':c.e.OPERATION,'project':c.PROJECT,'model':c.q.MODEL,'countSHA256':c.q.COUNT_SHA,'buildSHA256':cfg['oldSHA256'],'credentialIdentity':identity,'fixtureOnly':True})
    replace_fixture(old/'consumed.json',{'scopeSHA256':c.digest((old/'scope.json').read_bytes()),'fixtureOnly':True})
    replace_fixture(old/'response-1.json',{'at':get_time,'status':200,'complete':True,'credentialEchoRefused':False,'contentType':'application/json','bodyBase64':b64encode(raw).decode(),'bodySHA256':raw_sha,'fixtureOnly':True})
    replace_fixture(old/'validated-1.json',{'at':get_time,'rawSHA256':raw_sha,'value':c.q.validate_response(c.q.requests()[0],HTTPResult(200,raw)),'fixtureOnly':True})
    pins={p.name:c.digest(p.read_bytes()) for p in old.iterdir()}
    (root/'docs/task52b-authorized-readiness-result-v1.json').write_text(json.dumps({'buildSHA256':cfg['oldSHA256'],'privateEvidence':{'fileSHA256':pins},'operations':[{'rawSHA256':raw_sha}],'fixtureOnly':True}))
    operation='FICTIONAL-supervised-count';state=base/operation;c.e.make_directory(state)
    observation=base/'FICTIONAL-observation.json';permission=base/'FICTIONAL-permission.json';binding=root/'docs/task52b-count-only-dashboard-binding-v1.json'
    permissions={'listModels':'Read','responses':'Write','unrelated':'None'}
    facts={'project':c.PROJECT,'projectName':'WhereTo Model Evaluation','trackingId':'FICTIONAL','keyName':'WhereTo Task52B Evaluation','status':'Active','expiresOn':'2099-01-01','permissions':permissions,'credentialIdentity':identity,'observedAt':now,'changedPermissions':False,'secretValueAccessed':False,'fixtureOnly':True}
    c.private_create(observation,facts);oh=c.digest(observation.read_bytes())
    receipt={'project':c.PROJECT,'credentialIdentity':identity,'permissions':permissions,'independentlyEstablished':True,'basis':'independently-observed-dashboard','evidenceSHA256':oh,'observer':'FICTIONAL-OBSERVER','observedAt':now,'fixtureOnly':True}
    c.private_create(permission,receipt);ph=c.permission_record(receipt,identity,datetime.now(timezone.utc))
    binding.write_text(json.dumps({'credentialIdentity':identity,'permissionSHA256':ph,'observationSHA256':oh,'fixtureOnly':True}))
    if mode=='original_defect':
        (root/'scripts/task52b_count_only.py').write_bytes(subprocess.check_output(['git','show','3e2ba623e15b3f0ce73286775bb9acc62a3432ac:scripts/task52b_count_only.py'],cwd=ROOT))
    b=json.loads(Path(cfg['build']).read_bytes());b['filesSHA256']={n:c.digest((root/n).read_bytes()) for n in b['filesSHA256'] if n not in ('scripts/task52b_run_count_once.py','scripts/task52b_run_model_get_once.py')}
    source=(ROOT/'scripts/task52b_run_count_once.py').read_text();normalized=re.sub(r"(?m)^MANIFEST_SHA = '[0-9a-f]{64}'$","MANIFEST_SHA = '__BUILD_SHA__'",source)
    b['bootstrapTemplateSHA256']=c.digest(normalized.encode())
    if hasattr(c,'identity_manifest'):b.update(c.identity_manifest())
    build=root/'docs/FICTIONAL-count-build.json';build.write_text(json.dumps(b));sha=c.digest(build.read_bytes())
    (root/'scripts/task52b_run_count_once.py').write_text(re.sub(r"(?m)^MANIFEST_SHA = '[0-9a-f]{64}'$","MANIFEST_SHA = '"+sha+"'",source))
    proof=c.digest(json.dumps(pins,sort_keys=True).encode())
    scope=c.proposed_scope()|{'operation':operation,'buildSHA256':sha,'credentialIdentity':identity,'permissionSHA256':ph,'priorGETBundleSHA256':proof,'supervisorIdentity':b['filesSHA256']['scripts/task52b_count_only.py'],'fixtureOnly':True}
    c.private_create(state/'scope.json',scope);auth=base/(operation+'.send-authorization.json')
    c.private_create(auth,{'operation':operation,'explicitOwnerSendConfirmation':True,'buildSHA256':sha,'scopeSHA256':c.digest((state/'scope.json').read_bytes()),'credentialIdentity':identity,'permissionSHA256':ph,'priorGETBundleSHA256':proof,'fixtureOnly':True})
    cfg.update(mode=mode,state=str(state),authorization=str(auth),build=str(build),buildSHA256=sha,permission=str(permission),observation=str(observation),binding=str(binding))
    config=root/'count-config.json';config.write_text(json.dumps(cfg));config.chmod(0o600)
    historical=''
    if mode=='original_defect':historical='import importlib.util,scripts\nspec=importlib.util.spec_from_file_location("scripts.task52b_count_only",'+repr(str(root/'scripts/task52b_count_only.py'))+')\nm=importlib.util.module_from_spec(spec)\nsys.modules[spec.name]=m\nscripts.task52b_count_only=m\nspec.loader.exec_module(m)\n'
    driver=root/'count-driver.py';driver.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\n'+historical+'from backend.task52b_count_tls_fixture import configure\nconfigure('+repr(str(config))+')\nfrom scripts import task52b_run_count_once as b\nif __name__=="__main__":\n sys.argv=["supervisor","--execute-count-only-once"]\n b.main()\n')
    if mode=='changed_source':(root/'scripts/task52b_count_only.py').write_text((root/'scripts/task52b_count_only.py').read_text()+'\n# FICTIONAL altered source\n')
    if mode=='bad_bootstrap':(root/'scripts/task52b_run_count_once.py').write_text(source+'\n# FICTIONAL altered bootstrap\n')
    if mode=='bad_metadata':Path(cfg['key']+'.metadata.json').write_text(Path(cfg['key']+'.metadata.json').read_text()+' ')
    if mode=='missing_permission':permission.unlink()
    if mode=='read_permission':
        receipt['permissions']={'listModels':'Read','responses':'Read','unrelated':'None'};replace_fixture(permission,receipt)
    return cfg,driver


def configure(path):
    cfg=json.loads(Path(path).read_bytes());root=Path(cfg['root']);state=Path(cfg['state']);e=c.e
    c.ROOT=root;c.STATE=state;c.OPERATION='FICTIONAL-supervised-count';c.AUTHORIZATION=Path(cfg['authorization']);c.BUILD=Path(cfg['build']);c.BOOTSTRAP=root/'scripts/task52b_run_count_once.py';c.PERMISSION=Path(cfg['permission']);c.OBSERVATION=Path(cfg['observation']);c.BINDING=Path(cfg['binding'])
    e.ROOT=root;e.BASE=state.parent;e.STATE=Path(cfg['original']);e.PRIVATE_ENROLLMENT=Path(cfg['enrollment']);e.MANIFEST=Path(cfg['oldBuild']);e.AUTHORIZATION=Path(cfg['oldAuthorization']);e.certifi.core._CACERT_PATH=cfg['ca']
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
    def trace(frame,event,arg):
        if event=='exception' and frame.f_code.co_name in ('verify_supervision','verified_wire_identity','verify_count_build','prior_get','verified_permission','permission_record','fresh') and frame.f_globals is c.__dict__:
            kind,value,_=arg
            if kind is c.q.Refused and str(value) in ('count_worker_identity','count_loaded_code_identity','count_source_identity','count_build_identity','count_bootstrap_identity','count_bootstrap_source','prior_evidence_stale','responses_write_required'):
                p=Path(cfg['diagnostic'])
                if not p.exists():e.private_create(p,{'fixtureOnly':True,'code':str(value),'function':frame.f_code.co_name,'line':frame.f_lineno,'wireClaim':(state/'wire-consumed.json').exists()})
        return trace
    sys.settrace(trace)
    if cfg['mode']=='monkeypatch_wire':
        ns={};exec('def exchange(self,key):\n return None\n',c.__dict__,ns);c.CountOnlyHTTPS.exchange=ns['exchange']
    if cfg['mode']=='changed_constant':
        fn=c.CountOnlyHTTPS.exchange;fn.__code__=fn.__code__.replace(co_consts=tuple('FICTIONAL-MODIFIED' if x=='/v1/responses/input_tokens' else x for x in fn.__code__.co_consts))
    if cfg['mode']=='monkeypatch_dial':c._SingleDial.connect=lambda self:None
    if cfg['mode']=='monkeypatch_class':c.CountOnlyHTTPS.__getattribute__=lambda self,name:object.__getattribute__(self,name)
