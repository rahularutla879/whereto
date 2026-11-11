"""Trusted reconstruction of validation dependencies, not live planner objects."""
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
from time import monotonic
from pydantic import AwareDatetime,BaseModel,ConfigDict
from experiments.shared_state.contracts import Denied,Kind
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.evidence_models import canonical,plain


class Reference(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    referenceTime: AwareDatetime


class CheckpointIssuer:
    """Trusted server only; anchor/enrollment credentials never belong to a browser.

    Source and root/outing must come from the existing owned action context. This
    fixture does not implement real issuer authentication or a public resume API.
    """
    def __init__(self,connection,root,outing):
        self.__connection,self.__root,self.__outing=connection,root,outing

    def capture(self,store,broker,token,reference_time):
        source=broker._source(token)  # Existing integrity/expiry/revocation proof.
        original_seal=source.digest
        records={'request':source.value,'interpretation_result':source.result,
                 'reference':Reference(referenceTime=reference_time)}
        if source.result.pending:
            records['pending_effective']=source.result.pending;provenance='synthetic_pending_effective'
        else:
            if source.raw is None:raise Denied('raw_source_missing')
            records['raw']=source.raw;provenance='synthetic_fresh'
        action=ProviderAction(purpose='pending' if source.result.pending else 'advanced' if source.result.interpretation.journey else 'ordinary',
            sourceDigest=broker._digest(source.value),interpretationDigest=broker._digest(source.result),requestRevision=source.revision)
        h=store.create(Kind.ACTION,action);lease=store.claim(h,1)
        with self.__connection() as c:
            c.execute('SELECT synthetic_state.enroll_budget(%s,%s,%s)',(store._hash(h.token,'session'),self.__root,self.__outing))
        if broker._source(token).digest!=original_seal:raise Denied('source_changed')
        now=store._call('evidence_clock')['now_ms']
        deadline=int(now+max(0,600-(monotonic()-source.created))*1000)
        store.publish(lease,records,provenance,self.__connection,absolute_deadline=deadline)
        # No bridge_actions registration / request plan / capability / transport.
        return h


def restore_interpretation(store,lease,*,answers=None):
    from backend.interpretation import InterpretationInput,ClarificationAnswers
    from backend.planning_admission import AdmissionRegistry
    records,_=store.recover(lease)
    if not {'request','reference','interpretation_result'}<=set(records):raise Denied('incomplete_checkpoint')
    value=records['request'].model_copy(deep=True)
    if 'pending_effective' in records:
        pending=records['pending_effective']
        if pending.text!=value.text or 'raw' in records:raise Denied('pending_source')
        value=value.model_copy(update={'pending':pending,'answers':answers or ClarificationAnswers()})
    elif answers is not None:raise Denied('new_source_validation_required')
    raw=records.get('raw')
    class Recorded:
        def interpret(self,text):
            if raw is None or text!=value.text:raise Denied('new_interpretation_required')
            return raw.model_copy(deep=True)
    registry=AdmissionRegistry();scope=registry.new_scope()
    outcome=registry.validate(value,scope,lease.revision,Recorded(),now=records['reference'].referenceTime)
    result=outcome.disposition.result
    if answers is None and canonical(plain(result))!=canonical(plain(records["interpretation_result"])):
        raise Denied("checkpoint_revalidation_difference")
    # Newly scoped process-local validation is still NOT provider/financial authority.
    return result
