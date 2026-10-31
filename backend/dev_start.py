"""Owner-only local launcher. Configuration is data, never shell code."""
import argparse
import os
from pathlib import Path
import shlex
import stat

PROFILE = Path(__file__).with_name('.env.development')
RUNTIME = Path(__file__).with_name('.env.persistence')
FLAGS = {'VENUE_DATA_MODE','WHERETO_REAL_DEV','WHERETO_ENV','WHERETO_EXPLORATION_DEV',
         'WHERETO_DEV_DAILY_USD','WHERETO_DEV_WARN_USD','WHERETO_RATINGS_DEV',
         'WHERETO_CONTACT_DETAILS_DEV','WHERETO_START_LOOKUP_DEV','WHERETO_DIAGNOSTICS_DEV'}
DB_KEYS = {'WHERETO_DB_'+key for key in ('HOST','PORT','NAME','USER','PASSWORD','SSLROOTCERT')}


def read_private(path, allowed):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_size>4096:
        raise ValueError('Private configuration must be an owner-only regular file (chmod 600).')
    values={}
    for line in path.read_text().splitlines():
        parts=shlex.split(line,comments=True)
        if not parts:continue
        if len(parts)!=1 or '=' not in parts[0]:raise ValueError('Use plain KEY=value assignments, without shell commands.')
        key,value=parts[0].split('=',1)
        if key not in allowed or key in values:raise ValueError('Unknown or duplicate local configuration key.')
        values[key]=value
    return values


def environment(env, *, mock=False, profile=PROFILE, runtime=RUNTIME):
    result=dict(env)
    if any(env.get(k) for k in ('CI','VERCEL','RENDER','RAILWAY_ENVIRONMENT','K_SERVICE','NETLIFY','FLY_APP_NAME','DYNO','AWS_EXECUTION_ENV','CODESPACES','GITHUB_ACTIONS','WEBSITE_HOSTNAME')) or env.get('NODE_ENV')=='production':
        raise ValueError('This launcher is for local development only; CI and production must not load owner profiles.')
    if profile.exists() and not mock:
        values=read_private(profile,FLAGS)
        if values.get('VENUE_DATA_MODE') not in ('real','mock'):raise ValueError('Local profile needs VENUE_DATA_MODE=real or mock.')
        for key,value in values.items():
            if key.endswith('_DEV') and value not in ('0','1'):raise ValueError('Development flags must be 0 or 1.')
        result.update(values)
    if mock:
        result.update(VENUE_DATA_MODE='mock',WHERETO_REAL_DEV='0',WHERETO_EXPLORATION_DEV='0')
    if runtime.exists():
        values=read_private(runtime,DB_KEYS)
        if not values.get('WHERETO_DB_USER','').startswith('whereto_plan_runtime.'):
            raise ValueError('Use the restricted backend/.env.persistence login, never the migration administrator.')
        from backend.database_check import connection_settings,DatabaseCheckError
        try:connection_settings(values)
        except DatabaseCheckError:raise ValueError("Restricted database TLS configuration is incomplete.") from None
        # connection_settings(values) # Validate TLS settings before starting, no connection.
        for key in DB_KEYS:result.pop(key,None)
        result.update(values)
    elif result.get('VENUE_DATA_MODE')=='real':
        raise ValueError('Restricted backend/.env.persistence is missing. See docs/database-setup.md; do not recreate the project.')
    for key in ('WHERETO_DEV_DAILY_USD','WHERETO_DEV_WARN_USD'):
        if key in result:
            from decimal import Decimal
            try:value=Decimal(result[key])
            except Exception:raise ValueError('Development warning amounts must be numbers.') from None
            if not value.is_finite() or value<0:raise ValueError('Development warning amounts must be nonnegative numbers.')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mock',action='store_true')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--no-reload',action='store_true')
    args=parser.parse_args()
    try:settings=environment(os.environ,mock=args.mock)
    except (OSError,ValueError) as error:
        # These messages are fixed configuration instructions, never values.
        print('Backend configuration could not load. Check private profile permissions/assignments and restricted database settings. See docs/database-setup.md.')
        raise SystemExit(1) from None
    os.environ.clear();os.environ.update(settings)
    print('Local backend starting in '+settings.get('VENUE_DATA_MODE','mock')+' mode. Provider requests require deliberate actions.')
    import uvicorn
    uvicorn.run('backend.main:app',host='127.0.0.1',port=args.port,reload=not args.no_reload,reload_dirs=['backend'] if not args.no_reload else None,access_log=False)

if __name__=='__main__':main()
