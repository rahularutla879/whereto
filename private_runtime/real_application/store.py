"""Same real financial store; additional immutable response-receipt completion gate."""
from psycopg.types.json import Jsonb
from private_runtime.real_finance.runtime import Store as FinancialStore

class Store(FinancialStore):
    def _invoke(self,c,a,p):
        return c.execute('SELECT provider_state.native_protocol(%s,%s,%s,%s,%s) AS result',(a,Jsonb(p),'real',self._epoch_context.get(),self._proof)).fetchone()['result']

    def _call(self,verb,**args):
        if verb in ('claim','revise','revoke','native_begin','native_revise','native_revoke'):
            with self.service.witness.serial():return super()._call(verb,**args)
        return super()._call(verb,**args)
