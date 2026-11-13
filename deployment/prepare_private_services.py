"""Source-pinned private role projection. Never edits frozen input or provisions SQL.

Only named, count-checked dependency/guard replacements are permitted. No planner,
financial, source-validation or ordering algorithm is rewritten. Every derived
byte, parent input and transformation enters the new cohort manifest.
"""
import ast,json,hashlib,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROLES=('backend','factory','counter','dispatcher','recovery')

def sha(v):return hashlib.sha256(v).hexdigest()
def functions(source,names):
 tree=ast.parse(source);found={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))}
 if set(names)-found.keys():raise ValueError('Source declaration changed')
 return '\n\n'.join(found[n] for n in names)+'\n'
def replace(text,old,new):
 if text.count(old)!=1:raise ValueError('Reviewed projection no longer matches')
 return text.replace(old,new,1)
def source(module):
 p=ROOT/(module.replace('.','/')+'.py')
 if not p.exists():p=ROOT/module.replace('.','/')/'__init__.py'
 return p if p.exists() else None

def prepare(target):
 from experiments.ordinary_network.identity import verify
 parent=verify();target=Path(target)
 if target.exists() or ROOT in target.resolve().parents:raise ValueError('Fresh isolated context required')
 target.mkdir(parents=True);provenance={};outputs={};role_files={}
 def read(module):
  p=source(module)
  if p is None or p.is_symlink():raise ValueError('Missing reviewed module '+module)
  raw=p.read_bytes();provenance[str(p.relative_to(ROOT))]=sha(raw);return raw.decode()
 def projected(module,role):
  raw=read('experiments.service_isolation.runtime' if module=='experiments.service_isolation.runtime_dependencies' else module)
  if module=='private_runtime.owned_dispatch' and role not in ('factory','dispatcher'):
   return "from contextvars import ContextVar\nCALLER=ContextVar('non_factory_caller',default=None)\ndef configure(config):pass\n"
  if module=='private_runtime.entry' and role!='backend':
   tree=ast.parse(raw)
   class EntryRole(ast.NodeTransformer):
    def visit_If(self,node):
     if isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name) and node.test.left.id=='ROLE' and isinstance(node.test.comparators[0],ast.Constant) and node.test.comparators[0].value=='backend':return node.orelse
     return self.generic_visit(node)
   text=ast.unparse(EntryRole().visit(tree))+'\n';return text.replace('runtime, privileged_server, backend_app','runtime, privileged_server')
  if module=='private_runtime.private_service' and role not in ('factory','dispatcher'):
   tree=ast.parse(raw)
   if role!='backend':
    tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='backend_app']
    tree.body=[n for n in tree.body if not isinstance(n,ast.ImportFrom) or n.module!='experiments.ordinary_hosted.request_auth']
   class RoleOnly(ast.NodeTransformer):
    def visit_If(self,node):
     test=node.test
     if isinstance(test,ast.BoolOp) and isinstance(test.op,ast.And):
      match=next((x for x in test.values if isinstance(x,ast.Compare) and isinstance(x.left,ast.Attribute) and isinstance(x.left.value,ast.Name) and x.left.value.id=='p' and x.left.attr=='role'),None)
      if match is not None:test=match
     if isinstance(test,ast.Compare) and isinstance(test.left,ast.Attribute) and isinstance(test.left.value,ast.Name) and test.left.value.id=='p' and test.left.attr=='role' and len(test.comparators)==1 and isinstance(test.comparators[0],ast.Constant):
      if test.comparators[0].value!=role:return None
     return self.generic_visit(node)
   return ast.unparse(RoleOnly().visit(tree))+'\n'
  if module=='private_runtime.simulation':
   from backend.journey_fixtures import CASES
   read('backend.journey_fixtures')
   approved={'Buy groceries and maybe stop for coffee.','Visit the bank and grocery store, whichever is closer first.','Visit the pharmacy before the bank, but the bank before the pharmacy.'}
   data={text:record for text,record,_ in CASES if text in approved}
   if set(data)!=approved:raise ValueError('Synthetic source examples changed')
   return replace(raw,'ADDITIONAL={}','ADDITIONAL='+repr(data))
  if module=='backend.ai.ollama':
   return "from backend.ai import AIError\nclass OllamaProvider:\n def __init__(self,*a,**k):raise AIError('Hosted inference is unavailable; no local fallback')\n"
  if module=='private_runtime.registry' and role not in ('factory','dispatcher'):
   a=raw.index("            if self.role in ('factory','dispatcher'):");b=raw.index("            if self.role in ('counter','recovery'):",a);raw=raw[:a]+raw[b:]
  if module=='experiments.shared_state.contracts' and role not in ('factory','dispatcher'):
   return functions(raw,['Denied','Unavailable'])
  if module=='experiments.shared_state.evidence_models' and role not in ('factory','dispatcher'):
   return 'import json\nfrom experiments.shared_state.contracts import Denied\n'+functions(raw,['canonical','strict_json'])
  if module.startswith('experiments.') and module.endswith('_identity') or module in ('experiments.service_isolation.identity','experiments.ordinary_hosted.identity','experiments.ordinary_ui.identity','experiments.hosted_identity.identity'):
   # This is a NEW build identity; no old evaluator/source hash is returned.
   return 'from private_runtime.image_identity import verify\ndef verify_build():\n return {"identity":"52-private-role-runtime-v1","build":verify()}\n'
  if module=='experiments.service_isolation.server':
   return 'from private_runtime.registry import epoch,connection\n'
  if module=='experiments.service_isolation.auth':
   return 'import base64,json\nfrom hashlib import sha256\nfrom experiments.shared_state.evidence_models import canonical\nfrom experiments.shared_state.contracts import Denied\nMAX_BODY=200000\nMAX_RESPONSE=1048576\n'+functions(raw,['b64','unb64','binding'])
  if module=='experiments.hosted_identity.auth':
   tree=ast.parse(raw)
   tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name not in ('Auth','Client')]
   raw=ast.unparse(tree)+'\n';raw=raw.replace('Tokens, OfflineKeys, GoogleKeys','Tokens, GoogleKeys');raw=replace(raw,'import TLS, b64,','import b64,');return raw
  if module=='experiments.hosted_identity.tokens':
   tree=ast.parse(raw);tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name!='OfflineKeys'];raw=ast.unparse(tree)+'\n'
   return replace(raw,"type(keys) is not (OfflineKeys if offline else GoogleKeys)","offline or type(keys) is not GoogleKeys")
  if module=='experiments.shared_state.native_sessions':
   tree=ast.parse(raw)
   method=ast.parse('def _aad(self,meta,anchor):\n from private_runtime.registry import current\n from private_runtime.image_identity import verify\n return canonical({**strict_json(super()._aad(meta,anchor)),"deployment":current().c["redis"]["environment"],"runtimeBuild":verify()})').body[0]
   target_class=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeStore');target_class.body.append(method)
   return ast.unparse(tree)+'\n'
  if module=='experiments.shared_state.financial':
   return replace(raw,'from experiments.shared_state.postgres import LocalPostgres, uuid','from experiments.shared_state.postgres import uuid\nfrom private_runtime.native_ports import PersistentPostgres as LocalPostgres')
  if module=='experiments.shared_state.action_bridge':
   old="if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:\n            raise Denied('isolated_fixture_required')"
   return replace(raw,old,"from private_runtime.registry import current\n        current('factory')")
  if module=='experiments.service_isolation.runtime_dependencies':
   original=read('experiments.service_isolation.runtime');imports=[]
   for n in ast.parse(original).body:
    if isinstance(n,(ast.Import,ast.ImportFrom)) and not (isinstance(n,ast.ImportFrom) and n.module=='experiments.service_isolation.auth'):imports.append(ast.get_source_segment(original,n))
   return '\n'.join(imports)+'\nfrom experiments.service_isolation.auth import b64,unb64\n'+functions(original,['ScopedWitness','CounterConnection'])
  if module=='experiments.service_isolation.runtime':
   return 'from private_runtime.native_runtime import *\n'
  if module=='private_runtime.native_runtime':
   raw=read('private_runtime.native_runtime');original=read('experiments.service_isolation.runtime')
   make=functions(original,['make_broker']);make=replace(make,'from datetime import datetime','from datetime import datetime,timezone');make=replace(make,"datetime.fromisoformat(config['referenceTime'])",'datetime.now(timezone.utc)')
   return raw+'\nClient=client\n'+make
  if module=='experiments.service_isolation.factory':
   tree=ast.parse(raw)
   for n in tree.body:
    if isinstance(n,ast.ClassDef) and n.name=='Factory':n.body=[m for m in n.body if not isinstance(m,ast.FunctionDef) or m.name!='handle']
   raw=ast.unparse(tree)+'\n';return replace(raw,"revision=revision, kind='native-service-locator'","revision=revision, kind='native-service-locator', deployment=self.config['redis']['environment']")
  if module=='experiments.ordinary_ui.server':
   header='''from copy import deepcopy
from email.message import Message
from experiments.ordinary_hosted.factory import Factory as Parent
from private_runtime.registry import connection,client as Client,cache
from private_runtime.native_runtime import make_broker
from private_runtime import registry as base
from private_runtime.auth_port import authenticated as Auth
from experiments.service_isolation.auth import unb64
from experiments.shared_state.contracts import Denied
from experiments.ordinary_hosted.public_json import decode
from experiments.ordinary_hosted import request_auth
PATHS={**request_auth.PATHS,'/api/planning-mode':'GET','/api/private-ordinary/revoke':'POST'}
request_auth.PATHS=PATHS
'''
   return header+functions(raw,['Factory'])
  if module=='experiments.ordinary_hosted.factory':
   return replace(raw,'from experiments.hosted_identity.auth import Auth','from private_runtime.auth_port import authenticated as Auth')
  if module=='backend.provider_budget':
   tree=ast.parse(raw)
   for n in tree.body:
    if isinstance(n,ast.ClassDef) and n.name=='ProviderSettings':
     for m in n.body:
      if isinstance(m,ast.FunctionDef) and m.name=='require_live_provider':m.body=ast.parse('from private_runtime.native_ports import require_native\nrequire_native()').body
   return ast.unparse(tree)+'\n'
  if module in ('backend.places','backend.routes'):
   name='require_development_discovery' if module.endswith('places') else 'require_development_routes'
   tree=ast.parse(raw);found=False
   for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name==name:n.body=ast.parse('from private_runtime.native_ports import require_native\nrequire_native()').body;found=True
   if not found:raise ValueError('Native guard changed')
   return ast.unparse(tree)+'\n'
  if module=='backend.places_transport':
   return '''from experiments.shared_state.contracts import Denied
def access_token(*_):raise Denied('direct_provider_unavailable')
def text_search(body,*,field_mask=None):
 from private_runtime.native_ports import require_native
 from backend.action_dispatch import send,search
 require_native();handled,data=send(search(body,field_mask))
 if not handled:raise Denied('direct_provider_unavailable')
 return data
'''
  if module=='backend.routes_transport':
   helper=functions(raw,['_validate_basic_body'])
   return '''from backend.routes import RouteError,RoutePoint,matrix_body
from experiments.shared_state.contracts import Denied
'''+helper+'''
def compute_matrix(body):
 from private_runtime.native_ports import require_native
 from backend.action_dispatch import send,matrix
 require_native();_validate_basic_body(body);handled,data=send(matrix(body))
 if not handled:raise Denied('direct_provider_unavailable')
 return data
'''
  if module in ('backend.venue_details','backend.saved_refresh'):
   # Their HTTP routes remain disabled; raw provider implementations must not be reachable.
   return raw
  return raw
 def dependencies(module,text):
  result=set()
  for n in ast.walk(ast.parse(text)):
   if isinstance(n,ast.Import):result.update(a.name for a in n.names)
   if isinstance(n,ast.ImportFrom):
    base=n.module or ''
    if n.level:
     package=module.rsplit('.',1)[0];base='.'.join(package.split('.')[:len(package.split('.'))-n.level+1]+([base] if base else []))
    if base:result.add(base)
    result.update(base+'.'+a.name for a in n.names if a.name!='*')
  return {m for m in result if m.startswith(('backend.','experiments.','private_runtime.')) and (source(m) is not None or m=='experiments.service_isolation.runtime_dependencies')}
 for role in ROLES:
  queue=['private_runtime.entry','private_runtime.private_service','private_runtime.registry','private_runtime.image_identity'];seen={};allowed=['factory','dispatcher']
  if role in allowed:
   queue+=['experiments.shared_state.native_sessions','experiments.ordinary_ui.server','experiments.service_isolation.runtime']
   # Fixed native Graph registry; never untrusted module names from records.
   tree=ast.parse(read('experiments.shared_state.native_graph'));names=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MODULES' for t in n.targets));queue+=['backend.'+n for n in names if source('backend.'+n) is not None]
  while queue:
   module=queue.pop()
   if module in seen:continue
   if module=='private_runtime.image_build':continue
   if source(module) is None and module!='experiments.service_isolation.runtime_dependencies':raise ValueError('Missing role source '+module)
   if any(x.startswith(('test_','run_')) or x in ('bootstrap','testing_clock','real_fixtures','journey_fixtures') for x in module.split('.')):raise ValueError('Fixture dependency '+module)
   text=projected(module,role);seen[module]=text;queue+=sorted(dependencies(module,text)-seen.keys())
  files={}
  for module,text in sorted(seen.items()):
   p=source(module);name=module.replace('.','/')+('/__init__.py' if p is not None and p.name=='__init__.py' else '.py');files[name]=text.encode();outputs[role+'/'+name]=sha(text.encode())
  role_files[role]=files
 # One common protocol cohort, separate role projections. Original source bytes never change.
 provenance['deployment/prepare_private_services.py']=sha(Path(__file__).read_bytes())
 for p in [ROOT/'deployment/Dockerfile.private-service',ROOT/'deployment/requirements-private-authority-linux-amd64.lock',*sorted((ROOT/'deployment/sql').glob('hosted-*-contract-v1.sql'))]:provenance[str(p.relative_to(ROOT))]=sha(p.read_bytes())
 cohort={'identity':'52-private-role-runtime-v1','parentNetworkManifest':parent,'realProviderTransport':False,'inputs':dict(sorted(provenance.items())),'outputs':dict(sorted(outputs.items())),'baseImages':json.loads((ROOT/'deployment/base-images.json').read_text()),'lockSHA256':sha((ROOT/'deployment/requirements-private-linux-amd64.lock').read_bytes())}
 raw=(json.dumps(cohort,sort_keys=True,indent=2)+'\n').encode();pin=sha(raw)
 for role,files in role_files.items():
  directory=target/role;directory.mkdir()
  for name,body in files.items():
   p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
  own=(json.dumps({'cohort':pin,'role':role,'files':sorted(files)},sort_keys=True,indent=2)+'\n').encode()
  (directory/'private-cohort.json').write_bytes(raw);(directory/'private-role.json').write_bytes(own)
  (directory/'private_runtime/image_build.py').write_text(f'COHORT={pin!r}\nROLE_PIN={sha(own)!r}\nROLE={role!r}\n')
 (target/'cohort.json').write_bytes(raw)
 shutil.copyfile(ROOT/'deployment/requirements-private-linux-amd64.lock',target/'requirements.lock')
 shutil.copyfile(ROOT/'deployment/requirements-private-authority-linux-amd64.lock',target/'authority-requirements.lock')
 shutil.copyfile(ROOT/'deployment/Dockerfile.private-service',target/'Dockerfile')
 print(pin)
 return pin
if __name__=='__main__':prepare(sys.argv[1])
