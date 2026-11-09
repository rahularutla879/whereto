"""Test-only Phase B runtime identity verification; no dispatch/runtime hooks."""
import json
from pathlib import Path
from scripts import task52_version_review as history

MANIFEST=history.ROOT/'docs/task52-runtime-phase-b1.json'
MANIFEST_SHA='bba7caeab233f515d038a84c42842cbd20e37c13be64e8d2cd2da1b992b7d5a9'
RUNTIME='52b-runtime-phase-b1'
PURPOSES={'preparation_observation','legacy_ordinary','legacy_advanced_handoff'}


def verify(*, runtime=RUNTIME, purpose='preparation_observation'):
    try:raw=MANIFEST.read_bytes()
    except OSError:raise history.VersionError() from None
    if (history.sha(raw)!=MANIFEST_SHA or runtime!=RUNTIME or
            type(purpose) is not str or purpose not in PURPOSES):raise history.VersionError()
    data=json.loads(raw)
    if (data['format']!='52b-runtime-identity-v2' or data['runtimeIdentity']!=runtime
            or set(data['allowedInternalPurposes'])!=PURPOSES):raise history.VersionError()
    history.verify('52b-historical-evaluator-b04','historical_evaluator')
    if data['historicalManifestSHA256']!=history.MANIFEST_SHA:raise history.VersionError()
    paths=history.git('ls-files','--cached','--others','--exclude-standard').decode().splitlines()
    try:
        if history.source_root(paths,lambda p:(history.ROOT/p).read_bytes())!=data['implementationRootSHA256']:
            raise history.VersionError()
        for p,expected in data['sourceHashes'].items():
            if history.sha((history.ROOT/p).read_bytes())!=expected:raise history.VersionError()
    except OSError:raise history.VersionError() from None
    from backend.ai import Interpretation
    if history.digest(Interpretation.model_json_schema())!=data['canonicalSchemaSHA256']:
        raise history.VersionError()
    from backend.source_preparation import PREPARATION_VERSION,RUNTIME_ID
    from backend.validation_phases import LEGACY_PROFILE
    if (RUNTIME_ID!=runtime or PREPARATION_VERSION!=data['preparedSourceTypeVersion']
            or LEGACY_PROFILE!=data['semanticPolicy']):raise history.VersionError()
    return {'runtime':runtime,'purpose':purpose,'verified':True,'planningAuthorized':False,
            'historicalSourceEqualityClaimed':False}
