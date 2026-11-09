"""Test-only B2 preflight; intentionally NO historical-code execution path.

Source/version equality is not artifact/environment reproducibility. The retained
manifests lack an approved execution-environment artifact lock. Refuse execution
instead of importing current packages as if they were historical dependencies.
No credentials, journal, network, installs, checkouts or executable snapshots.
"""
from pathlib import Path
import importlib.metadata
import json
import re
import sys

from scripts import task52_version_review as history

HISTORICAL_ID='52b-historical-evaluator-b04'
B1_ID='52b-runtime-phase-b1'
B1_MANIFEST=history.ROOT/'docs/task52-runtime-phase-b1.json'
B1_MANIFEST_SHA='bba7caeab233f515d038a84c42842cbd20e37c13be64e8d2cd2da1b992b7d5a9'
# No historically approved artifact lock exists in either retained manifest.
# This tuple must not be populated from current env files or caller JSON.
APPROVED_EXECUTION_ENVIRONMENTS=()


class HistoricalReplayBlocked(RuntimeError):
    def __init__(self):
        super().__init__('Historical replay blocked: exact execution environment and isolation are not verified.')


def requirement_pins(raw):
    result={}
    for line in raw.decode().splitlines():
        match=re.fullmatch(r'([A-Za-z0-9_-]+)(?:\[[A-Za-z0-9_, -]+\])?==([A-Za-z0-9.+_-]+)',line)
        if not match:raise history.VersionError()
        name=match[1].lower().replace('_','-')
        if name in result:raise history.VersionError()
        result[name]=match[2]
    return result


def version_comparison(pins, installed):
    # Metadata lookup only; no dependency modules are imported for this audit.
    rows=[]
    for name,expected in sorted(pins.items()):
        try:actual=installed(name)
        except importlib.metadata.PackageNotFoundError:actual=None
        rows.append({'distribution':name,'requiredVersion':expected,
                     'installedVersion':actual,'matches':actual==expected})
    return rows


def audit():
    checked=history.verify(HISTORICAL_ID,'historical_evaluator')
    retained=history.identity(HISTORICAL_ID,'historical_evaluator')
    b1raw=B1_MANIFEST.read_bytes()
    if history.sha(b1raw)!=B1_MANIFEST_SHA:raise history.VersionError()
    b1=json.loads(b1raw)
    # Read exactly the source snapshot selected by the original manifest.
    req=history.git('show',retained['gitCommit']+':backend/requirements.txt')
    if history.sha(req)!=b1['sourceHashes']['backend/requirements.txt']:
        raise history.VersionError()
    rows=version_comparison(requirement_pins(req),importlib.metadata.version)
    return {'version':'52b-historical-execution-preflight-v1',
            'historicalIdentity':checked,'comparisonBaselineRuntimeIdentity':B1_ID,
            'historicalGitCommit':retained['gitCommit'],'historicalGitTree':retained['gitTree'],
            'corpusSHA256':retained['corpusSHA256'],'sixPins':retained['originalSixPins'],
            'b1ManifestSHA256':B1_MANIFEST_SHA,
            'schemaSHA256RecordedInB1':b1['canonicalSchemaSHA256'],
            'requirementsSHA256':history.sha(req),'dependencyVersions':rows,
            'allPinnedVersionsMatch':all(r['matches'] for r in rows),
            'currentPythonVersion':sys.version.split()[0],
            'b1PythonVersion':b1['buildIdentity']['python'],
            'pythonVersionMatchesB1':sys.version.split()[0]==b1['buildIdentity']['python'],
            'historicalArtifactEnvironmentVerified':False,
            'approvedExecutionEnvironmentCount':len(APPROVED_EXECUTION_ENVIRONMENTS),
            'blockers':['missing_approved_historical_interpreter_and_dependency_artifact_lock',
                        'historical_execution_confinement_not_verified'],
            'historicalCodeExecuted':False,'runtimeExtractionPermitted':False,
            'dependencyInstallationAttempted':False,'providerRequests':0,
            'paidJournalAccessedByThisTool':False}


def require_execution_ready():
    # Fail closed for every current snapshot. No force/current-deps/skip flag.
    result=audit()
    if not APPROVED_EXECUTION_ENVIRONMENTS or not result['historicalArtifactEnvironmentVerified']:
        raise HistoricalReplayBlocked()
    # No executor is implemented behind an unverified gate.
    raise HistoricalReplayBlocked()


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
    raise SystemExit(2)  # blocked, never a successful replay exit code
