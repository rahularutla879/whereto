"""Invented provider responses for Task 46 tests only. Never a real-mode fallback."""
from backend.places import QUERIES


def search_fixture(body, **_kwargs):
    query = body['textQuery'].removeprefix('dinner ').replace('bowling centers', 'bowling alleys').replace('restaurants serving dinner', 'restaurants').replace(' venues in ', ' in ')
    activity = next((a for a, q in QUERIES.items() if query == q or query.startswith(q + ' in ')), 'coffee')
    city = 'Washington' if 'Washington' in query else 'Baltimore'
    state = 'DC' if city == 'Washington' else 'MD'
    result = {'places': [
        {'id': f'Fixture_{activity}_{i}', 'displayName': {'text': f'Fixture {activity} venue {i}'},
         'formattedAddress': f'{i + 1} Synthetic Street, {city}, {state}',
         'location': {'latitude': 39.28 + i * .001, 'longitude': -76.60},
         'rating': 4.0 + (i % 6) / 10, 'userRatingCount': 100 + i * 100,
         'types': [{'food': 'restaurant', 'coffee': 'cafe', 'bowling': 'bowling_alley'}.get(activity, 'establishment')],
         'addressComponents': [{'longText': city, 'shortText': city, 'types': ['locality']},
                               {'longText': state, 'shortText': state, 'types': ['administrative_area_level_1']}],
         'attributions': [{'provider': 'Synthetic credit', 'providerUri': 'https://example.com/credits'}]}
        for i in range(body['pageSize'])]}
    import os
    if os.environ.get('WHERETO_RATINGS_DEV') != '1':
        for place in result['places']:
            place.pop('rating', None); place.pop('userRatingCount', None)
    return result


def matrix_fixture(body):
    return [{'originIndex': i, 'destinationIndex': j, 'status': {}, 'condition': 'ROUTE_EXISTS',
             'duration': f'{120 + i * 10 + j}s', 'distanceMeters': 1000 + i * 100 + j}
            for i in range(len(body['origins'])) for j in range(len(body['destinations']))][::-1]


def details_fixture(place_id):
    return {'placeId': place_id, 'phone': '+1 (202) 555-0100', 'telephoneUrl': 'tel:+12025550100',
            'website': 'https://example.com/venue', 'attributions': [{'provider': 'Synthetic contact credit', 'uri': 'https://example.com'}]}


def paginated_search_fixture(body, **kwargs):
    """Twenty invented relevant venues, ten/page with opaque synthetic cursors."""
    offset = 10 if body.get('pageToken') == 'synthetic-next-page' else 0
    result = search_fixture({**body, 'pageSize': 20}, **kwargs)
    result['places'] = result['places'][offset:offset + body['pageSize']]
    if not offset:
        result['nextPageToken'] = 'synthetic-next-page'
    return result


def bowling_diagnostic_fixture(body, **kwargs):
    """Invented DC coverage: two strict matches, four new supported matches.

    This models provider filtering/coverage, not actual Washington businesses.
    """
    from copy import deepcopy
    bowling = body['textQuery'].startswith('bowling')
    places = search_fixture({**body, 'pageSize':9} if bowling else body, **kwargs)['places']
    for i, p in enumerate(places):
        p.update(rating=4.5, userRatingCount=200,
                 location={'latitude':38.90 + i*.001,'longitude':-77.04})
    if not bowling: return {'places':places}
    if body.get('strictTypeFiltering'):
        return {'places':places[:2]}
    places[2].update(displayName={'text':'Synthetic Bowling and Games Arcade'},types=['video_arcade'],primaryType='video_arcade')
    places[3].update(displayName={'text':'Synthetic Multi Activity Center'},types=['bowling_alley','video_arcade'],primaryType='video_arcade')
    places[6].update(displayName={'text':'Synthetic Racing Arcade'},types=['video_arcade'],primaryType='video_arcade')
    places[7]['addressComponents'] = [{'longText':'Arlington','types':['locality']}, {'longText':'Virginia','shortText':'VA','types':['administrative_area_level_1']}]
    # One duplicate of an unsupported arcade must still be counted as a duplicate.
    places[8] = deepcopy(places[6])
    return {'places':places}
