"""Explicit offline composite source harness; no enrollment/live command."""
from pathlib import Path
import importlib.util,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def modules():
    boot=load('_generation_boot',ROOT/'scripts/task52b_run_generation_tests.py');boot.modules()
    for name in ('task52b_real_enrollment','task52b_original_journal','task52b_enrolled_transport'):
        load('scripts.'+name,ROOT/'scripts'/f'{name}.py')
    return sys.modules['scripts.task52b_original_journal']
def main():
    modules();tests=load('_task52b_original_enrollment_tests',ROOT/'backend/test_task52b_original_enrollment.py')
    suite=unittest.defaultTestLoader.loadTestsFromModule(tests) if len(sys.argv)==1 else unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:],tests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
