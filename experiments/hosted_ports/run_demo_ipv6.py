"""Run only the existing disposable real-financial harness with IPv6 probes.

No live addresses, provider I/O, credential discovery, production source change
or alternate financial implementation. Existing restore/crash drills follow.
"""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from experiments.shared_state import run_grants
from private_runtime.real_finance import run_sql
from private_runtime.real_application.test_tls_setup import setup


def main():
    original=run_grants.run
    path=Path(__file__).with_name('test_demo_ipv6.py');expected=sha256(path.read_bytes()).hexdigest()
    financial=sha256((run_sql.ROOT/'private_runtime/real_finance/test_sql.py').read_bytes()).hexdigest()
    def selected(*args,**kw):
        if len(args)>4 and args[0]=='exec' and args[2:4]==('python','-c') and 'private_runtime.real_finance.test_sql' in args[4]:
            client=args[1];setup(run_grants.D,client)
            return original('exec',client,'python','-c',"from hashlib import sha256\nfrom pathlib import Path\nassert sha256(Path('/app/experiments/hosted_ports/test_demo_ipv6.py').read_bytes()).hexdigest()=="+repr(expected)+"\nassert sha256(Path('/app/private_runtime/real_finance/test_sql.py').read_bytes()).hexdigest()=="+repr(financial)+"\nfrom experiments.hosted_ports.test_demo_ipv6 import run\nrun()")
        return original(*args,**kw)
    with patch.object(run_grants,'run',selected):run_sql.main()

if __name__=='__main__':main()
