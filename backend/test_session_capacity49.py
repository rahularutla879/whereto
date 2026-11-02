"""Retain admitted active searches without raising provider budgets or lifetime."""
import unittest
from unittest.mock import patch
from backend.option_sessions import OptionSessions,MAX_ACTIVE_SESSIONS
from backend.places import DiscoveryError

class SessionRetention(unittest.TestCase):
 def test_repeated_testing_retains_thirty_then_bounds_fifty_and_expires_at_ten_minutes(self):
  clock=[1000.0]
  with patch('backend.option_sessions.Timer') as timer,patch('backend.option_sessions.monotonic',side_effect=lambda:clock[0]),patch('requests.Session.send',side_effect=AssertionError('Retention must not dispatch')):
   registry=OptionSessions();tokens=[registry.create({'fixture':i}) for i in range(30)]
   self.assertEqual(registry.get(tokens[0])[0],{'fixture':0})
   self.assertEqual(len(registry.entries),30)
   tokens.extend(registry.create({'fixture':i}) for i in range(30,MAX_ACTIVE_SESSIONS))
   self.assertEqual(len(registry.entries),50)
   self.assertEqual(registry.get(tokens[0])[0],{'fixture':0})
   newest=registry.create({'fixture':'newest'})
   self.assertEqual(len(registry.entries),50)
   with self.assertRaises(DiscoveryError):registry.get(tokens[0])
   self.assertEqual(registry.get(tokens[1])[0],{'fixture':1})
   self.assertEqual(registry.get(newest)[0],{'fixture':'newest'})
   self.assertEqual(timer.call_args.args[0],600)
   clock[0]+=600
   with self.assertRaises(DiscoveryError):registry.get(newest)
