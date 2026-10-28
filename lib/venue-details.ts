export type Credit = { provider?: string | null; uri?: string | null };
export type ContactDetails = { phone: string | null; telephoneUrl: string | null; website: string | null; attributions: Credit[] };
export function safeWebsite(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password ? url.href : null; } catch { return null; }
}
export class ContactLookupError extends Error {
  constructor(message:string,readonly notAdmitted=false){super(message);}
}
export class VenueDetailsSession {
  private requests = new Map<string, Promise<ContactDetails>>();
  clear() { this.requests.clear(); }
  retryUnsent(token:string,placeId:string){this.requests.delete(token+":"+placeId);}
  get(token: string, placeId: string, send: typeof fetch = fetch) {
    const key = `${token}:${placeId}`;
    let response = this.requests.get(key);
    if (!response) {
      response = (async () => {
        const result = await send("/api/venues/details", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, placeId }), cache: "no-store", signal: AbortSignal.timeout(35000) });
        const data = await result.json();
        if (!result.ok) throw new ContactLookupError(typeof data.message === "string" ? data.message : "Contact lookup is unavailable.",data.diagnostics?.contactRequestAdmitted===false);
        if (data.placeId !== placeId) throw new Error("Venue contact details could not be verified.");
        return { phone: typeof data.phone === "string" ? data.phone : null,
          telephoneUrl: typeof data.telephoneUrl === "string" && /^tel:\+?\d{7,15}$/.test(data.telephoneUrl) ? data.telephoneUrl : null,
          website: safeWebsite(data.website), attributions: Array.isArray(data.attributions) ? data.attributions : [] };
      })();
      this.requests.set(key, response);
    }
    return response;
  }
}
