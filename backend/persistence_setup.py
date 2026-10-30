"""One-time explicit admin setup for a separate restricted backend login.

Reads existing admin env; writes a new private file, never prints secrets.
Does not overwrite or rotate an existing configuration.
"""
import os
from pathlib import Path
import secrets
import shlex

import psycopg
from psycopg import sql
from backend.database_check import connection_settings


def main():
    target = Path(__file__).with_name('.env.persistence')
    if target.exists():
        print('Persistence configuration already exists; left unchanged.')
        return 0
    try:
        settings = connection_settings(os.environ)
        suffix = settings['user'].split('.', 1)[1]
        password = secrets.token_urlsafe(48)
        # Exclusive creation prevents replacement; file is private before writing.
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with psycopg.connect(**settings) as connection:
                if not connection.pgconn.ssl_in_use:
                    raise ValueError()
                connection.execute("SET LOCAL statement_timeout='5s'")
                connection.execute(sql.SQL('ALTER ROLE whereto_plan_runtime PASSWORD {}').format(sql.Literal(password)))
                values = {key: os.environ[key] for key in ('WHERETO_DB_HOST','WHERETO_DB_NAME','WHERETO_DB_SSLROOTCERT')}
                values.update(WHERETO_DB_PORT='5432', WHERETO_DB_USER='whereto_plan_runtime.'+suffix, WHERETO_DB_PASSWORD=password)
                with os.fdopen(descriptor, 'w') as file:
                    descriptor = None
                    file.write(''.join(f'{key}={shlex.quote(value)}\n' for key,value in values.items()))
                    file.flush()
                    os.fsync(file.fileno())
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            target.unlink(missing_ok=True)
            raise
    except Exception:
        print('Private persistence setup failed. Check configuration privately; no credentials displayed.')
        return 1
    print('Restricted runtime login configured in ignored backend/.env.persistence (0600).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
