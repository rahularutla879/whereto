"""Run bounded offline suites using unchanged frozen imports plus explicit ports.

Run this file by absolute path FROM the matching B2 checkout with PYTHONPATH=.
No path overrides, metadata, credentials, real writer enrollment or live mode.
"""
import argparse
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPLAY=('backend.test_task52_q1','backend.test_task52_q2',
        'backend.test_task52_ordering_v51','backend.test_task52_version_review')
HISTORICAL=('backend.test_task52_q4c',
            'backend.test_task52_q4d','backend.test_task52_real_integration')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=('replay','boundary','historical'),required=True)
    args=parser.parse_args()
    evidence=load('scripts.task52b_evidence_access',ROOT/'scripts/task52b_evidence_access.py')
    journal_result=None
    if args.suite=='historical':
        # Q4B owns its original SH locks and deliberately tests a real EX lock.
        # Do not mask that unchanged test with an extra session-long SH lease.
        with evidence.original_evidence(lock_owner='frozen_q4b'):
            journal_result=unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromName('backend.test_task52_q4b'))
    with evidence.original_evidence():
        if args.suite=='boundary':
            identity=load('scripts.task52b_execution_identity',ROOT/'scripts/task52b_execution_identity.py')
            identity.verify()
            load('scripts.task52b_execution_boundary',ROOT/'scripts/task52b_execution_boundary.py')
            module=load('_task52b_execution_tests',ROOT/'backend/test_task52b_execution_boundary.py')
            suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        else:
            suite=unittest.defaultTestLoader.loadTestsFromNames(REPLAY if args.suite=='replay' else HISTORICAL)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and (journal_result is None or journal_result.wasSuccessful()) else 1


if __name__=='__main__':sys.exit(main())
