"""Offline composite-source lab only; no execute/live/enrollment command."""
from pathlib import Path
import importlib.util,sys,unittest
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def modules():
 for name in ('task52b_execution_identity','task52b_execution_boundary','task52b_evidence_access','task52b_first_slot_identity','task52b_first_slot','task52b_code_identity','task52b_generation_policy','task52b_generation_candidate'):
  load('scripts.'+name,ROOT/'scripts'/f'{name}.py')
 load('_task52b_first_slot_tests',ROOT/'backend/test_task52b_first_slot.py')
 return sys.modules['scripts.task52b_generation_candidate']

def main():
 if len(sys.argv)!=1:raise SystemExit('Offline generation lab only; no inference/enrollment/live option')
 modules();tests=load('_task52b_generation_tests',ROOT/'backend/test_task52b_generation.py')
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests));return 0 if r.wasSuccessful() else 1

if __name__=='__main__':sys.exit(main())
