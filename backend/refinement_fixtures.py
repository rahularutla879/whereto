"""Invented retail/refresh responses, explicit offline tests only."""
import re
from backend.ai import Interpretation
from backend.acceptance_fixtures import search_fixture as cinema_search


def place(identity,name,kind='clothing_store',parent=None,city='Jersey City',lat=40.73):
    return {'id':identity,'displayName':{'text':name},'formattedAddress':'Invented fixture address, '+city,
        'location':{'latitude':lat,'longitude':-74.05},'types':[kind,'store'] if kind not in ('shopping_mall','restaurant','cafe') else [kind],
        'addressComponents':[{'longText':city,'types':['locality']},{'longText':'New Jersey','types':['administrative_area_level_1']}],
        'containingPlaces':[{'id':parent,'name':'places/'+parent}] if parent else [],'attributions':[]}


def search_fixture(body,**kwargs):
    q=body['textQuery'].casefold()
    if any(word in q for word in ('movie','cinema','bhooja')):return cinema_search(body,**kwargs)
    if kwargs:return {'places':[place('Refine49_origin','Synthetic confirmed Jersey City start','premise')]}
    if 'mall' in q or 'shopping center' in q:return {'places':[place('Refine49_mall','Synthetic shopping mall','shopping_mall'),place('Refine49_othermall','Other synthetic shopping mall','shopping_mall')]}
    if any(word in q for word in ('restaurant','cafe','coffee','bars')):
        kind='cafe' if 'cafe' in q or 'coffee' in q else 'restaurant'
        return {'places':[place('Refine49_'+kind+str(i),'Synthetic '+kind+str(i),kind,lat=40.73+i*.0001) for i in range(4)]}
    brand=next((b for b in ('zara','nike','adidas','apple','sephora') if b in q),'zara')
    kind='electronics_store' if brand=='apple' else 'beauty_supply_store' if brand=='sephora' else 'clothing_store'
    return {'places':[place('Refine49_'+brand,brand.title(),kind,'Refine49_mall'),
        place('Refine49_'+brand+'_outlet',brand.title()+' Outlet',kind,'Refine49_othermall'),
        place('Refine49_unrelated','Unrelated clothing store'),place('Refine49_similar',brand.title()+' inspired boutique')]}


class FixtureAI:
    def interpret(self,text):
        phrases=[]
        for part in re.split(r'\band\b|\bthen\b|\bafterward\b',text,flags=re.I):
            if re.search(r'coffee',part,re.I):phrases.append('coffee')
            elif re.search(r'dinner',part,re.I):phrases.append('dinner')
            elif re.search(r'movie|cinema',part,re.I):phrases.append('movie')
            elif re.search(r'mall',part,re.I):phrases.append('shopping malls')
            else:
                match=re.search(r'(?:zara|nike|adidas|apple|sephora)\s+(?:outlets?|stores?)',part,re.I)
                if match:phrases.append(match.group())
        return Interpretation(activities=phrases,location='Hyderabad' if 'hyderabad' in text.casefold() else 'Jersey City',date=None,people=None,budget_per_person=None,preferences=[])


def refreshed(identity):
    from datetime import datetime,timezone
    return {'name':'Synthetic refreshed cinema' if 'movie' in identity else 'Zara' if 'zara' in identity else 'Synthetic refreshed venue',
        'mapsUrl':'https://www.google.com/maps/search/?api=1&query=Invented+fixture&query_place_id='+identity,'phone':'+1 202 555 0149','telephoneUrl':'tel:+12025550149','website':'https://example.com/invented-venue',
        'address':'Invented current provider address','businessStatus':'OPERATIONAL','attributions':[],
        'refreshedAt':datetime.now(timezone.utc).isoformat()}
