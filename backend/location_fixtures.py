"""Invented DC-area provider responses; never imported as a live fallback."""
from backend.real_fixtures import matrix_fixture


def place(identity,name,lat=38.9,lon=-77.02,region='DC',types=None):
    city={'DC':'Washington','MD':'Bethesda','VA':'Arlington'}[region]
    return {'id':identity,'displayName':{'text':name},'formattedAddress':f'Synthetic public address, {city}, {region}',
        'location':{'latitude':lat,'longitude':lon},'types':types or ['bowling_alley'],
        'addressComponents':[{'longText':city,'shortText':city,'types':['locality']},{'longText':region,'shortText':region,'types':['administrative_area_level_1']}],
        'attributions':[{'provider':'Invented fixture credit','providerUri':'https://example.com/credit'}]}


def spatial_search_fixture(body,**kwargs):
    query=body['textQuery']
    if query.startswith('public transit'):
        return {'places':[place('Synthetic_reference_'+str(i),'Synthetic public transit reference '+str(i),38.9+i*.005,-77.02,types=['subway_station','transit_station']) for i in range(3)]}
    if kwargs and 'pageSize' in body and body['pageSize']==3:
        return {'places':[place('Synthetic_manual_station','Synthetic confirmed station',types=['train_station','establishment'])]}
    activity='bowling' if 'bowling' in query else 'food' if 'restaurant' in query else 'coffee' if 'cafe' in query else 'museum'
    kind={'bowling':'bowling_alley','food':'restaurant','coffee':'cafe','museum':'museum'}[activity]
    center=body.get('locationBias',{}).get('circle',{}).get('center',{'latitude':38.9,'longitude':-77.02})
    if 'locationRestriction' in body:
        box=body['locationRestriction']['rectangle']
        center={k:(box['low'][k]+box['high'][k])/2 for k in ('latitude','longitude')}
    page=int(body.get('pageToken','0'))
    # Later venues vary with the actual search anchor, demonstrating multiple paths.
    cluster='' if activity=='bowling' else f"_{round(center['latitude']*1000)}_{round(center['longitude']*1000)}"
    places=[place(f'Synthetic_{activity}_{i+page*10}{cluster}',f'Synthetic {activity} venue {i+page*10}',
                  center['latitude']+(i%6)*.003,center['longitude']-(i%3)*.003,
                  region='MD' if i%6==4 else 'VA' if i%6==5 else 'DC',types=[kind,'video_arcade'] if activity=='bowling' and i%6==3 else [kind]) for i in range(body['pageSize'])]
    if activity=='bowling':
        # Unsupported arcade is never a bowling facility just because it appeared.
        places[-1]=place('Synthetic_unsupported_arcade','Synthetic racing arcade',types=['video_arcade'])
    result={'places':places}
    if page<1:result['nextPageToken']='1'
    return result


REGION_LATITUDES=(38.86,38.91,38.96)

def acceptance_search_fixture(body,**kwargs):
    query=body['textQuery']
    box=body.get('locationRestriction',{}).get('rectangle')
    center=(box['low']['latitude']+box['high']['latitude'])/2 if box else None
    region=min(range(3),key=lambda i:abs(REGION_LATITUDES[i]-center)) if center is not None else None
    if query.startswith('public transit'):
        return {'places':[place(f'Synthetic_reference_{region}',f'Synthetic public activity region {region+1}',REGION_LATITUDES[region],-77.02,types=['transit_station'])]}
    if kwargs and body['pageSize']==3:
        return {'places':[place('Synthetic_manual_station','Synthetic confirmed station',38.91,-77.02,types=['train_station'])]}
    bowling='bowling' in query
    kind='bowling' if bowling else 'food'
    records=[]
    for i in range(body['pageSize']):
        group=i%3 if region is None or bowling else region
        identity=f'Synthetic_{kind}_{i}' if bowling else f'Synthetic_food_{group}_{i}'
        records.append(place(identity,f'Synthetic {kind} choice {i+1}',REGION_LATITUDES[group]+i*.00005,-77.02,types=['bowling_alley' if bowling else 'restaurant']))
    return {'places':records}


def acceptance_matrix_fixture(body):
    def group(point):
        if 'location' in point:
            lat=point['location']['latLng']['latitude']
            return min(range(3),key=lambda i:abs(REGION_LATITUDES[i]-lat))
        identity=point['placeId']
        if identity.startswith('Synthetic_reference_'):return int(identity.rsplit('_',1)[1])
        if identity.startswith('Synthetic_bowling_'):return int(identity.rsplit('_',1)[1])%3
        if identity.startswith('Synthetic_food_'):return int(identity.split('_')[2])
        return 1
    data=[]
    for i,a in enumerate(body['origins']):
        for j,b in enumerate(body['destinations']):
            delta=abs(group(a['waypoint'])-group(b['waypoint']))
            first='Synthetic_reference_' in a['waypoint'].get('placeId','') or 'location' in a['waypoint']
            seconds=(600,2100,2700)[delta] if first else (240,1800,3600)[delta]
            data.append({'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS','duration':f'{seconds}s','distanceMeters':(3000,30000,70000)[delta]})
    return data


def neighborhood_fixture(body, **kwargs):
    food='restaurant' in body['textQuery']
    activity='food' if food else 'drinks'
    box=body.get('locationRestriction',{}).get('rectangle')
    london='London' in body['textQuery'] or bool(box and box['low']['latitude']>50)
    latitude,longitude=(51.52,-.08) if london else (40.75,-73.98)
    city='London' if london else 'New York'
    page=1 if body.get('pageToken') else 0
    records=[]
    for i in range(8):
        records.append({'id':f'Synthetic_{activity}_{i+page*8}','displayName':{'text':f'Synthetic {activity} {i+page*8}'},
            'formattedAddress':f'Synthetic address, {city}',
            'location':{'latitude':latitude+i*.0002,'longitude':longitude},
            'addressComponents':[{'longText':city,'types':['locality']}],
            'types':['restaurant' if food else 'bar']})
    # No neighborhood text: exact strict membership is deliberately unavailable.
    records.append({**records[0],'id':f'Synthetic_remote_{activity}','location':{'latitude':0.,'longitude':0.}})
    records.append(records[0])
    return {'places':records[:body['pageSize']], **({'nextPageToken':'synthetic-page-2'} if not page else {})}
