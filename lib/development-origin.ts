// Carry the original browser boundary through localhost Next→Python proxies.
// Backend exploration admission validates these; normal mode ignores them.
export function developmentOriginHeaders(request?: Request): Record<string,string> {
  if (!request) return {};
  const host = request.headers.get("host") ?? new URL(request.url).host;
  const loopback = new Set(["localhost", "127.0.0.1", "::1", "[::1]", "::ffff:127.0.0.1"]);
  const forwardedFor = request.headers.get("x-forwarded-for");
  const forwardedHost = request.headers.get("x-forwarded-host");
  let nonlocalForwarding = request.headers.has("forwarded") || !!forwardedFor?.split(",").some(ip=>!loopback.has(ip.trim()));
  try { nonlocalForwarding ||= !!forwardedHost && !loopback.has(new URL(`http://${forwardedHost}`).hostname); }
  catch { nonlocalForwarding = true; }
  return {
    "X-WhereTo-Client-Host": host,
    "X-WhereTo-Client-Origin": request.headers.get("origin") ?? "",
    "X-WhereTo-Proxied": nonlocalForwarding ? "1" : "0",
  };
}
