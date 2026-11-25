"""Offline command/source guards. No genuine key, cloud or database access."""
from pathlib import Path
import json,unittest
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def test_dump_stdout_and_no_unsafe_scope(self):
        v=json.loads((ROOT/'deployment/cloud-run/b1-application-backup-PROPOSED-v2.json').read_bytes())
        args=v['export']['pgDumpArgv']
        self.assertNotIn('--file=-',args);self.assertIn('--schema=whereto',args)
        self.assertFalse(any(a.startswith('--file') for a in args))
        for a in ('--enable-row-security','--no-owner','--no-acl','--disable-triggers'):self.assertNotIn(a,args)
        self.assertFalse(v['executionAuthorized']);self.assertFalse(v['key']['created']);self.assertFalse(v['offSite']['folderCreated'])
    def test_semantic_acl_preserves_all_security_dimensions(self):
        text=(ROOT/'deployment/sql/b1-application-baseline-readonly-v2.sql').read_text()
        for term in ('aclexplode','acldefault','a.grantor','a.grantee','a.privilege_type','a.is_grantable','c.relrowsecurity','c.relforcerowsecurity'):self.assertIn(term,text)
        self.assertTrue((ROOT/'deployment/sql/b1-application-baseline-readonly-v1.sql').exists())
    def test_fixture_is_cache_only_and_network_isolated(self):
        text=(ROOT/'deployment/check_b1_fixture.py').read_text()
        for term in ("'--pull=never'","'--network','none'","'--read-only'","'--tmpfs'"):self.assertIn(term,text)
        self.assertNotIn('.env.database',text);self.assertNotIn('.env.persistence',text)
