"""Offline network projection of the existing owner-enrolled compiler. No apply.

Observed identities are metadata, not authorization. Fresh read-only preflight
and separate owner approval are required before either rendered batch executes.
"""
import argparse
import ipaddress
import json
import shlex
from pathlib import Path
from deployment.hosting_batch import published_config, RECEIPTS
from deployment.publication_batch import enrolled_plan
from deployment.cloud_run_real import ROOT, original

OBSERVATION = ROOT / "deployment/cloud-run/network-storage-observation-v1.json"
FOUNDATION = ROOT / "deployment/cloud-run/foundation-enrollment-complete-v1.json"

def verify_inputs():
    record = original.read(ROOT/"deployment/cloud-run/network-storage-inputs-v1.json")
    for name, expected in record["filesSHA256"].items():
        f = ROOT/name
        if f.is_symlink() or original.sha(f.read_bytes()) != expected:
            raise ValueError("Reviewed preparation source changed: " + name)

def configuration(observation):
    o = observation
    if (o["project"], o["region"], o["baselineCommit"]) != (original.PROJECT, original.REGION, "61de32e04845a995ce5c09d91ed347496a39d611"):
        raise ValueError("Observed target/source mismatch")
    if not o["targetNetworkNamesAbsent"] or any(o[k] != 0 for k in ("routers", "reservedAddresses", "peerings", "VPNTunnels", "RunServices", "cloudMutations")):
        raise ValueError("Network/dependency inventory requires fresh review")
    if not o["EditorRemediationPreserved"] or not o["repositoryPrivateCohortPreserved"] or o["secretContainers"] != 6:
        raise ValueError("Completed foundation drift")
    c = published_config()
    subnet = ipaddress.ip_network(o["proposedSubnetCidr"], strict=True)
    if str(subnet) != "10.92.0.0/26" or o["overlapWithObservedGCPRanges"]:
        raise ValueError("Reviewed subnet identity")
    for value in o["existingSubnetRanges"] + o["existingNonDefaultRoutes"]:
        if subnet.overlaps(ipaddress.ip_network(value, strict=True)):
            raise ValueError("Observed range overlap")
    accounts = original.read(FOUNDATION)["independentFinalVerification"]["workloadAccounts"]
    if set(o["existingWorkloads"]) != set(original.ROLES):
        raise ValueError("Six observed workload identities required")
    for role in original.ROLES:
        actual = o["existingWorkloads"][role]
        expected = accounts[role]
        if actual != {"email": original.sa(role), "subject": expected["uniqueId"]} or not expected["enabled"] or expected["userManagedKeys"]:
            raise ValueError("Observed immutable workload mismatch")
        c["workloads"][role]["subject"] = actual["subject"]
    c["subnetCidr"] = str(subnet)
    original.validate(c)
    return c

def prepare(owner_directory, observation=None):
    o = original.read(OBSERVATION) if observation is None else observation
    c = configuration(o)
    artifacts = {r: ((RECEIPTS/(r+".manifest.json")).read_bytes(), (RECEIPTS/(r+".config.json")).read_bytes()) for r in original.ROLES}
    p = enrolled_plan(c, owner_directory, artifacts)
    commands = p["networkCommandsForReviewOnly"]
    if len(commands) != 5 or any(v["commandForReviewOnly"] is not None for v in p["roles"].values()):
        raise ValueError("Finite network-only projection required")
    return {"identity": "53-network-storage-preparation-v1", "provisioningAuthorized": False,
            "configuration": c, "observationSHA256": original.sha(OBSERVATION.read_bytes()),
            "sourceBuild": p["sourceBuild"], "observedAtUTC": o["observedAtUTC"],
            "batchesForSeparateApproval": {"N1": commands[:2], "N2": commands[2:]},
            "runtimeCommands": 0, "completedFoundationCommands": 0, "publicationCommands": 0,
            "storageFindings": original.storage_findings(c["storage"]), "blockers": p["blockers"],
            "externalRangesNotVerified": True, "securityAccepted": False,
            "costCeilingApproved": False, "storageAccountQuoteVerified": False}

def render(plan, batch, owner_directory):
    if batch not in ("N1", "N2"):
        raise ValueError("Exact N1 or N2 required")
    lines = ["#!/bin/sh", "set -eu", "# REVIEW ONLY. Separate owner authorization AND fresh cloud preflight required.",
             "# Stop on error; no automatic retry/resume. Do not replay completed commands.",
             "# N2 requires N1 completion; reserved IPv4 starts recurring charges.",
             "export CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API=false",
             "export CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK=true",
             "cd " + shlex.quote(str(ROOT)),
             shlex.join([str(ROOT/"backend/.venv/bin/python"), "-m", "deployment.network_storage", str(Path(owner_directory).resolve()), "--check"])]
    lines += [shlex.join(["/opt/homebrew/bin/gcloud", *argv[1:]]) for argv in plan["batchesForSeparateApproval"][batch]]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner_directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    verify_inputs()
    p = prepare(args.owner_directory)
    if args.check:
        print(json.dumps({"verified": True, "executed": False, "networkCommands": 5, "runtimeCommands": 0}))
        return
    if args.output is None:
        parser.error("--check or --output required")
    args.output.mkdir(mode=0o700)
    for name in ("N1", "N2"):
        f = args.output/(name+".sh")
        with f.open("x") as out: out.write(render(p, name, args.owner_directory))
        f.chmod(0o700)
    with (args.output/"plan.json").open("x") as out: json.dump(p, out, indent=2, sort_keys=True)
    print(json.dumps({"rendered": True, "executed": False, "batches": ["N1", "N2"]}))

if __name__ == "__main__": main()
