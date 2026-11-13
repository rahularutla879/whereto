"""Loopback fictional IAP edge only; separate from the Docker-free Next process."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import http.client,json,time,secrets,sys
from pathlib import Path
import jwt
from cryptography.hazmat.primitives import serialization
import os
if not Path('/.dockerenv').exists() or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or os.environ.get('WHERETO_ENV')=='production':raise RuntimeError('Offline IAP fixture only')
root,upstream,port=Path(sys.argv[1]),sys.argv[2],int(sys.argv[3])
key=serialization.load_pem_private_key((root/'iap.pem').read_bytes(),None);doc=json.loads((root/'iap.json').read_text())['alice'];cookie=secrets.token_hex(32)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):self.run_request()
 def do_POST(self):self.run_request()
 def run_request(self):
  if any(self.headers.get(k) for k in ('Authorization','X-Serverless-Authorization','X-Goog-IAP-JWT-Assertion','X-Whereto-Context','X-Whereto-User')):self.send_error(403);return
  if self.path.startswith('/api/') and 'network-ui='+cookie not in self.headers.get('Cookie','').split('; '):self.send_error(403);return
  n=int(self.headers.get('Content-Length','0'))
  if n>65536 or self.headers.get('Transfer-Encoding'):self.send_error(413);return
  body=self.rfile.read(n);h={'Content-Type':'application/json'}
  if self.command=='POST':
   if self.headers.get('Origin')!='http://'+self.headers.get('Host',''):self.send_error(403);return
   h['Origin']='https://frontend-task52-offline.run.app'
  now=int(time.time());h['X-Goog-IAP-JWT-Assertion']=jwt.encode({**doc['claims'],'iat':now,'exp':now+600},key,algorithm='ES256',headers=doc['headers'])
  c=http.client.HTTPConnection(upstream,8080,timeout=120)
  try:
   c.request(self.command,self.path,body,h);r=c.getresponse();b=r.read(2000001)
   if len(b)>2000000:raise ValueError()
   self.send_response(r.status)
   for k,v in r.getheaders():
    if k.lower() not in ('connection','transfer-encoding','content-length','set-cookie'):self.send_header(k,v)
   self.send_header('Content-Length',str(len(b)))
   if self.path=='/':self.send_header('Set-Cookie','network-ui='+cookie+'; HttpOnly; SameSite=Strict; Path=/')
   self.end_headers();self.wfile.write(b)
  except (OSError,ValueError):self.send_error(503)
  finally:c.close()
ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
