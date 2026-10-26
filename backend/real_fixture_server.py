"""Explicit offline test server; never imported by the production application.

Run: backend/.venv/bin/python -m backend.real_fixture_server --port 8016
All provider/AI boundaries are replaced; an actual requests send raises.
"""
import argparse
import os
import re
from time import sleep
from unittest.mock import patch

from backend.ai import Interpretation
from backend.real_fixtures import bowling_diagnostic_fixture, paginated_search_fixture, search_fixture, matrix_fixture, details_fixture
from backend.places import DiscoveryError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8016)
    args = parser.parse_args()
    os.environ.update(VENUE_DATA_MODE='real', WHERETO_REAL_DEV='1', WHERETO_ENV='development',
                      WHERETO_CONTACT_DETAILS_DEV='1', WHERETO_START_LOOKUP_DEV='1', WHERETO_RATINGS_DEV='1', NODE_ENV='development')
    counts = {'searches': 0, 'elements': 0, 'details': 0, 'ai': 0}
    scenario = {'name': 'normal'}

    def search(body, **kwargs):
        counts['searches'] += 1
        if scenario['name'] in ('quota', 'authentication'):
            raise DiscoveryError(scenario['name'], 'Google quota or authentication is unavailable. Stop and review settings.')
        if kwargs:
            if scenario['name'] == 'lookup_failure': raise DiscoveryError('quota', 'Starting-place quota reached. Stop and review usage.')
            result = search_fixture({'textQuery': 'cafes in Baltimore', 'pageSize': 3})
            for i, place in enumerate(result['places']):
                place['types'] = [['street_address'], ['postal_code'], ['neighborhood']][i]
                place['displayName']['text'] = ['Synthetic address', 'Synthetic ZIP area', 'Synthetic neighborhood'][i]
            if scenario['name'] == 'single_start': result['places'] = result['places'][:1]
            if scenario['name'] == 'lookup_empty': result['places'] = []
            return result
        result = (bowling_diagnostic_fixture(body) if scenario["name"] == "bowling_diagnostic" else
                  paginated_search_fixture(body) if scenario["name"] == "expanded" else search_fixture(body))
        if scenario['name'] == 'long_names':
            for place in result['places']:
                place['displayName']['text'] += ' A Very Long Synthetic Venue Name For Responsive Headline Verification'
        if scenario['name'] == 'sparse' and body['textQuery'].startswith('bowling alleys'): result['places'] = result['places'][:2]
        if scenario['name'] == 'empty': result['places'] = []
        if scenario['name'] == 'partial': result['places'] = result['places'][:1]
        return result

    def matrix(body):
        if scenario['name'] == 'slow_routes': sleep(3)
        counts['elements'] += len(body['origins']) * len(body['destinations'])
        result = matrix_fixture(body)
        if scenario['name'] == 'bowling_diagnostic':
            for element in result:
                origin = body['origins'][element['originIndex']]['waypoint'].get('placeId','')
                if origin == 'Fixture_bowling_5': element['duration'] = '900s'
        return [] if scenario['name'] == 'missing_routes' else result

    def details(place_id):
        counts['details'] += 1
        if scenario['name'] == 'details_failure': raise DiscoveryError('quota', 'Contact lookup quota reached.')
        if scenario['name'] == 'missing_contacts': return {'placeId': place_id, 'phone': None, 'telephoneUrl': None, 'website': None, 'attributions': []}
        return details_fixture(place_id)

    class FixtureAI:
        def interpret(self, text):
            counts['ai'] += 1
            pattern = r'\b(bowling|dinner|coffee|museum|movie|concert)\b'
            activities = [m[0] for m in re.finditer(pattern, text, re.I)]
            group = re.search(r'\b(\d+) people\b', text)
            leg = re.search(r'between venues under (\d+) minutes', text, re.I)
            return Interpretation(activities=activities or ['coffee'], people=int(group[1]) if group else None,
                budget_per_person=None, date=None, location='Washington, DC' if 'Washington, DC' in text else 'Baltimore' if 'Baltimore' in text else None,
                preferences=[], transport='walking' if 'walking' in text else 'driving' if 'driving' in text else None,
                travel_leg_minutes=int(leg[1]) if leg else None)

    with patch('requests.sessions.Session.send', side_effect=AssertionError('Offline fixture server refused network')), \
         patch('backend.places_transport.text_search', side_effect=search), \
         patch('backend.routes_transport.compute_matrix', side_effect=matrix), \
         patch('backend.venue_details.fetch_details', side_effect=details), \
         patch('backend.interpretation.create_provider', return_value=FixtureAI()):
        from backend.main import app
        @app.get('/__test/counts')
        def stats(): return counts
        @app.post('/__test/scenario')
        def set_scenario(value: dict):
            scenario['name'] = value.get('name', 'normal')
            os.environ['WHERETO_START_LOOKUP_DEV'] = '0' if scenario['name'] == 'lookup_disabled' else '1'
            # Tests reset only process-local admission, never real accounting.
            from backend import main as api
            from backend.provider_budget import ProviderBudget, ProviderSettings
            api.provider_budget = ProviderBudget(ProviderSettings.from_env().model_copy(update={'candidates_per_activity':10})) if scenario['name']=='minute_pause' else ProviderBudget()
            if scenario['name']=='minute_pause':
                from time import monotonic
                api.provider_budget._matrix_window.append((monotonic(),150))
            return {'ok': True}
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning', access_log=False)


if __name__ == '__main__': main()
