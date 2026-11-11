"""Explicit loopback fixture process for the unchanged application routes.

Server-owned synthetic inputs only. No application startup imports this module.
All external transports and database connections fail before I/O.
"""
import argparse
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
import re
from time import monotonic
from pathlib import Path
from threading import Lock
from unittest.mock import patch

REFERENCE = datetime(2026, 11, 5, 15, tzinfo=timezone.utc)
CASES = Path(__file__).with_name('task52_v51_application_cases.json')


def refuse_production():
    if (os.environ.get('NODE_ENV') == 'production'
            or os.environ.get('WHERETO_ENV') == 'production'
            or any(os.environ.get(key) for key in ('VERCEL', 'K_SERVICE', 'WEBSITE_INSTANCE_ID'))):
        raise ValueError('The synthetic application fixture requires a local test process')


class MemoryDocuments:
    """Disposable synthetic save store behind the actual receipt selection."""
    def __init__(self):
        self.documents = {}
        self.lock = Lock()

    @contextmanager
    def database(self, token, readonly=False):
        yield self

    def write(self, _connection, document, token):
        from backend.saved_plans import digest, PersistenceError, SavedDocument
        key = digest(token)
        candidate = SavedDocument.model_validate_json(document.model_dump_json())
        with self.lock:
            if key in self.documents and self.documents[key] != candidate:
                raise PersistenceError(409)
            self.documents[key] = candidate

    def read(self, _connection, token):
        from backend.saved_plans import digest, PersistenceError, SavedDocument
        with self.lock:
            document = self.documents.get(digest(token))
            if document is None:
                raise PersistenceError(404)
            saved = SavedDocument.model_validate_json(document.model_dump_json())
        return {**saved.model_dump(mode='json'), 'saved': True, 'liveDetailsAvailable': False,
                'expiresAt': (REFERENCE + timedelta(days=30)).isoformat()}


@contextmanager
def application_fixture(*, enabled=True):
    """Own all patches for this explicit fixture process and restore on exit."""
    refuse_production()
    from backend.ai import Interpretation
    from backend.interpretation import interpret_request
    from backend.test_advanced_planning import IntegrationTests
    from backend.test_advanced_routing import record
    from backend.testing_clock import calendar_clock
    from scripts.task52_v51_local_continuation import LocalContinuation

    document = json.loads(CASES.read_text())
    assert document['syntheticOnly']
    cases = {c['text']: c['extraction'] for c in document['cases']}
    store = MemoryDocuments()
    counts = {'extractions': 0, 'externalSends': 0}
    continuation = LocalContinuation()
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, WHERETO_AI_WARMUP_DEV='0', WHERETO_START_LOOKUP_DEV='1'))
        fixture = IntegrationTests()
        fixture.setUp()
        stack.callback(fixture.doCleanups)
        stack.enter_context(calendar_clock(REFERENCE))
        calendar = stack.enter_context(patch('backend.advanced_planning.datetime', wraps=datetime))
        calendar.now.side_effect = lambda tz=None: REFERENCE.astimezone(tz or timezone.utc)
        for city in ('New York', 'Jersey City', 'Hyderabad'):
            for kind in ('cafe','museum','restaurant','bowling_alley','video_arcade','movie_theater','supermarket','bank','pharmacy'):
                for i in range(3):
                    venue = record(f'Synthetic_{city.replace(" ","_")}_{kind}_{i}',
                                   f'Synthetic {kind} {i}', [kind])
                    venue['formattedAddress'] = f'{i+1} Fictional Road, {city}'
                    venue['addressComponents'] = [{'longText': city, 'types':['locality']}]
                    if city == 'Hyderabad':
                        venue['location'] = {'latitude':17.443, 'longitude':78.38}
                    fixture.records.append(venue)

        def search(body, **kwargs):
            fixture.searches.append(body)
            text = body['textQuery'].casefold()
            if kwargs:
                return {'places':[record('Synthetic_public_start','Synthetic public starting point',['establishment'])]}
            city = next((c for c in ('Jersey City','Hyderabad','New York') if c.casefold() in text),
                        'New York')
            kind = next((kind for word,kind in (
                ('coffee','cafe'),('cafe','cafe'),('tea','cafe'),('museum','museum'),
                ('restaurant','restaurant'),('dinner','restaurant'),('bowling','bowling_alley'),
                ('arcade','video_arcade'),('movie','movie_theater'),('cinema','movie_theater'),
                ('supermarket','supermarket'),('grocer','supermarket'),('bank','bank'),('pharmacy','pharmacy'),
            ) if word in text), None)
            if kind is None and 'suny' in text:
                return {'places':[fixture.records[0]]}
            return {'places':[v for v in fixture.records if kind in v['types']
                              and v['addressComponents'][0]['longText'] == city][:3]}

        def extract(value, **_kwargs):
            if value.pending is None:
                counts['extractions'] += 1
            raw = cases.get(value.text)
            if raw is None:
                from backend.ai import AIError
                raise AIError('No server-owned extraction for this synthetic request', code='llm_invalid_response')
            if enabled:
                return continuation.interpret(value, raw, REFERENCE)
            class Supplied:
                def interpret(self, _text):
                    return Interpretation.model_validate(deepcopy(raw))
            return interpret_request(value, provider=Supplied(), now=REFERENCE)

        def no_send(*_args, **_kwargs):
            counts['externalSends'] += 1
            raise AssertionError('Synthetic fixture refused external network')

        stack.enter_context(patch('backend.places_transport.text_search', side_effect=search))
        stack.enter_context(patch('requests.sessions.Session.send', side_effect=no_send))
        stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('No outbound sockets')))
        stack.enter_context(patch('psycopg.connect', side_effect=AssertionError('No real database')))
        stack.enter_context(patch('backend.interpretation.create_provider', side_effect=AssertionError('No model factory')))
        stack.enter_context(patch('backend.saved_plans.database', store.database))
        stack.enter_context(patch('backend.saved_plans.write_document', store.write))
        stack.enter_context(patch('backend.saved_plans.read_document', store.read))
        from backend import main
        from backend.provider_budget import ProviderBudget
        stack.enter_context(patch.object(main, 'provider_budget', ProviderBudget()))
        registry = main.advanced_sessions
        original_run = registry.run

        def advanced_answer(value):
            if value.date and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value.date):
                with registry.lock:
                    session = registry.items.get(value.token)
                if (session is not None and session.expires > monotonic()
                        and session.context.timezoneBasis != 'destination_calendar'):
                    from backend.advanced_planning import AdvancedAnswerError
                    raise AdvancedAnswerError('advanced_answer_invalid',
                        'Choose an exact YYYY-MM-DD date until the search area calendar is confirmed. Your request is kept.')
            return original_run(value)

        stack.enter_context(patch.object(registry, 'run', side_effect=advanced_answer))
        stack.enter_context(patch.object(main, 'interpret_request', side_effect=extract))
        yield main.app, fixture, counts, store


def main():
    refuse_production()
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged loopback port')
    with application_fixture(enabled=not args.legacy) as (app, fixture, counts, store):
        from fastapi import Request
        from fastapi.responses import JSONResponse
        from urllib.parse import urlparse

        @app.middleware('http')
        async def fixture_loopback(request: Request, call_next):
            local = {'localhost','127.0.0.1','::1'}
            host = urlparse('http://' + request.headers.get('host','')).hostname
            origin = request.headers.get('origin')
            if (request.client.host not in local or host not in local
                    or request.headers.get('forwarded')
                    or request.headers.get('x-forwarded-for','127.0.0.1') not in local
                    or origin and urlparse(origin).hostname not in local):
                return JSONResponse(status_code=403, content={'message':'Synthetic fixture accepts loopback only'})
            return await call_next(request)

        @app.get('/__test/counts')
        def counters():
            return {**counts, 'searches':len(fixture.searches), 'matrixRequests':len(fixture.calls),
                    'savedDocuments':len(store.documents)}

        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning', access_log=False)


if __name__ == '__main__':
    main()
