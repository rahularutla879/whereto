"""Explicit local HTTPS test driver; no live/account/credential CLI."""
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv)!=1:raise SystemExit("Offline TLS tests only; no account/live options")
    # Keep unchanged B2 imports in the matching checkout; load only new modules.
    load('scripts.task52b_execution_identity',ROOT/'scripts/task52b_execution_identity.py')
    load('scripts.task52b_execution_boundary',ROOT/'scripts/task52b_execution_boundary.py')
    load('scripts.task52b_evidence_access',ROOT/'scripts/task52b_evidence_access.py')
    load('scripts.task52b_first_slot_identity',ROOT/'scripts/task52b_first_slot_identity.py').verify(full=True)
    load('scripts.task52b_first_slot',ROOT/'scripts/task52b_first_slot.py')
    tests=load('_task52b_first_slot_tests',ROOT/'backend/test_task52b_first_slot.py')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
