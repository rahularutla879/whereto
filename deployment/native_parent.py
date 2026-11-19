"""Build the frozen parent in its exact source snapshot, never repin its checks.

Build-time only; no Git/owner files are required by a deployed application.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import io,json,os,subprocess,sys,tarfile
COMMIT='85a0e0b3a5626c69073853a7ac6ad8eb13180f92'
ROOT=Path(__file__).resolve().parents[1]

def prepare(target):
    target=Path(target).resolve()
    if target.exists() or ROOT in target.parents:raise ValueError('Fresh isolated parent target required')
    with TemporaryDirectory(prefix='whereto-frozen-parent-') as temp:
        source=Path(temp)/'source';source.mkdir()
        raw=subprocess.check_output(['git','archive','--format=tar',COMMIT],cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:archive.extractall(source,filter='data')
        # The unchanged parent validates ALL its original frontend/backend pins.
        code='from deployment.prepare_private_services import prepare; print(prepare('+repr(str(target))+'))'
        result=subprocess.run([sys.executable,'-c',code],cwd=source,env={**os.environ,'PYTHONPATH':str(source),'PYTHONNOUSERSITE':'1'},check=True,capture_output=True,text=True)
        parent=result.stdout.strip().splitlines()[-1]
        if parent!='53c8a313b0bf1f80f5b743f7753c88cea62c98590c70b880dfe6a5a1de8f44e4':raise ValueError('Frozen parent projection changed')
        return parent
