"""Direct deterministic shortlist checks, with fictional candidates only."""
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from backend.advanced_routing import _shortlist
from backend.test_task52_ordering_v5 import reply


class V51PlannerCompatibility(TestCase):
    def test_required_flexible_coffee_can_precede_split_or_follow_partial_order(self):
        c={'text':'Pharmacy before bank; coffee whenever convenient.','stops':['Pharmacy','bank','coffee'],'expectedEdges':[[0,1]]}
        ai=reply(c)
        groups=[NS(occurrence=i,requested=s,status='candidates',candidates=[NS(place_id=f'fictional-{i}')]) for i,s in enumerate(ai.journey.stops)]
        with patch('backend.advanced_routing._gap',return_value=0):paths=_shortlist(NS(journey=ai.journey,stops=groups),None,None)
        self.assertEqual({tuple(i for i,_ in path) for path in paths},{(0,1,2),(0,2,1),(2,0,1)})
