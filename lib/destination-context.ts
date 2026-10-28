// Intent only: never infers coordinates or claims a place was resolved.
export type DestinationContext = {
  originalText: string;
  intent: "explicit" | "current_relative" | "missing" | "unresolved";
  status: "resolved" | "ambiguous" | "unresolved" | "verification_unavailable";
  source: "request" | "confirmed_anchor" | "provider_components" | "browser";
  precision: "named_area" | "representative_point" | "unknown";
  timezone?: string | null;
};
export function currentRelative(text: string) {
  return /\b(?:near\s+(?:me|my current location)|around\s+(?:me|here|my location)|close to me|in my area|nearby)\b/i.test(text)
    && !/\bin\s+(?!my area\b|my location\b|the (?:evening|morning|afternoon|city)\b|a\b|an\b|walking distance\b|driving distance\b)[a-z]/i.test(text);
}
export function explicitOrigin(text: string) {
  return /\bstarting from\s+([^.,;!?]+?)(?=\s+(?:today|tomorrow|for \d)|[.,;!?]|$)/i.exec(text)?.[1]?.trim();
}
export function recoveryCode(value: unknown): string | undefined {
  return typeof value==="string" && ["outing_date_expired","outing_time_expired","expired","destination_unresolved","destination_ambiguous","destination_verification_unavailable","geographic_verification"].includes(value) ? value : undefined;
}
