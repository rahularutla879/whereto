"""Private local action evidence; never a public model/planning receipt."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
class ProviderAction(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True)
    purpose: Literal['ordinary','advanced','pending','options','lookup','area','details','refresh']
    sourceDigest: str=Field(pattern='^[0-9a-f]{64}$')
    interpretationDigest: str=Field(pattern='^[0-9a-f]{64}$')
    requestRevision: int=Field(ge=1)
