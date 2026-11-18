"""Real dispatcher/counter callbacks; no startup selector or credential discovery.

Use only inside the existing authenticated roles. The caller must supply the
existing HTTPS, scoped secret and protected accounting dependencies. Neither a
configuration flag nor a returned token count is dispatch/spending authority.
No historical-evaluation module, model GET, fixture or alternate provider here.
"""
from base64 import b64encode, b64decode
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import re

from backend.ai.openai_candidate import MODEL, request_bytes
from backend.provider_enrollment_review import review_bound
from backend.provider_responses import (GoogleResponseAdapter, HTTPResult,
                                        ProviderResponseError, strict_object)
from private_runtime.https import Endpoint, HTTPS

VERSION = '52-real-provider-callbacks-v1'
ORIGIN = Endpoint('https://api.openai.com', 'https://api.openai.com')
EVALUATION_PROJECT = 'proj_E4EfEvC5uQYN4nqFaYZoo3I4'
COUNT_PATH = '/v1/responses/input_tokens'
GENERATE_PATH = '/v1/responses'


def digest(raw):
    return sha256(raw).hexdigest()


def generation_source(wire):
    """Accept only the source-pinned candidate template with its final user source.

    Reconstruct through the existing builder, not an approximate prompt/schema
    comparison. This does not validate model output or authorize the source.
    """
    if type(wire) is not bytes or not 1 <= len(wire) <= 100000:
        raise ProviderResponseError('application_request_bound')
    try:
        body = strict_object(wire)
        text = body['input'][-1]['content']
        if body['model'] != MODEL or request_bytes(text) != wire:
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError):
        raise ProviderResponseError('application_request_identity') from None
    return text


def count_payload(wire):
    generation_source(wire)
    body = strict_object(wire)
    # Same documented input-bearing projection as the frozen diagnostic, but
    # derived anew for EACH actual application request. Never reuse its count.
    return json.dumps({k: body[k] for k in ('model', 'input', 'text', 'reasoning')},
                      sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class OpenAIHTTP:
    """Fixed count/generation exchange over the existing verified HTTPS port.

    credential is an explicitly enrolled server-owned loader, NOT a key value,
    request field, environment lookup or historical evaluation credential. No
    endpoint argument, redirects, retries, model GET or generation fallback.
    Constructing this low-level dependency is not permission to invoke it.
    """
    def __init__(self, project, credential, transport=None, *, purpose):
        if (type(project) is not str or not re.fullmatch(r'proj_[A-Za-z0-9]{8,80}', project)
                or project == EVALUATION_PROJECT or not callable(credential)):
            raise ProviderResponseError('application_credential_enrollment')
        if purpose not in ('count', 'generation'):
            raise ProviderResponseError('openai_role_purpose')
        self._path = COUNT_PATH if purpose == 'count' else GENERATE_PATH
        self.project = project
        self._credential = credential
        self._http = transport if transport is not None else HTTPS(
            connections=1, deadline=120, request_limit=100000, response_limit=700000)

    def _post(self, path, wire):
        if path != self._path:
            raise ProviderResponseError('openai_operation')
        key = self._credential()
        if (type(key) is not str or not key.startswith('sk-') or
                any(c.isspace() for c in key)):
            raise ProviderResponseError('application_credential_refused')
        # Existing HTTPS is http.client based: no proxy/netrc/redirect/retry or
        # insecure fallback. Exceptions remain uncertain to the financial owner.
        raw = self._http.request(ORIGIN, 'POST', path, wire, {
            'Authorization': 'Bearer ' + key, 'OpenAI-Project': self.project,
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'Accept-Encoding': 'identity', 'Connection': 'close'})
        if type(raw) is not bytes or len(raw) > 700000 or key.encode() in raw or b'Bearer ' in raw or b'sk-' in raw:
            raise ProviderResponseError('credential_echo_refused')
        return HTTPResult(200, raw)

    def count(self, wire):
        projected = count_payload(wire)
        response = self._post(COUNT_PATH, projected)
        value = response.decode()
        if (type(value) is not dict or set(value) != {'object', 'input_tokens'} or
                value['object'] != 'response.input_tokens' or
                type(value['input_tokens']) is not int or not 1 <= value['input_tokens'] <= 100000):
            raise ProviderResponseError('application_count_response')
        return value['input_tokens'], response

    def generate(self, wire):
        generation_source(wire)
        return self._post(GENERATE_PATH, wire)


@dataclass(frozen=True)
class CountRecord:
    """Request-specific measurement, never a counter attestation or spending cap."""
    generation_sha256: str
    count_sha256: str
    raw_response_sha256: str
    tokens: int


class CounterCallback:
    """Counter-role algorithm around protected, independently supplied SQL ports.

    begin MUST durably consume the count operation and bind current source,
    admission, model/project, policy and epoch before any credential or I/O.
    commit MUST attest through the restricted counter role, not worker JSON.
    failure MUST retain uncertainty; no retry. The old byte-counter SQL does NOT
    implement this interface. No production opener is enrolled here. A missing
    authority therefore refuses construction; no memory substitute is selected.
    """
    def __init__(self, exchange, authority):
        if (exchange is None or authority is None or
                any(not callable(getattr(authority, n, None)) for n in ('begin', 'commit', 'uncertain'))):
            raise ProviderResponseError('protected_counter_authority_required')
        self.exchange, self.authority = exchange, authority

    def count(self, capability, wire):
        generation_source(wire)
        projected = count_payload(wire)
        operation = self.authority.begin(capability, wire, digest(projected), self.exchange.project)
        # Durable begin is outside try: its uncertain commit must never cause IO.
        try:
            tokens, raw = self.exchange.count(wire)
            record = CountRecord(digest(wire), digest(projected), raw.digest, tokens)
            self.authority.commit(operation, record, raw)
            return record
        except BaseException:
            self.authority.uncertain(operation)
            raise


class DispatcherCallback:
    """Final responder of owned_dispatch.dispatch / GrantService.send only.

    accounting.require MUST read the protected exact current SQL reservation and
    witness/profile; it cannot be supplied by an ordinary worker. The callback
    verifies provider-specific request/rate/count shape again, never substitutes
    byte counting. Google response facts are returned request-locally only.
    """
    def __init__(self, openai, google_exchange, accounting, clock):
        self.openai = openai
        self.google = GoogleResponseAdapter(google_exchange)
        self.accounting, self.clock = accounting, clock

    def dispatch(self, config, value):
        from private_runtime.owned_dispatch import dispatch
        return dispatch(config, value, self)

    def __call__(self, wire):
        body = strict_object(wire)
        provider = 'google' if type(body) is dict and 'operation' in body else 'openai'
        if provider == 'openai':
            generation_source(wire)
        # Trusted protected authority returns its policy/count and immutable
        # pre-send quote, not request-controlled rates or reported actual usage.
        enrolled = self.accounting.require(wire)
        if type(enrolled) is not dict or set(enrolled) != {'policy', 'count', 'reservedMicroUSD'}:
            raise ProviderResponseError('protected_reservation_required')
        policy = deepcopy(enrolled['policy'])
        if policy.get('provider') != provider:
            raise ProviderResponseError('reserved_provider_binding')
        if (provider == 'google' and getattr(self.accounting, 'profile', None) == '52-real-provider-finance-v1'
                and policy.get('account') != getattr(self.google._exchange, 'account', None)):
            raise ProviderResponseError('reserved_google_project_binding')
        if provider == 'openai' and policy.get('account') != self.openai.project:
            raise ProviderResponseError('reserved_project_binding')
        if getattr(self.accounting, 'profile', None) == '52-real-provider-finance-v1':
            # Trusted role dependency: bound() revalidates a protected SQL receipt
            # inside the committed-delivery context, including cache-write cost.
            bound = self.accounting.bound(wire, enrolled, self.clock())
        else:
            bound = review_bound(policy, wire, now=self.clock(), count=enrolled['count'])
        # Exact integer conservative quote, not an allowance supplied by caller.
        if (type(enrolled['reservedMicroUSD']) is not int or
                enrolled['reservedMicroUSD'] != bound.maximum_micro_usd):
            raise ProviderResponseError('protected_reservation_mismatch')
        if provider == 'google':
            return self.google(wire)
        response = self.openai.generate(wire)
        # JSON-safe exact raw bytes across the existing authenticated RPC. Do not
        # parse/re-serialize the provider body and pretend it is the raw response.
        return dict(provider='openai', bodyBase64=b64encode(response.body).decode(),
                    bodySHA256=response.digest)


def inference_response(value):
    """Factory-side response handoff into the existing AIProvider decoder."""
    if (type(value) is not dict or set(value) != {'provider', 'bodyBase64', 'bodySHA256'}
            or value['provider'] != 'openai' or type(value['bodyBase64']) is not str
            or len(value['bodyBase64']) > 933336):
        raise ProviderResponseError('inference_response_envelope')
    try:
        raw = b64decode(value['bodyBase64'], validate=True)
    except ValueError:
        raise ProviderResponseError('inference_response_envelope') from None
    if len(raw) > 700000 or digest(raw) != value['bodySHA256']:
        raise ProviderResponseError('inference_response_integrity')
    return HTTPResult(200, raw)
