"""Ground only the routing preference; never interpret activities or venues."""
import re
from backend.models import TransportationMode

PATTERNS = {
 'driving':r'\bdriving\b(?!\s+range)|\bby car\b|\bdrive\s+(?:to|from|between)\b',
 'walking':r'\b(?:on foot|by foot)\b|\bwalk(?:ing)?\s+(?:to|from|between)\b|\bwalking\s+(?:outing|route|mode|travel)\b',
 'cycling':r'\b(?:cycling|by bike|biking)\b',
 'transit':r'\b(?:public transit|by bus|by train)\b',
}

def is_walking_route_phrase(raw,start,end):
 return any(m.start()<=start and end<=m.end() for m in re.finditer(PATTERNS['walking'],raw,re.I))


def resolve_mode(raw, reported, manual=''):
 negated={m[1].lower() for m in re.finditer(r"\b(?:not|no|without|instead of|rather than|don't|do not)\s+(driving|walking)\b",raw,re.I)}
 stated=set()
 for mode,pattern in PATTERNS.items():
  for match in re.finditer(pattern,raw,re.I):
   if not re.search(r"(?:not|no|without|instead of|rather than|don't|do not)\s+$",raw[:match.start()],re.I):stated.add(mode)
 if len(stated)>1:return None,['Choose one travel mode for the whole outing; mixed travel modes are not supported.']
 source=next(iter(stated),None)
 if source in ('cycling','transit'):return None,['Only Driving and Walking travel modes are supported. Adjust the request to use one of them.']
 if manual and source and manual!=source:
  return None,[f'Your request says {source}, but Travel mode is {manual.title()}. Make the request and preference match, then plan again.']
 if (manual or source or (reported.value if reported else 'driving')) in negated:return None,['Choose one supported travel mode that matches your request.']
 if manual:return TransportationMode(manual),[]
 if source:return TransportationMode(source),[]
 if reported:
  word=reported.value
  evidence={'walking':r'\bwalk(?:ing)?\b|on foot','driving':r'\bdriv(?:e|ing)\b|by car','cycling':r'\bcycl(?:e|ing)\b|\bbik(?:e|ing)\b','transit':r'\btransit\b|\bbus\b|\btrain\b'}[word]
  if not re.search(evidence,raw,re.I):return None,['A travel mode could not be verified in your words. Choose Driving or Walking in preferences.']
  if word not in ('driving','walking'):return None,['Only Driving and Walking travel modes are supported. Adjust the request to use one of them.']
  return reported,[]
 return TransportationMode.driving,[]
