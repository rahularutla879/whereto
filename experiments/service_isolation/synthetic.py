"""Fixed, invented provider responses. No model parser, network or fallback."""
import json
from copy import deepcopy
from experiments.shared_state.contracts import Denied

ORDINARY='Coffee and museum in Baltimore on November 7, 2026'
PENDING='Coffee and museum in Baltimore'

def outputs():
    from backend.journey_fixtures import CASES
    ordinary=dict(activities=['coffee','museum'],location='Baltimore',date='2026-11-07',budget_per_person=None,preferences=[])
    return {ORDINARY:ordinary,PENDING:dict(ordinary,date=None),**{text:data for text,data,_ in CASES}}

def respond(payload):
    body=json.loads(payload)
    if 'model' in body:
        data=outputs().get(body['input'])
        if data is None:raise Denied('unknown_synthetic_source')
        return dict(output=deepcopy(data),usage=dict(provider=body['provider'],model=body['model'],input_tokens=len(payload),output_tokens=2,cached_tokens=0,reasoning_tokens=0,tool_calls=0))
    from backend.real_fixtures import search_fixture,matrix_fixture
    if body['operation']=='details':
        from backend.venue_details import DETAILS_MASK,contact_links
        identity=body['url'].rsplit('/',1)[-1];raw={'id':identity,'name':'Synthetic venue'}
        return contact_links(raw,identity) if body['mask']==DETAILS_MASK else raw
    if body['operation']=='matrix':
        # Same supplied fixture implementation used by native advanced tests.
        from backend.test_advanced_routing import AdvancedRoutingTests
        from types import SimpleNamespace
        return AdvancedRoutingTests.matrix(SimpleNamespace(calls=[],values={},route_error=None,partial=False),body['body'])
    if body['operation']=='search':
        if any(x in body['body']['textQuery'].casefold() for x in ('suny','pharmacy','bank','grocer','supermarket','penn','college','new york')):
            from backend.test_advanced_planning import IntegrationTests
            from backend.test_advanced_routing import COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION
            sample=IntegrationTests('test_named_roundtrip_dto_and_receipt');sample.searches=[];sample.records=[COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION]
            return sample.search(body['body'])
        return search_fixture(body['body'])
    raise Denied('synthetic_operation')
