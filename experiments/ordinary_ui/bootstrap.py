"""Disposable fake IdP key custody; never real Google or financial signing authority."""
import json,os
from pathlib import Path
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives import serialization
from experiments.hosted_identity import bootstrap as parent

def main():
 if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'} or os.environ.get('WHERETO_ENV','development') not in ('development','test') or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')):raise RuntimeError('Synthetic controller only')
 original=jwt.encode;templates={}
 def encode(payload,key,*args,**kwargs):
  if payload.get('iss')=='https://cloud.google.com/iap':
   name=payload['sub'].removeprefix('accounts.google.com:synthetic-')
   if name not in ('alice','bob','revoked') or kwargs.get('headers',{}).get('kid')!='task52-offline-iap':raise RuntimeError('Fixture identity scope')
   templates[name]=dict(claims={k:v for k,v in payload.items() if k not in ('iat','exp')},headers=kwargs['headers'])
   p=Path('/tmp/ui-fixture-iap.pem')
   if not p.exists():
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
  return original(payload,key,*args,**kwargs)
 with patch.object(jwt,'encode',encode):parent.main()
 fd=os.open('/tmp/ui-fixture-iap.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(templates,f)
if __name__=='__main__':main()
