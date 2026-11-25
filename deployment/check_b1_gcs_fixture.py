"""Fictional in-memory GCS destination with actual existing B1 PG17 recovery.

No cloud requests, live database or genuine key. Existing fixture VM only.
"""
from pathlib import Path
from hashlib import sha256
import os,json
from deployment.check_b1_fixture import main
from deployment import b1_gcs as g

def transfer(cipher,receipt):
    g.artifact(cipher,receipt['ciphertextSHA256'])
    name=g.object_name('fictional-gcs-b1-0001',cipher.name)
    store={}
    if name in store:raise AssertionError('create-only replay')
    store[name]=(123,cipher.read_bytes())
    metadata=dict(bucket=g.BUCKET,name=name,generation='123',size=str(len(store[name][1])))
    identity=g.object_receipt(metadata,name,receipt['bytes'])
    assert identity['generation']=='123'
    downloaded=g.verify_download(store[name][1],receipt['ciphertextSHA256'])
    assert sha256(downloaded).hexdigest()==receipt['ciphertextSHA256']
    p=cipher.parent/'downloaded.cms';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(downloaded)
    print(json.dumps({'fakeGCS':'pinned version/hash roundtrip','realGCSRequests':0}),flush=True)
    return p
if __name__=="__main__":main(transfer=transfer)
