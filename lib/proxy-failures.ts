// Server proxies never log response bodies or arbitrary exception messages.
export function invalidUpstreamResponse() {
  const correlationId=crypto.randomUUID().replaceAll("-","").slice(0,16);
  console.warn(`failure reference=${correlationId} code=internal_application_error operation=proxy_response`);
  return Response.json({code:"internal_application_error",message:"The planning service returned a response the app could not validate. This is an application error; retry or use the reference ID to investigate.",correlationId},
    {status:502,headers:{"Cache-Control":"no-store","X-Correlation-ID":correlationId}});
}
