import process from 'node:process';import fs from 'node:fs';import ts from 'typescript';
const dest=process.argv[2];fs.mkdirSync(dest,{recursive:true});
for(const [source,name] of [['lib/identity-json.ts','identity-json'],['lib/server-identity.ts','server-identity'],['lib/server-https.ts','server-https'],['lib/private-server-boundary.ts','private-server-boundary'],['experiments/ordinary_network/preload.ts','preload']]){
 let s=fs.readFileSync(source,'utf8');for(const n of ['identity-json','server-identity','server-https','private-server-boundary'])s=s.replaceAll(`'../../lib/${n}'`,`'./${n}.mjs'`).replaceAll(`'./${n}'`,`'./${n}.mjs'`);
 fs.writeFileSync(`${dest}/${name}.mjs`,ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,removeComments:true}}).outputText);
}
