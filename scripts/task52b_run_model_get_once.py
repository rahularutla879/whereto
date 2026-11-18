"""Prepared model GET-only supervisor; absent owner send authorization refuses.

No enrollment command, POST, inference, key/permission change or retry option.
"""
import json
import multiprocessing
import resource
import sys
from datetime import datetime,timezone
from scripts import task52b_model_get as run
MANIFEST_SHA = '7b103d93089a50293f132914440d3632e2d9403c2d6f142b57f8166a64d4faa4'


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:run.execute_get_only(MANIFEST_SHA)
    except Exception:raise SystemExit(2) from None  # No secret/exception text.


def main():
    if sys.argv[1:]!=['--execute-model-get-once']:
        raise SystemExit('Exact model GET-only option required; no other endpoint supported')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        run.validate_preparation(MANIFEST_SHA)
        run.live_preconditions(run.STATE)
    except Exception:raise SystemExit('Model GET send not enrolled; no authorization created or consumed') from None
    if any((run.STATE/n).exists() for n in ('launcher-claim.json','supervisor-claim.json','consumed.json')):
        raise SystemExit('Model GET runner already claimed; no resend permitted')
    try:run.private_create(run.STATE/'launcher-claim.json',{'operation':run.OPERATION,'buildSHA256':MANIFEST_SHA,'supervisorPID':run.e.os.getpid(),'at':run.e.stamp()})
    except FileExistsError:raise SystemExit('Model GET runner already claimed; no resend permitted') from None
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
