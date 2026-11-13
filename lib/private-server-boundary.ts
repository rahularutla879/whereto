// No environment selector. Only reviewed server bootstrap can install a profile.
// Explicit constructors select status-only or the two reviewed ordinary routes.
import type {ServerIdentityPort} from './server-identity';
type Profile=Readonly<{handle:(path:string,request?:Request)=>Promise<Response>}>;
const key=Symbol.for('whereto.private-boundary.v1');
type Registry={profile?:Profile;brands:WeakSet<object>};
const root=globalThis as typeof globalThis&{[key]?:Registry};
function registry(){if(typeof window!=='undefined')throw Error('Server only');return root[key]??=( {brands:new WeakSet()} );}
function createProfile(origin:string,backend:string,port:ServerIdentityPort,send:typeof fetch,ordinary:boolean):Profile {
 if(!/^https:\/\/[^/@?#]+$/.test(origin)||!/^https:\/\/[^/@?#]+\/?$/.test(backend))throw Error('Private configuration required');
 const profile=Object.freeze({async handle(path:string,request?:Request){
  const headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'};
  if(path==='/api/development-diagnostics')return Response.json({},{status:404,headers});
  const business=ordinary&&['/api/interpret','/api/plans/generate'].includes(path);
  if(path!=='/api/health'&&!business)return Response.json({code:'hosted_route_unavailable',message:'Private planning is unavailable.'},{status:503,headers});
  if(!request||request.method!==(business?'POST':'GET')||request.headers.get('sec-fetch-site')==='cross-site'||['authorization','x-serverless-authorization','x-whereto-context','x-whereto-user'].some(h=>request.headers.has(h)))return Response.json({status:'error',backend:'unavailable'},{status:403,headers});
  try{
   if(business&&request.headers.get('origin')!==origin)throw Error();
   const deadline=business?(path==='/api/interpret'?70000:115000):3000;
   const signal=AbortSignal.any([request.signal,AbortSignal.timeout(deadline)]);
   let body=new Uint8Array();
   if(business){const bodySignal=AbortSignal.any([signal,AbortSignal.timeout(5000)]);const reader=request.body?.getReader();if(!reader)throw Error();let n=0;const chunks:Uint8Array[]=[];const stop=()=>{void reader.cancel();};bodySignal.addEventListener('abort',stop,{once:true});try{while(true){bodySignal.throwIfAborted();const v=await reader.read();if(v.done)break;n+=v.value.byteLength;if(n>65536)throw Error();chunks.push(v.value);}bodySignal.throwIfAborted();body=Buffer.concat(chunks);}finally{bodySignal.removeEventListener('abort',stop);await reader.cancel().catch(()=>{});}}
   const target=business?path:'/health';
   const assertion=request.headers.get('x-goog-iap-jwt-assertion');if(!assertion||assertion.length>16384)throw Error();
   const proof=await port.verifyAndSeal({path:target,method:request.method,body,assertion,signal});
   const response=await send(new URL(target,backend),{method:request.method,...(business?{body:Buffer.from(body)}:{}),cache:'no-store',redirect:'manual',headers:{Authorization:'Bearer '+proof.workloadToken,'X-Whereto-Context':proof.context,...(business?{'Content-Type':'application/json'}:{})},signal});
   if(!response.ok||response.status>=300||!response.body)throw Error();
   const reader=response.body.getReader(),chunks:Uint8Array[]=[];let size=0;const cancel=()=>{void reader.cancel();};signal.addEventListener('abort',cancel,{once:true});
   try{while(true){signal.throwIfAborted();const v=await reader.read();if(v.done)break;size+=v.value.byteLength;if(size>(business?1048576:4096))throw Error();chunks.push(v.value);}}finally{signal.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});}
   const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(chunks)));signal.throwIfAborted();if(business)return Response.json(data,{headers});if(data?.status!=='ok')throw Error();
   return Response.json({status:'ok',backend:'ok'},{headers});
  }catch{return Response.json(business?{code:'private_action_refused',message:'This outing could not continue safely. Start a new request.'}:{status:'error',backend:'unavailable'},{status:503,headers});}
 }});registry().brands.add(profile);return profile;
}
export function installPrivateProfile(profile:Profile){const r=registry();if(r.profile||!r.brands.has(profile))throw Error('Private composition refused');r.profile=profile;}
export function privateRoute(path:string,request?:Request):Promise<Response>|null {return registry().profile?.handle(path,request)??null;}

export function createStatusOnlyProfile(origin:string,backend:string,port:ServerIdentityPort,send:typeof fetch=fetch):Profile{return createProfile(origin,backend,port,send,false);}
export function createOrdinaryProfile(origin:string,backend:string,port:ServerIdentityPort,send:typeof fetch=fetch):Profile{return createProfile(origin,backend,port,send,true);}
