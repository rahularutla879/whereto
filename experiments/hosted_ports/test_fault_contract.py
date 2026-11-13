import unittest,tempfile,importlib.util,traceback,marshal,hashlib,linecache
from pathlib import Path
from experiments.hosted_ports.fault_contract import assert_state,EXPECTED
class Tests(unittest.TestCase):
 def test_exact_expected_history_and_every_wrong_dimension_refuse(self):
  assert_state(EXPECTED,EXPECTED)
  for value in [(0,1,0),(6845,0,0),(6845,1,1),(6846,1,0)]:
   with self.assertRaises(AssertionError):assert_state(value,value)
  with self.assertRaises(AssertionError):assert_state(EXPECTED,(0,0,0))
 def test_mutating_source_can_misreport_the_loaded_assertion(self):
  # Reproduce a plausible mechanism, not proof of the original unknown failure.
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'case.py';p.write_text('def check(value):\n assert value == 0\n')
   spec=importlib.util.spec_from_file_location('mutable_case',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   loaded=hashlib.sha256(marshal.dumps(module.check.__code__)).hexdigest()
   p.write_text('def check(value):\n assert value == 1 # changed source\n');linecache.clearcache()
   try:module.check(1)
   except AssertionError:
    self.assertIn('value == 1',traceback.format_exc())
   else:self.fail('Loaded old assertion should fail')
   self.assertEqual(loaded,hashlib.sha256(marshal.dumps(module.check.__code__)).hexdigest())
if __name__=='__main__':unittest.main()
