"""No Docker or external I/O; verifies the separately disabled packaging overlay."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest,json,shutil
from hashlib import sha256
from deployment import prepare_trixie_candidate as c

class CandidateTests(unittest.TestCase):
    def test_exact_patch_only_and_no_promotion(self):
        bases,changes=c.validate()
        self.assertFalse(bases['promotionApproved']);self.assertFalse(bases['realProviderTransport'])
        self.assertEqual(len(changes),11)
        self.assertEqual(json.loads((c.ROOT/'package-lock.json').read_text())['packages']['node_modules/next']['version'],'16.4.2')
    def test_projected_code_unchanged_with_new_candidate_identity(self):
        original=(c.ROOT/'deployment/private-role-cohort-v1.json').read_bytes()
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/'candidate';m=c.prepare(target)
            self.assertNotEqual(m['cohort'],m['parentCohort']);self.assertEqual(m['parentCohort'],sha256(original).hexdigest())
            parent=json.loads(original);derived=json.loads((target/'roles/cohort.json').read_bytes())
            self.assertEqual(parent['outputs'],derived['outputs'])
            self.assertFalse(derived['realProviderTransport'])
            for role in c.ROLES:
                d=target/'roles'/role;own=json.loads((d/'private-role.json').read_bytes())
                self.assertEqual(own['cohort'],m['cohort'])
                for name in own['files']:self.assertEqual(sha256((d/name).read_bytes()).hexdigest(),parent['outputs'][role+'/'+name])
            self.assertEqual((target/'frontend-bookworm-next/deployment/private-role-cohort-v1.json').read_bytes(),original)
            self.assertEqual((target/'frontend-trixie/package-lock.json').read_bytes(),(c.ROOT/'package-lock.json').read_bytes())
            with self.assertRaises(ValueError):c.prepare(target)
        self.assertEqual((c.ROOT/'deployment/private-role-cohort-v1.json').read_bytes(),original)
    def test_invalid_candidate_or_unrelated_dependency_refuses(self):
        with TemporaryDirectory() as tmp:
            d=Path(tmp)
            for p in c.CANDIDATE.glob('*.json'):shutil.copyfile(p,d/p.name)
            with patch.object(c,'CANDIDATE',d):
                base=d/'base-images.json';original=base.read_bytes();v=json.loads(original);v['promotionApproved']=True;base.write_text(json.dumps(v))
                with self.assertRaises(ValueError):c.validate()
                base.write_bytes(original)
                lock=d/'next-package-lock.json';v=json.loads(lock.read_bytes());v['packages']['node_modules/react']['version']='99.0.0';lock.write_text(json.dumps(v))
                with self.assertRaises(ValueError):c.validate()
