"""Synthetic responder scope only; authorization is tested separately."""
import json,unittest
from private_runtime.simulation import respond
from experiments.shared_state.contracts import Denied
class Tests(unittest.TestCase):
 def search(self,**body):return respond(json.dumps({'operation':'search','body':body}).encode())
 def test_authored_coordinate_bias_and_named_fixture_city(self):
  bias={'circle':{'center':{'latitude':39.29,'longitude':-76.61},'radius':0.0}}
  self.assertEqual(len(self.search(textQuery='cafes',pageSize=3,locationBias=bias)['places']),3)
  self.assertEqual(len(self.search(textQuery='cafes in Baltimore',pageSize=3)['places']),3)
  self.assertEqual(len(self.search(textQuery='museum in Baltimore',pageSize=2)['places']),2)
  area=self.search(textQuery='Baltimore',pageSize=3)['places'];self.assertEqual(len(area),1);self.assertIn('locality',area[0]['types'])
  self.assertEqual(len(self.search(textQuery='museum',pageSize=2,locationBias={'circle':{'center':area[0]['location'],'radius':0}})['places']),2)
 def test_unknown_location_category_pagination_and_size_refuse(self):
  for value in ({'textQuery':'coffee shops'},{'textQuery':'restaurants in Baltimore'},{'textQuery':'coffee in Baltimore','pageToken':'more'},{'textQuery':'coffee in Baltimore','pageSize':11},{'textQuery':'coffee shops','locationBias':{'circle':{'center':{'latitude':0,'longitude':0},'radius':0}}}):
   with self.assertRaises(Denied):self.search(**{'pageSize':3,**value})
if __name__=='__main__':unittest.main()
