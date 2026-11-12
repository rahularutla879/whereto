// Fixed server-only component, not a hosted application launcher.
import fs from 'node:fs';
import ts from 'typescript';
const directory='private-runtime';fs.mkdirSync(directory,{recursive:true});
for(const name of ['identity-json','server-identity']){
 let source=fs.readFileSync(`lib/${name}.ts`,'utf8');
 if(name==='server-identity'){
  // The shipped artifact exposes only the closed Google-root constructor.
  source=source.replace("'./identity-json'","'./identity-json.mjs'")
   .replace('export function composeIdentityPort','function composeIdentityPort')
   .replace('export const REQUEST_ISSUER','const REQUEST_ISSUER')
   .replace('export const hash','const hash').replace('export const requestBinding','const requestBinding');
 }
 const result=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,removeComments:true},reportDiagnostics:true});
 if(result.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('Identity artifact compilation refused');
 fs.writeFileSync(`${directory}/${name}.mjs`,result.outputText);
}
fs.copyFileSync('deployment/private-startup-v1.json',`${directory}/startup-contract.json`);
