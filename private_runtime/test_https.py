import unittest,tempfile,subprocess,sys,ssl,time,socket,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from private_runtime.https import Endpoint,HTTPS,Refused
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=Path(cls.tmp.name);cls.ca=p/'cert.pem'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(p/'key.pem'),'-out',str(cls.ca),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,umask=0o077)
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  code="""import ssl,sys,time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  n=int(self.headers.get('Content-Length',0));raw=self.rfile.read(n)
  if self.path=='/slow':time.sleep(.3)
  self.send_response(302 if self.path=='/redirect' else 200);self.send_header('Content-Type','application/json');
  if self.path=='/truncated':self.send_header('Content-Length',str(len(raw)+10))
  self.end_headers();self.wfile.write(b'x'*100 if self.path=='/large' else raw)
s=ThreadingHTTPServer(('127.0.0.1',int(sys.argv[3])),H);c=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);c.load_cert_chain(sys.argv[1],sys.argv[2]);s.socket=c.wrap_socket(s.socket,server_side=True);s.serve_forever()
"""
  cls.proc=subprocess.Popen([sys.executable,'-c',code,str(cls.ca),str(p/'key.pem'),str(cls.port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),.1):break
   except OSError:time.sleep(.02)
  cls.endpoint=Endpoint('https://localhost:'+str(cls.port),'https://audience.invalid')
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=3);cls.tmp.cleanup()
 def test_valid_bytes_independent_process(self):
  self.assertEqual(HTTPS(ca_file=str(self.ca)).request(self.endpoint,'POST','/echo',b'{ "exact": true }',{'Content-Type':'application/json'}),b'{ "exact": true }')
 def test_default_roots_reject_fixture_ca(self):
  with self.assertRaises(Refused):HTTPS().request(self.endpoint,'POST','/echo',b'{}',{})
 def test_hostname_and_missing_cert_refuse(self):
  with self.assertRaises(Refused):HTTPS(ca_file=str(self.ca)).request(Endpoint('https://127.0.0.1:'+str(self.port),self.endpoint.audience),'POST','/echo',b'{}',{})
 def test_truncated_valid_json_is_still_refused(self):
  with self.assertRaises(Refused):HTTPS(ca_file=str(self.ca)).request(self.endpoint,'POST','/truncated',b'{}',{})
 def test_redirect_not_followed(self):
  with self.assertRaises(Refused):HTTPS(ca_file=str(self.ca)).request(self.endpoint,'POST','/redirect',b'{}',{})
 def test_bounds_deadline_and_capacity(self):
  for path,transport in [('/large',HTTPS(ca_file=str(self.ca),response_limit=10)),('/slow',HTTPS(ca_file=str(self.ca),deadline=.05))]:
   with self.assertRaises(Refused):transport.request(self.endpoint,'POST',path,b'{}',{})
  t=HTTPS(ca_file=str(self.ca),connections=1);t.gate.acquire()
  try:
   with self.assertRaises(Refused):t.request(self.endpoint,'POST','/echo',b'{}',{})
  finally:t.gate.release()
 def test_configuration_and_request_scope(self):
  for u in ('http://localhost','https://u:p@localhost','https://localhost/path','https://localhost?x'):
   with self.assertRaises(Refused):Endpoint(u,'https://aud.invalid')
  t=HTTPS(ca_file=str(self.ca),request_limit=2)
  for method,path,body in [('PUT','/echo',b'{}'),('POST','//bad',b'{}'),('POST','/echo',b'long'),('GET','/echo',b'{}')]:
   with self.assertRaises(Refused):t.request(self.endpoint,method,path,body,{})
if __name__=='__main__':unittest.main(verbosity=2)
