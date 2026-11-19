"""Reuse the existing production source projector for this native slice only.

Not a six-role release manifest. No startup/fixture signer/credential is emitted.
Planner algorithms are unchanged; provider gates and continuation retention are
finite dependency substitutions. Original source/cohorts remain byte-identical.
"""
import ast,json,shutil
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from deployment.prepare_private_services import prepare,replace
ROOT=Path(__file__).resolve().parents[2]

def backend(target):
    target=Path(target)
    if target.exists() or ROOT in target.resolve().parents:raise ValueError('Fresh isolated projection required')
    with TemporaryDirectory(prefix='whereto-native-source-') as temp:
        context=Path(temp)/'roles';parent=prepare(context)
        shutil.copytree(context/'factory/backend',target)
    inputs={};changes={}
    for name in ('provider_budget.py','places.py','routes.py','places_transport.py','routes_transport.py'):
        p=target/name;raw=p.read_text();old='from private_runtime.native_ports import require_native'
        if raw.count(old)!=1:raise ValueError('Real native guard projection changed')
        raw=raw.replace(old,'from private_runtime.real_application.native import require_native')
        if name=='provider_budget.py':
            tree=ast.parse(raw);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='local_real_enabled')
            fn.body=ast.parse('from private_runtime.real_application.native import enabled\nreturn enabled()').body
            raw=ast.unparse(tree)+'\n'
        p.write_text(raw);changes[name]=sha256(raw.encode()).hexdigest()
    # Real Google graphs are request-local. No process-global continuation stores
    # or timers are populated, even briefly. Existing ranking code is untouched.
    for name,cls,methods in [('option_sessions.py','OptionSessions',('create',)),('venue_details.py','DetailsSessions',('create','extend'))]:
        p=target/name;tree=ast.parse(p.read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        found=set()
        for fn in node.body:
            if isinstance(fn,ast.FunctionDef) and fn.name in methods:fn.body=[ast.Return(value=ast.Constant(value=None))];found.add(fn.name)
        if found!=set(methods):raise ValueError('Continuation dependency changed')
        p.write_text(ast.unparse(tree)+'\n');changes[name]=sha256(p.read_bytes()).hexdigest()
    for name in ('ai/openai_candidate.py','provider_responses.py','provider_enrollment_review.py'):
        raw=(ROOT/'backend'/name).read_bytes();(target/name).parent.mkdir(exist_ok=True);(target/name).write_bytes(raw);inputs['backend/'+name]=sha256(raw).hexdigest()
    return dict(identity='52-real-native-backend-slice-v1',parentProjection=parent,inputs=inputs,changes=changes,releaseEligible=False)
