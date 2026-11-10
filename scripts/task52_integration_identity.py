"""Pinned offline integration for security review."""
import json

from scripts import task52_diag_identity as diagnostic
from scripts import task52_q1 as q1
from scripts import task52_q4d_identity as q4d

IDENTITY = "52b-v51-original-journal-integration-preparation-offline-v1"
MANIFEST = q1.ROOT / "docs/task52-real-integration-build-v1.json"
MANIFEST_SHA = "6c7e93fdefa6d726b4be7d8e5da5d24c5d4cdc5b6652ff254767b14bf8f793ac"


def verify():
    if q1.sha(MANIFEST.read_bytes()) != MANIFEST_SHA:
        raise ValueError("Unknown integration build")
    manifest = json.loads(MANIFEST.read_text())
    if (
        manifest["identity"] != IDENTITY
        or manifest["syntheticWritesOnly"] is not True
        or manifest["liveDispatchAvailable"] is not False
        or manifest["financialAuthorization"] is not False
        or manifest["diagnosticBuildSHA256"] != diagnostic.MANIFEST_SHA
        or manifest["q4dBuildSHA256"] != q4d.MANIFEST_SHA
    ):
        raise ValueError("Integration purpose or parent mismatch")
    for path, expected in manifest["artifactHashes"].items():
        if q1.sha((q1.ROOT / path).read_bytes()) != expected:
            raise ValueError("Integration source or evidence mismatch")
    diagnostic.verify()
    return manifest
