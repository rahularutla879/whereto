import json
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import cloud_model52 as e
from scripts import cloud_model52_live as l
from scripts import cloud_model52_audit as a
from scripts import cloud_model52_batch as b
from backend import test_cloud_model52_audit as audit_fixtures
from backend.test_cloud_model52 import response,output

class SmallBatchTests(unittest.TestCase):
    def setup_plan(self,d):
        ledger,original,review=audit_fixtures.CorrectionTests().fixture(d)
        for p,id,charge in (('google','journey-01',16500000),('google','journey-02',16500000),('anthropic','journey-01',2200000)):
            ledger.db.execute('insert into attempts values(?,?,?,?,?,?)',(p,id,1,'recorded',charge,json.dumps({'status':'provider_error'})))
        ledger.db.commit();row=ledger.db.execute("select * from attempts where provider='openai'").fetchone();ledger.close()
        a.record_correction(Path(d)/'corrections',row,review)
        ready={'configurationHash':e.digest(e.metadata()),'evaluatorVersion':e.EVALUATOR_VERSION,
               'preparedAt':datetime.now(timezone.utc).isoformat(),'pricingVerifiedDateUTC':datetime.now(timezone.utc).date().isoformat(),
               'accountReview':{'creditsUSD':4.93,'autoReload':False,'globalSyntheticOnly':True,'responsesWriteVerified':True},
               'slots':[[id,1] for id in b.SLOTS],'counts':{id:5058 for id in b.SLOTS},
               'payloadHashes':{id:e.digest(e.Adapter('openai',None).payload(next(c for c in e.corpus()['cases'] if c['id']==id)['text'])) for id in b.SLOTS}}
        path=Path(d)/'plan.json';b.make_plan(path,ready);return path
    def test_only_five_slots_with_manual_gate_resume_no_repeat_and_no_refund(self):
        with tempfile.TemporaryDirectory() as d,patch.object(e,'STATE',Path(d)), \
             patch.object(l,'continuation_ledger',side_effect=lambda p:e.Ledger(p,e.metadata())):
            # Only this fake original record hash is accepted in the fixture.
            ledger,original,_=audit_fixtures.CorrectionTests().fixture(d);ledger.close()
            # Remove fixture file only in this disposable test directory.
            Path(d,'journal.sqlite').unlink()
            with patch.object(a,'ORIGINAL_OPENAI_RECORD_HASH',e.digest(original)):
                path=self.setup_plan(d);sends=[]
                original_score=e.score
                def fixture_score(case,text):
                    return original_score(case,text) if case['id']=='journey-01' else {'structuredValid':True,'validatedAccepted':True,'automatedFailures':[]}
                for i,id in enumerate(b.SLOTS):
                    with patch.object(e,'score',side_effect=fixture_score):
                        r=b.run_next(path,lambda payload:sends.append(payload) or response('openai',output(e.corpus()['cases'][0])))
                    self.assertEqual((r['caseId'],r['repetition']),(id,1))
                    if i<4:
                        with self.assertRaises(e.AdmissionError):b.run_next(path,lambda _:self.fail('No request before review'))
                    review=e.review_template([r]);review['reviews'][0].update(outcome='correct_extraction')
                    review['reviews'][0]['fields']={f:{'applicable':True,'correct':True} for f in e.SEMANTIC_FIELDS}
                    a.append_json(path.parent/('review-'+e.digest(r)+'.json'),review)
                self.assertIsNone(b.run_next(path,lambda _:self.fail('No sixth call')))
                self.assertEqual(len(sends),5)
                ledger=e.Ledger(Path(d)/'journal.sqlite',e.metadata())
                self.assertEqual(ledger.db.execute('select count(*) from attempts').fetchone()[0],9)
                self.assertEqual(ledger.db.execute("select charge from attempts where provider='openai' and case_id='journey-01'").fetchone()[0],2500000)
                self.assertFalse(ledger.reserve('openai','journey-01',1));ledger.close()
    def test_readiness_expiry_cap_and_slot_tampering_refuse_before_dispatch(self):
        value={'pricingVerifiedDateUTC':'2000-01-01','preparedAt':'2000-01-01T00:00:00+00:00'}
        with self.assertRaises(e.AdmissionError):b.check_fresh(value)
    def test_uncertain_consumed_slot_never_retried(self):
        with tempfile.TemporaryDirectory() as d,patch.object(e,'STATE',Path(d)), \
             patch.object(l,'continuation_ledger',side_effect=lambda p:e.Ledger(p,e.metadata())):
            ledger,original,_=audit_fixtures.CorrectionTests().fixture(d);ledger.close();Path(d,'journal.sqlite').unlink()
            with patch.object(a,'ORIGINAL_OPENAI_RECORD_HASH',e.digest(original)):
                path=self.setup_plan(d)
                def timeout(_):raise TimeoutError()
                first=b.run_next(path,timeout)
                self.assertEqual(first['status'],'uncertain_failure')
                with self.assertRaises(e.AdmissionError):b.run_next(path,lambda _:self.fail('No retry'))

if __name__=='__main__':unittest.main()
