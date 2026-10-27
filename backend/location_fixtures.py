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
