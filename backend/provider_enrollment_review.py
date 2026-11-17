"""Offline enrollment arithmetic/shape checks, NOT financial or dispatch authority.

No startup imports, network, credential discovery, SQL, grant or signature issuer.
Review records are untrusted data: independent verification and protected SQL
catalog/counter enrollment are still required. Never pass this result as a permit.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json,re
from backend.provider_responses import google_request,strict_object

DRAFT=Path(__file__).resolve().parents[1]/'deployment/real-provider-review-v1.json'
DRAFT_SHA='1314e57011a32a382d9e6908403a991fa6383f9584e3dbd1427d7f3c08b579a7'
MAX_MONEY=10**12  # micro-USD, matching existing SQL integer bound; not a grant.

class ReviewError(ValueError):pass

def integer(value,lo,hi):
    if type(value) is not int or not lo<=value<=hi:raise ReviewError('integer_bound')
    return value

def digest(value):return sha256(value).hexdigest()

def identifier(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value):raise ReviewError('review_identity')

def fingerprint(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise ReviewError('review_digest')

def window(checked,expires,now):
    integer(now,0,2**53);integer(checked,0,2**53);integer(expires,0,2**53)
    if not checked<=now<expires or not 0<expires-checked<=86400 or checked//86400!=now//86400:raise ReviewError('stale_review')

@dataclass(frozen=True)
class ReviewBound:
    """Review calculation only. Does not authenticate a counter or approve prices."""
    provider:str
    request_digest:str
    rate_version:str
    units:int
    maximum_micro_usd:int
    model_or_sku:str


def load_draft():
    raw=DRAFT.read_bytes()
    if digest(raw)!=DRAFT_SHA:raise ReviewError('draft_identity')
    value=strict_object(raw)
    if value['enabled'] is not False or value['dispatchAuthorized'] is not False:raise ReviewError('inactive_contract')
    for name,expected in value['sourcePins'].items():
        path=DRAFT.parents[1]/name
        if path.is_symlink() or digest(path.read_bytes())!=expected:raise ReviewError('source_identity')
    return value


def template_digest(body):
    value=deepcopy(body)
    if type(value.get('input')) is not list or not value['input'] or type(value['input'][-1]) is not dict or value['input'][-1].get('role')!='user' or type(value['input'][-1].get('content')) is not str:raise ReviewError('input_shape')
    value['input'][-1]['content']=''
    return digest(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def review_bound(policy,wire,*,now,count=None):
    """Validate proposed operator review data; never establishes its authenticity.

    Same-day/24h freshness is proposed for the first finite test, not an approved
    runtime policy. No actual-usage field is accepted in place of pre-send count.
    """
    common={'provider','account','version','checkedAt','expiresAt','priceEvidenceSHA256','rates'}
    if type(policy) is not dict:raise ReviewError('missing_policy')
    provider=policy.get('provider')
    extra=set() if provider=='google' else {'model','modelRevision','endpoint','templateSHA256','counterVersion','maxInput','maxOutput','inputMargin','costProfile'}
    if provider not in ('google','openai') or set(policy)!=common|extra:raise ReviewError('policy_shape')
    for key in ('account','version'):identifier(policy[key])
    fingerprint(policy['priceEvidenceSHA256']);window(policy['checkedAt'],policy['expiresAt'],now)
    if type(wire) is not bytes or len(wire)>100000:raise ReviewError('wire_bound')
    rates=policy['rates']
    if type(rates) is not dict:raise ReviewError('missing_prices')
    if provider=='google':
        if count is not None or set(rates)!={'search_pro','matrix_element','matrix_pro_element'}:raise ReviewError('maps_rates')
        for rate in rates.values():integer(rate,1,1000000)
        _,sku,units=google_request(wire)  # Existing exact method/mask/mode/dimensions.
        maximum=integer(units*rates[sku],0,MAX_MONEY)
    else:
        if set(rates)!={'inputMicroUsdPerMillion','outputMicroUsdPerMillion'}:raise ReviewError('llm_rates')
        for rate in rates.values():integer(rate,1,MAX_MONEY)
        if policy['model']!='gpt-6-luna' or policy['costProfile']!='input-output-only-reviewed-no-extras-v1':raise ReviewError('unbounded_cost_profile')
        fingerprint(policy['templateSHA256']);identifier(policy['counterVersion']);identifier(policy['modelRevision'])
        if policy['endpoint']!='https://api.openai.com/v1/responses':raise ReviewError('inference_endpoint')
        integer(policy['maxInput'],1,100000);integer(policy['maxOutput'],1,2000);integer(policy['inputMargin'],0,100000)
        body=strict_object(wire)
        if json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()!=wire:raise ReviewError('noncanonical_request')
        if type(body) is not dict or set(body)!={'model','input','temperature','reasoning','service_tier','max_output_tokens','store','text'}:raise ReviewError('inference_shape')
        if body['model']!=policy['model'] or body['reasoning']!={'effort':'none'} or body['service_tier']!='default' or body['store'] is not False:raise ReviewError('inference_profile')
        if template_digest(body)!=policy['templateSHA256']:raise ReviewError('application_template')
        output=integer(body['max_output_tokens'],1,policy['maxOutput'])
        if type(count) is not dict or set(count)!={'payloadSHA256','provider','account','model','modelRevision','counterVersion','inputTokens','checkedAt','expiresAt'}:raise ReviewError('complete_count_required')
        window(count['checkedAt'],count['expiresAt'],now)
        if count['payloadSHA256']!=digest(wire) or count['provider']!=provider or count['account']!=policy['account'] or count['modelRevision']!=policy['modelRevision'] or count['model']!=policy['model'] or count['counterVersion']!=policy['counterVersion']:raise ReviewError('count_binding')
        units=integer(count['inputTokens'],1,policy['maxInput'])+policy['inputMargin']
        if units>policy['maxInput']:raise ReviewError('input_bound')
        # Round EACH category up to micro-USD. Never release reserved exposure
        # from reported usage, cache discounts, failed requests or uncertainty.
        maximum=sum((tokens*rate+999999)//1000000 for tokens,rate in ((units,rates['inputMicroUsdPerMillion']),(output,rates['outputMicroUsdPerMillion'])))
        integer(maximum,0,MAX_MONEY)
    return ReviewBound(provider,digest(wire),policy['version'],units,maximum,sku if provider=='google' else policy['modelRevision'])
