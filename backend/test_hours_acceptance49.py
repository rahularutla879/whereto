"""Hours preparation reuses supplied, dated evidence. No live field is enabled."""
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from backend.test_feasibility import stop,period,request,NOW
from backend.feasibility import evaluate_feasibility
from backend.venue_normalization import normalize_google_place
from backend.places import FIELD_MASK
from backend.saved_refresh import REFRESH_MASK, CONTACT_REFRESH_MASK

class HoursAcceptance(unittest.TestCase):
 def setUp(self):
  guard=patch('requests.Session.send',side_effect=AssertionError('No hours requests authorized'));guard.start();self.addCleanup(guard.stop)
 def state(self,s,mode='drive'):
  r=request(stops=[s],routes=[]);r.mode=mode
  return evaluate_feasibility(r)
 def test_requested_window_open_closed_before_arrival_opens_late_and_closes_during(self):
  for opening,closing,expected in [(9,11,'feasible'),(8,9,'infeasible'),(11,22,'infeasible'),(9,10,'infeasible')]:
   for mode in ('drive','walk'):
    with self.subTest(opening=opening,closing=closing,mode=mode):
     self.assertEqual(self.state(stop(periods=[period(opening=opening,closing=closing)]),mode).hours_state,expected)
 def test_missing_schedule_duration_or_hours_never_implies_open(self):
  for missing in ('schedule','hours'):
   s=stop()
   if missing=='schedule':s.arrival=None;s.departure=None
   else:s.venue.currentOpeningHours=None
   self.assertEqual(self.state(s).hours_state,'unverified')
 def test_sunday_monday_and_special_day_overrides_use_dated_current_periods(self):
  s=stop(arrival='2026-10-25T14:00:00Z',departure='2026-10-25T15:00:00Z',periods=[period('2026-10-25',9,'2026-10-25',12)])
  self.assertEqual(self.state(s).hours_state,'feasible')
  s.arrival=datetime.fromisoformat('2026-10-26T14:00:00Z');s.departure=datetime.fromisoformat('2026-10-26T15:00:00Z')
  self.assertEqual(self.state(s).hours_state,'infeasible')
  s.venue.regularOpeningHours=stop().venue.currentOpeningHours
  self.assertEqual(self.state(s).hours_state,'infeasible')
 def test_overnight_and_always_open_sentinel(self):
  s=stop(arrival='2026-10-24T23:30:00-04:00',departure='2026-10-25T00:30:00-04:00',periods=[period(opening=22,end='2026-10-25',closing=2)])
  self.assertEqual(self.state(s).hours_state,'feasible')
  s=stop(periods=[{'open':{'day':0,'hour':0,'minute':0}}]);self.assertEqual(self.state(s).hours_state,'feasible')
 def test_destination_timezone_and_future_coverage(self):
  # 04:30 UTC is 10 AM in Hyderabad, not the browser's New York clock.
  now=datetime(2026,10,24,1,tzinfo=timezone.utc)
  s=stop(arrival='2026-10-24T04:30:00Z',departure='2026-10-24T05:30:00Z',now=now,zone='Asia/Kolkata',periods=[period(opening=9,closing=12)])
  r=request(stops=[s],routes=[]);r.evaluated_at=now
  self.assertEqual(evaluate_feasibility(r).hours_state,'feasible')
  s.arrival=datetime.fromisoformat('2026-11-07T04:30:00Z');s.departure=datetime.fromisoformat('2026-11-07T05:30:00Z')
  self.assertEqual(evaluate_feasibility(r).hours_state,'unverified')
 def test_operational_is_not_open_and_open_restaurant_is_not_booked(self):
  s=stop(periods=[],activity='food')
  s.venue=normalize_google_place({'id':'a','displayName':{'text':'Synthetic restaurant'},'businessStatus':'OPERATIONAL','timeZone':{'id':'America/New_York'},'currentOpeningHours':{'periods':[]}},'food',observed_at=NOW)
  result=self.state(s);self.assertEqual(result.hours_state,'infeasible')
  s=stop(activity='food');result=self.state(s);self.assertEqual(result.hours_state,'feasible')
  self.assertFalse(any('reservation' in c.code or 'ticket' in c.code for c in result.checks))
 def test_special_days_normalize_without_losing_override_and_live_masks_unchanged(self):
  v=normalize_google_place({'id':'synthetic','displayName':{'text':'Synthetic venue'},'currentOpeningHours':{'periods':[],'specialDays':[{'date':{'year':2026,'month':10,'day':25}}]}},'food',observed_at=NOW)
  self.assertEqual(v.currentOpeningHours.specialDays[0].isoformat(),'2026-10-25')
  for mask in (FIELD_MASK,REFRESH_MASK,CONTACT_REFRESH_MASK):self.assertNotIn('OpeningHours',mask);self.assertNotIn('timeZone',mask)
