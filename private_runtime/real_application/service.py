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
    def __init__(self,config,*,auth,client,epoch,owner=None,broker=None,issuer=None,counter=None,delivery=None,router=None,responder=None,count_delivery=None):
        self.c=deepcopy(config);self.role=config['service']
        checked=deepcopy(config)
        if self.role=='dispatcher':
            callers=checked['allow'].pop('/count-provider',None)
            if not callers or any(checked['trust'].get(p,{}).get('role')!='counter' or p not in checked['enrollment'] for p in callers):raise Denied('count_transport_callers')
        parent.enrollment(checked)
        self.auth,self.client,self.epoch=auth,client,epoch
        self.owner,self.broker,self.issuer=owner,broker,issuer
        self.counter,self.delivery,self.router,self.responder=counter,delivery,router,responder
        self.count_delivery=count_delivery
        if (self.role=='dispatcher')!=(count_delivery is not None):raise Denied('count_transport_role')
        if auth.c['service']!=self.role or auth.c['build']!=config['build'] or epoch()!=config['epoch']:raise Denied('real_role_identity')
        required={'factory':(owner,broker,issuer),'counter':(counter,),'dispatcher':(delivery,router,responder),'backend':(client,),'recovery':()}
        if self.role not in required or any(x is None for x in required[self.role]):raise Denied('real_role_dependencies')
        if self.role!='counter' and counter is not None or self.role!='dispatcher' and any(x is not None for x in (delivery,router,responder)) or self.role!='factory' and any(x is not None for x in (owner,broker,issuer)):raise Denied('real_role_separation')
    def probe(self):
        if self.role!='factory':raise Denied('real_probe_role')
        broker=self.broker()
        if broker.store.evidence.client.ping() is not True:raise Denied('real_probe_evidence')
        for role in ('counter','dispatcher','recovery'):
            if self.client.request(role,'/ui-probe',{})!={'available':True}:raise Denied('real_probe_dependency')
    def handle(self,config,path,value):
        if path=='/ui-probe':
            if value!={} or self.epoch()!=config['epoch']:raise Denied('real_probe')
            return {'available':True}
        if self.role=='factory':
            if path=='/dispatch-check':return self.owner.check(value)
            if path=='/ordinary':
                with self.owner.action():return Factory(config,broker=self.broker,issuer=self.issuer,auth=self.auth,readiness=self.probe).ordinary(value)
        if self.role=='counter' and path=='/count':return rpc.count(value,self.counter)
        if self.role=='dispatcher' and path=='/count-provider':return self.count_delivery(value)
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
