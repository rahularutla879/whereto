import { developmentOriginHeaders } from "@/lib/development-origin";
export async function GET(request:Request){
 const headers={"Cache-Control":"no-store"};
 const boundary=developmentOriginHeaders(request);
 const host=request.headers.get("host")??new URL(request.url).host;
 if(process.env.NODE_ENV!=="development"||boundary["X-WhereTo-Proxied"]!=="0"||!["localhost","127.0.0.1","[::1]"].includes(new URL(`http://${host}`).hostname))return Response.json({},{status:404,headers});
 try{
  const response=await fetch(`${process.env.BACKEND_URL??"http://127.0.0.1:8000"}/api/development-diagnostics`,{headers:boundary,cache:"no-store",signal:AbortSignal.timeout(5000)});
  return Response.json(response.ok?await response.json():{},{status:response.ok?200:404,headers});
 }catch{return Response.json({},{status:404,headers});}
}
