"""B1 stream/deadline primitive only. No CLI, credentials, keys or network client.

A future explicitly approved operator supplies pinned pg_dump/CMS argv and a
private child environment. Importing this module cannot export or restore data.
"""
from pathlib import Path
from hashlib import sha256
import os,signal,stat,subprocess,time

class Refused(RuntimeError):pass

def stream(producer,encryptor,destination,*,producer_env,seconds=60):
    """No plaintext file/stderr log; refuse both failures and partial ciphertext.

    Deadline covers both processes. Each gets its own process group so timeout
    kills descendants. This helper issues no authorization or automatic retry.
    """
    if not 0<seconds<=60:raise Refused('deadline')
    target=Path(destination)
    if target.exists() or target.is_symlink():raise Refused('existing_generation')
    parent=target.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=os.getuid() or parent.st_mode&0o077:raise Refused('private_directory')
    partial=target.with_name(target.name+'.partial')
    fd=os.open(partial,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    children=[];start=time.monotonic()
    try:
        with os.fdopen(fd,'wb') as out:
            a=subprocess.Popen(producer,env=producer_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);children.append(a)
            try:b=subprocess.Popen(encryptor,stdin=a.stdout,stdout=out,stderr=subprocess.PIPE,env={'PATH':os.defpath,'LANG':'C'},start_new_session=True)
            finally:a.stdout.close()
            children.append(b)
            for child in children:os.set_blocking(child.stderr.fileno(),False)
            def reject_diagnostics():
                for child in children:
                    try:chunk=os.read(child.stderr.fileno(),4096)
                    except BlockingIOError:chunk=b''
                    if chunk:raise Refused('diagnostic_output')
            while any(p.poll() is None for p in children):
                reject_diagnostics()
                if any(p.poll() not in (None,0) for p in children):raise Refused('pipeline_stage')
                if partial.stat().st_size>64*1024*1024:raise Refused('ciphertext_size')
                if time.monotonic()-start>=seconds:raise Refused('deadline')
                time.sleep(.01)
            if any(p.returncode!=0 for p in children):raise Refused('pipeline_stage')
            reject_diagnostics()
            for child in children:child.stderr.close()
            out.flush();os.fsync(out.fileno())
            if partial.stat().st_size>64*1024*1024:raise Refused('ciphertext_size')
        # Exclusive final name, never replacement of a previous generation.
        os.link(partial,target);partial.unlink()
        directory=os.open(target.parent,os.O_RDONLY);os.fsync(directory);os.close(directory)
        h=sha256()
        with target.open('rb') as f:
            for block in iter(lambda:f.read(65536),b''):h.update(block)
        return {'ciphertextSHA256':h.hexdigest(),'bytes':target.stat().st_size}
    except BaseException:
        for child in children:
            # A reaped group leader may still have live descendants.
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        for child in children:
            child.wait()
            if child.stderr is not None:child.stderr.close()
        # Preserve .partial as failed, never upload/certify or retry it.
        raise Refused('incomplete_export') from None
