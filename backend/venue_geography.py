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
    if area.name:
        parts = [normalized(part).replace(' ', '') for part in area.name.split(',')]
        if (not parts[0] or parts[0] not in names(local_types | region_types)
                or not all(part and part in names(local_types | region_types) for part in parts[1:])):
            return 'area_unverified'
    if area.radius_m is not None and distance_m(area.coordinates, coordinates) > area.radius_m:
        return 'outside_radius'
    return None


def geographic_detail(area, coordinates, components):
    """Fixed aggregate categories only; no area names or coordinates returned."""
    reason = geographic_reason(area, coordinates, components)
    if reason == 'outside_radius':
        return reason
    if reason == 'area_unverified':
        local = {'locality', 'postal_town', 'neighborhood', 'sublocality',
                 *(f'sublocality_level_{i}' for i in range(1, 6))}
        types = {t for c in components for t in c.get('types', [])}
        return 'different_named_area_or_region' if types & local else 'missing_local_area_evidence'
    return 'geography_unverified'
