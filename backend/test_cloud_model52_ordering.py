"""Offline synthetic tests; no owner credentials/journal or network access."""
import hashlib
import json
from pathlib import Path
import unittest

from backend.ai import Interpretation
from scripts import cloud_model52_ordering as order

FIXTURES = Path(__file__).resolve().parents[1] / 'docs/task52-ordering-safety-cases.json'


def cases():
    return json.loads(FIXTURES.read_text())['cases']


def reply(case):
    return Interpretation(activities=case['stops'], budget_per_person=None, date=None,
        location=case.get('location'), preferences=[], journey={'stops': [
            {'source': s, 'kind': case.get('kinds', ['activity'] * len(case['stops']))[i],
             'requirement': 'optional' if i in case.get('optional', []) else 'required'}
            for i, s in enumerate(case['stops'])], 'order': [
                {'before': a, 'after': b, 'source': case['text']}
                for a, b in case['expectedRelationships']]})


class OrderingSafetyTests(unittest.TestCase):
    def test_predeclared_31_source_rubrics_and_no_mutation(self):
        self.assertEqual(len(cases()), 31)
        for case in cases():
            with self.subTest(case=case['id']):
                ai = reply(case); before = ai.model_dump(mode='json')
                got = order.inspect_order(case['text'], ai)
                self.assertEqual(got['outcome'], case['expectedOutcome'], got)
                self.assertEqual({(p['before'], p['after']) for p in got['proofs']},
                                 {tuple(p) for p in case['expectedRelationships']}, got)
                self.assertEqual(ai.model_dump(mode='json'), before)

    def test_all_unproven_extra_and_reversed_pair_indices_fail(self):
        probes = 0
        for case in cases():
            if case['expectedOutcome'] == 'clarification_required': continue
            expected = [tuple(x) for x in case['expectedRelationships']]
            for a in range(len(case['stops'])):
                for b in range(len(case['stops'])):
                    if a == b or order.reach(expected, a, b): continue
                    ai = reply(case)
                    raw = ai.model_dump(mode='json')
                    raw['journey']['order'].append({'before':a, 'after':b, 'source':case['text']})
                    raw['journey']['ordering'] = 'constrained'
                    ai = Interpretation.model_validate(raw)
                    got = order.inspect_order(case['text'],ai)
                    self.assertEqual(got['outcome'],'clarification_required',(case['id'],a,b,got))
                    probes += 1
        self.assertGreater(probes, 40)

    def test_known_consumed_trailing_cue_and_valid_partial_quote(self):
        case = next(c for c in cases() if c['id']=='trailing-then')
        ai = reply(case)
        ai.journey.order[0].source = 'museum, then coffee'
        self.assertEqual(order.inspect_order(case['text'],ai)['outcome'],'verified_order')
        raw = ai.model_dump(mode='json')
        raw['journey']['order'].insert(0, {'before':0,'after':1,'source':'Coffee, museum, then'})
        got = order.inspect_order(case['text'],Interpretation.model_validate(raw))
        self.assertFalse(got['edges'][0]['proven'])
        self.assertTrue(got['edges'][1]['proven'])
        self.assertEqual(got['outcome'],'clarification_required')

    def test_cue_only_fabricated_quote_wrong_occurrence_missing_proof(self):
        case=next(c for c in cases() if c['id']=='two-independent-pairs')
        for span in ('then','Coffee then museum','Coffee → gallery'):
            ai=reply(case); ai.journey.order[1].source=span
            self.assertEqual(order.inspect_order(case['text'],ai)['outcome'],'clarification_required')
        ai=reply(case); ai.journey.order.pop()
        self.assertIn('missing_proven_required_relationship',order.inspect_order(case['text'],ai)['issues'])
        simple=next(c for c in cases() if c['id']=='simple-then')
        raw=reply(simple).model_dump(mode='json')
        raw['journey']['order'][0].update(before=1,after=0)
        wrong=Interpretation.model_validate(raw)
        self.assertFalse(wrong.journey.order_conflict) # Acyclic is insufficient.
        got=order.inspect_order(simple['text'],wrong)
        self.assertIn('unproven_model_edge',got['issues'])
        self.assertIn('missing_proven_required_relationship',got['issues'])

    def test_transitivity_requires_full_inside_quote_path_not_list_closure(self):
        case=next(c for c in cases() if c['id']=='chain')
        raw=reply(case).model_dump(mode='json')
        raw['journey']['order'].append({'before':0,'after':2,'source':case['text']})
        self.assertEqual(order.inspect_order(case['text'],Interpretation.model_validate(raw))['outcome'],'verified_order')
        raw['journey']['order'][-1]['source']='Coffee, then museum'
        self.assertEqual(order.inspect_order(case['text'],Interpretation.model_validate(raw))['outcome'],'clarification_required')

    def test_ownership_unique_offsets_names_and_work_bound(self):
        case=next(c for c in cases() if c['id']=='similar-names')
        ai=reply(case); got=order.inspect_order(case['text'],ai)
        for occurrence in got['occurrences']:
            a,b=occurrence['span'];self.assertEqual(case['text'][a:b],occurrence['text'])
        self.assertLess(got['occurrences'][0]['span'][1],got['occurrences'][1]['span'][0])
        self.assertEqual(order.bind_occurrences('coffee '*400,reply({'stops':['coffee']*32,'expectedRelationships':[]}).journey.stops)[1],
                         'occurrence_binding_work_limit')
        named={'text':'Visit First Bank and Last Cafe.', 'stops':['First Bank','Last Cafe'],
            'kinds':['named_place','named_place'], 'expectedRelationships':[]}
        ai=reply(named)
        self.assertEqual(order.inspect_order(named['text'],ai)['outcome'],'verified_no_mandatory_order')
        raw=ai.model_dump(mode='json')
        raw['journey'].update(order=[{'before':0,'after':1,'source':named['text']}],ordering='constrained')
        self.assertEqual(order.inspect_order(named['text'],Interpretation.model_validate(raw))['outcome'],'clarification_required')

    def test_long_evidence_does_not_make_unsupported_prose_valid(self):
        case=next(c for c in cases() if c['id']=='long-clause')
        self.assertGreater(len(case['text']),450);self.assertLessEqual(len(case['text']),500)
        raw=reply(case).model_dump(mode='json')
        raw['journey']['order']=[{'before':0,'after':1,'source':case['text']}]
        raw['journey']['ordering']='constrained'
        self.assertEqual(order.inspect_order(case['text'],Interpretation.model_validate(raw))['outcome'],'clarification_required')

    def test_no_production_or_cloud_configuration_imports(self):
        import ast
        source=Path(order.__file__).read_text();tree=ast.parse(source)
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual(len(imports),1);self.assertEqual(imports[0].names[0].name,'re')

    def test_six_post_freeze_synthetic_holdouts(self):
        data=json.loads(FIXTURES.with_name('task52-ordering-safety-holdouts.json').read_text())
        self.assertEqual(data['frozenModuleSHA256'],hashlib.sha256(Path(order.__file__).read_bytes()).hexdigest())
        for case in data['cases']:
            self.assertEqual(order.inspect_order(case['text'],reply(case))['outcome'],case['expectedOutcome'],case['id'])

    def test_readonly_cloud_replay_keeps_halted_classification(self):
        import sqlite3
        from scripts import cloud_model52 as e
        from scripts.cloud_model52_ordering_replay import cloud_rows
        from backend.test_cloud_model52 import output,response
        db=sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('create table attempts(provider,case_id,repetition,status,charge,record)')
        case=next(c for c in e.corpus()['cases'] if c['id']=='journey-04')
        record={'status':'complete','configurationHash':'synthetic-config','response':response('openai',output(case))}
        db.execute('insert into attempts values(?,?,?,?,?,?)',('openai','journey-04',1,'recorded_halted',2500000,json.dumps(record)))
        before=db.execute('select * from attempts').fetchall()
        got=cloud_rows(db,Path('/nonexistent-no-correction-needed'))
        self.assertEqual(got[0]['originalDatabaseState'],'recorded_halted')
        self.assertFalse(got[0]['historicalClassificationChanged'])
        self.assertTrue(got[0]['proposedCombinedAcceptedExtraction']) # Ordering replay cannot authorize dispatch.
        self.assertEqual(db.execute('select * from attempts').fetchall(),before)

    def test_27_historical_qwen_rows_replay_without_mutation_or_network(self):
        from scripts.cloud_model52_ordering_replay import qwen_rows
        from unittest.mock import patch
        path=FIXTURES.parents[1]/'backend/evaluation/results-task50e-model-investigation.json'
        before=path.read_bytes()
        with patch('requests.sessions.Session.send',side_effect=AssertionError('No network')):
            result=qwen_rows(path)
        self.assertEqual(len(result),27)
        self.assertEqual(path.read_bytes(),before)


if __name__=='__main__':unittest.main()
