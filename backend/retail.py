"""Source-derived retail constraints; formats are soft unless explicitly required."""
import re
from dataclasses import dataclass

RETAIL_TYPES={'store','clothing_store','shoe_store','electronics_store','book_store','department_store','sporting_goods_store','jewelry_store','home_goods_store','beauty_supply_store'}
MALL_TYPES={'shopping_mall','shopping_center','shopping_centre'}
FORMATS=r'outlets?|factory (?:stores?|outlets?)|flagships?|(?:retail )?(?:stores?|shops?)'
CATEGORIES=r'clothes|clothing|shoes?|electronics|books?|bookstores?|department|specialty|shopping|retail'

@dataclass(frozen=True)
class RetailIntent:
    query: str
    brands: tuple[str,...]=()
    destination: bool=False
    outlet: bool=False
    hard_format: bool=False
    same_mall: bool=False
    parent: str|None=None


def intent(activity):
    text=str(activity).removeprefix('custom:').casefold().strip()
    if text=='shopping':return RetailIntent('shopping malls',destination=True)
    if not re.search(r'\b(?:'+FORMATS+r'|malls?|shopping cent(?:er|re)s?|retail plazas?|shopping complexes?|'+CATEGORIES+r')\b',text):return None
    text=re.sub(r'^(?:find|visit|go shopping at|shop for|shopping at)\s+(?:a |an |the )?','',text)
    main=re.split(r'\binside\b|\bin (?:the )?same\b',text,maxsplit=1)[0]
    destination=bool(re.search(r'\b(?:malls?|shopping cent(?:er|re)s?|retail plazas?|outlet cent(?:er|re)s?)\b',main))
    brands=()
    if destination and re.search(r'\bwith\b',text):
        part=re.split(r'\bwith\b',text,maxsplit=1)[1]
        brands=tuple(p.strip() for p in re.split(r'\band\b|,',part) if p.strip())
    elif not destination:
        part=re.split(r'\b(?:inside|near|around|in|close to)\b',text,maxsplit=1)[0]
        part=re.sub(r'\bonly\b|\bno regular stores?\b|\bmust be (?:an? )?|\brequired\b','',part)
        part=re.sub(r'\b(?:'+FORMATS+r')\b','',part).strip()
        if part and not re.fullmatch(r'(?:'+CATEGORIES+r')(?:\s+(?:'+CATEGORIES+r'))*',part):
            brands=tuple(p.strip() for p in re.split(r'\band\b|,',part) if p.strip())
    outlet=bool(re.search(r'\boutlets?\b|\bfactory\b',text))
    parent=re.search(r'\binside\s+(?:the )?(.+)',text)
    destination=destination or (bool(re.search(r'\bsame mall\b',text)) and len(brands)>1)
    return RetailIntent(text,brands,destination,outlet,bool(re.search(r'\bonly\b|\bno regular stores?\b|\bmust be (?:an? )?|\brequired\b',text)),bool(re.search(r'\bsame mall\b',text)),parent.group(1) if parent else None)


def query(activity,variant='initial'):
    value=intent(activity)
    if not value:return None
    if value.destination:return ('outlet shopping centers' if value.outlet else 'shopping malls') if value.brands else value.query
    if value.brands:
        # Search identity first even when Google omits the preferred format.
        # This accepts regular stores immediately rather than rejecting/refetching.
        return ' and '.join(value.brands)+(' outlets stores' if value.outlet and variant=='initial' else ' stores')
    return value.query


def matches_brand(name,brand):
    clean=lambda s:re.sub(r'[^a-z0-9]+',' ',s.casefold()).strip()
    name,brand=clean(name),clean(brand)
    if name==brand:return True
    # Exact provider name identity plus generic verified-format words; a search
    # hit, a substring, or "Zara inspired boutique" cannot prove brand identity.
    if not name.startswith(brand+' '):return False
    suffix=name[len(brand):].strip()
    return bool(re.fullmatch(r'(?:(?:outlet|factory|store|shop|flagship|clothing|retail)\s*)+',suffix))


def verdict(venue,value):
    types=set(venue.providerTypes or [])|({venue.primaryType} if venue.primaryType else set())
    if value.destination:
        return bool(types&MALL_TYPES), 'retail_destination_type'
    if value.brands and (len(value.brands)!=1 or not matches_brand(venue.name,value.brands[0])):
        return False,'brand_identity_unverified'
    if not types&RETAIL_TYPES:return False,'retail_type_unverified'
    if not value.brands:
        required=next((expected for pattern,expected in ((r'\b(?:clothes|clothing)\b',{'clothing_store'}),(r'\bshoes?\b',{'shoe_store'}),(r'\belectronics\b',{'electronics_store'}),(r'\b(?:books?|bookstores?)\b',{'book_store'}),(r'\bdepartment\b',{'department_store'})) if re.search(pattern,value.query)),None)
        if required and not types&required:return False,'retail_category_unverified'
    if value.hard_format and value.outlet and not re.search(r'\boutlet\b|\bfactory\b',venue.name,re.I):
        return False,'mandatory_outlet_unverified'
    parents=venue.containingPlaces or []
    if value.parent and not any(p.displayName and p.displayName.casefold()==value.parent.casefold() for p in parents):
        return False,'tenant_relationship_unverified'
    if value.same_mall and not any(p.isMall for p in parents):return False,'tenant_relationship_unverified'
    return True,'brand_and_retail_type' if value.brands else 'retail_type'
