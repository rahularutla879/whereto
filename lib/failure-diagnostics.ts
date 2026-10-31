// Accept only stable error categories and opaque correlation IDs from the backend.
const CODES = new Set(["database_not_configured","database_runtime_role_required","database_connection_failed","database_authentication_failed","database_access_denied","save_validation_failed","save_reference_expired","save_transaction_failed","saved_link_unavailable","llm_interpretation_failed","no_relevant_venues","insufficient_routing","provider_quota_rejected","provider_service_error","venue_refresh_disabled","venue_refresh_limit","internal_application_error","local_request_required"]);
export function classifiedFailure(value: unknown): {code:string;message:string;correlationId?:string;diagnostics?:Record<string,unknown>} | undefined {
  if (!value || typeof value !== "object") return;
  const data=value as Record<string,unknown>;
  if(typeof data.code!=="string" || !CODES.has(data.code) || typeof data.message!=="string" || data.message.length>600) return;
  const correlationId=typeof data.correlationId==="string" && /^[a-f0-9]{16}$/.test(data.correlationId) ? data.correlationId : undefined;
  return {code:data.code,message:data.message,...(correlationId?{correlationId}: {}),...(data.diagnostics && typeof data.diagnostics==="object" ? {diagnostics:data.diagnostics as Record<string,unknown>}: {})};
}
export function failureText(value: unknown, fallback: string): string {
  const failure=classifiedFailure(value);
  return failure ? `${failure.message}${failure.correlationId?` Reference: ${failure.correlationId}.`:""}` : fallback;
}
