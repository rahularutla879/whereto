// Server-owned HTTPS channel. Identity proofs are supplied by ServerIdentityPort.
import {Agent,request as httpsRequest} from 'node:https';
export type NetworkEnrollment={audience:string;endpoint:string};
export function createHTTPSChannel(enrollment:NetworkEnrollment):typeof fetch {
 return channel(enrollment,new Agent({keepAlive:false,maxSockets:4,maxTotalSockets:4,rejectUnauthorized:true,minVersion:'TLSv1.2'}));
}
// Trusted test injection only; production artifact does not export this constructor.
export function channel(c:NetworkEnrollment,agent:Agent):typeof fetch {
 if(typeof window!=='undefined')throw Error('Server only');
 for(const value of [c.audience,c.endpoint]){const u=new URL(value);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.origin!==value.replace(/\/$/,''))throw Error('HTTPS enrollment required');}
 let active=0;
 return async(input,init)=>{
  const u=new URL(String(input));const method=init?.method??'GET';const paths=['/health','/api/interpret','/api/plans/generate','/api/planning-mode','/api/private-ordinary/revoke'];
  if(u.origin!==new URL(c.audience).origin||!paths.includes(u.pathname)||u.search||u.hash||!['GET','POST'].includes(method)||init?.redirect!=='manual'||active>=4)throw Error('Network scope refused');
  const body=init.body==null?Buffer.alloc(0):Buffer.from(init.body as Uint8Array);if(body.length>65536||method==='GET'&&body.length)throw Error('Body refused');
  init.signal?.throwIfAborted();active++;
  try{return await new Promise<Response>((resolve,reject)=>{
   const stop=()=>{reject(Error('Request stopped'));req.destroy();};const timer=setTimeout(stop,method==='GET'?3000:u.pathname==='/api/interpret'?70000:115000);
   const req=httpsRequest(new URL(u.pathname,c.endpoint),{agent,method,headers:Object.fromEntries(new Headers(init.headers))},res=>{
    let size=0;const chunks:Buffer[]=[];const max=method==='GET'?4096:1048576;
    res.on('data',(b:Buffer)=>{size+=b.length;if(size>max)stop();else chunks.push(b);});
    res.on('error',reject);res.on('end',()=>{if(!res.complete||res.statusCode!==200||!String(res.headers['content-type']).startsWith('application/json'))return reject(Error('Response refused'));resolve(new Response(Buffer.concat(chunks),{status:200,headers:{'Content-Type':'application/json'}}));});
   });
   req.on('error',reject);req.on('close',()=>{clearTimeout(timer);init.signal?.removeEventListener('abort',stop);});init.signal?.addEventListener('abort',stop,{once:true});req.end(body);
  });}finally{active--;}
 };
}
