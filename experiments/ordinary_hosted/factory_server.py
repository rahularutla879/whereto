"""Local-only additional allowlisted operation on the authenticated frozen factory."""
from unittest.mock import patch
from experiments.hosted_identity import server
from experiments.service_isolation import server as base
original=base.handler
def handler(c,path,value,owner):
 if c['service']=='factory' and path=='/ordinary':
  from experiments.ordinary_hosted.factory import Factory
  try:return Factory(c).ordinary(value)
  except Exception as error:
   import json,traceback
   print(json.dumps({'event':'ordinary_factory_refused','class':type(error).__name__,'reason':getattr(error,'code',None),'sqlstate':getattr(error,'sqlstate',None) or getattr(error.__context__,'sqlstate',None),'reasonCategory':getattr(error,'reason',None),'frames':[(f.filename.rsplit('/',1)[-1],f.name,f.lineno) for f in traceback.extract_tb(error.__traceback__)]}),flush=True)
   raise
 return original(c,path,value,owner)
def main():
 with patch.object(base,'handler',handler):server.main()
if __name__=='__main__':main()
