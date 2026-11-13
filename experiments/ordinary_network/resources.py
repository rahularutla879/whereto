"""Mount-ID inventory of containers actually created here; never broad prune."""
from contextlib import contextmanager
import subprocess,json
from pathlib import Path
from unittest.mock import patch
_ACTIVE=None

def record(D,container):
 if _ACTIVE is not None:_ACTIVE(container)

@contextmanager
def inventory(D):
 global _ACTIVE
 original=subprocess.check_output;run=subprocess.run
 def listed():return set(original(D+['volume','ls','-q'],text=True).split())
 before=listed();before_networks=set(original(D+['network','ls','-q'],text=True).split());owned=set();containers=set();networks=set()
 def capture(container):
  if len(container)!=64:return
  d=json.loads(original(D+['inspect',container],text=True))[0];containers.add(container)
  owned.update(m['Name'] for m in d.get('Mounts',[]) if m['Type']=='volume' and m.get('Name') not in before)
 _ACTIVE=capture
 def checked(command,**kwargs):
  result=original(command,**kwargs)
  if list(command[:len(D)+1]) in (D+['run'],D+['create']):capture((result.decode() if isinstance(result,bytes) else result).strip())
  return result
 def ran(command,**kwargs):
  result=run(command,**kwargs)
  if result.returncode==0 and list(command[:len(D)+2])==D+['network','create']:
   networks.add(json.loads(original(D+['network','inspect',command[-1]],text=True))[0]['Id'])
  if result.returncode==0 and list(command[:len(D)+2])==D+['volume','create'] and command[-1] not in before:owned.add(command[-1])
  return result
 try:
  with patch.object(subprocess,'check_output',checked),patch.object(subprocess,'run',ran):yield
 finally:
  _ACTIVE=None
  for container in containers:run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  removed=[];retained=[]
  for name in owned & listed():
   r=run(D+['volume','rm',name],capture_output=True)
   (removed if r.returncode==0 else retained).append(name)
  for network in networks-before_networks:run(D+['network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  Path('/tmp/network-resource-inventory.json').write_text(json.dumps(dict(originalVolumeCount=len(before),provedOwnedRemoved=sorted(removed),provedOwnedRetained=sorted(retained),allOriginalVolumesPreserved=before<=listed(),unattributedNewVolumesPreserved=sorted(listed()-before-owned)))+'\n')
