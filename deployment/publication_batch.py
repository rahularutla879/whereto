"""Render exactly six local-image pushes. No execute/apply/network operation.

The generated operator batch re-verifies the source-bound owner-supplied
Ed25519 publication signature before any Docker tag/push. Missing genuine
frontend enrollment or missing owner/security/cost decisions remains a stop.
"""
from pathlib import Path
import argparse,json,shlex,subprocess,os
from deployment.cloud_run_real import pins,ROOT,original

def proposed_service_urls():
    """Documented deterministic URLs, not observed resources or enrollment."""
    number=original.PROJECT_NUMBER
    names={r:'whereto-'+r for r in original.ROLES}
    if any(len(name+'-'+number)>63 for name in names.values()):raise ValueError('Deterministic DNS segment too long')
    return dict(observed=False,project=original.PROJECT,region=original.REGION,
                urls={r:'https://'+n+'-'+number+'.'+original.REGION+'.run.app' for r,n in names.items()},
                source='https://docs.cloud.google.com/run/docs/triggering/https-request',
                requirement='Confirm project/SA subjects before enrollment and status.url before any tester/provider action; stop on mismatch')

def render(owner_directory):
    images=pins();directory=Path(owner_directory).resolve()
    if ROOT==directory or ROOT in directory.parents:raise ValueError('Owner-only external directory required')
    # Owner files remain private. Do not inspect/read API or signing keys.
    header=['#!/bin/sh','set -eu', 'cd '+shlex.quote(str(ROOT)),
      'IMAGES=$(node deployment/frontend_trust.mjs publication-images '+shlex.quote(str(directory))+')',
      'set -f', 'set -- $IMAGES', '[ "$#" -eq 6 ] || exit 78',
      "python3 -c "+shlex.quote("import subprocess,json,sys; d=['docker','--context','colima-whereto-task52']; xs=[json.loads(subprocess.check_output(d+['image','inspect',i]))[0] for i in sys.argv[1:]]; (len(xs)==6 and all(x['Architecture']=='amd64' and x['Os']=='linux' for x in xs) and sum(x['Size'] for x in xs)<=5*1024**3) or sys.exit(78)")+" \"$@\"",
      '# Signature is exact artifact-only approval. No Run/IAM/secret/provider command follows.',
      '# Existing credential helper and repository must be separately approved/enrolled.']
    for role in original.ROLES:
        # Consume only the authenticated in-memory snapshot, never reread JSON.
        header.append('IMAGE=$1; shift')
        header.append('case "$IMAGE" in sha256:'+'?'*64+') ;; *) exit 78;; esac')
        tag=f'us-east4-docker.pkg.dev/where-to-512422/whereto-private/whereto-{role}:owner-'+images['cohort'][:12]+'-'
        header+=['TAG='+shlex.quote(tag)+'${IMAGE#sha256:}','docker --context colima-whereto-task52 image inspect "$IMAGE" >/dev/null','docker --context colima-whereto-task52 tag "$IMAGE" "$TAG"','docker --context colima-whereto-task52 push "$TAG"']
    header+=['# Stop on first error. Do not rerun without owner approval.', '# Download actual amd64 registry manifest/config bytes and verify OCI receipts.', '# No registry digest is inferred from local ID/config, and no deployment is activated.']
    return '\n'.join(header)+'\n'

def enrolled_plan(config,owner_directory,registry_artifacts=None):
    """Finite owner-signed frontend replacement; original cohort stays immutable."""
    from deployment import cloud_run_real as c
    r=subprocess.run(['node',str(ROOT/'deployment/frontend_trust.mjs'),'verified-publication',str(Path(owner_directory).resolve())],cwd=ROOT,env={'PATH':os.environ.get('PATH','/usr/bin:/bin')},capture_output=True,text=True,timeout=10)
    if r.returncode!=0:raise ValueError('Genuine owner trust/publication proof missing')
    approved=json.loads(r.stdout);m=c.pins();selected={**m,'candidateForReview':approved['images'],'configDigests':approved['configDigests']}
    parent=c.parent();parent.pins=lambda:selected
    plan=parent.compile_plan(config);receipts=registry_artifacts or {}
    if set(receipts)-set(original.ROLES):raise ValueError('Unknown registry role')
    verifier=c.reviewed_parent();verifier.pins=lambda:{'candidateForReview':selected['configDigests']}
    for role,w in config['workloads'].items():
        if role in receipts:
            manifest,raw=receipts[role]
            result=verifier.publication_receipt(role,manifest,c.original.sha(manifest),raw)
            if result['registryManifest']!=w['registryManifest']:raise ValueError('Registry receipt mismatch')
        else:
            plan['roles'][role]['commandForReviewOnly']=None
            plan['blockers'].append(role+' actual registry bytes missing')
    plan.update(identity='53-owner-enrolled-real-artifact-plan-v1',provisioningAuthorized=False,releaseEligible=False,realDemoSupportedByCurrentImages=True)
    plan['imageContentReview'].update(realProfileRepackagingRequired=False,frontendTrustEnrolled=True,securityAccepted=False,securityInventory='docs/task52-production-enrollment-security.md',ownerArtifactOnlySecurityReference=approved['securityDecisionSHA256'])
    for item in plan['publicationForReviewOnly']:
        item['commands'][0][2]=approved['images'][item['role']]
        item['localImage']=approved['images'][item['role']]
        item['localConfigDigest']=approved['configDigests'][item['role']]
    plan['blockers'].append('Artifact-only owner signature is not hosting security acceptance, model qualification or provider financial authority')
    return plan

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('owner_directory',type=Path);p.add_argument('output',type=Path);p.add_argument('--cloud-plan',type=Path);p.add_argument('--registry-receipts',type=Path);a=p.parse_args()
    if a.cloud_plan:
        artifacts={}
        if a.registry_receipts:
            for role in original.ROLES:
                f=a.registry_receipts/(role+'.manifest.json');c=a.registry_receipts/(role+'.config.json')
                if f.exists() or c.exists():artifacts[role]=(f.read_bytes(),c.read_bytes())
        result=enrolled_plan(original.read(a.cloud_plan),a.owner_directory,artifacts)
        with a.output.open('x') as f:json.dump(result,f,sort_keys=True,indent=2)
        return
    if a.output.resolve()==ROOT or ROOT in a.output.resolve().parents:raise ValueError('External batch output required')
    with a.output.open('x') as f:f.write(render(a.owner_directory))
    a.output.chmod(0o700)
    print(json.dumps({'rendered':True,'executed':False,'maximumPushCommands':6,'authorization':'absent until exact owner signature and genuine frontend record verify'}))
if __name__=='__main__':main()
