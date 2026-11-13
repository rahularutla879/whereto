"""Fixed test DNS only. TLS still verifies the original enrolled hostname."""
import socket,os
from pathlib import Path

def install():
 if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'} or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or os.environ.get('WHERETO_ENV')=='production':raise RuntimeError('Fixture DNS only')
 original=socket.getaddrinfo;names={p+'.task52.invalid' for p in ('frontend','factory','counter','dispatcher','recovery','worker-a','worker-b')}
 def resolve(host,*a,**k):return original('127.0.0.1' if host in names else host,*a,**k)
 socket.getaddrinfo=resolve
