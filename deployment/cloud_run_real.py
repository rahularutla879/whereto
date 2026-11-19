"""Finite real-image binding of the reviewed offline Cloud Run compiler.

Preserves its networking, six identities, secrets, rollout and financial gates.
No command execution. OCI bytes must prove the candidate config before deploy
argv can be emitted. Publication, provisioning and release remain unauthorized.
"""
from pathlib import Path
from types import ModuleType
import argparse,json
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'deployment/candidates/real-native-v1'
PARENT_SHA256='fb5015551174a2652186755b7ad4e00b85fdc43e0b288c9acbdd19a07adc2eee'

def reviewed_parent():
    p=ROOT/'deployment/cloud_run.py';raw=p.read_bytes()
    if p.is_symlink() or sha256(raw).hexdigest()!=PARENT_SHA256:raise ValueError('reviewed compiler changed')
    m=ModuleType('reviewed_real_cloud_run_parent');m.__file__=str(p)
    exec(compile(raw,str(p),'exec'),m.__dict__)
    return m
original=reviewed_parent()

def pins():
    enrollment=original.read(ROOT/'deployment/cloud-run/real-source-pins-v1.json')
    for name,h in enrollment['filesSHA256'].items():
        p=ROOT/name
        if p.is_symlink() or original.sha(p.read_bytes())!=h:raise original.Refused('real deployment source changed: '+name)
    manifest=original.read(CANDIDATE/'images.json')
    if set(manifest['candidateForReview'])!=set(original.ROLES) or set(manifest['configDigests'])!=set(original.ROLES):raise original.Refused('six exact real images required')
    for name,h in manifest['artifactsSHA256'].items():
        p=CANDIDATE/name
        if p.is_symlink() or original.sha(p.read_bytes())!=h:raise original.Refused('real candidate artifact changed: '+name)
    cohort=original.read(CANDIDATE/'cohort.json')
    if original.sha((CANDIDATE/'cohort.json').read_bytes())!=manifest['cohort'] or cohort['profile']!='52-real-native-six-role-v4' or cohort['realProviderTransport']is not True or cohort['releaseEligible']is not False:raise original.Refused('inactive real source cohort required')
    for name,h in {**cohort['inputs'],**manifest['buildInputs']}.items():
        p=ROOT/name
        if p.is_symlink() or original.sha(p.read_bytes())!=h:raise original.Refused('real source identity changed: '+name)
    for collection in ('candidateForReview','configDigests'):
        for d in manifest[collection].values():
            if not d.startswith('sha256:'):raise original.Refused('immutable local/config digest required')
            original.digest(d[7:])
    return manifest

def parent():
    m=reviewed_parent()
    m.Refused=original.Refused
    m.pins=pins;m.CALLERS={**m.CALLERS,'dispatcher':('factory','counter')}
    def read(path):
        if Path(path)==ROOT/'deployment/candidates/trixie-zlib-v2/cohort.json':path=CANDIDATE/'cohort.json'
        return original.read(path)
    m.read=read
    return m

def decode(raw):
    if not isinstance(raw,bytes) or len(raw)>2000000:raise original.Refused('bounded OCI bytes required')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise original.Refused('duplicate OCI member')
            result[k]=v
        return result
    try:return json.loads(raw,object_pairs_hook=pairs)
    except (ValueError,UnicodeError) as e:raise original.Refused('invalid OCI JSON') from e

def publication_receipt(role,raw,registry_digest,config_raw):
    images=pins();original.digest(registry_digest)
    if role not in images['configDigests'] or original.sha(raw)!=registry_digest:raise original.Refused('registry role/manifest identity')
    v=decode(raw);config=decode(config_raw);expected=images['configDigests'][role]
    if v.get('schemaVersion')!=2 or v.get('mediaType')not in ('application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json') or v.get('config',{}).get('digest')!=expected or 'sha256:'+original.sha(config_raw)!=expected or config.get('architecture')!='amd64' or config.get('os')!='linux':raise original.Refused('registry content is not exact candidate linux amd64 config')
    if type(v.get('layers'))is not list or len(v['layers'])!=len(config.get('rootfs',{}).get('diff_ids',[])):raise original.Refused('OCI layer count does not match proven config')
    return dict(role=role,registryManifest=registry_digest,localConfigDigest=expected,localImage=images['candidateForReview'][role],verified=True)

def compile_plan(config,registry_artifacts=None):
    images=pins();plan=parent().compile_plan(config);registry_artifacts=registry_artifacts or {}
    if set(registry_artifacts)-set(original.ROLES):raise original.Refused('unknown registry role')
    for role,w in config['workloads'].items():
        if role in registry_artifacts:
            raw,configuration=registry_artifacts[role]
            receipt=publication_receipt(role,raw,original.sha(raw),configuration)
            if receipt['registryManifest']!=w['registryManifest']:raise original.Refused('configured registry identity differs from proven receipt')
        else:
            plan['roles'][role]['commandForReviewOnly']=None
            plan['blockers'].append(role+' exact registry manifest/config bytes not enrolled')
    for item in plan['publicationForReviewOnly']:
        item['localImage']=images['candidateForReview'][item['role']]
        item['localConfigDigest']=images['configDigests'][item['role']]
    plan.update(identity='53-offline-real-native-image-plan-v1',realDemoSupportedByCurrentImages=images['containerAcceptancePassed'])
    plan['imageContentReview'].update(realProfileRepackagingRequired=False,securityInventory='deployment/candidates/real-native-v1/security.json',securityAccepted=False,frontendTrustEnrolled=False,legacyCatalogLoader='compatibility import only; no Python fixture catalog included',localOllama='refusal-only stub; no local transport')
    plan['blockers']+=['candidate frontend deliberately has no genuine enrollment trust key; source-bound rebuild required after trust enrollment','residual image vulnerabilities require independent security disposition; no exception approved']
    return plan

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('--registry-receipts',type=Path);a=p.parse_args();artifacts={}
    if a.registry_receipts:
        for role in original.ROLES:
            manifest=a.registry_receipts/(role+'.manifest.json');config=a.registry_receipts/(role+'.config.json')
            if manifest.exists() or config.exists():artifacts[role]=(manifest.read_bytes(),config.read_bytes())
    print(json.dumps(compile_plan(original.read(a.config),artifacts),indent=2,sort_keys=True))
if __name__=='__main__':main()
