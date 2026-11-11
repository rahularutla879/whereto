"""Explicit private DTO evidence, never executable session or admission objects."""
from datetime import datetime,date
from enum import Enum
import json
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from experiments.shared_state.contracts import Denied, Kind, types

VERSION='52-encrypted-shared-evidence-local-v1'
MAX_BYTES=65536


class Membership(BaseModel):
    """Details/refresh membership; no access token or provider response content."""
    model_config=ConfigDict(extra='forbid',frozen=True)
    purpose: str=Field(pattern='^(details|refresh|selection)$')
    documentDigest: str=Field(pattern='^[0-9a-f]{64}$')
    selectedId: str=Field(min_length=1,max_length=200)
    allowedIds: list[str]=Field(min_length=1,max_length=100)
    consumedIds: list[str]=Field(default_factory=list,max_length=100)


def model_types():
    from backend.ai import Interpretation
    from backend.interpretation import InterpretationInput, InterpretationContext,InterpretationResult
    from experiments.shared_state.evidence_recovery import Reference
    from backend.starting_places import StartingPlaceQuery
    from backend.starting_areas import StartingAreaQuery
    from backend.routes import RouteResult
    return {**{k.value:v for k,v in types().items()},'request':InterpretationInput,
            'raw':Interpretation,'context':InterpretationContext,'starting_place':StartingPlaceQuery,
            'starting_area':StartingAreaQuery,'route':RouteResult,'membership':Membership,'reference':Reference,'interpretation_result':InterpretationResult}


def plain(v):
    # Include explicitly excluded private DTO fields in the encrypted integrity domain.
    if isinstance(v,BaseModel):return {k:plain(getattr(v,k)) for k in type(v).model_fields}
    if isinstance(v,(date,UUID)):return v.isoformat() if isinstance(v,date) else str(v)
    if isinstance(v,Enum):return v.value
    if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [plain(x) for x in v]
    return v


def canonical(v):
    try:return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (ValueError,TypeError):raise Denied('evidence_encoding') from None


def strict_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError()
            out[k]=v
        return out
    try:
        v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if canonical(v)!=raw:raise ValueError()
        return v
    except (ValueError,TypeError,UnicodeError):raise Denied('evidence_encoding') from None


def data_view(value):
    """Data-only display projection. Never copies published save bearer credentials."""
    if type(value) in (model_types()['options'],model_types()['advanced_results']):
        return value.model_copy(update={'saveReceipt':None,'saveAccessToken':None},deep=True)
    return value


def no_credentials(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.casefold() in {'password','secret','authorization','accesstoken','saveaccesstoken','savereceipt','api_key','apikey'} and v is not None:
                raise Denied('credential_storage_forbidden')
            no_credentials(v)
    elif isinstance(value,list):
        for v in value:no_credentials(v)


def pack(records,provenance):
    """Only an explicit synthetic admission exists. Real Google data remains blocked."""
    if provenance not in ('synthetic_fresh','synthetic_pending_effective','synthetic_refresh'):
        raise Denied('unreviewed_data_policy')
    if not isinstance(records,dict) or not 1<=len(records)<=16:raise Denied('evidence_records')
    if provenance!='synthetic_fresh' and 'raw' in records:raise Denied('raw_provenance')
    if provenance=='synthetic_fresh' and 'pending_effective' in records:raise Denied('raw_provenance')
    out={}
    for k,v in records.items():
        if k not in model_types() or type(v) is not model_types()[k]:raise Denied('evidence_type')
        if k=='request' and v.pending is not None and provenance=='synthetic_fresh':raise Denied('raw_provenance')
        if k=='advanced_handoff' and v.executionStatus!='advanced_unavailable':raise Denied('handoff_type')
        out[k]=plain(v)
        no_credentials(out[k])
    raw=canonical({'version':VERSION,'provenance':provenance,'records':out})
    if len(raw)>MAX_BYTES:raise Denied('evidence_capacity')
    return raw


def unpack(raw):
    v=strict_json(raw)
    if not isinstance(v,dict) or set(v)!={'version','provenance','records'} or v['version']!=VERSION:
        raise Denied('evidence_version')
    try:
        records={k:model_types()[k].model_validate_json(canonical(x)) for k,x in v['records'].items()}
        if pack(records,v['provenance'])!=raw:raise ValueError()
        return records
    except (ValueError,TypeError,KeyError,AttributeError):raise Denied('evidence_type') from None
