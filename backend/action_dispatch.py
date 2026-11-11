"""Inactive server-composition seam. No startup selector, issuer or HTTP client.

A separately constructed trusted local issuer may bind this context. Request
objects/digests are data, never authority by themselves. Normal startup is None.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json

_active = ContextVar('server_owned_provider_action', default=None)


@dataclass(frozen=True, repr=False)
class Request:
    canonical: bytes

    @classmethod
    def make(cls, operation, method, url, mask, body=None):
        value=dict(operation=operation,method=method,url=url,mask=mask,body=body)
        data=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(data)>65536:raise ValueError('Provider request too large')
        return cls(data)

    def value(self):return json.loads(self.canonical)

    @property
    def digest(self):return hashlib.sha256(self.canonical).hexdigest()


@contextmanager
def budget(outing, attempts, payloads):
    owner=_active.get()
    if owner is None:
        yield
    else:
        with owner.reserve(outing,attempts,payloads):yield


def send(request):
    owner=_active.get()
    return (False,None) if owner is None else (True,owner.dispatch(request))


def search(body, field_mask=None):
    if _active.get() is None:return None
    from backend.places import ENDPOINT,FIELD_MASK
    from backend.search_fields import search_mask
    mask=field_mask if field_mask is not None else search_mask(FIELD_MASK)+',places.containingPlaces'
    return Request.make('search','POST',ENDPOINT,mask,body)


def matrix(body):
    if _active.get() is None:return None
    from backend.routes import ENDPOINT,FIELD_MASK
    return Request.make('matrix','POST',ENDPOINT,FIELD_MASK,body)


def details(identity, mask):
    if _active.get() is None:return None
    return Request.make('details','GET','https://places.googleapis.com/v1/places/'+identity,mask)
