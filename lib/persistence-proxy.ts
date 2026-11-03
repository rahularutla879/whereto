import {timingHeaders} from "./server-timing";
import { publicPlanningPayload } from "./public-planning-payload";
import { classifiedFailure } from "./failure-diagnostics";
import { developmentOriginHeaders } from "./development-origin";

export async function persistenceProxy(path: "/api/plans/save" | "/api/plans/reopen" | "/api/plans/refresh" | "/api/plans/advanced", request: Request) {
  const started=performance.now();
  const advanced=path==="/api/plans/advanced";
  const headers = { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" };
  const url = new URL(request.url);
  const origin = request.headers.get("origin");
  const host = request.headers.get("host") ?? url.host;
  const loopback = new Set(["localhost", "127.0.0.1", "::1", "[::1]", "::ffff:127.0.0.1"]);
  let valid = false;
  try {
    // Next rewrites request.url to localhost and adds an IPv4-mapped loopback
    // forwarding address. Compare browser Origin to the actual incoming Host.
    valid = loopback.has(new URL(`${url.protocol}//${host}`).hostname)
      && (!origin || origin === `${url.protocol}//${host}`)
      && !request.headers.has("forwarded")
      && (!request.headers.has("x-forwarded-host") || request.headers.get("x-forwarded-host") === host)
      && (!request.headers.has("x-forwarded-for") || request.headers.get("x-forwarded-for")!.split(",").every(ip=>loopback.has(ip.trim())))
      && request.headers.get("sec-fetch-site") !== "cross-site";
  } catch { valid = false; }
  if (!valid) return Response.json({ message: "Private plans accept same-origin local requests only." }, { status: 403, headers });
  try {
    const reader = request.body?.getReader();
    const chunks: Uint8Array[] = []; let size = 0;
    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 4096) { await reader.cancel(); return Response.json({ message: "Save request is too large." }, { status: 413, headers }); }
        chunks.push(value);
      }
    }
    const body = Buffer.concat(chunks).toString("utf8");
    try {
      const payload = JSON.parse(body);
      if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error();
    } catch {
      return Response.json({ message: "Saved-plan request is invalid." }, { status: 422, headers });
    }
    const base = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method: "POST", body, headers: { "Content-Type": "application/json", ...developmentOriginHeaders(request), "X-WhereTo-Proxied":"0" },
      cache: "no-store", signal: AbortSignal.any([request.signal, AbortSignal.timeout(45000)]),
    });
    const data = await response.json();
    Object.assign(headers,timingHeaders(response.headers.get("server-timing"),performance.now()-started));
    if(advanced&&!response.ok&&typeof data?.message==='string')return Response.json(publicPlanningPayload(data),{status:response.status,headers});
    if (!response.ok && classifiedFailure(data)) return Response.json(publicPlanningPayload(classifiedFailure(data)), { status:response.status, headers });
    if (!response.ok) return Response.json({ message: response.status === 404 ? "Saved plan unavailable. The link may be invalid, inaccessible or expired."
      : response.status === 409 ? "Save reference expired or changed. Generate plans again before saving."
      : "Saved plans are unavailable. Your current itinerary is kept; try again later." }, { status: [404,409,413,422].includes(response.status) ? response.status : 503, headers });
    return Response.json(publicPlanningPayload(data), { headers });
  } catch {
    return Response.json({ message: advanced?"Advanced planning is unavailable. Your current request and itinerary are kept; try again.":"Saved plans are unavailable. Your current itinerary is kept; check the backend and try again." }, { status: 503, headers });
  }
}
