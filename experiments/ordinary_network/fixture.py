"""Disposable orchestration/ingress, never imported into an application image."""
import subprocess,secrets,json,socket,os
from pathlib import Path
class Fixture:
 def __init__(self,D,client,network,mount,image,configs,extras,helpers,volumes,temp):
  self.D,self.client,self.temp=D,client,Path(temp);self.ingress=None;self.processes=[];self.helpers=helpers;self.volumes=volumes;self.image=image;self.mount=mount
  self.network='whereto-network-'+secrets.token_hex(12)
  subprocess.run(D+['network','create','--opt','com.docker.network.bridge.enable_ip_masquerade=false',self.network],check=True,stdout=subprocess.DEVNULL)
  sockets='whereto-sockets-'+secrets.token_hex(12);subprocess.run(D+['volume','create',sockets],check=True,stdout=subprocess.DEVNULL);volumes.append(sockets)
  # Test edge has no credential/HTTP role, publishes loopback only and disables
  # bridge IP masquerading. The protected core keeps its networkless guard.
  # Named UNIX-socket volume contains opaque TLS bytes only; no host mounts.
  for mode,net in [('core',network),('edge',self.network)]:
   args=['run','-d','--platform','linux/amd64','--network',net,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','64m','--cpus','.1','--mount','type=volume,src='+mount+',dst=/app,readonly','--mount','type=volume,src='+sockets+',dst=/sockets','-e','PYTHONPATH=/app']
   if mode=='edge':args+=['--network-alias','worker-a.task52.invalid','--network-alias','worker-b.task52.invalid','-p','127.0.0.1::8098','-p','127.0.0.1::8099']
   else:
    # Bootstrap ownership only, before any application connection.
    h=subprocess.check_output(D+['run','-d','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+sockets+',dst=/sockets','--entrypoint','sleep',image,'30'],text=True).strip()
    try:subprocess.run(D+['exec',h,'chown','10001:10001','/sockets'],check=True)
    finally:subprocess.run(D+['rm','-fv',h],check=True,stdout=subprocess.DEVNULL)
   container=subprocess.check_output(D+args+['--entrypoint','python',image,'-m','experiments.ordinary_network.relay',mode],text=True).strip();self.processes.append(container);helpers.append(container)
  d=json.loads(subprocess.check_output(D+['inspect',self.processes[-1]],text=True))[0]
  self.endpoints=['https://worker-'+name+'.task52.invalid:'+d['NetworkSettings']['Ports'][str(port)+'/tcp'][0]['HostPort'] for name,port in [('a',8098),('b',8099)]]
  # Only this separate synthetic ingress process receives the fixed fake IAP key.
  for remote,local in [('ui-fixture-iap.pem','iap.pem'),('ui-fixture-iap.json','iap.json')]:
   content=subprocess.check_output(D+['exec',client,'cat','/tmp/'+remote]);p=self.temp/local;p.write_bytes(content);p.chmod(0o600)
 def configure(self,data):data['network']=dict(endpoints=['https://worker-a.task52.invalid:8098','https://worker-b.task52.invalid:8099'])
 def start_frontend(self,data):
  directory=self.temp/'frontend-code';subprocess.run(['node','experiments/ordinary_network/compile_fixture.mjs',str(directory)],check=True)
  c=data['frontend'];public={k:c[k] for k in ('iapAudience','testers','ordinaryBuild','identityEnvironment','epoch','signingKey','googleKeys','caPem')};public['audiences']={'backend':c['audiences']['backend']};public['enrollment']={'frontend':c['enrollment']['frontend']};public['oidcTokens']={c['audiences']['backend']:c['oidcTokens'][c['audiences']['backend']]};(directory/'frontend.json').write_text(json.dumps(dict(frontend=public,network=data['network'])));(directory/'frontend.json').chmod(0o600)
  volume='whereto-frontend-'+secrets.token_hex(12);subprocess.run(self.D+['volume','create',volume],check=True,stdout=subprocess.DEVNULL);self.volumes.append(volume)
  helper=subprocess.check_output(self.D+['run','-d','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+volume+',dst=/fixture','--entrypoint','sleep',self.image,'60'],text=True).strip()
  try:
   subprocess.run(self.D+['cp',str(directory)+'/.',helper+':/fixture/'],check=True);subprocess.run(self.D+['exec',helper,'chown','-R','1000:1000','/fixture'],check=True)
  finally:subprocess.run(self.D+['rm','-fv',helper],check=True,stdout=subprocess.DEVNULL)
  image=json.loads(Path('/tmp/network-image-identities.json').read_text())['frontend']['id']
  front=subprocess.check_output(self.D+['run','-d','--platform','linux/amd64','--network',self.network,'--network-alias','network-frontend.task52.invalid','-p','127.0.0.1::8080','--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','1','--mount','type=volume,src='+volume+',dst=/app/fixture,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=1000,gid=1000,mode=0700','-e','PORT=8080','-e','HOSTNAME=0.0.0.0','--entrypoint','node',image,'--import','/app/fixture/preload.mjs','server.js'],text=True).strip();self.processes.append(front);self.helpers.append(front);self.frontend=front
  d=json.loads(subprocess.check_output(self.D+['inspect',front],text=True))[0];return int(d['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort'])
 def capture(self,data):
  r=subprocess.run(self.D+['exec',self.frontend,'cat','/tmp/last-proof.json'],capture_output=True)
  if r.returncode==0:Path(data['capture']).write_bytes(r.stdout);Path(data['capture']).chmod(0o600)
 def start_ingress(self,port):
  volume='whereto-idp-'+secrets.token_hex(12);subprocess.run(self.D+['volume','create',volume],check=True,stdout=subprocess.DEVNULL);self.volumes.append(volume)
  helper=subprocess.check_output(self.D+['run','-d','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+volume+',dst=/identity','--entrypoint','sleep',self.image,'60'],text=True).strip()
  try:
   for name in ('iap.pem','iap.json'):subprocess.run(self.D+['cp',str(self.temp/name),helper+':/identity/'+name],check=True)
   subprocess.run(self.D+['exec',helper,'chown','-R','10001:10001','/identity'],check=True)
  finally:subprocess.run(self.D+['rm','-fv',helper],check=True,stdout=subprocess.DEVNULL)
  self.ingress=subprocess.check_output(self.D+['run','-d','--platform','linux/amd64','--network',self.network,'-p','127.0.0.1::8081','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--mount','type=volume,src='+volume+',dst=/identity,readonly','--mount','type=volume,src='+self.mount+',dst=/app,readonly','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','-e','WHERETO_ENV=development','--entrypoint','python',self.image,'-m','experiments.ordinary_network.ingress','/identity','network-frontend.task52.invalid','8081'],text=True).strip();self.processes.append(self.ingress);self.helpers.append(self.ingress)
  d=json.loads(subprocess.check_output(self.D+['inspect',self.ingress],text=True))[0];self.browser_url='http://127.0.0.1:'+d['NetworkSettings']['Ports']['8081/tcp'][0]['HostPort']
 def stop_ingress(self):
  if self.ingress:subprocess.run(self.D+['rm','-fv',self.ingress],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.ingress=None
 def close(self):
  self.stop_ingress()
  for p in reversed(self.processes):subprocess.run(self.D+['rm','-fv',p],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(self.D+['network','rm',self.network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
