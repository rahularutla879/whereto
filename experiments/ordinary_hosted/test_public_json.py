from unittest import TestCase
from experiments.ordinary_hosted.public_json import decode
class PublicJSONTests(TestCase):
 def test_whitespace_and_key_order_are_public_syntax_not_evidence_rewrites(self):
  self.assertEqual(decode(b'{ "text" : "Coffee", "answers":{} }'),{'text':'Coffee','answers':{}})
 def test_duplicates_nonfinite_depth_and_malformed_inputs_refuse(self):
  for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]',b'{} trailing',b'{"x":'+b'['*34+b'0'+b']'*34+b'}'):
   with self.assertRaises(ValueError):decode(raw)
