// No environment selector. Only reviewed server bootstrap can install a profile.
// Current bounded profile is authenticated liveness ONLY, not planning readiness.
import type {ServerIdentityPort} from './server-identity';
type Profile=Readonly<{handle:(path:string,request?:Request)=>Promise<Response>}>;
const key=Symbol.for('whereto.private-boundary.v1');
type Registry={profile?:Profile;brands:WeakSet<object>};
const root=globalThis as typeof globalThis&{[key]?:Registry};
function registry(){if(typeof window!=='undefined')throw Error('Server only');return root[key]??=( {brands:new WeakSet()} );}
export function createStatusOnlyProfile(origin:string,backend:string,port:ServerIdentityPort,send:typeof fetch=fetch):Profile {
 if(!/^https:\/\/[^/@?#]+$/.test(origin)||!/^https:\/\/[^/@?#]+\/?$/.test(backend))throw Error('Private configuration required');
 const profile=Object.freeze({async handle(path:string,request?:Request){
  const headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'};
  if(path==='/api/development-diagnostics')return Response.json({},{status:404,headers});
  if(path!=='/api/health')return Response.json({code:'hosted_route_unavailable',message:'Private planning is unavailable.'},{status:503,headers});
  if(!request||request.method!=='GET'||request.headers.get('sec-fetch-site')==='cross-site'||['authorization','x-serverless-authorization','x-whereto-context','x-whereto-user'].some(h=>request.headers.has(h)))return Response.json({status:'error',backend:'unavailable'},{status:403,headers});
  try{
   const assertion=request.headers.get('x-goog-iap-jwt-assertion');if(!assertion||assertion.length>16384)throw Error();
   const signal=AbortSignal.any([request.signal,AbortSignal.timeout(3000)]);const proof=await port.verifyAndSeal({path:'/health',method:'GET',body:new Uint8Array(),assertion,signal});
   const response=await send(new URL('/health',backend),{method:'GET',cache:'no-store',redirect:'manual',headers:{Authorization:'Bearer '+proof.workloadToken,'X-Whereto-Context':proof.context},signal});
   if(!response.ok||response.status>=300||!response.body)throw Error();
   const reader=response.body.getReader(),chunks:Uint8Array[]=[];let size=0;const cancel=()=>{void reader.cancel();};signal.addEventListener('abort',cancel,{once:true});
   try{while(true){signal.throwIfAborted();const v=await reader.read();if(v.done)break;size+=v.value.byteLength;if(size>4096)throw Error();chunks.push(v.value);}}finally{signal.removeEventListener('abort',cancel);await reader.cancel().catch(()=>{});}
   const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(chunks)));signal.throwIfAborted();if(data?.status!=='ok')throw Error();
   return Response.json({status:'ok',backend:'ok'},{headers});
  }catch{return Response.json({status:'error',backend:'unavailable'},{status:503,headers});}
 }});registry().brands.add(profile);return profile;
}
export function installPrivateProfile(profile:Profile){const r=registry();if(r.profile||!r.brands.has(profile))throw Error('Private composition refused');r.profile=profile;}
export function privateRoute(path:string,request?:Request):Promise<Response>|null {return registry().profile?.handle(path,request)??null;}
