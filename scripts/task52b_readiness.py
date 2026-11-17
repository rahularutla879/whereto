"""Inactive first-slot readiness checks. No credential loader or network client.

Only fictional HTTPResult fixtures can exercise the two-request protocol today.
Reuse existing exclusive/fsynced evidence writes; never open the paid journal.
Quotes and counts are review data, not SQL/counter/dispatch authorization.
"""
from base64 import b64encode
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re

from scripts import task52b_prepare_openai as prepared
from scripts.task52_q4a import private_create
from backend.provider_responses import HTTPResult, ProviderResponseError, strict_object

VERSION = '52b-first-slot-readiness-preparation-v1'
MODEL = 'gpt-6-luna'
ORIGIN = 'https://api.openai.com'
REQUEST_SHA = '5c2ad0aa457ae84497f489a1ca155ce805c8f160fd5260f59e0a4a3e8a078c02'
COUNT_SHA = '70939877e0df3fca79fb68cab25d5449ae2533ec31892ed91b762ddbd2c8e6d1'
CEILING_NANO = 2_500_000  # Existing conditional proposal, NOT an allowance.
MAX_INPUT = 12_000
MARGIN = 2_048
MAX_OUTPUT = 2_000
RATE_KEYS = {'input', 'cached_input', 'cache_write_30m', 'cache_write_12h', 'output'}
EXTRA_KEYS = {'tools', 'separate_reasoning', 'other_fees'}

class Refused(ValueError): pass


def integer(n, low, high):
    if type(n) is not int or not low <= n <= high:
        raise Refused('integer_bound')
    return n


def fingerprint(s):
    if type(s) is not str or len(s) != 64 or any(c not in '0123456789abcdef' for c in s):
        raise Refused('evidence_identity')
    return s


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    body: bytes


def requests():
    """Exact documented input-bearing projection, not a new generation payload."""
    prepared.verify_artifacts()
    r = prepared.prepare()[0]
    raw = (prepared.ARTIFACTS / r['countFile']).read_bytes()
    if r['requestSHA256'] != REQUEST_SHA or sha256(raw).hexdigest() != COUNT_SHA:
        raise Refused('frozen_payload')
    # Generation-only controls (e.g. max_output_tokens) are not count fields.
    if set(strict_object(raw)) != {'model', 'input', 'text', 'reasoning'}:
        raise Refused('count_schema')
    return (Request('GET', ORIGIN + '/v1/models/' + MODEL, b''),
            Request('POST', ORIGIN + '/v1/responses/input_tokens', raw))


def validate_response(request, response):
    """Count API does not echo a model; bind it to the exact outbound request."""
    pair = requests()
    if type(request) is not Request or request not in pair:
        raise Refused('request_substitution')
    if type(response) is not HTTPResult:
        raise Refused('response_type')
    if response.status in (401, 403):
        raise Refused('permission_denied_no_permission_change')
    try:
        value = response.decode()
    except ProviderResponseError:
        raise Refused('http_or_json_refusal') from None
    if type(value) is not dict:
        raise Refused('response_shape')
    if request == pair[0]:
        # Keep additional provider metadata verbatim, not as authority.
        if (value.get('object') != 'model' or value.get('id') != MODEL or
                type(value.get('created')) is not int or value['created'] < 0 or
                type(value.get('owned_by')) is not str or not value['owned_by']):
            raise Refused('model_identity')
        return {'model': MODEL, 'responseSHA256': response.digest}
    if set(value) != {'object', 'input_tokens'} or value['object'] != 'response.input_tokens':
        raise Refused('count_response_shape')
    tokens = integer(value['input_tokens'], 1, MAX_INPUT - MARGIN)
    return {'model': MODEL, 'generationSHA256': REQUEST_SHA, 'countSHA256': COUNT_SHA,
            'inputTokens': tokens, 'inputBound': tokens + MARGIN,
            'responseSHA256': response.digest, 'financialAuthorization': False}


class ReadinessTransport:
    """Real construction refuses even unsigned approved=true packets."""
    def __init__(self, enrollment=None, *, credential=None):
        raise Refused('real_readiness_enrollment_unavailable')


class FictionalReadiness:
    """Disposable fixture scope; immutable consumption survives runner replacement.

    Not an operational enrollment, general ledger, or adversarial OS sandbox.
    No caller callback/URL/key is accepted, and no request can leave this process.
    """
    def __init__(self, responses):
        if type(responses) is not tuple or len(responses) != 2 or any(type(x) not in (HTTPResult, type(None)) for x in responses):
            raise Refused('fictional_responses_only')
        self.responses = responses
        self.temp = TemporaryDirectory(prefix='whereto-readiness-fictional-')
        self.directory = Path(self.temp.name)
        self.directory.chmod(0o700)
        self.sent = []
    def close(self): self.temp.cleanup()
    def run(self):
        pair = requests()
        try:
            private_create(self.directory / 'scope-consumed.json',
                           {'version': VERSION, 'fixtureOnly': True, 'requests': [
                               {'method': r.method, 'url': r.url, 'bodySHA256': sha256(r.body).hexdigest()} for r in pair],
                            'permissionProfile': {'listModels': 'Read', 'responses': 'Read', 'unrelated': 'None'}})
        except FileExistsError:
            raise Refused('replay_or_uncertain_prior_attempt') from None
        results = []
        for i, (r, response) in enumerate(zip(pair, self.responses), 1):
            private_create(self.directory / f'intent-{i}.json',
                           {'method': r.method, 'url': r.url, 'bodySHA256': sha256(r.body).hexdigest(), 'fixtureOnly': True})
            self.sent.append(r)
            if response is None:
                raise Refused('uncertain_response_no_retry')
            if type(response.body) is not bytes or len(response.body) > 1048576:
                raise Refused('response_bound')
            private_create(self.directory / f'raw-{i}.json',
                           {'status': response.status, 'complete': response.complete,
                            'contentType': response.content_type,
                            'bodyBase64': b64encode(response.body).decode(), 'sha256': response.digest})
            results.append(validate_response(r, response))
        return {'fixtureValidated': True, 'financialAuthorization': False, 'results': results}


def conservative_quote(count, *, project, model_revision, prices, now, extras, uplift_bps,
                       output_limit=MAX_OUTPUT):
    """Pure review arithmetic. Price/account evidence is not authenticated here.

    The frozen payload omits cache TTL/breakpoints: documented default is30m.
    Cache writes REPLACE ordinary input rates, not add to them. Reserve the
    highest applicable input/read/30m-write rate; never assume a cache hit.
    Output covers visible, reasoning and formatting tokens within the API cap.
    Unknown fees/premiums refuse. Round each category UP to integer nanodollars.
    """
    required = {'project', 'model', 'modelRevision', 'generationSHA256', 'countSHA256', 'inputTokens', 'checkedAt', 'expiresAt'}
    if type(count) is not dict or set(count) != required or count['model'] != MODEL or count['generationSHA256'] != REQUEST_SHA or count['countSHA256'] != COUNT_SHA:
        raise Refused('complete_count_binding')
    if type(project) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', project) or count['project'] != project:
        raise Refused('account_scope')
    if type(model_revision) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', model_revision) or count['modelRevision'] != model_revision:
        raise Refused('model_revision')
    def fresh(record):
        t = integer(now, 0, 2**53)
        a = integer(record['checkedAt'], 0, 2**53)
        b = integer(record['expiresAt'], 0, 2**53)
        if not a <= t < b or b-a > 86400 or a//86400 != t//86400:
            raise Refused('stale_evidence')
    fresh(count)
    keys = {'project', 'model', 'modelRevision', 'ratesNanoPerMillion', 'sourceSHA256', 'checkedAt', 'expiresAt'}
    if type(prices) is not dict or set(prices) != keys or prices['model'] != MODEL or prices['modelRevision'] != model_revision or prices['project'] != project:
        raise Refused('unknown_prices')
    fingerprint(prices['sourceSHA256']);fresh(prices)
    rates = prices['ratesNanoPerMillion']
    if type(rates) is not dict or set(rates) != RATE_KEYS:
        raise Refused('unknown_price_categories')
    for rate in rates.values(): integer(rate, 1, 10**12)
    if type(extras) is not dict or set(extras) != EXTRA_KEYS:
        raise Refused('unknown_extra_categories')
    for fee in extras.values(): integer(fee, 0, 10**12)
    integer(uplift_bps, 0, 10000)
    output = integer(output_limit, 1, MAX_OUTPUT)
    if output != prepared.prepare()[0]['request']['max_output_tokens']:
        raise Refused('frozen_output_limit')
    n = integer(count['inputTokens'], 1, MAX_INPUT-MARGIN) + MARGIN
    up = lambda a,b: (a+b-1)//b
    # The exact frozen body has no top-level or content-block TTL overrides.
    body = prepared.prepare()[0]['request']
    if set(body) != {'model','input','temperature','reasoning','service_tier','max_output_tokens','store','text'} or any(type(m.get('content')) is not str for m in body['input']):
        raise Refused('cache_configuration')
    input_rate = max(rates['input'], rates['cached_input'], rates['cache_write_30m'])
    input_cost = up(n * input_rate, 10**6)
    output_cost = up(output * rates['output'], 10**6)
    subtotal = input_cost + output_cost + sum(extras.values())
    uplift = up(subtotal * uplift_bps, 10000)
    total = subtotal + uplift
    if total > 10**12: raise Refused('money_overflow')
    return {'inputBound': n, 'maxOutputTokens': output, 'inputNanodollars': input_cost,
            'inputRateNanoPerMillion': input_rate, 'cacheTTL': '30m',
            'cacheWrite12hApplicable': False, 'outputNanodollars': output_cost,
            'extraNanodollars': sum(extras.values()), 'upliftNanodollars': uplift,
            'maximumNanodollars': total, 'proposedCeilingNanodollars': CEILING_NANO,
            'withinProposedCeiling': total <= CEILING_NANO, 'approved': False,
            'financialAuthorization': False}
