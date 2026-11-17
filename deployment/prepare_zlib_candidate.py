"""One signed-package delta over the existing inactive Trixie candidate.

No network, installer execution, financial policy or normal startup selection.
The reviewed Debian archive is mounted only during image build, never shipped.
"""
from pathlib import Path
import json,shutil,re
from deployment import prepare_trixie_candidate as parent
from deployment.prepare_private_services import ROOT,ROLES
from deployment.prepare_trixie_candidate import digest,encoded

DIRECTORY=ROOT/'deployment/candidates/trixie-zlib-v2'
OLD='1:1.3.dfsg+really1.3.1-1+b1'
FIXED='1:1.3.dfsg+really1.3.1-1+deb13u1'
def package(archive):
    m=json.loads((DIRECTORY/'security-package.json').read_text());p=Path(archive)
    if (m['promotionApproved'] is not False or m['package']!='zlib1g' or m['sourcePackage']!='zlib' or m['architecture']!='amd64'
        or m['oldVersion']!=OLD or m['version']!=FIXED or m['confirmedFix']!='CVE-2026-85091'
        or not re.fullmatch('[0-9a-f]{64}',m['sha256'])
        or not m['url'].startswith('https://deb.debian.org/debian-security/pool/updates/main/z/zlib/')
        or p.is_symlink() or not p.is_file() or p.stat().st_size!=m['size'] or digest(p.read_bytes())!=m['sha256']):raise ValueError('Exact reviewed Debian security archive required')
    return m

def dockerfile(text,variable,reference,m):
    old=next(line for line in text.splitlines() if line.startswith('ARG '+variable+'='))
    if text.count('FROM ${'+variable+'} AS ')!=2:raise ValueError('Reviewed Dockerfile stages changed')
    text=text.replace('FROM ${'+variable+'} AS ','FROM security_base AS ')
    stage=f'''ARG {variable}={reference}
FROM ${{{variable}}} AS security_base
# Exact Debian13 security package, SHA checked against signed APT metadata.
RUN --mount=type=bind,source=security/zlib1g.deb,target=/tmp/zlib1g.deb,readonly \\
    . /etc/os-release && test "$ID:$VERSION_ID" = "debian:13" \\
    && printf '%s  %s\\n' '{m['sha256']}' /tmp/zlib1g.deb | sha256sum -c - \\
    && test "$(dpkg-query -W -f='${{Version}}' zlib1g)" = '{OLD}' \\
    && dpkg -i /tmp/zlib1g.deb \\
    && test "$(dpkg-query -W -f='${{Version}}' zlib1g)" = '{FIXED}' \\
    && dpkg --audit
'''
    return text.replace(old,stage,1)

def prepare(target,archive):
    m=package(archive);out=Path(target).resolve();build=parent.prepare(out)
    role_dir=out/'roles';front=out/'frontend-trixie-next';old_raw=(role_dir/'cohort.json').read_bytes()
    for directory in [role_dir,front]:
        (directory/'security').mkdir();shutil.copyfile(archive,directory/'security/zlib1g.deb')
    py=role_dir/'Dockerfile';node=front/'deployment/Dockerfile.frontend-private'
    py.write_text(dockerfile(py.read_text(),'PYTHON_IMAGE',build['bases']['images']['python']['reference'],m))
    node.write_text(dockerfile(node.read_text(),'NODE_IMAGE',build['bases']['images']['node']['reference'],m))
    cohort=json.loads(old_raw);cohort['candidate'].update(identity='52-trixie-zlib-v2',priorCandidateCohortSHA256=digest(old_raw),securityPackage=m,derivedDockerfiles={'python':digest(py.read_bytes()),'frontend':digest(node.read_bytes())})
    for p in [Path(__file__),DIRECTORY/'security-package.json']:cohort['inputs'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    raw=encoded(cohort);pin=digest(raw);(role_dir/'cohort.json').write_bytes(raw)
    for role in ROLES:
        d=role_dir/role;own=json.loads((d/'private-role.json').read_bytes());own['cohort']=pin;body=encoded(own)
        (d/'private-cohort.json').write_bytes(raw);(d/'private-role.json').write_bytes(body)
        (d/'private_runtime/image_build.py').write_text(f'COHORT={pin!r}\nROLE_PIN={digest(body)!r}\nROLE={role!r}\n')
    (front/'deployment/private-role-cohort-v1.json').write_bytes(raw)
    build.update(identity='52-trixie-zlib-v2',cohort=pin,priorCandidateCohort=digest(old_raw),securityPackage=m,contexts=['roles','frontend-trixie-next'])
    (out/'candidate-build.json').write_bytes(encoded(build));return build

if __name__=='__main__':
    import sys
    print(json.dumps(prepare(*sys.argv[1:]),sort_keys=True))
