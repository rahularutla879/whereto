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
    parser.add_argument('--exploration-ledger', help='Offline-only temporary accounting path')
    parser.add_argument('--refinements',action='store_true',help='Offline retail and saved refresh fixtures')
    parser.add_argument('--acceptance', action='store_true', help='Offline Hyderabad cinema/save acceptance scenario')
    parser.add_argument('--advanced', action='store_true', help='Offline Task50E integrated fixtures; SQL remains real when configured')
    parser.add_argument('--journey', action='store_true', help='Offline complex-interpretation fixtures')
    parser.add_argument('--local-ai',action='store_true',help='Use installed local Qwen with otherwise offline advanced provider fixtures')
    args = parser.parse_args()
    if args.local_ai and not args.advanced:parser.error('--local-ai requires --advanced')
    if not args.local_ai:os.environ['WHERETO_AI_WARMUP_DEV']='0'  # Fully offline fixtures never prepare a real model.
    if args.exploration_ledger:
        os.environ.update(WHERETO_EXPLORATION_DEV='1', WHERETO_DEV_COST_LEDGER=args.exploration_ledger)
    os.environ.update(VENUE_DATA_MODE='real', WHERETO_REAL_DEV='1', WHERETO_ENV='development',
                      WHERETO_CONTACT_DETAILS_DEV='1', WHERETO_START_LOOKUP_DEV='1', WHERETO_RATINGS_DEV='1', NODE_ENV='development')
    if args.advanced:
        os.environ.update(WHERETO_ADVANCED_DEV='1',WHERETO_STOP_RESOLUTION_DEV='1',WHERETO_HOURS_DEV='1')
    counts = {'searches': 0, 'elements': 0, 'details': 0, 'ai': 0}
    route_policies=[]
    scenario = {'name': 'advanced' if args.advanced else 'refinements' if args.refinements else 'cinema_acceptance' if args.acceptance else 'normal'}

    def hours_records(records):
        if scenario['name'] not in ('advanced_now','advanced_now_closed','advanced_now_opens_before','advanced_now_closes_during','advanced_acceptance_closed'):return records
        from backend.hours_fixtures49 import fixture_hours
        from datetime import datetime,timedelta,timezone
        from zoneinfo import ZoneInfo
        for record in records:
            record.update(fixture_hours(closed=scenario['name']=='advanced_now_closed' and record['id']=='Synthetic_college'))
            if scenario['name']=='advanced_acceptance_closed' and record['id']=='Synthetic_college':
                # Only today's verified college periods are removed; future dates
                # remain distinct. Café hours stay active and unmodified.
                record['currentOpeningHours']['periods']=record['currentOpeningHours']['periods'][1:]
            if record['id']=='Synthetic_college' and scenario['name'] in ('advanced_now_opens_before','advanced_now_closes_during'):
                instant=(datetime.now(timezone.utc)+timedelta(minutes=1 if scenario['name']=='advanced_now_opens_before' else 5)).astimezone(ZoneInfo('America/New_York'))
                period=record['currentOpeningHours']['periods'][0]
                boundary=period['open' if scenario['name']=='advanced_now_opens_before' else 'close']
                boundary.update(hour=instant.hour,minute=instant.minute)
        return records

    def search(body, **kwargs):
        from backend.development_cost import dispatch
        dispatch('search')
        counts['searches'] += 1
        if args.advanced and scenario['name'].startswith('advanced'):
            from backend.test_advanced_routing import COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION
            from backend.test_stop_resolution import place
            from copy import deepcopy
            records=[COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION,place('Synthetic_station_two','Penn Station','2 Fixture Road, New York',['train_station'])]
            query=body['textQuery'].lower()
            if kwargs and not any(word in query for word in ('suny','penn')):
                return {'places':[place('Synthetic_start','Synthetic public starting point',types=['establishment'])]}
            types=next((t for word,t in [('bowling','bowling_alley'),('restaurant','restaurant'),('bars','bar'),('museum','museum'),('cafe','cafe'),('coffee','cafe'),('grocer','supermarket'),('supermarket','supermarket'),('atm','atm'),('bank','bank'),('pharmac','pharmacy')] if word in query),None)
            if types:
                page=int(body.get('pageToken','synthetic-1').split('-')[-1])
                city='Jersey City' if 'jersey city' in query or types in ('bowling_alley','restaurant','bar') else 'New York'
                generated=[place(f'Synthetic_{types}_{i}',f'Invented {types} {i}',f'{i+1} Fixture Road, {city}',[types],lat=40.75+i*.0001) for i in range((page-1)*10,page*10)]
                for venue in generated:
                    venue['addressComponents']=[{'longText':city,'types':['locality']}]+([{'longText':'New Jersey','shortText':'NJ','types':['administrative_area_level_1']}] if city=='Jersey City' else [])
                return {'places':hours_records(generated[:body.get('pageSize',10)]),**({'nextPageToken':f'synthetic-{page+1}'} if page<3 else {})}
            if 'suny' in query:return {'places':hours_records([deepcopy(COLLEGE)])}
            if 'penn' in query:return {'places':[deepcopy(p) for p in records if p['displayName']['text']=='Penn Station']}
            # Ordinary Jersey City request uses the same invented evidence boundary.
            if 'jersey city' in query:
                kind='bowling_alley' if 'bowl' in query else 'restaurant' if 'restaurant' in query else 'bar'
                venues=[place(f'Synthetic_{kind}_{i}',f'Invented {kind} {i}',f'{i+1} Fixture Road, Jersey City',[kind]) for i in range(body.get('pageSize',10))]
                for venue in venues:venue['addressComponents']=[{'longText':'Jersey City','types':['locality']},{'longText':'New Jersey','shortText':'NJ','types':['administrative_area_level_1']}]
                return {'places':venues}
            return {'places':deepcopy([p for p in records if types is None or types in p['types']][:body.get('pageSize',10)])}
        if scenario['name'] in ('refinements','travel_modes','hours','hours_closed','hours_missing'):
            from backend.refinement_fixtures import search_fixture as refinement_search
            data=refinement_search(body,**kwargs)
            if scenario['name'] in ('hours','hours_closed') and not kwargs:
                from backend.hours_fixtures49 import fixture_hours
                for index,place in enumerate(data.get('places',[])):
                    place.update(fixture_hours(closed=scenario['name']=='hours_closed' or index==0))
            return data
        if scenario['name']=='cinema_acceptance':
            from backend.acceptance_fixtures import search_fixture as acceptance_search
            return acceptance_search(body,**kwargs)
        if scenario['name']=='places_daily':
            from types import SimpleNamespace
            from backend.provider_errors import classify
            response=SimpleNamespace(status_code=429,json=lambda:{'error':{'details':[{'reason':'RATE_LIMIT_EXCEEDED','metadata':{'quota_limit':'SearchTextRequestPerDayPerProject'}}]}})
            code,message,diagnostics=classify(response,'search');error=DiscoveryError(code,message);error.diagnostics=diagnostics;raise error
        if scenario['name'] in ('quota', 'authentication'):
            raise DiscoveryError(scenario['name'], 'Google quota or authentication is unavailable. Stop and review settings.')
        if scenario['name'] in ('strict_local','strict_far'):
            from backend.strict_local_fixtures import local_places,local_origin
            return {'places':[local_origin()]} if kwargs else local_places(body,distant_only=scenario['name']=='strict_far')
        if scenario['name']=='open_activity' and not kwargs:
            from backend.location_fixtures import place
            phrase='pottery class' if 'pottery' in body['textQuery'] else 'restaurant' if 'restaurant' in body['textQuery'] else 'cafe'
            box=body.get('locationRestriction',{}).get('rectangle')
            lat=(box['low']['latitude']+box['high']['latitude'])/2 if box else 38.9
            lon=(box['low']['longitude']+box['high']['longitude'])/2 if box else -77.02
            return {'places':[place('Synthetic_'+phrase.replace(' ','_')+str(i),'Synthetic '+phrase+' '+str(i),lat,lon,types=['establishment'] if phrase=='pottery class' else [phrase]) for i in range(10)]}
        if scenario['name'] == 'browsing' and not kwargs:
            from backend.location_fixtures import place
            is_food='restaurant' in body['textQuery']
            box=body.get('locationRestriction',{}).get('rectangle')
            lat=(box['low']['latitude']+box['high']['latitude'])/2 if box else 40.75
            lon=(box['low']['longitude']+box['high']['longitude'])/2 if box else -73.98
            offset=counts['searches']*10
            records=[place(f'Synthetic_{"food" if is_food else "drinks"}_{n}',f'Synthetic {"restaurant" if is_food else "bar"} {n}',lat,lon,types=['restaurant' if is_food else 'bar']) for n in range(offset,offset+10)]
            for p in records:
                p['formattedAddress']='Synthetic address, Manhattan, New York'
                p['addressComponents']=[{'longText':'Manhattan','types':['sublocality_level_1']},{'longText':'New York','types':['locality']}]
            return {'places':records}
        if scenario['name'] in ('geographic','outing_expired','unknown_destination'):
            if kwargs:
                return {'places':[{
                    'id':'Synthetic_manual_reference','displayName':{'text':'Synthetic public park'},
                    'formattedAddress':'Synthetic reference, New York, NY',
                    'location':{'latitude':40.75,'longitude':-73.98},'types':['park'],
                    'addressComponents':[{'longText':'New York','types':['locality']}]}]}
            from backend.location_fixtures import neighborhood_fixture
            return neighborhood_fixture(body)
        if scenario['name'] == 'location_acceptance':
            from backend.location_fixtures import acceptance_search_fixture
            return acceptance_search_fixture(body,**kwargs)
        if scenario['name'] == 'location_first':
            from backend.location_fixtures import spatial_search_fixture
            return spatial_search_fixture(body, **kwargs)
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
        from backend.development_cost import dispatch
        dispatch('matrix', len(body['origins'])*len(body['destinations']))
        counts['elements'] += len(body['origins']) * len(body['destinations'])
        route_policies.append({'mode':body['travelMode'],'preference':body.get('routingPreference'),'departureTimeSent':'departureTime' in body,'elements':len(body['origins'])*len(body['destinations'])})
        if args.advanced and scenario['name'].startswith('advanced'):
            def seconds(a,b):
                if body['travelMode']=='WALK':return 600
                if scenario['name']=='advanced_traffic_long':return 3600
                if scenario['name']=='advanced_acceptance_fractional':return 119.316666667
                if scenario['name'] in ('advanced_optional_later','advanced_optional_discovery','advanced_optional_impossible'):
                    ids=' '.join(p['waypoint'].get('placeId','') for p in (a,b))
                    cafe=re.search(r'Synthetic_cafe_(\d+)',ids)
                    threshold=4 if scenario['name']=='advanced_optional_later' else 10 if scenario['name']=='advanced_optional_discovery' else 1000
                    if cafe and int(cafe[1])<threshold:return 3000
                if scenario['name']=='advanced_shortest':
                    ids=' '.join(p['waypoint'].get('placeId','') for p in (a,b))
                    cafe=re.search(r'Synthetic_cafe_(\d+)',ids)
                    if cafe:return (int(cafe[1])+1)*60
                return 120
            return [{'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS','duration':str(seconds(a,b))+'s','distanceMeters':600} for i,a in enumerate(body['origins']) for j,b in enumerate(body['destinations'])]
        if scenario['name'] == 'slow_routes': sleep(3)
        if scenario['name'] in ('strict_local','strict_far'):
            from backend.strict_local_fixtures import local_matrix
            return local_matrix(body)
        if scenario['name']=='location_acceptance':
            from backend.location_fixtures import acceptance_matrix_fixture
            return acceptance_matrix_fixture(body)
        if scenario['name']=='travel_modes':
            from backend.travel_mode_fixtures import matrix as mode_matrix
            return mode_matrix(body)
        result = matrix_fixture(body)
        if scenario['name'] == 'bowling_diagnostic':
            for element in result:
                origin = body['origins'][element['originIndex']]['waypoint'].get('placeId','')
                if origin == 'Fixture_bowling_5': element['duration'] = '900s'
        return [] if scenario['name'] == 'missing_routes' else result

    def details(place_id):
        from backend.development_cost import dispatch
        dispatch('details')
        counts['details'] += 1
        if scenario['name'] == 'details_failure': raise DiscoveryError('quota', 'Contact lookup quota reached.')
        if scenario['name'] == 'missing_contacts': return {'placeId': place_id, 'phone': None, 'telephoneUrl': None, 'website': None, 'attributions': []}
        return details_fixture(place_id)

    class FixtureAI:
        def interpret(self, text):
            counts['ai'] += 1
            if args.local_ai:return local_provider.interpret(text)
            if args.advanced:
                import json
                from pathlib import Path
                rows=json.loads(Path(__file__).with_name('repair_extractions.json').read_text())+json.loads(Path(__file__).with_name('return_phrase_extractions.json').read_text())
                match=next((r for r in rows if r['text'].casefold()==text.casefold()),None)
                if match:return Interpretation.model_validate(match['raw'])
            if args.journey or args.advanced:
                from backend.journey_fixtures import FixtureAI as JourneyAI
                return JourneyAI().interpret(text)
            if scenario['name'] in ('refinements','travel_modes','hours','hours_closed','hours_missing'):
                from backend.refinement_fixtures import FixtureAI as RefinementAI
                return RefinementAI().interpret(text)
            if scenario['name']=='cinema_acceptance':
                from backend.acceptance_fixtures import FixtureAI as AcceptanceAI
                return AcceptanceAI().interpret(text)
            pattern = r'\b(pottery class|go-karting|show movies|bowling|dinner|drinks|coffee|museum|movies?|concert)\b'
            activities = [m[0] for m in re.finditer(pattern, text, re.I)]
            leg = re.search(r'between venues under (\d+) minutes', text, re.I)
            from backend.between_policy import between_intent
            between,_,_=between_intent(text)
            return Interpretation(activities=activities or ['coffee'], people=None,
                budget_per_person=None, date=None, location='Hyderabad' if 'Hyderabad' in text else 'Mystery District' if 'Mystery District' in text else 'Manhattan' if 'Manhattan' in text else 'Washington, DC' if 'Washington, DC' in text else 'Baltimore' if 'Baltimore' in text else None,
                preferences=[], transport='walking' if 'walking' in text else 'driving' if 'driving' in text else None,
                travel_leg_minutes=int(leg[1]) if leg else int(between.value) if between and between.unit=='minutes' and between.mode=='strict' and between.value.is_integer() else None)

    def refreshed_saved(identity,**kwargs):
        counts['details']+=1
        from backend.development_cost import dispatch
        dispatch('details',1)
        if scenario['name']=='refresh_partial' and 'restaurant' in identity:
            raise DiscoveryError('invalid_response','Synthetic unavailable venue; no retry.')
        from backend.refinement_fixtures import refreshed
        data=refreshed(identity)
        if kwargs.get('include_hours'):
            from datetime import date
            from backend.hours_fixtures49 import fixture_hours
            from backend.venue_normalization import normalize_google_place
            from backend.planning_hours import venue_hours
            raw={'id':identity,'displayName':{'text':data['name']},**fixture_hours()}
            data['hoursEvidence']=venue_hours(normalize_google_place(raw,kwargs.get('activity','food')),date.fromisoformat(kwargs['outing_date']),start=kwargs.get('window_start'),end=kwargs.get('window_end'))
        if not kwargs.get("include_contacts"):data={k:v for k,v in data.items() if k not in ("phone","website","telephoneUrl")}
        return data

    from backend.ai import create_provider
    local_provider=create_provider() if args.local_ai else None
    from backend.location_context import outing_problem as actual_outing_problem
    def calendar(request,now=None):
        if scenario['name']=='outing_expired':
            from datetime import datetime,timedelta
            from zoneinfo import ZoneInfo
            now=datetime.combine(request.date+timedelta(days=1),datetime.min.time(),tzinfo=ZoneInfo(request.calendarTimezone or 'America/New_York'))
        return actual_outing_problem(request,now)
    with patch('backend.location_context.outing_problem',side_effect=calendar), patch('requests.sessions.Session.send', side_effect=AssertionError('Offline fixture server refused network')), \
         patch('backend.places_transport.text_search', side_effect=search), \
         patch('backend.routes_transport.compute_matrix', side_effect=matrix), \
         patch('backend.venue_details.fetch_details', side_effect=details), \
         patch('backend.saved_refresh.fetch_saved_details', side_effect=refreshed_saved), \
         patch('backend.interpretation.create_provider', return_value=FixtureAI()):
        from backend.main import app
        @app.get('/__test/counts')
        def stats(): return counts
        @app.post('/__test/expire-advanced')
        def expire_advanced():
            from backend.advanced_planning import sessions
            for session in sessions.items.values():session.expires=0
            return {'expired':len(sessions.items)}
        @app.get('/__test/routes')
        def route_stats():return route_policies
        @app.post('/__test/scenario')
        def set_scenario(value: dict):
            scenario['name'] = value.get('name', 'normal')
            if scenario['name']=='exhausted':
                from backend.option_sessions import option_sessions
                from backend.models import ContinuationStatus
                from backend.continuation_status import continuation_status
                for _,context,_ in option_sessions.entries.values():
                    for job in context.get('jobs',[]):job['done']=True
                    context['regionSteps']={a:32 for a in context['request'].activities}
                    last=context.get('lastContinuation')
                    if last:
                        last.canDiscover=False
                        last.continuationStatus=ContinuationStatus(**continuation_status(combinations=last.canExpand))
            os.environ['VENUE_DATA_MODE'] = 'mock' if scenario['name']=='mock' else 'real'
            os.environ['WHERETO_EXPLORATION_DEV'] = '1' if args.exploration_ledger and scenario['name']!='mock' else '0'
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
