"""Reuse the approved disposable two-DB/Redis harness, never owner/cloud storage."""
from pathlib import Path
from hashlib import sha256
import json
from unittest.mock import patch
from experiments.shared_state import run_grants as parent
from experiments.shared_state.run_native import local_resources

ROOT=Path(__file__).resolve().parents[2]

def main():
    from .profile import verify,scripts,contracts
    manifest=verify()
    test_hash=sha256((ROOT/'private_runtime/real_finance/test_sql.py').read_bytes()).hexdigest()
    print(json.dumps(dict(event='real_finance_execution_identity',manifestSHA256=sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),testSHA256=test_hash,harnessSHA256=sha256(Path(__file__).read_bytes()).hexdigest(),sqlSHA256={k:sha256(v.encode()).hexdigest() for k,v in scripts().items()},contractSHA256={k:sha256(v.encode()).hexdigest() for k,v in contracts().items()})),flush=True)
    original=parent.run
    check=parent.subprocess.check_output;execute=parent.subprocess.run;created=set()
    before=set(check(parent.D+['volume','ls','--format','{{.Name}}'],text=True).splitlines())
    print(json.dumps(dict(event='real_finance_resource_inventory',volumes=len(before),inventorySHA256=sha256('\n'.join(sorted(before)).encode()).hexdigest())),flush=True)
    def checked(command,**kw):
        command=list(command)
        if 'pg_dump' in command:
            command=[x.replace('--schema=synthetic_state','--schema=provider_state').replace('--schema=grant_rules','--schema=provider_rules').replace('--schema=witness','--schema=provider_witness') for x in command]
        value=check(command,**kw)
        if list(command)[:len(parent.D)+2]==parent.D+['run','-d']:created.add(value.decode().strip() if isinstance(value,bytes) else value.strip())
        return value
    def cleanup(command,**kw):
        command=list(command)
        if command[:len(parent.D)+2]==parent.D+['rm','-f'] and len(command)==len(parent.D)+3 and command[-1] in created:command[command.index('-f')]='-fv'
        return execute(command,**kw)
    def run(*args,**kw):
        if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','unittest'):
            client=args[1]
            original('cp',str(ROOT/'private_runtime'),client+':/app/private_runtime')
            original('exec','--user','0',client,'mkdir','-p','/app/docs')
            original('cp',str(ROOT/'deployment/sql'),client+':/app/deployment/sql')
            for n in ('provider_responses.py','provider_enrollment_review.py'):
                original('cp',str(ROOT/'backend'/n),client+':/app/backend/'+n)
            original('cp',str(ROOT/'backend/ai/openai_candidate.py'),client+':/app/backend/ai/openai_candidate.py')
            original('cp',str(ROOT/'docs/task52-cloud-prompt-v51-REVIEWED-v1.json'),client+':/app/docs/task52-cloud-prompt-v51-REVIEWED-v1.json')
            return original('exec',client,'python','-c',f"from pathlib import Path\nfrom hashlib import sha256\nassert sha256(Path('/app/private_runtime/real_finance/test_sql.py').read_bytes()).hexdigest()=={test_hash!r}\nfrom experiments.shared_state.financial_diagnostics import observe\nimport unittest\nwith observe():\n r=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromName('private_runtime.real_finance.test_sql'))\nraise SystemExit(not r.wasSuccessful())")
        if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','experiments.shared_state.test_application_grants'):
            return original('exec',args[1],'python','-m','private_runtime.real_finance.test_sql',*args[5:],**kw)
        return original(*args,**kw)
    try:
        with patch.object(parent,'run',run),patch.object(parent.subprocess,'check_output',checked),patch.object(parent.subprocess,'run',cleanup),local_resources():parent.main(recovery=True)
    finally:
        after=set(check(parent.D+['volume','ls','--format','{{.Name}}'],text=True).splitlines())
        if not before<=after:raise RuntimeError('Pre-existing volume changed')
        print(json.dumps(dict(event='real_finance_resource_cleanup',preExistingPreserved=len(before),newVolumesRemaining=len(after-before))),flush=True)

if __name__=='__main__':main()
