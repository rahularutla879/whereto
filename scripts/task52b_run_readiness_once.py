"""Explicit one-shot supervisor for the separately authorized readiness pair."""
import json
import multiprocessing
import resource
import sys
from scripts import task52b_readiness_enrolled as run
MANIFEST_SHA = '3a7a8dd5c9c6b0272d515e742b158bb42f4d01e50e14529bf374c9f65d034517'


def child():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try: run.execute_authorized(MANIFEST_SHA)
    except Exception:
        # No traceback, secret paths or exception text in terminal/logs.
        raise SystemExit(2) from None


def main():
    if sys.argv[1:] != ['--execute-authorized-readiness-once']:
        raise SystemExit('Exact readiness-only option required; no live inference option')
    run.verify_build(MANIFEST_SHA)
    run.private_directory(run.STATE)
    if (run.STATE/'consumed.json').exists():
        raise SystemExit('Readiness authorization already consumed; no request repeated')
    try:run.private_create(run.STATE/'supervisor-claim.json',{'operation':run.OPERATION,'buildSHA256':MANIFEST_SHA,'at':run.stamp()})
    except FileExistsError:raise SystemExit('Readiness runner already claimed; no request repeated') from None
    context=multiprocessing.get_context('spawn');p=context.Process(target=child)
    p.start()
    try:
        p.join(60)
        if p.is_alive():p.kill();p.join();reason='supervisor_deadline_no_retry'
        else:reason='worker_exit'
    except BaseException:
        if p.is_alive():p.kill();p.join()
        run.private_create(run.STATE/'supervisor.json',{'reason':'operator_interrupted_no_retry','at':run.stamp()})
        raise SystemExit('Stopped; inspect durable private evidence; never retry') from None
    run.private_create(run.STATE/'supervisor.json',{'reason':reason,'exit':p.exitcode,'at':run.stamp()})
    if (run.STATE/'result.json').exists():
        value=run.record(run.STATE/'result.json');print(json.dumps(value,sort_keys=True))
    else:
        print(json.dumps({'operation':run.OPERATION,'result':'stopped','reason':reason,'consumed':(run.STATE/'consumed.json').exists(),'inference':0}))


if __name__=='__main__':main()
