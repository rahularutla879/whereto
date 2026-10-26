import type { Credit } from "./venue-details";
export type StartingMatch = { placeId: string; name: string; address: string; coordinates: { latitude: number; longitude: number }; precision: "address_or_place" | "postal_area" | "neighborhood" | "city" | "approximate_area"; attributions: Credit[] };
export class StartingPlaceSession {
  private responses = new Map<string, Promise<StartingMatch[]>>();
  clear() { this.responses.clear(); }
  get(query: string, send: typeof fetch = fetch) {
    const key = query.trim().toLocaleLowerCase();
    let response = this.responses.get(key);
    if (!response) {
      response = (async () => {
        const res = await send("/api/starting-places", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: query.trim() }), cache: "no-store", signal: AbortSignal.timeout(35000) });
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.message === "string" ? data.message : "Starting-place search is unavailable.");
        if (!Array.isArray(data.matches) || data.matches.length > 3 || !data.matches.every((v: StartingMatch) => v && typeof v.name === "string" && typeof v.address === "string" && typeof v.placeId === "string" && ["address_or_place", "postal_area", "neighborhood", "city", "approximate_area"].includes(v.precision) && typeof v.coordinates?.latitude === "number" && Number.isFinite(v.coordinates.latitude) && Math.abs(v.coordinates.latitude) <= 90 && typeof v.coordinates.longitude === "number" && Number.isFinite(v.coordinates.longitude) && Math.abs(v.coordinates.longitude) <= 180)) throw new Error("Starting-place matches could not be verified.");
        return data.matches as StartingMatch[];
      })();
      this.responses.set(key, response);
    }
    return response;
  }
}
