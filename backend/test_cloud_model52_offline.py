"""Offline fake outputs. No cloud/local model or owner configuration access."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from backend.ai import Interpretation
from backend.journey import REPHRASE, validate_journey
from backend.journey_fixtures import reply
from scripts import cloud_model52 as e
from scripts import cloud_model52_offline as offline
from scripts import cloud_model52_proposal as proposal
from scripts.cloud_model52_semantics import reference_wire


def fixture(text, phrases, **kwargs):
    return {'id': 'offline-only', 'text': text, 'expectedExtraction': reply(phrases, **kwargs)}


@contextmanager
def reference(case):
    _, gold = e.validate(case, json.dumps(reference_wire(case)))
    with patch('scripts.cloud_model52_semantics.reference_result', return_value=gold):
        yield


class OfflineComparisonTests(unittest.TestCase):
    def test_all_25_original_references_and_evidence_placeholder_still_pass(self):
        for case in e.corpus()['cases'][:25]:
            with self.subTest(case=case['id']):
                value = reference_wire(case)
                self.assertFalse(offline.score(case, json.dumps(value))['automatedFailures'])
        case = e.corpus()['cases'][0]; value = reference_wire(case)
        for stop in value['journey']['stops']: stop['evidence'] = stop['source']
        scored = offline.score(case, json.dumps(value))
        self.assertFalse(scored['automatedFailures'])
        self.assertIsNone(scored['fullyCorrect']); self.assertTrue(scored['reviewRequired'])

    def test_generic_the_is_occurrence_bound_and_evaluation_only(self):
        case = fixture('Go to the pharmacy first, then the supermarket.', ['pharmacy', 'supermarket'],
            order=[(0, 1, 'pharmacy first, then the supermarket')])
        value = reference_wire(case)
        value['activities'] = ['the pharmacy', 'the supermarket']
        for stop, source in zip(value['journey']['stops'], value['activities']):
            stop['source'] = source
        value['journey']['order'][0]['source'] = 'the pharmacy first, then the supermarket'
        original = copy.deepcopy(value)
        with reference(case):
            old = e.score(case, json.dumps(value))
            new = offline.score(case, json.dumps(value))
        self.assertIn('activities', old['automatedFailures'])
        self.assertFalse(new['automatedFailures'])
        self.assertEqual(len(new['comparisonProjections']), 2)
        self.assertEqual(new['validatedAccepted'], old['validatedAccepted'])
        self.assertEqual(value, original)

    def test_negative_names_brands_number_and_modifiers_never_normalize(self):
        for actual, gold, kind in [('The Pharmacy', 'Pharmacy', 'named_place'),
                ('the pharmacy', 'pharmacy', 'brand'), ('the museum', 'museum', 'named_place'),
                ('the who', 'who', 'activity'), ('pharmacies', 'pharmacy', 'activity'),
                ('the pharmacies', 'pharmacy', 'activity'), ('a pharmacy', 'pharmacy', 'activity'),
                ('the outlet pharmacy', 'pharmacy', 'activity'), ('the pharmacy', 'Pharmacy', 'activity'),
                ('the coffee shop', 'coffee', 'activity')]:
            with self.subTest(actual=actual, gold=gold, kind=kind):
                case = fixture('Visit ' + actual + '.', [gold], kinds={0: kind})
                value = reference_wire(case)
                value['activities'] = [actual]
                value['journey']['stops'][0]['source'] = actual
                projected, changes = offline.article_projection(case, Interpretation.model_validate(value))
                self.assertFalse(changes)
                self.assertEqual(projected.activities, [actual])

    def test_case_of_original_proper_name_cannot_be_hidden_by_model_kind(self):
        case = fixture('Visit The Pharmacy.', ['Pharmacy'])
        value = reference_wire(case)
        value['activities'] = ['the pharmacy']
        value['journey']['stops'][0]['source'] = 'the pharmacy'
        self.assertFalse(offline.article_projection(case, Interpretation.model_validate(value))[1])

    def test_repeated_occurrences_and_optionality_remain_distinct(self):
        case = fixture('Visit the museum, then coffee, then the museum.', ['museum', 'coffee', 'museum'])
        value = reference_wire(case)
        value['activities'] = ['the museum', 'coffee', 'the museum']
        for s, p in zip(value['journey']['stops'], value['activities']): s['source'] = p
        raw = Interpretation.model_validate(value)
        changes = offline.article_projection(case, raw)[1]
        self.assertEqual([x['occurrence'] for x in changes], [0, 2])
        self.assertLess(changes[0]['actualSpan'][1], changes[1]['actualSpan'][0])
        raw.journey.stops.pop(); raw.activities.pop()
        self.assertFalse(offline.article_projection(case, raw)[1])
        raw = Interpretation.model_validate(value); raw.journey.stops[0].requirement = 'optional'
        self.assertNotIn(0, [x['occurrence'] for x in offline.article_projection(case, raw)[1]])

    def test_original_bad_edge_stays_rejected_despite_article_equivalence(self):
        case = next(c for c in e.corpus()['cases'] if c['id'] == 'journey-07')
        value = reference_wire(case); value['activities'] = ['the pharmacy', 'the supermarket']
        for stop, source in zip(value['journey']['stops'], value['activities']): stop['source'] = source
        value['journey']['order'][0]['source'] = 'first, then'
        scored = offline.score(case, json.dumps(value))
        self.assertTrue(scored['structuredValid']); self.assertFalse(scored['validatedAccepted'])
        self.assertTrue(scored['automatedChecks']['activities'])
        self.assertIn('trustedDisposition', scored['referenceFailures'])

    def test_null_journey_is_not_valid_strict_wire_even_if_local_parser_allows_it(self):
        from backend.test_cloud_model52 import output
        for id in ('journey-01', 'ordinary-dinner'):
            case = next(c for c in e.corpus()['cases'] if c['id'] == id)
            value = json.loads(output(e.corpus()['cases'][0])); value['journey'] = None
            if id == 'ordinary-dinner':
                value.update(activities=['dinner', 'drinks'], location='Hyderabad')
            scored = offline.score(case, json.dumps(value))
            self.assertFalse(scored['structuredValid']); self.assertFalse(scored['validatedAccepted'])
            self.assertEqual(scored['wireContractFailures'], ['$.journey: non-null object required'])

    def test_existing_provenance_deadline_return_and_optional_guards(self):
        changes = [('journey-01', lambda v: v['journey']['stops'][0].update(evidence='drinks')),
            ('journey-01', lambda v: v['journey']['stops'][0].update(evidence='Eiffel Tower')),
            ('journey-06', lambda v: v['journey']['stops'][1].update(requirement='required')),
            ('journey-06', lambda v: v['journey']['stops'][1].update(evidence='')),
            ('journey-10', lambda v: v['journey'].update(endpoint=None)),
            ('journey-12', lambda v: v['journey']['total_duration'].update(relation='under')),
            ('journey-14', lambda v: v['journey'].update(deadline=None)),
            ('journey-01', lambda v: v['journey']['stops'].pop())]
        for id, change in changes:
            case = next(c for c in e.corpus()['cases'] if c['id'] == id)
            value = reference_wire(case); change(value)
            self.assertTrue(offline.score(case, json.dumps(value))['automatedFailures'])


class OrderingContractTests(unittest.TestCase):
    def test_cue_only_wrong_direction_and_list_order_are_not_successes(self):
        case = fixture('Visit the pharmacy before the bank.', ['pharmacy', 'bank'],
            order=[(0, 1, 'pharmacy before the bank')])
        good = reference_wire(case)
        self.assertIsNone(validate_journey(case['text'], Interpretation.model_validate(good))[0])
        for edge in [{'before': 0, 'after': 1, 'source': 'before'},
                     {'before': 1, 'after': 0, 'source': 'pharmacy before the bank'}]:
            bad = copy.deepcopy(good); bad['journey']['order'] = [edge]
            self.assertEqual(validate_journey(case['text'], Interpretation.model_validate(bad)), (REPHRASE, True))
        unordered = fixture('Coffee and museum.', ['Coffee', 'museum'])
        bad = reference_wire(unordered); bad['journey'].update(ordering='constrained',
            order=[{'before': 0, 'after': 1, 'source': 'Coffee and museum'}])
        with reference(unordered):
            self.assertIn('journeySemantics', offline.score(unordered, json.dumps(bad))['automatedFailures'])

    def test_first_then_reverse_and_repeated_wrong_edge_caught_by_comparator(self):
        for case in [fixture('Coffee first, then museum.', ['Coffee', 'museum'], order=[(0, 1, 'Coffee first, then museum')]),
                fixture('coffee then museum then coffee.', ['coffee', 'museum', 'coffee'],
                    order=[(0, 1, 'coffee then museum'), (1, 2, 'museum then coffee')])]:
            bad = reference_wire(case)
            bad['journey']['order'][0].update(before=1, after=0)
            with reference(case):
                self.assertIn('journeySemantics', offline.score(case, json.dumps(bad))['automatedFailures'])

    def test_partial_order_long_quote_and_duplicate_name_are_not_implicit_chain(self):
        case = fixture('coffee before museum; the museum visit includes a long conversation; bookstore is flexible.',
            ['coffee', 'museum', 'bookstore'], order=[(0, 1, 'coffee before museum')])
        good = reference_wire(case)
        with reference(case):
            self.assertFalse(offline.score(case, json.dumps(good))['automatedFailures'])
            bad = copy.deepcopy(good); bad['journey']['order'].append({'before': 1, 'after': 2,
                'source': 'museum visit includes a long conversation; bookstore'})
            self.assertIn('journeySemantics', offline.score(case, json.dumps(bad))['automatedFailures'])
        # Equal name strings do not identify which occurrence an edge binds.
        duplicate = fixture('Visit Acme, then coffee, then Acme.', ['Acme', 'coffee', 'Acme'],
            kinds={0: 'named_place', 2: 'named_place'}, order=[(0, 1, 'Acme, then coffee'), (1, 2, 'coffee, then Acme')])
        bad = reference_wire(duplicate); bad['journey']['order'][1].update(before=0, after=2)
        with reference(duplicate):
            self.assertTrue(offline.score(duplicate, json.dumps(bad))['automatedFailures'])

    def test_long_relationship_quote_and_overlapping_activity_words(self):
        text = 'Visit the museum, which has a rather long description about the exterior of the building, then get coffee.'
        case = fixture(text, ['museum', 'coffee'], order=[(0, 1, text)])
        good = reference_wire(case)
        self.assertIsNone(validate_journey(text, Interpretation.model_validate(good))[0])
        with reference(case):
            self.assertFalse(offline.score(case, json.dumps(good))['automatedFailures'])
        # Sharing the coffee token/category does not collapse coffee-shop and
        # later coffee occurrences or turn their evidence into interchangeable spans.
        case = fixture('Visit the coffee shop before coffee.', ['coffee shop', 'coffee'],
            order=[(0, 1, 'coffee shop before coffee')])
        bad = reference_wire(case); bad['journey']['stops'][1]['evidence'] = 'the coffee shop'
        with reference(case):
            scored = offline.score(case, json.dumps(bad))
        self.assertIn('sourceEvidenceAttachment', scored['automatedFailures'])


class ProposalTests(unittest.TestCase):
    def test_all_19_examples_and_active_configuration_unchanged(self):
        self.assertEqual(len(e.compact_examples()[0]), 19)
        self.assertEqual(proposal.messages('synthetic')[1:], e.messages('synthetic')[1:])
        self.assertEqual(proposal.messages('synthetic')[0]['content'], e.SYSTEM_PROMPT + proposal.ADDITION)
        self.assertEqual(e.digest(e.metadata()), '1c2352a7ec2b0bf826567de22b36ff2265bcd957e979d5b307cface7b5e0ee4e')
        for provider in e.CANDIDATES:
            proposed = proposal.payload(provider, 'synthetic')
            original = e.Adapter(provider, None).payload('synthetic')
            if provider == 'openai': proposed['input'] = original['input']
            elif provider == 'anthropic': proposed['system'] = original['system']
            else: proposed['systemInstruction'] = original['systemInstruction']
            self.assertEqual(proposed, original)
        stats = proposal.schema_stats(e.wire_schema('anthropic'))
        self.assertEqual((stats['unionNodes'], stats['optionalProperties']), (15, 0))

    def test_google_projection_preserves_structure_and_canonical_limits(self):
        original = e.wire_schema('google'); proposed = proposal.google_array_projection()
        def facts(node):
            if isinstance(node, dict):
                return {k: facts(v) for k, v in node.items() if k not in ('minItems', 'maxItems', 'description')}
            if isinstance(node, list): return [facts(x) for x in node]
            return node
        self.assertEqual(facts(original), facts(proposed))
        self.assertTrue(proposal.schema_stats(original)['maxArrayBounds'])
        self.assertFalse(proposal.schema_stats(proposed)['maxArrayBounds'])
        # Wire candidate never permits an oversized result through canonical parsing.
        case = e.corpus()['cases'][0]; value = reference_wire(case)
        value['journey']['stops'] *= 17
        self.assertFalse(offline.score(case, json.dumps(value))['structuredValid'])

    def test_separate_holdouts_accept_good_reject_bad_edges_without_prompt_tuning(self):
        data = json.loads(Path('docs/task52-offline-holdouts.json').read_text())
        self.assertFalse(data['usedForPromptTuning'])
        corpus_texts = {c['text'] for c in e.corpus()['cases']}
        for item in data['cases']:
            with self.subTest(source=item['text']):
                self.assertNotIn(item['text'], corpus_texts)
                self.assertNotIn(item['text'], json.dumps(proposal.messages('')))
                case = fixture(item['text'], item['phrases'], order=item['order'],
                    kinds={int(k): v for k, v in item.get('kinds', {}).items()})
                good = reference_wire(case)
                with reference(case):
                    self.assertFalse(offline.score(case, json.dumps(good))['automatedFailures'])
                    for change in [{'source': 'before'}, {'before': 1, 'after': 0}]:
                        bad = copy.deepcopy(good)
                        bad['journey']['order'][0].update(change)
                        rejected = offline.score(case, json.dumps(bad))
                        self.assertTrue(not rejected['structuredValid'] or rejected.get('automatedFailures'))

    def test_rejected_output_and_unreviewed_rubric_cannot_count_as_extraction(self):
        case = e.corpus()['cases'][6]; value = reference_wire(case)
        value['journey']['order'][0]['source'] = 'first, then'
        record = {'caseId': case['id'], 'repetition': 1, 'configurationHash': e.digest(e.metadata()),
                  'scoring': offline.score(case, json.dumps(value))}
        review = e.review_template([record]); item = review['reviews'][0]
        item['outcome'] = 'correct_extraction'
        item['fields'] = {k: {'applicable': True, 'correct': True} for k in e.SEMANTIC_FIELDS}
        with self.assertRaisesRegex(ValueError, 'Rejected output'):
            e.adjudicate([record], review)
        item['outcome'] = 'safe_failure'; item['fields']['ordering']['correct'] = None
        with self.assertRaisesRegex(ValueError, 'Every field'):
            e.adjudicate([record], review)


if __name__ == '__main__': unittest.main()
