"""Q1 artifact verifier and read-only reconstruction, never a paid runner.

No CLI, credential loader, provider factory, request payload builder, admission
issuer or ledger constructor. All incomplete semantic judgments stay unqualified.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/task52-q1-offline-manifest-v1.json'
MANIFEST_SHA='a2736b5412e8788b719c400f7121cec12e6359bc11ba327269b5af5eecb06f7b'
IDENTITY='52b-q1-offline-reconstruction-v1'
CONTRACT='52b-q1-qualification-v1'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())


def verify(*,identity=IDENTITY):
    if identity!=IDENTITY or sha(MANIFEST.read_bytes())!=MANIFEST_SHA:
        raise ValueError('Unknown or changed Q1 manifest')
    m=json.loads(MANIFEST.read_text())
    if m['identity']!=identity or m['contract']!=CONTRACT or m['paidDispatchAuthorized'] or m['planningAuthorized']:
        raise ValueError('Invalid Q1 identity or authority')
    for name,value in m['artifactHashes'].items():
        if sha((ROOT/name).read_bytes())!=value:raise ValueError('Q1 artifact/source mismatch')
    from scripts.task52_phase_b2_identity import verify as b2
    b2()
    from scripts import cloud_model52 as original
    try:original.corpus()
    except ValueError as error:
        if str(error)!='Reference source changed; review required: backend/journey.py':raise
    else:raise ValueError('Original paid gate must still refuse B2')
    rubric=json.loads((ROOT/'docs/task52-q1-rubric-v1.json').read_text())
    corpus=json.loads((ROOT/'docs/task52-evaluation-corpus.json').read_text())
    if rubric['caseCount']!=66 or len(rubric['cases'])!=66:raise ValueError('Q1 case count')
    if len(set(r['id'] for r in rubric['cases']))!=66:raise ValueError('Duplicate Q1 case')
    for r,c in zip(rubric['cases'],corpus['cases']):
        if r['id']!=c['id'] or r['sourceText']!=c['text'] or r['originalReferenceDigest']!=digest(c):
            raise ValueError('Q1 reference mismatch')
        if r['sourceSHA256']!=sha(c['text'].encode()) or set(r['fields'])!=set(rubric['dimensions']):
            raise ValueError('Q1 field/source mismatch')
        if r['independentReviewComplete']:raise ValueError('Frozen review draft cannot self-approve')
        for f in r['fields'].values():
            if f['applicability'] not in rubric['states'] or f['independentReview']!='pending':raise ValueError('Unknown field state')
            if f['applicability']=='not_applicable' and f['expected'] is not None:raise ValueError('Invalid N/A assertion')
            if f['applicability']!='not_applicable' and not f['sourceAnchors']:raise ValueError('Missing source evidence')
            if any(a.casefold() not in c['text'].casefold() for a in f['sourceAnchors']):raise ValueError('Unbound rubric anchor')
    return m


@contextmanager
def offline():
    """Trusted Python test I/O guards, NOT a hostile-code OS sandbox."""
    state=(ROOT/'backend/.local/task52-model-evaluation').resolve()
    original_connect=sqlite3.connect
    def connect(database,*a,**kw):
        name=str(database)
        if not (kw.get('uri') and name==f'file:{state}/journal.sqlite?mode=ro'):
            raise ValueError('Q1 SQLite access must be read-only')
        return original_connect(database,*a,**kw)
    with ExitStack() as s:
        s.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('Q1 no provider requests')))
        s.enter_context(patch('socket.socket.connect',side_effect=AssertionError('Q1 no sockets')))
        s.enter_context(patch.object(sqlite3,'connect',connect))
        yield


def private_hashes():
    state=ROOT/'backend/.local/task52-model-evaluation'
    return {str(p.relative_to(state)):sha(p.read_bytes()) for p in state.rglob('*') if p.is_file()}


def replay():
    m=verify()
    from backend.ai import parse_interpretation
    from backend.interpretation import InterpretationInput,interpret_request
    from backend.journey import LIMITATION
    from scripts import cloud_model52 as original
    from scripts import cloud_model52_ordering_v4 as policy
    cases={c['id']:c for c in json.loads((ROOT/'docs/task52-evaluation-corpus.json').read_text())['cases']}
    rubrics={c['id']:c for c in json.loads((ROOT/'docs/task52-q1-rubric-v1.json').read_text())['cases']}
    before=private_hashes();results=[]
    if digest(before)!=m['paidEvidence']['privateFileSetHash']:
        raise ValueError('Private source evidence identity mismatch')
    if (digest(original.schema())!=m['schema']['strictParserSchemaSHA256']
            or digest(original.wire_schema('openai'))!=m['schema']['originalV3WireHashes']['openai']):
        raise ValueError('Unknown strict schema identity')
    with offline():
        with sqlite3.connect(f"file:{ROOT}/backend/.local/task52-model-evaluation/journal.sqlite?mode=ro",uri=True) as db:
            if db.execute('pragma integrity_check').fetchone()!=('ok',):raise ValueError('Journal integrity')
            rows=db.execute('select * from attempts order by rowid').fetchall()
            if [digest(r) for r in rows]!=m['paidEvidence']['rowHashes'] or sha((ROOT/'backend/.local/task52-model-evaluation/journal.sqlite').read_bytes())!=m['paidEvidence']['journalSHA256']:
                raise ValueError('Immutable paid evidence mismatch')
            if len(rows)!=10 or rows[-1][3]!='recorded_halted' or sum(r[4] for r in rows)!=47366625:raise ValueError('Journal baseline mismatch')
        for row in rows:
            if row[0]!='openai':continue
            record=json.loads(row[5]);binding=next(x for x in m['responses'] if x['case']==row[1])
            if any(record.get(k)!=binding[k] for k in ('model','promptVersion','configurationHash','payloadHash')) or digest(record['response'])!=binding['responseHash']:
                raise ValueError('Unknown response/configuration binding')
            content,usage,status=original.Adapter('openai',None).decode(record['response'])
            if status!='complete':raise ValueError('Recorded output incomplete')
            ai=parse_interpretation(content)
            missing=original.missing_properties(json.loads(content),original.schema())
            unknown=original.missing_properties(json.loads(content),original.schema(),unknown=True)
            if missing or unknown:raise ValueError('Recorded wire structure drift')
            frozen=ai.model_dump(mode='json');case=cases[row[1]]
            order=policy.inspect_order(case['text'],ai.model_copy(deep=True))
            class Recorded:
                def interpret(self,text):
                    if text!=case['text']:raise ValueError('Wrong replay source')
                    return ai.model_copy(deep=True)
            result=interpret_request(InterpretationInput(text=case['text'],calendarTimezone=original.timezone_for(case)),provider=Recorded(),now=datetime.fromisoformat(m['clock']['referenceTime'].replace('Z','+00:00')))
            handoff=(result.executionStatus=='advanced_unavailable' and result.issues==[LIMITATION] and result.unsupported==[LIMITATION] and result.context is not None and result.interpretation.journey is not None)
            accepted=handoff or not (result.issues or result.unsupported or result.questions)
            legacy='accepted_advanced_handoff' if handoff else 'accepted_ordinary' if accepted else 'blocked_or_clarify'
            guard=('blocked_by_complete_legacy_validation' if not accepted else 'blocked_by_independent_ordering' if order['trustedGraph'] is None else 'candidate_acceptance_after_legacy_checks_not_planning_authority')
            raw='incorrect_provenance' if row[1]=='journey-07' else 'incorrect_unsupported_order' if row[1]=='extension-repeated' else 'agent_review_correct_not_independently_qualified'
            # These are frozen same-agent review annotations for seven exact
            # allowlisted responses, NOT an algorithm for judging new output.
            # Independent qualification stays null, even on a reviewed match.
            findings={k:('pending' if f['applicability']=='awaiting_review' else
                         'agent_absence_match' if f['applicability']=='not_applicable' else 'agent_match')
                      for k,f in rubrics[row[1]]['fields'].items()}
            if row[1]=='journey-07':findings['source_provenance']='agent_mismatch'
            if row[1]=='extension-repeated':
                for k in ('mandatory_order','unordered_flexible','hallucinations','source_provenance'):
                    findings[k]='agent_mismatch'
            results.append({'slot':[row[0],row[1],row[2]],'original':deepcopy(binding),
                'structuredValid':True,'raw':{'rubricFinding':raw,'fullyCorrectIndependent':None,'reviewerKind':'Codex same-agent reconstruction review',
                    'fieldReview':findings,'fieldReviewAutomated':False,'rubricCaseDigest':digest(rubrics[row[1]])},
                'legacy':{'disposition':legacy,'resultHash':digest(result.model_dump(mode='json')),'issuesCount':len(result.issues),'questionFields':[q.field for q in result.questions]},
                'proposedGuarded':{'disposition':guard,'orderingOutcome':order['outcome'],'issues':order['issues'],
                    'originalGraph':order['originalGraph'],'unsupportedModelEdges':order['unsupportedModelEdges'],
                    'provedRelationships':[[p['before'],p['after']] for p in order['source']['proofs']],
                    'normalization':order['normalization'],'planningAuthorized':False},
                'historicalMeasurements':{'completeLatencyMs':record['latencyMs'],'providerUsage':list(usage),'retainedNanodollars':row[4]},
                'reviewCoverage':'seven-case same-agent full-field inspection recorded in specification; mechanical replay proves structure/legacy/order only'})
            if frozen!=ai.model_dump(mode='json'):raise ValueError('Raw output mutated')
    after=private_hashes()
    if before!=after or len(after)!=324:raise ValueError('Private evidence changed')
    return {'identity':IDENTITY,'contract':CONTRACT,'manifestSHA256':MANIFEST_SHA,'runnerSHA256':sha(Path(__file__).read_bytes()),
            'scope':'current-runtime behavioral reconstruction, not exact historical execution or independent qualification',
            'results':results,'counts':{'responses':7,'structuredValid':7,'agentRubricCorrect':5,'rawFailures':2,'legacyAccepted':sum(r['legacy']['disposition']!='blocked_or_clarify' for r in results),'guardCandidateCompatible':sum(r['proposedGuarded']['disposition'].startswith('candidate_') for r in results),'independentSignoffs':0},
            'journal':{'sha256':after['journal.sqlite'],'privateFilesUnchanged':324,'attempts':10,'accountedNanodollars':47366625,'remainingNanodollars':11952633375,'persistentHalt':True},
            'providerRequests':0,'paidDispatchAuthorized':False,'planningAuthorized':False}
