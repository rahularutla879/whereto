import json
import subprocess
import unittest
from unittest.mock import patch
from deployment import hosting_batch as h

class Tests(unittest.TestCase):
    def plan(self):
        # Fictional signature-port result only; actual manifest/config/source verification runs.
        from types import SimpleNamespace
        record=json.loads((h.RECEIPTS / "images.json").read_text())
        approved={"images": {r:"sha256:"+v["indexSHA256"] for r,v in record["actualRegistryReceipts"].items()}, "configDigests": {r:v["actualConfigDigest"] for r,v in record["actualRegistryReceipts"].items()}, "securityDecisionSHA256": "a"*64}
        with patch("deployment.publication_batch.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout=json.dumps(approved))):
            return h.prepare("/tmp/FICTIONAL-owner")
    def test_all_six_actual_leaf_digests(self):
        c=h.published_config()
        for role,w in c["workloads"].items():
            self.assertEqual(w["registryManifest"],h.original.sha((h.RECEIPTS/(role+".manifest.json")).read_bytes()))
            self.assertIsNone(w["subject"])
            self.assertTrue(all(v is None for v in w["secretVersions"].values()))
    def test_foundation_has_no_runtime_or_repeat_publication(self):
        p=self.plan(); commands=p["foundationCommandsForSeparateApproval"]
        self.assertEqual(sum(x[1:4]==["iam","service-accounts","create"] for x in commands),6)
        self.assertEqual(sum(x[1:3]==["secrets","create"] for x in commands),6)
        self.assertEqual(sum(x[1:3]==["secrets","add-iam-policy-binding"] for x in commands),6)
        self.assertEqual(len(commands),22)
        self.assertTrue(all("--project=where-to-512422" in x for x in commands))
        self.assertNotIn("publicationForReviewOnly",p)
        for x in commands:
            self.assertNotEqual(x[1],"run")
            self.assertNotIn("allUsers"," ".join(x))
            self.assertNotIn("versions",x)
            self.assertNotIn("compute",x)
        self.assertEqual(commands[0][3:6],list(h.APIS))
    def test_missing_enrollment_still_blocks_every_service(self):
        p=self.plan()
        self.assertFalse(p["releaseEligible"]);self.assertFalse(p["provisioningAuthorized"])
        self.assertFalse(p["foundationAuthorized"])
        self.assertTrue(p["blockers"])
        self.assertTrue(all(v["commandForReviewOnly"] is None for v in p["roles"].values()))
    def test_signature_still_required(self):
        with self.assertRaises(ValueError):h.prepare("/tmp/NO-OWNER-TRUST")
    def test_shell_syntax_and_no_substitution_or_apply(self):
        text=h.render_foundation(self.plan(),"/tmp/FICTIONAL-owner")
        check=subprocess.run(["sh","-n"],input=text,text=True,capture_output=True)
        self.assertEqual(check.returncode,0,check.stderr)
        self.assertIn("--check",text)
        for forbidden in ("docker ","run deploy","secrets versions","allUsers","eval ","serviceusage.serviceUsageConsumer"):
            self.assertNotIn(forbidden,text)
    def test_receipt_record_substitution_refuses(self):
        real=h.original.read
        def read(path):
            value=real(path)
            if Path(path).name=="images.json":value["actualRegistryReceipts"]["frontend"]["referenceByAMD64Manifest"]+="BAD"
            return value
        from pathlib import Path
        with patch.object(h.original,"read",side_effect=read):
            with self.assertRaises(ValueError):h.published_config()
