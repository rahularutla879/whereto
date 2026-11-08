"""Offline compatibility and adversarial checks; no owner journal or credentials."""
import hashlib
import json
from pathlib import Path
import unittest

from backend.ai import Interpretation
from backend.test_cloud_model52_ordering import reply, cases as original_cases
from scripts import cloud_model52_ordering as v1
from scripts import cloud_model52_ordering_v2 as v2

DOCS=Path(__file__).resolve().parents[1]/'docs'


def cases():
    return json.loads((DOCS/'task52-ordering-compatibility-v2-cases.json').read_text())['cases']


class CompatibilityTests(unittest.TestCase):
    def test_v1_frozen_original_rubrics_holdouts_and_63_probes(self):
        frozen=json.loads((DOCS/'task52-ordering-safety-holdouts.json').read_text())
        self.assertEqual(hashlib.sha256(Path(v1.__file__).read_bytes()).hexdigest(),frozen['frozenModuleSHA256'])
        for c in original_cases():
            self.assertEqual(v1.inspect_order(c['text'],reply(c))['outcome'],c['expectedOutcome'])
        for c in frozen['cases']:
            self.assertEqual(v1.inspect_order(c['text'],reply(c))['outcome'],c['expectedOutcome'])
        count=0
        for c in original_cases():
            if c['expectedOutcome']=='clarification_required':continue
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or v1.reach([tuple(x) for x in c['expectedRelationships']],a,b):continue
                    raw=reply(c).model_dump(mode='json')
                    raw['journey'].update(order=raw['journey']['order']+[{'before':a,'after':b,'source':c['text']}],ordering='constrained')
                    ai=Interpretation.model_validate(raw)
                    for checker in (v1,v2):self.assertEqual(checker.inspect_order(c['text'],ai)['outcome'],'clarification_required')
                    count+=1
        self.assertEqual(count,63)

    def test_40_declared_compatibility_patterns_and_negatives_without_mutation(self):
        self.assertEqual(len(cases()),40)
        for c in cases():
            with self.subTest(case=c['id']):
                ai=reply(c);before=ai.model_dump(mode='json')
                r=v2.inspect_order(c['text'],ai)
                self.assertEqual(r['outcome']!='clarification_required',c['accept'],r)
                self.assertEqual(before,ai.model_dump(mode='json'))
                if c['accept']:
                    # Quotes may omit source-leading whitespace; their actual
                    # stop/cue coordinates must still be owned and contained.
                    self.assertTrue(v2.inspect_order('  '+c['text'],ai)['outcome']!='clarification_required',c['id'])
                for p in r['proofs']:
                    a,b=p['span'];self.assertEqual(c['text'][a:b],p['source'])
                    self.assertIsNotNone(v2.CUE.fullmatch(c['text'][slice(*p['cueSpan'])]))
        # Remaining common coverage limit: scope of a comma-separated optional
        # third stop is conservative. Record the false clarification explicitly
        # instead of silently dropping the proven-looking requirement or
        # declaring universal production readiness from Qwen compatibility.
        c={'text':'Visit pharmacy before bank, maybe get coffee.',
            'stops':['pharmacy','bank','coffee'],'expectedRelationships':[[0,1]],'optional':[2]}
        ai=reply(c);ai.journey.stops[2].evidence='maybe get coffee'
        self.assertEqual(v2.inspect_order(c['text'],ai)['outcome'],'clarification_required')

    def test_new_positive_rules_reject_every_unproven_direction_and_occurrence(self):
        probes=0
        for c in cases():
            if not c['accept']:continue
            edges=[tuple(x) for x in c['expectedRelationships']]
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or v1.reach(edges,a,b):continue
                    raw=reply(c).model_dump(mode='json')
                    # Replace, rather than merely create a cycle alongside
                    # the correct edge: an acyclic wrong graph must also fail.
                    raw['journey'].update(order=[{'before':a,'after':b,'source':c['text']}],ordering='constrained')
                    r=v2.inspect_order(c['text'],Interpretation.model_validate(raw))
                    self.assertEqual(r['outcome'],'clarification_required',(c['id'],a,b,r))
                    probes+=1
        self.assertGreater(probes,20)

    def test_fronted_and_ordinal_proofs_require_their_actual_cue_span(self):
        for name,quote in [('after-visiting','pharmacy, go to coffee'),
                ('before-going','bank, stop at pharmacy'),
                ('ordinal-prefix','pharmacy, second visit bank, third get coffee')]:
            c=next(x for x in cases() if x['id']==name);ai=reply(c)
            ai.journey.order[0].source=quote
            self.assertEqual(v2.inspect_order(c['text'],ai)['outcome'],'clarification_required')
        # Integration must not discard a newly proven start/finish relation:
        # the current legacy cue vocabulary predates that rule. This remains
        # a production integration blocker, not permission to repair outputs.
        from backend.journey import validate_journey
        c=next(x for x in cases() if x['id']=='start-finish');ai=reply(c)
        canonical=ai.model_copy(deep=True);validate_journey(c['text'],canonical)
        self.assertEqual(len(ai.journey.order),1)
        self.assertEqual(canonical.journey.order,[])
        self.assertIn('missing_proven_required_relationship',v2.inspect_order(c['text'],canonical)['issues'])

    def test_order_words_in_venue_names_are_not_cue_offsets(self):
        c={'text':'Visit First Bank, then Last Cafe.', 'stops':['First Bank','Last Cafe'],
            'kinds':['named_place','named_place'],'expectedRelationships':[[0,1]]}
        r=v2.inspect_order(c['text'],reply(c))
        self.assertEqual(r['outcome'],'verified_order')
        self.assertEqual(c['text'][slice(*r['proofs'][0]['cueSpan'])],'then')

    def test_all_27_reviewed_qwen_graphs_and_six_clear_regressions(self):
        review=json.loads((DOCS/'task52-ordering-qwen-review-v2.json').read_text())
        actual=json.loads((DOCS.parent/'backend/evaluation/results-task50e-model-investigation.json').read_text())
        texts={r['case']:r['text'] for r in actual['baseline']['rows']}
        self.assertEqual(len(review['rows']),27)
        restored=0
        for row in review['rows']:
            original=actual[row['cohort']]['rows'][row['row']]
            self.assertEqual(row['source'],original.get('text') or texts[original['case']])
            self.assertEqual(row['originalGraph'],original['raw']['journey']['order'])
            self.assertEqual(row['stops'],original['raw']['journey']['stops'])
            ai=Interpretation.model_validate(original['raw'])
            before=ai.model_dump(mode='json')
            old=v1.inspect_order(row['source'],ai);new=v2.inspect_order(row['source'],ai)
            actual_edges={(e.before,e.after) for e in ai.journey.order}
            correct=actual_edges=={tuple(e) for e in row['reviewedMandatoryRelationships']}
            if correct:
                self.assertNotEqual(new['outcome'],'clarification_required',row)
                restored+=old['outcome']=='clarification_required'
            else:self.assertEqual(new['outcome'],'clarification_required',row)
            self.assertEqual(before,ai.model_dump(mode='json'))
        self.assertEqual(restored,6)

    def test_dependency_boundary_is_offline_only(self):
        import ast
        tree=ast.parse(Path(v2.__file__).read_text())
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual(len(imports),2)
        self.assertEqual(imports[1].module,'scripts.cloud_model52_ordering')
        from scripts.cloud_model52_ordering_compatibility import positive
        for unknown in ('unknown','error','refused','clarification_required'):
            self.assertFalse(positive({'outcome':unknown}))

    def test_separate_eight_post_freeze_holdouts(self):
        data=json.loads((DOCS/'task52-ordering-compatibility-v2-holdouts.json').read_text())
        self.assertEqual(data['frozenModuleSHA256'],hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest())
        self.assertEqual(len(data['cases']),8)
        for c in data['cases']+data['regressionCases']:
            self.assertEqual(v2.inspect_order(c['text'],reply(c))['outcome']!='clarification_required',c['accept'],c['id'])


if __name__=='__main__':unittest.main()
