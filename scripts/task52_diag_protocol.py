"""Fixed synthetic diagnostic purpose over unchanged Q4C durable algorithms.

Never imports/enables a real writer or transport. Old Q4D still halts at loss.
Only this new build/purpose can accept an explicitly scoped synthetic review.
"""
from types import SimpleNamespace
from scripts import task52_q4c_protocol as core
from scripts import task52_q4a as base
from scripts import task52_diag_auth as auth
from scripts import task52_diag_identity as identity
from scripts.task52_diag_scoring import assess

VERSION=identity.IDENTITY
CRASHES=core.CRASHES
admission=core.admission
utc=core.utc
live_dispatch=base.live_dispatch
FakeTransport=base.FakeTransport
_context={**vars(core),'VERSION':VERSION,'REGISTRY':{},'auth':auth,'assess':assess,
          'base':SimpleNamespace(plan=identity.plan,private_create=base.private_create,
             fsync_dir=base.fsync_dir,FakeTransport=FakeTransport)}
REGISTRY=_context['REGISTRY']


def methods(source):
    return {name:(core.contextmanager(auth.bind_function(value.__wrapped__,_context))
                  if hasattr(value,'__wrapped__') else auth.bind_function(value,_context))
            for name,value in vars(source).items() if callable(value) and hasattr(value,'__code__')}


_factory=methods(core.SyntheticJournal);_engine=methods(core.Engine)
_init=_factory['__init__'];_check=_engine['check'];_review=_engine['review_binding']


def checked_init(self,trust,*,base_charge=1000000):
    identity.verify(full=True)
    _init(self,trust,base_charge=base_charge)


def checked_directory(self):
    identity.verify();marker=_check(self)
    if marker['identity']!=VERSION:raise auth.Denied('Wrong diagnostic fixture identity')
    return marker


def review_binding(self,data,outcome):
    _review(self,data,outcome)
    d=outcome['data']['assessment']['diagnostic']
    if not d['mechanicallyEligibleAfterReview']:raise auth.Denied('Ineligible diagnostic cannot be reviewed away')
    auth.exact(data['diagnostic'],{'purpose':identity.PURPOSE,'defectHash':d['allowlistedDefect'],
        'systemIncompatible':d['systemIncompatible'],'planningAuthorized':False})


SyntheticJournal=type('DiagnosticSyntheticJournal',(),{**_factory,'__init__':checked_init,'__module__':__name__})
Engine=type('DiagnosticEngine',(),{**_engine,'check':checked_directory,'review_binding':review_binding,'__module__':__name__})
_context.update(SyntheticJournal=SyntheticJournal,Engine=Engine)
