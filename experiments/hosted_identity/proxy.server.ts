// Inactive server-only forwarding contract. Not imported by app routes.
import { Buffer } from "node:buffer";

export const routes = {
  "/api/interpret": ["/api/interpret", 65536, 70000],
  "/api/plans/generate": ["/api/plans/generate", 65536, 115000],
  "/api/plans/advanced": ["/api/plans/advanced", 4096, 45000],
  "/api/plans/options": ["/api/plans/options", 65536, 115000],
  "/api/plans/save": ["/api/plans/save", 4096, 45000],
  "/api/plans/reopen": ["/api/plans/reopen", 4096, 45000],
  "/api/plans/refresh": ["/api/plans/refresh", 4096, 45000],
  "/api/venues/details": ["/api/venues/details", 65536, 30000],
  "/api/starting-areas": ["/api/starting-areas", 65536, 115000],
  "/api/starting-places": ["/api/starting-places", 65536, 30000],
  "/api/planning-mode": ["/api/planning-mode", 0, 30000],
  "/api/health": ["/health", 0, 3000],
} as const;
type Path = keyof typeof routes;
// Trusted server composition must supply independently verified IAP, Google ID
// token acquisition and exact request sealing. Browser objects cannot supply it.
export interface ServerIdentityPort {
  verifyAndSeal(input: { path: string; method: string; body: Uint8Array; assertion: string; signal: AbortSignal }): Promise<{ workloadToken: string; context: string }>;
}
export function createInactiveForwarder(origin: string, backend: string, identity: ServerIdentityPort, send: typeof fetch) {
  if (typeof window !== "undefined" || !origin.startsWith("https://") || !backend.startsWith("https://") || new URL(backend).username || new URL(backend).password || new URL(backend).search || new URL(backend).hash) throw new Error("Server configuration required");
  return async (path: Path, request: Request): Promise<Response> => {
    const resultHeaders = { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" };
    if (!Object.hasOwn(routes, path)) return Response.json({ error: "request_refused" }, { status:403, headers:resultHeaders });
    const [upstream, limit, timeout] = routes[path];
    if (request.method !== (limit ? "POST" : "GET") || (limit && request.headers.get("origin") !== origin) || request.headers.get("sec-fetch-site") === "cross-site") return Response.json({error:"request_refused"},{status:403,headers:resultHeaders});
    if (["authorization","x-serverless-authorization","x-whereto-context","x-whereto-user"].some(k=>request.headers.has(k))) return Response.json({error:"request_refused"},{status:403,headers:resultHeaders});
    const assertion=request.headers.get("x-goog-iap-jwt-assertion");
    if (!assertion || assertion.length>16384) return Response.json({error:"authentication_required"},{status:401,headers:resultHeaders});
    const reader=request.body?.getReader();const chunks:Uint8Array[]=[];let size=0;
    try {
      const readSignal=AbortSignal.any([request.signal,AbortSignal.timeout(5000)]);
      const cancel=()=>{void reader?.cancel();};readSignal.addEventListener("abort",cancel,{once:true});
      try {
        if(reader)while(true){readSignal.throwIfAborted();const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){await reader.cancel();return Response.json({error:"request_too_large"},{status:413,headers:resultHeaders});};chunks.push(value);}
        readSignal.throwIfAborted();
      } finally {readSignal.removeEventListener("abort",cancel);}
      const body=Buffer.concat(chunks);const signal=AbortSignal.any([request.signal,AbortSignal.timeout(timeout)]);
      const credential=await identity.verifyAndSeal({path:upstream,method:request.method,body,assertion,signal});signal.throwIfAborted();
      const response=await send(new URL(upstream,backend),{method:request.method,body:limit?body:undefined,
        headers:{"Content-Type":"application/json","Authorization":"Bearer "+credential.workloadToken,"X-Whereto-Context":credential.context},
        cache:"no-store",redirect:"manual",signal});
      if(response.status>=300&&response.status<400)throw new Error("redirect");
      if(!response.ok)return Response.json({error:"upstream_refused"},{status:[401,403,404,409,413,422,429].includes(response.status)?response.status:503,headers:resultHeaders});
      // Never copy upstream credential, identity or cookie headers into the browser.
      return new Response(response.body,{status:response.status,headers:{...resultHeaders,"Content-Type":"application/json"}});
    } catch {await reader?.cancel().catch(()=>{});return Response.json({error:"request_unavailable"},{status:503,headers:resultHeaders});}
  };
}
