"""Finite real frontend projection; original app and historical locks stay intact."""
from pathlib import Path
from hashlib import sha256
import json,shutil
ROOT=Path(__file__).resolve().parents[1]

def prepare(target,*,fixture=False):
    target=Path(target)
    if target.exists() or ROOT in target.resolve().parents or type(fixture)is not bool:raise ValueError('Fresh isolated real frontend context required')
    target.mkdir(parents=True);inputs={}
    def copy(name,dest=None):
        source=ROOT/name
        if source.is_symlink():raise ValueError('Unreviewed source link')
        raw=source.read_bytes();inputs[name]=sha256(raw).hexdigest();out=target/(dest or name);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
    for directory in ('app','components','lib','data'):
        for p in sorted((ROOT/directory).rglob('*')):
            if p.is_file() and not p.name.endswith(('.test.ts','.test.tsx','.spec.ts','.spec.tsx')):copy(str(p.relative_to(ROOT)))
    for name in ('next.config.ts','tsconfig.json','postcss.config.mjs','deployment/Dockerfile.frontend-private','deployment/build-private-frontend.mjs','deployment/frontend-private-entry.mjs','deployment/frontend-private-launch.sh','deployment/private-role-cohort-v1.json'):copy(name)
    copy('deployment/candidates/trixie-v1/next-package.json','package.json');copy('deployment/candidates/trixie-v1/next-package-lock.json','package-lock.json')
    if fixture:
        for name in ('experiments/real_frontend/identity.mjs','experiments/hosted_ports/frontend_fixture_identity.mjs'):copy(name)
    p=target/'app/page.tsx';s=p.read_text()
    for old,new in [('const [privateUI,setPrivateUI]=useState(false);','const [privateUI,setPrivateUI]=useState(true);'),('const [privateReal,setPrivateReal]=useState(false),[privateFixture,setPrivateFixture]=useState(false);',f'const [privateReal,setPrivateReal]=useState(true),[privateFixture,setPrivateFixture]=useState({str(fixture).lower()});')]:
        if s.count(old)!=1:raise ValueError('Real page projection changed')
        s=s.replace(old,new)
    p.write_text(s)
    manifest=dict(identity='52-real-frontend-source-v1',fixture=fixture,nextVersion='16.4.5',inputs=inputs,pageSHA256=sha256(p.read_bytes()).hexdigest(),releaseEligible=False)
    (target/'real-frontend-source.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest
