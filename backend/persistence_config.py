"""Select the existing restricted login without ever connecting as administrator."""
import os
from pathlib import Path
import shlex
import stat
from backend.database_check import connection_settings, DatabaseCheckError

RUNTIME_FILE = Path(__file__).with_name('.env.persistence')
KEYS = {'WHERETO_DB_'+name for name in ('HOST','PORT','NAME','USER','PASSWORD','SSLROOTCERT')}


def runtime_settings(env):
    # Explicit restricted environment wins, including deliberately bad credentials
    # during outage tests. Ordinary unconfigured startup never reads a secret file.
    user = env.get('WHERETO_DB_USER','')
    selected = env
    if user.startswith('postgres.'):
        # The owner's administrator checker configuration is not a runtime login.
        # Reuse only the separately provisioned private runtime file; do not SET ROLE
        # on an administrator connection or broaden any grants.
        try:
            info = RUNTIME_FILE.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size>4096:
                raise ValueError('Unsafe runtime configuration')
            selected = {}
            for line in RUNTIME_FILE.read_text().splitlines():
                parts = shlex.split(line, comments=True)
                if not parts: continue
                if len(parts)!=1 or '=' not in parts[0]: raise ValueError('Invalid assignment')
                key,value=parts[0].split('=',1)
                if key not in KEYS or key in selected: raise ValueError('Unknown assignment')
                selected[key]=value
        except (OSError, ValueError):
            raise DatabaseCheckError('runtime_role_required') from None
    if selected.get('WHERETO_DB_USER') and not selected['WHERETO_DB_USER'].startswith('whereto_plan_runtime.'):
        raise DatabaseCheckError('runtime_role_required')
    return connection_settings(selected)
