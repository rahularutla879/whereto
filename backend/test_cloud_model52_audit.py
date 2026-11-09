import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import cloud_model52 as e
from scripts import cloud_model52_audit as a
from backend.test_cloud_model52 import output,response

class CorrectionTests(unittest.TestCase):
    def fixture(self,d):
        case=e.corpus()['cases'][0];payload=e.Adapter('openai',None).payload(case['text'])
        raw=response('openai',output(case));raw.update(error=None,_http_status=200,model='gpt-6-luna')
        # Historical classification only; no paid request occurs in this fixture.
        record={'provider':'openai','model':'gpt-6-luna','caseId':'journey-01','repetition':1,
                'status':'provider_error','response':raw,'configurationHash':e.digest(e.metadata()),
                'payloadHash':e.digest(payload),'latencyMs':1,'accountedNanodollars':2500000}
        derived={**record,'status':'complete','usage':[100,20],'scoring':e.score(case,output(case))}
        review=e.review_template([derived]);item=review['reviews'][0];item.update(outcome='correct_extraction')
        item['fields']={k:{'applicable':True,'correct':True} for k in e.SEMANTIC_FIELDS}
        ledger=e.Ledger(Path(d)/'journal.sqlite',e.metadata())
        ledger.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',('openai','journey-01',1,'recorded',2500000,json.dumps(record)))
        ledger.db.commit()
        return ledger,record,review
    def test_append_only_recovery_never_rewrites_refunds_or_retries(self):
        with tempfile.TemporaryDirectory() as d:
            ledger,record,review=self.fixture(d);row=ledger.db.execute('select * from attempts').fetchone()
            root=ledger.db.execute('select config from metadata').fetchone();before=Path(d,'journal.sqlite').read_bytes()
            with patch.object(a,'ORIGINAL_OPENAI_RECORD_HASH',e.digest(record)):
                path=a.record_correction(Path(d)/'corrections',row,review)
                self.assertEqual(a.record_correction(path.parent,row,review),path)
                self.assertEqual(a.effective_record(row,path.parent)['status'],'complete')
                self.assertEqual(a.effective_record(row,path.parent)['accountedNanodollars'],2500000)
                self.assertFalse(ledger.reserve('openai','journey-01',1))
                self.assertEqual(ledger.db.execute('select * from attempts').fetchone(),row)
                self.assertEqual(ledger.db.execute('select config from metadata').fetchone(),root)
                self.assertEqual(Path(d,'journal.sqlite').read_bytes(),before)
                changed=json.loads(path.read_text());changed['financialAdjustmentNanodollars']=-2500000
                with self.assertRaises(e.AdmissionError):a.append_json(path,changed)
                path.write_text(json.dumps(changed))
                with self.assertRaises(e.AdmissionError):a.effective_record(row,path.parent)
            ledger.close()
    def test_missing_or_stale_evidence_review_and_halts_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            ledger,record,review=self.fixture(d);row=ledger.db.execute('select * from attempts').fetchone()
            with patch.object(a,'ORIGINAL_OPENAI_RECORD_HASH',e.digest(record)):
                with self.assertRaises(e.AdmissionError):a.effective_record(row,Path(d)/'corrections')
                bad=dict(record);bad['response']={**bad['response'],'_http_status':400}
                with self.assertRaises(e.AdmissionError):a.correction_value((*row[:5],json.dumps(bad)),review)
                with self.assertRaises(e.AdmissionError):a.correction_value((*row[:4],0,row[5]),review)
                broken=json.loads(json.dumps(review));broken['reviews'][0]['fields']['grounding']['correct']=False
                with self.assertRaises(e.AdmissionError):a.correction_value(row,broken)
                a.record_correction(Path(d)/'corrections',row,review)
                with self.assertRaises(e.AdmissionError):a.effective_record((*row[:3],'recorded_halted',*row[4:]),Path(d)/'corrections')
            ledger.close()


# Offline fake fixtures only; the unmodified paid source gate rejects B2.
def load_tests(loader, tests, pattern):
    from scripts.task52_b2_test_fixture import OfflineUnitSuite
    return OfflineUnitSuite(tests)


if __name__=='__main__':unittest.main()
