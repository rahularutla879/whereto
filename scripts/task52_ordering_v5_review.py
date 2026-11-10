"""V5 source/rubric/replay proposals only. No dispatch, credentials or writers."""
from contextlib import closing
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
import sqlite3

from backend.ai import Interpretation,parse_interpretation
from backend.journey import validate_journey
from backend.interpretation import InterpretationInput,interpret_request
from scripts import task52_q1 as q1
from scripts import task52_ordering_v5 as v5
from scripts import cloud_model52 as original
from scripts import cloud_model52_ordering_v4 as v4
from scripts.task52_q4b import inspect_original
from scripts.task52_q4c_identity import verify_build

RUBRIC_ID='52b-q1-rubric-v2-owner-list-order-PROPOSED'
PROPOSAL_ID='52b-q3-openai-b2-v5-owner-list-PROPOSED-v2'
DOCS=q1.ROOT/'docs'


def read(name):return json.loads((DOCS/name).read_text())


def rubric_interpretation(row):
    f=row['fields'];stops=sorted((f['required_activities']['expected'] or [])+(f['optional_activities']['expected'] or []),key=lambda s:s['index'])
    named={n['index']:n['kind'] for n in f['exact_named_identity']['expected'] or []}
    geography=f['geography']['expected']
    return Interpretation(activities=[s['sourcePhrase'] for s in stops],budget_per_person=None,date=None,
        location=geography['destinationText'] if geography else None,preferences=[],
        journey={'stops':[{'source':s['sourcePhrase'],'kind':named.get(s['index'],'activity'),'requirement':s['requirement']} for s in stops]})


def amendment():
    q1.verify();verify_build(full=True)
    parent=read('task52-q1-rubric-v1.json');declared=read('task52-v5-rubric-impact-decisions-v1.json')
    required=set(declared['mandatoryReachabilityChanges']);conditional=set(declared['conditionalOrderChanges'])
    pending=set(declared['conditionalOrderAmendmentAwaitingOwner']);language=set(declared['additionalOrderingJudgmentAwaitingOwner'])
    rows=[]
    for old in parent['cases']:
        row=deepcopy(old);id=old['id'];ai=rubric_interpretation(old);n=len(ai.activities)
        prior=deepcopy(old['fields']['mandatory_order']['expected']);before=prior['requiredReachability']
        status=('mandatory_graph_change' if id in required else 'conditional_graph_change' if id in conditional else
                'conditional_amendment_awaiting_owner' if id in pending else 'language_order_awaiting_owner' if id in language else 'graph_unchanged')
        proposed=v5.closure([(i,i+1) for i in range(n-1)],n) if id in required else deepcopy(before)
        conditional_graph=[[0,1]] if id in conditional|pending else []
        evidence=[]
        owned,error=v5.bind_occurrences(old['sourceText'],ai.journey.stops) if n else ([],None)
        if (id in required|conditional|pending) and owned:
            span=[owned[0][0],owned[-1][1]]
            value={'sourceSHA256':old['sourceSHA256'],'span':span,'source':old['sourceText'][slice(*span)],
                   'occurrences':list(range(n)),'basis':'Owner default-list decision; same-agent case expectation, not automatic grammar proof or independent approval.'}
            evidence=[{**value,'evidenceHash':q1.digest(value)}]
        changed=[]
        if id in required|conditional:
            fields=row['fields'];target=fields['mandatory_order']['expected']
            target.update(requiredReachability=proposed,conditionalReachability=conditional_graph,
                          indexBasis='V5 source-bound occurrence list; explicit partial/flexible/contradictory exceptions take priority',
                          optionalProjection='Full source-proven closure, then restrict to selected visits; optional visits remain optional')
            fields['unordered_flexible']['expected']={'mode':'owner_default_sequence' if id in required else 'conditional_list',
                'independentOccurrences':[],'noFullSequenceFromList':False}
            fields['source_provenance']['expected']['edgeEvidence']='Both owned stop occurrences and source-proven bounded list/explicit relationship; temporal cue OR complete owner-V5 list proof, never an unrelated nearby cue.'
            changed=['mandatory_order','unordered_flexible','source_provenance']
            for key in changed:
                fields[key]['basis']='Proposed owner-list amendment from the unchanged source; same-agent case expectation, not original v1 gold or independent signoff.'
                fields[key]['sourceAnchors']=[evidence[0]['source']] if evidence else [old['sourceText']]
        row['orderingV5Amendment']={'status':status,'parentOrdering':prior,'proposedRequiredClosure':None if id in language else proposed,
             'candidateConditionalClosure':conditional_graph,'sourceListEvidence':evidence,
             'changedFields':changed,'ownerGeneralRuleApproved':True,'individualCaseApproved':False,
             'requiresOwnerJudgment':id in conditional|pending|language,
             'implementationSourceAnalysis':v5.source_analysis(old['sourceText'],ai),
             'implementationAnalysisIsNotGold':True,'originalUnresolvedFieldsPreserved':[k for k,f in old['fields'].items() if f['applicability']=='awaiting_review']}
        if id in pending:row['orderingV5Amendment']['note']='Original unresolved mandatory_order record is kept byte-for-byte; conditional/list/return scope amendment still needs case review.'
        if id in language:row['orderingV5Amendment']['note']='English finite grammar does not establish aur/list scope. Original date ambiguity remains; no new definite graph is manufactured.'
        rows.append(row)
    if len(rows)!=66 or (required|conditional|pending|language)-{r['id'] for r in rows}:raise ValueError('Invalid declared impact coverage')
    return {'identity':RUBRIC_ID,'status':'PROPOSED; not independently approved or paid authority','parentContract':q1.CONTRACT,
        'parentRubricSHA256':q1.sha((DOCS/'task52-q1-rubric-v1.json').read_bytes()),'corpusSHA256':original.CORPUS_SHA,
        'policy':v5.VERSION,'policySHA256':q1.sha((q1.ROOT/'scripts/task52_ordering_v5.py').read_bytes()),'scorer':v5.SCORER,
        'ownerDecision':'A complete chronological activity list defaults to visit order; explicit partial/flexible/contradictory instructions override. No implicit optionality or occurrence merging.',
        'caseCount':66,'dimensions':parent['dimensions'],'states':parent['states'],'cases':rows,
        'counts':dict(Counter(r['orderingV5Amendment']['status'] for r in rows)),
        'originalUnresolvedJudgmentsPreserved':6,'independentCaseApprovals':0,
        'newOwnerJudgmentCases':sorted(conditional|pending|language),'originalPaidEvidenceChanged':False}


def impact(rubric):
    counts=Counter(r['orderingV5Amendment']['implementationSourceAnalysis']['category'] for r in rubric['cases'])
    return {'identity':'52b-v5-all66-impact-v1','rubric':RUBRIC_ID,'rubricDigest':q1.digest(rubric),
            'graphImpactCounts':rubric['counts'],'implementationSourceCategories':dict(counts),
            'countsHaveDifferentDenominators':'Graph changes compare proposed gold; implementation categories measure bounded source recognizer coverage, not model accuracy.',
            'cases':[{'id':r['id'],'sourceText':r['sourceText'],'sourceSHA256':r['sourceSHA256'],**r['orderingV5Amendment']} for r in rubric['cases']]}


def mapping(raw,effective,decision):
    a,b=raw.journey,effective.journey
    known=bool(a is not None and b is not None and
        [(s.source,s.kind,s.requirement) for s in a.stops]==[(s.source,s.kind,s.requirement) for s in b.stops] and
        a.endpoint==b.endpoint and a.total_duration==b.total_duration)
    edges=[[e.before,e.after] for e in b.order] if b else []
    return {'occurrenceMappingKnown':known,'originalToEffective':list(range(len(a.stops))) if known else None,
            'effectiveGraph':edges,'orderingRequirementsKnown':decision['source']['category']not in ('unknown','contradictory'),
            'sourceRequiredOrderPreserved':known and decision['source']['category']not in ('unknown','contradictory') and all(v5.reach(edges,a,b) for a,b in decision['requiredClosure']),
            'unknownMappingNeverAuthorizesPlanning':True}


def replay():
    verify_build(full=True);baseline=inspect_original();before=q1.private_hashes()
    historical=q1.replay();old_openai={r['slot'][1]:r for r in historical['results']}
    frozen=read('task52-ordering-v4-results.json');reviews=read('task52-ordering-qwen-review-v2.json')['rows']
    recorded=json.loads((q1.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    qwen=[]
    for i,review in enumerate(reviews):
        ai=Interpretation.model_validate(recorded[review['cohort']]['rows'][review['row']]['raw'])
        raw=ai.model_dump(mode='json');old=v4.inspect_order(review['source'],ai)
        if q1.digest(old)!=frozen['qwen'][i]['v4']['resultHash']:raise ValueError('Frozen Qwen V4 mismatch')
        new=v5.inspect_order(review['source'],ai)
        effective=ai.model_copy(deep=True);explanation,blocked=validate_journey(review['source'],effective)
        mapped=mapping(ai,effective,new)
        if {'journeyBlocking':blocked,'explanation':explanation,'effectiveGraph':mapped['effectiveGraph'],'legacyGraphNormalized':mapped['effectiveGraph']!=[[e.before,e.after] for e in ai.journey.order]}!=frozen['qwen'][i]['production']:
            raise ValueError('Frozen Qwen legacy journey result changed')
        qwen.append({'ordinal':i+1,'cohort':review['cohort'],'row':review['row'],'sourceSHA256':q1.sha(review['source'].encode()),
            'rawHash':q1.digest(raw),'originalV4':deepcopy(frozen['qwen'][i]['v4']),
            'V5':new,'mapping':mapped,'originalLegacyJourneyValidation':deepcopy(frozen['qwen'][i]['production']),
            'originalRawGraphReviewCorrectUnderV4':frozen['qwen'][i]['reviewedGraphCorrect'],
            'V5WithLegacyJourneyCompatibleOnly':new['trustedGraph']is not None and not blocked and mapped['sourceRequiredOrderPreserved'],
            'comparisonIsOrderingOnly':True,'fullSemanticIndependentSignoff':None})
        if raw!=ai.model_dump(mode='json'):raise ValueError('Recorded Qwen changed')
    cases={c['id']:c for c in read('task52-evaluation-corpus.json')['cases']};openai=[]
    with q1.offline(),closing(sqlite3.connect(f'file:{original.STATE}/journal.sqlite?mode=ro',uri=True)) as db:
        for row in db.execute("SELECT * FROM attempts WHERE provider='openai' ORDER BY rowid"):
            record=json.loads(row[5]);content,usage,status=original.Adapter('openai',None).decode(record['response'])
            old=old_openai[row[1]]
            if q1.digest(record['response'])!=old['original']['responseHash'] or status!='complete':raise ValueError('Response identity mismatch')
            ai=parse_interpretation(content);snapshot=ai.model_dump(mode='json');new=v5.inspect_order(cases[row[1]]['text'],ai)
            legacy_accepted=old['legacy']['disposition']!='blocked_or_clarify'
            class Recorded:
                def interpret(self,text):
                    if text!=cases[row[1]]['text']:raise ValueError('Wrong replay source')
                    return ai.model_copy(deep=True)
            complete=interpret_request(InterpretationInput(text=cases[row[1]]['text'],calendarTimezone=original.timezone_for(cases[row[1]])),
                 provider=Recorded(),now=datetime.fromisoformat(read('task52-q1-offline-manifest-v1.json')['clock']['referenceTime'].replace('Z','+00:00')))
            if q1.digest(complete.model_dump(mode='json'))!=old['legacy']['resultHash']:raise ValueError('Complete B2 outcome changed')
            mapped=mapping(ai,complete.interpretation,new)
            combined='candidate_only_not_planning_authority' if legacy_accepted and new['trustedGraph']is not None and mapped['sourceRequiredOrderPreserved'] else 'blocked_or_clarify'
            openai.append({'slot':list(row[:3]),'source':cases[row[1]]['text'],'originalRowState':row[3],
                'originalRecordedClassification':record['status'],'originalRecordHash':q1.digest(record),
                'originalResponseHash':q1.digest(record['response']),'rawOutputHash':q1.digest(snapshot),
                'originalQ1':deepcopy(old),'V5':new,'mapping':mapped,'combinedV5WithUnchangedCompleteB2':combined,
                'newFullIndependentCorrectness':None,
                'reviewNote':'New owner-policy ordering comparison only. Original non-order same-agent findings and full B2 disposition preserved; source/evidence still checked. No independent requalification.'})
            if snapshot!=ai.model_dump(mode='json'):raise ValueError('Recorded OpenAI changed')
    if before!=q1.private_hashes():raise ValueError('Private evidence changed')
    def compare(rows):
        return dict(Counter(('compatible' if r['originalV4']['outcome'].startswith('verified_') else 'blocked')+' -> '+('compatible' if r['V5']['trustedGraph']is not None else 'blocked') for r in rows))
    return {'identity':'52b-v5-historical-replay-v1','policy':v5.VERSION,'scorer':v5.SCORER,
            'scope':'New policy assessment; original mixed prompt cohorts and every historical classification remain unchanged.',
            'qwen':qwen,'openai':openai,'counts':{'Qwen':27,'OpenAI':7,
                'QwenTransitions':compare(qwen),'QwenV5WithLegacyJourneyCompatibleOnly':sum(r['V5WithLegacyJourneyCompatibleOnly'] for r in qwen),
                'QwenRawOrderingTransitions':dict(Counter(('correct' if r['originalRawGraphReviewCorrectUnderV4'] else 'raw_error')+' -> '+('compatible' if r['V5']['trustedGraph']is not None else 'blocked') for r in qwen)),'OpenAITransitions':dict(Counter(
                ('compatible' if r['originalQ1']['proposedGuarded']['disposition'].startswith('candidate_') else 'blocked')+' -> '+('compatible' if r['combinedV5WithUnchangedCompleteB2'].startswith('candidate_') else 'blocked') for r in openai)),
                'independentSignoffs':0},'originalJournal':baseline,'providerRequests':0,'paidApprovalCreated':False}


def proposal(rubric):
    old=read('task52-q3-openai-proposal-v1.json');rows={r['id']:r for r in rubric['cases']}
    slots=[]
    for slot in old['slots']:
        amendment_row=rows[slot['slot'][1]]
        slots.append({'slot':slot['slot'],'source':slot['source'],'sourceSHA256':slot['sourceSHA256'],
            'oldPayloadHashHistoricalOnly':slot['payloadHash'],'futureV5PayloadHash':None,
            'orderingAmendment':amendment_row['orderingV5Amendment'],
            'rubricCaseDigest':q1.digest(amendment_row),'independentReviewComplete':False,
            'currentlyAdmissible':False})
    return {'identity':PROPOSAL_ID,'status':'PROPOSED, blocked on prompt/case/build review; no dispatch approval',
        'supersedesForFutureNewEvaluation':old['identity'],'preservesParentArtifactUnchanged':True,
        'parentProposalDigest':q1.digest(old),'oldConfigurationHashHistoricalOnly':old['successorConfigurationHash'],
        'policy':v5.VERSION,'policySHA256':rubric['policySHA256'],'rubric':RUBRIC_ID,'rubricDigest':q1.digest(rubric),
        'scorer':v5.SCORER,'model':'gpt-6-luna','slots':slots,
        'futurePromptVersion':None,'futureConfigurationHash':None,'futureExecutionBuildHash':None,
        'promptBlocker':'Existing unchanged v4 prompt says Never infer edges from list order. A separately reviewed prompt/examples revision and new payload hashes are required; none is implemented here.',
        'oldQ4Contracts':'Q4A/Q4B/Q4C remain frozen V4 engineering evidence; not V5-compatible authorization or raw-error guards. A new reviewed purpose/build and owner approval are required.',
        'maxProposedAttempts':5,'maxProposedAdditionalReservationNanodollars':12500000,'reservationPerAttemptNanodollars':2500000,
        'pricesFreshlyVerified':False,'realApprovals':0,'newRequests':0,'newReservations':0,
        'realJournalRootUnchanged':old['baseline']['rootHash'],'historicalHaltRemainsActive':True,
        'originalExperimentCapsUnchanged':True,'noNewCasesOrRepetitions':True}
