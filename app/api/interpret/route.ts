import {timingHeaders} from "@/lib/server-timing";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const started=performance.now();
  const headers:Record<string,string> = { "Cache-Control": "no-store" };
  let payload: unknown;
  try { payload = await request.json(); }
  catch { return Response.json({ code: "invalid_request", message: "Send a JSON outing request." }, { status: 400, headers }); }
  try {
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}/api/interpret`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      cache: "no-store", signal: AbortSignal.timeout(70000),
    });
    const data = await response.json();
    Object.assign(headers,timingHeaders(response.headers.get("server-timing"),performance.now()-started));
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
    return Response.json({ code: "ai_unavailable", message: "AI interpretation unavailable or timed out. Start the Python backend and local AI service, then retry. No plan was generated." }, { status: 503, headers });
  }
}
