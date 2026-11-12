"""Reuse the frozen disposable grant harness; redirect only synthetic test selection."""
from unittest.mock import patch
from contextlib import contextmanager
from unittest import TestCase
from experiments.shared_state import run_grants

@contextmanager
def local_resources():
    """Rebalance caps inside the unchanged approved2-CPU/4-GiB VM, never SQL timeouts."""
    original=run_grants.subprocess.check_output
    def checked(command,**kwargs):
        command=list(command)
        if command[:len(run_grants.D)+2]==run_grants.D+['run','-d']:
            if 'POSTGRES_DB=whereto_synthetic' in command:
                i=command.index('--cpus');command[i+1]='1'
            elif run_grants.REDIS in command:
                i=command.index('--cpus');command[i+1]='.25'
        return original(command,**kwargs)
    with patch.object(run_grants.subprocess,'check_output',checked):yield


def main(tests=('NativeTests',),recovery=True):
    if type(tests) is not tuple or any(x not in ('NativeTests','ProcessTests','CodecTests') for x in tests):raise ValueError('Native tests only')
    original=run_grants.run
    def selected(*args,**kwargs):
        if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','unittest'):
            args=(*args[:5],*['experiments.shared_state.test_native_sessions.'+x for x in tests],'-v','-f')
        elif len(args)>4 and args[0]=='exec' and args[2:5]==('python','-m','experiments.shared_state.test_application_grants'):
            args=(*args[:4],'experiments.shared_state.test_native_sessions',*args[5:])
        return original(*args,**kwargs)
    with local_resources(),patch.object(run_grants,'run',selected):run_grants.main(recovery=recovery)

class ResourceTests(TestCase):
    def test_local_caps_change_only_disposable_fixture_creation(self):
        with patch.object(run_grants.subprocess,'check_output',return_value=b'synthetic') as called:
            with local_resources():
                command=run_grants.D+['run','-d','--cpus','.5','-e','POSTGRES_DB=whereto_synthetic',run_grants.PG]
                run_grants.subprocess.check_output(command)
                self.assertEqual(called.call_args.args[0][called.call_args.args[0].index('--cpus')+1],'1')
                command=run_grants.D+['run','-d','--cpus','.1',run_grants.REDIS]
                run_grants.subprocess.check_output(command)
                self.assertEqual(called.call_args.args[0][called.call_args.args[0].index('--cpus')+1],'.25')
                untouched=['not-a-fixture','--cpus','.5'];run_grants.subprocess.check_output(untouched)
                self.assertEqual(called.call_args.args[0],untouched)

if __name__=='__main__':main(('CodecTests','NativeTests','ProcessTests'))
