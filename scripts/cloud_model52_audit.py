"""Append-only offline classification corrections; never rewrites paid attempts."""
import json
import os
from pathlib import Path
from scripts import cloud_model52 as e

ORIGINAL_OPENAI_RECORD_HASH = 'e1750bfe6fff68fd3fe6f4cead6884ba5d495681f617a9bad5f1af6b9a80cbba'


def append_json(path,value):
    """Exclusive immutable creation; an existing different value is an error."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.exists():
        if json.loads(path.read_text())!=value:raise e.AdmissionError('Append-only audit conflict')
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    directory=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)


def correction_value(row,review):
    provider,case_id,repeat,state,charge,encoded=row
    record=json.loads(encoded)
    if (provider,case_id,repeat,state,record.get('status'))!=('openai','journey-01',1,'recorded','provider_error'):
        raise e.AdmissionError('Correction only covers the original decoder-misclassified slot')
    if charge!=2500000 or record.get('accountedNanodollars')!=charge:
        raise e.AdmissionError('Original reservation must remain unchanged')
    if e.digest(record)!=ORIGINAL_OPENAI_RECORD_HASH:
        raise e.AdmissionError('Immutable original OpenAI record hash changed')
    case=next(c for c in e.corpus()['cases'] if c['id']==case_id)
    if record['model']!='gpt-6-luna' or record['configurationHash']!=e.digest(e.metadata()) or record['payloadHash']!=e.digest(e.Adapter(provider,None).payload(case['text'])):
        raise e.AdmissionError('Original model/request/configuration mismatch')
    response=record['response']
    if response.get('_http_status')!=200 or response.get('status')!='completed' or response.get('error') is not None or response.get('model')!='gpt-6-luna':
        raise e.AdmissionError('Provider evidence does not establish completed Luna response')
    content,usage,status=e.Adapter(provider,None).decode(response)
    case=next(c for c in e.corpus()['cases'] if c['id']==case_id)
    scoring=e.score(case,content)
    if status!='complete' or not scoring['structuredValid'] or not scoring['validatedAccepted'] or scoring.get('automatedFailures'):
        raise e.AdmissionError('Offline correction failed current structure/grounding/semantic checks')
    if not usage or any(type(n) is not int or n<0 for n in usage) or usage[0]>e.INPUT_CAP or usage[1]>e.OUTPUT_CAP:
        raise e.AdmissionError('Correction usage invalid/over cap')
    derived={**record,'status':status,'usage':usage,'scoring':scoring}
    checked=e.adjudicate([derived],review)
    if checked['fullyCorrectReviewedAttempts']!=1 or checked['criticalFailures']:
        raise e.AdmissionError('Complete reviewed rubric required before reconciliation')
    return {'kind':'offline_decoder_correction_v1','slot':[provider,case_id,repeat],
        'model':record['model'],'originalDatabaseState':state,'originalClassification':record['status'],
        'originalRecordHash':e.digest(record),'providerResponseHash':e.digest(response),
        'correctedClassification':status,'originalReservationNanodollars':charge,'financialAdjustmentNanodollars':0,
        'configurationHash':record['configurationHash'],'payloadHash':record['payloadHash'],
        'corpusHash':e.CORPUS_SHA,'evaluatorVersion':e.EVALUATOR_VERSION,'correctedScoring':scoring,
        'review':review,'reviewerKind':'agent rubric inspection; independent human signoff not performed',
        'usage':list(usage),'originalTimingMs':record['latencyMs']}


def record_correction(directory,row,review):
    value=correction_value(row,review)
    path=Path(directory)/('correction-'+e.digest(value)+'.json')
    append_json(path,value)
    return path


def effective_record(row,directory):
    """A correction never admits a retry, refunds cost or clears a review halt."""
    if row[3]=='reserved_uncertain' or row[5] is None:raise e.AdmissionError('Uncertain original attempt')
    record=json.loads(row[5])
    if row[3]=='recorded_halted':raise e.AdmissionError('Persistent review halt')
    if record.get('status')=='complete':return record
    matches=[]
    for path in Path(directory).glob('correction-*.json'):
        value=json.loads(path.read_text())
        if value.get('slot')!=list(row[:3]):continue
        if path.name!='correction-'+e.digest(value)+'.json':raise e.AdmissionError('Correction content hash mismatch')
        if value!=correction_value(row,value['review']):raise e.AdmissionError('Correction no longer independently verifies')
        matches.append(value)
    if len(matches)!=1:raise e.AdmissionError('No unique verified append-only correction')
    value=matches[0]
    return {**record,'status':value['correctedClassification'],'usage':value['usage'],
            'scoring':value['correctedScoring'],'auditCorrectionHash':e.digest(value),
            'originalRecordedClassification':record['status'],'accountedNanodollars':row[4]}
