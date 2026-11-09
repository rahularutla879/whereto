"""Reviewed spelling regression; all venue/origin coordinates are fictional.

These are hypothetical provider replies, not the original browser response.
No known My Home Bhooja coordinates or live availability are represented.
"""
from copy import deepcopy
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch

from backend.location_context import outing_problem
from backend.option_sessions import option_sessions
from backend.places import DiscoveryError, SearchArea
from backend.provider_budget import ProviderBudget
from backend.real_fixtures import matrix_fixture
from backend.real_planning import PlannerInput, real_plans
from backend.testing_clock import calendar_clock
from backend.test_real_planning import ENV
from backend.venue_geography import geographic_reason, normalized
from backend.venue_models import Coordinates

POINT = Coordinates(latitude=0., longitude=0.)
ORIGIN = {'point': {'id': 'authorized-start', 'coordinates': POINT.model_dump()},
          'explicitly_authorized': True, 'source': 'manual',
          'precision': 'address_or_place', 'label': 'Synthetic confirmed origin'}
NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


def components(neighborhood='HITEC City', city='Hyderabad', region='Telangana'):
    return [{'longText': name, 'types': [kind]} for name, kind in
            [(neighborhood, 'sublocality_level_1'), (city, 'locality'),
             (region, 'administrative_area_level_1')] if name]


class HitecSpellingTests(unittest.TestCase):
    def reason(self, name, evidence=None, **kw):
        return geographic_reason(SearchArea(name=name, **kw), POINT,
                                 components() if evidence is None else evidence)

    def test_exact_reviewed_alias_and_all_requested_parent_tokens(self):
        for spelling in ('Hitech City', 'HITEC City', 'hitech-city'):
            for name in (spelling, spelling + ', Hyderabad', spelling + ', Hyderabad, Telangana'):
                for supplied in ('HITEC City', 'Hitech City'):
                    with self.subTest(name=name, supplied=supplied):
                        self.assertIsNone(self.reason(name, components(supplied)))
        self.assertEqual(self.reason('Hitech City, Bengaluru'), 'area_unverified')
        self.assertEqual(self.reason('Hitech City, Andhra Pradesh'), 'area_unverified')

    def test_parent_only_or_wrong_parent_never_establishes_alias(self):
        for evidence in (components(None), components(city=None), components(region=None),
                         components(city='Bengaluru'), components(region='Andhra Pradesh'), []):
            self.assertEqual(self.reason('Hitech City', evidence), 'area_unverified')
        # Same-spelling matching retains its existing semantics.
        self.assertIsNone(self.reason('Hitech City', components('Hitech City', None, None)))

    def test_no_business_landmark_county_or_fuzzy_alias(self):
        for kind in ('establishment', 'route', 'premise', 'administrative_area_level_2', 'locality'):
            evidence=components(None)+[{'longText': 'HITEC City', 'types': [kind]}]
            self.assertEqual(self.reason('Hitech City', evidence), 'area_unverified')
        for requested in ('Hitech City Mall', 'Hitec', 'Hitech', 'HITEX City',
                          'My Home Bhooja', 'Madhapur', 'Hitech City Phase 2'):
            self.assertEqual(self.reason(requested), 'area_unverified')
        self.assertEqual(self.reason('Hitech City', components('HITEC City Mall')), 'area_unverified')
        self.assertNotEqual(normalized('Hitech City'), normalized('HITEC City'),
                            'Global venue/name identity normalization must stay unchanged')

    def test_distant_alias_matches_still_require_destination_clarification(self):
        from backend.places import parse_response
        records=[]
        for i,latitude in enumerate((0.,2.)):
            records.append({'id':'Synthetic_area_'+str(i),'displayName':{'text':'Synthetic venue'},
                'formattedAddress':'Synthetic address', 'location':{'latitude':latitude,'longitude':0.},
                'addressComponents':components()})
        with self.assertRaises(DiscoveryError) as caught:
            parse_response({'places':records},SearchArea(name='Hitech City',enforce_name=False),10)
        self.assertEqual(caught.exception.code,'destination_ambiguous')

    def test_radius_and_region_guards_still_run_after_alias(self):
        far=Coordinates(latitude=1., longitude=1.)
        self.assertEqual(self.reason('Hitech City', coordinates=far, radius_m=500.), 'outside_radius')
        self.assertEqual(self.reason('Hitech City', boundary_coordinates=far, boundary_radius_m=500.), 'outside_radius')
        self.assertEqual(self.reason('Hitech City', excluded_regions=['VA'],
            evidence=components()+[{'shortText':'VA','types':['administrative_area_level_1']}]), 'excluded_region')


class HitecPlanningTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, ENV, clear=True))
        self.enterContext(calendar_clock(NOW))
        self.enterContext(patch('requests.sessions.Session.send', side_effect=AssertionError('No live sends')))
        self.evidence=components()
        self.search=self.enterContext(patch('backend.places_transport.text_search', side_effect=self.supplied))
        self.routes=self.enterContext(patch('backend.routes_transport.compute_matrix', side_effect=matrix_fixture))
        self.addCleanup(option_sessions.entries.clear)
        self.request=PlannerInput(activities=['custom:box cricket','food','movie'],
            activityIntents={'custom:box cricket':'box cricket'}, dinner=True,
            location='hitech city', date='2026-11-10', calendarTimezone='Asia/Kolkata',
            transport='driving', locationFirst=True, startingLocation=ORIGIN)

    def supplied(self, body, **kw):
        phrase=('box cricket' if 'box cricket' in body['textQuery'] else
                'movie' if 'movie' in body['textQuery'] or 'cinema' in body['textQuery'] else 'restaurant')
        kind={'box cricket':'establishment','movie':'movie_theater','restaurant':'restaurant'}[phrase]
        return {'places':[{'id':'Synthetic_'+phrase.replace(' ','_')+str(i),
            'displayName':{'text':'Synthetic '+phrase+' '+str(i)},
            'formattedAddress':'Synthetic address only', 'location':POINT.model_dump(),
            'types':[kind], 'addressComponents':deepcopy(self.evidence)} for i in range(3)]}

    def test_fixed_date_original_three_stops_proceed_without_rewriting_destination(self):
        original=self.request.model_dump()
        self.assertIsNone(outing_problem(self.request))
        result=real_plans(self.request, ProviderBudget())
        self.assertTrue(result.provisionalPlans, result.message)
        self.assertEqual(self.request.model_dump(), original)
        self.assertEqual(result.request.location, 'hitech city')
        self.assertEqual(result.request.date.isoformat(), '2026-11-10')
        self.assertEqual(result.request.transport, 'driving')
        self.assertEqual(result.request.activities, ['custom:box cricket','food','movie'])
        self.assertFalse(self.request.useOriginAsSearchAnchor)
        self.assertEqual(self.search.call_count, 3)
        bodies=[str(c.args[0]) for c in self.search.call_args_list]
        self.assertEqual(len(set(bodies)), 3, 'No retry/duplicate request')
        self.assertIn('hitech city', self.search.call_args_list[0].args[0]['textQuery'])
        self.assertTrue(all(p.firstLeg['source']=='manual' for p in result.provisionalPlans))
        self.assertTrue(all([v.activity for v in p.candidate.venues]==self.request.activities
                            for p in result.provisionalPlans))
        self.assertFalse('"latitude":' in result.model_dump_json())

    def test_missing_neighborhood_reproduces_error_and_retries_retain_accounting(self):
        self.evidence=components(None)
        session=ProviderBudget()
        for attempt in (1,2):
            with self.assertRaises(DiscoveryError) as caught:
                real_plans(self.request, session)
            error=caught.exception
            self.assertEqual(error.code, 'destination_unresolved')
            self.assertEqual(error.diagnostics['failureBoundary'], 'geography')
            self.assertEqual(error.diagnostics['discoveryReasons'], {'area_unverified':3})
            self.assertIn("couldn't confidently locate", str(error))
            self.assertEqual(self.search.call_count, attempt)
            self.assertEqual(session._requests, attempt)
            self.assertEqual(self.routes.call_count, 0)
        self.assertFalse(self.request.useOriginAsSearchAnchor)
        self.assertEqual(self.request.location, 'hitech city')

    def test_explicit_reference_consent_does_not_bypass_strict_destination(self):
        self.evidence=components(None)
        with self.assertRaises(DiscoveryError) as caught:
            real_plans(self.request.model_copy(update={'useOriginAsSearchAnchor':True,
                'geography':self.request.geography.model_copy(update={'strictDestination':True})}), ProviderBudget())
        self.assertEqual(caught.exception.code, 'geographic_verification')
        self.assertEqual(self.routes.call_count, 0)
        result=real_plans(self.request.model_copy(update={'useOriginAsSearchAnchor':True}), ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertEqual(result.request.location, 'hitech city')

    def test_explicit_destination_correction_keeps_other_requirements(self):
        corrected=self.request.model_copy(update={'location':'HITEC City, Hyderabad, Telangana'})
        result=real_plans(corrected, ProviderBudget())
        self.assertTrue(result.provisionalPlans, result.message)
        self.assertEqual(result.request.location, corrected.location)
        for field in ('activities','date','transport','dinner'):
            self.assertEqual(getattr(result.request,field),getattr(self.request,field))
