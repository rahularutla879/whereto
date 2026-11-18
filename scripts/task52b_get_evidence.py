"""Read-only original-build verification of one already consumed model GET.

The later count build pins this selector. Original code is verified from local
Git objects, never executed, repinned to current files, or checked out. No HTTP
or credential-value loading is available here.
"""
from base64 import b64decode
from pathlib import Path
import json,re,subprocess
from scripts import task52b_readiness_enrolled as e
from backend.provider_responses import HTTPResult

ROOT=Path(__file__).resolve().parents[1]
q=e.q


def blobs(commit,names):
    if not re.fullmatch('[0-9a-f]{40}',commit) or any(not re.fullmatch('[A-Za-z0-9_./-]+',n) or '..' in n.split('/') or n.startswith('/') for n in names):
        raise q.Refused('prior_get_archive_path')
    try:
        result=subprocess.run(['/usr/bin/git','cat-file','--batch'],cwd=ROOT,
            input=''.join(commit+':'+n+'\n' for n in names).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=10)
        data=result.stdout;out={};offset=0
        for name in names:
            end=data.index(b'\n',offset);header=data[offset:end].split();size=int(header[2])
            if header[1]!=b'blob' or not 0<=size<=2_000_000:raise ValueError()
            offset=end+1;out[name]=data[offset:offset+size];offset+=size
            if data[offset:offset+1]!=b'\n':raise ValueError()
            offset+=1
        if offset!=len(data):raise ValueError()
        return out
    except (OSError,ValueError,IndexError,subprocess.SubprocessError):
        raise q.Refused('prior_get_source_archive') from None


def archived_build(binding):
    name=binding['originalManifest'];commit=binding['executionCommit']
    raw=blobs(commit,[name])[name]
    if e.digest(raw)!=binding['sourceBuildSHA256']:raise q.Refused('prior_get_original_build')
    build=json.loads(raw);files=build['filesSHA256'];boot='scripts/task52b_run_model_get_once.py'
    source=blobs(commit,list(files)+[boot])
    if any(e.digest(source[n])!=h for n,h in files.items()):raise q.Refused('prior_get_original_sources')
    text=source[boot].decode();m=re.search(r"(?m)^MANIFEST_SHA = '([0-9a-f]{64})'$",text)
    if m is None or m.group(1)!=binding['sourceBuildSHA256'] or e.digest((text[:m.start(1)]+'__BUILD_SHA__'+text[m.end(1):]).encode())!=build['bootstrapTemplateSHA256']:
        raise q.Refused('prior_get_original_bootstrap')
    if e.digest(Path(e.sys.executable).resolve().read_bytes())!=build['pythonExecutableSHA256']:
        raise q.Refused('prior_get_original_interpreter')
    # The count's own source-pinned build independently verifies its current CA.
    # Preserve the historical CA identity, rather than treating a fixture CA as
    # the CA that authenticated the original GET.
    if binding['originalCAFileSHA256']!=build['caBundleSHA256']:raise q.Refused('prior_get_original_ca')
    return build


def verify(path,now,fresh):
    binding=json.loads(path.read_bytes())
    if binding.get('project')!=e.PROJECT or binding.get('model')!=q.MODEL or binding.get('countSHA256')!=q.COUNT_SHA:
        raise q.Refused('prior_get_selector_binding')
    build=archived_build(binding)
    operation=binding['operation']
    if not re.fullmatch('[A-Za-z0-9_-]+',operation):raise q.Refused('prior_get_operation')
    directory=e.BASE/operation;e.private_directory(directory)
    pins=binding['privateFilesSHA256']
    expected={'scope.json','launcher-claim.json','runtime.json','supervisor-claim.json','consumed.json','intent.json','wire-consumed.json','response-1.json','validated.json','result.json','supervisor.json'}
    if set(pins)!=expected or {p.name for p in directory.iterdir()}!=expected:raise q.Refused('prior_scope_inventory')
    records={}
    for name,h in pins.items():
        raw=e.private_read(directory/name)
        if e.digest(raw)!=h:raise q.Refused('prior_scope_integrity')
        records[name]=json.loads(raw)
    raw_auth=e.private_read(e.BASE/(operation+'.send-authorization.json'))
    if e.digest(raw_auth)!=binding['authorizationSHA256']:raise q.Refused('prior_get_authorization_integrity')
    auth=json.loads(raw_auth);s=records['scope.json'];result=records['result.json'];v=records['validated.json'];raw=records['response-1.json']
    fixed={'operation':operation,'project':e.PROJECT,'model':q.MODEL,'method':'GET','endpoint':q.requests()[0].url,'bodySHA256':e.digest(b''),'getMaximum':1,'postMaximum':0,'inferenceMaximum':0,'retries':0}
    if any(type(s.get(k))is not type(value) or s.get(k)!=value for k,value in fixed.items()):raise q.Refused('prior_get_scope_binding')
    identity=e.digest(e.private_read(e.PRIVATE_ENROLLMENT));scope_hash=pins['scope.json'];build_hash=binding['sourceBuildSHA256']
    if (s['buildSHA256']!=build_hash or s['credentialIdentity']!=identity or binding['credentialIdentity']!=identity or
            s['supervisorIdentity']!=build['filesSHA256']['scripts/task52b_model_get.py'] or
            any(auth.get(k)!=value for k,value in {'operation':operation,'buildSHA256':build_hash,'scopeSHA256':scope_hash,'credentialIdentity':identity,'explicitOwnerSendConfirmation':True,'getMaximum':1,'postMaximum':0,'inferenceMaximum':0,'retries':0,'originalEvidenceBundleSHA256':s['originalEvidenceBundleSHA256']}.items())):
        raise q.Refused('prior_get_authority_binding')
    if (records['consumed.json']['scopeSHA256']!=scope_hash or records['wire-consumed.json']['intentSHA256']!=pins['intent.json'] or
            records['intent.json']!={'operation':operation,'method':'GET','endpoint':fixed['endpoint'],'bodySHA256':fixed['bodySHA256'],'buildSHA256':build_hash}):raise q.Refused('prior_get_consumption')
    rt=records['runtime.json'];launch=records['launcher-claim.json'];supervisor=records['supervisor.json'];claim=records['supervisor-claim.json']
    if (rt['buildSHA256']!=build_hash or rt['identityScheme']!=build['loadedIdentityScheme'] or rt['loadedWireIdentitySHA256']!=build['loadedCodeIdentities']['wire'] or
            type(rt['workerPID'])is not int or rt['workerPID']<=0 or type(launch['supervisorPID'])is not int or launch['supervisorPID']<=0 or
            launch['buildSHA256']!=build_hash or launch['operation']!=operation or claim!={'operation':operation,'supervisorIdentity':s['supervisorIdentity']} or
            supervisor.get('exit')!=0 or supervisor.get('reason')!='worker_exit'):raise q.Refused('prior_get_supervision')
    body=b64decode(raw['bodyBase64'],validate=True);h=e.digest(body)
    if raw['status']!=200 or raw['complete']is not True or raw.get('sendStarted')is not True or raw.get('errorCategory')is not None or raw.get('credentialEchoRefused')is not False or raw['bodyBytes']!=len(body) or h!=binding['rawResponseSHA256'] or h!=raw['bodySHA256']:
        raise q.Refused('prior_get_response')
    value=q.validate_response(q.requests()[0],HTTPResult(200,body,True,raw['contentType']))
    expiry=fresh(raw['at'],now).isoformat()
    if (v['value']!=value or v['rawSHA256']!=h or v['observedAt']!=raw['at'] or v['expiresAt']!=expiry or
            binding['observedAt']!=raw['at'] or binding['expiresAt']!=expiry or
            any(result.get(k)!=value for k,value in {'operation':operation,'result':'completed','status':200,'model':q.MODEL,'rawSHA256':h,'observedAt':raw['at'],'expiresAt':expiry,'getMaximum':1,'postRequests':0,'inference':0,'retries':0}.items())):
        raise q.Refused('prior_get_validation')
    for record in (auth,launch,rt,records['consumed.json'],records['wire-consumed.json'],raw,v,supervisor):fresh(record.get('at',record.get('approvedAt')),now)
    if auth['expiresAt']!=fresh(auth['approvedAt'],now).isoformat():raise q.Refused('prior_get_authorization_expiry')
    return {'model':q.MODEL,'rawSHA256':h,'observedAt':raw['at'],'expiresAt':expiry,'credentialIdentity':identity,'bundleSHA256':e.digest(path.read_bytes()),'priorBuildSHA256':build_hash}
