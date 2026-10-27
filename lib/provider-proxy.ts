import { developmentOriginHeaders } from "./development-origin";
// Fixed server-only upstream paths; never forward arbitrary URLs or credentials.
export async function providerProxy(path: "/api/planning-mode" | "/api/venues/details" | "/api/starting-places" | "/api/plans/options", request?: Request) {
  const headers = { "Cache-Control": "no-store" };
  try {
    const body = request ? JSON.stringify(await request.json()) : undefined;
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method: request ? "POST" : "GET", body, headers: { "Content-Type": "application/json", ...developmentOriginHeaders(request) },
      cache: "no-store", signal: AbortSignal.timeout(path === "/api/plans/options" ? 115000 : 30000),
    });
    const data = await response.json();
    if (!response.ok) return Response.json({ message: response.status === 422 && typeof data.message === "string" ? data.message : "Venue lookup is unavailable. Try again later." }, { status: 422, headers });
    return Response.json(data, { headers });
  } catch {
    return Response.json({ message: "Venue lookup is unavailable. Check that the local backend is running." }, { status: 503, headers });
  }
}
