"""ASGI boundary: bounded reads/admission and content-free request outcomes."""
import asyncio
from time import perf_counter
from uuid import uuid4
from starlette.responses import JSONResponse
from backend.admission import AdmissionError, active_lease, fingerprint, requests
from backend.operations import event, request_id

OPERATIONS = {
    '/api/interpret': 'interpretation', '/api/plans/generate': 'planning',
    '/api/plans/options': 'options', '/api/plans/advanced': 'advanced',
    '/api/plans/save': 'save', '/api/plans/reopen': 'reopen',
    '/api/plans/refresh': 'saved_refresh', '/api/venues/details': 'details',
    '/api/starting-places': 'lookup', '/api/starting-areas': 'starting_areas',
}


class RequestManagement:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] != 'http' or path not in OPERATIONS:
            return await self.app(scope, receive, send)
        from backend.failures import MESSAGES
        operation = OPERATIONS[path]
        reference = uuid4().hex[:16]  # Never trust a client correlation header.
        context = request_id.set(reference)
        start = perf_counter()
        lease = None
        http_released = False
        status = 499
        event('request_started', operation)

        async def reject(code, http_status):
            nonlocal status
            status = http_status
            await JSONResponse({'code': code, 'message': MESSAGES[code], 'correlationId': reference},
                status_code=status, headers={'Cache-Control': 'no-store', 'X-Correlation-ID': reference,
                'Referrer-Policy': 'no-referrer'})(scope, receive, send)

        async def observed_send(message):
            nonlocal status, http_released
            if message['type'] == 'http.response.start':
                status = message['status']
                message = {**message, 'headers': [(k, v) for k, v in message.get('headers', [])
                    if k.lower() != b'x-correlation-id'] + [(b'x-correlation-id', reference.encode())]}
            # Release HTTP ownership before publishing the final response byte.
            # A legitimate immediate next action must not race ASGI teardown.
            # An outstanding worker retains its own independent reference.
            if message['type'] == 'http.response.body' and not message.get('more_body') and lease and not http_released:
                lease.release()
                http_released = True
            await send(message)

        try:
            # Count readers too; a slow body cannot create an unbounded queue.
            lease = requests.acquire(uuid4().bytes, operation)
            async def read():
                body = bytearray()
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return None
                    body.extend(message.get('body', b''))
                    if len(body) > (4096 if operation in ('advanced', 'save', 'reopen', 'saved_refresh') else 65536):
                        raise OverflowError()
                    if not message.get('more_body'):
                        return bytes(body)
            body = await asyncio.wait_for(read(), timeout=5)
            if body is None:
                event('cancelled', operation, reason='cancelled')
                return
            # Exchange the provisional reader key atomically for a content key.
            key = fingerprint(path, body)
            lease.bind(key)
            lease_context = active_lease.set(lease)
            replayed = False
            async def replay():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {'type': 'http.request', 'body': body, 'more_body': False}
                return await receive()
            try:
                await self.app(scope, replay, observed_send)
            finally:
                active_lease.reset(lease_context)
        except AdmissionError as error:
            if error.reason == 'duplicate':
                event('rejected', operation, reason=error.reason)
            await reject(error.code, 409 if error.reason == 'duplicate' else 429 if error.reason == 'burst' else 503)
        except OverflowError:
            await reject('request_too_large', 413)
        except TimeoutError:
            await reject('request_body_timeout', 408)
        finally:
            if lease and not http_released:
                lease.release()
            event('request_finished', operation, status=status, duration_ms=(perf_counter()-start)*1000)
            request_id.reset(context)
