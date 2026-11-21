import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from deployment import network_storage as n

class Tests(unittest.TestCase):
    def observation(self): return n.original.read(n.OBSERVATION)
    def plan(self):
        rec=n.original.read(n.RECEIPTS/"images.json")["actualRegistryReceipts"]
        approved={"images":{r:"sha256:"+v["indexSHA256"] for r,v in rec.items()},"configDigests":{r:v["actualConfigDigest"] for r,v in rec.items()},"securityDecisionSHA256":"a"*64}
        with patch("deployment.publication_batch.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout=json.dumps(approved))):
            return n.prepare("/tmp/FICTIONAL-owner")
    def test_observed_subjects_and_published_images(self):
        c=n.configuration(self.observation())
        for role,w in c["workloads"].items():
            self.assertEqual(w["subject"],self.observation()["existingWorkloads"][role]["subject"])
            self.assertEqual(w["registryManifest"],n.original.sha((n.RECEIPTS/(role+".manifest.json")).read_bytes()))
            self.assertTrue(all(v is None for v in w["secretVersions"].values()))
    def test_wrong_identity(self):
        o=self.observation();o["existingWorkloads"]["factory"]["subject"]="100000000000000000000"
        with self.assertRaisesRegex(ValueError,"workload"): n.configuration(o)
    def test_wrong_target_and_source(self):
        for key in ("project","region","baselineCommit"):
            o=self.observation();o[key]="WRONG"
            with self.assertRaises(ValueError): n.configuration(o)
    def test_overlap_even_if_claimed_safe(self):
        for key in ("existingSubnetRanges","existingNonDefaultRoutes"):
            o=self.observation();o[key].append("10.92.0.0/24")
            with self.assertRaisesRegex(ValueError,"overlap"): n.configuration(o)
    def test_no_unreviewed_cidr(self):
        o=self.observation();o["proposedSubnetCidr"]="10.93.0.0/26"
        with self.assertRaises(ValueError): n.configuration(o)
    def test_existing_resources_require_review(self):
        for key in ("routers","reservedAddresses","peerings","VPNTunnels","RunServices","cloudMutations"):
            o=self.observation();o[key]=1
            with self.assertRaises(ValueError): n.configuration(o)
    def test_completed_foundation_drift(self):
        for key in ("EditorRemediationPreserved","repositoryPrivateCohortPreserved","targetNetworkNamesAbsent"):
            o=self.observation();o[key]=False
            with self.assertRaises(ValueError): n.configuration(o)
    def test_only_original_five_network_commands(self):
        p=self.plan();c=p["configuration"]
        # Independently assert the reviewed finite command scope. The old raw
        # compiler's pre-owner frontend pins intentionally cannot be repinned.
        cmd=n.original.command
        expected=[cmd("compute","networks","create","whereto-staging","--subnet-mode=custom"),
                  cmd("compute","networks","subnets","create","whereto-staging","--network=whereto-staging","--region=us-east4","--range=10.92.0.0/26","--enable-private-ip-google-access"),
                  cmd("compute","addresses","create","whereto-staging-egress","--region=us-east4"),
                  cmd("compute","routers","create","whereto-staging","--network=whereto-staging","--region=us-east4"),
                  cmd("compute","routers","nats","create","whereto-staging","--router=whereto-staging","--region=us-east4","--nat-all-subnet-ip-ranges","--nat-external-ip-pool=whereto-staging-egress")]
        self.assertEqual(p["batchesForSeparateApproval"]["N1"],expected[:2])
        self.assertEqual(p["batchesForSeparateApproval"]["N2"],expected[2:])
        self.assertEqual(len(expected),5)
        self.assertTrue(all(x[:2]==["gcloud","compute"] for x in expected))
    def test_no_startup_storage_or_cost_approval(self):
        p=self.plan()
        for k in ("provisioningAuthorized","securityAccepted","costCeilingApproved","storageAccountQuoteVerified"):self.assertFalse(p[k])
        self.assertEqual(p["runtimeCommands"],0);self.assertTrue(p["storageFindings"])
        self.assertEqual(p["completedFoundationCommands"],0);self.assertEqual(p["publicationCommands"],0)
    def test_signed_proof_required(self):
        with self.assertRaises(ValueError): n.prepare("/tmp/NO-OWNER-PROOF")
    def test_shell_and_scope(self):
        for batch in ("N1","N2"):
            text=n.render(self.plan(),batch,"/tmp/FICTIONAL-owner")
            self.assertEqual(subprocess.run(["sh","-n"],input=text,text=True,capture_output=True).returncode,0)
            self.assertIn("--check",text)
            for forbidden in ("services enable","service-accounts create","secrets create","run deploy","allUsers","docker ","versions add","--nat-auto-allocate-nat-external-ips"):
                self.assertNotIn(forbidden,text)
        with self.assertRaises(ValueError):n.render(self.plan(),"ALL","/tmp/FICTIONAL-owner")
    def test_preparation_source_binding(self):
        n.verify_inputs()
        with patch.object(n.original, "sha", return_value="0"*64):
            with self.assertRaisesRegex(ValueError,"source changed"): n.verify_inputs()
    def test_capacity_sql_is_readonly_metadata_only(self):
        text=(n.ROOT/"deployment/sql/hosted-capacity-readonly-v1.sql").read_text().upper()
        self.assertIn("BEGIN TRANSACTION READ ONLY",text);self.assertTrue(text.rstrip().endswith("ROLLBACK;"))
        for forbidden in ("CREATE ","ALTER ","DROP ","INSERT ","UPDATE ","DELETE ","PG_AUTHID","QUERY,"):
            self.assertNotIn(forbidden,text)
