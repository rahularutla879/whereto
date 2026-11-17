"""Isolated packaging overlay; never selects a runtime or changes application authority.

Reuse the reviewed projectors, preserve original code/locks, bind candidate bases
and the exact isolated Next patch to new build identities. No Docker/account I/O.
"""
from pathlib import Path
from hashlib import sha256
import json,shutil
from deployment.prepare_private_services import prepare as roles,ROOT,ROLES
from deployment.prepare_closed_frontend import prepare as frontend

CANDIDATE=ROOT/'deployment/candidates/trixie-v1'
def digest(value):return sha256(value).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()

def validate():
    bases=json.loads((CANDIDATE/'base-images.json').read_text())
    if bases['promotionApproved'] is not False or bases['realProviderTransport'] is not False or bases['platform']!='linux/amd64':raise ValueError('Candidate must remain disabled')
    for name,tag in [('python','3.12-slim-trixie'),('node','24-trixie-slim')]:
        ref=bases['images'][name]['reference'];pin=ref.split('@sha256:')
        if len(pin)!=2 or pin[0]!=name+':'+tag or len(pin[1])!=64 or any(c not in '0123456789abcdef' for c in pin[1]):raise ValueError('Exact supported base required')
    old=json.loads((ROOT/'package-lock.json').read_text());new=json.loads((CANDIDATE/'next-package-lock.json').read_text())
    p=json.loads((ROOT/'package.json').read_text());q=json.loads((CANDIDATE/'next-package.json').read_text())
    if old['packages']['node_modules/next']['version']!='16.4.2' or q['dependencies']['next']!='16.4.5' or new['packages']['node_modules/next']['version']!='16.4.5':raise ValueError('Reviewed Next patch only')
    q['dependencies']['next']=p['dependencies']['next']
    if q!=p:raise ValueError('Unrelated package change')
    changes=[]
    for name in old['packages'].keys()|new['packages'].keys():
        if old['packages'].get(name)!=new['packages'].get(name):
            if name not in ('','node_modules/next') and not (name in old['packages'] and name.startswith('node_modules/@next/')):raise ValueError('Unrelated dependency '+name)
            if name and (new['packages'][name]['version']!='16.4.5' or old['packages'][name]['version']!='16.4.2' or not new['packages'][name].get('integrity','').startswith('sha512-') or not new['packages'][name].get('resolved','').startswith('https://registry.npmjs.org/')):raise ValueError('Exact verified Next package required')
            changes.append(name)
    return bases,sorted(changes)

def prepare(target):
    bases,changes=validate();target=Path(target).resolve()
    if target.exists() or target==ROOT or ROOT in target.parents:raise ValueError('Fresh external isolated directory required')
    target.mkdir(parents=True);role_dir=target/'roles';roles(role_dir)
    parent=(role_dir/'cohort.json').read_bytes()
    if parent!=(ROOT/'deployment/private-role-cohort-v1.json').read_bytes():raise ValueError('Original source cohort changed')
    cohort=json.loads(parent);cohort['baseImages']=bases
    cohort['candidate']={'identity':'52-trixie-compatibility-v1','parentCohortSHA256':digest(parent),'promotionApproved':False,'unchangedApplicationCode':True}
    for p in [Path(__file__),CANDIDATE/'base-images.json']:cohort['inputs'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    raw=encoded(cohort);pin=digest(raw);(role_dir/'cohort.json').write_bytes(raw)
    for role in ROLES:
        d=role_dir/role;own=json.loads((d/'private-role.json').read_bytes());own['cohort']=pin;body=encoded(own)
        (d/'private-cohort.json').write_bytes(raw);(d/'private-role.json').write_bytes(body)
        (d/'private_runtime/image_build.py').write_text(f'COHORT={pin!r}\nROLE_PIN={digest(body)!r}\nROLE={role!r}\n')
    front=target/'frontend-trixie';frontend(ROOT,front);(front/'deployment/private-role-cohort-v1.json').write_bytes(raw)
    patch=target/'frontend-trixie-next';shutil.copytree(front,patch)
    control=target/'frontend-bookworm-next';frontend(ROOT,control)
    for directory in [patch,control]:
        shutil.copyfile(CANDIDATE/'next-package.json',directory/'package.json')
        shutil.copyfile(CANDIDATE/'next-package-lock.json',directory/'package-lock.json')
    result={'identity':'52-trixie-compatibility-v1','promotionApproved':False,'realProviderTransport':False,'cohort':pin,'parentCohort':digest(parent),'bases':bases,'nextPatchChanges':changes,'contexts':['roles','frontend-trixie','frontend-trixie-next','frontend-bookworm-next'],'nextPackageSHA256':digest((CANDIDATE/'next-package.json').read_bytes()),'nextLockSHA256':digest((CANDIDATE/'next-package-lock.json').read_bytes())}
    (target/'candidate-build.json').write_bytes(encoded(result));return result

if __name__=='__main__':
    import sys
    print(json.dumps(prepare(sys.argv[1]),sort_keys=True))
