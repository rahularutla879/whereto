"""Local-only six image build; never publishes or enrolls services."""
import json,subprocess
from pathlib import Path
import sys
P=Path(sys.argv[1]).resolve();m=json.loads((P/'candidate-build.json').read_bytes());D=['docker','--context','colima-whereto-task52'];out={}
for role in ('backend','factory','counter','dispatcher','recovery','frontend'):
 tag='whereto-'+role+':real-native-'+m['cohort'][:12];context=P/('frontend' if role=='frontend' else 'roles');args=['-f',str(context/'deployment/Dockerfile.frontend-private')] if role=='frontend' else ['--build-arg','ROLE='+role]
 args+=['--build-arg',('NODE_IMAGE=' if role=='frontend' else 'PYTHON_IMAGE=')+m['bases']['images']['node' if role=='frontend' else 'python']['reference']]
 subprocess.run(D+['buildx','build','--load','--platform','linux/amd64','--progress','plain',*args,'-t',tag,str(context)],check=True)
 x=json.loads(subprocess.check_output(D+['image','inspect',tag]))[0];out[role]=dict(image=x['Id'],tag=tag,platform=x['Os']+'/'+x['Architecture'],user=x['Config']['User'],entrypoint=x['Config'].get('Entrypoint'),command=x['Config']['Cmd']);(P/'images.json').write_text(json.dumps(out,indent=2)+'\n');print('BUILT',role,x['Id'],flush=True)
