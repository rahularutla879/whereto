"""Fixed local fake metadata/JWKS. No signing or caller-selected identity endpoint."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json,ssl,os
if os.environ.get('K_SERVICE') or not Path('/.dockerenv').exists():raise RuntimeError('Local identity fixture only')
c=json.loads(Path('/identity/metadata.json').read_text())
class H(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  u=urlsplit(self.path)
  if u.path in ('/workload','/iap') and not u.query:raw=json.dumps(c[u.path[1:]]).encode()
  elif u.path=='/metadata' and parse_qs(u.query)=={'audience':[c['audience']]}:raw=c['token'].encode()
  else:self.send_error(403);return
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
s=ThreadingHTTPServer(('0.0.0.0',8443),H);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.load_cert_chain('/identity/server.crt','/identity/server.key');s.socket=ctx.wrap_socket(s.socket,server_side=True);s.serve_forever()
