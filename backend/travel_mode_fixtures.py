"""Invented directional route responses, offline acceptance only."""
def matrix(body):
 rows=[]
 for i,a in enumerate(body['origins']):
  for j,b in enumerate(body['destinations']):
   source=a['waypoint'].get('placeId','fixture-origin')
   target=b['waypoint'].get('placeId','fixture-origin')
   first='origin' in source
   walk=body['travelMode']=='WALK'
   seconds=(720 if walk else 240) if first else (900 if walk else 300)
   directional=sum(ord(c)*(n+1) for n,c in enumerate(source+'>'+target))%11
   rows.append({'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS',
    'duration':str(seconds+directional)+'s','distanceMeters':(1600 if walk else 1200) if first else (2400 if walk else 1800)})
 return rows[::-1]
