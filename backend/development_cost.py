"""Local estimate guard. No credentials, request identities or Google content."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path
import stat
from time import time

# USD millionths/event, global first paid tier, checked 2026-10-26.
RATES = {'search_pro': 32000, 'search_enterprise': 35000, 'details': 20000, 'matrix_element': 5000}
_active = ContextVar('development_cost_reservation', default=None)


class AccountingError(RuntimeError):
    pass


def daily_limit():
    try:
        n = Decimal(os.environ.get('WHERETO_DEV_DAILY_USD', '10'))
        if not n.is_finite() or n <= 0 or n.as_tuple().exponent < -6:
            raise ValueError()
        return int(n * 1000000)
    except (InvalidOperation, ValueError):
        raise AccountingError('Invalid local daily spending allowance. Set WHERETO_DEV_DAILY_USD to a positive USD amount.') from None


def dispatch(operation, count=1):
    """Called at the transport boundary, after authentication, before actual I/O."""
    active = _active.get()
    if not active and os.environ.get('WHERETO_EXPLORATION_DEV') == '1':
        from backend.provider_budget import ProviderLimitError
        raise ProviderLimitError('Exploration provider work requires a reserved local cost allowance.')
    if active:
        try: active(operation, count)
        except (AccountingError, OSError):
            from backend.provider_budget import ProviderLimitError
            raise ProviderLimitError('Local cost accounting failed before provider dispatch. No request was sent.') from None


class DevelopmentCost:
    def __init__(self):
        self.limit = daily_limit()
        self.path = Path(os.environ.get('WHERETO_DEV_COST_LEDGER', str(Path.home()/'.local/state/whereto/development-cost.json'))).expanduser()
        if not self.path.is_absolute():
            raise AccountingError('Use an absolute private path for local development cost accounting.')

    @contextmanager
    def locked(self):
        fd = None
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                created = True
            except FileExistsError:
                fd = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW)
                created = False
            if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_mode & 0o077:
                raise ValueError()
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if created:
                data = {'version': 1, 'days': {}, 'recent': []}
                self.write(fd, data)
            else:
                data = json.loads(os.read(fd, os.fstat(fd).st_size), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if (set(data) != {'version','days','recent'} or type(data['version']) is not int or data['version'] != 1
                    or not isinstance(data['days'], dict) or not isinstance(data['recent'], list)):
                raise ValueError()
            for day, row in data['days'].items():
                datetime.strptime(day, '%Y-%m-%d')
                if (set(row) != {'grossMicrousd','reserved','dispatched'} or type(row['grossMicrousd']) is not int or row['grossMicrousd'] < 0):
                    raise ValueError()
                for key in ('reserved','dispatched'):
                    if not isinstance(row[key],dict) or any(k not in RATES or type(v) is not int or v<0 for k,v in row[key].items()):
                        raise ValueError()
                if row['grossMicrousd'] != sum(RATES[k]*v for k,v in row['reserved'].items()):
                    raise ValueError()
            if any(not isinstance(e,list) or len(e)!=3 or type(e[0]) not in (int,float) or e[1] not in ('search','details','elements') or type(e[2]) is not int or e[2]<0 for e in data['recent']):
                raise ValueError()
            yield fd, data
        except (OSError, ValueError, TypeError, KeyError):
            raise AccountingError('Local development cost accounting is unavailable, busy or invalid. No new provider work was admitted; inspect the ledger without deleting usage.') from None
        finally:
            if fd is not None:
                os.close(fd)

    @staticmethod
    def write(fd, data):
        encoded = json.dumps(data, sort_keys=True).encode()
        os.lseek(fd, 0, 0)
        os.ftruncate(fd, 0)
        if os.write(fd, encoded) != len(encoded):
            raise OSError('Incomplete accounting write')
        os.fsync(fd)

    @staticmethod
    def day():
        return datetime.now().astimezone().date().isoformat()

    @contextmanager
    def reserve(self, units, on_dispatch=None):
        if any(k not in RATES or type(n) is not int or n < 0 for k,n in units.items()):
            raise AccountingError('Invalid local usage reservation; no provider work admitted.')
        with self.locked() as (fd, data):
            row = data['days'].setdefault(self.day(), {'grossMicrousd':0,'reserved':{},'dispatched':{}})
            charge = sum(RATES[k]*n for k,n in units.items())
            if row['grossMicrousd'] + charge > self.limit:
                raise AccountingError('Local daily estimated spending allowance reached. No new provider work was admitted. Review usage and the explicit local allowance; no retry is scheduled.')
            now=time()
            recent=[e for e in data['recent'] if now-e[0]<60]
            additions={'search':units.get('search_pro',0)+units.get('search_enterprise',0), 'details':units.get('details',0),'elements':units.get('matrix_element',0)}
            for kind, maximum in (('search',10),('details',10),('elements',150)):
                if additions[kind]+sum(e[2] for e in recent if e[1]==kind)>maximum:
                    raise AccountingError('Local shared provider minute allowance reached. Wait before a deliberate action; no retry is scheduled.')
            data['recent']=recent+[[now,k,n] for k,n in additions.items() if n]
            row['grossMicrousd']+=charge
            for k,n in units.items(): row['reserved'][k]=row['reserved'].get(k,0)+n
            self.write(fd,data)  # Charge BEFORE I/O; errors/unsent batch reservations stay charged.
            sent = {}
            def measured(operation, count):
                key={'search':'search_enterprise' if units.get('search_enterprise') else 'search_pro', 'details':'details','matrix':'matrix_element'}[operation]
                n=count
                if type(n) is not int or n <= 0 or sent.get(key,0)+n > units.get(key,0):
                    raise AccountingError('Provider dispatch exceeds its reserved usage; no request sent.')
                sent[key] = sent.get(key,0)+n
                row['dispatched'][key]=row['dispatched'].get(key,0)+n
                self.write(fd,data)
                if on_dispatch: on_dispatch(operation, count)
            token=_active.set(measured)
            try: yield charge
            finally: _active.reset(token)

    def snapshot(self):
        with self.locked() as (_,data):
            gross=data['days'].get(self.day(),{}).get('grossMicrousd',0)
            return {'localDay':self.day(),'estimatedDayGrossUsd':gross/1000000,'dailyAllowanceUsd':self.limit/1000000,
                    'estimatedAllowanceRemainingUsd':max(0,self.limit-gross)/1000000,
                    'cloudQuotaRemaining':None,'cloudBillingVerified':False}
