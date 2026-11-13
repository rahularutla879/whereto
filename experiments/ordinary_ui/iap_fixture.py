"""Fixed fictional testers, same600s lifetime; controller CLI only, no HTTP signer."""
import json,os,sys,time
from pathlib import Path
import jwt
from cryptography.hazmat.primitives import serialization

def main():
 if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'} or os.environ.get('WHERETO_ENV','development') not in ('development','test') or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or len(sys.argv)!=2 or sys.argv[1] not in ('alice','bob','revoked'):raise RuntimeError('Synthetic controller only')
 doc=json.loads(Path('/tmp/ui-fixture-iap.json').read_text())[sys.argv[1]];now=int(time.time())
 key=serialization.load_pem_private_key(Path('/tmp/ui-fixture-iap.pem').read_bytes(),None)
 print(jwt.encode({**doc['claims'],'iat':now,'exp':now+600},key,algorithm='ES256',headers=doc['headers']))
if __name__=='__main__':main()
