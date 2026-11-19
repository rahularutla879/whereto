"""Local candidate scans only. Public vulnerability DB; no registry publication."""
import json,subprocess,secrets,tempfile,os,hashlib,sys
from pathlib import Path
D=['docker','--context','colima-whereto-task52'];P=Path(sys.argv[1]).resolve();root=P/'scans';root.mkdir(exist_ok=True);os.chmod(root,0o700)
scanner='anchore/grype@sha256:13113eeceab017260370cf540e1d25442c59665fd07d1b09b66d63bb0c282887'
images={r:v['image'] for r,v in json.loads((P/'images.json').read_bytes()).items()}
volume='whereto-real-grype-'+secrets.token_hex(8);before=subprocess.check_output(D+['volume','ls','--format','{{.Name}}'],text=True).splitlines();result={'scanner':scanner,'beforeVolumes':before,'ownedVolume':volume,'images':{},'databaseMustMatch':True}
subprocess.run(D+['volume','create','--label','whereto.task52.checkpoint=real-provider-images',volume],check=True,stdout=subprocess.DEVNULL)
try:
 subprocess.run(D+['run','--rm','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+volume+',dst=/cache','--entrypoint','python',images['counter'],'-c',"import os;os.chown('/cache',65532,65532);os.chmod('/cache',0o700)"],check=True)
 identity=None
 for i,(role,im) in enumerate(images.items()):
  archive=root/(role+'.tar');subprocess.run(D+['save','-o',str(archive),im],check=True,timeout=120);archive.chmod(0o644)
  args=D+['create','--platform','linux/amd64','--user','65532:65532','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','1g','--cpus','1','--pids-limit','128','--network','bridge' if i==0 else 'none','--mount','type=volume,src='+volume+',dst=/cache','-e','TMPDIR=/work','-e','GRYPE_DB_CACHE_DIR=/cache','-e','GRYPE_CHECK_FOR_APP_UPDATE=false','-e','GRYPE_DB_AUTO_UPDATE='+('true' if i==0 else 'false'),scanner,'docker-archive:/tmp/image.tar','--output','json']
  cid=subprocess.check_output(args,text=True).strip()
  try:
   with tempfile.TemporaryDirectory(prefix='task52-public-scan-work-') as tmp:
    os.chmod(tmp,0o777);subprocess.run(D+['cp',tmp,cid+':/work'],check=True,stdout=subprocess.DEVNULL)
   subprocess.run(D+['cp',str(archive),cid+':/tmp/image.tar'],check=True,stdout=subprocess.DEVNULL)
   out=root/(role+'.json');err=root/(role+'.log')
   with out.open('w') as f,err.open('w') as e:r=subprocess.run(D+['start','--attach',cid],stdout=f,stderr=e,timeout=300)
   state=json.loads(subprocess.check_output(D+['inspect',cid]))[0]['State'];item={'image':im,'exit':r.returncode,'oom':state['OOMKilled'],'rawSHA256':hashlib.sha256(out.read_bytes()).hexdigest()}
   if r.returncode==0:
    x=json.loads(out.read_text());db=x['descriptor']['db']['status'];assert db['valid'];dbid=(db['built'],db['from'],db['schemaVersion']);identity=identity or dbid;assert identity==dbid;item['database']=db;item['counts']={}
    for m in x['matches']:
     sev=m['vulnerability']['severity'];item['counts'][sev]=item['counts'].get(sev,0)+1
   result['images'][role]=item;(root/'scan-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(role,item,flush=True)
  finally:
   subprocess.run(D+['rm','-f',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);archive.chmod(0o600)
finally:
 subprocess.run(D+['volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 after=subprocess.check_output(D+['volume','ls','--format','{{.Name}}'],text=True).splitlines();result['allOriginalVolumesPreserved']=set(before)<=set(after);result['afterVolumeCount']=len(after);(root/'scan-summary.json').write_text(json.dumps(result,indent=2)+'\n')
