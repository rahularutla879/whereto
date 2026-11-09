"""Adversarial fake outputs only: no paid network, private state or gold changes."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from backend.ai import Interpretation
from backend.test_cloud_model52 import output, response
from scripts import cloud_model52 as e
from scripts.cloud_model52_semantics import compare_reference, evidence_failures, reference_wire


class SemanticComparatorTests(unittest.TestCase):
    def case(self,id):return next(c for c in e.corpus()['cases'] if c['id']==id)
    def scored(self,id,change):
        c=self.case(id);value=json.loads(output(c));change(value)
        return e.score(c,json.dumps(value))
    def test_all_25_original_references_still_pass_without_edit(self):
        for c in e.corpus()['cases'][:25]:
            with self.subTest(case=c['id']):
                self.assertFalse(e.score(c,output(c))['automatedFailures'])
    def test_unspecified_reference_allows_grounded_owned_span(self):
        s=self.scored('journey-01',lambda v:[stop.update(evidence=stop['source']) for stop in v['journey']['stops']])
        self.assertTrue(s['structuredValid']);self.assertTrue(s['validatedAccepted'])
        self.assertFalse(s['automatedFailures'])
    def test_hallucinated_and_other_stop_evidence_fail(self):
        for span in ('the Eiffel Tower','drinks'):
            s=self.scored('journey-01',lambda v:v['journey']['stops'][0].update(evidence=span))
            self.assertIn('sourceEvidenceAttachment',s['automatedFailures'])
            if span=='the Eiffel Tower':self.assertFalse(s['validatedAccepted'])
            else:self.assertTrue(s['validatedAccepted']) # Existing validator unchanged.
    def test_explicit_reference_evidence_is_not_a_wildcard(self):
        for span in ('','and maybe stop for coffee'):
            s=self.scored('journey-06',lambda v:v['journey']['stops'][1].update(evidence=span))
            self.assertIn('journeySemantics',s['automatedFailures'])
            self.assertIn('stops[1].explicitReferenceEvidence',s['referenceFailures'])
    def test_live_ordering_failure_is_safe_rejection_not_json_success(self):
        # Reproduce the third screen response offline, without retrying its slot.
        def change(v):
            v['activities']=['the pharmacy','the supermarket']
            for stop,source,evidence in zip(v['journey']['stops'],v['activities'],
                    ['Go to the pharmacy first','then the supermarket']):
                stop.update(source=source,evidence=evidence)
            v['journey']['order'][0]['source']='first, then'
        s=self.scored('journey-07',change)
        self.assertTrue(s['structuredValid'])
        self.assertFalse(s['validatedAccepted'])
        self.assertIn('trustedDisposition',s['referenceFailures'])
        # Mere connective words do not identify the two stops bound by an edge.
        self.assertTrue(s['issues'])
    def test_omitted_required_schema_property_cannot_pass_as_default(self):
        s=self.scored('journey-01',lambda v:v['journey']['stops'][0].pop('evidence'))
        self.assertFalse(s['structuredValid']);self.assertTrue(s['missingRequiredProperties'])
        s=self.scored('journey-01',lambda v:v.pop('people'))
        self.assertFalse(s['structuredValid'])
    def test_optional_status_stop_multiplicity_identity_are_strict(self):
        changes=[('journey-06',lambda v:v['journey']['stops'][1].update(requirement='required')),
                 ('journey-01',lambda v:v['journey']['stops'].pop()),
                 ('journey-03',lambda v:v['journey']['stops'][0].update(source='College of Optometry')),
                 ('journey-11',lambda v:v['journey']['endpoint'].update(source='finish'))]
        for id,change in changes:
            with self.subTest(case=id):self.assertTrue(self.scored(id,change).get('automatedFailures'))
    def test_raw_invented_order_and_relation_not_hidden_by_trusted_repair(self):
        def order(v):v['journey'].update(ordering='constrained',order=[{'before':0,'after':1,'source':'Dinner and drinks'}])
        self.assertIn('journeySemantics',self.scored('journey-01',order)['automatedFailures'])
        self.assertIn('journeySemantics',self.scored('journey-12',lambda v:v['journey']['total_duration'].update(relation='under'))['automatedFailures'])
    def test_return_deadline_duration_and_default_scalar_mismatches_fail(self):
        changes=[('journey-10',lambda v:v['journey'].update(endpoint=None)),
                 ('journey-12',lambda v:v['journey']['total_duration'].update(minutes=30)),
                 ('journey-14',lambda v:v['journey']['deadline'].update(relation='before')),
                 ('journey-15',lambda v:v['journey']['stops'][0]['duration'].update(minutes=5)),
                 ('journey-01',lambda v:v.update(people=4)),
                 ('journey-01',lambda v:v.update(date_expressions=[]))]
        for id,change in changes:
            with self.subTest(case=id):self.assertTrue(self.scored(id,change).get('automatedFailures'))
    def test_owned_repetition_mapping_does_not_accept_other_occurrence(self):
        j=Interpretation.model_validate({'activities':['coffee','museum','coffee'],'location':None,'date':None,'budget_per_person':None,'preferences':[],
            'journey':{'stops':[{'source':'coffee','evidence':'coffee'},{'source':'museum','evidence':'museum'},{'source':'coffee','evidence':'museum'}]}}).journey
        self.assertIn('stops[2].evidenceAttachment',evidence_failures('coffee then museum then coffee',j))
        j.stops[2].evidence='coffee';self.assertFalse(evidence_failures('coffee then museum then coffee',j))
    def test_partial_order_is_graph_not_edge_serialization(self):
        c=self.case('journey-01');j=Interpretation.model_validate(c['expectedExtraction']).journey
        # Source-grounding still gates every real edge; graph equivalence never
        # permits an invented edge in the unordered original reference.
        self.assertFalse(j.order)
        changed=copy.deepcopy(c['expectedExtraction']);changed['journey']['order']=[{'before':0,'after':1,'source':'Dinner and drinks'}];changed['journey']['ordering']='constrained'
        raw=Interpretation.model_validate(changed);_,result=e.validate(c,json.dumps(reference_wire(c)))
        self.assertTrue(compare_reference(c,raw,result))
    def test_unknown_destination_not_replaced_with_familiar_city(self):
        c=self.case('ordinary-unknown')
        v=reference_wire(self.case('journey-23'));v.update(activities=['movies'],location='Hyderabad',date_expressions=['today'])
        v['journey']['stops']=[{'source':'movies','kind':'activity','requirement':'required','evidence':'movies','duration':None}]
        s=e.score(c,json.dumps(v));self.assertFalse(s['automatedChecks']['location'])
    def test_accepted_wrong_evidence_triggers_durable_review_halt(self):
        c=self.case('journey-01');value=json.loads(output(c));value['journey']['stops'][0]['evidence']='drinks'
        with tempfile.TemporaryDirectory() as d:
            ledger=e.Ledger(Path(d)/'journal.sqlite',e.metadata())
            record=e.run_one(ledger,e.Adapter('openai',lambda _:response('openai',json.dumps(value))),c,1,6000)
            self.assertTrue(record['reviewHalt'])
            with self.assertRaises(e.AdmissionError):ledger.reserve('openai','journey-02',1)
            ledger.close()


# Offline fake fixtures only; the unmodified paid source gate rejects B2.
def load_tests(loader, tests, pattern):
    from scripts.task52_b2_test_fixture import OfflineUnitSuite
    return OfflineUnitSuite(tests)


if __name__=='__main__':unittest.main()
