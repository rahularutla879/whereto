"""Exact recorded local extraction and invented provider evidence; Google blocked."""
import json,unittest
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlparse,parse_qs
from unittest.mock import Mock
from backend.ai import Interpretation
from backend.interpretation import interpret_request,InterpretationInput
from backend import test_advanced_planning as fixture
from backend.test_advanced_routing import start
from backend.test_advanced_timing import duration
from backend.test_stop_resolution import place

class ReturnPhrases(unittest.TestCase):
    def test_actual_installed_model_outputs_normalize_without_guessing_endpoint(self):
        for row in json.loads(Path(__file__).with_name('return_phrase_extractions.json').read_text()):
            with self.subTest(text=row['text']):
                p=Mock();p.interpret.return_value=Interpretation.model_validate(row['raw'])
                r=interpret_request(InterpretationInput(text=row['text']),p,now=datetime(2026,11,4,15,tzinfo=timezone.utc))
                j=r.interpretation.journey
                self.assertEqual([s.requirement for s in j.stops],['required','required'])
                self.assertEqual(j.stops[0].kind,'named_place');self.assertFalse(j.order_conflict)
                self.assertEqual((j.order[0].before,j.order[0].after),(0,1))
                self.assertEqual((j.total_duration.minutes,j.total_duration.relation),(180,'maximum'))
                self.assertTrue(all(s.duration is None for s in j.stops));self.assertIsNone(j.deadline)
                if 'to my starting point' not in row['text']:
                    self.assertEqual([q.field for q in r.questions],['endpoint'])
                    r=interpret_request(InterpretationInput(text=row['text'],pending=r.pending,answers={'endpoint':'Return to my starting point'}),p,now=datetime(2026,11,4,15,tzinfo=timezone.utc))
                    self.assertEqual(r.context.endpointStatus,'origin_confirmed')
                self.assertEqual(p.interpret.call_count,1)
                self.assertEqual(r.executionStatus,'advanced_unavailable',r.issues)
    def test_identity_after_duration_is_not_missing_identity(self):
        from backend.journey import unresolved_return_clause
        self.assertIsNone(unresolved_return_clause('Get coffee and return within three hours to Penn Station.'))
        self.assertIsNone(unresolved_return_clause('Get coffee, be back within three hours, then return home.'))

    def test_numeric_conflict_and_named_endpoint_cannot_be_repaired_away(self):
        row=json.loads(Path(__file__).with_name('return_phrase_extractions.json').read_text())[0]
        for change in ('total','endpoint','cycle'):
            raw=json.loads(json.dumps(row['raw']))
            if change=='total':raw['journey']['total_duration']={'minutes':90,'relation':'maximum','source':'within 3 hours'}
            if change=='endpoint':raw['journey']['endpoint']={'kind':'named_place','source':'Penn Station'}
            if change=='cycle':raw['journey']['order'].append({'before':1,'after':0,'source':row['text']})
            p=Mock();p.interpret.return_value=Interpretation.model_validate(raw)
            r=interpret_request(InterpretationInput(text=row['text']),p)
            self.assertFalse(r.questions);self.assertIsNone(r.request)
            self.assertIn('unclear or conflict',r.issues[0])

class LegsExploration(unittest.TestCase):
    def setUp(self):
        self.h=fixture.IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def optional(self):
        return self.h.session([{'source':'groceries','duration':duration(10)},{'source':'pharmacy','duration':duration(5)},{'source':'coffee','requirement':'optional','evidence':'maybe coffee','duration':duration(20)}],endpoint={'kind':'origin','source':'return to starting point'},total_duration=duration(90,'maximum'))
    def inventory(self,n=10):
        self.h.records=[place(f'Synthetic_{k}_{i}',f'Invented {k} {i}',types=[k],lat=40.75+i*.0001) for k in ('supermarket','pharmacy','cafe') for i in range(n)]
    def slow_cafes(self,count):
        for a in self.h.records:
            for b in self.h.records:
                if ('cafe' in a['types'] and int(a['id'].split('_')[-1])<count) or ('cafe' in b['types'] and int(b['id'].split('_')[-1])<count):self.h.values['DRIVE',a['id'],b['id']]=3000
    def test_optional_later_combination_first_continuation_without_places(self):
        self.inventory();self.slow_cafes(4);s=self.optional()
        a=self.h.run_session(s,startingLocation=start());self.assertTrue(all(len(o.stops)==2 for o in a.options))
        self.assertEqual(a.exploration['optional'][0]['state'],'checked_infeasible');self.assertTrue(a.canExpand and a.canDiscover)
        self.assertIn('checked so far',a.options[0].omitted[0]['explanation'])
        before=len(self.h.searches);b=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertTrue(any(len(o.stops)==3 for o in b.options));self.assertEqual(len(self.h.searches),before)
        self.assertTrue(set(o.id for o in a.options).isdisjoint(o.id for o in b.options))
        self.assertTrue(all(o.elapsedUpperSeconds<=5400 for o in b.options))
        print('50E later combinations:',s.selection_counts,'usage',s.outing.usage())
    def test_discovery_prioritizes_optional_coffee_and_keeps_required_inventory(self):
        self.inventory(4);self.slow_cafes(4);s=self.optional();a=self.h.run_session(s,startingLocation=start())
        before=len(self.h.searches);old={c.place_id for c in s.resolver.routing_snapshot().stops[0].candidates}
        self.h.records.append(place('Synthetic_cafe_10','Invented new cafe',types=['cafe']))
        b=self.h.run_session(s,startingLocation=start(),action='discover')
        self.assertIn('cafe',self.h.searches[before]['textQuery'])
        self.assertTrue(old<={c.place_id for c in s.resolver.routing_snapshot().stops[0].candidates})
        self.assertLessEqual(len(self.h.searches)-before,2)
        for _ in range(4):
            if any(len(o.stops)==3 for o in b.options):break
            b=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertTrue(any(len(o.stops)==3 and o.stops[2].placeId=='Synthetic_cafe_10' for o in b.options))
    def test_three_hour_inclusive_limit_and_edit_keep_return_hard(self):
        s=self.h.session([{'source':'SUNY College of Optometry','kind':'named_place','duration':duration(160)},{'source':'coffee','duration':duration(14)}],endpoint={'kind':'origin','source':'return to starting point'},total_duration=duration(180,'maximum'))
        a=self.h.run_session(s,startingLocation=start());self.assertTrue(a.options)
        self.assertEqual(a.options[0].elapsedUpperSeconds,10800)
        self.assertEqual(a.options[0].durationState,'feasible')
        counts=len(self.h.searches),len(self.h.calls)
        b=self.h.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':1,'minutes':15,'relation':'exact'}]})
        self.assertFalse(b.options);self.assertFalse(b.canShowBeyond)
        self.assertEqual(counts,(len(self.h.searches),len(self.h.calls)))

    def test_private_origin_outbound_return_and_public_legs(self):
        s=self.h.session(endpoint={'kind':'origin','source':'return to start'});r=self.h.run_session(s,startingLocation=start())
        legs=r.options[0].legs
        for leg in legs:
            q=parse_qs(urlparse(leg.mapsUrl).query);self.assertEqual(q['api'],['1']);self.assertEqual(q['travelmode'],['driving'])
            self.assertNotIn('advanced_origin',leg.mapsUrl);self.assertNotIn('40.75',leg.mapsUrl)
        self.assertNotIn('origin',parse_qs(urlparse(legs[0].mapsUrl).query))
        self.assertNotIn('destination',parse_qs(urlparse(legs[-1].mapsUrl).query))
        self.assertEqual(parse_qs(urlparse(legs[1].mapsUrl).query)['destination_place_id'],['Synthetic_coffee'])
        self.assertNotIn('latitude',r.model_dump_json())
    def test_origin_free_named_ending_walking(self):
        s=self.h.session([{'source':'coffee'}],endpoint={'kind':'named_place','source':'finish at Penn Station'})
        from backend.models import TransportationMode
        s.context.transport=TransportationMode.walking
        r=self.h.run_session(s);self.assertEqual(len(r.options[0].legs),1)
        q=parse_qs(urlparse(r.options[0].legs[-1].mapsUrl).query)
        self.assertEqual(q['origin_place_id'],['Synthetic_coffee']);self.assertEqual(q['destination_place_id'],['Synthetic_station']);self.assertEqual(q['travelmode'],['walking'])
    def test_unknown_coffee_duration_and_hard_cap_preserved(self):
        s=self.optional();s.journey.stops[2].duration=None
        a=self.h.run_session(s,startingLocation=start());self.assertEqual(a.exploration['optional'][0]['state'],'needs_duration')
        self.assertTrue(any(q.get('occurrence')==2 for q in a.questions))
        counts=len(self.h.searches),len(self.h.calls)
        b=self.h.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':2,'minutes':90,'relation':'exact'}]})
        self.assertTrue(all(len(o.stops)==2 for o in b.options));self.assertIn('visit times alone',b.options[0].omitted[0]['explanation']);self.assertEqual(counts,(len(self.h.searches),len(self.h.calls)))
    def test_stale_evidence_recovery_has_specific_code(self):
        from datetime import timedelta
        s=self.optional();self.h.run_session(s,startingLocation=start())
        for c in s.candidates.values():
            for l in c.legs:l.evidence=l.evidence.model_copy(update={'observed_at':l.evidence.observed_at-timedelta(minutes=6)})
        r=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertEqual(r.code,'advanced_evidence_expired');self.assertEqual(r.exploration['combination'],'evidence_expired')
        self.assertFalse(r.canDiscover);self.assertTrue(s.seen)
