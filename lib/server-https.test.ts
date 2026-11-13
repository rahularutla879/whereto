import test from 'node:test';import assert from 'node:assert/strict';import {mkdtempSync,readFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {spawn,execFileSync} from 'node:child_process';import {Agent} from 'node:https';import {once} from 'node:events';import {channel,createHTTPSChannel} from './server-https';

test('independent HTTPS process: exact bytes, trusted hostname, bounds and no redirects/fallback',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'whereto-net-'));let server:ReturnType<typeof spawn>|undefined;
 try{
  execFileSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes','-keyout',join(dir,'key'),'-out',join(dir,'cert'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],{stdio:'ignore'});
  const code=`const h=require('https'),fs=require('fs');const s=h.createServer({key:fs.readFileSync(process.argv[1]),cert:fs.readFileSync(process.argv[2])},(q,r)=>{let b=[];q.on('data',v=>b.push(v));q.on('end',()=>{r.writeHead(q.url==='/health'?302:200,{'Content-Type':'application/json'});r.end(q.url==='/api/planning-mode'?'x'.repeat(5000):Buffer.concat(b));});});s.listen(0,'127.0.0.1',()=>console.log(s.address().port));`;
  server=spawn(process.execPath,['-e',code,join(dir,'key'),join(dir,'cert')],{stdio:['ignore','pipe','ignore']});const [data]=await once(server.stdout!,'data');const port=Number(String(data).trim());const url='https://localhost:'+port;
  const agent=new Agent({ca:readFileSync(join(dir,'cert')),lookup:(_h,o,cb)=>{if(typeof o==='object'&&o.all)return cb(null,[{address:'127.0.0.1',family:4}]);cb(null,'127.0.0.1',4);},rejectUnauthorized:true,maxSockets:4});const send=channel({audience:'https://backend.invalid',endpoint:url},agent);
  const input=Buffer.from('{ "exact": true }');const r=await send('https://backend.invalid/api/interpret',{method:'POST',body:input,redirect:'manual'});assert.deepEqual(Buffer.from(await r.arrayBuffer()),input);
  await assert.rejects(send('https://backend.invalid/health',{method:'GET',redirect:'manual'}));
  await assert.rejects(send('https://backend.invalid/api/planning-mode',{method:'GET',redirect:'manual'}));
  await assert.rejects(send('https://wrong.invalid/api/interpret',{method:'POST',body:input,redirect:'manual'}));
  await assert.rejects(send('https://backend.invalid/api/interpret',{method:'POST',body:input,redirect:'follow'}));
  await assert.rejects(send('https://backend.invalid/api/interpret',{method:'POST',body:Buffer.alloc(65537),redirect:'manual'}));
  await assert.rejects(createHTTPSChannel({audience:url,endpoint:url})(url+'/api/interpret',{method:'POST',body:input,redirect:'manual'}));
  agent.destroy();
 }finally{if(server){server.kill('SIGTERM');await once(server,'exit');}rmSync(dir,{recursive:true,force:true});}
});
test('production channel rejects plaintext, URL credentials and non-root endpoints',()=>{
 for(const endpoint of ['http://backend.invalid','https://user:secret@backend.invalid','https://backend.invalid/path'])assert.throws(()=>createHTTPSChannel({audience:'https://backend.invalid',endpoint}));
});
