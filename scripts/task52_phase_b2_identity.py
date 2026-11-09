"""Offline B2 source-set identity, not historical equality or spending authority."""
import json
from scripts import task52_version_review as history

MANIFEST=history.ROOT/'docs/task52-runtime-phase-b2.json'
MANIFEST_SHA='5151423b78a7140790c3e6951c3fb64be49b6887db5b230449b7b011bca4cf14'
RUNTIME='52b-runtime-phase-b2'
PURPOSES={'preparation_observation','legacy_ordinary','legacy_advanced_handoff'}


def verify(*,runtime=RUNTIME,purpose='preparation_observation'):
    try:raw=MANIFEST.read_bytes()
    except OSError:raise history.VersionError() from None
    if history.sha(raw)!=MANIFEST_SHA or runtime!=RUNTIME or type(purpose) is not str or purpose not in PURPOSES:
        raise history.VersionError()
    data=json.loads(raw)
    if data['format']!='52b-runtime-identity-v2' or data['runtimeIdentity']!=runtime:
        raise history.VersionError()
    history.verify('52b-historical-evaluator-b04','historical_evaluator')
    paths=history.git('ls-files','--cached','--others','--exclude-standard').decode().splitlines()
    if history.source_root(paths,lambda p:(history.ROOT/p).read_bytes())!=data['implementationRootSHA256']:
        raise history.VersionError()
    for path,expected in data['sourceHashes'].items():
        if history.sha((history.ROOT/path).read_bytes())!=expected:raise history.VersionError()
    baseline=history.ROOT/'docs/task52-b2-behavior-baseline-v1.json'
    if history.sha(baseline.read_bytes())!=data['reconstructionBaseline']['sha256']:
        raise history.VersionError()
    from backend.ai import Interpretation
    from backend.source_preparation import PREPARATION_VERSION,RUNTIME_ID
    if (history.digest(Interpretation.model_json_schema())!=data['canonicalSchemaSHA256']
            or RUNTIME_ID!=runtime or PREPARATION_VERSION!=data['preparedSourceTypeVersion']):raise history.VersionError()
    return {'runtime':runtime,'verified':True,'purpose':purpose,'planningAuthorized':False,
            'historicalSourceEqualityClaimed':False,'behavioralReconstruction':True}
