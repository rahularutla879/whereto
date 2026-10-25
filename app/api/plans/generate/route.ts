import { adaptRanking } from "../../../../lib/planning-client";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const headers = { "Cache-Control": "no-store" };
  let payload: unknown;
  try { payload = await request.json(); }
  catch { return Response.json({ code: "invalid_request", message: "Invalid request: send a JSON outing request." }, { status: 400, headers }); }
  try {
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}/api/plans/generate`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      cache: "no-store", signal: AbortSignal.timeout(115000),
    });
    const data: unknown = await response.json();
    if (response.status === 422) {
      const error = data as { code?: string; message?: string };
      if (!error || typeof error.message !== "string") throw new Error("Invalid validation response");
      return Response.json(data, { status: 422, headers });
    }
    if (!response.ok) throw new Error("Backend failed");
    adaptRanking(data);
    return Response.json(data, { headers });
  } catch {
    return Response.json({ code: "backend_unavailable", message: "Python planner unavailable. Start the backend and try again. No plan was generated." }, { status: 503, headers });
  }
}
