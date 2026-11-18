"""Pure offline first-slot payload and nanodollar tests; no credentials/I/O port."""
import unittest
from scripts import task52b_generation_policy as p

class PolicyTests(unittest.TestCase):
 def test_frozen_payload_and_standard_bound(self):
  self.assertEqual(p.digest(p.payload()),p.PAYLOAD_SHA)
  result=p.quote(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':0},0)
  self.assertEqual((result['inputBound'],result['maxOutputTokens'],result['maximumNanodollars'],result['approved']),(7752,2000,1969000,False))
 def test_original_ceiling_and_upward_rounding(self):
  fees={'tools':0,'separate_reasoning':0,'other_fees':0}
  self.assertEqual(p.quote(9952,p.RATES,fees,0)['maximumNanodollars'],2500000)
  self.assertEqual(p.quote(5704,p.RATES,fees,1)['premiumNanodollars'],197)
  with self.assertRaises(p.Refused):p.quote(9952,p.RATES,fees|{'other_fees':1},0)
 def test_unknown_fees_prices_and_output_cannot_authorize(self):
  fees={'tools':0,'separate_reasoning':0,'other_fees':0}
  for count,rates,extra,premium in [(True,p.RATES,fees,0),(5704,p.RATES|{'output':1},fees,0),(5704,p.RATES,fees|{'other_fees':None},0),(5704,p.RATES,fees,None),(9953,p.RATES,fees,0)]:
   with self.subTest(count=count,premium=premium):
    with self.assertRaises(p.Refused):p.quote(count,rates,extra,premium)
  with self.assertRaises(p.Refused):p.quote(5704,p.RATES,fees,0,output=2001)
