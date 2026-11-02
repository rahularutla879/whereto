// Local development only. Own a private runtime tree, never kill a port's owner.
import process from 'node:process';
import console from 'node:console';
import {Buffer} from 'node:buffer';
import {setTimeout,clearTimeout,setInterval,clearInterval} from 'node:timers';
import {setTimeout as delay} from 'node:timers/promises';
import {fork,spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {createServer as httpServer,request} from 'node:http';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {mkdirSync,writeFileSync,readFileSync,lstatSync,unlinkSync,realpathSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
const file=fileURLToPath(import.meta.url),root=realpathSync(resolve(dirname(file),'..'));
const worker=process.argv[2]==='--worker';
const [service,...args]=process.argv.slice(worker?3:2);
if(!['backend','frontend'].includes(service)){console.error('Choose backend or frontend.');process.exit(1);}
const port=service==='backend'?8000:3000;
const folder=resolve(root,'backend/.local/dev-servers'),metadata=resolve(folder,service+'.json');
const label=service==='backend'?'Backend':'Frontend';
function privateDirectory(){
 mkdirSync(folder,{recursive:true,mode:0o700});
 const info=lstatSync(folder);
 if(realpathSync(folder)!==folder||!info.isDirectory()||info.isSymbolicLink()||(process.getuid&&info.uid!==process.getuid())||(info.mode&0o077))throw Error('Unsafe local runtime directory.');
}
function readOwner(){
 try{
  privateDirectory();const info=lstatSync(metadata);
  if(!info.isFile()||info.isSymbolicLink()||info.size>2048||(info.mode&0o077)||(process.getuid&&info.uid!==process.getuid()))return;
  const value=JSON.parse(readFileSync(metadata,'utf8'));
  if(value.root===root&&value.service===service&&/^[a-f0-9]{64}$/.test(value.token)&&Number.isInteger(value.controlPort)&&value.controlPort>0&&value.controlPort<65536)return value;
 }catch{/* Missing/stale private metadata or an already exited owned process is safe. */}
}
async function control(owner,stop=false){
 return new Promise(resolve=>{
  const req=request({host:'127.0.0.1',port:owner.controlPort,path:stop?'/stop':'/status',method:'POST',headers:{authorization:'Bearer '+owner.token}},res=>{
   let body='';res.on('data',data=>{if(body.length<2048)body+=data;});res.on('end',()=>{try{const value=JSON.parse(body);resolve(res.statusCode===200&&value.root===root&&value.service===service?value:null);}catch{resolve(null);}});
  });req.on('error',()=>resolve(null));req.setTimeout(1000,()=>{req.destroy();resolve(null);});req.end();
 });
}
function bindable(host){return new Promise(resolve=>{
 const probe=createServer();probe.once('error',error=>resolve(host==='::'&&error.code==='EAFNOSUPPORT'));probe.listen({host,port,exclusive:true},()=>probe.close(()=>resolve(true)));
});}
async function available(){return await bindable('127.0.0.1')&&await bindable('::');}
if(!worker){
 if(args.includes('--stop')){
  const owner=readOwner();
  const verified=owner&&await control(owner);
  const status=verified&&await control(owner,true);
  if(!status){console.error(`No authenticated ${service} launcher is available. No process was terminated.`);process.exit(1);}
  const deadline=Date.now()+12000;
  while(Date.now()<deadline){
   if(!await control(owner)&&await available()){console.log(`${label} stopped; port ${port} released.`);process.exit(0);}
   await delay(100);
  }
  console.error(`${label} stop did not release port ${port} within the bounded wait. No unrelated process was touched.`);process.exit(1);
 }
 if(args.some(a=>a==='--port'||a==='-p'||/^-[p][0-9]/.test(a)||a.startsWith('--port='))){console.error(`Use the fixed ${label.toLowerCase()} port ${port}.`);process.exit(1);}
 const owner=readOwner(),status=owner&&await control(owner);
 if(status||!await available()){
  console.error(status?`${label} for this repository is already running on ${port}. Reuse it, or stop its Terminal with Control+C. No duplicate was started.`:`Port ${port} is occupied by an unverified existing process. No process was stopped and no alternate port was selected. Stop its original Terminal or investigate the conflict before restarting.`);
  process.exit(1);
 }
 const child=fork(file,['--worker',service,...args],{cwd:root,stdio:['inherit','inherit','inherit','ipc']});
 let stopping=false;
 const stop=()=>{if(!stopping){stopping=true;if(child.connected)child.send('stop',()=>{});}};
 process.on('SIGINT',stop);process.on('SIGTERM',stop);process.on('SIGHUP',stop);
 child.on('error',()=>{console.error(`${label} supervisor could not start.`);process.exitCode=1;});
 child.on('exit',(code)=>{process.exitCode=stopping?0:code??1;});
}else{
 // A live IPC owner, not a PID file, is the lifetime authority. Parent loss also stops us.
 let child,stopping=false,forceTimer,pollTimer,finishTimer,server,token;
 let exitCode=0;
 const signalTree=(signal)=>{
  if(!child?.pid)return;
  try{if(process.platform==='win32')child.kill(signal);else process.kill(-child.pid,signal);}catch(error){if(error.code!=='ESRCH')console.error(`${label} process cleanup could not signal its owned tree.`);}
 };
 const groupAlive=()=>{if(!child?.pid)return false;try{process.kill(process.platform==='win32'?child.pid:-child.pid,0);return true;}catch{return false;}};
 function finish(){
  clearTimeout(forceTimer);clearInterval(pollTimer);clearTimeout(finishTimer);
  try{if(readOwner()?.token===token)unlinkSync(metadata);}catch{/* Missing/stale private metadata or an already exited owned process is safe. */}
  server?.close();if(process.connected)process.disconnect();process.exit(exitCode);
 }
 async function stop(code=0){
  if(stopping)return;stopping=true;exitCode=code;
  // Signal only the runtime leader first: Uvicorn/Next gracefully supervise their workers.
  if(child?.exitCode===null)try{child.kill('SIGTERM');}catch{/* Missing/stale private metadata or an already exited owned process is safe. */}
  else signalTree('SIGTERM');
  forceTimer=setTimeout(()=>{if(groupAlive()){console.error(`${label} grace period elapsed; terminating only its owned runtime tree.`);signalTree('SIGKILL');}},8000);
  pollTimer=setInterval(async()=>{if(!groupAlive()&&await available())finish();},75);
  finishTimer=setTimeout(()=>{console.error(`${label} cleanup timed out; no unrelated listener was touched.`);exitCode=1;finish();},11000);
  if(!child)finish();
 }
 process.on('message',message=>{if(message==='stop')void stop();});
 process.on('disconnect',()=>void stop());process.on('SIGINT',()=>void stop());process.on('SIGTERM',()=>void stop());process.on('SIGHUP',()=>void stop());
 try{
  privateDirectory();token=randomBytes(32).toString('hex');
  server=httpServer((req,res)=>{
   const auth=Buffer.from(req.headers.authorization??''),expected=Buffer.from('Bearer '+token);
   if(req.method!=='POST'||auth.length!==expected.length||!timingSafeEqual(auth,expected)||!['/status','/stop'].includes(req.url)){res.writeHead(404).end();return;}
   res.setHeader('Content-Type','application/json');res.end(JSON.stringify({root,service,stopping}));if(req.url==='/stop')void stop();
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  // Exclusive metadata creation prevents concurrent launch races; stale files are never PID kill authority.
  if(readOwner()){
   if(await control(readOwner()))throw Error('Already running.');
   unlinkSync(metadata);
  }
  writeFileSync(metadata,JSON.stringify({root,service,controlPort:server.address().port,token}),{mode:0o600,flag:'wx'});
  if(stopping)finish();
  const command=service==='backend'?resolve(root,'backend/.venv/bin/python'):process.execPath;
  const commandArgs=service==='backend'?['-m','backend.dev_start',...args]:[resolve(root,'node_modules/next/dist/bin/next'),'dev','--port','3000',...args];
  child=spawn(command,commandArgs,{cwd:root,stdio:'inherit',detached:process.platform!=='win32',env:{...process.env,NEXT_EXIT_TIMEOUT_MS:'5000'}});
  child.on('error',()=>{console.error(`${label} runtime could not start. Check the installed local dependencies.`);void stop(1);});
  child.on('exit',code=>void stop(code??0));
 }catch{console.error(`${label} launcher could not acquire its private local runtime state. Check backend/.local/dev-servers ownership/permissions; see docs/dev-lifecycle.md. No existing process was terminated.`);void stop(1);}
}
