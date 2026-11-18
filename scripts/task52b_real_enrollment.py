"""Exact first-slot enrollment verification; no signer, live CLI or key reads.

Real trust is source-enrolled, never selected by environment/unsigned JSON.
The separately identified fixture entry cannot enroll the original path or a
remote peer. Same-user administrator/correlated authority rollback is outside
this local operator boundary, not claimed to be a hosted recovery service.
"""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime,timezone,timedelta
from copy import deepcopy
import json,os,stat,subprocess,tempfile
from scripts import task52b_generation_candidate as parent
from scripts import task52b_generation_policy as policy

core=parent.q.protocol.auth.core
Denied=core.Denied
ROOT=policy.ROOT
ORIGINAL=ROOT/'backend/.local/task52-model-evaluation'
TRUST_FILE=ROOT/'backend/.local/task52b-original-enrollment/trust.json'
BINDING_FILE=TRUST_FILE.with_name('operation.json')
VERSION='52b-original-journal-enrollment-v1'
PURPOSE='one_unreviewed_extension_repeated_r2_technical_diagnostic'
ROLES=('owner','rubric','readiness_permission','readiness','execute')
GROUP={'owner':'owner','readiness_permission':'owner','rubric':'security','readiness':'operator','execute':'operator'}


def approved_trust_sha256():
    # A future independently reviewed source enrollment must pin real public
    # roles/resources here, then obtain signatures for that exact new build.
    return None


def now():return datetime.now(timezone.utc)
def utc(value):return value.strftime('%Y-%m-%dT%H:%M:%SZ')
def canonical(v):return core.canonical(v)
def digest(v):return core.digest(v)


def private(path,maximum=1048576):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or s.st_size>maximum:raise Denied('Private enrollment file')
        raw=os.read(fd,maximum+1)
        if len(raw)!=s.st_size:raise Denied('Private enrollment length')
        return raw
    finally:os.close(fd)


def file_identity(path):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path or any(p.is_symlink() for p in (path,*path.parents)):raise Denied('Canonical path required')
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1:raise Denied('Owner-only canonical resource')
    return [s.st_dev,s.st_ino]


def directory(path):
    path=Path(path);s=path.lstat()
    if path.resolve()!=path or any(p.is_symlink() for p in (path,*path.parents)) or not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise Denied('Private canonical directory')


def verify_detached(packet,role,trust):
    """Same canonical Ed25519/OpenSSH verifier and bounds as Q4C."""
    core.fields(packet,'envelope signature');raw=packet['envelope'].encode();e=core.parse(raw)
    if role not in ROLES+('authority',):raise Denied('Unknown enrollment role')
    who=trust['roles']['security' if role=='authority' else GROUP[role]]
    namespace='whereto.task52b.original-firstslot.'+role+'.v1'
    core.fields(e,'version audience purpose role principal namespace scope journal nonce issuedAt expiresAt trustHash bindingHash data')
    core.exact([e['version'],e['audience'],e['purpose'],e['role'],e['principal'],e['namespace'],e['trustHash']],
        [VERSION,'52b-original-firstslot-'+('LAB' if trust['fixtureOnly'] else 'REAL'),PURPOSE,role,who['principal'],namespace,policy.stable(trust)])
    for k in ('scope','journal','nonce','bindingHash'):core.hash_field(e[k])
    if type(packet['signature'])is not str or not packet['signature'].isascii() or not 100<=len(packet['signature'])<=4000:raise Denied('Detached signature bounds')
    with tempfile.TemporaryDirectory(prefix='whereto-enrollment-public-verify-') as temporary:
        d=Path(temporary);(d/'allowed').write_text(f'{who["principal"]} namespaces="{namespace}" {who["key"]}\n');(d/'signature').write_text(packet['signature'])
        result=subprocess.run(['/usr/bin/ssh-keygen','-Y','verify','-f',str(d/'allowed'),'-I',who['principal'],'-n',namespace,'-s',str(d/'signature')],input=raw,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        if result.returncode:raise Denied('Invalid enrollment signature')
    return e


def valid_time(e,at):
    issued=core.stamp(e['issuedAt']);expires=core.stamp(e['expiresAt'])
    if not issued<=at<expires or not 0<(expires-issued).total_seconds()<=86400 or at.date()!=issued.date():raise Denied('Enrollment expired/future/day')


def check_trust(trust):
    core.fields(trust,'version fixtureOnly roles journal lock facts authority credentialEnrollment credentialMetadataSHA256 epoch minimumSequence')
    if trust['version']!=VERSION or type(trust['fixtureOnly'])is not bool or set(trust['roles'])!={'owner','security','operator'}:raise Denied('Trust profile')
    principals=[];keys=[]
    for record in trust['roles'].values():
        core.fields(record,'principal key');principals.append(record['principal']);keys.append(core.public_key(record['key']))
        if not core.PRINCIPAL.fullmatch(record['principal']):raise Denied('Principal identity')
    if len(set(principals))!=3 or len(set(keys))!=3:raise Denied('Independent role keys required')
    core.hash_field(trust['epoch'])
    if type(trust['minimumSequence'])is not int or trust['minimumSequence']<1:raise Denied('Explicit authority sequence')
    db=Path(trust['journal']);lock=Path(trust['lock']);facts=Path(trust['facts'])
    if db.name!='journal.sqlite' or lock!=db.with_name('experiment.lock') or facts==db.parent or facts.is_relative_to(db.parent):raise Denied('One original lock and separate facts required')
    if trust['fixtureOnly']:
        if db.parent==ORIGINAL or not db.parent.name.startswith('whereto-original-copy-') or not db.is_relative_to(Path(tempfile.gettempdir()).resolve()):raise Denied('Fixture cannot select real journal')
    elif db!=ORIGINAL/'journal.sqlite' or lock!=ORIGINAL/'experiment.lock' or facts!=ROOT/'backend/.local/task52b-original-enrollment/child':raise Denied('Exact real resource paths')
    if not trust['fixtureOnly'] and trust['credentialEnrollment']!=str(ROOT/'backend/.local/task52b-readiness/credential-enrollment-v1.json'):raise Denied('Existing credential enrollment only')
    directory(db.parent);file_identity(db);file_identity(lock)
    return trust


@dataclass(frozen=True)
class Enrollment:
    trustBytes:bytes
    bindingBytes:bytes
    trustSHA256:str
    buildSHA256:str
    fixture:bool

    @property
    def trust(self):return json.loads(self.trustBytes)
    @property
    def package(self):return json.loads(self.bindingBytes)
    @property
    def binding(self):return self.package['spec']
    @property
    def binding_hash(self):return policy.stable(self.binding)
    @property
    def journal(self):return Path(self.trust['journal'])
    @property
    def lock(self):return Path(self.trust['lock'])
    @property
    def facts(self):return Path(self.trust['facts'])
    @property
    def journal_hash(self):return self.binding['journalHash']
    @property
    def scope(self):return self.binding['scope']

    def authority(self):
        t=self.trust;packet=json.loads(private(Path(t['authority'])));e=verify_detached(packet,'authority',t);valid_time(e,now())
        if (e['scope'],e['journal'],e['bindingHash'])!=(self.scope,self.journal_hash,self.binding_hash):raise Denied('Authority scope binding')
        data=e['data']
        core.fields(data,'epoch sequence revokedKeyHashes')
        if data['epoch']!=t['epoch'] or type(data['sequence'])is not int or data['sequence']<t['minimumSequence']:raise Denied('Epoch/authority mismatch')
        if sorted(set(data['revokedKeyHashes']))!=data['revokedKeyHashes']:raise Denied('Revocation state')
        for h in data['revokedKeyHashes']:core.hash_field(h)
        if any(core.public_key(v['key']) in data['revokedKeyHashes'] for v in t['roles'].values()):raise Denied('Revoked enrollment signer')
        # Persistent, append-only observations prevent a locally observed sequence
        # from being rolled back while a consumed scope remains on disk.
        if self.facts.exists():
            seen=[int(p.stem.split('-')[-1]) for p in self.facts.glob('authority-seen-*.json')]
            if seen and data['sequence']<max(seen):raise Denied('Authority rollback')
        return data

    def signed(self,packet,role,at):
        self.authority();e=verify_detached(packet,role,self.trust);valid_time(e,at)
        if (e['scope'],e['journal'],e['bindingHash'])!=(self.scope,self.journal_hash,self.binding_hash):raise Denied('Signature scope/binding')
        data=e['data'];b=self.binding
        if role=='owner':expected={'bindingHash':self.binding_hash,'technicalPurposeApproved':True,'reservationMaximum':2500000,'operationMaximum':1,'semanticReview':'deferred','planningAuthorized':False}
        elif role=='rubric':expected={'bindingHash':self.binding_hash,'independentSecurityApproved':True,'realWriterApproved':True,'postAppendApproved':True,'semanticReview':'deferred','planningAuthorized':False}
        elif role=='readiness_permission':expected={'bindingHash':self.binding_hash,'additionalReadinessRequests':0}
        elif role=='readiness':expected={'bindingHash':self.binding_hash,'permissionHash':core.digest(self.package['packets']['readiness_permission']),'accountTermsAndFeesReviewed':True,'modelAliasCountApplicabilityReviewed':True}
        elif role=='execute':
            expected={'slot':policy.SLOT,'sourceHash':parent.q.identity.requests()[0]['sourceSHA256'],'payloadHash':policy.PAYLOAD_SHA,'inputBound':7752,'outputBound':2000,'reservation':2500000,'ownerHash':core.digest(self.package['packets']['owner']),'readinessHash':core.digest(self.package['packets']['readiness']),'previousReviewHash':core.ZERO}
        else:raise Denied('No semantic review or additional operation authority')
        core.exact(data,expected)
        return e,core.digest(packet)

    def recheck_current(self):
        # Full source/readiness audit already ran before credential/TLS access.
        # Reverify every signed positive authority and exact financial/time
        # boundary after TLS, without spending the network deadline recompiling.
        for role in ROLES:self.signed(self.package['packets'][role],role,now())
        projected=deepcopy(self.binding['financialPacket']);projected['operationID']='a'*64
        policy.validate_packet(projected,now(),expected_build=self.buildSHA256)

    def guard(self,active=True):
        from scripts import task52b_original_journal as journal
        journal.verify_build();t=self.trust;b=self.binding
        check_trust(t)
        if type(self.fixture)is not bool or self.fixture!=t['fixtureOnly'] or self.package['fixtureOnly']!=self.fixture:raise Denied('Fixture authority separation')
        if not self.fixture and (approved_trust_sha256() is None or policy.digest(self.trustBytes)!=approved_trust_sha256() or private(TRUST_FILE)!=self.trustBytes or private(BINDING_FILE)!=self.bindingBytes):raise Denied('Real source-enrolled authority required')
        if b['marker']['scope']!=self.scope or b['marker']['prefixHash']!=journal.PREFIX or self.journal_hash!=digest({'root':b['marker']['root'],'prefix':b['marker']['prefix']}):raise Denied('Original prefix/scope binding')
        if policy.stable(t)!=self.trustSHA256 or self.buildSHA256!=journal.build_sha() or b['sourceBuildSHA256']!=self.buildSHA256:raise Denied('Enrollment source binding')
        if file_identity(self.journal)!=b['journalIdentity'] or file_identity(self.lock)!=b['lockIdentity']:raise Denied('Journal/lock device inode mismatch')
        self.authority()
        if b.get('processingCategories')!={'serviceTier':'default','cache12hRequested':False,'toolsRequested':False,'separateReasoningFees':False,'otherFeesKnown':True}:raise Denied('Unknown processing/fee category')
        if b['epoch']!=t['epoch']:raise Denied('Enrollment epoch')
        # Current positive authority always uses a server-owned clock. Historical
        # fold verification uses the stored, signed fact time through signed().
        if active:
            for role in ('owner','rubric','readiness_permission','readiness','execute'):self.signed(self.package['packets'][role],role,now())
            projected=deepcopy(b['financialPacket']);projected['operationID']='a'*64  # Actual operation derives from durable SCOPE and execute signature, not unsigned caller input.
            policy.validate_packet(projected,now(),expected_build=self.buildSHA256)
            if projected['credentialIdentity']!=b['credentialIdentity'] or policy.digest(private(Path(t['credentialEnrollment'])))!=b['credentialIdentity']:raise Denied('Credential binding')
            if projected['writerIdentity']!=json.loads(parent.MANIFEST.read_bytes())['loadedCodeIdentities']['writer']:raise Denied('Writer identity')
            if not self.fixture:
                actual=policy.inspect_readiness()
                for k in ('credentialIdentity','countBundleSHA256','modelGETBundleSHA256'):
                    if projected[k]!=actual[k]:raise Denied('Current readiness binding')
                for name in ('modelEvidence','countEvidence','permissionEvidence'):
                    if datetime.fromisoformat(projected[name]['expiresAt'])>datetime.fromisoformat(actual['expiresAt']):raise Denied('Readiness deadline cannot be extended')
            else:
                if not self.package['fixtureOnly']:raise Denied('Fixture purpose')
        return b


def enroll_real():
    from scripts import task52b_original_journal as journal
    journal.verify_build()
    pin=approved_trust_sha256()
    if pin is None:raise Denied('Real trust is not source-enrolled; no credentials or journal write')
    raw=private(TRUST_FILE)
    if policy.digest(raw)!=pin:raise Denied('Approved trust fingerprint')
    t=json.loads(raw);check_trust(t)
    if t['fixtureOnly']:raise Denied('Fixture trust is never real authority')
    receipt=Enrollment(raw,private(BINDING_FILE),policy.stable(t),journal.build_sha(),False)
    receipt.guard();return receipt


def enroll_fixture(trust,binding):
    """Explicit offline port: complete historical COPY, never original paths."""
    check_trust(trust)
    if not trust['fixtureOnly'] or not binding['fixtureOnly']:raise Denied('Fixture enrollment only')
    from scripts import task52b_original_journal as journal
    receipt=Enrollment(canonical(trust),json.dumps(binding,sort_keys=True,separators=(',',':')).encode(),policy.stable(trust),journal.build_sha(),True)
    receipt.guard();return receipt
