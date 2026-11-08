"""Read-only V3 policy comparison; network disabled, no credential loading."""
from collections import Counter
import json
import sqlite3
import statistics
import time
from unittest.mock import patch

from backend.ai import Interpretation,parse_interpretation
from scripts import cloud_model52 as e
from scripts import cloud_model52_ordering_v3 as v3
from scripts import cloud_model52_ordering_compatibility as c
from scripts import cloud_model52_ordering_replay as baseline

DOCS=e.ROOT/'docs'


def brief(r):
    return {'resultHash':e.digest(r),**{k:r[k] for k in ('outcome','issues','originalGraph',
        'trustedGraph','unsupportedModelEdges','normalization','rawModelOrderingCorrect','safeNextAction')},
        'sourceCategory':r['source']['category'],'sourceRequirements':r['source']['requirements'],
        'sourceAbsenceProof':r['source']['absenceProof'],'sourceQualifiers':r['source']['qualifiers'],
        'proofs':[{k:p[k] for k in ('before','after','rule','span','cueSpan')} for p in r['source']['proofs']]}


def compare_cases(cases):
    rows=[]
    for case in cases:
        ai=c.fixture_reply(case);r=v3.inspect_order(case['text'],ai)
        rows.append({'id':case['id'],'expectedCategory':case['sourceCategory'],
            'expectedRelationships':case['expectedRelationships'],
            'production':c.production(case['text'],ai),'v2':c.brief(c.v2.inspect_order(case['text'],ai)),
            'v3':brief(r),'matchedSourceRubric':r['source']['category']==case['sourceCategory']})
    return rows


def _build():
    # Reproduce every original V1 and V2 comparison without overwriting either.
    original=baseline.replay()
    old=c.build();saved=json.loads((DOCS/'task52-ordering-compatibility-v2.json').read_text())
    for key in ('summary','qwen','openai','compatibilityCases','postFreezeCases','negativeProbes','journal'):
        if old[key]!=saved[key]:raise ValueError('Frozen V2 baseline drift: '+key)
    raw=json.loads((e.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    reviews=json.loads((DOCS/'task52-ordering-qwen-review-v2.json').read_text())['rows']
    qwen=[]
    for review,oldrow in zip(reviews,old['qwen']):
        ai=Interpretation.model_validate(raw[review['cohort']]['rows'][review['row']]['raw'])
        before=ai.model_dump(mode='json');r=v3.inspect_order(review['source'],ai)
        if c.positive(r):
            projection=v3.project(review['source'],ai,r).model_dump(mode='json')
            expected=ai.model_dump(mode='json')
            if r['normalization']:expected['journey'].update(order=[],ordering=r['source']['mode'])
            if projection!=expected:raise ValueError('Non-ordering projection mutation')
        if before!=ai.model_dump(mode='json'):raise ValueError('Raw fixture mutated')
        qwen.append({**{k:oldrow[k] for k in ('cohort','row','case','rawHash','sourceHash',
            'reviewedGraphCorrect','category','production','v2')},'v3':brief(r)})
    cloud=[]
    db=sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True)
    try:
        for row,prior in zip(db.execute("select * from attempts where provider='openai' order by rowid"),old['openai']):
            record=json.loads(row[5]);content,_,_=e.Adapter('openai',None).decode(record['response'])
            case=next(x for x in e.corpus()['cases'] if x['id']==row[1]);ai=parse_interpretation(content)
            cloud.append({**prior,'v3':brief(v3.inspect_order(case['text'],ai))})
    finally:db.close()
    cases=json.loads((DOCS/'task52-ordering-compatibility-v3-cases.json').read_text())['cases']
    held=json.loads((DOCS/'task52-ordering-compatibility-v3-holdouts.json').read_text())
    if held['frozenModuleSHA256']!=c.sha(v3.__file__):raise ValueError('Post-freeze V3 drift')
    checks=compare_cases(cases);holdouts=compare_cases(held['cases']);regressions=compare_cases(held['regressionCases'])
    limits=[]
    for case in json.loads((DOCS/'task52-ordering-v3-release-limits.json').read_text())['cases']:
        ai=c.fixture_reply(case)
        limits.append({**case,'production':c.production(case['text'],ai),
            'v2':c.brief(c.v2.inspect_order(case['text'],ai)),
            'v3':brief(v3.inspect_order(case['text'],ai))})
    # Unsupported single-edge replacement probes on clear-source rubrics only.
    oldcases=json.loads((DOCS/'task52-ordering-safety-cases.json').read_text())['cases']
    v2cases=json.loads((DOCS/'task52-ordering-compatibility-v2-cases.json').read_text())['cases']
    probes=[]
    for case in oldcases+v2cases+cases:
        if case.get('accept') is False or case.get('expectedOutcome')=='clarification_required' or case.get('sourceCategory')=='unknown':continue
        for a in range(len(case['stops'])):
            for b in range(len(case['stops'])):
                if a==b or v3.reach(case['expectedRelationships'],a,b):continue
                d=c.fixture_reply(case).model_dump(mode='json');d['journey'].update(
                    order=[{'before':a,'after':b,'source':case['text']}],ordering='constrained')
                r=v3.inspect_order(case['text'],Interpretation.model_validate(d))
                probes.append({'case':case['id'],'claimedEdge':[a,b],'sourceCategory':r['source']['category'],
                    'outcome':r['outcome'],'trustedGraph':r['trustedGraph'],
                    'normalized':bool(r['normalization']),'rawModelOrderingCorrect':r['rawModelOrderingCorrect'],
                    'unsupportedEdgeAccepted':r['trustedGraph'] is not None and [a,b] in r['trustedGraph']})
    durations=[]
    for _ in range(50):
        for case in cases:
            ai=c.fixture_reply(case);start=time.perf_counter_ns()
            v3.inspect_order(case['text'],ai);durations.append((time.perf_counter_ns()-start)/1000)
    durations.sort()
    clear=[r for r in checks if r['expectedCategory']!='unknown']
    summary={'qwenRows':len(qwen),'qwenV2Clarifications':sum(not c.positive(r['v2']) for r in qwen),
        'qwenV3Clarifications':sum(not c.positive(r['v3']) for r in qwen),
        'qwenAuditedUnorderedNormalizations':sum(bool(r['v3']['normalization']) for r in qwen),
        'qwenRawOrderingCorrect':sum(r['v3']['rawModelOrderingCorrect'] for r in qwen),
        'qwenOtherCanonicalBlocksPreserved':sum(r['production']['journeyBlocking'] for r in qwen if c.positive(r['v3'])),
        'openaiRows':len(cloud),'openaiV3Compatible':sum(c.positive(r['v3']) for r in cloud),
        'declaredCases':len(checks),'declaredSourceRubricsMatched':sum(r['matchedSourceRubric'] for r in checks),
        'clearDeclaredCases':len(clear),'v2ClearClarifications':sum(not c.positive(r['v2']) for r in clear),
        'v3ClearClarifications':sum(not c.positive(r['v3']) for r in clear),
        'unknownDeclaredCases':len(checks)-len(clear),'unknownCorrectlyClarified':sum(
            not c.positive(r['v3']) for r in checks if r['expectedCategory']=='unknown'),
        'sourceCategories':dict(Counter(r['expectedCategory'] for r in checks)),
        'postFreezeCases':len(holdouts),'postFreezeMatched':sum(r['matchedSourceRubric'] for r in holdouts),
        'promotedRegressionCases':len(regressions),'promotedRegressionsMatched':sum(r['matchedSourceRubric'] for r in regressions),
        'negativeProbes':len(probes),'unsupportedEdgesAccepted':sum(r['unsupportedEdgeAccepted'] for r in probes),
        'negativeProbesSafelyNormalized':sum(r['normalized'] for r in probes),
        'exploratoryClearReleaseLimits':len(limits),
        'releaseLimitV3FalseClarifications':sum(not c.positive(r['v3']) for r in limits)}
    if baseline.replay()!=original:raise ValueError('Historical/paid evidence changed')
    return {'version':v3.VERSION,'baselineGitHEAD':'9aa9035cdf80a171195c82d7ece448bc99241712',
        'moduleSHA256':c.sha(v3.__file__),'runnerSHA256':c.sha(__file__),
        'sourceFileHashes':{name:c.sha(DOCS/name) for name in ('task52-ordering-compatibility-v3-cases.json',
            'task52-ordering-compatibility-v3-holdouts.json','task52-ordering-qwen-review-v2.json',
            'task52-ordering-v3-release-limits.json')},
        'summary':summary,'qwen':qwen,'openai':cloud,'declaredCases':checks,'holdouts':holdouts,
        'promotedRegressions':regressions,'negativeProbes':probes,'exploratoryReleaseLimits':limits,
        'timing':{'samples':len(durations),'p50Microseconds':statistics.median(durations),
            'p95Microseconds':durations[int(.95*(len(durations)-1))],'maxMicroseconds':max(durations),
            'scope':'50x29 local ordering-only decisions; fixture construction excluded, deep copy/hash included. Not end-to-end app latency.'},
        'journal':original['journal'],'requestsSent':0,'historicalEvidenceChanged':False,
        'independentHumanSignoff':False,'productionActivated':False}


def build():
    with patch('socket.create_connection',side_effect=AssertionError('Offline only')),patch('requests.sessions.Session.send',side_effect=AssertionError('Offline only')):
        return _build()


if __name__=='__main__':
    result=build();c.write_report(result,DOCS/'task52-ordering-compatibility-v3.json')
    print(json.dumps({'summary':result['summary'],'timing':result['timing'],'journal':result['journal']}))
