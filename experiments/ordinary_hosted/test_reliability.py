"""Deterministic original-path reproduction; no deadline or frozen test changes."""
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace as N
from experiments.ordinary_hosted.stable_session import Session,Parent
class ReliabilityTests(TestCase):
 def subject(self,kind):
  s=object.__new__(kind);s.token='fixture'
  source=N(created=100.,advanced=None,options=None,details=None,execution={},value=None,raw=None,result=None,revision=1,planned_revision=0,inference=None)
  s.broker=N(_source=lambda _:source,_Broker__advanced=N(items={}),now=None,budget=None)
  s.evidence=N(clock=lambda:10000000);s.answers=[];s.receipts={};s.last=None
  return s
 def test_original_sql_wall_and_monotonic_resampling_loses_one_ms(self):
  s=self.subject(Parent)
  with patch('experiments.shared_state.native_sessions.monotonic',return_value=100.5):first=s.state()['created']
  s.evidence.clock=lambda:10000001
  with patch('experiments.shared_state.native_sessions.monotonic',return_value=100.502):second=s.state()['created']
  self.assertEqual(first,9999500);self.assertEqual(second,9999499)
 def test_adapter_retains_integer_despite_same_clock_pair_skew(self):
  s=self.subject(Session)
  with patch('experiments.shared_state.native_sessions.monotonic',return_value=100.5):first=s.state()['created']
  s.evidence.clock=lambda:10000001
  with patch('experiments.shared_state.native_sessions.monotonic',return_value=100.502):second=s.state()['created']
  self.assertEqual(second,first)
 def test_restored_protected_integer_precedes_any_resampling(self):
  s=self.subject(Session);s._created_ms=9999400
  with patch('experiments.shared_state.native_sessions.monotonic',return_value=100.5):self.assertEqual(s.state()['created'],9999400)
