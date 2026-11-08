"""One fixed owner-approved five-slot OpenAI screen; one call per invocation.

Immutable manifest + correction/reviews supplement, never replace, paid journal.
No provider substitution, automatic retries, warmups or automatic next request.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
from scripts import cloud_model52 as e
from scripts import cloud_model52_live as l
from scripts import cloud_model52_audit as a

BATCH_NAME='openai-small-screen-after-15b1122'
INFERENCE_CONFIG_HASH='1c2352a7ec2b0bf826567de22b36ff2265bcd957e979d5b307cface7b5e0ee4e'
SLOTS=('ordinary-dinner','journey-03','journey-07','journey-12','journey-06')
PLAN=e.STATE/(BATCH_NAME+'.json')


def check_fresh(value):
    now=datetime.now(timezone.utc)
    if value.get('pricingVerifiedDateUTC')!=now.date().isoformat():
        raise e.AdmissionError('Daily model/pricing/processing verification expired')
    age=(now-datetime.fromisoformat(value['preparedAt'])).total_seconds()
    if not 0<=age<=86400:raise e.AdmissionError('Batch readiness expired')
    if value['configurationHash']!=INFERENCE_CONFIG_HASH or value['configurationHash']!=e.digest(e.metadata()) or value['evaluatorVersion']!=e.EVALUATOR_VERSION:
        raise e.AdmissionError('Batch inference/evaluator configuration changed')
    review=value.get('accountReview',{})
    credit=review.get('creditsUSD')
    if type(credit) not in (int,float) or credit<.0125 or review.get('autoReload') is not False or review.get('globalSyntheticOnly') is not True or review.get('responsesWriteVerified') is not True:
        raise e.AdmissionError('Account review missing/insufficient; refresh funded account evidence')
    if value['slots']!=[[id,1] for id in SLOTS] or len(SLOTS)!=5:
        raise e.AdmissionError('Outside the approved five original slots')
    cases={c['id']:c for c in e.corpus()['cases']}
    for id in SLOTS:
        count=value['counts'][id]
        if type(count) is not int or not 0<count<=e.INPUT_CAP-2048:
            raise e.AdmissionError('Complete-input count missing/over conservative cap')
        if value['payloadHashes'][id]!=e.digest(e.Adapter('openai',None).payload(cases[id]['text'])):
            raise e.AdmissionError('Counted input/request changed')


def make_plan(path,readiness):
    """Caller has completed official/account/token review; no inference here."""
    import sqlite3
    check_fresh(readiness)
    if path.exists():raise e.AdmissionError('Original batch plan already exists; never create another allowance')
    db=sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True)
    try:
        rows=db.execute('select * from attempts order by rowid').fetchall()
        if len(rows)!=4 or sum(r[4] for r in rows)!=37700000:
            raise e.AdmissionError('Reconcile original four-attempt baseline before this batch')
        for row in rows:
            if row[0]=='openai':a.effective_record(row,e.STATE/'corrections')
        for case_id in SLOTS:
            if db.execute('select 1 from attempts where provider=? and case_id=? and repetition=1',('openai',case_id)).fetchone():
                raise e.AdmissionError('Selected batch slot already consumed')
        value={**readiness,'baselineRows':[{'slot':list(r[:3]),'rowHash':e.digest(r)} for r in rows],
               'baselineRoot':db.execute('select config from metadata').fetchone()[0],
               'batch':BATCH_NAME,'maxNewAttempts':5,'retries':0,'concurrency':1}
        a.append_json(path,value)
        a.append_json(path.with_suffix('.seal.json'),{'planHash':e.digest(value)})
    finally:db.close()
    return value


def run_next(path=PLAN,transport=None):
    """Dispatch at most one unused slot. Resume skips consumed/reviewed slots.

    A previous noncomplete output, uncertain reservation, semantic mismatch or
    missing explicit rubric review blocks the next request without retrying.
    """
    plan=json.loads(path.read_text());check_fresh(plan)
    if json.loads(path.with_suffix('.seal.json').read_text())!={'planHash':e.digest(plan)}:
        raise e.AdmissionError('Immutable batch plan changed')
    if plan.get('maxNewAttempts')!=5 or plan.get('batch')!=BATCH_NAME or plan.get('concurrency')!=1 or plan.get('retries')!=0:
        raise e.AdmissionError('Unapproved batch allowance/settings')
    with e.exclusive(e.STATE):
        ledger=l.continuation_ledger(e.STATE/'journal.sqlite')
        try:
            if ledger.db.execute('select config from metadata').fetchone()[0]!=plan['baselineRoot']:
                raise e.AdmissionError('Original paid metadata changed')
            for old in plan['baselineRows']:
                row=ledger.db.execute('select * from attempts where provider=? and case_id=? and repetition=?',old['slot']).fetchone()
                if not row or e.digest(row)!=old['rowHash']:raise e.AdmissionError('Original paid attempt changed')
            allowed={tuple(old['slot']) for old in plan['baselineRows']} | {('openai',id,repeat) for id,repeat in plan['slots']}
            existing={tuple(row) for row in ledger.db.execute('select provider,case_id,repetition from attempts')}
            if existing-allowed:
                raise e.AdmissionError('Unexpected paid attempt outside original baseline/batch')
            # Only native successes or independently audited decoder correction
            # may count as complete. No correction refunds or reuses a slot.
            all_oa=ledger.db.execute("select * from attempts where provider='openai'").fetchall()
            selected={id for id,_ in plan['slots']}
            for row in all_oa:
                effective=a.effective_record(row,e.STATE/'corrections')
                if (row[1],row[2])!=('journey-01',1) and (row[1] not in selected or row[2]!=1):
                    raise e.AdmissionError('Unreviewed attempt outside fixed screen')
                if row[1] in selected:
                    if (effective.get('evaluatorVersion')!=e.EVALUATOR_VERSION or not effective.get('scoring',{}).get('structuredValid') or effective.get('scoring',{}).get('automatedFailures')):
                        raise e.AdmissionError('Previous response needs evaluator/failure review')
                    review_path=path.parent/('review-'+e.digest(json.loads(row[5]))+'.json')
                    if not review_path.exists():raise e.AdmissionError('Previous output needs rubric review before further spending')
                    reviewed=e.adjudicate([effective],json.loads(review_path.read_text()))
                    if reviewed['fullyCorrectReviewedAttempts']!=1 or reviewed['criticalFailures']:
                        raise e.AdmissionError('Previous output did not pass review')
            for id,repeat in plan['slots']:
                if ledger.db.execute('select 1 from attempts where provider=? and case_id=? and repetition=?',('openai',id,repeat)).fetchone():continue
                case=next(c for c in e.corpus()['cases'] if c['id']==id)
                payload=e.Adapter('openai',None).payload(case['text'])
                bound=plan['counts'][id]+2048
                if e.digest(payload)!=plan['payloadHashes'][id] or not 0<bound<=e.INPUT_CAP:
                    raise e.AdmissionError('Prepared complete-input hash/cap mismatch')
                # Selection/input checks precede the committed-before-I/O reserve.
                adapter=e.Adapter('openai',transport if transport is not None else l.HTTP('openai',l.credentials()['openai']))
                return e._run_one(ledger,adapter,case,repeat,bound)
            return None
        finally:ledger.close()
