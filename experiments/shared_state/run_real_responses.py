"""Extend the unchanged disposable grant harness with response-codec checks.

No new storage/bootstrap protocol. Copies only explicit test/source files into
its own fixture client, then runs the existing complete grant/recovery suite.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
from hashlib import sha256
import json
from unittest.mock import patch
from experiments.shared_state.run_native import local_resources
from experiments.shared_state import run_grants as fixture


def main(*, response_only=False):
    sources=('backend/provider_responses.py','backend/ai/openai_candidate.py',
             'backend/test_provider_responses.py','experiments/shared_state/test_real_provider_response.py',
             'experiments/shared_state/run_real_responses.py','docs/task52-cloud-prompt-v51-REVIEWED-v1.json')
    pins={name:sha256((fixture.ROOT/name).read_bytes()).hexdigest() for name in sources}
    print('Offline response source pins '+json.dumps(pins,sort_keys=True),flush=True)
    original=fixture.run
    check=fixture.subprocess.check_output;execute=fixture.subprocess.run;created=set()
    def checked(command,**kwargs):
        value=check(command,**kwargs)
        if list(command)[:len(fixture.D)+2]==fixture.D+['run','-d']:
            created.add(value.decode().strip() if isinstance(value,bytes) else value.strip())
        return value
    def cleanup(command,**kwargs):
        command=list(command)
        if command[:len(fixture.D)+2]==fixture.D+['rm','-f'] and len(command)==len(fixture.D)+3 and command[-1] in created:
            command[command.index('-f')]='-fv' # Only this fixture's anonymous volumes.
        return execute(command,**kwargs)
    def run(*args,**kwargs):
        if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','unittest'):
            client=args[1]
            for name in ('backend/provider_responses.py','backend/ai/openai_candidate.py','backend/test_provider_responses.py'):
                original('cp',str(fixture.ROOT/name),client+':/app/'+name)
            with TemporaryDirectory(prefix='whereto-response-prompt-') as folder:
                docs=Path(folder)/'docs';docs.mkdir(mode=0o755)
                copyfile(fixture.ROOT/'docs/task52-cloud-prompt-v51-REVIEWED-v1.json',docs/'task52-cloud-prompt-v51-REVIEWED-v1.json')
                original('cp',str(docs),client+':/app/docs')
            result=original('exec',client,'python','-m','unittest','experiments.shared_state.test_real_provider_response','-v','-f')
            if response_only:return result
        return original(*args,**kwargs)
    fixture.run=run
    try:
        with patch.object(fixture.subprocess,'check_output',checked),patch.object(fixture.subprocess,'run',cleanup),local_resources():
            fixture.main(recovery=not response_only)
    finally:
        fixture.run=original
        if any(sha256((fixture.ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in pins.items()):
            raise RuntimeError('Offline response sources changed during test')
        print('Offline response source pin preservation: PASS',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--response-only',action='store_true')
    main(response_only=parser.parse_args().response_only)
