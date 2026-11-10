"""Fixed V5.1 adapter over the verified Q4C OFFLINE synthetic protocol.

No exec/source rewriting, monkeypatches, import hooks, live transport or real
writer. Bind identical code objects to isolated fixed dependencies/registry.
Q4C's internal frozen-build checks still run, plus the new profile checks.
"""
from types import SimpleNamespace
from scripts import task52_q4c_protocol as core
from scripts import task52_q4a as original_base
from scripts import task52_v51_eval_auth as auth
from scripts import task52_v51_eval_identity as identity
from scripts.task52_v51_eval_scoring import assess

VERSION='52b-v51-signed-offline-evaluator-v1'
CRASHES=core.CRASHES
admission=core.admission
utc=core.utc
live_dispatch=original_base.live_dispatch  # Unconditional refusal.
FakeTransport=original_base.FakeTransport

# Exact same verified durable/state/accounting/locking algorithms. No caller
# can select another dependency profile or a database initialization path.
identity.verify_core()
_context={**vars(core),'VERSION':VERSION,'REGISTRY':{},'auth':auth,'assess':assess,
          'base':SimpleNamespace(plan=identity.plan,private_create=original_base.private_create,
             fsync_dir=original_base.fsync_dir,FakeTransport=FakeTransport)}
REGISTRY=_context['REGISTRY']


def methods(source):
    result={}
    for name,value in vars(source).items():
        if not callable(value) or not hasattr(value,'__code__'):continue
        # Rebuild contextmanager's standard-library wrapper around the bound
        # generator, rather than rebinding contextlib's own globals.
        result[name]=(core.contextmanager(auth.bind_function(value.__wrapped__,_context))
                      if hasattr(value,'__wrapped__') else auth.bind_function(value,_context))
    return result


_factory=methods(core.SyntheticJournal)
_engine=methods(core.Engine)
_original_init=_factory['__init__']
_original_check=_engine['check']


def checked_init(self,trust,*,base_charge=1000000):
    identity.verify_build(full=True)
    _original_init(self,trust,base_charge=base_charge)


def checked_directory(self):
    identity.verify_build()
    marker=_original_check(self)
    if marker['identity']!=VERSION:raise auth.Denied('Wrong synthetic profile')
    return marker


SyntheticJournal=type('V51SyntheticJournal',(),{**_factory,'__init__':checked_init,'__module__':__name__})
Engine=type('V51Engine',(),{**_engine,'check':checked_directory,'__module__':__name__})
_context.update(SyntheticJournal=SyntheticJournal,Engine=Engine)
