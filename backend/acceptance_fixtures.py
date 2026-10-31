"""Invented Hyderabad/Manhattan records, for explicit offline tests only."""
import re
from backend.ai import Interpretation
from backend.real_fixtures import matrix_fixture


def search_fixture(body, **kwargs):
    query=body['textQuery'].casefold()
    city='Manhattan' if 'manhattan' in query else 'Hyderabad'
    lat,lon=(40.75,-73.98) if city=='Manhattan' else (17.44,78.37)
    activity='movie' if any(w in query for w in ('cinema','movie')) else 'bowling' if 'bowling' in query else 'food' if 'restaurant' in query else 'drinks' if 'bar' in query else 'custom:pottery class'
    kind={'movie':'movie_theater','bowling':'bowling_alley','food':'restaurant','drinks':'bar'}.get(activity,'establishment')
    def venue(i, origin=False):
        return {'id':f'Test49_{"origin" if origin else activity.replace(":","_").replace(" ","_")}_{i}',
            'displayName':{'text': 'Synthetic My Home Bhooja (offline fixture)' if origin else f'Synthetic {"cinema" if activity=="movie" else activity} {i+1}'},
            'formattedAddress':f'Invented address, {city}', 'location':{'latitude':lat+i*.0001,'longitude':lon},
            'types':['premise','establishment'] if origin else [kind],
            'addressComponents':[{'longText':city,'types':['sublocality_level_1' if city=='Manhattan' else 'locality']},
                {'longText':'New York' if city=='Manhattan' else 'Telangana','types':['locality' if city=='Manhattan' else 'administrative_area_level_1']}],
            'attributions':[]}
    return {'places':[venue(0,True)] if kwargs else [venue(i) for i in range(min(6,body['pageSize']))]}


class FixtureAI:
    def interpret(self,text):
        phrases=re.findall(r'pottery class|movie theater|show movies|movies?|cinema|bowling|restaurant|dinner|drinks',text,re.I)
        return Interpretation(activities=[p.casefold() for p in phrases], location='Manhattan' if 'manhattan' in text.casefold() else 'Hyderabad' if any(w in text.casefold() for w in ('hyderabad','bhooja')) else None,
            date=None,budget_per_person=None,preferences=[])
