"""Synthetic workload identity over pinned local TLS; never Google token verification."""
import base64
from hashlib import sha256
import http.client
import json
import secrets
import socket
import ssl
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import canonical,strict_json

ISSUER='task52-synthetic-workloads-v1'
MAX_BODY=200000
MAX_RESPONSE=1024*1024

def b64(data):return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
def unb64(value):
    if type(value) is not str or len(value)>MAX_BODY*2:raise Denied('encoding')
    try:
        raw=base64.b64decode(value+'='*((-len(value))%4),altchars=b'-_',validate=True)
        if b64(raw)!=value:raise ValueError()
        return raw
    except (ValueError,TypeError):raise Denied('encoding') from None

def binding(audience,path,body):return sha256(canonical([audience,'POST',path,sha256(body).hexdigest()])).hexdigest()

def sign(config,audience,path,body,*,now=None,nonce=None):
    now=int(time.time()) if now is None else now
    doc=dict(iss=ISSUER,sub=config['principal'],aud=audience,role=config['role'],iat=now,exp=now+60,
        jti=nonce or secrets.token_hex(16),build=config['build'],environment=config['environment'],epoch=config['epoch'],request=binding(audience,path,body))
    head=b64(canonical({'alg':'EdDSA','typ':'JWT','kid':config['principal']}));payload=b64(canonical(doc));wire=(head+'.'+payload).encode()
    return wire.decode()+'.'+b64(Ed25519PrivateKey.from_private_bytes(unb64(config['signingKey'])).sign(wire))

class Verify:
    def __init__(self,config,consume,current_epoch):self.config,self.consume,self.current_epoch=config,consume,current_epoch
    def check(self,token,path,body):
        try:
            if type(token) is not str or len(token)>8192:raise ValueError()
            h,p,s=token.split('.');header=strict_json(unb64(h));claims=strict_json(unb64(p));c=self.config
            if set(header)!={'alg','typ','kid'} or header['alg']!='EdDSA' or header['typ']!='JWT':raise ValueError()
            principal=header['kid'];trusted=c['trust'][principal]
            Ed25519PublicKey.from_public_bytes(unb64(trusted['publicKey'])).verify(unb64(s),(h+'.'+p).encode())
            if set(claims)!=set('iss sub aud role iat exp jti build environment epoch request'.split()):raise ValueError()
            now=int(time.time())
            if claims['iss']!=ISSUER or claims['sub']!=principal or claims['aud']!=c['service'] or claims['role']!=trusted['role']:raise ValueError()
            if principal not in c['allow'].get(path,[]):raise ValueError()
            if type(claims['iat']) is not int or type(claims['exp']) is not int or not now-60<=claims['iat']<=now+5 or not now<claims['exp']<=claims['iat']+60:raise ValueError()
            if claims['build']!=c['build'] or claims['environment']!=c['environment'] or claims['epoch']!=c['epoch'] or claims['epoch']!=self.current_epoch():raise ValueError()
            if len(claims['jti'])!=32 or any(x not in '0123456789abcdef' for x in claims['jti']) or claims['request']!=binding(c['service'],path,body):raise ValueError()
            self.consume(c['service'],principal,claims['jti'],claims['request'],claims['exp']*1000)
            return principal,trusted.get('owner')
        except (ValueError,TypeError,KeyError,InvalidSignature):raise Denied('service_authentication') from None

class TLS(http.client.HTTPSConnection):
    def __init__(self,port,identity,ca,timeout):
        super().__init__('127.0.0.1',port,context=ssl.create_default_context(cafile=ca),timeout=timeout);self.identity=identity
    def connect(self):
        raw=socket.create_connection(('127.0.0.1',self.port),timeout=self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.identity)
        except BaseException:raw.close();raise

class Client:
    def __init__(self,config):self.config=config
    def request(self,service,path,value,*,token=None,raw=None):
        c=self.config;target=c['targets'][service];body=canonical(value) if raw is None else raw
        if len(body)>MAX_BODY:raise Denied('body_bound')
        auth=sign(c,service,path,body) if token is None else token
        conn=TLS(target['port'],target['hostname'],c['ca'],120)
        try:
            conn.request('POST',path,body,{'Content-Type':'application/json','Authorization':'Bearer '+auth})
            reply=conn.getresponse();wire=reply.read(MAX_RESPONSE+1)
            if len(wire)>MAX_RESPONSE:raise Denied('response_bound')
            result=strict_json(wire)
            if reply.status!=200:raise Denied(result.get('error','service_refused'))
            if type(result) is not dict or set(result)!={'result'}:raise Denied('response_shape')
            return result['result']
        except (OSError,http.client.HTTPException):raise Unavailable() from None
        finally:conn.close() # No retry, redirect, alternate endpoint or TLS fallback.
