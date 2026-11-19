"""Additive real-profile role/locator RPCs; no policy or credential enrollment."""
from private_runtime.real_finance.profile import ROOT,namespace,verify

def scripts():
    verify()
    from .identity import source_bytes
    def project(path):
        text=namespace(source_bytes(path).decode())
        for a,b in [('synthetic_dispatch_client','real_dispatch_client'),('synthetic_counter_client','real_counter_client'),('synthetic_factory_witness','real_factory_witness'),('synthetic_dispatch_witness','real_dispatch_witness'),('synthetic_counter_witness','real_counter_witness_client'),('synthetic_recovery_client','real_recovery_client'),('synthetic_backend_auth','real_backend_auth')]:text=text.replace(a,b)
        return text
    op=project('experiments/service_isolation/protocol.sql')
    # Price authority remains the protected SQL receipt, never caller JSON.
    op+='''
GRANT EXECUTE ON FUNCTION provider_state.real_accounting(jsonb) TO real_dispatch_client;
'''
    wit=project('experiments/service_isolation/witness.sql')+'\n'+project('experiments/hosted_identity/nonce.sql')
    return dict(operational=op,witness=wit)
