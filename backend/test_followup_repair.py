"""Follow-up acceptance: invented provider inventories; actual sends blocked."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from backend import test_advanced_planning as fixture
from backend.test_advanced_routing import start
from backend.test_stop_resolution import place
from backend.advanced_planning import AdvancedAnswerError, AdvancedInput, Sessions
from backend.advanced_routing import _shortlist

class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.h=fixture.IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def nearby(self):
        s=self.h.session([{'source':'grocery shopping'}],endpoint={'kind':'origin','source':'return'})
        s.text='Go grocery shopping tomorrow and return to where I started.'
        s.context.destination=None;s.context.timezone='UTC';s.context.timezoneBasis='unknown';s.requires_date_confirmation=True
        return s
    def test_device_nearby_uses_public_calendar_and_original_outbound_return(self):
        s=self.nearby();origin=start()
        first=self.h.run_session(s,startingLocation=origin)
        self.assertEqual(first.questions[0]['field'],'destination')
        r=self.h.run_session(s,startingLocation=origin,searchNearOrigin=True)
        self.assertEqual(r.status,'results');self.assertEqual(r.date,'2026-11-03')
        self.assertEqual([l.role for l in r.options[0].legs],['origin_to_first','return_to_origin'])
        self.assertEqual(s.origin,origin);self.assertEqual(s.context.timezone,'America/New_York')
        self.assertNotIn('latitude',r.model_dump_json())
        counts=(len(self.h.searches),len(self.h.calls))
        repeated=self.h.run_session(s,startingLocation=origin,searchNearOrigin=True)
        self.assertEqual(repeated,r);self.assertEqual(counts,(len(self.h.searches),len(self.h.calls)))
    def test_changed_origin_rejected_before_mutation_or_calls(self):
        s=self.nearby();self.h.run_session(s,startingLocation=start(),searchNearOrigin=True)
        other=start().model_copy(update={'accuracy_m':900,'precision':'approximate_area'})
        counts=(len(self.h.searches),len(self.h.calls));destination=s.context.destination
        with self.assertRaisesRegex(AdvancedAnswerError,'starting point changed'):
            self.h.run_session(s,startingLocation=other,searchNearOrigin=True)
        self.assertEqual(s.context.destination,destination);self.assertEqual(counts,(len(self.h.searches),len(self.h.calls)))
    def test_explicit_destination_never_replaced_with_origin(self):
        s=self.h.session([{'source':'grocery shopping'}])
        with self.assertRaises(AdvancedAnswerError):self.h.run_session(s,startingLocation=start(),searchNearOrigin=True)
        self.assertEqual(s.context.destination,'New York');self.assertEqual(self.h.searches,[])
    def test_real_expiry_has_separate_safe_code(self):
        s=self.nearby();s.expires=0;sessions=Sessions();sessions.items[s.token]=s
        with self.assertRaises(AdvancedAnswerError) as c:sessions.run(AdvancedInput(token=s.token))
        self.assertEqual(c.exception.code,'advanced_session_expired')
    def test_unknown_calendar_keeps_coordinate_bias_and_accepts_exact_date(self):
        self.h.records=deepcopy(self.h.records)
        for record in self.h.records:record['formattedAddress']='Unknown calendar';record.pop('timeZone',None)
        s=self.nearby();r=self.h.run_session(s,startingLocation=start(),searchNearOrigin=True)
        self.assertEqual(r.questions[0]['field'],'date');self.assertEqual(s.context.timezoneBasis,'unknown')
        searches=len(self.h.searches)
        r=self.h.run_session(s,startingLocation=start(),date='2026-11-07')
        self.assertEqual(r.status,'results');self.assertEqual(searches,len(self.h.searches))
        self.assertIsNotNone(s.search_area.coordinates)
    def test_duration_units_relations_validation_and_original_atm(self):
        from pydantic import ValidationError
        for value in [-1,1.5,10081,'20']:
            with self.assertRaises(ValidationError):AdvancedInput(token='x'*43,dwell={'occurrence':0,'minutes':value,'relation':'exact'})
        s=self.h.session([{'source':'groceries'},{'source':'ATM','duration':{'minutes':5,'relation':'exact','source':'5 minutes'}}],endpoint={'kind':'origin','source':'return'},total_duration={'minutes':45,'relation':'maximum','source':'within 45 minutes'})
        self.h.run_session(s,startingLocation=start());counts=(len(self.h.searches),len(self.h.calls))
        r=self.h.run_session(s,startingLocation=start(),dwell={'occurrence':0,'minutes':20,'relation':'exact'})
        self.assertEqual(r.options[0].durationState,'feasible');self.assertEqual(r.options[0].stops[1].duration.minutes,5)
        self.assertEqual(r.options[0].totalConstraint.minutes,45);self.assertEqual(counts,(len(self.h.searches),len(self.h.calls)))
    def test_rich_inventory_represents_later_stops_and_unchecked_paths(self):
        for i in range(18):
            self.h.records.extend([place(f'Synthetic_cafe_rich_{i}',f'Cafe {i}',types=['cafe'],lat=40.75+i*.001),place(f'Synthetic_atm_rich_{i}',f'Bank ATM {i}',types=['atm','bank'],lat=40.75+i*.001)])
        offsets={}
        def paged(body,**kwargs):
            activity='cafe' if 'cafe' in body['textQuery'].lower() else 'atm'
            records=[r for r in self.h.records if activity in r['types']]
            offset=offsets.get(activity,0);offsets[activity]=offset+10
            self.h.searches.append(body)
            return {'places':records[offset:offset+10],**({'nextPageToken':'invented-next'} if offset==0 else {})}
        self.h.search_patch=patch('backend.places_transport.text_search',side_effect=paged)
        self.h.search_patch.start();self.addCleanup(self.h.search_patch.stop)
        s=self.h.session([{'source':'coffee'},{'source':'ATM'}]);self.h.run_session(s)
        varied=self.h.run_session(s,action='discover')
        self.assertGreater(len({o.stops[0].placeId for o in varied.options}),1)
        self.assertGreater(len({o.stops[1].placeId for o in varied.options}),1)
        snap=s.resolver.routing_snapshot()
        paths=_shortlist(snap,None,None,100,s.router.checked)
        self.assertGreater(len({p[1][1].place_id for p in paths}),10)
        self.assertGreater(len({p[0][1].place_id for p in paths}),10)
        offered=set(s.seen);self.h.run_session(s,action='different')
        self.assertTrue(s.seen-offered)
        audit=s.resolver.coverage(s.router,s.seen)
        self.assertGreater(audit['stops'][1]['retained'],10)
        self.assertTrue(audit['pendingRouteFrontier'])
        self.assertLess(audit['checkedAssignments'],len(snap.stops[0].candidates)*len(snap.stops[1].candidates))
        self.assertNotIn('Synthetic',str(audit));self.assertNotIn('latitude',str(audit))
    def test_directional_seconds_are_associated_with_correct_legs_and_mode(self):
        self.h.values.update({('DRIVE','origin','Synthetic_college'):1320,('DRIVE','Synthetic_college','Synthetic_coffee'):200,('DRIVE','Synthetic_coffee','origin'):1860})
        s=self.h.session(endpoint={'kind':'origin','source':'return'})
        r=self.h.run_session(s,startingLocation=start())
        self.assertEqual([l.role for l in r.options[0].legs],['origin_to_first','inter_activity','return_to_origin'])
        self.assertEqual([l.seconds for l in r.options[0].legs],[1320,200,1860])
        self.assertEqual(r.options[0].knownTravelSeconds,sum(l.seconds for l in r.options[0].legs))
        self.assertTrue(all(l.mode=='drive' for l in r.options[0].legs))
        for call in self.h.calls:
            self.assertEqual(call['routingPreference'],'TRAFFIC_AWARE');self.assertNotIn('departureTime',call)
        self.assertNotIn('origin_place_id',r.options[0].legs[0].mapsUrl);self.assertNotIn('destination_place_id',r.options[0].legs[-1].mapsUrl)
        self.assertNotIn('advanced_origin',str([l.mapsUrl for l in r.options[0].legs]))

    def test_representative_origin_qualification_keeps_actual_route_point(self):
        s=self.nearby();origin=start().model_copy(update={'source':'manual','precision':'postal_area','accuracy_m':500})
        r=self.h.run_session(s,startingLocation=origin,searchNearOrigin=True)
        self.assertEqual(r.status,'results');self.assertTrue(r.options[0].originApproximate)
        self.assertEqual(s.origin.point,origin.point)
