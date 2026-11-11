"""Inactive, synthetic-only financial client; no issuer or transport credentials."""
from experiments.shared_state.postgres import LocalPostgres, uuid
from experiments.shared_state.contracts import Reservation, Capability, Denied
from psycopg.types.json import Jsonb

VERSION = '52-financial-authority-local-pg-v3'
RATE_VERSION = 'development_cost.RATES-2026-11-03-v1'


class FinancialPostgres(LocalPostgres):
    @staticmethod
    def _invoke(c, action, args):
        return c.execute('SELECT synthetic_state.financial_protocol(%s,%s) AS result',
                         (action,Jsonb(args))).fetchone()['result']

    def reserve(self, lease, cap, operation):
        if type(cap) is not Capability:
            raise Denied('capability')
        self._call('reserve',**self._lease(lease),capability=self._hash(cap.token,'cap'),
                   operation=uuid(operation))
        return Reservation(operation,lease,cap)

    def usage(self):
        return self._call('usage')
