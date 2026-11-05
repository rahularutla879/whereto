"""Bounded, process-local operational measurements. Never record request content."""
from collections import Counter, deque
from contextvars import ContextVar
from contextlib import contextmanager
import json
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue, Full
from math import ceil
from threading import Lock
from time import perf_counter

request_id = ContextVar('operational_request_id', default=None)
OPERATIONS = frozenset(('interpretation', 'planning', 'options', 'advanced', 'save',
    'reopen', 'saved_refresh', 'lookup', 'starting_areas', 'details', 'search',
    'matrix', 'route', 'http', 'validation', 'inference', 'provider_admission', 'admission'))
EVENTS = frozenset(('request_started', 'request_finished', 'admitted', 'rejected',
    'failure', 'stage_finished', 'provider_reserved', 'provider_dispatched', 'cancelled'))
_lock = Lock()
_dropped = 0
_log_queue = Queue(maxsize=1024)


class BoundedLogHandler(QueueHandler):
    def enqueue(self, record):
        global _dropped
        try:
            self.queue.put_nowait(record)
        except Full:
            # Operational output must never block or grow without bound.
            with _lock:
                _dropped += 1


_logger = logging.getLogger('whereto.operations')
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(message)s'))
    _logger.addHandler(BoundedLogHandler(_log_queue))
    _listener = QueueListener(_log_queue, _handler)
    _listener.start()
_counts = Counter()
_samples = {}
_usage = Counter()


def event(name, operation, *, reason='none', status=None, duration_ms=None, units=None):
    # Fixed field/label vocabulary, even if an upstream exception carries arbitrary code.
    if name not in EVENTS or operation not in OPERATIONS:
        return
    from backend.failures import MESSAGES
    reasons = {'none', 'duplicate', 'capacity', 'burst', 'cancelled', 'timeout',
               'invalid_request', 'expired', 'quota', 'provider', 'authentication',
               'permission', 'invalid_response', 'local_minute', 'local_shared_minute',
               'concurrent_request', 'advanced_session_expired', 'advanced_answer_invalid'}
    reason = reason if reason in reasons or reason in MESSAGES else 'other'
    fields = dict(event=name, operation=operation, reason=reason)
    reference = request_id.get()
    if reference:
        fields['requestId'] = reference
    if status is not None:
        fields['status'] = int(status)
    if duration_ms is not None:
        fields['durationMs'] = round(max(0, duration_ms), 3)
    if units is not None:
        fields['units'] = {k: n for k, n in units.items() if k in {
            'search_pro', 'search_enterprise', 'details', 'details_pro',
            'matrix_element', 'matrix_pro_element'} and type(n) is int and n >= 0}
    with _lock:
        _counts[(name, operation, reason)] += 1
        if name in ('provider_reserved', 'provider_dispatched'):
            for sku, count in fields.get('units', {}).items():
                _usage[(name, sku)] += count
        if duration_ms is not None:
            _samples.setdefault(operation, deque(maxlen=1024)).append(max(0, duration_ms))
    level = logging.WARNING if name in ('failure', 'rejected') else logging.INFO
    _logger.log(level, json.dumps(fields, separators=(',', ':')))


@contextmanager
def stage(operation):
    start = perf_counter()
    try:
        yield
    finally:
        event('stage_finished', operation, duration_ms=(perf_counter()-start)*1000)


def snapshot():
    with _lock:
        timings = {}
        for operation, samples in _samples.items():
            values = sorted(samples)
            timings[operation] = {'sampleCount': len(values), **{
                f'p{p}Ms': round(values[max(0, ceil(len(values)*p/100)-1)], 3)
                for p in (50, 90, 95, 99)}}
        return {'counts': [{'event': k[0], 'operation': k[1], 'reason': k[2], 'count': v}
                           for k, v in sorted(_counts.items())], 'timings': timings,
                'scope': 'process_since_restart', 'sampleLimitPerOperation': 1024,
                'droppedLogEvents': _dropped, 'logQueueCapacity': 1024,
                'providerUsage': {name: {sku: count for (kind, sku), count in _usage.items() if kind == name}
                                  for name in ('provider_reserved', 'provider_dispatched')}}
