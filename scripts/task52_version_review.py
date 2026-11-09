"""Offline identity checks only: no runtime imports, scoring, dispatch or journal access.

The trusted allowlist anchors immutable manifests. Git object identity supplies
historical source retention; working-tree equality is a separate explicit check.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/task52-source-identities-v1.json'
# Filled when this separately reviewed manifest is created; never auto-discover.
MANIFEST_SHA = 'af0f271bea2aceafce244f8d43a948b88682a5bae5e8c417bb827e513efda259'
ROLES = {'historical_evaluator', 'runtime_legacy_foundation'}


class VersionError(ValueError):
    def __init__(self):
        super().__init__('Unrecognized or mismatched offline implementation identity.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def git(*args):
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise VersionError() from None


def selected(path):
    return ((path.startswith('backend/') and not Path(path).name.startswith('test_'))
            or (path.startswith('scripts/cloud_model52') and path.endswith('.py')))


def source_root(paths, read):
    return digest({p: sha(read(p)) for p in sorted(paths) if selected(p)})


def identity(name, role):
    try:
        raw = MANIFEST.read_bytes()
    except OSError:
        raise VersionError() from None
    if (sha(raw) != MANIFEST_SHA or type(name) is not str
            or type(role) is not str or role not in ROLES):
        raise VersionError()
    data = json.loads(raw)
    if data.get('format') != '52b-source-identities-v1':
        raise VersionError()
    entry = data.get('identities', {}).get(name)
    if not entry or entry['role'] != role:
        raise VersionError()
    return deepcopy(entry)


def verify(name, role, *, working=False):
    """Read-only, no code execution. Missing Git objects fail; never fetch/fallback."""
    entry = identity(name, role)
    commit = entry['gitCommit']
    if git('rev-parse', commit + '^{tree}').decode().strip() != entry['gitTree']:
        raise VersionError()
    paths = git('ls-tree', '-r', '--name-only', commit).decode().splitlines()
    def snapshot(path):
        return git('show', commit + ':' + path)
    corpus_path = entry['corpusPath']
    corpus = snapshot(corpus_path)
    if sha(corpus) != entry['corpusSHA256']:
        raise VersionError()
    if json.loads(corpus)['sourceSha256'] != entry['originalSixPins']:
        raise VersionError()
    if source_root(paths, snapshot) != entry['implementationRootSHA256']:
        raise VersionError()
    for path, expected in entry['originalSixPins'].items():
        if sha(snapshot(path)) != expected:
            raise VersionError()
    if working:
        current = git('ls-files', '--cached', '--others', '--exclude-standard').decode().splitlines()
        try:
            if (sha((ROOT / corpus_path).read_bytes()) != entry['corpusSHA256'] or
                    source_root(current, lambda p: (ROOT / p).read_bytes()) != entry['implementationRootSHA256']):
                raise VersionError()
        except OSError:
            raise VersionError() from None
    return {'identity': name, 'role': role, 'manifestSHA256': MANIFEST_SHA,
            'snapshotVerified': True, 'workingSourcesVerified': working,
            'dispatchAuthorized': False}


def replay_descriptor(original, *, expected_original_hash, target):
    """Provenance format prototype, NOT a scorer or proof of historical truth.

    The caller must obtain the expected digest from independently verified source
    evidence. Original labels/outcomes stay nested unchanged; no in-place edits.
    """
    if digest(original) != expected_original_hash:
        raise VersionError()
    verify(target, 'runtime_legacy_foundation')
    if not all(original.get(k) for k in ('operationId', 'evaluator', 'responseHash', 'configurationHash')):
        raise VersionError()
    if original['evaluator'] == target:
        raise VersionError()
    return {'format': '52b-offline-replay-descriptor-v1',
            'original': deepcopy(original), 'originalRecordSHA256': expected_original_hash,
            'replayImplementation': target, 'replayDisposition': 'unreviewed',
            'historicalOutcomeRewritten': False, 'paidAttemptAuthorized': False}
