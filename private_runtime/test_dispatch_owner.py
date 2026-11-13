import unittest
from unittest.mock import patch
from private_runtime.dispatch_owner import Owner,DispatchOwner,OwnerRouter
from experiments.shared_state.contracts import Denied
class Tests(unittest.TestCase):
 def setUp(self):self.enrollment=Owner('factory-r1','1'*64,'2'*64);self.owner=DispatchOwner(self.enrollment)
 def test_requires_native_action_and_exact_live_admission(self):
  with self.assertRaises(Denied),self.owner.permit('op',1,b'wire',lambda:None):pass
  checks=[]
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:checks.append(True)) as p:
   self.assertTrue(self.owner.check(p)['current']);self.assertEqual(checks,[True])
   with self.assertRaises(Denied):self.owner.check(p)
 def test_no_mutation_or_transfer(self):
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as p:
   for name in p:
    with self.assertRaises(Denied):self.owner.check({**p,name:'forged'})
   self.assertTrue(self.owner.check(p)['current'])
 def test_restarted_process_cannot_recreate_callback(self):
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as p:
   other=DispatchOwner(self.enrollment)
   with self.assertRaises(Denied):other.check(p)
 def test_expiry_and_cancelled_admission_refuse(self):
  with patch('private_runtime.dispatch_owner.monotonic',return_value=100),self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as p:
   with patch('private_runtime.dispatch_owner.monotonic',return_value=105),self.assertRaises(Denied):self.owner.check(p)
  def cancelled():raise Denied('admission_lost')
  with self.owner.action(),self.owner.permit('op',1,b'wire',cancelled) as p:
   with self.assertRaises(Denied):self.owner.check(p)
   with self.assertRaises(Denied):self.owner.check(p)
 def test_router_uses_only_approved_slot_principal_and_exact_result(self):
  class C:
   def request(_,target,path,value):return self.owner.check(value)
  r=OwnerRouter({'factory-r1':self.enrollment},C())
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as p:
   for key in ('owner','epoch','build'):
    with self.assertRaises(Denied):r.check({**p,key:'unreviewed'},'factory-r1')
   with self.assertRaises(Denied):r.check(p,'factory-r2')
   r.check(p,'factory-r1')
 def test_drain_cancels_remaining_permits_and_refuses_new_actions(self):
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as p:
   self.assertFalse(self.owner.drain(0))
   with self.assertRaises(Denied):self.owner.check(p)
  with self.assertRaises(Denied),self.owner.action():pass
 def test_competing_callback_consumption_is_single_use(self):
  from concurrent.futures import ThreadPoolExecutor
  def attempt(value):
   try:self.owner.check(value);return 'accepted'
   except Denied:return 'refused'
  with self.owner.action(),self.owner.permit('op',1,b'wire',lambda:None) as permit:
   with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(attempt,[permit,permit]))
  self.assertEqual(sorted(results),['accepted','refused'])
if __name__=='__main__':unittest.main()
