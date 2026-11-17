"""Google Place-ID-only cache on existing encrypted Redis; NEVER session evidence.

Only the published identifier exception is used. Names, coordinates, route facts,
raw responses and attribution are NOT stored here. Full recovery remains blocked.
No provider calls, financial operations, credentials or new storage service.
"""
from hashlib import sha256
import json,secrets,base64
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,StringConstraints,ValidationError
from experiments.shared_state.contracts import Denied

PlaceId=Annotated[str,StringConstraints(strict=True,min_length=1,max_length=256,pattern=r'^[A-Za-z0-9_-]+$')]
class GoogleReferences(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True)
    kind:Literal['google-place-identifiers-only-v1']='google-place-identifiers-only-v1'
    place_ids:tuple[PlaceId,...]=Field(min_length=1,max_length=100)
    def require_checkpoint(self):raise Denied('google_identifiers_cannot_restore_planning')


def references_from_search(value):
    """Explicit ID projection, never a lossy replacement for a native checkpoint."""
    if type(value) is not dict or type(value.get('places')) is not list:raise Denied('google_reference_shape')
    ids=[]
    for row in value['places']:
        if type(row) is not dict or type(row.get('id')) is not str:raise Denied('google_reference_shape')
        if row['id'] not in ids:ids.append(row['id'])
    try:return GoogleReferences(place_ids=tuple(ids))
    except ValidationError:raise Denied('google_reference_shape') from None


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

class ReferenceCache:
    """Optional non-authoritative cache. Not enrolled by any normal startup.

    store.meta checks current SQL source/revision/fence/expiry before and after IO.
    Existing Redis CAS/limits and key rotation are reused; IDs cannot grant work.
    """
    def __init__(self,store,lease):
        self.store,self.lease,self.redis=store,lease,store.evidence
        self.meta=store.meta(lease);self.epoch=store.current_epoch()
        self.environment=getattr(getattr(self.redis,'c',None),'environment','synthetic')
        self.path=self.redis.path(self.environment,self.epoch,sha256(canonical(['google-identifiers-only',self.meta['session'],self.meta['revision']])).hexdigest())
    def current(self):
        if self.store.current_epoch()!=self.epoch or self.store.meta(self.lease)!=self.meta:raise Denied('google_reference_source_changed')
    def now(self):
        seconds,micros=self.redis._run(self.redis.client.time)
        return seconds*1000+micros//1000
    def put(self,references):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if type(references) is not GoogleReferences:raise Denied('google_reference_type')
        try:references=GoogleReferences.model_validate_json(references.model_dump_json(warnings=False))
        except (ValueError,TypeError):raise Denied('google_reference_type') from None
        self.current();now=self.now();expires=min(now+600000,self.meta['expires_ms'])
        if expires<=now:raise Denied('google_reference_expired')
        kid=self.redis.keys.active;header={'kind':references.kind,'key_id':kid,'expires_ms':expires,'epoch':self.epoch,'environment':self.environment}
        nonce=secrets.token_bytes(12);sealed=nonce+AESGCM(self.redis.keys.key(kid)).encrypt(nonce,canonical(references.model_dump(mode='json')),canonical({'header':header,'source':self.meta}))
        blob=canonical({'header':header,'sealed':base64.b64encode(sealed).decode()})
        self.redis.publish(self.path,None,blob,expires)  # create-only: never renew TTL
        try:self.current()
        except BaseException:self.forget();raise
    def get(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag
        self.current();raw=self.redis.get(self.path)
        try:
            value=json.loads(raw);header=value['header']
            if set(value)!={'header','sealed'} or set(header)!={'kind','key_id','expires_ms','epoch','environment'} or header['kind']!='google-place-identifiers-only-v1' or header['epoch']!=self.epoch or header['environment']!=self.environment:raise ValueError()
            if type(header['expires_ms']) is not int or not self.now()<header['expires_ms']<=self.meta['expires_ms']:raise ValueError()
            sealed=base64.b64decode(value['sealed'],validate=True)
            data=AESGCM(self.redis.keys.key(header['key_id'])).decrypt(sealed[:12],sealed[12:],canonical({'header':header,'source':self.meta}))
            result=GoogleReferences.model_validate_json(data)
        except (ValueError,KeyError,TypeError,InvalidTag):raise Denied('google_reference_integrity') from None
        self.current();return result
    def forget(self):
        # Only this captured owned key. PEXPIREAT avoids adding a new DEL ACL right.
        prefix=self.path.rsplit(':',1)[0]
        self.redis._run(lambda:self.redis.client.eval("redis.call('PEXPIREAT',KEYS[1],1);redis.call('ZREM',KEYS[2],KEYS[1]);redis.call('HDEL',KEYS[3],KEYS[1]);return 1",3,self.path,prefix+':index',prefix+':sizes'))
