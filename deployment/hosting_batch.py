"""Offline projection of the existing owner-enrolled compiler. Never applies resources.

Publication is complete. Only the finite identity/empty-secret foundation is
executable after separate owner authorization; runtime enrollment stays closed.
"""
import argparse
import copy
import json
from pathlib import Path
import shlex
from deployment.publication_batch import enrolled_plan
from deployment.cloud_run_real import ROOT, original

RECEIPTS = ROOT / "deployment/candidates/registry-publication-v1"
APIS = ("run.googleapis.com", "iap.googleapis.com", "secretmanager.googleapis.com")

def published_config():
    config = copy.deepcopy(original.read(ROOT / "deployment/cloud-run/staging.example.json"))
    record = original.read(RECEIPTS / "images.json")["actualRegistryReceipts"]
    if set(record) != set(original.ROLES):
        raise ValueError("Exactly six published roles required")
    for role in original.ROLES:
        config["workloads"][role]["registryManifest"] = original.sha((RECEIPTS / (role + ".manifest.json")).read_bytes())
        expected = original.REGION + "-docker.pkg.dev/" + original.PROJECT + "/whereto-private/whereto-" + role + "@sha256:" + config["workloads"][role]["registryManifest"]
        if record[role]["referenceByAMD64Manifest"] != expected:
            raise ValueError("Published receipt changed")
    return config

def prepare(owner_directory):
    config = published_config()
    artifacts = {role: ((RECEIPTS / (role + ".manifest.json")).read_bytes(),
                        (RECEIPTS / (role + ".config.json")).read_bytes()) for role in original.ROLES}
    # Existing proof/source/OCI verifier; no secret value or private signing key.
    plan = enrolled_plan(config, owner_directory, artifacts)
    foundation = [original.command("services", "enable", *APIS)]
    for argv in plan["bootstrapCommandsForReviewOnly"]:
        if argv[1:5] == ["beta", "services", "identity", "create"] or argv[1:4] == ["iam", "service-accounts", "create"] or argv[1:4] == ["artifacts", "repositories", "add-iam-policy-binding"]:
            foundation.append(argv)
    foundation += plan["secretContainerCommandsForReviewOnly"]
    foundation += [argv for argv in plan["iamCommandsForReviewOnly"] if argv[1:3] == ["secrets", "add-iam-policy-binding"]]
    # Do not accidentally replay already-consumed publication/repository setup.
    plan.pop("publicationForReviewOnly")
    plan.pop("bootstrapCommandsForReviewOnly")
    plan["foundationCommandsForSeparateApproval"] = foundation
    plan["publicationCompleted"] = True
    plan["foundationAuthorized"] = False
    plan["configuration"] = config
    if any(v["commandForReviewOnly"] is not None for v in plan["roles"].values()):
        raise ValueError("Unknown enrollment must not produce deploy commands")
    return plan

def render_foundation(plan, owner_directory):
    lines = ["#!/bin/sh", "set -eu", "# REVIEW ONLY: owner must separately authorize this exact batch before execution.",
             "# No services, networking, secret versions, testers or provider grants. Stop on error; do not rerun blindly.",
             "cd " + shlex.quote(str(ROOT)),
             shlex.join([str(ROOT / "backend/.venv/bin/python"), "-m", "deployment.hosting_batch", str(Path(owner_directory).resolve()), "--check"])]
    lines += [shlex.join(argv) for argv in plan["foundationCommandsForSeparateApproval"]]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner_directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = prepare(args.owner_directory)
    if args.check:
        print(json.dumps({"verified": True, "executed": False, "roles": 6, "runtimeCommands": 0}))
        return
    if args.output is None:
        parser.error("--output or --check required")
    # Refuse overwrite, and keep generated approval material separate from source.
    args.output.mkdir(mode=0o700)
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    (args.output / "foundation.sh").write_text(render_foundation(plan, args.owner_directory))
    (args.output / "foundation.sh").chmod(0o700)
    print(json.dumps({"rendered": True, "executed": False, "runtimeCommands": 0}))

if __name__ == "__main__":
    main()
