"""Offline three-way ordering comparison; existing evidence remains read-only.

No credential loading, model dispatch/counting, approval or paid-state mutation.
The comparison is ordering-specific, never a whole-request accuracy claim.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import time
from unittest.mock import patch

from backend.ai import Interpretation, parse_interpretation
from backend.journey import validate_journey
from scripts import cloud_model52 as e
from scripts import cloud_model52_ordering as v1
from scripts import cloud_model52_ordering_v2 as v2
from scripts import cloud_model52_ordering_replay as baseline

DOCS=e.ROOT/'docs'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture_reply(c):
    return Interpretation(activities=c['stops'],budget_per_person=None,date=None,
        location=c.get('location'),preferences=[],journey={'stops':[
            {'source':s,'kind':c.get('kinds',['activity']*len(c['stops']))[i],
             'requirement':'optional' if i in c.get('optional',[]) else 'required'}
            for i,s in enumerate(c['stops'])],
            'order':[{'before':a,'after':b,'source':c['text']} for a,b in c['expectedRelationships']]})


def production(source,ai):
    copy=ai.model_copy(deep=True)
    explanation,blocking=validate_journey(source,copy)
    graph=[[x.before,x.after] for x in copy.journey.order] if copy.journey else []
    return {'journeyBlocking':blocking,'explanation':explanation,'effectiveGraph':graph,
        'legacyGraphNormalized':ai.journey is not None and graph!=[[x.before,x.after] for x in ai.journey.order]}


def positive(result):
    return result['outcome'] in ('verified_order','verified_no_mandatory_order')


def brief(result):
    """Keep hashes and proof coordinates; source/graphs live in bound fixtures."""
    return {'resultHash':e.digest(result),'outcome':result['outcome'],'issues':result['issues'],
        'occurrenceSpans':[r['span'] for r in result.get('occurrences',[])],
        'proofs':[{k:p[k] for k in ('before','after','rule','span','cueSpan')} for p in result['proofs']],
        'edgeResults':[{k:r[k] for k in ('before','after','proven')} for r in result['edges']]}


def check_cases(rows):
    results=[]
    for c in rows:
        ai=fixture_reply(c)
        results.append({'id':c['id'],'source':c['text'],'expectedAcceptedOrdering':c['accept'],
            'production':production(c['text'],ai),'v1':v1.inspect_order(c['text'],ai),
            'v2':v2.inspect_order(c['text'],ai)})
    return results


def negative_probes(rows):
    results=[]
    for c in rows:
        if not c.get('accept',c.get('expectedOutcome')!='clarification_required'):continue
        for a in range(len(c['stops'])):
            for b in range(len(c['stops'])):
                if a==b or v1.reach([tuple(x) for x in c['expectedRelationships']],a,b):continue
                raw=fixture_reply(c).model_dump(mode='json')
                raw['journey'].update(order=[{'before':a,'after':b,'source':c['text']}],ordering='constrained')
                ai=Interpretation.model_validate(raw)
                prod=production(c['text'],ai)
                results.append({'case':c['id'],'claimedEdge':[a,b],
                    'productionAcceptedUnsupported':not prod['journeyBlocking'] and [a,b] in prod['effectiveGraph'],
                    'productionNormalized':prod['legacyGraphNormalized'],
                    'v1AcceptedUnsupported':positive(v1.inspect_order(c['text'],ai)),
                    'v2AcceptedUnsupported':positive(v2.inspect_order(c['text'],ai))})
    return results


def _build():
    original=baseline.replay() # Network blocked, all324 private files verified.
    saved=json.loads((DOCS/'task52-ordering-safety-replay.json').read_text())
    if original!=saved:raise ValueError('Original v1 replay drift; stop, never overwrite it')
    newcases=json.loads((DOCS/'task52-ordering-compatibility-v2-cases.json').read_text())['cases']
    holdouts=json.loads((DOCS/'task52-ordering-compatibility-v2-holdouts.json').read_text())
    if holdouts['frozenModuleSHA256']!=sha(v2.__file__):raise ValueError('Post-freeze module drift')
    reviews=json.loads((DOCS/'task52-ordering-qwen-review-v2.json').read_text())['rows']
    actual=json.loads((e.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    texts={r['case']:r['text'] for r in actual['baseline']['rows']}
    qwen=[]
    with patch('socket.create_connection',side_effect=AssertionError('Offline only')),patch('requests.sessions.Session.send',side_effect=AssertionError('Offline only')):
        for review in reviews:
            row=actual[review['cohort']]['rows'][review['row']]
            if (row['case']!=review['case'] or review['source']!=(row.get('text') or texts[row['case']])
                    or row['raw']['journey']['stops']!=review['stops'] or row['raw']['journey']['order']!=review['originalGraph']):
                raise ValueError('Reviewed Qwen graph drift')
            ai=Interpretation.model_validate(row['raw'])
            prod=production(review['source'],ai);old=v1.inspect_order(review['source'],ai);new=v2.inspect_order(review['source'],ai)
            edges={(x.before,x.after) for x in ai.journey.order}
            correct=edges=={tuple(x) for x in review['reviewedMandatoryRelationships']}
            if not correct:category='unsupported_raw_safely_normalized' if prod['legacyGraphNormalized'] else 'previously_accepted_unsupported_order'
            elif review['case']=='ambiguous':category='genuine_identity_ambiguity_other_constraint'
            elif prod['journeyBlocking']:category='correct_order_already_rejected_other_constraint'
            elif not positive(old):category='correct_order_newly_rejected_v1'
            else:category='compatible_correct_order_graph'
            qwen.append({**review,'rawHash':e.digest(row['raw']),'reviewedGraphCorrect':correct,
                'originalRecordedExecutionStatus':row.get('executionStatus'),
                'originalRecordedHadRequest':row.get('hasRequest'),
                'sourceHash':e.digest(review['source']),
                'category':category,'production':prod,'v1':old,'v2':new})
        cloud=[]
        db=sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True)
        try:
            for row in db.execute("select * from attempts where provider='openai' order by rowid"):
                record=json.loads(row[5]);content,_,_=e.Adapter('openai',None).decode(record['response'])
                c=next(c for c in e.corpus()['cases'] if c['id']==row[1]);ai=parse_interpretation(content)
                old=next(r for r in original['cloud'] if r['slot']==list(row[:3]))
                cloud.append({'slot':list(row[:3]),'originalRowHash':e.digest(row),
                    'historicalClassification':record['status'],'historicalDatabaseState':row[3],
                    'production':production(c['text'],ai),'v1':old['proposedOrdering'],
                    'v2':v2.inspect_order(c['text'],ai),'historicalEvidenceChanged':False})
        finally:db.close()
        fixtures=check_cases(newcases);held=check_cases(holdouts['cases'])
        oldcases=json.loads((DOCS/'task52-ordering-safety-cases.json').read_text())['cases']
        probes=negative_probes(oldcases)+negative_probes(newcases)
    # Repeatable fixture set; benchmark validation only, no routing/model work.
    timings={}
    for name,checker in [('production',lambda raw,ai:production(raw,ai)),('v1',v1.inspect_order),('v2',v2.inspect_order)]:
        durations=[]
        inputs=[(c['text'],fixture_reply(c)) for c in newcases]
        for _ in range(50):
            for raw,ai in inputs:
                start=time.perf_counter_ns();checker(raw,ai);durations.append((time.perf_counter_ns()-start)/1000)
        ordered=sorted(durations)
        timings[name]={'samples':len(ordered),'p50Microseconds':statistics.median(ordered),
            'p95Microseconds':ordered[int(.95*(len(ordered)-1))],'maxMicroseconds':max(ordered)}
    correct=[r for r in qwen if r['reviewedGraphCorrect']]
    unsafe=[r for r in qwen if not r['reviewedGraphCorrect']]
    summary={'qwenRows':len(qwen),'reviewedCorrectOrderGraphs':len(correct),'reviewedUnsupportedRawGraphs':len(unsafe),
        'reviewCategories':dict(Counter(r['category'] for r in qwen)),
        'v1Clarifications':sum(not positive(r['v1']) for r in qwen),'v2Clarifications':sum(not positive(r['v2']) for r in qwen),
        'v1UnnecessaryCorrectGraphClarifications':sum(not positive(r['v1']) for r in correct),
        'v2UnnecessaryCorrectGraphClarifications':sum(not positive(r['v2']) for r in correct),
        'previouslyNonblockingCorrectGraphs':sum(not r['production']['journeyBlocking'] for r in correct),
        'newClarificationsOnPreviouslyNonblockingCorrectGraphV1':sum(not positive(r['v1']) and not r['production']['journeyBlocking'] for r in correct),
        'newClarificationsOnPreviouslyNonblockingCorrectGraphV2':sum(not positive(r['v2']) and not r['production']['journeyBlocking'] for r in correct),
        'productionAcceptedUnsupportedQwenGraphs':sum(not r['production']['journeyBlocking'] and not r['production']['legacyGraphNormalized'] for r in unsafe),
        'v2AcceptedUnsupportedQwenGraphs':sum(positive(r['v2']) for r in unsafe),
        'legacyNormalizedGraphsRequiringPolicyDecision':sum(r['production']['legacyGraphNormalized'] for r in unsafe),
        'compatibilityCases':len(fixtures),'compatibilityOutcomesMatched':sum(positive(r['v2'])==r['expectedAcceptedOrdering'] for r in fixtures),
        'negativeProbeCount':len(probes),'productionUnsupportedProbesAccepted':sum(r['productionAcceptedUnsupported'] for r in probes),
        'v1UnsupportedProbesAccepted':sum(r['v1AcceptedUnsupported'] for r in probes),
        'v2UnsupportedProbesAccepted':sum(r['v2AcceptedUnsupported'] for r in probes),
        'postFreezeCases':len(held),'postFreezeOutcomesMatched':sum(positive(r['v2'])==r['expectedAcceptedOrdering'] for r in held)}
    # Confirm *after* timing/comparison too: never mutate paid evidence.
    if baseline.replay()!=original:raise ValueError('Private evidence changed during comparison')
    qwen_public=[]
    for row in qwen:
        keys=('cohort','row','case','rawHash','sourceHash','reviewedGraphCorrect','category',
            'originalRecordedExecutionStatus','originalRecordedHadRequest','production')
        qwen_public.append({**{k:row[k] for k in keys},'v1':brief(row['v1']),'v2':brief(row['v2'])})
    for row in cloud+fixtures+held:
        row['v1']=brief(row['v1']);row['v2']=brief(row['v2'])
    return {'version':v2.VERSION,'baselineGitHEAD':'5344aa786f3c7ac173ad8d0a9b7a10d0db86ba59',
        'comparisonModuleSHA256':sha(__file__),
        'moduleHashes':{'v1':sha(v1.__file__),'v2':sha(v2.__file__)},'summary':summary,
        'sourceFiles':{name:sha(DOCS/name) for name in ('task52-ordering-qwen-review-v2.json',
            'task52-ordering-compatibility-v2-cases.json','task52-ordering-compatibility-v2-holdouts.json')},
        'negativeProbeConstruction':'92 single unsupported-edge replacements:63 on old source fixtures +29 on new positive patterns. The original63 appended-edge tests also run unchanged; do not pool these as independent samples.',
        'qwen':qwen_public,'openai':cloud,'compatibilityCases':fixtures,'postFreezeCases':held,'negativeProbes':probes,
        'timing':{'measurement':'Local complete ordering check; production includes copy/Journey validation.50 repetitions of40 fixture interpretations; no HTTP, AI, routing or browser. Not full application latency.', 'results':timings},
        'journal':original['journal'],'historicalClassificationsUnchanged':True,
        'requestsSent':{'inference':0,'counting':0,'providerAPI':0},'independentHumanSignoff':False,
        'releaseDecision':'Offline only. Correct Qwen ordering compatibility restored; legacy normalization policy and broader source-scope coverage still need owner review before any production activation.'}


def build():
    with patch('socket.create_connection',side_effect=AssertionError('Offline only')),patch('requests.sessions.Session.send',side_effect=AssertionError('Offline only')):
        return _build()


def write_report(result,destination):
    """One line per comparison record keeps versioned evidence diffs readable."""
    if destination.is_symlink():raise ValueError('Refuse symlink output')
    fields=[]
    for key,value in result.items():
        if isinstance(value,list):
            encoded='[\n'+',\n'.join('    '+json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in value)+'\n  ]'
        else:
            encoded=json.dumps(value,indent=2,ensure_ascii=False).replace('\n','\n  ')
        fields.append('  '+json.dumps(key)+': '+encoded)
    content='{\n'+',\n'.join(fields)+'\n}\n'
    if json.loads(content)!=result:raise ValueError('Report serialization changed evidence')
    destination.write_text(content)


if __name__=='__main__':
    result=build()
    destination=DOCS/'task52-ordering-compatibility-v2.json'
    if destination.is_symlink():raise SystemExit('Refuse symlink output; paid evidence stays read-only')
    write_report(result,destination)
    print(json.dumps({'summary':result['summary'],'timings':result['timing']['results']}))
