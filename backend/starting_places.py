"""Explicit starting-place search through the existing OAuth Text Search service.

No Geocoding API enablement/key/quota change. No input or coordinate logging.
"""
from hashlib import sha256
from collections import OrderedDict
from threading import Lock
from time import monotonic

_calendar_lock=Lock()
_calendars=OrderedDict()

def verified_start_calendar(start):
    """Transient calendar evidence from an existing approved origin lookup only."""
    if not start or start.source not in ('manual','suggested') or not start.point.coordinates:return None
    c=start.point.coordinates
    with _calendar_lock:
        evidence=_calendars.get((c.latitude,c.longitude))
        return evidence[1:] if evidence and evidence[0]>monotonic() else None

from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.places import DiscoveryError, DiscoveryCandidate, FIELD_MASK


class StartingPlaceQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=3, max_length=200, repr=False)

    @field_validator('query')
    @classmethod
    def clean(cls, value):
        value = value.strip()
        if len(value) < 3 or any(ord(c) < 32 for c in value):
            raise ValueError('Enter a place or address of 3–200 characters without control characters.')
        return value


def lookup_starting_places(request, session):
    import os
    session.settings.require_live_provider()
    if os.environ.get('WHERETO_START_LOOKUP_DEV') != '1':
        raise DiscoveryError('disabled', 'Starting-place search is disabled for this local session. Use current location or enable the documented lookup switch.')
    # A separate explicit lookup is counted in the SAME process request/search
    # minute budget; up to ten lookups/process, three matches, no pagination.
    from backend.planning_admission import guard_deferred
    guard_deferred()
    outing = session.outing()
    from backend.provider_budget import ProviderLimitError
    from backend.provider_errors import attach_accounting
    try:
        from backend.action_dispatch import search as provider_request
        with outing.reserve('lookup', sha256(request.query.casefold().encode()).hexdigest(),payload=provider_request({'textQuery':request.query,'pageSize':3,'languageCode':'en'},FIELD_MASK)):
            from backend.places_transport import text_search
            data = text_search({'textQuery': request.query, 'pageSize': 3, 'languageCode': 'en'}, field_mask=FIELD_MASK)
    except (ProviderLimitError,DiscoveryError) as error:raise attach_accounting(error,outing)
    places = data.get('places', []) if isinstance(data, dict) else None
    if not isinstance(places, list) or len(places) > 3:
        raise DiscoveryError('invalid_response', 'Starting-place search returned invalid information.')
    matches = []
    for raw in places:
        try:
            p = DiscoveryCandidate(provider_id=raw['id'], display_name=raw['displayName']['text'],
                address=raw['formattedAddress'], coordinates=raw['location'], attributions=raw.get('attributions', []))
            from backend.venue_details import contact_links
            credits = contact_links({'id': p.provider_id, 'attributions': p.attributions}, p.provider_id)['attributions']
            types = set(raw.get('types') or [])
            precision = ('postal_area' if 'postal_code' in types else
                         'city' if types & {'locality', 'administrative_area_level_1', 'administrative_area_level_2'} else
                         'neighborhood' if types & {'neighborhood', 'sublocality', 'sublocality_level_1'} else
                         'address_or_place' if types & {'street_address', 'premise', 'subpremise', 'establishment'} else 'approximate_area')
            from backend.location_context import timezone_for
            city=next((c.get('longText') for c in raw.get('addressComponents',[]) if 'locality' in c.get('types',[])),None)
            zone=timezone_for(city or p.address)
            if city and zone!='UTC':
                with _calendar_lock:
                    _calendars[(p.coordinates.latitude,p.coordinates.longitude)]=(monotonic()+600,city,zone)
                    while len(_calendars)>100:_calendars.popitem(last=False)
            matches.append({'placeId': p.provider_id, 'name': p.display_name, 'address': p.address,
                            'coordinates': p.coordinates.model_dump(), 'precision': precision, 'attributions': credits})
        except (KeyError, ValueError, TypeError):
            raise DiscoveryError('invalid_response', 'A starting-place match could not be verified.') from None
    return {'matches': matches, 'diagnostics': outing.usage()}
