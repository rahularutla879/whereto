"""Reproducible six-role context. Builds only; no image publication or activation."""
from pathlib import Path
import json,shutil
from deployment.prepare_real_services import prepare as services,ROOT,sha,encoded
from deployment.prepare_real_frontend import prepare as frontend
from deployment.prepare_zlib_candidate import package,dockerfile

def prepare(target,archive):
    target=Path(target).resolve()
    if target.exists() or ROOT in target.parents:raise ValueError('Fresh external candidate context required')
    patch=package(archive);cohort=services(target/'roles');roles=target/'roles'
    (roles/'security').mkdir();shutil.copyfile(archive,roles/'security/zlib1g.deb')
    front=target/'frontend';frontend(front)
    (front/'deployment/real-role-cohort-v1.json').write_bytes((roles/'cohort.json').read_bytes())
    # Existing private UI only; normal app/default files remain unchanged.
    # Do not include the normal mock demo branch in the real application bundle.
    (front/'app/page.tsx').write_text("'use client';\nimport {PrivateOrdinaryExperience} from '@/components/private-ordinary-experience';\nexport default function Home(){return <PrivateOrdinaryExperience real/>;}\n")
    # No fake identity, signer, key or developer CA is copied into this context.
    shutil.rmtree(front/'data');(front/'data').mkdir();shutil.copyfile(ROOT/'data/google-attribution.json',front/'data/google-attribution.json')
    registry=json.loads((ROOT/'data/mock-venues.json').read_bytes())
    registry['catalog']={k:{**v,'names':[],'prices':[]} for k,v in registry['catalog'].items()};registry['eventDates']=[];registry['tiers']=[]
    (front/'data/mock-venues.json').write_bytes(encoded(registry))
    p=front/'lib/mock-data.ts';text=p.read_text();at=text.index('export const VENUES: Venue[] =');p.write_text(text[:at].replace(') as Record<Activity, Definition>;',') as unknown as Record<Activity, Definition>;')+'export const VENUES: Venue[] = [];\n')
    # Every API is profile-only, even if the reviewed bootstrap is missing.
    # No BACKEND_URL, loopback/Ollama, ordinary-development or mock fallback.
    import re
    for p in (front/'app/api').rglob('route.ts'):
        original=p.read_text();methods=sorted(set(re.findall(r'export (?:async )?function (GET|POST|PUT|PATCH|DELETE)\(',original)))
        path='/'+str(p.parent.relative_to(front/'app'))
        if not methods:raise ValueError('Unknown frontend route '+str(p))
        p.write_text('import {privateRoute} from "@/lib/private-server-boundary";\nexport const runtime="nodejs";\n'+''.join('export async function '+m+'(request:Request){return privateRoute('+json.dumps(path)+',request)??Response.json({code:"hosted_route_unavailable"},{status:503});}\n' for m in methods))

    (front/'security').mkdir();shutil.copyfile(archive,front/'security/zlib1g.deb')
    df=(ROOT/'deployment/Dockerfile.frontend-private').read_text()
    df=df.replace('ARG LOCAL_FIXTURE=false','ARG ENROLLMENT_PUBLIC_KEY=')
    df=df.replace('deployment/private-role-cohort-v1.json ./deployment/','deployment/private-role-cohort-v1.json deployment/real-role-cohort-v1.json ./deployment/')
    a=df.index('# Only this public test transport');b=df.index('FROM ${NODE_IMAGE} AS runtime',a)
    df=df[:a]+'''RUN npm run build && if [ -z "$ENROLLMENT_PUBLIC_KEY" ]; then node deployment/build-private-frontend.mjs --real-profile --unenrolled-real-candidate; else printf '%s' "$ENROLLMENT_PUBLIC_KEY" > /tmp/enrollment-public.txt; node deployment/build-private-frontend.mjs --real-profile --enrollment-public-key /tmp/enrollment-public.txt; rm /tmp/enrollment-public.txt; fi
'''+df[b:]
    df=dockerfile(df,'NODE_IMAGE',cohort['baseImages']['images']['node']['reference'],patch)
    (front/'deployment/Dockerfile.frontend-private').write_text(df)
    proof=json.loads((front/'real-frontend-source.json').read_bytes());proof['realProjectionOutputs']={str(p.relative_to(front)):sha(p.read_bytes()) for p in [front/'app/page.tsx',front/'lib/mock-data.ts',front/'data/mock-venues.json',front/'deployment/Dockerfile.frontend-private',*(front/'app/api').rglob('route.ts')]};(front/'real-frontend-source.json').write_bytes(encoded(proof))
    result=dict(identity='52-real-provider-candidates-v1',profile=cohort['profile'],cohort=sha((roles/'cohort.json').read_bytes()),releaseEligible=False,promotionApproved=False,frontendTrustEnrolled=False,bases=cohort['baseImages'],contexts={'python':'roles','frontend':'frontend'},dockerfiles={'python':sha((roles/'Dockerfile').read_bytes()),'frontend':sha(df.encode())},inputs={name:sha((ROOT/name).read_bytes()) for name in ('deployment/prepare_real_candidate.py','deployment/prepare_real_frontend.py','deployment/build-private-frontend.mjs','deployment/frontend-private-entry.mjs')})
    (target/'candidate-build.json').write_bytes(encoded(result));return result
if __name__=='__main__':
    import sys
    d=prepare(*sys.argv[1:]);print(json.dumps(d,sort_keys=True))
