"""Versioned adapter: preserve the original integer source deadline, not float roundtrips."""
from experiments.shared_state.native_sessions import Session as Parent,Graph
class Session(Parent):
    _created_ms=None
    def state(self):
        record=super().state()
        if self._created_ms is None:self._created_ms=record['created']
        record['created']=self._created_ms
        return record
    @classmethod
    def resume(cls,*args,**kwargs):
        session=super().resume(*args,**kwargs)
        doc,_=session.evidence.read(session.lease)
        session._created_ms=Graph(session.evidence.clock()).load(doc['data'])['created']
        return session
