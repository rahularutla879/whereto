"""Bounded selected-option actions. Replay metadata only; no provider-content cache."""
from math import ceil
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
import os
import re
import requests
from uuid import UUID
from pydantic import Field
from backend.saved_plans import OpenRequest, reopen, digest, PersistenceError
from backend.venue_details import contact_links
from backend.places import DiscoveryError, PROJECT
from backend.provider_budget import local_real_enabled, ProviderLimitError

# Pro, below the existing Enterprise contact-details mask; no hours/photos/ratings.
REFRESH_MASK='id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions'
HOURS_REFRESH_FIELDS='timeZone,currentOpeningHours,regularOpeningHours'
CONTACT_REFRESH_MASK=REFRESH_MASK+',nationalPhoneNumber,internationalPhoneNumber,websiteUri'


class RefreshRequest(OpenRequest):
    refreshId: UUID
    candidateId: str = Field(min_length=1,max_length=200)
    includeContacts: bool = Field(default=False,strict=True)
    includeHours: bool = Field(default=False,strict=True)


def fetch_saved_details(identity, *, include_contacts=False, include_hours=False, outing_date=None, window_start=None, window_end=None, activity="food", calendar_timezone=None):
    if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', identity):
        raise PersistenceError(404)
    if include_hours and not saved_hours_enabled():raise DiscoveryError("disabled","Opening-hours loading is disabled in this development session.")
    if not local_real_enabled() or os.environ.get('WHERETO_CONTACT_DETAILS_DEV')!='1':
        raise DiscoveryError('disabled','Venue refresh is disabled in this development session.')
    mask=(CONTACT_REFRESH_MASK if include_contacts else REFRESH_MASK)+(','+HOURS_REFRESH_FIELDS if include_hours else '')
    from backend.action_dispatch import send,details as provider_request
    handled,data=send(provider_request(identity,mask))
    if handled:return data
    from backend.places_transport import access_token
    with requests.Session() as session:
        session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
        token=access_token(session)
        from backend.development_cost import dispatch
        dispatch('details',1,sku='details' if include_contacts or include_hours else 'details_pro')
        try:
            response=session.get('https://places.googleapis.com/v1/places/'+identity,
                headers={'Authorization':'Bearer '+token,'X-Goog-User-Project':PROJECT,'X-Goog-FieldMask':mask},timeout=(5,15),allow_redirects=False)
            if response.status_code!=200:
                from backend.provider_errors import classify
                code,message,diagnostics=classify(response,'details')
                if response.status_code==404:code='not_found'
                error=DiscoveryError(code,message)
                error.diagnostics=diagnostics
                raise error
            data=response.json()
            contact=contact_links(data,identity)
            credits=contact['attributions']
            name=data.get('displayName',{}).get('text')
            address=data.get('formattedAddress')
            status=data.get('businessStatus')
            if not isinstance(name,str) or not 1<=len(name.strip())<=200 or (address is not None and (not isinstance(address,str) or len(address)>1000)) or status not in (None,'OPERATIONAL','CLOSED_TEMPORARILY','CLOSED_PERMANENTLY'):
                raise ValueError()
            hours={}
            if include_hours:
                from datetime import date
                from backend.venue_normalization import normalize_google_place
                from backend.planning_hours import venue_hours
                fact=normalize_google_place(data,activity)
                hours={'hoursEvidence':venue_hours(fact,date.fromisoformat(outing_date),start=window_start,end=window_end,calendar_timezone=calendar_timezone)}
            return {**hours,'name':name.strip(),'address':address,'businessStatus':status,'attributions':credits,
                    'refreshedAt':datetime.now(timezone.utc).isoformat(),
                    'mapsUrl':verified_maps_url(data.get('googleMapsUri')),
                    **({k:contact[k] for k in ('phone','telephoneUrl','website')} if include_contacts else {})}
        except requests.Timeout:
            raise DiscoveryError('timeout','Venue details timed out. No automatic retry.') from None
        except requests.RequestException:
            raise DiscoveryError('provider','Venue service could not be reached. No automatic retry.') from None
        except (ValueError,TypeError,AttributeError):
            raise DiscoveryError('invalid_response','Current venue details could not be verified. No retry was made.') from None


def verified_maps_url(value):
    from urllib.parse import urlsplit
    try:
        parsed=urlsplit(value) if isinstance(value,str) and len(value)<=2048 else None
        if parsed and parsed.scheme=='https' and parsed.hostname in ('maps.google.com','www.google.com','maps.app.goo.gl') and not parsed.username and not parsed.password and not any(ord(c)<33 for c in value):
            return value
    except ValueError:pass
    return None


class RefreshSessions:
    def __init__(self):self.entries=OrderedDict();self.lock=Lock()
    def refresh(self,request,budget):
        document=reopen(OpenRequest(accessToken=request.accessToken)) # RLS/capability/expiry checked every action
        option=next((p for p in document['itineraries'] if p['candidateId']==request.candidateId),None)
        if not option or option['candidateId']!=document['selectedId'] or document['dataMode']!='real':raise PersistenceError(404)
        if not local_real_enabled() or os.environ.get('WHERETO_CONTACT_DETAILS_DEV')!='1':
            raise DiscoveryError('disabled','Venue refresh is disabled. The saved plan remains available.')
        if request.includeHours and not saved_hours_enabled():raise DiscoveryError('disabled','Opening-hours loading is disabled. Your saved plan is kept.')
        if not 1<=len(option['stops'])<=4:raise PersistenceError(404)
        from backend.planning_admission import guard_deferred
        guard_deferred()
        # A capability authorizes reading; it is not a lifetime provider quota.
        # Each explicit open/action gets a fresh bounded outing. The process and
        # durable ledger still admit every attempt across all viewers/links.
        action=(digest(request.accessToken),str(request.refreshId))
        with self.lock:
            now=monotonic()
            self.entries=OrderedDict((k,v) for k,v in self.entries.items() if now-v<1800)
            if action in self.entries:
                return {'candidateId':request.candidateId,'venues':{s['reference']:{'status':'already_attempted','message':'This detail-loading action was already attempted. No automatic retry.'} for s in option['stops']},'diagnostics':{}}
            if len(self.entries)>=512:
                error=ProviderLimitError('Shared replay registry capacity reached.',reason='session_capacity',retry_after=max(1,ceil(1800-(now-next(iter(self.entries.values()))))))
                return {'candidateId':request.candidateId,'venues':{option['stops'][0]['reference']:{'status':'unavailable',**refresh_issue(error)}},'diagnostics':{}}
            self.entries[action]=now
        outing=budget.outing()
        admitted_action=False
        results={}
        for stop in option['stops']:
            identity=stop['reference']
            if identity in results:continue
            admitted=False
            try:
                from backend.action_dispatch import details as provider_request
                mask=(CONTACT_REFRESH_MASK if request.includeContacts else REFRESH_MASK)+(','+HOURS_REFRESH_FIELDS if request.includeHours else '')
                with outing.reserve('details',digest(str(request.refreshId)+':'+identity), details_pro=not (request.includeContacts or request.includeHours),payload=provider_request(identity,mask)):
                    admitted=True
                    admitted_action=True
                    if request.includeHours:
                        constraints=document['constraints']
                        details=fetch_saved_details(identity,include_contacts=request.includeContacts,include_hours=True,
                            outing_date=constraints['date'],window_start=constraints['startTime'] if constraints.get('explicitStart') else None,
                            window_end=constraints['endTime'] if constraints.get('explicitEnd') else None,activity=stop['activity'],calendar_timezone=constraints.get('calendarTimezone'))
                    else:details=fetch_saved_details(identity,include_contacts=True) if request.includeContacts else fetch_saved_details(identity)
                results[identity]={'status':'refreshed',**details}
            except (DiscoveryError,ProviderLimitError) as error:
                from backend.failures import provider_code,evidence
                code='venue_refresh_limit' if isinstance(error,ProviderLimitError) else provider_code(error)
                reference=evidence(code,'saved_refresh',exception=error)
                issue=refresh_issue(error)
                results[identity]={'status':'unavailable',**issue,'correlationId':reference}
                # Stop on quota/service/admission failure; do not fan out after rejection.
                if not admitted or getattr(error,'code','') in ('quota','authentication','permission','provider','timeout'):
                    break
        if not admitted_action:
            with self.lock:self.entries.pop(action,None)
        try:usage=outing.usage()
        except ProviderLimitError:usage={'accountingUnavailable':True}
        return {'candidateId':request.candidateId,'venues':results,'diagnostics':usage}

refresh_sessions=RefreshSessions()


def automatic_details_enabled():
    """Separate owner approval; manual contact authorization never implies this."""
    return (local_real_enabled() and os.environ.get('WHERETO_CONTACT_DETAILS_DEV')=='1'
            and os.environ.get('WHERETO_SAVED_AUTO_DETAILS_DEV')=='1')


def refresh_issue(error):
    """Only fixed public explanations; no provider payload or sensitive exception text."""
    reason=getattr(error,'reason',None)
    retry=getattr(error,'retry_after',None)
    if isinstance(error,ProviderLimitError):
        if reason=='capability_allowance':
            reason='action_allowance';message='This detail-loading action exceeds its configured request allowance.'
        elif reason in ('local_minute','local_shared_minute'):
            message='The shared local Place Details minute limit is reached. Other saved links use this same limit.'
        elif reason=='concurrent_request':message='Another provider request is running. Wait for it to finish, then retry.'
        elif reason=='session_capacity':message='Shared detail-action capacity is reached. Try after an active action record expires.'
        elif 'accounting' in str(error).lower():reason='local_accounting';message='Local usage accounting is unavailable. Check the private ledger; your saved plan is kept.'
        elif 'daily estimated spending' in str(error).lower():reason='local_daily_allowance';message='The shared application daily spending allowance is reached. Review local usage.'
        else:reason='application_allowance';message='The shared application request allowance is reached. Review usage before continuing.'
    else:
        code=getattr(error,'code','provider')
        boundary=getattr(error,'diagnostics',{}).get('quotaBoundary','unknown')
        reason={'authentication':'provider_authentication','permission':'provider_authorization','invalid_response':'invalid_provider_response','not_found':'place_unavailable','timeout':'provider_timeout'}.get(code,'provider_service')
        if code=='quota':
            reason='cloud_'+boundary+'_quota'
            message={'daily':'Google reports its shared daily Place Details quota is exhausted. Review Cloud usage.', 'minute':'Google reports a Place Details rate limit. Pause and review Cloud usage.'}.get(boundary,'Google rejected Place Details for an unspecified quota or rate limit. Review Cloud usage.')
        else:message={'authentication':'Google authentication failed. Check the local provider credentials.','permission':'Google denied Place Details access. Check existing authorization.','not_found':'Google reports this saved place is unavailable. The original stop is kept.','timeout':'Google did not respond in time. Your saved plan is kept.','invalid_response':'The returned venue details could not be verified.'}.get(code,'The venue service is unavailable. Your saved plan is kept.')
    result={'reason':reason,'message':message,'retryable':reason not in ('cloud_daily_quota','cloud_unknown_quota','provider_authentication','provider_authorization','local_accounting','local_daily_allowance','application_allowance')}
    if retry is not None:result['retryAfterSeconds']=max(1,min(1800,int(retry)))
    return result


def saved_hours_enabled():
    return local_real_enabled() and os.environ.get('WHERETO_SAVED_HOURS_DEV')=='1' and os.environ.get('WHERETO_CONTACT_DETAILS_DEV')=='1'
