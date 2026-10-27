"""Allowlisted Google error evidence. Never retain raw payloads or descriptions."""

def classify(response,operation):
    service='routes.googleapis.com' if operation=='matrix' else 'places.googleapis.com'
    category={'search':'Places search','lookup':'Starting-place search','details':'Place Details','matrix':'Routes'}[operation]
    reason=None;boundary='unknown';limit=None
    allowed={
        'search':{'SearchTextRequestPerDayPerProject':'daily','SearchTextRequestPerMinutePerProject':'minute'},
        'lookup':{'SearchTextRequestPerDayPerProject':'daily','SearchTextRequestPerMinutePerProject':'minute'},
        'details':{'GetPlaceRequestPerDayPerProject':'daily','GetPlaceRequestPerMinutePerProject':'minute'},
        'matrix':{'ComputeRouteMatrixElementsPerDayPerProject':'daily','ComputeRouteMatrixElementsPerMinutePerProject':'minute',
                  'ComputeRouteMatrixPerDayPerProject':'daily','ComputeRouteMatrixPerMinutePerProject':'minute'}
    }
    try:
        data=response.json();error=data.get('error',{}) if isinstance(data,dict) else {}
        for detail in error.get('details',[]):
            if not isinstance(detail,dict):continue
            metadata=detail.get('metadata',{})
            if not isinstance(metadata,dict):continue
            value=metadata.get('quota_limit')
            if value in allowed[operation]:limit=value;boundary=allowed[operation][value]
            if detail.get('reason') in ('RATE_LIMIT_EXCEEDED','QUOTA_EXCEEDED','BILLING_DISABLED','SERVICE_DISABLED','ACCESS_DENIED','IAM_PERMISSION_DENIED'):
                reason=detail['reason']
    except (ValueError,TypeError,AttributeError):pass
    code={400:'invalid_request',401:'authentication',403:'permission',429:'quota'}.get(response.status_code,'provider')
    if code=='quota':
        message=(f'{category} daily '+('element quota' if operation=='matrix' else 'quota')+' is exhausted. Stop and review Cloud usage.' if boundary=='daily' else
                 f'{category} per-minute '+('element limit' if operation=='matrix' else 'rate limit')+' was reached. Pause testing and review usage; no reset time is known.' if boundary=='minute' else
                 f'{category} quota or rate limit was reached. The provider did not identify which limit; review Cloud usage before continuing.')
    elif reason=='BILLING_DISABLED':message=f'{category} is unavailable because Google reports billing disabled. Review the existing billing configuration; no settings were changed.'
    elif code=='permission':message=f'{category} access was denied. Review existing API permissions and billing configuration.'
    elif code=='authentication':message=f'{category} authentication failed. Check the existing local credentials.'
    elif code=='invalid_request':message=f'Google rejected the {category.lower()} request. Review the permitted inputs.'
    else:message=f'{category} is unavailable. The provider cause could not be verified.'
    return code,message+' No automatic retry was made.',{'service':service,'requestCategory':operation,'httpStatus':response.status_code,'providerReason':reason,'quotaBoundary':boundary,'quotaLimit':limit}


def attach_accounting(error,outing):
    from backend.provider_budget import ProviderLimitError
    try:usage=outing.usage()
    except ProviderLimitError:
        usage={'providerAttempts':outing._requests,'placesSearchRequests':outing._searches,'reservedMatrixElements':outing._elements,'accountingUnavailable':True}
    error.diagnostics={**getattr(error,'diagnostics',{}),**usage}
    return error
