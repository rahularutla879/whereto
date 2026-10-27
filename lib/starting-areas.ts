import type { StartingMatch } from "./starting-places";
export type FirstTravel = { value: number; unit: "minutes" | "miles"; mode: "strict" | "flexible"; exclusive?: boolean; originText?: string | null };
export type Geography = { strictDestination: boolean; excludedRegions: ("VA" | "MD" | "DC")[] };
export type OriginPreparation = { location: string; activities: string[]; transport: string | null; firstTravel?: FirstTravel | null; geography?: Geography };
export type StartingSuggestion = StartingMatch & { reason: string; score: number };
export class StartingAreaSession {
  private responses = new Map<string, Promise<{ matches: StartingSuggestion[]; referenceToken?: string }>>();
  clear() { this.responses.clear(); }
  get(input: OriginPreparation, send: typeof fetch = fetch) {
    const body={destination:input.location,activities:input.activities,transport:input.transport ?? "driving",firstTravel:input.firstTravel ?? null,geography:input.geography ?? {strictDestination:false,excludedRegions:[]}};
    const key=JSON.stringify(body);
    let response=this.responses.get(key);
    if (!response) {
      response=(async()=>{
        const res=await send("/api/starting-areas",{method:"POST",headers:{"Content-Type":"application/json"},body:key,cache:"no-store",signal:AbortSignal.timeout(115000)});
        const data=await res.json();
        if (!res.ok) throw new Error(typeof data.message==="string"?data.message:"Starting-area suggestions are unavailable.");
        if (!Array.isArray(data.matches)||data.matches.length>3||!data.matches.every((p:StartingSuggestion)=>p && ["address_or_place","postal_area","neighborhood","city","approximate_area"].includes(p.precision) && Array.isArray(p.attributions) && Number.isFinite(p.score) && typeof p.placeId==="string"&&typeof p.name==="string"&&typeof p.address==="string"&&typeof p.reason==="string"&&Number.isFinite(p.coordinates?.latitude)&&Math.abs(p.coordinates.latitude)<=90&&Number.isFinite(p.coordinates?.longitude)&&Math.abs(p.coordinates.longitude)<=180)) throw new Error("Starting-area facts could not be verified.");
        return {matches:data.matches as StartingSuggestion[],referenceToken:typeof data.referenceToken==="string"?data.referenceToken:undefined};
      })();
      this.responses.set(key,response);
    }
    return response;
  }
}
