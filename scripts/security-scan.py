"""Credential-value scan: report counts only, never matching content or values.

Run from the repository root after a production build. Reads private configuration
as data and checks tracked files, Git history, and generated browser assets.
"""
from pathlib import Path
import re
import shlex
import subprocess
from tempfile import TemporaryFile

root = Path(__file__).resolve().parent.parent
secrets = set()
for path in (root/'backend').glob('.env.*'):
    if path.name == '.env.example': continue
    for line in path.read_text().splitlines():
        parts = shlex.split(line, comments=True)
        if len(parts) != 1 or '=' not in parts[0]: continue
        key, value = parts[0].split('=', 1)
        if re.search(r'PASSWORD|SECRET|TOKEN|PRIVATE_KEY', key) and len(value) >= 8:
            secrets.add(value.encode())
tracked = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).split(b'\0')
files = [root/p.decode() for p in tracked if p]
files += [p for p in (root/'.next').rglob('*') if p.is_file()]
hits = 0
for path in files:
    if path.is_file():
        data = path.read_bytes()
        hits += any(value in data for value in secrets)
# Scan historical blobs through a batch pipe, without exposing their contents.
objects = subprocess.check_output(['git','rev-list','--objects','--all'],cwd=root).splitlines()
ids = [line.split(b' ',1)[0] for line in objects]
with TemporaryFile() as batch:
    subprocess.run(['git','cat-file','--batch'],input=b'\n'.join(ids)+b'\n',stdout=batch,check=True,cwd=root)
    batch.seek(0)
    history_hits = 0
    while header := batch.readline():
        fields = header.split()
        if len(fields) != 3: raise SystemExit('History scan failed (details withheld).')
        data = batch.read(int(fields[2])); batch.read(1)
        if fields[1] == b'blob' and any(value in data for value in secrets): history_hits += 1
print(f'Credential scan: {len(secrets)} configured sensitive values; {len(files)} current files/assets; {len(ids)} historical objects; current matches={hits}; historical matches={history_hits}.')
raise SystemExit(bool(hits or history_hits))
