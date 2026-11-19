"""Source-selected role construction; no grant installer or fixture selection."""
from datetime import datetime,timezone
from time import time
from dataclasses import fields
from experiments.shared_state.contracts import Denied,Limits
from experiments.service_isolation.auth import unb64
from private_runtime.dispatch_owner import DispatchOwner,Owner,OwnerRouter
from private_runtime.provider_callbacks import DispatcherCallback
from private_runtime.real_finance.runtime import CounterAuthority,CounterWitness,Accounting
from .rpc import ScopedWitness,RemoteSend,RemoteCounter,DeliveryStore
from .count_transport import RelayCounter,RemoteCount,CountDelivery
from .native import Broker,Issuer,Inference
from .store import Store
from .service import Role

def compose(ports,*,provider=None,google=None,clock=None):
    from .identity import verify_application
    verify_application();c=ports.c;role=ports.role
    if not ports._started or c.get('runtimeProfile')!='52-real-native-six-role-v4':raise Denied('real_runtime_profile')
    if role!='dispatcher' and (provider is not None or google is not None):raise Denied('provider_credential_role')
    def db(name='database',**kw):return ports.connection(name,**kw)
    def nonce(*args):
        with db('witness') as connection:connection.execute('SELECT provider_witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
    auth=ports.authentication_factory(c,nonce,ports.epoch);kw={}
    if role in ('factory','dispatcher'):
        key=unb64(c['authorityKey']);limits=Limits(**c['limits'])
        if len(key)!=32 or set(c['limits'])!={f.name for f in fields(Limits)}:raise Denied('authority_scope')
    if role=='factory':
        owner=DispatchOwner(Owner(c['principal'],c['build'],c['epoch'],c['principal']))
        def make():
            witness=ScopedWitness(lambda:db('witness'),lambda:db('witness'));service=RemoteSend(witness,lambda:db('issuer'),ports.client,owner)
            s=Store(connection=lambda **kw:db(**kw),issuer=lambda:db('issuer'),service=service,evidence=ports.evidence,key=key,limits=limits)
            issuer=Issuer(lambda:db('issuer'),c['financialRoot'])
            def refuse(*_):raise Denied('factory_provider_transport_forbidden')
            inference=Inference(s,lambda:db('issuer'),c['financialRoot'],RemoteCounter(ports.client),refuse)
            b=Broker(s,issuer,inference,refuse,now=clock() if clock is not None else datetime.now(timezone.utc));service.check_current=b.check_current;return b
        kw=dict(owner=owner,broker=make,issuer=lambda:db('issuer'))
    if role=='counter':
        authority=CounterAuthority(lambda:db(),CounterWitness(lambda:db('witness'),lambda:db('witness')),c['openaiProject'])
        kw=dict(counter=RelayCounter(RemoteCount(ports.client,c['openaiProject']),authority))
    if role=='dispatcher':
        if provider is None or google is None or set(provider)!={'count','generation'}:raise Denied('provider_enrollment_required')
        def delivery(worker):return DeliveryStore(worker,connection=lambda **kw:db(**kw),witness=ScopedWitness(lambda:db('witness'),lambda:db('witness')),evidence=ports.evidence,key=key,limits=limits)
        owners={v['slot']:Owner(**v) for v in c['dispatchOwners']}
        kw=dict(delivery=delivery,router=OwnerRouter(owners,ports.client),responder=DispatcherCallback(provider['generation'],google,Accounting(),time),count_delivery=CountDelivery(lambda:db(),ScopedWitness(lambda:db('witness'),lambda:db('witness')),provider['count']))
    return Role(c,auth=auth,client=ports.client,epoch=ports.epoch,**kw)
