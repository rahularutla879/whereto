"""Inventory checks exercise query/relevance evidence, not real availability."""
import unittest
from backend.models import ActivityType
from backend.places import QUERIES,DiscoveryRequest,SearchArea,search_body
from backend.interpretation import activity_category
from backend.venue_quality import relevance
from backend.venue_normalization import normalize_google_place
from backend.location_fixtures import place

class ActivityAudit(unittest.TestCase):
    def test_complete_canonical_query_inventory(self):
        self.assertEqual(len(list(ActivityType)),29)
        self.assertEqual(set(QUERIES),{a.value for a in ActivityType})
        for activity in ActivityType:
            body=search_body(DiscoveryRequest(activity=activity,destination=SearchArea(name='Hyderabad')),10)
            self.assertIn(QUERIES[activity.value],body['textQuery'])
            self.assertEqual('includedType' in body,activity=='bowling')
    def test_representative_flexible_activity_evidence_and_negative_controls(self):
        phrases=['pottery class','cooking workshop','painting workshop','swimming','laser tag','go-karting','rock climbing','fitness class','dance studio','spa','bookstore','aquarium','garden']
        for phrase in phrases:
            identity=activity_category(phrase)
            self.assertTrue(identity.startswith('custom:'),phrase)
            query=search_body(DiscoveryRequest(activity=identity,destination=SearchArea(name='Hyderabad')),10)
            self.assertNotIn('includedType',query)
            valid=normalize_google_place(place('Synthetic_valid','Synthetic '+phrase,types=['book_store'] if phrase=='bookstore' else ['establishment']),identity)
            invalid=normalize_google_place(place('Synthetic_invalid','Synthetic dental clinic',types=['dentist']),identity)
            self.assertEqual(relevance(valid).status,'strong' if phrase=='bookstore' else 'uncertain',phrase)
            self.assertEqual(relevance(invalid).status,'mismatch',phrase)
