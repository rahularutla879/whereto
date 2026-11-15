"""Source-bound append/single-send kernel; operational enrollment is unavailable.

All writes are currently limited to registered fresh fictional Q4C-schema state.
The same append/INTENT/capture path is tested without implementing live HTTP.
"""
from base64 import b64encode, b64decode
from contextlib import closing
from copy import deepcopy
import json
import os
import sqlite3
from types import SimpleNamespace

from scripts import task52_q1 as q1, task52_q4a as base
from scripts import task52_diag_protocol as parent
from scripts import task52_diag_identity as profile
from scripts import task52_real_integration as existing
from scripts import task52b_execution_identity as identity
from scripts import cloud_model52 as decoder

VERSION = '52b-append-single-send-execution-boundary-v1'
Denied = parent.auth.Denied
live_dispatch = base.live_dispatch  # No operational enrollment, credentials or HTTP.
REGISTRY = {}  # Test containment only; not an independent hostile-worker boundary.


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise Denied('Duplicate response key')
            result[key] = value
        return result
    def constant(_): raise Denied('Nonfinite response value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def _once(path, value):
    base.private_create(path, value)  # O_EXCL + file fsync + parent fsync, unchanged.


class SyntheticSend:
    """Closed responder, no callbacks, socket, credential or arbitrary URL port."""
    def __init__(self, raw, payload, *, failure=None, provider='openai',
                 method='POST', endpoint='/v1/responses'):
        if failure not in (None, 'before_send', 'possible_send', 'crash_before_raw'):
            raise Denied('Unknown synthetic failure')
        self.raw, self.payload, self.failure = raw, payload, failure
        self.provider, self.method, self.endpoint = provider, method, endpoint

    def exchange(self, directory, operation, payload_hash):
        identity.verify()
        if str(directory) not in REGISTRY or type(self.raw) is not bytes or len(self.raw)>1048576:
            raise Denied('Registered fictional storage and bounded raw response required')
        if type(self.payload) is not bytes or q1.sha(self.payload) != payload_hash:
            raise Denied('Canonical payload mismatch')
        entries = identity.requests()
        entry = next((r for r in entries if r['requestSHA256']==payload_hash), None)
        if entry is None or self.payload != entry['bytes'] or (
                self.provider, self.method, self.endpoint) != ('openai','POST','/v1/responses'):
            raise Denied('Provider/method/request substitution')
        intent = next((json.loads(p.read_bytes()) for p in directory.glob('fact-*')
                       if json.loads(p.read_bytes())['kind']=='INTENT' and
                       json.loads(p.read_bytes())['operation']==operation), None)
        if intent is None or intent['data']['payloadHash'] != payload_hash:
            raise Denied('Durable exact INTENT required')
        # Confirm committed reservation from an independent read connection.
        with closing(sqlite3.connect(f'file:{directory}/journal.sqlite?mode=ro',uri=True)) as db:
            db.execute('PRAGMA query_only=ON')
            rows = db.execute('SELECT * FROM attempts WHERE provider=? AND case_id=? AND repetition=?', entry['slot']).fetchall()
        if (len(rows)!=1 or rows[0][3:5]!=('reserved_uncertain',2500000) or
                json.loads(rows[0][5])['operation'] != operation):
            raise Denied('Committed reservation required')
        _once(directory/f'dispatch-{operation}.json',
              {'version': VERSION,'build':identity.MANIFEST_SHA,'operation':operation,
               'payloadHash':payload_hash,'intentHash':intent['hash'],'syntheticOnly':True})
        if self.failure in ('before_send','possible_send'):
            # Both consume the dispatch token and retain the entire reservation.
            raise TimeoutError('Fictional transport uncertainty; no resend')
        if self.failure=='crash_before_raw': os._exit(73)
        _once(directory/f'raw-{operation}.json',
              {'bytesBase64':b64encode(self.raw).decode('ascii'),'sha256':q1.sha(self.raw)})
        response = _json(self.raw)
        if (type(response) is not dict or response.get('model')!='gpt-6-luna'):
            raise Denied('Response model/envelope mismatch')
        content, usage, status = decoder.Adapter('openai',None).decode(response)
        _once(directory/f'decoded-{operation}.json',
              {'rawSHA256':q1.sha(self.raw),'responseHash':q1.digest(response),
               'content':content,'usage':usage,'status':status})
        return response


# Identical Q4C transition code with only the closed transport dependency changed.
# Preserve the existing diagnostic auth/scoring/plan; no review-rule amendment.
_context = {**parent._context, 'base':SimpleNamespace(
    plan=profile.plan, private_create=base.private_create,
    fsync_dir=base.fsync_dir, FakeTransport=SyntheticSend)}
_simulate = parent.auth.bind_function(parent.Engine.simulate_one, _context)


class AppendEngine(existing._AppendEngine):
    def check(self):
        identity.verify()
        marker = super().check()
        if str(self.directory) not in REGISTRY or REGISTRY[str(self.directory)] != identity.MANIFEST_SHA:
            raise Denied('No operational enrollment; fictional state only')
        return marker

    def db(self):
        connection = super().db()  # Existing PID/thread/current-lock guard.
        execute = connection.execute
        def constrained(statement, parameters=()):
            if statement == existing._APPEND:
                starts=[json.loads(p.read_bytes()) for p in sorted(self.directory.glob('fact-*'))
                        if json.loads(p.read_bytes())['kind']=='START']
                if not starts: raise Denied('Reservation without START')
                start=starts[-1]; index=start['data']['rowid']-11
                if not 0<=index<5: raise Denied('Reservation slot')
                slot=profile.plan()['slots'][index]
                if tuple(parameters)!=(*slot['slot'],'reserved_uncertain',2500000,self.record(start,slot)):
                    raise Denied('Reservation differs from approved immutable START')
            return execute(statement, parameters)
        connection.execute = constrained
        return connection

    def state(self):
        rows, facts, exposure, child = super().state()
        for outcome in (f for f in facts if f['kind']=='OUTCOME'):
            op=outcome['operation'];response=outcome['data']['response']
            try:
                dispatch=json.loads((self.directory/f'dispatch-{op}.json').read_bytes())
                raw=json.loads((self.directory/f'raw-{op}.json').read_bytes())
                decoded=json.loads((self.directory/f'decoded-{op}.json').read_bytes())
                grading=json.loads((self.directory/f'grading-{op}.json').read_bytes())
                original=b64decode(raw['bytesBase64'],validate=True)
                expected_status=decoder.Adapter('openai',None).decode(response)
                intent=next(f for f in facts if f['kind']=='INTENT' and f['operation']==op)
                if (dispatch!={'version':VERSION,'build':identity.MANIFEST_SHA,'operation':op,
                               'payloadHash':intent['data']['payloadHash'],'intentHash':intent['hash'],'syntheticOnly':True} or
                    set(raw)!={'bytesBase64','sha256'} or
                    raw['sha256']!=q1.sha(original) or _json(original)!=response or
                    decoded!={'rawSHA256':q1.sha(original),'responseHash':q1.digest(response),
                              'content':expected_status[0],'usage':list(expected_status[1]) if expected_status[1] else None,'status':expected_status[2]} or
                    grading!={'outcomeHash':outcome['hash'],'assessment':outcome['data']['assessment']}):
                    raise Denied('Immutable capture/decoding/grading mismatch')
            except (OSError,ValueError,KeyError,TypeError):
                raise Denied('Missing or corrupted capture evidence; no continuation') from None
        return rows,facts,exposure,child

    def simulate_one(self,permission,transport,now,*,crash_at=None):
        # All auth, review, scope, reservation, INTENT, uncertainty and HALT
        # checks are the frozen transition code, not caller-selected callbacks.
        identity.verify(full=True)
        if type(transport) is not SyntheticSend:
            raise Denied('Closed single-send transport required')
        candidates=identity.requests()
        envelope=parent.auth.parse(permission['envelope'].encode())
        requested=envelope['data']['payloadHash']
        expected=next((r for r in candidates if r['requestSHA256']==requested),None)
        if (expected is None or transport.payload!=expected['bytes'] or
                (transport.provider,transport.method,transport.endpoint)!=('openai','POST','/v1/responses')):
            raise Denied('Pre-reservation request mismatch')
        result = _simulate(self,permission,transport,now,crash_at=crash_at)
        with self.lock():
            _once(self.directory/f'grading-{result["operation"]}.json',
                  {'outcomeHash':result['hash'],'assessment':deepcopy(result['data']['assessment'])})
        return result


class SyntheticExecution:
    def __init__(self, trust):
        identity.verify(full=True)
        self.original=existing.inspect_original()  # Read-only, never authority.
        self.fixture=parent.SyntheticJournal(trust)
        REGISTRY[str(self.fixture.directory)]=identity.MANIFEST_SHA
        try:
            self.engine=AppendEngine(self.fixture.directory,trust)
        except Exception:
            self.close()
            raise

    def close(self):
        REGISTRY.pop(str(self.fixture.directory),None)
        self.fixture.close()
