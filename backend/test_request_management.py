"""Task 51: actual concurrent ownership, bounded ASGI reads and safe diagnostics."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from backend.admission import (AdmissionError, LocalAdmission, active_lease,
    fingerprint, inference, validate_environment)
from backend.operations import event, request_id, snapshot
from backend.request_middleware import RequestManagement


class AdmissionTests(unittest.TestCase):
    def test_atomic_reservations_and_independent_fair_admission(self):
        store = LocalAdmission(capacity=4)
        with ThreadPoolExecutor(max_workers=16) as pool:
            def attempt(_):
                try: return store.acquire(b'same', 'planning')
                except AdmissionError: return None
            results = list(pool.map(attempt, range(16)))
        leases = [value for value in results if value]
        self.assertEqual(len(leases), 1)
        independent = store.acquire(b'other', 'planning')
        self.assertEqual(store.snapshot()['active'], 2)
        for lease in leases+[independent]: lease.release()
        self.assertEqual(store.snapshot()['active'], 0)

    def test_rolling_burst_resume_without_daily_cap(self):
        now = [0]
        store = LocalAdmission(capacity=3, burst=2, interval=10, clock=lambda:now[0])
        for _ in range(2): store.acquire(b'fresh', 'planning').release()
        with self.assertRaises(AdmissionError) as error: store.acquire(b'next', 'planning')
        self.assertEqual(error.exception.reason, 'burst')
        for _ in range(1000):
            now[0] += 10
            store.acquire(b'fresh', 'planning').release()

    def test_capacity_released_only_when_worker_finishes(self):
        store = LocalAdmission(capacity=1)
        lease = store.acquire(b'work', 'planning')
        lease.retain()
        lease.release()
        with self.assertRaises(AdmissionError): store.acquire(b'next', 'planning')
        lease.release()
        store.acquire(b'next', 'planning').release()

    def test_fingerprint_canonicalization_and_request_scope(self):
        self.assertEqual(fingerprint('/a', b'{"a":1,"b":2}'), fingerprint('/a', b'{ "b":2, "a":1 }'))
        self.assertNotEqual(fingerprint('/a', b'{}'), fingerprint('/b', b'{}'))
        self.assertNotEqual(fingerprint('/a', b'{"a":1}'), fingerprint('/a', b'{"a":2}'))

    def test_all_known_production_environments_fail_closed(self):
        for env in ({'WHERETO_ENV':'production'}, {'NODE_ENV':'production'}, {'K_SERVICE':'service'},
                    {'WHERETO_ENV':'typo'}, {'RENDER':'true'}, {'WHERETO_ENV':'production','WHERETO_SHARED_STATE':'redis'}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), self.assertRaises(RuntimeError):
                validate_environment()
        with patch.dict(os.environ, {}, clear=True): validate_environment()

    def test_real_inference_adapter_gate_and_release_on_failure(self):
        from backend.ai import AISettings, AIError
        from backend.ai.ollama import OllamaProvider
        provider = OllamaProvider(AISettings())
        started, finish = Event(), Event()
        def work(_):
            started.set()
            finish.wait(3)
            raise AIError('private upstream body')
        with patch.object(provider, '_interpret', side_effect=work), ThreadPoolExecutor(2) as pool:
            first = pool.submit(provider.interpret, 'private input')
            self.assertTrue(started.wait(2))
            try:
                with self.assertRaises(AIError) as error: provider.interpret('different input')
                self.assertEqual(error.exception.code, 'service_busy')
                self.assertEqual(inference.snapshot()['active'], 1)
            finally: finish.set()
            with self.assertRaises(AIError): first.result(3)
        self.assertEqual(inference.snapshot()['active'], 0)

    def test_existing_ledger_details_tiers_and_combined_matrix_window(self):
        from backend.development_cost import DevelopmentCost, AccountingError, dispatch
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'WHERETO_DEV_COST_LEDGER': directory+'/ledger'}):
            cost = DevelopmentCost(enforce_limit=False)
            with cost.reserve({'details': 1, 'details_pro': 1}):
                # Mixed tier batches are not used by adapters; reserve each independently.
                pass
            with cost.reserve({'details_pro':1}): dispatch('details', sku='details_pro')
            with cost.reserve({'details':1}): dispatch('details', sku='details')
            with cost.reserve({'matrix_element':75}): dispatch('matrix',75,sku='matrix_element')
            with cost.reserve({'matrix_pro_element':75}): dispatch('matrix',75,sku='matrix_pro_element')
            with self.assertRaises(AccountingError):
                with cost.reserve({'matrix_pro_element':1}): self.fail('must reject before dispatch')
            row=json.loads(Path(directory+'/ledger').read_text())['days'][cost.day()]
            self.assertEqual(row['grossMicrousd'], 2*17000+2*20000+75*5000+75*10000)
            self.assertEqual(row['dispatched']['details_pro'],1)
            self.assertEqual(row['dispatched']['details'],1)

    def test_existing_session_overlap_maps_to_safe_busy_without_provider_blame(self):
        from backend.failures import provider_code, provider_status
        from backend.places import DiscoveryError
        for code, expected in [('busy', 'service_busy'), ('application_limit', 'provider_local_admission')]:
            error=DiscoveryError(code, 'private diagnostic')
            self.assertEqual(provider_code(error), expected)
            self.assertEqual(provider_status(error), 503)

    def test_privacy_and_bounded_metric_labels(self):
        secret='private address 12.345 token password provider-body'
        with self.assertLogs('whereto.operations',logging.INFO) as captured:
            context=request_id.set('0123456789abcdef')
            try:
                event('failure','planning',reason=secret)
                event('request_finished','planning',status=503,duration_ms=1.5)
                event('failure',secret,reason=secret)
            finally: request_id.reset(context)
        output='\n'.join(captured.output)
        self.assertNotIn(secret,output)
        self.assertIn('0123456789abcdef',output)
        self.assertIn('"reason":"other"',output)
        self.assertNotIn(secret,json.dumps(snapshot()))
        self.assertLessEqual(snapshot()['timings']['planning']['sampleCount'],1024)


class MiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, middleware, body=b'{}', path='/api/plans/generate', headers=None):
        sent=[]
        queue=asyncio.Queue()
        queue.put_nowait({'type':'http.request','body':body})
        async def receive(): return await queue.get()
        async def send(value): sent.append(value)
        await middleware({'type':'http','path':path,'headers':headers or []},receive,send)
        return sent

    async def test_body_bound_before_expensive_work(self):
        async def inner(*_): self.fail('endpoint must not run')
        with patch('backend.request_middleware.requests',LocalAdmission()):
            result=await self.invoke(RequestManagement(inner), b'x'*65537)
        self.assertEqual(result[0]['status'],413)

    async def test_duplicate_tabs_one_execution_and_correlation(self):
        started, finish = asyncio.Event(), asyncio.Event()
        count=0
        async def inner(scope,receive,send):
            nonlocal count
            count+=1
            self.assertEqual(await receive(),{'type':'http.request','body':b'{}','more_body':False})
            started.set()
            await finish.wait()
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':b'{}'})
        with patch('backend.request_middleware.requests',LocalAdmission()):
            middleware=RequestManagement(inner)
            first=asyncio.create_task(self.invoke(middleware,headers=[(b'x-correlation-id',b'forged')]))
            await started.wait()
            second=await self.invoke(middleware)
            self.assertEqual(second[0]['status'],409)
            finish.set()
            result=await first
            reference=dict(result[0]['headers'])[b'x-correlation-id'].decode()
            self.assertRegex(reference,r'^[a-f0-9]{16}$')
            self.assertEqual(count,1)
            await self.invoke(middleware) # Intentional fresh request after completion.
            self.assertEqual(count,2)

    async def test_cancelled_http_keeps_worker_lease_and_stops_next_dispatch(self):
        from backend.provider_work import run_work, check_cancelled
        from backend.provider_budget import ProviderLimitError
        started, finish = Event(), Event()
        store=LocalAdmission(capacity=1)
        lease=store.acquire(b'work','planning')
        errors=[]
        def work():
            started.set()
            finish.wait(3)
            try: check_cancelled()
            except ProviderLimitError: errors.append('cancelled')
        class Connected:
            async def is_disconnected(self): return False
        token=active_lease.set(lease)
        task=asyncio.create_task(run_work(Connected(),work))
        try:
            while not started.is_set(): await asyncio.sleep(.001)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
            lease.release()
            self.assertEqual(store.snapshot()['active'],1)
            finish.set()
            for _ in range(100):
                if store.snapshot()['active']==0: break
                await asyncio.sleep(.005)
            self.assertEqual(store.snapshot()['active'],0)
            self.assertEqual(errors,['cancelled'])
        finally:
            finish.set()
            active_lease.reset(token)


if __name__=='__main__': unittest.main()
