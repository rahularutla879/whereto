"""Task 42 synthetic evidence only. Network is forbidden throughout this suite."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from itertools import permutations
import os
import unittest
from unittest.mock import patch

from backend.models import ActivityType, OutingRequest
from backend.places import DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea, parse_response
from backend.provider_budget import ProviderBudget, ProviderLimitError, ProviderSettings
from backend.ranking import recommend_plans
from backend.test_places import place, request
from backend.venue_normalization import normalize_google_place
from backend.venue_quality import RULES, assess_candidates, relevance

WHEN = datetime(2026, 10, 24, tzinfo=timezone.utc)


def venue(identity='a', activity='bowling', name='Harbor Bowling Lanes', **fields):
    raw = place()
    raw.update(id=identity, displayName={'text': name}, **fields)
    return normalize_google_place(raw, activity, observed_at=WHEN)


class QualityTests(unittest.TestCase):
    def setUp(self):
        guard = patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_duplicate_id_merges_despite_changed_name_and_address(self):
        a = venue()
        b = venue(name='Renamed Bowling Center', formattedAddress='124 Example St')
        result = assess_candidates([a, b, a])
        self.assertEqual(len(result.venues), 1)
        self.assertEqual(result.venues[0].facts.id, a.id)
        self.assertEqual(len(result.venues[0].sources), 3)
        self.assertEqual(result.diagnostics['duplicate_place_id'], 2)
        self.assertEqual(result.excluded_count, 2)

    def test_complementary_fields_and_source_credits_survive(self):
        a = venue(rating=4.1, attributions=[{'provider': 'Credit A'}],
                  regularOpeningHours={'weekdayDescriptions': ['Saturday hours unknown']})
        b = venue(rating=None, websiteUri='https://example.invalid/harbor', types=['bowling_alley'],
                  regularOpeningHours={'openNow': False}, attributions=[{'provider': 'Credit B'}])
        baseline = deepcopy([a.model_dump(), b.model_dump()])
        result = assess_candidates([a, b]).venues[0]
        self.assertEqual(result.facts.rating, 4.1)
        self.assertIsNotNone(result.facts.websiteUrl)
        self.assertEqual(result.facts.regularOpeningHours.weekdayDescriptions, ['Saturday hours unknown'])
        self.assertFalse(result.facts.regularOpeningHours.openNow)
        self.assertEqual({c.provider for c in result.facts.attributions}, {'Credit A', 'Credit B'})
        self.assertEqual(result.facts.evidence, 'provider_supplied')
        self.assertEqual([a.model_dump(), b.model_dump()], baseline)

    def test_identity_facts_merge_before_relevance_and_preserve_optional_fields(self):
        a = venue(name='Harbor Cinema', types=['movie_theater'], rating=4.2)
        b = venue(types=['bowling_alley'])
        result = assess_candidates([a, b]).venues[0]
        self.assertEqual(result.facts.rating, 4.2)
        self.assertEqual(result.relevance[ActivityType.bowling].status, 'strong')
        self.assertEqual(len(result.sources), 2)

    def test_original_provider_ids_are_preserved_or_rejected_never_trimmed(self):
        for identity in ('  original-google-id', 'original-google-id  '):
            raw = place()
            raw['id'] = identity
            with self.assertRaises(DiscoveryError):
                parse_response({'places': [raw]}, request().area, 3)
        raw = place()
        raw['id'] = 'Original_Case-Sensitive.ID'
        self.assertEqual(parse_response({'places': [raw]}, request().area, 3).candidates[0].provider_id, raw['id'])

    def test_newer_fields_win_with_correct_receipt_times(self):
        a = venue(rating=4.0, userRatingCount=0)
        b = normalize_google_place({'id': 'a', 'displayName': {'text': a.name}, 'rating': 3.0},
                                   'bowling', observed_at=WHEN+timedelta(days=1))
        for records in ([a, b], [b, a]):
            facts = assess_candidates(records).venues[0].facts
            self.assertEqual((facts.rating, facts.ratingCount), (3.0, 0))
            self.assertEqual(facts.observedAt['rating'], WHEN+timedelta(days=1))
            self.assertEqual(facts.observedAt['ratingCount'], WHEN)

    def test_union_facts_do_not_inherit_newer_receipt_for_older_evidence(self):
        a = venue(types=['bowling_alley'], attributions=[{'provider': 'Credit A'}])
        b = normalize_google_place({'id': 'a', 'displayName': {'text': a.name},
                                    'types': ['video_arcade'], 'attributions': [{'provider': 'Credit B'}]},
                                   'bowling', observed_at=WHEN+timedelta(days=1))
        facts = assess_candidates([a, b]).venues[0].facts
        self.assertEqual(facts.observedAt['providerTypes'], WHEN)
        self.assertEqual(facts.observedAt['attributions'], WHEN)
        a.observedAt.pop('providerTypes')
        self.assertNotIn('providerTypes', assess_candidates([a, b]).venues[0].facts.observedAt)

    def test_conflicting_nested_snapshots_never_invent_periods_or_prices(self):
        a = venue(priceRange={'startPrice': {'currencyCode': 'USD', 'units': '30'}},
                  regularOpeningHours={'periods': [{'open': {'day': 6, 'hour': 10, 'minute': 0}}]})
        b = venue(priceRange={'endPrice': {'currencyCode': 'EUR', 'units': '20'}},
                  regularOpeningHours={'periods': [{'open': {'day': 6, 'hour': 12, 'minute': 0}}]})
        result = assess_candidates([a, b]).venues[0]
        self.assertEqual(len(result.facts.regularOpeningHours.periods), 1)
        self.assertEqual(len(result.sources), 2)
        if result.facts.priceRange.start and result.facts.priceRange.end:
            self.assertEqual(result.facts.priceRange.start.currency, result.facts.priceRange.end.currency)

    def test_different_ids_need_all_corroboration_and_keep_original_ids(self):
        a = venue(websiteUri='https://example.invalid/venues/harbor', name='Hárbor Bowling Lanes')
        b = venue('b', name='Harbor Bowling Lanes', websiteUri='https://example.invalid/venues/harbor',
                  location={'latitude': 39.28001, 'longitude': -76.6}, rating=4.5)
        result = assess_candidates([b, a])
        self.assertEqual(len(result.venues), 1)
        group = result.venues[0]
        self.assertEqual(group.facts.id, 'a')
        self.assertEqual({v.id for v in group.sources}, {'a', 'b'})
        self.assertEqual(group.facts.rating, 4.5)
        self.assertEqual(result.diagnostics['corroborated_alias'], 1)

    def test_ambiguous_same_name_address_point_kept(self):
        self.assertEqual(len(assess_candidates([venue(), venue('b')]).venues), 2)
        for url in ('https://example.invalid/', 'https://example.invalid/locations'):
            self.assertEqual(len(assess_candidates([venue(websiteUri=url), venue('b', websiteUri=url)]).venues), 2)

    def test_distinct_businesses_units_brands_complexes_cinemas_food_courts(self):
        shared = {'websiteUri': 'https://example.invalid/complex/harbor'}
        cases = [
            (venue(**shared), venue('b', name='Other Bowling Lanes', **shared)),
            (venue(types=['bowling_alley'], **shared), venue('b', types=['video_arcade'], **shared)),
            (venue(primaryType='bowling_alley', **shared), venue('b', primaryType='restaurant', **shared)),
            (venue(**shared), venue('b', formattedAddress='123 Example St, Suite 2', **shared)),
            (venue(**shared), venue('b', location={'latitude': 39.281, 'longitude': -76.6}, **shared)),
            (venue(name='AMC Harbor Cinema', activity='movie'), venue('b', name='AMC Harbor Cinema', activity='movie')),
            (venue(name='Harbor Food Court', activity='food'), venue('b', name='Pizza Restaurant', activity='food')),
            (venue(name='Harbor Arcade', activity='arcade'), venue('b', name='Harbor Cinema', activity='movie')),
        ]
        for a, b in cases:
            with self.subTest(names=(a.name, b.name)):
                self.assertEqual(len(assess_candidates([a, b]).venues), 2)

    def test_aliases_do_not_chain_across_close_coordinates(self):
        records = [venue(i, websiteUri='https://example.invalid/harbor',
                         location={'latitude': 39.28 + delta, 'longitude': -76.6})
                   for i, delta in [('a', 0), ('b', .00007), ('c', .00014)]]
        for ordered in permutations(records):
            self.assertEqual(len(assess_candidates(list(ordered)).venues), 2)

    def test_multi_activity_single_identity_and_per_activity_evidence(self):
        result = assess_candidates([venue(types=['bowling_alley']),
                                    venue(activity='arcade', types=['video_arcade']),
                                    venue(activity='food', types=['restaurant'])])
        self.assertEqual(len(result.venues), 1)
        group = result.venues[0]
        self.assertEqual([a.value for a in group.activities], ['arcade', 'bowling', 'food'])
        self.assertTrue(all(v.status == 'strong' for v in group.relevance.values()))
        self.assertEqual(set(group.facts.providerTypes), {'bowling_alley', 'video_arcade', 'restaurant'})

    def test_all_29_categories_have_evidence_rules_and_accept_missing_types(self):
        self.assertEqual(set(RULES), {a.value for a in ActivityType})
        for activity in ActivityType:
            with self.subTest(activity=activity):
                no_types = venue(activity=activity, name='Unclassified Harbor Venue')
                self.assertEqual(relevance(no_types).status, 'uncertain')
                expected, _ = RULES[activity.value]
                if expected:
                    self.assertEqual(relevance(venue(activity=activity, name='Harbor Venue',
                                                    types=sorted(expected))).status, 'strong')
                wrong = venue(activity=activity, name='Harbor Dental Clinic', primaryType='dentist')
                self.assertEqual(assess_candidates([wrong]).venues, [])

    def test_name_only_examples_for_all_categories(self):
        names = ['Bowling Alley', 'Harbor Pub', 'Harbor Cinema', 'Harbor Restaurant', 'Harbor Coffee',
                 'Harbor Park', 'Harbor Art Gallery', 'Harbor Museum', 'Harbor Karaoke', 'Harbor Arcade',
                 'Harbor Escape Rooms', 'Harbor Mini Golf', 'Harbor Mall', 'Harbor Zoo', 'Harbor Hiking Trail',
                 'Harbor Picnic Grounds', 'Harbor Skating Rink', 'Harbor Baseball', 'Harbor Basketball',
                 'Harbor Football', 'Harbor Soccer', 'Harbor Hockey', 'Harbor Stadium', 'Harbor Concert Hall',
                 'Harbor Performing Arts', 'Harbor Musical Theater', 'Harbor Ballet', 'Harbor Opera', 'Harbor Comedy']
        for activity, name in zip(ActivityType, names, strict=True):
            with self.subTest(activity=activity):
                verdict = relevance(venue(activity=activity, name=name))
                self.assertEqual((verdict.status, verdict.reason), ('uncertain', 'name_support_only'))

    def test_missing_primary_type_and_unknown_types_are_not_negatives(self):
        for types in (None, [], ['point_of_interest', 'establishment'], ['future_provider_type']):
            self.assertEqual(relevance(venue(name='Harbor Venue', types=types)).status, 'uncertain')
        self.assertEqual(relevance(venue(name='Harbor Venue', primaryType='bowling_alley')).status, 'strong')

    def test_ambiguous_keywords_do_not_create_confidence(self):
        for activity, name in [('bowling', 'Bowling Green Park'), ('escape', 'Escape Insurance'),
                               ('theater', 'Theater Equipment Supplier'), ('coffee', 'Coffee Supply Store')]:
            with self.subTest(name=name):
                self.assertEqual(relevance(venue(activity=activity, name=name)).status, 'mismatch')
        self.assertEqual(relevance(venue(name='Bowling Green Bowling Alley')).status, 'uncertain')
        for activity, name in [('drinks', 'Barber Shop'), ('arcade', 'Arcade Avenue'), ('opera', 'Opera Cafe')]:
            self.assertEqual(relevance(venue(activity=activity, name=name)).status, 'uncertain')

    def test_primary_type_and_multi_purpose_evidence(self):
        self.assertEqual(relevance(venue(name='Bowling Dental Clinic', types=['bowling_alley'])).status, 'uncertain')
        self.assertEqual(relevance(venue(primaryType='movie_theater', name='Harbor Cinema')).status, 'mismatch')
        self.assertEqual(relevance(venue(primaryType='movie_theater', types=['bowling_alley'])).status, 'strong')
        for activity in ('baseball', 'basketball', 'football', 'soccer', 'hockey', 'ballet', 'musical'):
            self.assertEqual(relevance(venue(activity=activity, name='Harbor Venue', types=['stadium', 'performing_arts_theater'])).status, 'uncertain')

    def test_clear_mismatch_missing_types_and_empty_no_fallback(self):
        result = assess_candidates([venue(name='Harbor Movie Theater')])
        self.assertEqual(result.venues, [])
        self.assertEqual(result.diagnostics, {'incompatible_venue_name': 1})
        self.assertEqual(assess_candidates([]).venues, [])

    def test_deterministic_groups_facts_associations_and_meaningful_order(self):
        records = [venue(), venue(activity='arcade', types=['video_arcade']), venue('b', name='Other Bowling Lanes', rating=4.0)]
        def content(result):
            return {g.facts.id: g.model_dump() for g in result.venues}
        baseline = content(assess_candidates(records))
        for ordered in permutations(records):
            result = assess_candidates(list(ordered))
            self.assertEqual(content(result), baseline)
            self.assertEqual(result.venues[0].facts.id, ordered[0].id)

    @patch.dict(os.environ, {'WHERETO_PLACES_DEV': '1'})
    def test_real_candidate_pipeline_excludes_deduplicates_and_retains_associations(self):
        raw = place()
        raw['displayName']['text'] = 'Harbor Bowling Arcade'
        wrong = place()
        wrong.update(id='wrong', displayName={'text': 'Harbor Dental Clinic'})
        with patch('backend.places_transport.text_search', side_effect=[{'places': [raw, raw, wrong]}, {'places': [raw]}]) as send:
            result = PlacesDiscovery(ProviderBudget().outing()).discover_many([
                request(), DiscoveryRequest(activity='arcade', destination={'name': 'Baltimore, MD'})])
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.excluded_count, 3)
        self.assertEqual({a.value for a in result.venues[0].activities}, {'bowling', 'arcade'})
        self.assertEqual(send.call_count, 2)
        self.assertEqual(result.diagnostics['conflicting_business_name'], 1)
        self.assertNotIn('diagnostics', result.model_dump())
        self.assertNotIn('venues', result.model_dump())
        self.assertNotIn('39.28', str(result.diagnostics))

    def test_geographic_city_county_neighborhood_and_radius(self):
        wrong = place('Washington', 'DC')
        wrong['displayName']['text'] = 'Baltimore Bowling'
        county = place()
        county['addressComponents'][0]['types'] = ['administrative_area_level_2']
        result = parse_response({'places': [wrong, county, place()]}, request().area, 3)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.diagnostics, {'area_unverified': 2})
        area = SearchArea(name='Fells Point, Baltimore, MD')
        near = place()
        near['addressComponents'].append({'longText': 'Fells Point', 'types': ['neighborhood']})
        self.assertEqual(parse_response({'places': [place(), near]}, area, 3).excluded_count, 1)
        self.assertEqual(len(parse_response({'places': [near]}, SearchArea(name="Fell’s Point, Baltimore, MD"), 3).candidates), 1)
        area = SearchArea(coordinates={'latitude': 39.28, 'longitude': -76.6}, radius_m=1)
        result = parse_response({'places': [place(), place(lat=39.29)]}, area, 3)
        self.assertEqual(result.diagnostics, {'outside_radius': 1})
        self.assertEqual(len(parse_response({'places': [place(lat=45)]}, SearchArea(name='Baltimore'), 3).candidates), 1)

    @patch.dict(os.environ, {'WHERETO_PLACES_DEV': '1'})
    def test_destination_precedes_current_and_start_in_integrated_pipeline(self):
        req = request(current_location=SearchArea(coordinates={'latitude': 0, 'longitude': 0}, radius_m=1),
                      starting_location={'coordinates': {'latitude': 0, 'longitude': 0}},
                      travel_constraints={'max_first_leg_minutes': 0})
        with patch('backend.places_transport.text_search', return_value={'places': [place()]}) as send:
            result = PlacesDiscovery(ProviderBudget().outing()).discover(req)
        self.assertEqual(len(result.candidates), 1)
        self.assertNotIn('circle', send.call_args.args[0]['locationBias'])

    @patch.dict(os.environ, {'WHERETO_PLACES_DEV': '1'})
    def test_all_filtered_returns_empty_without_refill_or_fiction(self):
        raw = place()
        raw['displayName']['text'] = 'Harbor Cinema'
        with patch('backend.places_transport.text_search', return_value={'places': [raw]}) as send:
            result = PlacesDiscovery(ProviderBudget().outing()).discover(request())
        self.assertEqual((result.candidates, result.venues, result.excluded_count), ([], [], 1))
        send.assert_called_once()

    @patch.dict(os.environ, {'WHERETO_PLACES_DEV': '1'})
    def test_budgets_and_mixed_areas_reject_before_extra_transport(self):
        adapter = PlacesDiscovery(ProviderBudget(ProviderSettings(searches_per_outing=1)).outing())
        with patch('backend.places_transport.text_search', return_value={'places': []}) as send:
            adapter.discover(request())
            with self.assertRaises(ProviderLimitError):
                adapter.discover(DiscoveryRequest(activity='coffee', destination={'name': 'Baltimore, MD'}))
            self.assertEqual(send.call_count, 1)
        with patch('backend.places_transport.text_search') as send:
            with self.assertRaises(ProviderLimitError):
                adapter.discover_many([request(), request()])
            with self.assertRaisesRegex(DiscoveryError, 'one explicit'):
                PlacesDiscovery(ProviderBudget().outing()).discover_many([
                    request(), DiscoveryRequest(activity='coffee', destination={'name': 'Washington, DC'})])
            send.assert_not_called()

    def test_fictional_planner_isolated_even_with_dev_switch(self):
        req = OutingRequest(activities=['bowling', 'movie', 'food'], date='2026-11-07')
        baseline = recommend_plans(req).model_dump()
        with patch.dict(os.environ, {'WHERETO_PLACES_DEV': '1'}), \
             patch('backend.venue_quality.assess_candidates', side_effect=AssertionError('quality called')), \
             patch('backend.places_transport.text_search', side_effect=AssertionError('transport called')):
            self.assertEqual(recommend_plans(req).model_dump(), baseline)
        self.assertTrue(baseline['provisionalPlans'] or baseline['plans'])


if __name__ == '__main__':
    unittest.main()
