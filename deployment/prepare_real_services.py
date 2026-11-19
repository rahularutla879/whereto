"""Finite real-role image projection. No enrollment, credentials or provider I/O.

Raw pinned parents are immutable proof data, never importable runtime modules.
The existing image verifier independently binds every derived executable byte.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import ast,json,shutil
from deployment.prepare_private_services import functions,replace,source,ROLES
from private_runtime.real_application.projection import backend
ROOT=Path(__file__).resolve().parents[1]
PROFILE='52-real-native-six-role-v4'
def sha(raw):return sha256(raw).hexdigest()
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def dependencies(module,text):
    out=set()
    for n in ast.walk(ast.parse(text)):
        if isinstance(n,ast.Import):out.update(a.name for a in n.names)
        if isinstance(n,ast.ImportFrom):
            base=n.module or ''
            if n.level:
                package=module.split('.')[:-1];base='.'.join(package[:len(package)-n.level+1]+([base] if base else []))
            if base:out.add(base)
            out.update(base+'.'+a.name for a in n.names if a.name!='*')
    return {v for v in out if v.startswith(('backend','private_runtime','experiments')) and source(v) is not None}
def prepare(target):
    target=Path(target).resolve()
    if target.exists() or ROOT in target.parents:raise ValueError('Fresh external context required')
    native=json.loads((ROOT/'private_runtime/real_application/sources.json').read_bytes());finance=json.loads((ROOT/'private_runtime/real_finance/sources.json').read_bytes())
    if native['identity']!=PROFILE or native['releaseEligible']is not False:raise ValueError('Reviewed inactive real source required')
    for name,h in {**native['inputs'],**finance['inputs']}.items():
        p=ROOT/name
        if p.is_symlink() or sha(p.read_bytes())!=h:raise ValueError('Source identity '+name)
    target.mkdir(parents=True);inputs={};outputs={};files={}
    with TemporaryDirectory(prefix='whereto-real-backend-') as tmp:
        b=Path(tmp)/'backend';backend(b)
        for p in b.rglob('*.py'):files['backend/'+str(p.relative_to(b))]=p.read_bytes()
    if {n:sha(v) for n,v in files.items()}!=native['backendOutputs']:raise ValueError('Backend projection changed')
    def raw(module):
        p=source(module);v=p.read_bytes();inputs[str(p.relative_to(ROOT))]=sha(v);return v.decode()
    def project(module):
        s=raw(module)
        if module=='private_runtime.owned_dispatch':return "from contextvars import ContextVar\nCALLER=ContextVar('verified_dispatch_caller',default=None)\n"
        if module=='private_runtime.private_service':
            tree=ast.parse(s);constants=[ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ('CALLERS','PATHS') for x in n.targets)]
            return '''from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from email.message import Message
from threading import BoundedSemaphore
from copy import deepcopy
import json,ssl,threading
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.hosted_identity.auth import USER,verify_proof,PROOF
from experiments.ordinary_hosted.request_auth import RequestVerifier
from experiments.service_isolation.auth import MAX_BODY,MAX_RESPONSE,b64
from private_runtime import owned_dispatch
'''+ '\n'.join(constants)+'\n'+functions(s,['enrollment','audit'])
        if module=='experiments.shared_state.native_sessions':return 'from time import monotonic\nfrom experiments.shared_state.contracts import Denied\nfrom experiments.shared_state.evidence_models import canonical,plain\n'+functions(s,['restore_validation'])
        if module=='experiments.service_isolation.auth':return 'import base64\nfrom hashlib import sha256\nfrom experiments.shared_state.contracts import Denied\nfrom experiments.shared_state.evidence_models import canonical\nMAX_BODY=200000\nMAX_RESPONSE=1048576\n'+functions(s,['b64','unb64','binding'])
        if module=='experiments.hosted_identity.auth':
            tree=ast.parse(s);tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name not in ('Auth','Client')];s=ast.unparse(tree)+'\n';s=s.replace('Tokens, OfflineKeys, GoogleKeys','Tokens, GoogleKeys');return replace(s,'import TLS, b64,','import b64,')
        if module=='experiments.hosted_identity.tokens':
            tree=ast.parse(s);tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name!='OfflineKeys'];s=ast.unparse(tree)+'\n';return replace(s,'type(keys) is not (OfflineKeys if offline else GoogleKeys)','offline or type(keys) is not GoogleKeys')
        if module in ('private_runtime.real_application.identity','private_runtime.real_finance.profile'):
            s=replace(s,'ROOT=Path(__file__).resolve().parents[2]',"ROOT=Path(__file__).resolve().parents[2]/'source-proof'")
            # Proofs keep logical pinned names/hashes but cannot be Python modules.
            s=s.replace('p=ROOT/name', "p=ROOT/(name+'.txt' if name.endswith('.py') else name)").replace('path=ROOT/name', "path=ROOT/(name+'.txt' if name.endswith('.py') else name)").replace('p=ROOT/n\n', "p=ROOT/(n+'.txt' if n.endswith('.py') else n)\n")
            if module.endswith('identity'):s=replace(s,"    verify();manifest=", "    from private_runtime.image_identity import verify as verify_image\n    verify_image();verify();manifest=")
        return s
    queue=['private_runtime.real_application.entry','private_runtime.image_identity'];seen=set()
    while queue:
        module=queue.pop()
        if module in seen or module=='private_runtime.image_build':continue
        if any(p.startswith(('test_','run_')) or p in ('simulation','bootstrap','testing_clock','journey_fixtures','real_fixtures') for p in module.split('.')):raise ValueError('Forbidden runtime dependency '+module)
        seen.add(module);p=source(module);name=str(p.relative_to(ROOT))
        text=files[name].decode() if name in files else project(module)
        files[name]=text.encode();queue+=sorted(dependencies(module,text)-seen)
    # Non-importable originals required by exact financial/native source checks.
    proof={**finance['inputs'],**native['inputs'],**native['backendOutputs']}
    for name,h in proof.items():
        v=files[name] if name in native['backendOutputs'] else (ROOT/name).read_bytes()
        if sha(v)!=h:raise ValueError('Proof identity '+name)
        files['source-proof/'+name+('.txt' if name.endswith('.py') else '')]=v
        if not name.endswith('.py'):files[name]=v
    for name in ('private_runtime/real_finance/sources.json','private_runtime/real_application/sources.json'):
        files[name]=(ROOT/name).read_bytes()
    # No fixture/profile generator or historical evaluator is executable in images.
    for name,v in files.items():
        if name.endswith('.py') and not name.startswith('source-proof/'):compile(v,name,'exec')
    bases=json.loads((ROOT/'deployment/candidates/trixie-v1/base-images.json').read_bytes());patch=json.loads((ROOT/'deployment/candidates/trixie-zlib-v2/security-package.json').read_bytes())
    for name in ('deployment/prepare_real_services.py','deployment/prepare_zlib_candidate.py','deployment/Dockerfile.private-service','deployment/requirements-private-linux-amd64.lock','deployment/candidates/trixie-v1/base-images.json','deployment/candidates/trixie-zlib-v2/security-package.json'):
        inputs[name]=sha((ROOT/name).read_bytes())
    # Current common constructor imports the full strict model/evidence closure.
    # Use that exact existing lock, not an insufficient synthetic counter lock.
    for role in ROLES:
        own=dict(files);own['private_runtime/entry.py']=b'from private_runtime.real_application.entry import main\nif __name__=="__main__":\n try:raise SystemExit(main())\n except Exception:print("Real private startup refused: verified enrollment required.");raise SystemExit(78)\n'
        for name,v in own.items():outputs[role+'/'+name]=sha(v)
    cohort=dict(identity='52-real-native-role-cohort-v1',profile=PROFILE,realProviderTransport=True,releaseEligible=False,platform='linux/amd64',nativeSourceSHA256=sha((ROOT/'private_runtime/real_application/sources.json').read_bytes()),nativeBuild=sha(json.dumps(native,sort_keys=True).encode()),inputs=dict(sorted(inputs.items())),outputs=dict(sorted(outputs.items())),baseImages=bases,securityPackage=patch,dependencyLockSHA256=sha((ROOT/'deployment/requirements-private-linux-amd64.lock').read_bytes()))
    body=encoded(cohort);pin=sha(body)
    for role in ROLES:
        d=target/role;d.mkdir()
        for name,v in files.items():p=d/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
        (d/'private_runtime/entry.py').write_bytes(b'from private_runtime.real_application.entry import main\nif __name__=="__main__":\n try:raise SystemExit(main())\n except Exception:print("Real private startup refused: verified enrollment required.");raise SystemExit(78)\n')
        own=encoded(dict(cohort=pin,role=role,files=sorted(set(files)|{'private_runtime/entry.py'})))
        (d/'private-role.json').write_bytes(own);(d/'private-cohort.json').write_bytes(body)
        (d/'private_runtime/image_build.py').write_text(f'COHORT={pin!r}\nROLE_PIN={sha(own)!r}\nROLE={role!r}\nPROFILE={PROFILE!r}\n')
    (target/'cohort.json').write_bytes(body)
    shutil.copyfile(ROOT/'deployment/requirements-private-linux-amd64.lock',target/'requirements.lock');shutil.copyfile(target/'requirements.lock',target/'authority-requirements.lock')
    from deployment.prepare_zlib_candidate import dockerfile
    docker=dockerfile((ROOT/'deployment/Dockerfile.private-service').read_text(),'PYTHON_IMAGE',bases['images']['python']['reference'],patch)
    (target/'Dockerfile').write_text(docker)
    return cohort
if __name__=='__main__':
    import sys
    print(json.dumps(prepare(sys.argv[1]),sort_keys=True))
