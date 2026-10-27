"""Scoped consecutive-leg preferences; no interpretation of unknown scope."""
import re
from backend.location_policy import FirstTravel

SCOPE=r'between (?:activities|stops|venues|places)'
OP=r'under|less than|at most|no more than|within|around|about|up to|prefer(?: around| about)?'
AMOUNT=r'\d+(?:\.\d+)?\s*(?:minutes?|mins?|miles?)\b'
PATTERNS=[re.compile(r'(?P<scope>'+SCOPE+r')\s+(?P<op>'+OP+r')\s*(?P<amount>'+AMOUNT+r')',re.I),
          re.compile(r'(?P<op>'+OP+r')\s*(?P<amount>'+AMOUNT+r')\s+(?P<scope>'+SCOPE+r')',re.I)]

def between_intent(raw):
    found=[]
    for pattern in PATTERNS:
        for m in pattern.finditer(raw):
            if any(m.start()<b and m.end()>a for a,b,_ in found):continue
            amount=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(\w+)',m['amount'])
            number,unit=amount.groups()
            op=m['op'].lower()
            preferential=op.startswith('prefer') or op in ('around','about') or op=='within' and bool(re.search(r"\bprefer\b[^.;!?]*$",raw[:m.start()],re.I))
            try:p=FirstTravel(value=float(number),unit='miles' if unit.lower().startswith('mile') else 'minutes',
                              mode='flexible' if preferential else 'strict',exclusive=op in ('under','less than'))
            except ValueError:return None,found,'Between-activity preference is outside the supported range.'
            found.append((m.start(),m.end(),p))
    if len({(p.value,p.unit,p.mode,p.exclusive) for _,_,p in found})>1:
        return None,found,'State one between-activity preference, not competing limits.'
    if found:
        # Additional differently scoped/qualified statements must still pass the
        # original travel guard. Only exact supported spans may be masked.
        return found[0][2],found,None
    return None,[],None

def mask(raw,spans):
    for a,b,_ in sorted(spans,reverse=True):raw=raw[:a]+' '*(b-a)+raw[b:]
    return raw
