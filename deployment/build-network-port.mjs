// Build closed production components, never the offline constructor or driver.
import './build-identity-port.mjs';
import fs from 'node:fs';import ts from 'typescript';import {createHash} from 'node:crypto';
const source=fs.readFileSync('lib/server-https.ts','utf8').replace('export function channel','function channel');
const result=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,removeComments:true},reportDiagnostics:true});
if(result.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('Network artifact refused');
fs.writeFileSync('private-runtime/server-https.mjs',result.outputText);fs.copyFileSync('deployment/private-network-v1.json','private-runtime/network-contract.json');
const files=['identity-json.mjs','server-identity.mjs','server-https.mjs','network-contract.json'];const manifest=Object.fromEntries(files.map(p=>[p,createHash('sha256').update(fs.readFileSync('private-runtime/'+p)).digest('hex')]));fs.writeFileSync('private-runtime/network-build.json',JSON.stringify(manifest,null,2)+'\n');
