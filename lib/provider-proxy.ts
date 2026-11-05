import { publicPlanningPayload } from "./public-planning-payload";
import { classifiedFailure } from "./failure-diagnostics";
import { recoveryCode } from "./destination-context";
import { providerDiagnosticNotes } from "./provider-diagnostics";
import { developmentOriginHeaders } from "./development-origin";
// Fixed server-only upstream paths; never forward arbitrary URLs or credentials.
export async function providerProxy(path: "/api/starting-areas" | "/api/planning-mode" | "/api/venues/details" | "/api/starting-places" | "/api/plans/options", request?: Request) {
  const headers = { "Cache-Control": "no-store" };
  try {
    const body = request ? JSON.stringify(await request.json()) : undefined;
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method: request ? "POST" : "GET", body, headers: { "Content-Type": "application/json", ...developmentOriginHeaders(request) },
      cache: "no-store", signal: AbortSignal.any([...(request ? [request.signal] : []), AbortSignal.timeout((path === "/api/plans/options" || path === "/api/starting-areas") ? 115000 : 30000)]),
    });
    const data = await response.json();
    const classified=classifiedFailure(data);
    if (!response.ok && classified) return Response.json(publicPlanningPayload({...classified,
      ...(path==="/api/plans/options"?{resumable:data.diagnostics?.failureBoundary==="local_minute",
        ...(typeof data.continuation?.canExpand==="boolean"&&typeof data.continuation?.canDiscover==="boolean"
          ?{continuation:{canExpand:data.continuation.canExpand,canDiscover:data.continuation.canDiscover}}:{})}:{}),
    }), { status:response.status, headers });
    if (!response.ok) return Response.json(publicPlanningPayload({ code:recoveryCode(data.code), message: response.status === 422 && typeof data.message === "string" ? data.message : "Venue lookup is unavailable. Try again later.",diagnosticNotes:providerDiagnosticNotes(data.diagnostics),...(path==="/api/plans/options"?{resumable:data.diagnostics?.failureBoundary==="local_minute",...(typeof data.continuation?.canExpand==="boolean"&&typeof data.continuation?.canDiscover==="boolean"?{continuation:{canExpand:data.continuation.canExpand,canDiscover:data.continuation.canDiscover}}:{})}:{}),...(path==="/api/venues/details"&&typeof data.diagnostics?.contactRequestAdmitted==="boolean"?{diagnostics:{contactRequestAdmitted:data.diagnostics.contactRequestAdmitted}}:{}) }), { status: 422, headers });
    return Response.json(publicPlanningPayload(data), { headers });
  } catch {
    return Response.json({ message: "Venue lookup is temporarily unavailable. Please try again." }, { status: 503, headers });
  }
}
