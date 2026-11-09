"""Offline geographic evidence checks; no geocoder, routing or inferred radius."""
from math import asin, cos, radians, sin, sqrt
import re
import unicodedata

from backend.venue_models import Coordinates


def normalized(value: str) -> str:
    value = ''.join(c for c in unicodedata.normalize('NFKD', value).casefold()
                    if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+', value))


def distance_m(a: Coordinates, b: Coordinates) -> float:
    lat1, lat2 = radians(a.latitude), radians(b.latitude)
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin(radians(b.longitude-a.longitude)/2)**2
    return 6371008.8 * 2 * asin(sqrt(min(1.0, h)))


def geographic_reason(area, coordinates: Coordinates, components: list[dict]) -> str | None:
    # Counties cannot establish a requested city/neighborhood with the same name.
    local_types = {'locality', 'postal_town', 'neighborhood', 'sublocality',
                   *(f'sublocality_level_{i}' for i in range(1, 6))}
    region_types = {'country', 'administrative_area_level_1'}
    def names(types):
        return {normalized(c[k]).replace(' ', '') for c in components if types.intersection(c.get('types', []))
                for k in ('longText', 'shortText') if isinstance(c.get(k), str)}
    excluded = set(getattr(area, 'excluded_regions', []))
    regions = names({'administrative_area_level_1'})
    aliases = {'VA':{'va','virginia'}, 'MD':{'md','maryland'}, 'DC':{'dc','districtofcolumbia'}}
    if excluded and not regions:
        return 'excluded_region_unverified'
    if any(regions & aliases[code] for code in excluded):
        return 'excluded_region'
    if area.name and getattr(area, 'enforce_name', True):
        supported=names(local_types | region_types)
        # Reviewed Hyderabad neighborhood spelling only. Parent components alone
        # never establish it; names/businesses/addresses are not alias evidence.
        if ('hyderabad' in names({'locality', 'postal_town'})
                and 'telangana' in regions):
            neighborhood_names = names(local_types - {'locality', 'postal_town'})
            if neighborhood_names & {'hiteccity', 'hitechcity'}:
                supported.update({'hiteccity', 'hitechcity'})
        words=[normalized(part).split() for part in area.name.split(',')]
        # A qualified neighborhood may span multiple address components.
        # Every token must be supported; no city/borough alias is fabricated.
        def supported_part(tokens):
            text=''.join(tokens)
            if text in supported:return True
            return bool(tokens) and any(''.join(tokens[:i]) in supported and supported_part(tokens[i:]) for i in range(1,len(tokens)))
        if not all(supported_part(tokens) for tokens in words):
            return 'area_unverified'
    if getattr(area,'boundary_radius_m',None) is not None and distance_m(area.boundary_coordinates,coordinates)>area.boundary_radius_m:
        return 'outside_radius'
    if area.radius_m is not None and distance_m(area.coordinates, coordinates) > area.radius_m:
        return 'outside_radius'
    return None


def geographic_detail(area, coordinates, components):
    """Fixed aggregate categories only; no area names or coordinates returned."""
    reason = geographic_reason(area, coordinates, components)
    if reason in ('outside_radius','excluded_region','excluded_region_unverified'):
        return reason
    if reason == 'area_unverified':
        local = {'locality', 'postal_town', 'neighborhood', 'sublocality',
                 *(f'sublocality_level_{i}' for i in range(1, 6))}
        types = {t for c in components for t in c.get('types', [])}
        return 'different_named_area_or_region' if types & local else 'missing_local_area_evidence'
    return 'geography_unverified'
