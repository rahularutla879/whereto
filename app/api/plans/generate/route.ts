import {privateRoute} from "@/lib/private-server-boundary";
import { publicPlanningPayload } from "@/lib/public-planning-payload";
import { invalidUpstreamResponse } from "@/lib/proxy-failures";
import { classifiedFailure } from "@/lib/failure-diagnostics";
import { developmentOriginHeaders } from "../../../../lib/development-origin";
import { adaptRanking } from "../../../../lib/planning-client";

import {timingHeaders} from "@/lib/server-timing";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const isolated=privateRoute("/api/plans/generate",request);if(isolated)return isolated;
  const started=performance.now();
  const headers:Record<string,string> = { "Cache-Control": "no-store" };
  let payload: unknown;
  try { payload = await request.json(); }
  catch { return Response.json({ code: "invalid_request", message: "Enter your outing and try again." }, { status: 400, headers }); }
  let received=false;
  try {
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}/api/plans/generate`, {
      method: "POST", headers: { "Content-Type": "application/json", ...developmentOriginHeaders(request) }, body: JSON.stringify(payload),
      cache: "no-store", signal: AbortSignal.any([request.signal, AbortSignal.timeout(115000)]),
    });
    received=true;
    const data: unknown = await response.json();
    Object.assign(headers,timingHeaders(response.headers.get("server-timing"),performance.now()-started));
    if (!response.ok && classifiedFailure(data)) return Response.json(publicPlanningPayload(classifiedFailure(data)), { status:response.status, headers });
    if (response.status === 422) {
      const error = data as { code?: string; message?: string };
      if (!error || typeof error.message !== "string") throw new Error("Invalid validation response");
      return Response.json(data, { status: 422, headers });
    }
    if (!response.ok) throw new Error("Backend failed");
    adaptRanking(data);
    return Response.json(publicPlanningPayload(data), { headers });
  } catch {
    if(received) return invalidUpstreamResponse();
    return Response.json({ code: "backend_unavailable", message: "We’re having trouble creating your plans right now. Please try again." }, { status: 503, headers });
  }
}
