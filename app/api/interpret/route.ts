import { classifiedFailure } from "@/lib/failure-diagnostics";
import {timingHeaders} from "@/lib/server-timing";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const started=performance.now();
  const headers:Record<string,string> = { "Cache-Control": "no-store" };
  let payload: unknown;
  try { payload = await request.json(); }
  catch { return Response.json({ code: "invalid_request", message: "Enter your outing and try again." }, { status: 400, headers }); }
  let received = false;
  try {
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}/api/interpret`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      cache: "no-store", signal: AbortSignal.any([request.signal, AbortSignal.timeout(70000)]),
    });
    received = true;
    const data = await response.json();
    Object.assign(headers,timingHeaders(response.headers.get("server-timing"),performance.now()-started));
    if (!response.ok && classifiedFailure(data)) {
      return Response.json(classifiedFailure(data), { status: response.status, headers });
    }
    if (response.status === 422 || response.status === 503) {
      if (typeof data?.message !== "string") throw new Error("Invalid error response");
      return Response.json(data, { status: response.status, headers });
    }
    if (!response.ok || !data?.interpretation || !Array.isArray(data.issues)
      || !data.issues.every((s: unknown) => typeof s === "string")
      || !Array.isArray(data.notes) || !data.notes.every((s: unknown) => typeof s === "string")
      || !(data.request === null || (typeof data.request === "object" && Array.isArray(data.request.activities)))) throw new Error("Invalid interpretation response");
    return Response.json(data, { headers });
  } catch {
    return Response.json(received
      ? { code: "llm_invalid_response", message: "We couldn't finish understanding that request. Please try again or edit the wording." }
      : { code: "ai_unavailable", message: "We're having trouble planning your outing right now. Please try again." }, { status: 503, headers });
  }
}
