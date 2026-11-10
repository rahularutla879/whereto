"""Diagnostic synthetic-only authorization adapter; no signer/enrollment/issuer.

Reuse Q4C's canonicalization, trust/key separation, bounds, role validators and
OpenSSH verification algorithm. Only plan, signed audience/purpose and binding
change. Frozen Q4C globals/functions are never patched.
"""
from types import FunctionType
from scripts import task52_q4c_auth as core
from scripts.task52_diag_identity import plan

VERSION='52b-v51-diagnostic-envelope-v1'
AUDIENCE='52b-v51-diagnostic-OFFLINE-SYNTHETIC-v1'
from scripts.task52_diag_identity import PURPOSE
# The pinned synthetic Trust/role format and role-specific namespaces are reused;
# the signed envelope audience/purpose/build provide the new policy domain.
Trust=core.Trust
Denied=core.Denied
Verified=core.Verified
ROLES=core.ROLES
ZERO=core.ZERO
canonical=core.canonical
parse=core.parse
exact=core.exact
digest=core.digest
def owner_data():
    from scripts.task52_diag_identity import defect_hash
    return {**core.owner_data(),'diagnosticPurpose':PURPOSE,'allowlistedDefectHash':defect_hash()}
fields=core.fields
stamp=core.stamp
public_key=core.public_key
subprocess=core.subprocess  # Same public-verifier process primitive for timeout tests.


def bind_function(function,namespace):
    """Same verified code object, new private fixed dependency namespace."""
    result=FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    result.__kwdefaults__=function.__kwdefaults__
    return result


_context={**vars(core),'plan':plan}
rubric_data=bind_function(core.rubric_data,_context)
permission_data=bind_function(core.permission_data,_context)
_context.update(rubric_data=rubric_data,permission_data=permission_data)
_validate_parent=bind_function(core.validate_data,_context)


def validate_data(role,data,now):
    from scripts.task52_diag_identity import defect_hash
    if role=='owner':
        exact(data,owner_data())
    elif role=='review':
        fields(data,'operationID outcomeHash responseHash judgments decision diagnostic')
        _validate_parent(role,{k:v for k,v in data.items() if k!='diagnostic'},now)
        fields(data['diagnostic'],'purpose defectHash systemIncompatible planningAuthorized')
        if type(data['diagnostic']['systemIncompatible'])is not bool:raise Denied('Explicit diagnostic review required')
        exact(data['diagnostic']['purpose'],PURPOSE)
        exact(data['diagnostic']['planningAuthorized'],False)
        if data['diagnostic']['defectHash']not in (None,defect_hash()):raise Denied('Unknown reviewed defect')
    else:_validate_parent(role,data,now)


# Q4C's _verify has a literal import of its frozen binding; the small domain
# adapter below preserves its checks and exact OpenSSH call, using this binding.
def _verify(packet,role,trust,now):
    from scripts.task52_diag_identity import binding
    if type(trust)is not Trust or role not in ROLES:raise Denied('Explicit trust/role required')
    t,r=trust.checked();fields(packet,'envelope signature')
    if type(packet['envelope'])is not str or type(packet['signature'])is not str or not 100<=len(packet['signature'])<=4000:
        raise Denied('Detached signature required')
    raw=packet['envelope'].encode('utf-8');e=parse(raw)
    fields(e,'version audience purpose role principal namespace scope journal nonce issuedAt expiresAt trustHash revocationHash binding data')
    entry=t['roles'][role]
    exact([e['version'],e['audience'],e['purpose'],e['role'],e['principal'],e['namespace'],e['trustHash'],e['revocationHash']],
          [VERSION,AUDIENCE,PURPOSE,role,entry['principal'],entry['namespace'],trust.document_hash,trust.revocation_hash])
    core.hash_field(e['scope']);core.hash_field(e['journal']);core.hash_field(e['nonce']);exact(e['binding'],binding())
    issued,expires=stamp(e['issuedAt']),stamp(e['expiresAt'])
    if now.tzinfo is None or not issued<=now<expires or not 0<(expires-issued).total_seconds()<=86400:raise Denied('Expired/future scope')
    if public_key(entry['key']) in r['revokedKeyHashes']:raise Denied('Revoked signer')
    validate_data(role,e['data'],now)
    if not packet['signature'].isascii():raise Denied('Signature armor')
    with core.tempfile.TemporaryDirectory(prefix='whereto-diag-public-verify-') as directory:
        d=core.Path(directory);allowed=d/'allowed';sig=d/'signature';revoked=d/'revoked'
        allowed.write_text(f'{entry["principal"]} namespaces="{entry["namespace"]}" {entry["key"]}\n')
        sig.write_text(packet['signature']);revoked.write_text(''.join(x['key']+'\n' for x in t['roles'].values() if public_key(x['key']) in r['revokedKeyHashes']))
        try:
            check=core.subprocess.run(['/usr/bin/ssh-keygen','-Y','verify','-f',str(allowed),'-I',entry['principal'],
                '-n',entry['namespace'],'-s',str(sig),'-r',str(revoked)],input=raw,
                stdout=core.subprocess.DEVNULL,stderr=core.subprocess.DEVNULL,timeout=5,
                env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        except (OSError,core.subprocess.TimeoutExpired):raise Denied('OpenSSH verification unavailable') from None
        if check.returncode:raise Denied('Invalid detached signature')
    return Verified(role,raw,digest(packet))


verify=bind_function(core.verify,{**vars(core),'_verify':_verify})
