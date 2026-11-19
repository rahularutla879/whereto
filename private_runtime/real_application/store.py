"""Same real financial store; additional immutable response-receipt completion gate."""
from psycopg.types.json import Jsonb
from private_runtime.real_finance.runtime import Store as FinancialStore

class Store(FinancialStore):
    def _invoke(self,c,a,p):
        return c.execute('SELECT provider_state.real_application_protocol(%s,%s,%s,%s,%s) AS result',(a,Jsonb(p),'real',self._epoch_context.get(),self._proof)).fetchone()['result']
