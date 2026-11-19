"""Record verified local six-role artifacts. No enrollment, publish or cloud I/O."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,re,sys,tarfile,shutil,subprocess
if not __debug__:raise SystemExit('Candidate evidence validation must be enabled; optimized Python refused')
ROOT=Path(__file__).resolve().parents[1]
def sha(v):return sha256(v).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def record(build,safety,target):
 build,safety,target=map(lambda x:Path(x).resolve(),(build,safety,target))
 if target.exists():raise ValueError('Fresh candidate record directory required')
 images=read(build/'images.json');smoke=read(build/'smoke.json');scans=read(build/'scans/scan-summary.json');roles=('frontend','backend','factory','counter','dispatcher','recovery')
 assert set(images)==set(smoke)==set(scans['images'])==set(roles)
 assert 'CONTAINER_BROWSER_ACCEPTANCE_PASSED' in (build/'browser-attempt.log').read_text()
 assert 'CONTAINER_SAFETY_ACCEPTANCE_PASSED' in (safety/'attempt.log').read_text()
 assert read(build/'browser-result.json')['passed'] is True and scans['allOriginalVolumesPreserved'] is True and scans['afterVolumeCount']==len(scans['beforeVolumes'])
 target.mkdir(parents=True);cohort=(build/'roles/cohort.json').read_bytes();pin=sha(cohort);configs={};metadata={};databases=set();findings={};summaries={}
 for role in roles:
  image=images[role]['image'];s=scans['images'][role];assert s['image']==image==smoke[role]['image'] and s['exit']==0 and s['oom']is False
  assert smoke[role]['unenrolledStartupExit']==78 and smoke[role]['verified']['cohort']==pin and images[role]['platform']=='linux/amd64'
  report=(build/f'scans/{role}.json').read_bytes();assert sha(report)==s['rawSHA256'];doc=json.loads(report);db=doc['descriptor']['db']['status'];databases.add((db['built'],db['from'],db['schemaVersion']))
  with tarfile.open(build/f'scans/{role}.tar') as archive:
   manifest=json.load(archive.extractfile('manifest.json'));raw=archive.extractfile(manifest[0]['Config']).read()
  assert not re.search(rb'sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',raw)
  config=json.loads(raw);assert config['architecture']=='amd64' and config['os']=='linux';configs[role]='sha256:'+sha(raw);assert configs[role]==doc['source']['target']['imageID']
  (target/'config').mkdir(exist_ok=True);(target/f'config/{role}.json').write_bytes(raw)
  metadata[role]={**images[role],'configDigest':configs[role],'runtime':smoke[role]['verified'],'unenrolledExit':78,'readOnlyApplication':True,'fixtureCredentialsOrRespondersInImage':False,'legacyCatalogLoader':'Compatibility import only; Python fixture data absent; not selected in real profile','sourceCohort':pin}
  findings[role]=[]
  for m in doc['matches']:
   v,a=m['vulnerability'],m['artifact']
   if v['severity']not in ('Critical','High'):continue
   findings[role].append(dict(advisory=v['id'],severity=v['severity'],package=a['name'],installed=a['version'],type=a['type'],purl=a.get('purl'),locations=a.get('locations',[]),fix=v.get('fix'),dataSource=v.get('dataSource'),namespace=v.get('namespace'),matchDetails=m.get('matchDetails'),vendorReference='https://security-tracker.debian.org/tracker/'+v['id'] if a['type']=='deb' else v.get('dataSource'),disposition='Unaccepted; hosting blocked pending remediation or independent disposition'))
  summaries[role]=dict(image=image,counts=s['counts'],rawScanSHA256=sha(report),scannerExit=0,oom=False)
 assert len(databases)==1
 for src,dst in [('roles/cohort.json','cohort.json'),('candidate-build.json','build.json'),('frontend/real-frontend-source.json','frontend-source.json'),('roles/Dockerfile','Dockerfile.python'),('frontend/deployment/Dockerfile.frontend-private','Dockerfile.frontend')]:shutil.copyfile(build/src,target/dst)
 raw=subprocess.check_output(['docker','--context','colima-whereto-task52','run','--rm','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--entrypoint','cat',images['frontend']['image'],'/app/private-runtime/frontend-build.json'])
 assert sha(raw)==smoke['frontend']['verified']['artifact'];(target/'frontend-build.json').write_bytes(raw)
 security=dict(identity='52-real-native-image-security-v1',scanner=scans['scanner'],database=dict(zip(('built','from','schemaVersion'),next(iter(databases)))),securityAccepted=False,criticalHigh=findings,scans=summaries,noScannerExclusions=True,vendorReview={'openssl':'Official current source index lists installed trixie-security3.5.7-1~deb13u3; six scanned high issues remain open. QUIC/CMS/AES paths require separate reachability review, not blanket acceptance.','perl':'CVE-2026-82560 installed5.40.1-6+deb13u1 still vulnerable/no-dsa per Debian. POD formatter not invoked by application; not an exception.','ncurses':'CVE-2025-69720 trixie6.5+20250216-2 vulnerable/no-dsa; fixed unstable package not adopted. CLI reachability remains review material.','otherFindings':'All scanner advisory/package/version/fix-state identities retained. No compatible fixed-version high match reported; individual independent vendor/reachability disposition incomplete.','bulkVendorData':'Public bulk-download attempt incomplete (host Python CA failure; system verified-TLS download exceeded30MB bound). Partial file retained locally, not used as vendor evidence.','sources':['https://security-tracker.debian.org/tracker/source-package/openssl','https://security-tracker.debian.org/tracker/CVE-2026-124709','https://security-tracker.debian.org/tracker/CVE-2026-82560','https://security-tracker.debian.org/tracker/CVE-2025-69720']},retainedConflictInventory='docs/task52-candidate-promotion-security.json',noSecurityExceptionApproved=True)
 write(target/'security.json',security)
 artifacts={str(p.relative_to(target)):sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
 buildinputs={**read(build/'candidate-build.json')['inputs'],**{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [ROOT/'deployment/build_real_candidates.py',ROOT/'deployment/scan_real_candidates.py',ROOT/'deployment/smoke_real_candidates.py',Path(__file__)]}}
 from deployment.cloud_run_real import original
 result=dict(identity='52-real-native-built-images-v1',recordedAtUTC=datetime.now(timezone.utc).isoformat(),cohort=pin,nativeBuild=read(build/'roles/cohort.json')['nativeBuild'],realProviderTransport=True,releaseEligible=False,promotionApproved=False,published=False,containerAcceptancePassed=True,frontendTrustEnrolled=False,candidateForReview={r:images[r]['image'] for r in roles},configDigests=configs,roles=metadata,artifactsSHA256=artifacts,buildInputs=buildinputs,mountExpectations=original.MOUNTS,rollbackReferences={'images':'deployment/candidates/trixie-zlib-v2/images.json','cohort':'deployment/candidates/trixie-zlib-v2/cohort.json','automaticRollbackPermitted':False},localTagsAreNotPublishedRegistryDigests=True)
 write(target/'images.json',result);return result
if __name__=='__main__':print(json.dumps(record(*sys.argv[1:]),sort_keys=True))
