"""New runtime-cohort identity. Never authorizes a historical evaluator build."""
from pathlib import Path
from hashlib import sha256
import json,os,stat
from experiments.shared_state.contracts import Denied
_checked=False

def verify():
    global _checked
    from private_runtime.image_build import COHORT,ROLE_PIN
    root=Path(__file__).resolve().parents[1]
    if _checked:return COHORT
    raw=(root/'private-cohort.json').read_bytes();own=(root/'private-role.json').read_bytes()
    if sha256(raw).hexdigest()!=COHORT or sha256(own).hexdigest()!=ROLE_PIN:raise Denied('runtime_cohort')
    manifest=json.loads(raw);role=json.loads(own);immutable=os.getuid()!=0
    if role['cohort']!=COHORT or role['role'] not in ('backend','factory','counter','dispatcher','recovery'):raise Denied('runtime_role')
    for name in role['files']:
        path=root/name
        if path.is_symlink() or name.startswith('/') or '..' in Path(name).parts or sha256(path.read_bytes()).hexdigest()!=manifest['outputs'][role['role']+'/'+name]:raise Denied('runtime_source')
        # Cache only kernel-enforced root ownership and non-writable ancestors.
        for item in (path,*path.parents):
            if item==root.parent:break
            st=item.stat();immutable=immutable and st.st_uid==0 and not st.st_mode&0o022 and (not stat.S_ISREG(st.st_mode) or not st.st_mode&0o200)
    _checked=immutable
    return COHORT
