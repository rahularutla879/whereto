"""Copy only the reviewed application runtime, never tests/private/evaluation state."""
import json
from pathlib import Path
import shutil
import sys


def prepare(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if target.exists() or target == source or source in target.parents:
        raise ValueError('Use an isolated output directory')
    manifest = json.loads((source/'deployment/backend-files.json').read_text())
    for relative in manifest['files']:
        path = source/relative
        if ((not relative.startswith('backend/') and relative != 'data/mock-venues.json')
                or any(part.startswith('test_') or part in ('evaluation','scripts') or 'fixture' in part for part in Path(relative).parts)
                or path.is_symlink() or source not in path.resolve().parents
                or not path.is_file() or path.suffix not in ('.py','.json')):
            raise ValueError('Invalid runtime manifest')
        destination = target/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)


if __name__ == '__main__':
    prepare(*sys.argv[1:])
