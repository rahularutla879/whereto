"""Authored identifiers only. No network or real provider content."""
import unittest
from pydantic import ValidationError
from backend.google_retention import GoogleReferences,references_from_search
from experiments.shared_state.contracts import Denied
from experiments.shared_state.evidence_models import pack

class RetentionTests(unittest.TestCase):
    def test_only_identifiers_no_names_or_route_fields(self):
        for field in ('name','coordinates','duration','distanceMeters','attributions','rawResponse'):
            with self.subTest(field=field),self.assertRaises(ValidationError):GoogleReferences(place_ids=('Fixture_A',),**{field:'not admitted'})
    def test_projection_is_explicit_and_not_checkpoint(self):
        r=references_from_search({'places':[{'id':'Fixture_A','displayName':{'text':'Authored name'}},{'id':'Fixture_A'}]})
        self.assertEqual(r.place_ids,('Fixture_A',));self.assertNotIn('Authored name',r.model_dump_json())
        with self.assertRaises(Denied):r.require_checkpoint()
        with self.assertRaises(Denied):pack({'raw':r},'google_real_v1')
    def test_invalid_identifiers_and_capacity_refuse(self):
        for ids in [(),('id\nprivate',),('x'*257,),tuple('Fixture_'+str(i) for i in range(101))]:
            with self.subTest(length=len(ids)),self.assertRaises(ValidationError):GoogleReferences(place_ids=ids)
