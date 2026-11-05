"""Offline Task 51 overhead baseline; invented fixtures, no model/Google/SQL sends."""
import io
import json
from math import ceil
from time import perf_counter
from unittest.mock import patch
from datetime import datetime, timezone

from backend.admission import LocalAdmission, fingerprint
from backend.operations import event


def measure(operation, count):
    values=[]
    for _ in range(count):
        started=perf_counter()
        operation()
        values.append((perf_counter()-started)*1000)
    values.sort()
    return {'samples':count, 'p50Ms':round(values[ceil(count*.5)-1],4),
            'p95Ms':round(values[ceil(count*.95)-1],4)}


def main():
    import logging
    # Measure actual structured formatting + writes to an in-memory log sink.
    logger=logging.getLogger('whereto.operations')
    handler=logging.StreamHandler(io.StringIO())
    previous=logger.handlers
    logger.handlers=[handler]
    store=LocalAdmission(burst=1000000)
    def admit(): store.acquire(fingerprint('/api/interpret',b'{"text":"Invented coffee request"}'),'interpretation').release()
    from backend.test_advanced_planning import IntegrationTests
    fixture=IntegrationTests('test_named_roundtrip_dto_and_receipt')
    fixture.setUp()
    try:
        # Retain offline HTTP-send blocking from the existing integration harness.
        results={'admissionAndFingerprint':measure(admit,1000),
                 'structuredEvent':measure(lambda:event('request_finished','planning',status=200,duration_ms=1),1000)}
        from backend.models import PlanningRequest
        from backend.ranking import recommend_plans
        ordinary=PlanningRequest(activities=['food','bowling'],date='2099-01-01')
        results['ordinaryCalculation']=measure(lambda:recommend_plans(ordinary),30)
        from backend.provider_budget import ProviderBudget, ProviderSettings
        def reserve():
            with ProviderBudget(ProviderSettings()).outing().reserve('search','synthetic'): pass
        results['providerAdmission']=measure(reserve,1000)
        from backend.interpretation import InterpretationInput, PendingClarification, interpret_request
        from backend.ai import Interpretation
        pending=PendingClarification(text='Coffee tomorrow.',
            interpretation=Interpretation(activities=['Coffee'],budget_per_person=None,date=None,location=None,preferences=[]),
            referenceTime=datetime.now(timezone.utc))
        value=InterpretationInput(text=pending.text,pending=pending,answers={'location':'Baltimore'})
        with patch('backend.interpretation.create_provider',side_effect=AssertionError('No AI call')):
            def clarify():
                result=interpret_request(value)
                assert result.request is not None
            results['fieldClarification']=measure(clarify,30)
        # Full fixture generation includes trusted resolution, routing, timing and receipt.
        results['advancedFixture']=measure(lambda:fixture.run_session(fixture.session()),30)
        print(json.dumps(results,indent=2))
    finally:
        fixture.doCleanups()
        logger.handlers=previous


if __name__=='__main__': main()
