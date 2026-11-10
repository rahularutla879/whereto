"""Read-only Q3 proposal construction. Not an issuer, approval or live runner.

No new paid-state file, SQLite write, transport, credentials, count or metadata
operation. The in-memory state machine exists only in backend/test_task52_q3.py.
"""
from contextlib import closing
from copy import deepcopy
import json
import sqlite3
from scripts import task52_q1 as q1
from scripts import cloud_model52 as e
from scripts import cloud_model52_proposal as prompt
from scripts import cloud_model52_ordering_v4 as order

IDENTITY='52b-q3-openai-b2-v4-guarded-PROPOSED-v1'
SLOTS=(('extension-repeated',2),('journey-04',2),('extension-partial',2),('journey-06',2),('journey-21',1))
RESERVATION=2500000
EXTRA_CAP=12500000
REASONS={
    'extension-repeated':'First, challenge the known unsafe extra edge on the next original repetition. Three occurrences, only museum1→coffee2, origin return and inclusive180. Any raw critical error stops even when the guard catches it.',
    'journey-04':'Exact mandatory SUNY identity then coffee, with both-stop source-owned direction and no invented geography/date.',
    'extension-partial':'Only pharmacy→bank; required coffee remains independently ordered, not optional.',
    'journey-06':'Mandatory groceries and optional coffee, no mandatory order. Explicit new r2 proposal, not reuse of the old unsent r1 authorization.',
    'journey-21':'Contradictory pharmacy/bank directions must clarify without a published graph or plan. A safe response must retain both requirements, not pick one.'}
STOP_CONDITIONS=[
    'Authentication/provider/schema/permission error, refusal or incomplete/truncated/invalid structure.',
    'Any critical raw stop/identity/order/optionality/return/duration/deadline error, even if safely blocked.',
    'Unsafe legacy acceptance, unsupported guarded edge, or any unresolved semantic field/review.',
    'Unexpected clarification or normalization; no field deletion/repair to obtain a pass.',
    'Known mappings/endpoint identity not independently preserved; legacy start/finish deletion cannot be scored correct.',
    'No complete independently reviewed disposition for previous response.',
    'Source/schema/prompt/configuration/approval/baseline/payload hash mismatch, unknown response provenance, duplicate or wrong next slot.',
    'Any uncertain reserved/dispatch state, crash, timeout, locked runner or persistent child halt.',
    'Expired/future/incorrect-day readiness or insufficient permissions/credits/rate limits/terms.',
    'Any original/incremental attempt, token, full-reservation or spend ceiling refusal; prices above the proposed reservation assumptions.'
]


def baseline():
    m=q1.verify();before=q1.private_hashes()
    if e.digest(before)!=m['paidEvidence']['privateFileSetHash']:raise ValueError('Original private evidence changed')
    with q1.offline(),closing(sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True)) as db:
        if db.execute('pragma integrity_check').fetchone()!=('ok',):raise ValueError('Journal integrity')
        rows=db.execute('select * from attempts order by rowid').fetchall()
        root=db.execute('select config from metadata').fetchone()[0]
    if ([e.digest(r) for r in rows]!=m['paidEvidence']['rowHashes'] or e.digest(root)!=m['paidEvidence']['rootHash']
        or len(rows)!=10 or rows[-1][3]!='recorded_halted' or sum(r[4] for r in rows)!=47366625):
        raise ValueError('Expected original ten-row halted baseline; stop, never reset')
    if before!=q1.private_hashes():raise ValueError('Read-only inspection changed private evidence')
    return {'journalSHA256':before['journal.sqlite'],'rootHash':e.digest(root),
        'rows':[{'ordinal':i+1,'slot':list(r[:3]),'rowHash':e.digest(r),'originalState':r[3],
                 'recordHash':e.digest(json.loads(r[5]))} for i,r in enumerate(rows)],
        'correctionAndPrivateEvidenceSetHash':e.digest(before),'correctionFileHashes':m['paidEvidence']['correctionFileHashes'],
        'privateFiles':324,'counts':{'openai':7,'google':2,'anthropic':1},'attempts':10,'accountedNanodollars':47366625,
        'remainingNanodollars':11952633375,'persistentHistoricalHalt':True,'newReservations':0}


def proposal():
    b=baseline();m=json.loads(q1.MANIFEST.read_text());v4=json.loads((e.ROOT/'docs/task52-v4-openai-approved-continuation.json').read_text())
    corpus=json.loads(e.CORPUS.read_text());rubrics={c['id']:c for c in json.loads((e.ROOT/'docs/task52-q1-rubric-v1.json').read_text())['cases']}
    consumed={tuple(r['slot']) for r in b['rows']}
    version={'identity':IDENTITY,'purpose':'synthetic offline evaluation only; future paid purpose requires explicit approval',
        'runtime':'52b-runtime-phase-b2','runtimeManifestHash':q1.sha((e.ROOT/'docs/task52-runtime-phase-b2.json').read_bytes()),
        'reconstruction':'52b-behavior-reconstruction-duration-b2-v1','historicalEnvironmentExact':False,
        'canonicalPydanticSchemaHash':m['schema']['canonicalPydanticSHA256'],'strictParserSchemaHash':m['schema']['strictParserSchemaSHA256'],
        'wireSchemaHash':e.digest(e.wire_schema('openai')),'originalCorpusHash':e.CORPUS_SHA,
        'Q1Contract':q1.CONTRACT,'Q1ManifestHash':q1.MANIFEST_SHA,'Q1RubricHash':q1.sha((e.ROOT/'docs/task52-q1-rubric-v1.json').read_bytes()),
        'promptVersion':v4['promptVersion'],'promptHash':v4['promptHash'],'originalV4ConfigurationHash':v4['configurationHash'],
        'semanticScorer':v4['scorer'],'orderingPolicy':order.VERSION,'orderingPolicyHash':q1.sha((e.ROOT/'scripts/cloud_model52_ordering_v4.py').read_bytes()),
        'originalJournalRootHash':b['rootHash'],'referenceTime':corpus['referenceTime'],'clockPolicy':corpus['clockPolicy'],
        'rawLegacyGuardedAxes':['unmodified raw-model/full-field review','complete actual B2 legacy disposition','raw V4 proof combined conservatively with complete legacy disposition'],
        'futureEvaluatorImplementationHash':None,
        'futureResponseHashPolicy':'Bind complete immutable provider response and separately decoded output to operation/slot/source/payload/configuration; compute only after response, never invent future response hashes.',
        'inferenceEndpoint':'https://api.openai.com/v1/responses','inferenceMethod':'POST',
        'authenticationScope':'existing restricted evaluation-project key, ignored backend config only; no key or headers in artifacts',
        'redirectsAllowed':False,'countingEndpointForSeparatelyApprovedReadiness':'POST https://api.openai.com/v1/responses/input_tokens',
        'guardIsProductionEnforcement':False,'model':'gpt-6-luna','inputCap':12000,'outputCap':2000,'reasoning':{'effort':'none'},
        'temperature':0,'serviceTier':'default','store':False,'tools':False,'concurrency':1,'retries':0}
    config_hash=e.digest(version);slots=[]
    for ordinal,(case_id,repeat) in enumerate(SLOTS,1):
        if ('openai',case_id,repeat) in consumed:raise ValueError('Consumed slot')
        case=next(c for c in corpus['cases'] if c['id']==case_id);rubric=rubrics[case_id]
        unresolved=[k for k,f in rubric['fields'].items() if f['applicability']=='awaiting_review']
        body=prompt.payload('openai',case['text'])
        if e.digest(body['input'][:-1]+[{'role':'user','content':''}])!=version['promptHash']:
            raise ValueError('Reviewed prompt/example identity changed')
        slots.append({'ordinal':ordinal,'slot':['openai',case_id,repeat],'source':case['text'],'sourceSHA256':rubric['sourceSHA256'],
            'originalCaseDigest':e.digest(case),'payloadHash':e.digest(body),'successorConfigurationHash':config_hash,
            'promptVersion':version['promptVersion'],'promptHash':version['promptHash'],'rubricCaseDigest':e.digest(rubric),
            'Q1FieldExpectations':deepcopy(rubric['fields']),'unresolvedQ1Fields':unresolved,'why':REASONS[case_id],
            'independentRubricApproved':False,'independentHistoricalFailuresReviewed':False,'currentlyAdmissibleForPaidDispatch':False,
            'futureMaximumInputTokenReservation':12000,'futureMaximumOutputTokenReservation':2000,
            'futureFullReservationNanodollars':RESERVATION,'freshCompleteInputCount':None,
            'expectedOutcome':'source-supported contradiction clarification, no plan/graph publication' if case_id=='journey-21' else 'correct complete extraction plus appropriate unresolved-context handoff, not itinerary authorization',
            'stopConditions':STOP_CONDITIONS})
    if any(s['unresolvedQ1Fields'] for s in slots):raise ValueError('Selected unresolved Q1 field; inadmissible')
    excluded=next(c for c in corpus['cases'] if c['id']=='journey-12')
    from backend.ai import Interpretation
    limitation=order.inspect_order(excluded['text'],Interpretation.model_validate(excluded['expectedExtraction']))
    return {'identity':IDENTITY,'status':'PROPOSED_FOR_OWNER_REVIEW_ONLY','dispatchAuthorized':False,'approvalSidecarCreated':False,
        'successorVersionSpecification':version,'successorConfigurationHash':config_hash,
        'baseline':b,'slots':slots,'maxProposedNewAttempts':5,'maxProposedAdditionalReservationNanodollars':EXTRA_CAP,
        'historicalOpenAIRecordsRemainSeparate':deepcopy(m['responses']),
        'historicalConservativeRatesNanodollarsPerToken':{'maximumInputIncludingCacheWrites':125,'outputIncludingReasoning':500},
        'pricesReverified':False,'newPaidReservations':0,'newRequests':0,'newJournal':False,
        'ifAllFiveLaterAuthorizedAndConsumed':{'counts':{'openai':12,'google':2,'anthropic':1},'totalAttempts':15,'remainingGlobalAttempts':579,
            'openaiRemaining':186,'accountedNanodollars':47366625+EXTRA_CAP,'remainingNanodollars':11952633375-EXTRA_CAP},
        'priorUnsentSlotsNotSelected':[['openai','journey-12',1],['openai','journey-06',1]],
        'excludedHomeCase':{'id':'journey-12','sourceSHA256':rubrics['journey-12']['sourceSHA256'],'authoredReferenceOnly':True,
            'V4Outcome':limitation['outcome'],'V4Issues':limitation['issues'],'reason':'Unproven source absence; do not force a clarification-only legacy result into an ordering success. No grammar change proposed.'},
        'globalQ1UnresolvedFields':6,'independentGoldReviewsComplete':0,'independentResponseReviewsComplete':0,
        'providerScope':{'openai':'proposal only','google':'BLOCKED per Q2, excluded','anthropic':'BLOCKED per Q2, excluded'}}
