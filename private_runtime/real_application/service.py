"""Existing authenticated HTTP boundaries with real-profile role dependencies.

No production enrollment constructor is provided here. Closed hosted startup must
supply measured role-owned ports and approved provider enrollments before use.
"""
from pathlib import Path
import ast
from copy import deepcopy
from experiments.shared_state.contracts import Denied
from experiments.service_isolation.auth import unb64
from experiments.shared_state.evidence_models import canonical
from experiments.hosted_identity.auth import USER
from private_runtime import private_service as parent,owned_dispatch
from . import rpc
from .factory import Factory

class Role:
    def __init__(self,config,*,auth,client,epoch,owner=None,broker=None,issuer=None,counter=None,delivery=None,router=None,responder=None):
        self.c=deepcopy(config);self.role=config['service'];parent.enrollment(config)
        self.auth,self.client,self.epoch=auth,client,epoch
        self.owner,self.broker,self.issuer=owner,broker,issuer
        self.counter,self.delivery,self.router,self.responder=counter,delivery,router,responder
        if auth.c['service']!=self.role or auth.c['build']!=config['build'] or epoch()!=config['epoch']:raise Denied('real_role_identity')
        required={'factory':(owner,broker,issuer),'counter':(counter,),'dispatcher':(delivery,router,responder),'backend':(client,),'recovery':()}
        if self.role not in required or any(x is None for x in required[self.role]):raise Denied('real_role_dependencies')
        if self.role!='counter' and counter is not None or self.role!='dispatcher' and any(x is not None for x in (delivery,router,responder)) or self.role!='factory' and any(x is not None for x in (owner,broker,issuer)):raise Denied('real_role_separation')
    def handle(self,config,path,value):
        if path=='/ui-probe':
            if value!={} or self.epoch()!=config['epoch']:raise Denied('real_probe')
            return {'available':True}
        if self.role=='factory':
            if path=='/dispatch-check':return self.owner.check(value)
            if path=='/ordinary':
                with self.owner.action():return Factory(config,broker=self.broker,issuer=self.issuer,auth=self.auth).ordinary(value)
        if self.role=='counter' and path=='/count':return rpc.count(value,self.counter)
        if self.role=='dispatcher' and path=='/send':return rpc.dispatch(value,store_factory=self.delivery,router=self.router,caller=owned_dispatch.CALLER.get(),responder=self.responder)
        raise Denied('real_role_method')

def boundary(role):
    """Compile only unchanged HTTP handlers with explicit trusted dependencies."""
    from .identity import verify_application,source_bytes
    verify_application()
    tree=ast.parse(source_bytes('private_runtime/private_service.py'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('privileged_server','backend_app')]
    ns={**vars(parent),'current':lambda:role,'handle':role.handle,'authentication':lambda config,auth_factory=None:role.auth}
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),str(__file__)+':reviewed-http','exec'),ns)
    return ns

def privileged_server(role,*,tls=None):return boundary(role)['privileged_server'](role.c,tls=tls)
def backend_app(role):return boundary(role)['backend_app'](role.c)
