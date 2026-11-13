"""Source projection and inactive packaging checks, not hosted application proof."""
import ast,json,unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from deployment.prepare_private_services import prepare
class Tests(unittest.TestCase):
 def test_role_outputs_and_no_fixture_or_bootstrap(self):
  with TemporaryDirectory() as tmp:
   root=Path(tmp)/'candidate';prepare(root)
   for role in ('backend','factory','counter','dispatcher','recovery'):
    files=list((root/role).rglob('*.py'));self.assertGreater(len(files),5)
    for p in files:
     ast.parse(p.read_text());self.assertFalse(p.name.startswith(('test_','run_')));self.assertNotIn(p.name,('bootstrap.py','testing_clock.py','real_fixtures.py','journey_fixtures.py'))
    self.assertFalse((root/role/'experiments/hosted_identity/bootstrap.py').exists())
    self.assertFalse((root/role/'private_runtime/test_projection.py').exists())
   for role in ('counter','recovery'):
    self.assertFalse((root/role/'backend').exists());self.assertFalse((root/role/'experiments/ordinary_ui/server.py').exists())
 def test_projected_aad_retains_canonical_bytes_and_original_bindings(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  with TemporaryDirectory() as tmp:
   root=Path(tmp)/'candidate';prepare(root)
   tree=ast.parse((root/'factory/experiments/shared_state/native_sessions.py').read_text())
   native=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeStore')
   method=next(n for n in native.body if isinstance(n,ast.FunctionDef) and n.name=='_aad')
   class Base:
    def _aad(self,meta,anchor):return json.dumps({'session':meta['session'],'anchor':anchor},sort_keys=True).encode()
   cls=ast.ClassDef(name='Candidate',bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=[method],decorator_list=[])
   unit=ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[]))
   env={'Base':Base,'canonical':lambda d:json.dumps(d,sort_keys=True).encode(),'strict_json':json.loads}
   with patch.dict('sys.modules',{'private_runtime.registry':SimpleNamespace(current=lambda:SimpleNamespace(c={'redis':{'environment':'private-staging'}})),'private_runtime.image_identity':SimpleNamespace(verify=lambda:'1'*64)}):
    exec(compile(unit,'<reviewed-aad-projection>','exec'),env)
    result=env['Candidate']()._aad({'session':'owned'},{'epoch':'2'*64})
   self.assertIs(type(result),bytes);self.assertEqual(json.loads(result),{'session':'owned','anchor':{'epoch':'2'*64},'deployment':'private-staging','runtimeBuild':'1'*64})
 def test_checked_manifest_matches_current_projection(self):
  from hashlib import sha256
  expected=Path('deployment/private-role-cohort-v1.json').read_bytes()
  with TemporaryDirectory() as tmp:
   actual=prepare(Path(tmp)/'candidate')
   self.assertEqual(actual,sha256(expected).hexdigest())
 def test_inert_startup_manifest_is_not_permission(self):
  value=json.loads(Path('deployment/private-services-v1.json').read_text());self.assertFalse(value['launchable']);self.assertFalse(value['sql']['retry']);self.assertEqual(value['providerMode'],'synthetic only; no real transport or real-token counter')
if __name__=='__main__':unittest.main()
