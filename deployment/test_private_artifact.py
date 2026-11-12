"""Actual compiled server component; no Google endpoints or provider authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,subprocess,shutil
ROOT=Path(__file__).resolve().parent.parent
class IdentityArtifactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=TemporaryDirectory(prefix='.task52-sdk-',dir=ROOT);cls.addClassCleanup(cls.temp.cleanup);cls.directory=Path(cls.temp.name)
  (cls.directory/'lib').mkdir();(cls.directory/'deployment').mkdir()
  for name in ('server-identity.ts','identity-json.ts'):shutil.copyfile(ROOT/'lib'/name,cls.directory/'lib'/name)
  shutil.copyfile(ROOT/'deployment/private-startup-v1.json',cls.directory/'deployment/private-startup-v1.json')
  subprocess.run(['node',str(ROOT/'deployment/build-identity-port.mjs')],cwd=cls.directory,check=True,capture_output=True)
 def node(self,source):
  r=subprocess.run(['node','--input-type=module','-e',source],cwd=self.directory,capture_output=True,text=True,timeout=10)
  self.assertEqual(r.returncode,0,r.stderr)
 def test_only_closed_google_factory_and_nonlaunchable_contract(self):
  self.node("import assert from 'node:assert/strict';import fs from 'node:fs';const m=await import('./private-runtime/server-identity.mjs');assert.deepEqual(Object.keys(m),['createGoogleIdentityPort']);assert.equal(JSON.parse(fs.readFileSync('private-runtime/startup-contract.json')).launchable,false)")
 def test_shipped_factory_never_accepts_fixture_key_or_uses_network(self):
  self.node("""import assert from 'node:assert/strict';import {randomBytes} from 'node:crypto';import {SignJWT,generateKeyPair} from 'jose';
const m=await import('./private-runtime/server-identity.mjs');let calls=0;globalThis.fetch=async()=>{calls++;throw Error('No real endpoints')};
const c={backendAudience:'https://backend.example.invalid',iapAudience:'/projects/0/locations/us-east4/services/frontend',serviceSubject:'synthetic',serviceEmail:'synthetic@example.invalid',testers:['alice'],build:'b'.repeat(64),epoch:'a'.repeat(64),environment:'production',signingKey:randomBytes(32).toString('base64url')};
const key=await generateKeyPair('ES256');const now=Math.floor(Date.now()/1000);const token=await new SignJWT({iss:'https://cloud.google.com/iap',aud:c.iapAudience,sub:'alice',iat:now,exp:now+600}).setProtectedHeader({alg:'ES256',kid:'task52-offline-iap'}).sign(key.privateKey);
await assert.rejects(m.createGoogleIdentityPort(c).verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion:token,signal:new AbortController().signal}));assert.equal(calls,0);
""")
if __name__=='__main__':unittest.main(verbosity=2)
