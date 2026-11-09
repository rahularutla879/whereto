"""Frozen-V3 comparison plus V4 release evidence. No transport or paid writes."""
from contextlib import nullcontext
from datetime import datetime,timezone
import json
import sqlite3
import statistics
import time
from unittest.mock import Mock,patch

from backend.ai import Interpretation,parse_interpretation
from backend.interpretation import InterpretationInput,interpret_request
from backend.ordering_shadow import capture_local_test,interpret_observed
from scripts import cloud_model52 as e
from scripts import cloud_model52_ordering_v4 as v4
from scripts import cloud_model52_ordering_policy_replay as previous
from scripts import cloud_model52_ordering_compatibility as c

DOCS=e.ROOT/'docs'


def samples(values):
    values=sorted(values)
    return {'samples':len(values),'p50Microseconds':statistics.median(values),
        'p95Microseconds':values[int(.95*(len(values)-1))],'maxMicroseconds':max(values)}


def _build():
    old=previous.build();saved=json.loads((DOCS/'task52-ordering-compatibility-v3.json').read_text())
    for k in saved:
        if k!='timing' and saved[k]!=old[k]:raise ValueError('Frozen V3 baseline drift: '+k)
    reviews=json.loads((DOCS/'task52-ordering-qwen-review-v2.json').read_text())['rows']
    actual=json.loads((e.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    qwen=[]
    for review,prior in zip(reviews,old['qwen']):
        ai=Interpretation.model_validate(actual[review['cohort']]['rows'][review['row']]['raw'])
        qwen.append({**prior,'v4':previous.brief(v4.inspect_order(review['source'],ai))})
    cloud=[]
    db=sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True)
    try:
        for row,prior in zip(db.execute("select * from attempts where provider='openai' order by rowid"),old['openai']):
            content,_,_=e.Adapter('openai',None).decode(json.loads(row[5])['response'])
            case=next(x for x in e.corpus()['cases'] if x['id']==row[1])
            cloud.append({**prior,'v4':previous.brief(v4.inspect_order(case['text'],parse_interpretation(content)))})
    finally:db.close()
    cases=json.loads((DOCS/'task52-ordering-v4-cases.json').read_text())['cases']
    held=json.loads((DOCS/'task52-ordering-v4-holdouts.json').read_text())
    if held['frozenModuleSHA256']!=c.sha(v4.__file__):raise ValueError('V4 post-freeze drift')
    checks=[]
    for cohort,rows in [('predeclared',cases),('postFreeze',held['cases'])]:
        for case in rows:
            ai=c.fixture_reply(case)
            checks.append({'cohort':cohort,'id':case['id'],'expectedAccepted':case['accept'],
                'v3':previous.brief(previous.v3.inspect_order(case['text'],ai)),
                'v4':previous.brief(v4.inspect_order(case['text'],ai))})
    allcases=[]
    for file in ('task52-ordering-safety-cases.json','task52-ordering-compatibility-v2-cases.json',
                 'task52-ordering-compatibility-v3-cases.json'):
        allcases+=json.loads((DOCS/file).read_text())['cases']
    probes=[]
    for cohort,rows in [('original147',allcases),('newPatterns',cases+held['cases'])]:
        for case in rows:
            if case.get('accept') is False or case.get('expectedOutcome')=='clarification_required' or case.get('sourceCategory')=='unknown':continue
            for a in range(len(case['stops'])):
                for b in range(len(case['stops'])):
                    if a==b or v4.reach(case['expectedRelationships'],a,b):continue
                    data=c.fixture_reply(case).model_dump(mode='json')
                    data['journey'].update(order=[{'before':a,'after':b,'source':case['text']}],ordering='constrained')
                    r=v4.inspect_order(case['text'],Interpretation.model_validate(data))
                    probes.append({'cohort':cohort,'case':case['id'],'claimedEdge':[a,b],
                        'retainedUnsupported':r['trustedGraph'] is not None and [a,b] in r['trustedGraph'],
                        'outcome':r['outcome'],'normalized':bool(r['normalization'])})
    times=[]
    for _ in range(50):
        for case in cases:
            ai=c.fixture_reply(case);start=time.perf_counter_ns()
            v4.inspect_order(case['text'],ai);times.append((time.perf_counter_ns()-start)/1000)
    boundary={}
    case={'text':'Dinner and bowling tomorrow in Jersey City.','stops':['Dinner','bowling'],
        'location':'Jersey City','expectedRelationships':[[0,1]]}
    output=None
    for enabled in (False,True):
        values=[];diagnostics=[]
        for _ in range(100):
            provider=Mock();provider.interpret.return_value=c.fixture_reply(case)
            with patch('backend.interpretation.create_provider',return_value=provider):
                with capture_local_test() if enabled else nullcontext([]) as diag:
                    start=time.perf_counter_ns()
                    r=interpret_observed(InterpretationInput(text=case['text']),
                        lambda value,**kw:interpret_request(value,now=datetime(2026,11,8,12,tzinfo=timezone.utc),**kw))
                    values.append((time.perf_counter_ns()-start)/1000)
            if output is None:output=r.model_dump(mode='json')
            if output!=r.model_dump(mode='json'):raise ValueError('Shadow changed interpretation')
            diagnostics+=diag
        boundary['on' if enabled else 'off']={**samples(values),'observerStatuses':{
            status:sum(x['status']==status for x in diagnostics) for status in sorted({d['status'] for d in diagnostics})}}
    summary={'qwenCorrectRawCompatible':sum(c.positive(r['v4']) and r['reviewedGraphCorrect'] for r in qwen),
        'qwenAuditedNormalizations':sum(bool(r['v4']['normalization']) for r in qwen),
        'qwenClarifications':sum(not c.positive(r['v4']) for r in qwen),
        'openaiCompatible':sum(c.positive(r['v4']) for r in cloud),
        'predeclaredCases':len(cases),'predeclaredMatched':sum(c.positive(r['v4'])==r['expectedAccepted'] for r in checks if r['cohort']=='predeclared'),
        'postFreezeCases':len(held['cases']),'postFreezeMatched':sum(c.positive(r['v4'])==r['expectedAccepted'] for r in checks if r['cohort']=='postFreeze'),
        'clearSources':sum(r['expectedAccepted'] for r in checks),
        'falseClarifications':sum(r['expectedAccepted'] and not c.positive(r['v4']) for r in checks),
        'negativeSources':sum(not r['expectedAccepted'] for r in checks),
        'negativeSourcesAccepted':sum(not r['expectedAccepted'] and c.positive(r['v4']) for r in checks),
        'originalNegativeProbes':sum(r['cohort']=='original147' for r in probes),
        'newNegativeProbes':sum(r['cohort']=='newPatterns' for r in probes),
        'retainedUnsupportedEdges':sum(r['retainedUnsupported'] for r in probes)}
    after=previous.baseline.replay()['journal']
    if after!=old['journal']:raise ValueError('Paid/private evidence changed')
    return {'version':v4.VERSION,'baselineGitHEAD':'d271ed1c349d21dfb7bf598a3e6eb47e724c3025',
        'hashes':{'policy':c.sha(v4.__file__),'observer':c.sha(e.ROOT/'backend/ordering_shadow.py'),
            'interpretation':c.sha(e.ROOT/'backend/interpretation.py'),'runner':c.sha(__file__),
            'apiBoundary':c.sha(e.ROOT/'backend/main.py'),
            'cases':c.sha(DOCS/'task52-ordering-v4-cases.json'),'holdouts':c.sha(DOCS/'task52-ordering-v4-holdouts.json')},
        'summary':summary,'qwen':qwen,'openai':cloud,'cases':checks,'probes':probes,
        'timing':{'policy':samples(times),'boundary':boundary,
            'scope':'Local fixtures only. Policy50x20; interpretation boundary100 off/100 on; fake AI, no HTTP/routes. Not production p95 or end-to-end latency.'},
        'journal':after,'requestsSent':0,'enforcementActivated':False,'shadowDefault':'OFF',
        'independentHumanSignoff':False,'historicalEvidenceChanged':False}


def build():
    with patch('requests.sessions.Session.send',side_effect=AssertionError('Offline only')),patch('socket.create_connection',side_effect=AssertionError('Offline only')):
        return _build()


if __name__=='__main__':
    r=build();c.write_report(r,DOCS/'task52-ordering-v4-results.json')
    print(json.dumps({'summary':r['summary'],'timing':r['timing']}))
