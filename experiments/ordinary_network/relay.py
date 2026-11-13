"""Opaque test-only TLS byte conduit across a frozen loopback fixture boundary.

No credentials, decryption, SQL, Docker access or application authorization.
Never packaged. Internal bridge + named UNIX-socket volume exist only in tests.
"""
import socket,socketserver,select,sys,os
from threading import Thread
class Relay(socketserver.ThreadingMixIn,socketserver.TCPServer):allow_reuse_address=True;daemon_threads=True
class Unix(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True
class Handler(socketserver.BaseRequestHandler):
 def handle(self):
  try:
   mode,port=self.server.scope
   peer=socket.socket(socket.AF_UNIX) if mode=='edge' else socket.socket()
   peer.settimeout(120);peer.connect('/sockets/'+str(port)+'.sock' if mode=='edge' else ('127.0.0.1',port));self.request.settimeout(120)
   with peer:
    while True:
     readable,_,_=select.select([peer,self.request],[],[],120)
     if not readable:return
     for source in readable:
      data=source.recv(65536)
      if not data:return
      (self.request if source is peer else peer).sendall(data)
  except OSError:pass
if __name__=='__main__':
 mode=sys.argv[1];assert mode in ('edge','core')
 servers=[]
 for port in (8098,8099):
  address=('0.0.0.0',port) if mode=='edge' else '/sockets/'+str(port)+'.sock'
  if mode=='core':
   try:os.unlink(address)
   except FileNotFoundError:pass
  s=(Relay if mode=='edge' else Unix)(address,Handler);s.scope=(mode,port);servers.append(s)
  if mode=='core':os.chmod(address,0o666)
  Thread(target=s.serve_forever,daemon=True).start()
 __import__('threading').Event().wait()
