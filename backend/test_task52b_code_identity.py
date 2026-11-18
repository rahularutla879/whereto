"""Stable code identities retain source, constants, defaults and namespace binding."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import FunctionType
import ast,hashlib,marshal,subprocess,sys,unittest
from scripts import task52b_code_identity as identity
from scripts import task52b_model_get as g

class IdentityTests(unittest.TestCase):
 def test_reference_changes_and_marshal_flags_do_not_change_identity(self):
  code=g.GetOnlyHTTPS.exchange.__code__;i=code.co_consts.index('/v1/models/gpt-6-luna')
  stable=identity.fingerprint(code);before=marshal.dumps(code);held=code.co_consts[i];during=marshal.dumps(code)
  self.assertNotEqual(before,during);self.assertEqual(stable,identity.fingerprint(code));del held
  self.assertEqual(before,marshal.dumps(code));self.assertEqual(stable,identity.fingerprint(code))
 def test_full_code_fields_and_typed_constants_are_bound(self):
  code=g.GetOnlyHTTPS.exchange.__code__;base=identity.fingerprint(code)
  for changed in (code.replace(co_code=code.co_code+b'\x09\x00'),code.replace(co_consts=code.co_consts+('CHANGED',)),code.replace(co_exceptiontable=code.co_exceptiontable+b'\0'),code.replace(co_filename='CHANGED'),code.replace(co_linetable=b''),code.replace(co_names=code.co_names+('CHANGED',))):
   self.assertNotEqual(base,identity.fingerprint(changed))
  self.assertNotEqual(identity.canonical(True),identity.canonical(1));self.assertNotEqual(identity.canonical(1),identity.canonical(1.0))
  self.assertEqual(identity.canonical(frozenset((2,1))),identity.canonical(frozenset((1,2))))
 def test_pinned_compilation_and_loaded_method_equal(self):
  fn=g.GetOnlyHTTPS.exchange;p=Path(g.__file__);sha=hashlib.sha256(p.read_bytes()).hexdigest()
  expected=identity.compiled(p,sha,'GetOnlyHTTPS.exchange')
  self.assertEqual(expected,identity.require(fn,p,sha,'GetOnlyHTTPS.exchange',g.__dict__))
  self.assertEqual(expected,identity.fingerprint(fn.__code__))
 def test_different_code_globals_defaults_or_source_refuse(self):
  fn=g.GetOnlyHTTPS.exchange;p=Path(g.__file__);sha=hashlib.sha256(p.read_bytes()).hexdigest()
  foreign=FunctionType(fn.__code__,dict(g.__dict__),fn.__name__);foreign.__qualname__=fn.__qualname__
  with self.assertRaises(identity.IdentityRefused):identity.require(foreign,p,sha,fn.__qualname__,g.__dict__)
  changed=FunctionType(fn.__code__.replace(co_consts=fn.__code__.co_consts+('CHANGED',)),g.__dict__,fn.__name__);changed.__qualname__=fn.__qualname__
  with self.assertRaises(identity.IdentityRefused):identity.require(changed,p,sha,fn.__qualname__,g.__dict__)
  default=FunctionType(fn.__code__,g.__dict__,fn.__name__,('CHANGED',));default.__qualname__=fn.__qualname__
  with self.assertRaises(identity.IdentityRefused):identity.require(default,p,sha,fn.__qualname__,g.__dict__)
  with self.assertRaises(identity.IdentityRefused):identity.require(fn,p,'0'*64,fn.__qualname__,g.__dict__)
 def test_independent_clean_interpreters_agree(self):
  command='import sys;sys.path.insert(0,'+repr(str(g.ROOT))+');from scripts import task52b_model_get as g;print(g.identity_manifest()["loadedCodeIdentities"]["wire"])'
  values=[subprocess.check_output([sys.executable,'-I','-B','-c',command],env={'PATH':'/usr/bin:/bin'}).decode().strip() for _ in range(3)]
  self.assertEqual(len(set(values)),1);self.assertEqual(values[0],g.identity_manifest()['loadedCodeIdentities']['wire'])
