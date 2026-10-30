"""Synthetic Hyderabad coverage for offline tests, never live fallback data."""
def local_places(body,*,distant_only=False):
    food='restaurant' in body['textQuery'];kind='food' if food else 'drinks'
    local=not distant_only and bool(body.get('pageToken') or body['textQuery'].endswith('venues'))
    group='local' if local else 'distant'
    places=[{'id':f'Synthetic_{kind}_{group}_{i}','displayName':{'text':f'Synthetic {"restaurant" if food else "bar"} {group} {i}'},
        'formattedAddress':'Synthetic address, Hyderabad','location':{'latitude':17.36+(i*.0001 if local else .01),'longitude':78.54},
        'types':['restaurant' if food else 'bar'],'addressComponents':[{'longText':'Hyderabad','types':['locality']}],
        'rating':4. if local else 5.,'userRatingCount':100} for i in range(6)]
    return {'places':places,**({'nextPageToken':'synthetic-local-page'} if not body.get('pageToken') else {})}

def local_matrix(body,first_seconds=600):
    rows=[]
    for i,a in enumerate(body['origins']):
        for j,b in enumerate(body['destinations']):
            origin=a['waypoint'].get('placeId','');target=b['waypoint'].get('placeId','')
            seconds=(first_seconds if 'local' in target else 1800) if origin=='Synthetic_Kothapet_origin' or 'location' in a['waypoint'] else 120
            rows.append({'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS','duration':f'{seconds}s','distanceMeters':1000})
    return rows

def local_origin():
    return {'id':'Synthetic_Kothapet_origin','displayName':{'text':'Synthetic Kothapet reference'},
        'formattedAddress':'Synthetic Kothapet reference, Hyderabad','location':{'latitude':17.36,'longitude':78.54},
        'types':['neighborhood'],'addressComponents':[{'longText':'Hyderabad','types':['locality']}]}
