"""Security and lifetime checks for the disposable local application fixture."""
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.task52_v51_application_fixture import CASES, application_fixture, refuse_production
from scripts.task52_real_integration import inspect_original


def connect_socket(socket):
    with socket.socket() as connection:
        connection.connect(('203.0.113.1',443))

def post(path,payload,status=200):
    """Same dependency-free ASGI boundary used by existing shadow tests."""
    import asyncio
    from backend.main import app
    async def run():
        sent=[]
        delivered=False
        async def receive():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':json.dumps(payload).encode(),'more_body':False}
            await asyncio.Future()
        async def send(message):
            sent.append(message)
        scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
            'method':'POST','scheme':'http','path':path,'raw_path':path.encode(),'query_string':b'',
            'root_path':'','server':('localhost',8000),'client':('127.0.0.1',1234),
            'headers':[(b'host',b'localhost:8000'),(b'content-type',b'application/json')]}
        await app(scope,receive,send)
        assert next(m['status'] for m in sent if m['type']=='http.response.start')==status
        return json.loads(b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body'))
    return asyncio.run(run())


class LocalApplicationFixtureTests(TestCase):
    def test_production_environments_refuse_before_fixture_setup(self):
        for key in ('NODE_ENV','WHERETO_ENV','VERCEL','K_SERVICE','WEBSITE_INSTANCE_ID'):
            with self.subTest(key=key):
                with patch.dict('os.environ',{key:'production' if key.endswith('ENV') else 'hosted'}):
                    with self.assertRaisesRegex(ValueError,'local test process'):
                        refuse_production()

    def test_server_owned_cases_cover_originals_and_independent_inputs(self):
        cases = json.loads(CASES.read_text())
        self.assertTrue(cases['syntheticOnly'])
        self.assertEqual(len({c['text'] for c in cases['cases']}),16)
        self.assertEqual([c['id'] for c in cases['cases'][:5]],
                         ['extension-repeated','journey-04','extension-partial','journey-06','journey-21'])
        self.assertTrue(all(c['extraction']['activities'] for c in cases['cases']))
        from scripts.task52_v51_eval_identity import plan
        self.assertEqual([c['text'] for c in cases['cases'][:5]], [s['source'] for s in plan()['slots']])
        self.assertNotIn('task52_v51_application_fixture',Path('backend/main.py').read_text())

    def test_context_restores_runtime_and_refuses_real_transports(self):
        from backend import main
        from backend.interpretation import InterpretationInput
        original = main.interpret_request
        with application_fixture() as (_app, _fixtures, counts, _store):
            import requests
            import psycopg
            import socket
            for operation in (lambda:requests.get('https://example.invalid'),
                              lambda:psycopg.connect(''),
                              lambda:connect_socket(socket)):
                with self.assertRaises(AssertionError):
                    operation()
            raw = main.interpret_request(InterpretationInput(text='Buy groceries and maybe stop for coffee.'))
            self.assertEqual([(e.before,e.after) for e in raw.interpretation.journey.order],[(0,1)])
            self.assertEqual(counts['extractions'],1)
        self.assertIs(main.interpret_request,original)

    def test_manual_area_uses_existing_context_without_changing_source_graph(self):
        from backend.interpretation import InterpretationInput
        with application_fixture() as (_app,_fixture,_counts,_store):
            from backend import main
            r=main.interpret_outing(InterpretationInput(
                text='Buy groceries and maybe stop for coffee.',preferences={'location':'New York'}))
            self.assertIsNotNone(r.advancedToken)
            self.assertIsNone(r.request)
            self.assertEqual(r.context.destination,'New York')
            self.assertEqual([(e.before,e.after) for e in r.interpretation.journey.order],[(0,1)])

    def test_journal_inspection_still_matches_and_grants_no_authority(self):
        report=inspect_original()
        self.assertFalse(report['executionAuthorized'])
        r=report['inspection']['original']
        self.assertEqual(r['attempts'],10)
        self.assertEqual(r['privateFilesUnchanged'],324)
        self.assertTrue(r['persistentHistoricalHalt'])

    def test_http_optional_omission_and_unreachable_routes(self):
        with application_fixture() as (_app,fixture,_counts,_store):
            # Every route into optional coffee is unreachable; required groceries
            # still produce an option, carrying an explicit omitted-stop record.
            original_matrix=fixture.matrix
            def matrix(body):
                for a in body['origins']:
                    for b in body['destinations']:
                        aid=a['waypoint'].get('placeId','origin')
                        bid=b['waypoint'].get('placeId','origin')
                        if '_cafe_' in bid or bid=='Synthetic_coffee':
                            fixture.values[(body['travelMode'],aid,bid)]='unreachable'
                return original_matrix(body)
            from backend import routes_transport
            routes_transport.compute_matrix.side_effect=matrix
            raw=post('/api/interpret',{'text':'Buy groceries and maybe stop for coffee.'})
            token=raw['advancedToken']
            result=post('/api/plans/advanced',{'token':token,'date':'2026-11-20','destination':'New York'})
            self.assertTrue(result['options'])
            for option in result['options']:
                self.assertEqual([s['occurrence'] for s in option['stops']],[0])
                self.assertEqual([s['occurrence'] for s in option['omitted']],[1])
            # A missing required route cannot publish the three required visits.
            fixture.route_error=None
            routes_transport.compute_matrix.side_effect=lambda body:[{'originIndex':i,'destinationIndex':j,
                'status':{},'condition':'ROUTE_NOT_FOUND'}
                for i in range(len(body['origins'])) for j in range(len(body['destinations']))]
            raw=post('/api/interpret',{'text':'Tea, then museum, then dinner.'})
            result=post('/api/plans/advanced',{'token':raw['advancedToken'],
                'date':'2026-11-20','destination':'New York'})
            self.assertEqual(result['options'],[])

    def test_http_whole_trip_bound_requires_dwell_and_refuses_overrun(self):
        from backend.test_advanced_routing import start
        with application_fixture() as (_app,_fixture,_counts,_store):
            source=json.loads(CASES.read_text())['cases'][0]['text']
            raw=post('/api/interpret',{'text':source})
            answer={'token':raw['advancedToken'],'startingLocation':start().model_dump(mode='json')}
            result=post('/api/plans/advanced',answer)
            self.assertTrue(result['options'])
            self.assertEqual(result['options'][0]['durationState'],'unverified')
            for occurrence in range(3):
                result=post('/api/plans/advanced',{**answer,'dwell':{
                    'occurrence':occurrence,'minutes':10,'relation':'exact'}})
            self.assertTrue(result['options'])
            self.assertTrue(all(o['durationState']=='feasible' and o['ending']=='origin'
                                and o['elapsedUpperSeconds']<=180*60 for o in result['options']))
            result=post('/api/plans/advanced',{**answer,'dwell':{
                'occurrence':0,'minutes':200,'relation':'exact'}})
            self.assertEqual(result['options'],[])
