"""Bounded HTTPS transport. No credentials, proxies, redirects, retries or fallbacks."""
from dataclasses import dataclass
import http.client
import ssl
from threading import BoundedSemaphore
from time import monotonic
from urllib.parse import urlsplit

class Refused(RuntimeError):pass

@dataclass(frozen=True)
class Endpoint:
    url: str
    audience: str
    def __post_init__(self):
        for value in (self.url,self.audience):
            u=urlsplit(value)
            if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/') or any(c.isspace() for c in value):raise Refused('endpoint')
            if u.port is not None and not 1<=u.port<=65535:raise Refused('endpoint')

class HTTPS:
    def __init__(self,*,ca_file=None,connections=4,deadline=120,request_limit=200000,response_limit=1048576):
        if type(connections) is not int or not 1<=connections<=4 or not 0<deadline<=120:raise Refused('limits')
        self.context=ssl.create_default_context(cafile=ca_file);self.context.minimum_version=ssl.TLSVersion.TLSv1_2
        self.gate=BoundedSemaphore(connections);self.deadline=deadline;self.request_limit=request_limit;self.response_limit=response_limit
    def request(self,endpoint,method,path,body,headers):
        if type(endpoint) is not Endpoint or method not in ('GET','POST') or not path.startswith('/') or path.startswith('//') or any(c in path for c in ('?','#','\r','\n')) or type(body) is not bytes or len(body)>self.request_limit or method=='GET' and body:raise Refused('request')
        if not self.gate.acquire(False):raise Refused('capacity')
        start=monotonic();c=None
        try:
            u=urlsplit(endpoint.url);c=http.client.HTTPSConnection(u.hostname,u.port or 443,context=self.context,timeout=min(5,self.deadline))
            c.connect();remaining=self.deadline-(monotonic()-start)
            if remaining<=0:raise Refused('deadline')
            stream=c.sock;stream.settimeout(remaining)
            c.request(method,path,body,headers);r=c.getresponse()
            if r.status!=200 or r.getheader('Content-Type','').split(';')[0]!='application/json':raise Refused('response')
            if r.getheader('Content-Length') and (not r.getheader('Content-Length').isdigit() or int(r.getheader('Content-Length'))>self.response_limit):raise Refused('response_bound')
            chunks=[];n=0
            while True:
                if r.isclosed():break
                remaining=self.deadline-(monotonic()-start)
                if remaining<=0:raise Refused('deadline')
                stream.settimeout(remaining)
                b=r.read1(min(65536,self.response_limit+1-n))
                if not b:break
                n+=len(b)
                if n>self.response_limit:raise Refused('response_bound')
                chunks.append(b)
            if r.length not in (None,0):raise Refused('incomplete_response')
            return b''.join(chunks)
        except (OSError,http.client.HTTPException):raise Refused('connection') from None
        finally:
            if c:c.close()
            self.gate.release()
