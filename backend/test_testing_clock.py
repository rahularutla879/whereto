"""Calendar fixture boundaries; never relax actual expiry or capability TTLs."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import unittest
from unittest.mock import patch

from backend import location_context
from backend.date_resolution import resolve_datetime
from backend.models import OutingRequest
from backend.testing_clock import calendar_clock,route_evidence_clock,FIXTURE_NOW


def request(day='2026-11-07',**kw):
    return OutingRequest(activities=['coffee'],location='New York',date=day,
        calendarTimezone='America/New_York',**kw)


class CalendarFixtureTests(unittest.TestCase):
    def test_timezone_aware_reference_required_and_clock_restores(self):
        original=location_context.datetime
        with self.assertRaises(ValueError):calendar_clock(datetime(2026,11,1))
        with self.assertRaisesRegex(RuntimeError,'synthetic'):
            with calendar_clock():
                self.assertEqual(location_context.datetime.now(timezone.utc),FIXTURE_NOW)
                with calendar_clock(datetime(2040,1,1,tzinfo=timezone.utc)):
                    self.assertEqual(location_context.datetime.now(timezone.utc).year,2040)
                self.assertEqual(location_context.datetime.now(timezone.utc),FIXTURE_NOW)
                raise RuntimeError('synthetic')
        self.assertIs(location_context.datetime,original)

    def test_real_freshness_policy_future_current_and_expired(self):
        with calendar_clock(datetime(2026,11,7,15,tzinfo=timezone.utc)):
            self.assertIsNone(location_context.outing_problem(request('2026-11-08')))
            self.assertIsNone(location_context.outing_problem(request()))
            self.assertEqual(location_context.outing_problem(request('2026-11-06'))[0],'outing_date_expired')
            # 10am New York: exact start is valid; earlier is expired.
            self.assertIsNone(location_context.outing_problem(request(startTime=600,explicitStart=True)))
            self.assertEqual(location_context.outing_problem(request(startTime=599,explicitStart=True))[0],'outing_time_expired')
            self.assertEqual(location_context.outing_problem(request(startTime=599,explicitStart=False,endTime=600,explicitEnd=True))[0],'outing_time_expired')
            self.assertIsNone(location_context.outing_problem(request(startTime=599,explicitStart=False,endTime=601,explicitEnd=True)))

    def test_explicit_now_is_not_replaced_by_fixture_clock(self):
        with calendar_clock(datetime(2050,1,1,tzinfo=timezone.utc)):
            self.assertEqual(location_context.outing_problem(request())[0],'outing_date_expired')
            self.assertIsNone(location_context.outing_problem(request(),now=FIXTURE_NOW))
        with calendar_clock():
            self.assertEqual(location_context.outing_problem(request(),now=datetime(2050,1,1,tzinfo=timezone.utc))[0],'outing_date_expired')

    def test_relative_dates_weekday_and_cross_timezone_midnight(self):
        for instant,city,expected in [(datetime(2026,11,1,20,tzinfo=timezone.utc),'Hyderabad','2026-11-03'),
                                     (datetime(2026,11,1,20,tzinfo=timezone.utc),'New York','2026-11-02')]:
            with calendar_clock(instant):
                result=resolve_datetime('tomorrow',[],[],city,now=location_context.datetime.now(timezone.utc))
                self.assertEqual(result.date.isoformat(),expected)
                self.assertFalse(result.issues)
        with calendar_clock():
            result=resolve_datetime('Saturday November 7, 2026',[],[],'New York',now=location_context.datetime.now(timezone.utc))
            self.assertEqual((result.date.isoformat(),result.date.weekday()),('2026-11-07',5))

    def test_dst_offsets_fold_and_nonexistent_time_are_not_flattened(self):
        zone=ZoneInfo('America/New_York')
        for hour,offset,fold in [(5,-4,0),(6,-5,1)]:
            with calendar_clock(datetime(2026,11,1,hour,30,tzinfo=timezone.utc)):
                local=location_context.datetime.now(zone)
                self.assertEqual((local.hour,local.minute,local.utcoffset(),local.fold),
                                 (1,30,timedelta(hours=offset),fold))
        with calendar_clock():
            result=resolve_datetime('2027-03-14 at 2:30 AM',[],[],'New York',now=location_context.datetime.now(timezone.utc))
            self.assertTrue(result.issues)

    def test_ttl_quota_and_billing_clocks_are_not_frozen(self):
        from backend import provider_budget,option_sessions,development_cost
        original=(provider_budget.monotonic,option_sessions.monotonic,development_cost.time)
        with calendar_clock():
            self.assertEqual(original,(provider_budget.monotonic,option_sessions.monotonic,development_cost.time))
            sessions=option_sessions.OptionSessions()
            with patch('backend.option_sessions.Timer'),patch('backend.option_sessions.monotonic',return_value=0):token=sessions.create({})
            with patch('backend.option_sessions.monotonic',return_value=599.999):
                self.assertEqual(sessions.get(token)[0],{})
            with patch('backend.option_sessions.monotonic',return_value=600):
                with self.assertRaisesRegex(Exception,'expired'):sessions.get(token)

    def test_testcase_cleanup_restores_clock_after_failure(self):
        original=location_context.datetime
        class DeliberateFailure(unittest.TestCase):
            def runTest(case):
                case.enterContext(calendar_clock())
                case.fail('intentional nested fixture cleanup test')
        result=unittest.TestResult();DeliberateFailure().run(result)
        self.assertEqual(len(result.failures),1)
        self.assertIs(location_context.datetime,original)

    def test_route_creation_and_reuse_share_clock_but_expiry_still_enforced(self):
        from backend import routes
        original=routes.datetime
        with route_evidence_clock():
            leg=routes._leg(routes.RoutePoint(id='a',place_id='Synthetic_A'),
                routes.RoutePoint(id='b',place_id='Synthetic_B'),'drive',status='ok',
                duration_seconds=60.0,duration_minutes=1.0,distance_meters=100)
            self.assertEqual(leg.observed_at,FIXTURE_NOW)
            self.assertTrue(routes.current_evidence(leg,'drive'))
        for age,accepted in [(-1,False),(0,True),(299.999,True),(300,False),(301,False)]:
            with route_evidence_clock(FIXTURE_NOW+timedelta(seconds=age)):
                self.assertEqual(routes.current_evidence(leg,'drive'),accepted,age)
        self.assertIs(routes.datetime,original)
