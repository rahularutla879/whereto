"""Independent process callback ownership; not a provider or accounting simulation."""
import multiprocessing as mp
import unittest
from private_runtime.dispatch_owner import Owner,DispatchOwner
from experiments.shared_state.contracts import Denied

def worker(channel):
 owner=DispatchOwner(Owner('factory-r1','1'*64,'2'*64))
 checks=[]
 with owner.action(),owner.permit('reserved-op',1,b'canonical',lambda:checks.append('admission-checked')) as permit:
  channel.send(permit)
  while True:
   command,value=channel.recv()
   if command=='stop':return
   try:channel.send(('accepted',owner.check(value),list(checks)))
   except Denied as error:channel.send(('refused',error.code))

class Tests(unittest.TestCase):
 def test_two_processes_and_killed_owner_cannot_transfer_permit(self):
  ctx=mp.get_context('spawn');resources=[]
  try:
   for _ in range(2):
    parent,child=ctx.Pipe();process=ctx.Process(target=worker,args=(child,));process.start();resources.append((process,parent));self.assertTrue(parent.poll(5))
   first,second=[pipe.recv() for _,pipe in resources]
   self.assertNotEqual(first['boot'],second['boot'])
   a,ap=resources[0];b,bp=resources[1]
   bp.send(('check',first));self.assertTrue(bp.poll(5));self.assertEqual(bp.recv()[0],'refused')
   ap.send(('check',first));self.assertTrue(ap.poll(5));reply=ap.recv();self.assertEqual(reply[0],'accepted');self.assertEqual(reply[2],['admission-checked'])
   ap.send(('check',first));self.assertTrue(ap.poll(5));self.assertEqual(ap.recv()[0],'refused')
   a.terminate();a.join(5);self.assertFalse(a.is_alive())
   bp.send(('check',first));self.assertTrue(bp.poll(5));self.assertEqual(bp.recv()[0],'refused')
   bp.send(('check',second));self.assertTrue(bp.poll(5));self.assertEqual(bp.recv()[0],'accepted')
  finally:
   for process,pipe in resources:
    if process.is_alive():process.terminate()
    process.join(5);pipe.close()
 def test_terminated_pending_owner_cannot_be_replaced(self):
  ctx=mp.get_context('spawn');resources=[]
  try:
   parent,child=ctx.Pipe();process=ctx.Process(target=worker,args=(child,));process.start();resources.append((process,parent));self.assertTrue(parent.poll(5));pending=parent.recv()
   process.terminate();process.join(5);self.assertFalse(process.is_alive())
   replacement,child=ctx.Pipe();process=ctx.Process(target=worker,args=(child,));process.start();resources.append((process,replacement));self.assertTrue(replacement.poll(5));fresh=replacement.recv()
   replacement.send(('check',pending));self.assertTrue(replacement.poll(5));self.assertEqual(replacement.recv()[0],'refused')
   replacement.send(('check',fresh));self.assertTrue(replacement.poll(5));self.assertEqual(replacement.recv()[0],'accepted')
  finally:
   for process,pipe in resources:
    if process.is_alive():process.terminate()
    process.join(5);pipe.close()
if __name__=='__main__':unittest.main()
