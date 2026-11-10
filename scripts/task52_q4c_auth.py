"""Q4C detached-signature verifier; OFFLINE audience only, no signer/issuer.

Trust hash pins must come from a trusted caller. This prototype's caller is a
synthetic fixture; no real trust enrollment, paid authority or OS isolation.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path

from scripts import task52_q1 as q1
from scripts.task52_q4a import plan

VERSION = '52b-q4c-envelope-v1'
AUDIENCE = '52b-q4c-OFFLINE-SYNTHETIC-v1'
ROLES = {'owner':'owner-scope.v1','rubric':'rubric-review.v1',
         'readiness_permission':'readiness-permission.v1','readiness':'readiness-evidence.v1',
         'execute':'execute-one.v1','review':'response-review.v1'}
HEX = re.compile(r'[0-9a-f]{64}\Z')
PRINCIPAL = re.compile(r'q4c-[a-z0-9-]{1,50}\Z')
ZERO = '0'*64


class Denied(ValueError):pass


def canonical(value):
    def bounded(v, depth=0):
        if depth>15:raise Denied('Envelope nesting')
        if isinstance(v,dict):
            if len(v)>100 or any(type(k)is not str for k in v):raise Denied('Object bounds')
            for k,x in v.items():bounded(k,depth+1);bounded(x,depth+1)
        elif isinstance(v,list):
            if len(v)>66:raise Denied('Array bounds')
            for x in v:bounded(x,depth+1)
        elif type(v)is str:
            if not v.isascii() or len(v)>1000:raise Denied('ASCII field bounds')
        elif v is not None and type(v)not in (bool,int):raise Denied('No floats or custom values')
        elif type(v)is int and not -(2**63)<v<2**63:raise Denied('Integer bounds')
    bounded(value)
    result=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if len(result)>50000:raise Denied('Envelope size')
    return result


def parse(raw):
    if type(raw)is not bytes or len(raw)>50000:raise Denied('Canonical bytes required')
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise Denied('Duplicate JSON key')
            d[k]=v
        return d
    def number(_):raise Denied('Noninteger JSON number')
    try:v=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_float=number,parse_constant=number)
    except (ValueError,UnicodeError,RecursionError):raise Denied('Invalid canonical JSON') from None
    if canonical(v)!=raw:raise Denied('Noncanonical signed bytes')
    return v


def exact(a,b):
    if canonical(a)!=canonical(b):raise Denied('Exact scope/type mismatch')


def digest(value):
    # Packet envelope is an already-validated canonical JSON STRING, potentially
    # longer than one semantic field. Hash the wrapper without re-parsing it.
    return q1.digest(value)


def hash_field(value):
    if type(value)is not str or not HEX.fullmatch(value):raise Denied('Invalid hash/nonce')


def stamp(value):
    if type(value)is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value):raise Denied('UTC timestamp required')
    try:return datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise Denied('Invalid timestamp') from None


def fresh(value,now):
    t=stamp(value)
    if now.tzinfo is None or not 0<=(now-t).total_seconds()<=86400 or t.date()!=now.astimezone(timezone.utc).date():
        raise Denied('Readiness stale/future/wrong UTC day')


def public_key(key):
    if type(key)is not str or not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]{68}',key):raise Denied('Only exact Ed25519 public keys')
    try:blob=base64.b64decode(key.split()[1],validate=True)
    except ValueError:raise Denied('Malformed public key') from None
    if blob!=struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32)+blob[-32:] or len(blob)!=51:
        raise Denied('Malformed Ed25519 blob')
    return q1.sha(blob)


@dataclass(frozen=True)
class Trust:
    document: bytes
    document_hash: str
    revocations: bytes
    revocation_hash: str

    def checked(self):
        if q1.sha(self.document)!=self.document_hash or q1.sha(self.revocations)!=self.revocation_hash:
            raise Denied('Trust/revocation pin mismatch')
        t=parse(self.document);r=parse(self.revocations)
        if set(t)!={'version','audience','syntheticOnly','revocationHash','roles'} or set(r)!={'version','revokedKeyHashes'}:
            raise Denied('Trust schema')
        exact([t['version'],t['audience'],t['syntheticOnly'],t['revocationHash']],
              ['52b-q4c-trust-v1',AUDIENCE,True,self.revocation_hash])
        if r['version']!='52b-q4c-revocations-v1' or type(r['revokedKeyHashes'])is not list:
            raise Denied('Revocation schema')
        for h in r['revokedKeyHashes']:hash_field(h)
        if sorted(set(r['revokedKeyHashes']))!=r['revokedKeyHashes'] or set(t['roles'])!=set(ROLES):raise Denied('Trust roles/revocations')
        for role,entry in t['roles'].items():
            if set(entry)!={'principal','key','namespace'} or not PRINCIPAL.fullmatch(entry['principal']):raise Denied('Trust principal')
            exact(entry['namespace'],'whereto.task52b.'+ROLES[role]);public_key(entry['key'])
        # Independent role groups must have distinct principals AND keys.
        groups=[('owner','readiness_permission'),('rubric','review'),('readiness','execute')]
        for group in groups:exact(t['roles'][group[0]]['key'],t['roles'][group[1]]['key']);exact(t['roles'][group[0]]['principal'],t['roles'][group[1]]['principal'])
        entries=[t['roles'][g[0]] for g in groups]
        if len({e['key'] for e in entries})!=3 or len({e['principal'] for e in entries})!=3:raise Denied('Signer groups must be separate')
        return t,r


def fields(value,keys):
    if type(value)is not dict or set(value)!=set(keys.split()):raise Denied('Missing/unknown fields')


def owner_data():
    return {'attempts':5,'reservation':2500000,'childCap':12500000,'aggregateCap':12000000000,
            'globalAttempts':594,'providerAttempts':198,'inputCap':12000,'outputCap':2000,
            'concurrency':1,'retries':0,'historicalHaltAcknowledged':True,'criticalFailureAcknowledged':True}


def rubric_data():
    p=plan()
    return {'independentOfAuthor':True,'historicalFailuresReviewed':True,
            'cases':[{'slot':s['slot'],'rubricHash':s['rubricCaseDigest'],
                      'judgments':{k:'agree' for k in s['Q1FieldExpectations']}} for s in p['slots']]}


def permission_data():return {'operations':['model_metadata','account_review','complete_input_count'],
                              'payloadHashes':[s['payloadHash'] for s in plan()['slots']]}


def validate_data(role,data,now):
    p=plan();slots=p['slots']
    if role=='owner':exact(data,owner_data())
    elif role=='rubric':exact(data,rubric_data())
    elif role=='readiness_permission':exact(data,permission_data())
    elif role=='readiness':
        fields(data,'permissionHash observedAt counts outputCap checks');hash_field(data['permissionHash']);fresh(data['observedAt'],now)
        if type(data['counts'])is not list or len(data['counts'])!=5 or any(type(n)is not int or not 0<n<=9952 for n in data['counts']):raise Denied('Complete input counts')
        exact(data['outputCap'],2000)
        exact(data['checks'],{k:True for k in ('key','keyExpiry','credits','rechargeOff','prices','processing','rates','model')})
    elif role=='execute':
        fields(data,'slot sourceHash payloadHash inputBound outputBound reservation ownerHash readinessHash previousReviewHash')
        s=next((s for s in slots if canonical(s['slot'])==canonical(data['slot'])),None)
        if not s:raise Denied('Wrong original slot')
        exact([data['sourceHash'],data['payloadHash'],data['inputBound'],data['outputBound'],data['reservation']],
              [s['sourceSHA256'],s['payloadHash'],12000,2000,2500000])
        for k in ('ownerHash','readinessHash','previousReviewHash'):hash_field(data[k])
    elif role=='review':
        fields(data,'operationID outcomeHash responseHash judgments decision')
        for k in ('operationID','outcomeHash','responseHash'):hash_field(data[k])
        if type(data['judgments'])is not dict or set(data['judgments'])!=set(slots[0]['Q1FieldExpectations']):raise Denied('Complete24-field review required')
        if any(type(v)is not str or v not in ('agree','disagree','unresolved') for v in [*data['judgments'].values(),data['decision']]):raise Denied('Unknown review outcome')
    else:raise Denied('Unknown role')


@dataclass(frozen=True)
class Verified:
    role: str
    envelope: bytes
    packet_hash: str
    execution_authorized: bool = False


def _verify(packet,role,trust,now):
    """Only public verification. Caller must separately enforce durable replay."""
    from scripts.task52_q4c_identity import binding
    if type(trust)is not Trust or role not in ROLES:raise Denied('Explicit trust/role required')
    t,r=trust.checked();fields(packet,'envelope signature')
    if type(packet['envelope'])is not str or type(packet['signature'])is not str or not 100<=len(packet['signature'])<=4000:
        raise Denied('Detached signature required')
    raw=packet['envelope'].encode('utf-8');e=parse(raw)
    fields(e,'version audience purpose role principal namespace scope journal nonce issuedAt expiresAt trustHash revocationHash binding data')
    entry=t['roles'][role]
    exact([e['version'],e['audience'],e['purpose'],e['role'],e['principal'],e['namespace'],e['trustHash'],e['revocationHash']],
          [VERSION,AUDIENCE,'synthetic_evaluation_only',role,entry['principal'],entry['namespace'],trust.document_hash,trust.revocation_hash])
    hash_field(e['scope']);hash_field(e['journal']);hash_field(e['nonce']);exact(e['binding'],binding())
    issued,expires=stamp(e['issuedAt']),stamp(e['expiresAt'])
    if now.tzinfo is None or not issued<=now<expires or not 0<(expires-issued).total_seconds()<=86400:raise Denied('Expired/future scope')
    if public_key(entry['key']) in r['revokedKeyHashes']:raise Denied('Revoked signer')
    validate_data(role,e['data'],now)
    if not packet['signature'].isascii():raise Denied('Signature armor')
    # No shell, SSH agent, personal .ssh paths, private keys or provider I/O.
    with tempfile.TemporaryDirectory(prefix='whereto-q4c-public-verify-') as directory:
        d=Path(directory);allowed=d/'allowed';sig=d/'signature';revoked=d/'revoked'
        allowed.write_text(f'{entry["principal"]} namespaces="{entry["namespace"]}" {entry["key"]}\n')
        sig.write_text(packet['signature']);revoked.write_text(''.join(x['key']+'\n' for x in t['roles'].values() if public_key(x['key']) in r['revokedKeyHashes']))
        try:
            check=subprocess.run(['/usr/bin/ssh-keygen','-Y','verify','-f',str(allowed),'-I',entry['principal'],
                '-n',entry['namespace'],'-s',str(sig),'-r',str(revoked)],input=raw,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,
                env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        except (OSError,subprocess.TimeoutExpired):raise Denied('OpenSSH verification unavailable') from None
        if check.returncode:raise Denied('Invalid detached signature')
    return Verified(role,raw,digest(packet))


def verify(packet,role,trust,now):
    try:
        return _verify(packet,role,trust,now)
    except Denied:
        raise
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError,RecursionError,struct.error):
        raise Denied('Malformed or unknown authorization identity') from None
