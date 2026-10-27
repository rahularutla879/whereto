"""Deterministic location/first-leg intent. No provider calls or invented points."""
from decimal import Decimal
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FirstTravel(ContractModel):
    value: float = Field(ge=0, le=1440, strict=True, allow_inf_nan=False)
    unit: Literal['minutes','miles'] = 'minutes'
    mode: Literal['strict','flexible'] = 'strict'
    exclusive: bool = Field(default=False,strict=True)
    originText: str | None = Field(default=None,max_length=200,repr=False)

    @model_validator(mode='after')
    def valid_distance(self):
        if self.unit=='miles' and self.value>200:
            raise ValueError('First-stop miles must be from zero to 200.')
        return self


class Geography(ContractModel):
    strictDestination: bool = Field(default=False,strict=True)
    excludedRegions: list[Literal['VA','MD','DC']] = Field(default_factory=list,max_length=3)


AMOUNT=r'(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>minutes?|mins?|miles?)\b'
OP=r'(?P<op>under|less than|at most|no more than|within|around|about|prefer(?: somewhere)?(?: around| about)?)'
PATTERNS=[
    re.compile(OP+r'\s*'+AMOUNT+r'\s*(?:away\s*)?(?:of|from)\s+(?P<origin>[^.;!?]+)',re.I),
    re.compile(r'first (?:stop|destination|activity)\s+(?:to be\s+)?'+OP+r'\s*'+AMOUNT+r'(?:\s+away)?',re.I),
    re.compile(r'(?P<op>prefer(?: somewhere)?(?: around| about)?)\s*'+AMOUNT+r'\s+away',re.I),
]


def first_intent(raw):
    matches=[]
    for pattern in PATTERNS:
        for m in pattern.finditer(raw):
            if any(m.start()<end and m.end()>start for start,end,_ in matches):continue
            origin=m.groupdict().get('origin')
            # Avoid swallowing later activity/travel instructions into a place.
            end=m.end()
            if origin:
                segment=re.split(r'\s+(?:and(?: then| keep| no more| under| at most)?|followed by|for \d+|on (?:Saturday|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday)|keep driving)\b',origin,flags=re.I)[0]
                end=m.start('origin')+len(segment)
                origin=segment.strip(' ,')
            op=m['op'].lower()
            matches.append((m.start(),end,{'value':float(m['value']),'unit':'miles' if m['unit'].lower().startswith('mile') else 'minutes',
                            'mode':'flexible' if any(w in op for w in ('prefer','around','about')) or op=='within' and re.search(r"(?:i['’]d|i would|we would|we['’]d)?\s*prefer\b[^.;!?]*$",raw[:m.start()],re.I) else 'strict',
                            'exclusive':op in ('under','less than'), 'originText':origin}))
    if len({(v['unit'],v['value'],v['mode']) for _,_,v in matches})>1:
        return None,matches,'State one first-stop preference in minutes or miles, not competing limits.'
    if not matches:return None,[],None
    try:
        preference=FirstTravel(**matches[0][2])
        if any(v['exclusive'] for _,_,v in matches):preference=preference.model_copy(update={'exclusive':True})
        return preference,matches,None
    except ValueError:return None,matches,'First-stop preference is outside the supported range.'


def geographic_intent(raw):
    strict=bool(re.search(r'\b(?:only (?:within|in)|strictly within|stay within)\s+(?!\d)',raw,re.I))
    regions=[code for name,code in [('Virginia','VA'),('Maryland','MD'),('District of Columbia','DC')]
             if re.search(r'\b(?:no|exclude|excluding|not in)\s+'+name+r'\b',raw,re.I)]
    return Geography(strictDestination=strict,excludedRegions=regions)


def effective_max(preference):
    return preference.value*(2 if preference.mode=='flexible' else 1) if preference else None


def radius(preference,band,mode):
    if preference:
        return max(250,min(2000000,band*(1609.344 if preference.unit=='miles' else 80 if mode=='walk' else 600)))
    return 2000 if mode=='walk' else 8000


def first_measure(leg,preference):
    if leg.status not in ('ok','same_location'):return None
    return (Decimal(str(leg.distance_meters))/Decimal('1609.344') if preference.unit=='miles' else
            (Decimal(leg.duration_nanoseconds)/Decimal(10**9) if leg.duration_nanoseconds is not None else Decimal(str(leg.duration_seconds)))/60)


def exceeds(leg,preference,maximum=None,*,original=False):
    n=first_measure(leg,preference)
    limit=Decimal(str(preference.value if original else effective_max(preference) if maximum is None else maximum))
    return None if n is None else n>limit or preference.mode=='strict' and preference.exclusive and n==limit
