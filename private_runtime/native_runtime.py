"""Reviewed native dependency ports; planner/action algorithms are projected unchanged."""
from contextvars import ContextVar
from threading import RLock
from psycopg.types.json import Jsonb
from private_runtime.registry import current,connection,cache,client
from private_runtime.owned_dispatch import OwnedRemoteSend as RemoteSend
from experiments.service_isolation.runtime_dependencies import *
# The build adds the source-pinned original make_broker function below with only
# its reference-clock constructor changed to trusted wall time (never a test clock).

class DeliveryConnection:
    def __init__(self,config):self.config=config
    def __enter__(self):self.c=connection(self.config);return self
    def __exit__(self,*args):return self.c.__exit__(*args)
    def execute(self,query,args):
        if query!='SELECT synthetic_state.app_accept(%s,%s,%s)' or args[1]!='deliver':raise Denied('delivery_method')
        return self.c.execute('SELECT synthetic_state.service_accept_delivery(%s,%s)',(args[0],args[2]))

class DeliveryStore(NativeStore):
    def __init__(self,config,worker):
        from private_runtime.image_identity import verify
        verify();p=current('dispatcher')
        self.service=GrantService(witness(config),lambda:DeliveryConnection(config))
        self.evidence=cache(config);self.current_epoch=self.service.witness.epoch
        self._epoch_context=ContextVar('delivery_epoch',default=None);self._proof=None;self._dispatch_lock=RLock()
        self._key=unb64(config['hashKey']);self._limits=Limits(**config['limits']);self._pid=os.getpid();self._worker=worker;self._pool=p.pools['database']
        with self._tx():pass
    def _invoke(self,c,action,args):
        return c.execute('SELECT synthetic_state.service_dispatch(%s,%s,%s,%s) AS result',(action,Jsonb(args),'synthetic',self._epoch_context.get())).fetchone()['result']

_witness=None
def witness(config):
    global _witness
    if _witness is None:_witness=ScopedWitness(lambda:connection(config,'witness'),lambda:connection(config,'witness'))
    return _witness
