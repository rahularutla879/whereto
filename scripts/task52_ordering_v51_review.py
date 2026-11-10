"""V5.1 proposed rubric, prompt and replay artifacts. Read-only real evidence."""
from collections import Counter
from contextlib import closing
from copy import deepcopy
import json
import sqlite3
from backend.ai import Interpretation,parse_interpretation
from backend.journey import validate_journey
from scripts import task52_ordering_v5_review as parent
from scripts import task52_ordering_v5_identity as frozen
from scripts import task52_ordering_v51 as policy
from scripts import task52_prompt_v51 as prompt
from scripts import task52_q1 as q1
from scripts import cloud_model52 as original

RUBRIC='52b-q1-rubric-v3-owner-decisions-v5.1-PROPOSED'
SUCCESSOR='52b-q3-openai-b2-v5.1-owner-decisions-PROPOSED-v3'


def amendment():
    frozen.verify();previous=parent.read('task52-q1-rubric-v2-owner-list-PROPOSED.json')
    rows=deepcopy(previous['cases']);required=set(parent.read('task52-v5-rubric-impact-decisions-v1.json')['mandatoryReachabilityChanges'])|{'ordinary-multilingual'}
    conditional={'journey-06','extension-inclusive'}
    for row in rows:
        id=row['id'];n=len(parent.rubric_interpretation(row).activities)
        status='mandatory_graph_change' if id in required else 'conditional_graph_change' if id in conditional else 'graph_unchanged'
        fields=row['fields'];analysis=policy.source_analysis(row['sourceText'],parent.rubric_interpretation(row))
        if id in required|conditional:
            target=fields['mandatory_order'];target['applicability']='supported'
            target['expected'].update(requiredReachability=policy.closure([(i,i+1) for i in range(n-1)],n) if id in required else [],
                conditionalReachability=[[0,1]] if id in conditional else [],
                indexBasis='V5.1 source occurrences; explicit scope takes priority over owner default list order',
                optionalProjection='Owner Rule B: full closure before projection onto selected visits; optional stays optional')
            fields['unordered_flexible']['expected']={'mode':'owner_default_sequence' if id in required else 'conditional_list','independentOccurrences':[],'noFullSequenceFromList':False}
            fields['source_provenance']['expected']['edgeEvidence']='Both owned occurrences and complete source-bound list connector (reviewed whole-word aur included) or explicit scoped ordering cue.'
            for key in ('mandatory_order','unordered_flexible','source_provenance'):
                fields[key]['basis']='Proposed V5.1 case expectation under owner Rules A-D; no independent case approval.'
                fields[key]['sourceAnchors']=[row['sourceText']]
        row['orderingV51Amendment']={'status':status,'parentV5Status':row['orderingV5Amendment']['status'],
            'sourceAnalysis':analysis,'sourceAnalysisIsNotGold':True,'ownerRulesConfirmed':['A','B','C','D'],
            'individualCaseApproved':False,'independentReviewComplete':False,
            'orderingResolution':'Proposed resolution of original optional-order judgment by owner Rule B; independent review still pending' if id=='extension-inclusive' else None,
            'remainingUnresolvedFields':[k for k,f in fields.items() if f['applicability']=='awaiting_review']}
    original_gaps=[{'case':r['id'],'field':k,'proposedV51Status':'owner-rule proposed resolution; not independent signoff' if r['id']=='extension-inclusive' and k=='mandatory_order' else 'still awaiting review'} for r in parent.read('task52-q1-rubric-v1.json')['cases'] for k,f in r['fields'].items() if f['applicability']=='awaiting_review']
    return {'identity':RUBRIC,'status':'PROPOSED; general owner rules confirmed, individual gold review pending',
        'parentContract':q1.CONTRACT,'parentV5Identity':previous['identity'],'parentV5RubricSHA256':q1.sha((parent.DOCS/'task52-q1-rubric-v2-owner-list-PROPOSED.json').read_bytes()),
        'originalCorpusSHA256':original.CORPUS_SHA,'policy':policy.VERSION,'scorer':policy.SCORER,
        'caseCount':66,'dimensions':previous['dimensions'],'states':previous['states'],'cases':rows,
        'counts':dict(Counter(r['orderingV51Amendment']['status'] for r in rows)),
        'sourceCoverage':dict(Counter(r['orderingV51Amendment']['sourceAnalysis']['category'] for r in rows)),
        'originalSixUnresolved':original_gaps,'remainingProposedUnresolvedFieldCount':sum(len(r['orderingV51Amendment']['remainingUnresolvedFields']) for r in rows),
        'independentCaseApprovals':0,'historicalRubricsChanged':False}


def impact(rubric):
    return {'identity':'52b-v5.1-all66-impact-v1','rubric':RUBRIC,'rubricDigest':q1.digest(rubric),
        'countsComparedToOriginalQ1':rubric['counts'],'sourceCoverageNotAccuracy':rubric['sourceCoverage'],
        'originalSixUnresolved':rubric['originalSixUnresolved'],'independentGoldApprovals':0,
        'cases':[{'id':r['id'],'source':r['sourceText'],'sourceSHA256':r['sourceSHA256'],
            'currentOrdering':r['fields']['mandatory_order'],'flexiblePlacement':r['fields']['unordered_flexible'],
            **r['orderingV51Amendment']} for r in rubric['cases']]}


def replay():
    frozen.verify();old=parent.replay();before=q1.private_hashes()
    recorded=json.loads((q1.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    qwen=[]
    for row in old['qwen']:
        ai=Interpretation.model_validate(recorded[row['cohort']]['rows'][row['row']]['raw'])
        source=next(r['source'] for r in parent.read('task52-ordering-qwen-review-v2.json')['rows'] if r['cohort']==row['cohort'] and r['row']==row['row'])
        new=policy.inspect_order(source,ai);effective=ai.model_copy(deep=True);_,blocked=validate_journey(source,effective)
        mapping=parent.mapping(ai,effective,new)
        qwen.append({'originalV5Comparison':row,'V51':new,'effectiveMapping':mapping,
            'combinedLegacyJourneyCompatibleOnly':new['trustedGraph']is not None and not blocked and mapping['sourceRequiredOrderPreserved'],
            'fullIndependentCorrectness':None})
    openai=[];cases={c['id']:c for c in parent.read('task52-evaluation-corpus.json')['cases']}
    with closing(sqlite3.connect(f'file:{original.STATE}/journal.sqlite?mode=ro',uri=True)) as db:
        real={r[1]:r for r in db.execute("select * from attempts where provider='openai'")}
    for row in old['openai']:
        id=row['slot'][1];record=json.loads(real[id][5]);content,_,status=original.Adapter('openai',None).decode(record['response'])
        if status!='complete' or q1.digest(record['response'])!=row['originalResponseHash']:raise ValueError('Recorded response drift')
        ai=parse_interpretation(content);new=policy.inspect_order(cases[id]['text'],ai)
        mapping=deepcopy(row['mapping']);mapping['orderingRequirementsKnown']=new['source']['category']not in ('unknown','contradictory')
        mapping['sourceRequiredOrderPreserved']=mapping['occurrenceMappingKnown'] and mapping['orderingRequirementsKnown'] and all(policy.reach(mapping['effectiveGraph'],a,b) for a,b in new['requiredClosure'])
        accepted=row['originalQ1']['legacy']['disposition']!='blocked_or_clarify'
        openai.append({'slot':row['slot'],'originalV5Comparison':row,'V51':new,'effectiveMapping':mapping,
            'combinedWithUnchangedCompleteB2':accepted and new['trustedGraph']is not None and mapping['sourceRequiredOrderPreserved'],
            'fullIndependentCorrectness':None})
    if before!=q1.private_hashes():raise ValueError('Private evidence changed')
    return {'identity':'52b-v5.1-historical-replay-v1','policy':policy.VERSION,'historicalFindingsUnchanged':True,
        'qwen':qwen,'openai':openai,'counts':{'Qwen':27,'QwenV51OrderingCompatible':sum(r['V51']['trustedGraph']is not None for r in qwen),
            'QwenWithLegacyJourneyCompatibleOnly':sum(r['combinedLegacyJourneyCompatibleOnly'] for r in qwen),'OpenAI':7,
            'OpenAIV51OrderingCompatible':sum(r['V51']['trustedGraph']is not None for r in openai),'OpenAIWithCompleteB2CompatibleOnly':sum(r['combinedWithUnchangedCompleteB2'] for r in openai),
            'changedV5OrderingOutcomes':sum((r['V51']['trustedGraph']is not None)!=(r['originalV5Comparison']['V5']['trustedGraph']is not None) for r in qwen+openai),'independentApprovals':0},
        'originalJournal':old['originalJournal'],'providerRequests':0,'newPaidAuthority':False}


def successor(rubric,proposed_prompt):
    previous=parent.read('task52-q3-openai-v5-PROPOSED-v2.json');hashes=prompt.payload_hashes(proposed_prompt)
    rows={r['id']:r for r in rubric['cases']};slots=[]
    for old in previous['slots']:
        id=old['slot'][1];row=rows[id]
        slots.append({'slot':old['slot'],'source':old['source'],'sourceSHA256':old['sourceSHA256'],
            'proposedPayloadHash':hashes[id],'rubricCaseDigest':q1.digest(row),'all24Expectations':row['fields'],
            'ordering':row['fields']['mandatory_order'],'sourceProofCoverage':row['orderingV51Amendment']['sourceAnalysis']['category'],
            'unresolvedFields':row['orderingV51Amendment']['remainingUnresolvedFields'],
            'independentReviewComplete':False,'currentlyAdmissible':False})
    return {'identity':SUCCESSOR,'status':'PROPOSED ONLY; no owner execution or financial authorization',
        'parentV5ProposalDigest':q1.digest(previous),'originalQ3Identity':parent.read('task52-q3-openai-proposal-v1.json')['identity'],
        'policy':policy.VERSION,'scorer':policy.SCORER,'rubric':RUBRIC,'rubricDigest':q1.digest(rubric),
        'promptVersion':proposed_prompt['identity'],'proposedPromptHash':proposed_prompt['promptHash'],
        'proposedPromptConfigurationHash':proposed_prompt['configurationHash'],'model':'gpt-6-luna','slots':slots,
        'futureLiveBuild':None,'ownerApproval':None,'independentSourceReview':None,'freshReadiness':None,'operationPermission':None,
        'historicalProposedCapOnly':{'attempts':5,'perRequestNanodollars':2500000,'totalNanodollars':12500000,'currentPricingGuaranteed':False,'financialAuthorization':False},
        'stopConditions':['raw critical semantic error even if guarded','provider/schema/truncation error','unknown source mapping or semantic review','missing source proof or required relationship','readiness/configuration/hash/cap/admission failure','historical or child halt without a separately reviewed exact child purpose'],
        'Q4A_Q4C':'Frozen V4 engineering identities/envelopes do not authorize V5.1. New reviewed build/purpose and real operator workflow still required.',
        'originalJournalHaltPreserved':True,'newRequests':0,'newReservations':0,'expandedMatrix':False}
