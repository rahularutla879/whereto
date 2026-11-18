"""Prepared count-only supervisor; absent owner send authorization refuses.

No enrollment command, GET, inference, key/permission change or retry option.
"""
import json
import multiprocessing
import resource
import sys
from datetime import datetime,timezone
from scripts import task52b_count_only as run
MANIFEST_SHA = '9adaaa19c20e6bead0aab4fd6ed638946d3e2e894fd1a3fcf3c58f5fe7879344'


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:run.execute_count_only(MANIFEST_SHA)
    except Exception:raise SystemExit(2) from None  # No secret/exception text.


def main():
    if sys.argv[1:]!=['--execute-count-only-once']:
        raise SystemExit('Exact count-only option required; no other endpoint supported')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        run.validate_preparation(MANIFEST_SHA)
        run.live_preconditions(run.STATE,datetime.now(timezone.utc))
    except Exception:raise SystemExit('Count send not enrolled; no authorization created or consumed') from None
    if any((run.STATE/n).exists() for n in ('launcher-claim.json','supervisor-claim.json','consumed.json')):
        raise SystemExit('Count runner already claimed; no resend permitted')
    try:run.private_create(run.STATE/'launcher-claim.json',{'operation':run.OPERATION,'buildSHA256':MANIFEST_SHA,'supervisorPID':run.e.os.getpid(),'at':run.e.stamp()})
    except FileExistsError:raise SystemExit('Count runner already claimed; no resend permitted') from None
    p=multiprocessing.get_context('spawn').Process(target=child);reason='worker_exit'
    try:
        p.start();p.join(60)
        if p.is_alive():p.kill();p.join();reason='supervisor_deadline_no_retry'
    except BaseException:
        if p.pid and p.is_alive():p.kill();p.join()
        run.private_create(run.STATE/'supervisor.json',{'reason':'interrupted_no_retry','at':run.e.stamp()})
        raise SystemExit('Stopped; inspect private evidence; never retry') from None
    run.private_create(run.STATE/'supervisor.json',{'reason':reason,'exit':p.exitcode,'at':run.e.stamp()})
    result=run.e.record(run.STATE/'result.json') if (run.STATE/'result.json').exists() else {'operation':run.OPERATION,'result':'stopped','reason':reason,'inference':0}
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
