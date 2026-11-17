import unittest,json,os
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from deployment import prepare_zlib_candidate as c

class ZlibCandidateTests(unittest.TestCase):
    def test_exact_single_package_dockerfile_stages_and_guards(self):
        m=json.loads((c.DIRECTORY/'security-package.json').read_text())
        for name,var,ref in [('Dockerfile.private-service','PYTHON_IMAGE','python:test'),('Dockerfile.frontend-private','NODE_IMAGE','node:test')]:
            text=c.dockerfile((c.ROOT/'deployment'/name).read_text(),var,ref,m)
            self.assertEqual(text.count('dpkg -i'),1);self.assertEqual(text.count('FROM security_base AS '),2)
            self.assertIn('sha256sum -c -',text);self.assertIn('debian:13',text)
            self.assertNotIn('apt-get upgrade',text);self.assertIn(c.FIXED,text)
            self.assertIn('USER ',text)
    def test_altered_archive_refuses_before_projection(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.deb';p.write_bytes(b'fictional invalid archive, never installed')
            with self.assertRaises(ValueError):c.prepare(Path(tmp)/'output',p)
            self.assertFalse((Path(tmp)/'output').exists())
    @unittest.skipUnless(os.environ.get('TASK52_SECURITY_DEB'),'verified external Debian package required; no automatic download')
    def test_source_and_policy_unchanged_new_build_identity(self):
        m=c.package(os.environ['TASK52_SECURITY_DEB'])
        original=(c.ROOT/'deployment/private-role-cohort-v1.json').read_bytes()
        with TemporaryDirectory() as tmp:
            out=Path(tmp)/'candidate';build=c.prepare(out,os.environ['TASK52_SECURITY_DEB'])
            new=(out/'roles/cohort.json').read_bytes();cohort=json.loads(new)
            self.assertEqual(cohort['outputs'],json.loads(original)['outputs'])
            self.assertNotEqual(build['cohort'],build['priorCandidateCohort'])
            self.assertEqual(sha256(new).hexdigest(),build['cohort']);self.assertFalse(build['promotionApproved'])
            self.assertFalse(build['realProviderTransport'])
            self.assertEqual(sha256((out/'roles/security/zlib1g.deb').read_bytes()).hexdigest(),m['sha256'])
            for r in c.ROLES:self.assertEqual(json.loads((out/'roles'/r/'private-role.json').read_bytes())['cohort'],build['cohort'])
        self.assertEqual((c.ROOT/'deployment/private-role-cohort-v1.json').read_bytes(),original)
