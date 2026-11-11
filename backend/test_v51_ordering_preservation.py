"""Reviewed synthetic requests through the development interpretation boundary."""
from copy import deepcopy
from datetime import datetime, timezone
from dataclasses import replace
import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from backend.ai import Interpretation
from backend.interpretation import InterpretationInput
from backend.test_task52_v51_evaluator import fake_responses
from scripts.task52_ordering_preservation_dev import interpret_for_development
from backend.validation_phases import validate_legacy
from scripts.task52_v51_eval_identity import plan

NOW = datetime(2026, 11, 5, 15, tzinfo=timezone.utc)


class OrderingPreservationTests(TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.send', side_effect=AssertionError('No provider requests')))
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('No outbound connections')))
        self.slots = plan()['slots']
        self.payloads = [json.loads(r['output'][0]['content'][0]['text']) for r in fake_responses()]

    def interpret(self, index, payload=None, *, enabled=True, **kwargs):
        slot = self.slots[index]
        value = InterpretationInput(text=slot['source'], **kwargs)
        extraction = self.payloads[index] if payload is None else payload
        with patch('backend.interpretation.create_provider', side_effect=AssertionError('No model factory')):
            return interpret_for_development(value, extraction=extraction, now=NOW, preserve_order=enabled)

    def test_optional_coffee_retains_source_owned_order(self):
        result = self.interpret(3)
        self.assertEqual(result.executionStatus, 'advanced_unavailable')
        self.assertEqual([(e.before, e.after) for e in result.interpretation.journey.order], [(0, 1)])

    def test_off_matches_original_and_production_cannot_select_profile(self):
        from backend.main import interpret_outing
        value = InterpretationInput(text=self.slots[3]['source'])
        provider = SimpleNamespace(interpret=Mock(return_value=self.payloads[3]))
        expected = validate_legacy(value, provider, now=NOW).result
        self.assertEqual(self.interpret(3, enabled=False), expected)
        self.assertEqual(interpret_for_development(value, extraction=self.payloads[3], now=NOW), expected)
        self.assertEqual(expected.interpretation.journey.order, [])
        # The actual API boundary still uses the legacy adapter.
        with patch('backend.interpretation.create_provider', return_value=provider):
            with patch('backend.advanced_planning.enabled', return_value=False):
                actual = interpret_outing(value)
        self.assertEqual(actual.interpretation, expected.interpretation)
        self.assertEqual(actual.executionStatus, expected.executionStatus)
        self.assertIsNone(actual.advancedToken)
        with self.assertRaises(ValueError):
            InterpretationInput.model_validate({'text': value.text, 'preserve_order': True})

    def test_five_reviewed_extractions_preserve_graph_and_non_order_requirements(self):
        for index, edges in enumerate(([(0, 1), (1, 2)], [(0, 1)], [(0, 1)], [(0, 1)], [])):
            with self.subTest(case=self.slots[index]['slot']):
                original = deepcopy(self.payloads[index])
                result = self.interpret(index)
                self.assertEqual(self.payloads[index], original)
                self.assertEqual(result.interpretation, Interpretation.model_validate(original))
                self.assertEqual([(e.before, e.after) for e in result.interpretation.journey.order], edges)
                self.assertEqual(result.executionStatus,
                                 'clarification_required' if index == 4 else 'advanced_unavailable')
                self.assertIsNone(result.request)
                self.assertIsNone(result.advancedToken)
                if index == 4:
                    self.assertIsNone(result.pending)
                else:
                    self.assertEqual(result.pending.interpretation, result.interpretation)

    def test_incorrect_raw_extractions_never_become_handoffs(self):
        probes = [
            (3, lambda v: v['journey'].update(order=[], ordering='unspecified')),
            (3, lambda v: v['journey']['order'][0].update(before=1, after=0)),
            (2, lambda v: v['journey']['order'].append(dict(before=1, after=2, source=self.slots[2]['source']))),
            (3, lambda v: v['journey']['stops'][1].update(requirement='required', evidence='')),
            (2, lambda v: v['journey']['stops'][2].update(requirement='optional', evidence='whenever convenient')),
            (0, lambda v: (v['activities'].pop(), v['journey']['stops'].pop(), v['journey']['order'].pop())),
            (1, lambda v: v['journey']['stops'][0].update(kind='activity')),
            (1, lambda v: (v['activities'].__setitem__(0, 'Another College'),
                           v['journey']['stops'][0].update(source='Another College'))),
            (3, lambda v: v['journey'].update(endpoint={'kind':'origin', 'source':'coffee'})),
            (0, lambda v: v['journey'].update(total_duration=None)),
            (0, lambda v: v['journey'].update(endpoint=None)),
            (0, lambda v: v['journey']['endpoint'].update(source='return to the starting point and office')),
            (4, lambda v: v['journey'].update(clarification='', ordering='flexible')),
            (3, lambda v: v['journey']['order'][0].update(source='and maybe')),
            (3, lambda v: v['journey']['order'].append(deepcopy(v['journey']['order'][0]))),
            (3, lambda v: v['journey']['stops'][1].update(evidence='')),
            (3, lambda v: v.update(location='Invented City')),
            (3, lambda v: v.update(people=2)),
        ]
        for number, (index, mutate) in enumerate(probes):
            with self.subTest(probe=number):
                payload = deepcopy(self.payloads[index])
                mutate(payload)
                result = self.interpret(index, payload)
                self.assertEqual(result.executionStatus, 'clarification_required')
                self.assertIsNone(result.request)
                self.assertIsNone(result.advancedToken)
                self.assertIsNone(result.pending)
        malformed = self.payloads[3] | {'inventedField': True}
        with self.assertRaises(ValueError):
            self.interpret(3, malformed)

    def test_unresolved_occurrences_and_unexpected_mutations_block(self):
        def changed(*args, **kwargs):
            d = validate_legacy(*args, **kwargs)
            if mode == 'mapping':
                return replace(d, preparation=replace(d.preparation, mapping=()))
            if mode == 'context':
                d.result.context.originText = 'unexpected origin'
            elif mode == 'journey':
                d.result.interpretation.journey.stops[0].requirement = 'optional'
            return d

        for mode in ('mapping', 'context', 'journey'):
            with self.subTest(mode=mode):
                with patch('scripts.task52_ordering_preservation_dev.validate_legacy', side_effect=changed):
                    result = self.interpret(3)
                self.assertEqual(result.executionStatus, 'clarification_required')
                self.assertIsNone(result.pending)

    def test_pending_and_manual_overrides_cannot_enter_gated_path(self):
        pending = self.interpret(3, enabled=False).pending
        for value in (InterpretationInput(text=pending.text, pending=pending),
                      InterpretationInput(text=pending.text, preferences={'location':'New York'})):
            with self.assertRaises(ValueError):
                interpret_for_development(value, extraction=self.payloads[3], now=NOW, preserve_order=True)

    def test_existing_advanced_sessions_apply_order_and_refuse_contradiction(self):
        from backend.advanced_planning import AdvancedInput, Sessions
        from backend.provider_budget import ProviderBudget, ProviderSettings
        from backend.test_advanced_planning import IntegrationTests
        from backend.test_advanced_routing import start, record

        fixture = IntegrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.records += [record('Synthetic_coffee_two', 'Synthetic second coffee cafe', ['cafe']),
                            record('Synthetic_museum', 'Synthetic museum', ['museum'])]
        # Resolution independently verifies the requested city against venue evidence.
        fixture.records += [{**r,
            'formattedAddress': r['formattedAddress'].replace('New York', 'Jersey City'),
            'addressComponents': [{'longText':'Jersey City','types':['locality']}],
        } for r in fixture.records if r['id'] != 'Synthetic_college']
        search = fixture.search

        def city_search(body, **kwargs):
            response = search(body, **kwargs)
            locality = 'Jersey City' if 'jersey city' in body['textQuery'].casefold() else 'New York'
            records = [r for r in response['places'] if r['addressComponents'][0]['longText'] == locality]
            if 'museum' in body['textQuery'].casefold():
                records = [r for r in fixture.records if 'museum' in r['types']
                           and r['addressComponents'][0]['longText'] == locality]
            return {'places': records}

        self.enterContext(patch('backend.places_transport.text_search', side_effect=city_search))
        sessions = Sessions()
        for index, allowed in enumerate(({(0, 1, 2)}, {(0, 1)}, {(0, 1, 2), (0, 2, 1), (2, 0, 1)}, {(0,), (0, 1)})):
            with self.subTest(case=self.slots[index]['slot']):
                result = self.interpret(index)
                value = InterpretationInput(text=self.slots[index]['source'])
                token = sessions.create(value.text, result, ProviderBudget(ProviderSettings()), value.preferences)
                self.assertIsNotNone(token)
                args = {'startingLocation': start()} if index == 0 else {}
                if index in (1, 3):
                    args.update(destination='New York', date='2026-11-07')
                output = sessions.run(AdvancedInput(token=token, **args))
                self.assertEqual(output.status, 'results', (output.message, output.questions))
                orders = {tuple(s.occurrence for s in o.stops) for o in output.options}
                session = sessions.items[token]
                self.assertEqual(session.journey, result.interpretation.journey)
                if index == 2:
                    # The display ranks a bounded subset of the valid candidates.
                    routed = {tuple(v.occurrence for v in c.visits) for c in session.candidates.values()}
                    self.assertEqual(routed, allowed)
                    self.assertTrue(orders <= allowed)
                else:
                    self.assertEqual(orders, allowed)
                if index == 0:
                    self.assertTrue(all(o.ending == 'origin' and o.legs[-1].role == 'return_to_origin' for o in output.options))
                    self.assertTrue(all(o.durationState == 'unverified' for o in output.options))
                if index == 1:
                    self.assertTrue(all(o.stops[0].placeId == 'Synthetic_college' for o in output.options))
                if index == 3:
                    self._check_saved_order(output, allowed)

        counts = (len(fixture.searches), len(fixture.calls))
        value = InterpretationInput(text=self.slots[4]['source'])
        self.assertIsNone(sessions.create(value.text, self.interpret(4), ProviderBudget(ProviderSettings()), value.preferences))
        self.assertEqual((len(fixture.searches), len(fixture.calls)), counts)

        fixture.values.update({('DRIVE', 'Synthetic_pharmacy', 'Synthetic_bank'): 'unreachable',
                               ('DRIVE', 'Synthetic_pharmacy', 'Synthetic_coffee'): 'unreachable',
                               ('DRIVE', 'Synthetic_pharmacy', 'Synthetic_coffee_two'): 'unreachable'})
        value = InterpretationInput(text=self.slots[2]['source'])
        token = sessions.create(value.text, self.interpret(2), ProviderBudget(ProviderSettings()), value.preferences)
        output = sessions.run(AdvancedInput(token=token))
        self.assertEqual(output.options, [])
        self.assertNotEqual(output.status, 'results')

    def _check_saved_order(self, output, expected_orders):
        from backend.saved_plans import (receipts, read_document, SaveRequest, SavedDocument,
                                         write_document)

        ids = [o.id for o in output.options]
        # The current receipt saves only the selected advanced alternative.
        observed = set()
        for selected in ids:
            document = receipts.select(SaveRequest(receipt=output.saveReceipt, accessToken=output.saveAccessToken,
                                                   candidateIds=ids, selectedId=selected))
            # Exercise the production write/read mapping without a connection.
            tables = {}
            writer = Mock()
            writer.execute.return_value.fetchone.return_value = None
            with patch('backend.saved_plans.insert',
                       side_effect=lambda _connection, table, row: tables.setdefault(table, []).append(row)):
                write_document(writer, document, output.saveAccessToken)
            plan = tables['plans'][0] | {'access_expires_at': NOW}
            constraint = tables['plan_constraints'][0].copy()
            for field in ('activity_intents', 'preferences'):
                constraint[field] = constraint[field].obj
            metadata = {m['stop_id']: m for m in tables['source_metadata']}
            stops = [r | metadata[r['id']] for r in tables['itinerary_stops']]
            reader = Mock()
            reader.execute.side_effect = [
                Mock(**{'fetchone.return_value': plan}),
                Mock(**{'fetchone.return_value': constraint}),
                Mock(**{'fetchall.return_value': tables['generated_itineraries']}),
                Mock(**{'fetchall.return_value': stops}),
            ]
            saved = read_document(reader, output.saveAccessToken)
            reloaded = SavedDocument.model_validate({k: saved[k] for k in SavedDocument.model_fields})
            self.assertEqual(len(reloaded.itineraries), 1)
            option = reloaded.itineraries[0].advanced
            observed.add(tuple(option.occurrenceOrder))
            self.assertEqual([(e.before, e.after) for e in option.journey.order], [(0, 1)])
            self.assertEqual(option.journey.stops[1].requirement, 'optional')
            if len(option.occurrenceOrder) == 2:
                tampered = option.model_dump()
        self.assertEqual(observed, expected_orders)
        tampered['occurrenceOrder'] = [1, 0]
        from backend.saved_advanced import AdvancedSaved
        with self.assertRaisesRegex(ValueError, 'Saved precedence violation'):
            AdvancedSaved.model_validate(tampered)

    def test_planner_preserves_required_order_through_skipped_optional_middle(self):
        from backend.advanced_routing import _shortlist
        from backend.journey import Journey
        from scripts.task52_ordering_v51 import inspect_order

        text = 'Coffee, maybe museum, dinner.'
        journey = Journey(stops=[{'source':'Coffee'},
                                 {'source':'museum','requirement':'optional','evidence':'maybe museum'},
                                 {'source':'dinner'}],
                          order=[{'before':0,'after':1,'source':text},
                                 {'before':1,'after':2,'source':text}])
        raw = Interpretation(activities=['Coffee','museum','dinner'], journey=journey,
                             budget_per_person=None, date=None, location=None, preferences=[])
        proof = inspect_order(text, raw)
        self.assertEqual(proof['mandatoryRequiredVisitClosure'], [[0, 2]])
        groups = [SimpleNamespace(occurrence=i, requested=s, status='candidates',
                                  candidates=[SimpleNamespace(place_id=f'fictional-{i}')])
                  for i, s in enumerate(journey.stops)]
        with patch('backend.advanced_routing._gap', return_value=0):
            paths = _shortlist(SimpleNamespace(journey=journey, stops=groups), None, None)
        self.assertEqual({tuple(i for i, _ in path) for path in paths}, {(0, 1, 2), (0, 2)})

    def test_gated_handoff_cannot_bypass_required_admission(self):
        from backend.advanced_planning import Sessions
        from backend.planning_admission import require_foundation_for_test
        from backend.provider_budget import ProviderBudget, ProviderLimitError, ProviderSettings

        value = InterpretationInput(text=self.slots[3]['source'])
        result = self.interpret(3)
        sessions = Sessions()
        with patch('backend.advanced_planning.enabled', return_value=True), require_foundation_for_test():
            with self.assertRaises(ProviderLimitError):
                sessions.create(value.text, result, ProviderBudget(ProviderSettings()), value.preferences)
        self.assertFalse(sessions.items)


class GeneralizedOrderingTests(TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.send', side_effect=AssertionError('No provider requests')))
        self.enterContext(patch('socket.socket.connect', side_effect=AssertionError('No outbound connections')))
        self.enterContext(patch('backend.interpretation.create_provider', side_effect=AssertionError('No model factory')))

    def validate(self, text, stops, edges, *, ordering_mode=None, **fields):
        from scripts.task52_ordering_preservation_dev import validate_for_development

        journey_fields = fields.pop('journey_fields', {})
        entries = [stop if isinstance(stop, dict) else {'source': stop} for stop in stops]
        extraction = {
            'activities': [entry['source'] for entry in entries],
            'date': None, 'location': None, 'budget_per_person': None, 'preferences': [],
            'journey': {'stops': entries, 'ordering': ordering_mode or ('constrained' if edges else 'unspecified'),
                        'order': [{'before': a, 'after': b, 'source': quote} for a, b, quote in edges],
                        **journey_fields},
            **fields,
        }
        original = deepcopy(extraction)
        validation = validate_for_development(InterpretationInput(text=text), extraction=extraction, now=NOW)
        self.assertEqual(extraction, original)
        self.assertEqual(Interpretation.model_validate_json(validation.raw_snapshot), Interpretation.model_validate(original))
        return validation

    def test_independent_supported_phrases_reach_typed_handoff(self):
        from backend.interpretation import InterpretationResult

        cases = [
            ('Tea, then bowling, then dinner.', ['Tea','bowling','dinner'],
             [(0,1,'Tea, then bowling'), (1,2,'bowling, then dinner')], {}),
            ('Arcade, bowling, dinner, movie.', ['Arcade','bowling','dinner','movie'],
             [(0,1,'Arcade, bowling'), (1,2,'bowling, dinner'), (2,3,'dinner, movie')], {}),
            ('Maybe skating, then lunch.', [{'source':'skating','requirement':'optional','evidence':'Maybe skating'},'lunch'],
             [(0,1,'skating, then lunch')], {}),
            ('Museum, maybe bowling, dinner.', ['Museum',{'source':'bowling','requirement':'optional','evidence':'maybe bowling'},'dinner'],
             [(0,1,'Museum, maybe bowling'), (1,2,'bowling, dinner')], {}),
            ('Bookstore and maybe tea.', ['Bookstore',{'source':'tea','requirement':'optional','evidence':'maybe tea'}],
             [(0,1,'Bookstore and maybe tea')], {}),
            ('Pharmacy before bank, tea whenever convenient.', ['Pharmacy','bank','tea'],
             [(0,1,'Pharmacy before bank')], {}),
            ('Arcade whenever convenient, bowling, dinner.', ['Arcade','bowling','dinner'],
             [(1,2,'bowling, dinner')], {}),
            ('Museum after dinner.', ['Museum','dinner'], [(1,0,'Museum after dinner')], {}),
            ('Tea, museum, tea.', ['Tea','museum','tea'], [(0,1,'Tea, museum'),(1,2,'museum, tea')], {}),
            ('Visit Harbor Art Museum, then pizza.', [{'source':'Harbor Art Museum','kind':'named_place'},'pizza'],
             [(0,1,'Harbor Art Museum, then pizza')], {}),
            ('Arcade aur bowling in Hyderabad.', ['Arcade','bowling'], [(0,1,'Arcade aur bowling')], {'location':'Hyderabad'}),
            ('Tea and bowling, in any order.', ['Tea','bowling'], [], {'ordering_mode':'flexible'}),
            ('Tea, dinner in New York on 2026-11-07, on foot.', ['Tea','dinner'],
             [(0,1,'Tea, dinner')], {'location':'New York'}),
            ('Tea, pizza in New York tomorrow, finish at Maple Community Library.', ['Tea','pizza'],
             [(0,1,'Tea, pizza')], {'location':'New York','journey_fields':{
                 'endpoint': {'kind':'named_place','source':'finish at Maple Community Library'}}}),
        ]
        for text, stops, edges, fields in cases:
            with self.subTest(text=text):
                check = self.validate(text, stops, edges, **fields)
                result = check.result
                self.assertEqual(check.disposition, 'source_order_preserved')
                self.assertEqual(result.executionStatus, 'advanced_unavailable')
                self.assertEqual([(e.before,e.after,e.source) for e in result.interpretation.journey.order], edges)
                self.assertIsNone(result.advancedToken)
                self.assertIsNone(result.request)
                self.assertEqual(result.pending.interpretation, result.interpretation)
                if text.startswith('Arcade, bowling'):
                    old = InterpretationResult.model_validate_json(check.legacy_snapshot)
                    self.assertEqual(old.interpretation.journey.order, [])
                if 'on foot' in text:
                    self.assertEqual(str(result.context.date), '2026-11-07')
                    self.assertEqual(result.context.transport.value, 'walking')
                    self.assertEqual(result.context.destination, 'New York')
                if 'finish at' in text:
                    self.assertEqual(result.interpretation.journey.endpoint.source, 'finish at Maple Community Library')

    def test_forward_graphs_fail_when_source_or_non_order_constraints_are_unproved(self):
        cases = [
            ('Meeting Notes, tea.', [{'source':'Meeting Notes','kind':'named_place'},'tea'],
             [(0,1,'Meeting Notes, tea')], {}),
            ('Tea versus bowling.', ['Tea','bowling'], [(0,1,'Tea versus bowling')], {}),
            ('Tea as well as bowling.', ['Tea','bowling'], [(0,1,'Tea as well as bowling')], {}),
            ('Tea and bowling, in any order.', ['Tea','bowling'], [(0,1,'Tea and bowling')], {}),
            ('Tea, bowling, tea.', ['Tea','bowling'], [(0,1,'Tea, bowling')], {}),
            ('Tea, bowling, tea.', ['Tea','bowling','tea'], [(0,1,'Tea, bowling'),(1,2,'Tea, bowling')], {}),
            ('Bowling before dinner, library.', ['Bowling','dinner','library'], [(0,1,'Bowling before dinner')], {}),
            ('Bowling before dinner; if raining skip it.', ['Bowling','dinner'], [(0,1,'Bowling before dinner')], {}),
            ('Bowling before dinner; bring umbrellas.', ['Bowling','dinner'], [(0,1,'Bowling before dinner')], {}),
            ('Bowling before dinner, but dinner before bowling.', ['Bowling','dinner'],
             [(0,1,'Bowling before dinner')], {}),
            ('Bowling before dinner, tea whenever convenient.', ['Bowling','dinner','tea'],
             [(0,1,'Bowling before dinner'),(1,2,'dinner, tea whenever convenient')], {}),
            ('Tea, bowling, dinner.', ['Tea','bowling','dinner'], [(0,1,'Tea, bowling')], {}),
            ('Tea, bowling, dinner.', ['Tea','bowling','dinner'], [(1,0,'Tea, bowling'),(1,2,'bowling, dinner')], {}),
            ('Tea, bowling, dinner.', ['Tea, bowling','dinner'], [(0,1,'Tea, bowling, dinner')], {}),
            ('Tea aurora bowling.', ['Tea','bowling'], [(0,1,'Tea aurora bowling')], {}),
            ('Tea aur bowling.', ['Tea','bowling'], [(0,1,'Tea and bowling')], {}),
            ('Tea, bowling in New York and Queens.', ['Tea','bowling'],
             [(0,1,'Tea, bowling')], {'location':'New York and Queens'}),
            ('Tea, bowling in New York tomorrow.', ['Tea','bowling'],
             [(0,1,'Tea, bowling')], {'location':'New York','date_expressions':['today']}),
            ('Tea, bowling tomorrow.', ['Tea','bowling'], [(0,1,'Tea, bowling')], {}),
            ('Tea, bowling under $25.', ['Tea','bowling'],
             [(0,1,'Tea, bowling')], {'budget_per_person':25, 'currency':'USD'}),
            ('Tea, bowling by bike.', ['Tea','bowling'], [(0,1,'Tea, bowling')], {}),
            ('Tea, bowling, return to where I started within 45 minutes.', ['Tea','bowling'],
             [(0,1,'Tea, bowling')], {'journey_fields':{'endpoint':{'kind':'origin','source':'return to where I started'}}}),
            ('Tea, bowling.', ['Tea','bowling'], [(0,1,'Tea, bowling')], {'transport':'walking'}),
            ('Tea whenever convenient, then dinner.', ['Tea','dinner'], [], {'ordering_mode':'flexible'}),
        ]
        for text, stops, edges, fields in cases:
            with self.subTest(text=text):
                check = self.validate(text, stops, edges, **fields)
                self.assertNotEqual(check.disposition, 'source_order_preserved')
                self.assertEqual(check.result.executionStatus, 'clarification_required')
                self.assertIsNone(check.result.request)
                self.assertIsNone(check.result.pending)
                self.assertIsNone(check.result.advancedToken)

    def test_new_return_and_walking_reach_the_planner_with_real_timing_contract(self):
        from backend.advanced_planning import AdvancedInput, Sessions
        from backend.provider_budget import ProviderBudget, ProviderSettings
        from backend.test_advanced_planning import IntegrationTests
        from backend.test_advanced_routing import record, start

        fixture = IntegrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.records.append(record('Synthetic_dinner','Synthetic dinner',['restaurant']))
        text = 'Tea, dinner in New York tomorrow, on foot, return to where I started within 45 minutes.'
        checked = self.validate(text, ['Tea','dinner'], [(0,1,'Tea, dinner')], location='New York',
                                journey_fields={'endpoint':{'kind':'origin','source':'return to where I started'},
                                                'total_duration':{'minutes':45,'relation':'maximum','source':'within 45 minutes'}})
        result = checked.result
        self.assertEqual(checked.disposition, 'source_order_preserved')
        sessions = Sessions()
        token = sessions.create(text, result, ProviderBudget(ProviderSettings()), InterpretationInput(text=text).preferences)
        self.assertIsNotNone(token)
        # Missing origin is checked before any synthetic search.
        self.assertEqual(sessions.run(AdvancedInput(token=token)).status, 'clarification')
        self.assertFalse(fixture.searches)
        inputs = {'token': token, 'startingLocation': start()}
        unverified = sessions.run(AdvancedInput(**inputs))
        self.assertEqual(unverified.status, 'results')
        self.assertEqual(unverified.options[0].durationState, 'unverified')
        self.assertEqual([s.occurrence for s in unverified.options[0].stops], [0,1])
        self.assertEqual(unverified.options[0].ending, 'origin')
        self.assertTrue(all(leg.mode == 'walk' for leg in unverified.options[0].legs))
        with_dwell = sessions.run(AdvancedInput(**inputs, edits={'dwell':[
            {'occurrence':0,'minutes':5,'relation':'exact'}, {'occurrence':1,'minutes':10,'relation':'exact'}]}))
        self.assertEqual(with_dwell.options[0].durationState, 'feasible')
        self.assertEqual(with_dwell.options[0].elapsedUpperSeconds, 2700)
        over = sessions.run(AdvancedInput(**inputs, dwell={'occurrence':1,'minutes':11,'relation':'exact'}))
        self.assertEqual(over.options, [])

        fixture.records.append(record('Synthetic_library','Maple Community Library',['library']))
        terminal = 'Tea, dinner in New York tomorrow, finish at Maple Community Library.'
        checked = self.validate(terminal, ['Tea','dinner'], [(0,1,'Tea, dinner')], location='New York',
                                journey_fields={'endpoint':{
                                    'kind':'named_place','source':'finish at Maple Community Library'}})
        self.assertEqual(checked.disposition, 'source_order_preserved')
        token = sessions.create(terminal, checked.result, ProviderBudget(ProviderSettings()),
                                InterpretationInput(text=terminal).preferences)
        self.assertIsNotNone(token)
        final = sessions.run(AdvancedInput(token=token))
        self.assertEqual(final.status, 'results')
        self.assertEqual(final.options[0].ending, 'named_destination')
        self.assertEqual(final.options[0].legs[-1].role, 'final_destination')
