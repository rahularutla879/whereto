export const TOKEN = /^[A-Za-z0-9_-]{43}$/;
export const SAVED_KEY = "whereto.private-plan.v1";
export function privateLink(origin: string, token: string) {
  if (!TOKEN.test(token)) throw new Error("Invalid private link");
  return `${origin}/#saved=${token}`;
}
export function fragmentToken(hash: string): string | undefined {
  const value = /^#saved=([A-Za-z0-9_-]{43})$/.exec(hash)?.[1];
  return value && TOKEN.test(value) ? value : undefined;
}

export type SavedPlan = {
  hoursRefreshAvailable?:boolean;
  version: 1 | 2; saved: true; dataMode: "mock" | "real"; selectedId: string; expiresAt: string; liveDetailsAvailable: false;
  constraints: { location: string; date: string; activities: string[]; activityIntents: Record<string,string>; startTime: number; endTime: number; explicitStart?: boolean; explicitEnd?: boolean;
    maxFirstLegTravelExclusive?:boolean; maxLegTravelExclusive?:boolean; travelExclusive?:boolean;
    planningMode: "origin" | "surprise"; transport: string | null; calendarTimezone: string | null;
    firstTravel: Preference | null; betweenTravel: Preference | null; maxFirstLegTravel: number | null; maxLegTravel: number | null;
    travel: number | null; geography: { strictDestination: boolean; excludedRegions: string[] };
    budget?:number|null;groupBudget?:number|null;
    dinner: boolean; dinnerStops: number[] | null; requireAvailability: boolean; requireWheelchairAccess: boolean; allowRevisits: boolean };
  itineraries: { advanced?: {budgetScope?:'outing'|'travel';durationOverrides?:number[];departureOverride?:boolean;travelException?:boolean;sourceText:string;journey:{stops:{source:string;kind:string;requirement:string;duration:import('./advanced-planning').Dwell|null}[];ordering:string;order:{before:number;after:number}[];endpoint:{kind:string;source:string}|null;total_duration:import('./advanced-planning').Dwell|null;deadline:{source:string;relation:string;minute:number|null}|null};occurrenceOrder:number[];omittedOccurrences:number[];ending:string;endpointId:string|null;historicalTiming:string;departureMinute:number|null}|null; candidateId: string; stops: { position: number; activity: string; provider: "mock" | "google_places"; reference: string;
    timingBasis: "unknown" | "fictional"; start: number | null; end: number | null; duration: number | null;
    fictional: { name: string; neighborhood: string | null; price: number | null } | null }[];
    fictionalMetrics: { totalTravel: number | null; legs: (number | null)[] } | null }[];
};
type Preference = { value: number; unit: string; mode: string; exclusive: boolean };
export function preferenceText(value: Preference | null) {
  return value ? `${value.mode === "flexible" ? "Flexible" : "Strict"}: ${value.exclusive ? "under" : "up to"} ${value.value} ${value.unit}${value.mode === "flexible" ? ` preferred; maximum ${value.value * 2} ${value.unit}` : ""}` : "No preference";
}
export function validateSaved(value: unknown): SavedPlan {
  const data = value as SavedPlan;
  if (!data || ![1,2].includes(data.version) || data.saved !== true || data.liveDetailsAvailable !== false || !["mock","real"].includes(data.dataMode)
    || !data.constraints || !Array.isArray(data.constraints.activities) || !Array.isArray(data.itineraries) || !data.itineraries.length || data.itineraries.length > 3
    || !data.itineraries.some(p => p.candidateId === data.selectedId)
    || data.itineraries.some(p => !Array.isArray(p.stops) || p.stops.length !== (p.advanced?.occurrenceOrder.length??data.constraints.activities.length) || (data.version===2)!==!!p.advanced
      || p.stops.some((s,i) => s.position !== i || s.activity !== data.constraints.activities[p.advanced?.occurrenceOrder[i]??i] || typeof s.reference !== "string"
        || (data.dataMode === "real" && (s.provider !== "google_places" || s.fictional !== null || s.start !== null || s.end !== null || s.duration !== null || p.fictionalMetrics !== null))))) throw new Error("Saved plan is incomplete or unavailable.");
  if(data.version===2&&data.itineraries.some(p=>{
    const a=p.advanced;if(!a||data.dataMode!=='real'||a.journey.stops.length!==data.constraints.activities.length)return true;
    const indexes=[...a.occurrenceOrder,...a.omittedOccurrences].sort((x,y)=>x-y);
    return indexes.length!==a.journey.stops.length||indexes.some((n,i)=>n!==i)||a.omittedOccurrences.some(n=>a.journey.stops[n].requirement!=='optional')||a.journey.order.some(e=>a.occurrenceOrder.includes(e.before)&&a.occurrenceOrder.includes(e.after)&&a.occurrenceOrder.indexOf(e.before)>=a.occurrenceOrder.indexOf(e.after));
  }))throw Error("Saved advanced requirements are incomplete.");
  return {...data,constraints:{...data.constraints,transport:data.constraints.transport??"driving"}};
}
