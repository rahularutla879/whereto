import {privateRoute} from "@/lib/private-server-boundary";
import { diagnosticBoundary } from "@/lib/development-access";
export async function GET(request:Request){
 const isolated=privateRoute("/api/development-diagnostics",request);if(isolated)return isolated;
 const headers={"Cache-Control":"no-store"};
 const boundary=diagnosticBoundary(request);
 if(!boundary)return Response.json({},{status:404,headers});
 try{
  const response=await fetch(`${process.env.BACKEND_URL??"http://127.0.0.1:8000"}/api/development-diagnostics`,{headers:boundary,cache:"no-store",signal:AbortSignal.timeout(5000)});
  return Response.json(response.ok?await response.json():{},{status:response.ok?200:404,headers});
 }catch{return Response.json({},{status:404,headers});}
}
