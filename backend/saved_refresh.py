"""Explicit selected-option refresh. Only IDs/budgets survive the request."""
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
import os
import requests
from uuid import UUID
from pydantic import Field
from backend.models import ContractModel
from backend.saved_plans import OpenRequest, reopen, digest, PersistenceError
from backend.venue_details import contact_links
from backend.places import DiscoveryError, PROJECT
from backend.provider_budget import local_real_enabled, ProviderLimitError

# Pro, below the existing Enterprise contact-details mask; no hours/photos/ratings.
REFRESH_MASK='id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions'
CONTACT_REFRESH_MASK=REFRESH_MASK+',nationalPhoneNumber,internationalPhoneNumber,websiteUri'


class RefreshRequest(OpenRequest):
    refreshId: UUID
    candidateId: str = Field(min_length=1,max_length=200)
    includeContacts: bool = Field(default=False,strict=True)


def fetch_saved_details(identity, *, include_contacts=False):
    if not local_real_enabled() or os.environ.get('WHERETO_CONTACT_DETAILS_DEV')!='1':
        raise DiscoveryError('disabled','Venue refresh is disabled in this development session.')
    from backend.places_transport import access_token
    with requests.Session() as session:
        session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
        token=access_token(session)
        from backend.development_cost import dispatch
        dispatch('details',1)
        try:
            response=session.get('https://places.googleapis.com/v1/places/'+identity,
                headers={'Authorization':'Bearer '+token,'X-Goog-User-Project':PROJECT,'X-Goog-FieldMask':CONTACT_REFRESH_MASK if include_contacts else REFRESH_MASK},timeout=(5,15),allow_redirects=False)
            if response.status_code!=200:
                from backend.provider_errors import classify
                code,message,diagnostics=classify(response,'details')
                raise DiscoveryError(code,message)
            data=response.json()
            contact=contact_links(data,identity)
            credits=contact['attributions']
            name=data.get('displayName',{}).get('text')
            address=data.get('formattedAddress')
            status=data.get('businessStatus')
            if not isinstance(name,str) or not 1<=len(name.strip())<=200 or (address is not None and (not isinstance(address,str) or len(address)>1000)) or status not in (None,'OPERATIONAL','CLOSED_TEMPORARILY','CLOSED_PERMANENTLY'):
                raise ValueError()
            return {'name':name.strip(),'address':address,'businessStatus':status,'attributions':credits,
                    'refreshedAt':datetime.now(timezone.utc).isoformat(),
                    'mapsUrl':verified_maps_url(data.get('googleMapsUri')),
                    **({k:contact[k] for k in ('phone','telephoneUrl','website')} if include_contacts else {})}
        except (requests.RequestException,ValueError,TypeError,AttributeError):
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
        key=digest(request.accessToken)
        with self.lock:
            now=monotonic()
            self.entries=OrderedDict((k,v) for k,v in self.entries.items() if now-v[0]<1800)
            if key not in self.entries:
                if len(self.entries)>=50:raise ProviderLimitError('Local refresh session capacity reached. No provider request was made.')
                self.entries[key]=(now,budget.outing(),set())
            _,outing,attempted=self.entries[key]
        results={}
        for stop in option['stops']:
            identity=stop['reference']
            if identity in results:continue
            attempt=(str(request.refreshId),identity)
            with self.lock:
                if attempt in attempted:
                    results[identity]={'status':'already_attempted','message':'Already attempted in this session. No automatic retry.'};continue
                attempted.add(attempt)
            admitted=False
            try:
                with outing.reserve('details',str(request.refreshId)+':'+identity):
                    admitted=True
                    details=fetch_saved_details(identity,include_contacts=True) if request.includeContacts else fetch_saved_details(identity)
                results[identity]={'status':'refreshed',**details}
            except (DiscoveryError,ProviderLimitError) as error:
                if not admitted:
                    with self.lock:attempted.discard(attempt)
                from backend.failures import provider_code,MESSAGES,evidence
                code='venue_refresh_limit' if isinstance(error,ProviderLimitError) else provider_code(error)
                reference=evidence(code,'saved_refresh',exception=error)
                results[identity]={'status':'unavailable','message':MESSAGES.get(code,'Venue details unavailable; your saved stop is kept.'),'correlationId':reference}
                # Stop on quota/service/admission failure; do not fan out after rejection.
                if not admitted or getattr(error,'code','') in ('quota','authentication','permission','provider','timeout'):
                    break
        return {'candidateId':request.candidateId,'venues':results,'diagnostics':outing.usage()}

refresh_sessions=RefreshSessions()
