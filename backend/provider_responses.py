"""Inactive Google response adapter for the existing protected dispatch callback.

No credential discovery, retry, startup selector or financial authority here.
The trusted dispatcher supplies its single-send exchange AFTER GrantService.send.
Recorded exchanges exercise this same codec offline. Raw bodies stay request-local;
no real provider response is admitted to Redis by this module.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from time import monotonic

from backend.action_dispatch import Request
from backend.places import ENDPOINT as SEARCH_URL, FIELD_MASK as SEARCH_MASK
from backend.routes import ENDPOINT as MATRIX_URL, FIELD_MASK as MATRIX_MASK
from backend.routes_transport import _validate_basic_body

VERSION = '52-real-provider-response-port-v1'
MAX_RESPONSE = 1048576


class ProviderResponseError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)  # Never include request, credential or response text.


def strict_object(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate')
            value[key] = item
        return value
    def finite(value):
        number = float(value)
        if not isfinite(number):
            raise ValueError('nonfinite')
        return number
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=finite,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, TypeError):
        raise ProviderResponseError('invalid_provider_json') from None


@dataclass(frozen=True, repr=False)
class HTTPResult:
    status: int
    body: bytes
    complete: bool = True
    content_type: str = 'application/json'

    @property
    def digest(self):
        return sha256(self.body).hexdigest()

    def decode(self):
        if (type(self.body) is not bytes or len(self.body) > MAX_RESPONSE or
                type(self.status) is not int or self.status != 200 or
                self.complete is not True or type(self.content_type) is not str or
                self.content_type.split(';')[0].strip() != 'application/json'):
            raise ProviderResponseError('provider_response_refused')
        return strict_object(self.body)


def google_request(payload):
    """Canonical method/endpoint/mask and SKU units, never authorization.

    The issuer has already proved the body against the owned action. This repeats
    the selected-operation checks; it does not infer source authority from a hash.
    """
    if type(payload) is not bytes or len(payload) > 65536:
        raise ProviderResponseError('provider_request_refused')
    v = strict_object(payload)
    if type(v) is not dict or set(v) != {'operation', 'method', 'url', 'mask', 'body'}:
        raise ProviderResponseError('provider_request_refused')
    if Request.make(v['operation'], v['method'], v['url'], v['mask'], v['body']).canonical != payload:
        raise ProviderResponseError('noncanonical_request')
    if v['method'] != 'POST' or type(v['body']) is not dict:
        raise ProviderResponseError('provider_request_refused')
    if v['operation'] == 'search':
        if v['url'] != SEARCH_URL or v['mask'] not in (SEARCH_MASK, SEARCH_MASK + ',places.containingPlaces'):
            raise ProviderResponseError('unreviewed_search_mask')
        body = v['body']
        # Initial ordinary discovery only; pagination/Details/Enterprise stay shut.
        if (set(body) - {'textQuery', 'pageSize', 'languageCode', 'locationBias',
                         'locationRestriction', 'includedType', 'strictTypeFiltering'} or
                type(body.get('textQuery')) is not str or not 1 <= len(body['textQuery']) <= 1000 or
                type(body.get('pageSize')) is not int or not 1 <= body['pageSize'] <= 10 or
                body.get('languageCode') != 'en'):
            raise ProviderResponseError('unreviewed_search_body')
        from backend.venue_models import Coordinates
        try:
            if ('locationBias' in body) == ('locationRestriction' in body):
                raise ValueError()
            key = 'locationBias' if 'locationBias' in body else 'locationRestriction'
            region = body[key]
            if type(region) is not dict or len(region) != 1:
                raise ValueError()
            if set(region) == {'circle'} and key == 'locationBias':
                circle = region['circle']
                if set(circle) != {'center','radius'} or type(circle['radius']) not in (int,float) or not 0 <= circle['radius'] <= 50000:
                    raise ValueError()
                Coordinates.model_validate(circle['center'])
            elif set(region) == {'rectangle'}:
                rectangle = region['rectangle']
                if set(rectangle) != {'low','high'}:
                    raise ValueError()
                low = Coordinates.model_validate(rectangle['low'])
                high = Coordinates.model_validate(rectangle['high'])
                if low.latitude > high.latitude:
                    raise ValueError()
            else:
                raise ValueError()
            if 'strictTypeFiltering' in body and type(body['strictTypeFiltering']) is not bool:
                raise ValueError()
            if 'includedType' in body and (type(body['includedType']) is not str or not 1 <= len(body['includedType']) <= 100):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise ProviderResponseError('unreviewed_search_geography') from None
        return v, 'search_pro', 1
    if v['operation'] == 'matrix':
        if v['url'] != MATRIX_URL or v['mask'] != MATRIX_MASK:
            raise ProviderResponseError('unreviewed_matrix_mask')
        _validate_basic_body(v['body'])
        units = len(v['body']['origins']) * len(v['body']['destinations'])
        if not 1 <= units <= 300:
            raise ProviderResponseError('matrix_unit_bound')
        return v, 'matrix_pro_element' if v['body']['travelMode'] == 'DRIVE' else 'matrix_element', units
    raise ProviderResponseError('unsupported_provider_operation')


class GoogleResponseAdapter:
    """Callable used as GrantService.send's final response callback.

    exchange receives the exact canonical Request and derived SKU/units. Only a
    trusted dispatcher may supply a network implementation; none is enrolled in
    this repository. A worker must not receive this dependency. It is not a grant.
    """
    def __init__(self, exchange=None):
        self._exchange = exchange

    def dispatch(self, config, value):
        """Use existing authenticated owner routing and durable delivery checks.

        This is an inactive composition port, never a public operation. Missing
        exchange refuses before callback routing and never discovers credentials.
        """
        if self._exchange is None:
            raise ProviderResponseError('real_provider_enrollment_required')
        from private_runtime.owned_dispatch import dispatch
        return dispatch(config, value, self)

    def __call__(self, payload):
        value, sku, units = google_request(payload)
        if self._exchange is None:
            raise ProviderResponseError('real_provider_enrollment_required')
        result = self._exchange(payload, sku, units)  # Once only; no catch/retry.
        if type(result) is not HTTPResult:
            raise ProviderResponseError('provider_response_type')
        data = result.decode()
        expected = dict if value['operation'] == 'search' else list
        if type(data) is not expected or isinstance(data, dict) and 'error' in data:
            raise ProviderResponseError('provider_response_shape')
        # Existing PlacesDiscovery/GoogleRouteCalculator perform semantic parsing.
        return data


def real_inference_accounting(*_args, **_kwargs):
    """No byte-to-token conversion or worker-supplied price can authorize OpenAI."""
    raise ProviderResponseError('missing_reviewed_model_count_rate_and_grant')


class GoogleHTTPExchange:
    """Single HTTPS send with dispatcher-injected OAuth; never discovers Mac ADC.

    Construct only inside the separately reviewed dispatcher enrollment. The
    ordinary worker must not receive token_provider. No startup imports this port.
    A session factory substitutes HTTP in offline tests; URLs/masks are fixed.
    """
    def __init__(self, token_provider=None, *, session_factory=None):
        self._token = token_provider
        self._sessions = session_factory

    def __call__(self, payload, sku, units):
        import requests
        from backend.places import PROJECT
        value, derived_sku, derived_units = google_request(payload)
        if sku != derived_sku or type(units) is not int or units != derived_units:
            raise ProviderResponseError('provider_unit_binding')
        if self._token is None:
            raise ProviderResponseError('workload_oauth_not_enrolled')
        with (self._sessions or requests.Session)() as session:
            session.trust_env = False  # No host proxy, netrc or local credential fallback.
            session.verify = True
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))
            token = self._token(session)  # Trusted dispatcher dependency, no default.
            if type(token) is not str or not token or any(c.isspace() for c in token):
                raise ProviderResponseError('workload_oauth_refused')
            body = json.dumps(value['body'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            captured = bytearray()
            status = 0
            media = 'application/json'
            began = monotonic()
            try:
                with session.post(value['url'], data=body, timeout=(5, 15),
                        allow_redirects=False, stream=True,
                        headers={'Authorization':'Bearer '+token, 'X-Goog-User-Project':PROJECT,
                                 'X-Goog-FieldMask':value['mask'], 'Content-Type':'application/json',
                                 'Accept-Encoding':'identity'}) as response:
                    status = response.status_code
                    media = response.headers.get('Content-Type','')
                    length = response.headers.get('Content-Length')
                    if (response.headers.get('Content-Encoding','identity') != 'identity' or
                            length is not None and (not length.isdigit() or int(length) > MAX_RESPONSE)):
                        raise ProviderResponseError('provider_response_bound')
                    for chunk in response.iter_content(chunk_size=65536):
                        if monotonic() - began > 20:
                            return HTTPResult(status, bytes(captured), False, media)
                        captured.extend(chunk)
                        if len(captured) > MAX_RESPONSE:
                            raise ProviderResponseError('provider_response_bound')
                    if monotonic() - began > 20 or length is not None and len(captured) != int(length):
                        return HTTPResult(status, bytes(captured), False, media)
                return HTTPResult(status, bytes(captured), True, media)
            except requests.RequestException:
                # A timeout may follow a successful send: no retry/refund, and the
                # existing reservation owner handles UNCERTAIN/quarantine.
                return HTTPResult(status, bytes(captured), False, media)
