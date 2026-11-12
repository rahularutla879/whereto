import {privateRoute} from "@/lib/private-server-boundary";
export const runtime = "nodejs";

export function GET():Promise<Response>;
export function GET(request:Request):Promise<Response>;
export async function GET(request?:Request) {
  const isolated=privateRoute("/api/health",request);if(isolated)return isolated;
  const headers = { "Cache-Control": "no-store" };

  try {
    const baseUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) throw new Error("Backend health request failed");

    const data: unknown = await response.json();
    if (typeof data !== "object" || data === null || !("status" in data) || data.status !== "ok") {
      throw new Error("Unexpected backend health response");
    }

    return Response.json({ status: "ok", backend: "ok" }, { headers });
  } catch {
    return Response.json({ status: "error", backend: "unavailable" }, { status: 503, headers });
  }
}
