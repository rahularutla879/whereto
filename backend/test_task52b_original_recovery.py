"""Supplemental fresh-supervisor recovery test; same pinned adapter/fixture.

Loaded explicitly as _task52b_original_recovery_tests after the original harness;
ordinary discovery skips. No standalone enrollment or live execution entry.
"""
import unittest
OPT_IN=__name__=='_task52b_original_recovery_tests'
if OPT_IN:
 import _task52b_original_enrollment_tests as original
 import multiprocessing,os
 from scripts import task52b_original_journal as j
 from scripts import task52b_enrolled_transport as w
 from scripts import task52b_generation_policy as p
 Base=original.OriginalEnrollmentTests
else:Base=unittest.TestCase

@unittest.skipUnless(OPT_IN,'Explicit frozen-source recovery harness required')
class IndependentReplacementTests(Base):
 # Inherit fixture helpers, not the eleven existing test cases.
 def test_fresh_supervisor_after_intent_cannot_recover_send(self):
  f=self.fixture();r=self.run_case(f,'after_intent')
  self.assertEqual(r['workerExit'],73);self.assertEqual(f[2].value,0)
  receipt=f[0].receipt;bound=w.binding(f[1])
  def replacement():
   try:
    engine=j.OriginalEngine(receipt)
    transport=w.fixture_transport(receipt,bound.port,self.root/'good.pem')
    j.supervise(engine,transport)
   except (j.Denied,FileExistsError):os._exit(0)
   os._exit(99)
  process=multiprocessing.get_context('fork').Process(target=replacement)
  process.start();process.join(130)
  if process.is_alive():process.kill();process.join();self.fail('Replacement exceeded unchanged deadline')
  self.assertEqual(process.exitcode,0);self.assertEqual(f[2].value,0)
  self.assertEqual(j.independent_verify(f[0])['childExposureNanodollars'],2500000)
  self.assertEqual(p.journal_snapshot(receipt.journal.parent)['rows'][10][5],2500000)
