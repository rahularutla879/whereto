"""Actual two-PostgreSQL/Redis native slice; no live providers or host secrets."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from hashlib import sha256
from experiments.shared_state import run_grants
from private_runtime.real_finance import run_sql
from .projection import backend

def main(*,source_only=False,service_only=False):
    if type(source_only)is not bool or type(service_only)is not bool or source_only and service_only:raise ValueError('Offline cohort selection')
    test_names=['private_runtime.real_application.test_checkpoint']
    if not source_only:test_names.append('private_runtime.real_application.test_native')
    if service_only:test_names=['private_runtime.real_application.test_services']
    from .sql import application_sql
    root=Path(__file__).resolve().parent
    test_hash=sha256((root/'test_native.py').read_bytes()).hexdigest()
    service_test_hash=sha256((root/'test_services.py').read_bytes()).hexdigest()
    checkpoint_test_hash=sha256((root/'test_checkpoint.py').read_bytes()).hexdigest()
    diagnostic_hash=sha256((root/'test_diagnostics.py').read_bytes()).hexdigest()
    print(json.dumps(dict(event='real_native_execution_identity',testModules=test_names,sourcesSHA256=sha256((root/'sources.json').read_bytes()).hexdigest(),testSHA256=test_hash,checkpointTestSHA256=checkpoint_test_hash,serviceTestSHA256=service_test_hash,diagnosticSHA256=diagnostic_hash,harnessSHA256=sha256(Path(__file__).read_bytes()).hexdigest(),applicationSQLSHA256=sha256(application_sql().encode()).hexdigest())),flush=True)
    original=run_grants.run
    with TemporaryDirectory(prefix='whereto-real-native-run-') as tmp:
        projected=Path(tmp)/'backend';manifest=backend(projected)
        print(json.dumps(dict(event='real_native_projection',**manifest)),flush=True)
        def run(*args,**kw):
            if len(args)>4 and args[0]=='exec' and args[2:4]==('python','-c') and 'private_runtime.real_finance.test_sql' in args[4]:
                client=args[1]
                if service_only:
                    import zipfile
                    doc=json.loads((run_sql.ROOT/'experiments/hosted_identity/dependency.json').read_bytes());wheel=Path('/tmp/whereto-evidence-wheels')/doc['file']
                    if sha256(wheel.read_bytes()).hexdigest()!=doc['sha256']:raise ValueError('JWT wheel identity')
                    with TemporaryDirectory() as deps:
                        with zipfile.ZipFile(wheel) as archive:archive.extractall(deps)
                        original('cp',deps+'/.',client+':/tmp/evidence-deps')
                original('cp',str(run_sql.ROOT/'private_runtime'),client+':/app/private_runtime')
                original('exec','--user','0',client,'mkdir','-p','/app/docs')
                original('cp',str(run_sql.ROOT/'docs/task52-cloud-prompt-v51-REVIEWED-v1.json'),client+':/app/docs/task52-cloud-prompt-v51-REVIEWED-v1.json')
                original('cp',str(run_sql.ROOT/'deployment/sql'),client+':/app/deployment/sql')
                original('cp',str(run_sql.ROOT/'deployment/prepare_private_services.py'),client+':/app/deployment/prepare_private_services.py')
                for name in ('test_provider_responses.py',):original('cp',str(run_sql.ROOT/'backend'/name),client+':/app/backend/'+name)
                original('cp',str(projected)+'/.',client+':/app/backend')
                return original('exec',client,'python','-c',f"import unittest\nfrom hashlib import sha256\nfrom pathlib import Path\nassert sha256(Path('/app/private_runtime/real_application/test_native.py').read_bytes()).hexdigest()=={test_hash!r}\nassert sha256(Path('/app/private_runtime/real_application/test_checkpoint.py').read_bytes()).hexdigest()=={checkpoint_test_hash!r}\nassert sha256(Path('/app/private_runtime/real_application/test_services.py').read_bytes()).hexdigest()=={service_test_hash!r}\nassert sha256(Path('/app/private_runtime/real_application/test_diagnostics.py').read_bytes()).hexdigest()=={diagnostic_hash!r}\nfrom private_runtime.real_application.test_diagnostics import observe as session_observe\nfrom experiments.shared_state.financial_diagnostics import observe\nwith observe(),session_observe():\n r=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromNames({test_names!r}))\nraise SystemExit(not r.wasSuccessful())")
            if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','private_runtime.real_finance.test_sql'):
                return original('exec',args[1],'python','-m','private_runtime.real_application.test_native',*args[5:],**kw)
            return original(*args,**kw)
        # Reuse existing resource caps, ephemeral wheel identities and ownership
        # cleanup. Run serially: no unrelated cohort inventory may disappear.
        with patch.object(run_grants,'run',run):run_sql.main()

if __name__=='__main__':main()
