"""Offline source/projection checks; no database, credentials or provider I/O."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import unittest
from . import profile

class ProfileTests(unittest.TestCase):
    def test_source_manifest_and_reproducible_output(self):
        self.assertEqual(profile.verify()['baseline'],'a964ccce7d4fdf81b39cb05a68575abaa309c933')
        self.assertEqual(profile.scripts(),profile.scripts())
        self.assertEqual(profile.contracts(),profile.contracts())
    def test_source_substitution_refuses(self):
        original=Path.read_bytes;target=profile.PARENT/'application_grants.sql'
        def altered(path):return b'-- changed\n'+original(path) if path==target else original(path)
        with patch.object(Path,'read_bytes',altered),self.assertRaises(ValueError):profile.verify()
    def test_parent_projection_cannot_drift_silently(self):
        with self.assertRaises(ValueError):profile.replace('different parent','expected','replacement')
        with self.assertRaises(ValueError):profile.replace('x x','x','replacement')
    def test_installers_do_not_issue_grants_prices_or_epochs(self):
        for text in profile.scripts().values():
            self.assertNotIn('INSERT INTO provider_rules.configuration',text)
            self.assertNotIn("'fictional-reviewed-real-profile-v1'",text)
            self.assertNotIn('whereto_synthetic_',text)
        op=profile.scripts()['operational']
        self.assertIn("REVOKE ALL ON FUNCTION provider_state.approve_requests",op)
        self.assertIn('REVOKE EXECUTE ON FUNCTION provider_state.app_count_input',op)
    def test_count_and_generation_authority_are_distinct(self):
        text=(profile.HERE/'counter_witness.sql').read_text()
        self.assertIn("q#>>'{lines,0,kind}' IS DISTINCT FROM 'count'",text)
        self.assertIn("q->'charge' IS DISTINCT FROM '0'::jsonb",text)
        self.assertIn('real_counter_witness',text)
        self.assertNotIn("'operator'",text)
    def test_hosted_contract_measures_new_schema_and_rejects_clock(self):
        for text in profile.contracts().values():
            self.assertIn('52-real-hosted-storage-contract-v1',text)
            self.assertIn('provider_rules',text)
            self.assertIn('test_clock',text)
        self.assertIn('sourceBuild',profile.contracts()['operational'])
    def test_historical_token_count_is_not_application_input(self):
        for name in ('rules.sql','counter.sql','runtime.py','profile.py'):
            self.assertNotIn('5704',(profile.HERE/name).read_text())
        text=(profile.HERE/'runtime.py').read_text()
        self.assertIn("statement_timeout='1500ms'",text)
        self.assertIn("lock_timeout='250ms'",text)

if __name__=='__main__':unittest.main()
