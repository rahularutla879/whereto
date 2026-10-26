import { interpretedPreferences } from "./preferences";
import { recommendationCopy } from "./recommendation-copy";
import { realHeadlines } from "./real-headlines";
import { EMPTY_PREFERENCES, type Preferences, type PlannerResult, type Plan, type DisplayVenue } from "./planner";

// Pydantic JSON uses the existing camelCase names. This adapter only shapes cards;
// selection, scores, schedules, prices and travel all come from Python.
type Ranked = {
  candidate: { id: string; venues: DisplayVenue[]; people: number; date: string };
  feasibility: "confirmed" | "provisional";
  stops: Plan["stops"]; prices: Plan["prices"]; legs: Plan["legs"];
  costPerPerson: number | null; groupCost: number | null;
  totalTravel: number | null; elapsedDuration: number | null;
  issues: { code?: string; field?: string; status?: string; message: string }[];
  firstLeg?: Plan["firstLeg"]; routeEvidence?: Plan["routeEvidence"];
  score?: number; components?: { quality?: number };
};
type Ranking = { dataMode?: "mock" | "real"; detailsToken?: string; optionsToken?: string; canExpand?: boolean; canDiscover?: boolean; request: { location: string; activities: PlannerResult["activities"]; cost: string; budget?: number | null; groupBudget?: number | null; dinner?: boolean; dinnerStops?: number[] | null };
  plans: Ranked[]; provisionalPlans: Ranked[]; alternativeBatches?: Ranked[][]; message: string; notes: string[]; errors: { message: string }[] };

export function adaptRanking(value: unknown): PlannerResult {
  // Reject broken upstream responses instead of displaying misleading empty success.
  const data = value as Ranking;
  if (!data || !data.request || !Array.isArray(data.request.activities) || typeof data.request.location !== "string"
    || !Array.isArray(data.plans) || !Array.isArray(data.provisionalPlans) || typeof data.message !== "string"
    || !Array.isArray(data.notes) || !data.notes.every(n => typeof n === "string") || !Array.isArray(data.errors)
    || data.plans.length + data.provisionalPlans.length > 3) throw new Error("Invalid planning response");
  const real = data.dataMode === "real";
  if (data.dataMode !== undefined && !["mock", "real"].includes(data.dataMode)) throw new Error("Invalid data mode");
  if ([...data.plans, ...data.provisionalPlans].some(p => p.stops?.some(s => real
    ? !s.venue?.providerPlaceId || s.venue.id !== s.venue.providerPlaceId || s.venue.dataQuality?.identity !== "verified"
    : !!s.venue?.providerPlaceId))) throw new Error("Mixed venue data modes");
  const nullableNumber = (n: unknown) => n === null || (typeof n === "number" && Number.isFinite(n) && n >= 0);
  const selected = [...data.plans, ...data.provisionalPlans];
  if (data.alternativeBatches !== undefined && (!Array.isArray(data.alternativeBatches) || data.alternativeBatches.length > 2
    || (!real && data.alternativeBatches.length) || data.alternativeBatches.some(batch => !Array.isArray(batch) || batch.length < 1 || batch.length > 3))) throw new Error("Invalid additional options");
  for (const p of selected) {
    if (!p.candidate || typeof p.candidate.id !== "string" || !Array.isArray(p.stops) || !p.stops.length
      || !Array.isArray(p.candidate.venues) || p.stops.length !== data.request.activities.length
      || !Array.isArray(p.issues) || !p.issues.every(i => typeof i.message === "string")
      || !Array.isArray(p.prices) || p.prices.length !== p.stops.length
      || !Array.isArray(p.legs) || p.legs.length !== p.stops.length - 1
      || ![p.costPerPerson, p.groupCost, p.totalTravel, p.elapsedDuration].every(nullableNumber)
      || !Number.isInteger(p.candidate.people) || p.candidate.people < 1
      || !(typeof p.candidate.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(p.candidate.date))
      || !p.stops.every((s, i) => s.venue && typeof s.venue.id === "string" && typeof s.venue.name === "string"
        && s.venue.activity === data.request.activities[i] && nullableNumber(s.start) && nullableNumber(s.end)
        && nullableNumber(s.venue.duration) && nullableNumber(s.venue.capacity)
        && typeof s.venue.dataQuality === "object" && s.venue.dataQuality !== null)
      || !p.prices.every(q => nullableNumber(q.amount) && typeof q.status === "string")
      || !p.legs.every(q => nullableNumber(q.minutes) && typeof q.status === "string")) throw new Error("Invalid itinerary response");
  }
  if (data.plans.some(p => p.feasibility !== "confirmed") || data.provisionalPlans.some(p => p.feasibility !== "provisional")) throw new Error("Invalid feasibility response");
  const normalized = (value: unknown) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
  const copy = recommendationCopy(selected.map(p => ({
    score: normalized(p.score),
    quality: p.stops.every(s => typeof s.venue.experience === "number" && Number.isFinite(s.venue.experience) && s.venue.experience >= 0)
      ? normalized(p.components?.quality) : null,
    cost: p.costPerPerson, travel: p.totalTravel,
    venues: p.stops.map(s => ({ id: s.venue.id, name: s.venue.name })),
  })), data.request.cost);
  const themes = ["lavender", "peach", "mint"] as const;
  const headlines = real ? realHeadlines(selected.map(p => p.stops.map(s => s.venue)), data.request.dinnerStops ?? (data.request.dinner ? data.request.activities.flatMap((a, i) => a === "food" ? [i] : []) : [])) : [];
  const plans: Plan[] = selected.map((p, i) => ({
    dataMode: data.dataMode ?? "mock", location: data.request.location, detailsToken: data.detailsToken,
    constraintIssues: p.issues,
    hardBudget: data.request.budget != null || data.request.groupBudget != null,
    firstLeg: p.firstLeg, routeEvidence: p.routeEvidence,
    id: p.candidate.id, title: real ? headlines[i].title : copy[i].title, fullTitle: real ? headlines[i].fullTitle : undefined, theme: themes[i],
    label: real ? headlines[i].label : `${copy[i].label} · OPTION ${i + 1}`,
    description: real ? `${p.totalTravel === null ? "Travel is not fully verified" : `${p.totalTravel} estimated minutes between stops`}. Suggested for this venue combination${p.totalTravel === null ? "" : ", travel convenience"} and variety. ${p.stops.some(s => s.venue.rating != null && (s.venue.ratingCount ?? 0) > 0) ? "Google ratings and their counts also inform ranking." : "No rating evidence was used."}` : copy[i].description,
    venues: p.stops.map(s => s.venue), stops: p.stops, price: p.costPerPerson, groupCost: p.groupCost,
    travel: p.totalTravel, duration: p.elapsedDuration, people: p.candidate.people, date: p.candidate.date,
    feasibility: p.feasibility, issues: [...new Set(p.issues.map(i => i.message.replaceAll("openingHours", "Opening hours")))], prices: p.prices, legs: p.legs,
  }));
  const alternativeBatches = (data.alternativeBatches ?? []).map(batch => adaptRanking({ ...data, plans: [], provisionalPlans: batch, alternativeBatches: undefined }).plans);
  const identities = [...plans, ...alternativeBatches.flat()].map(p => p.venues.map(v => v.id).join("\u0000"));
  if (new Set(identities).size !== identities.length) throw new Error("Duplicate itinerary options");
  return { dataMode: data.dataMode ?? "mock", optionsToken: data.optionsToken, canExpand: data.canExpand, canDiscover: data.canDiscover, plans, alternativeBatches, location: data.request.location, activities: data.request.activities,
    message: plans.length ? data.message : [...new Set([data.message, ...data.errors.map(e => e.message.replaceAll("openingHours", "Opening hours"))])].join(" "), notes: data.notes };
}

export type ClarificationField = "location" | "people" | "date" | "activities" | "time";
export type ClarificationAnswers = Partial<Record<ClarificationField, string>>;
export type PendingOuting = {
  pending: { text: string; interpretation: unknown; answers: ClarificationAnswers; referenceTime: string };
  questions: { field: ClarificationField; question: string; kind: "essential" | "ambiguous";
    reason?: string | null; helpText?: string | null }[];
};

export type ValidatedOuting = {
  request: { location: string; date: string; people: number; activities: PlannerResult["activities"];
    budget: number | null; travel: number | null; cost: Preferences["cost"]; startTime: number; endTime: number;
    groupBudget: number | null; maxLegTravel: number | null; maxFirstLegTravel?: number | null; travelExclusive?: boolean; maxLegTravelExclusive?: boolean; maxFirstLegTravelExclusive?: boolean; transport: string | null;
    dinnerStops: number[] | null };
  continuation: PendingOuting;
  explicitCost: boolean;
  explicitTime: boolean;
};

export async function generateOuting(text: string, preferences: Preferences = EMPTY_PREFERENCES,
  context?: { locationContext?: LocationContext; onValidated?: (value: ValidatedOuting) => void; today?: string; onInterpreted?: (values: Preferences) => void;
    continuation?: PendingOuting; answers?: ClarificationAnswers;
    onClarification?: (value: PendingOuting | null) => void; onComplete?: () => void; signal?: AbortSignal }, send: typeof fetch = fetch): Promise<PlannerResult> {
  // Raw text goes to Python AI; the legacy keyword resolver is never called.
  // `today` remains source-compatible; only the Python resolver owns the clock.
  const failure = (message: string): PlannerResult => ({ plans: [], message, location: "",
    activities: [], notes: [], requestFailed: true });
  try {
    const interpreted = await send("/api/interpret", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, preferences, ...(context?.locationContext?.currentArea ? { hasCurrentLocation: true } : {}), ...(context?.continuation ? { pending: context.continuation.pending, answers: context.answers ?? {} } : {}) }), cache: "no-store", signal: context?.signal ? AbortSignal.any([context.signal, AbortSignal.timeout(75000)]) : AbortSignal.timeout(75000) });
    const extraction = await interpreted.json();
    if (!interpreted.ok) return failure(typeof extraction?.message === "string" ? extraction.message : "AI interpretation unavailable. No plan was generated.");
    if (!Array.isArray(extraction?.issues) || !extraction.issues.every((s: unknown) => typeof s === "string")
      || !Array.isArray(extraction.notes) || !extraction.notes.every((s: unknown) => typeof s === "string")) throw new Error("Invalid interpretation response");
    if (extraction.pending) {
      const fields = ["location", "people", "date", "activities", "time"];
      if (extraction.pending.text !== text || !extraction.pending.interpretation
        || typeof extraction.pending.referenceTime !== "string" || !extraction.pending.answers
        || !Array.isArray(extraction.questions) || !extraction.questions.every((q: PendingOuting["questions"][number]) =>
          q && fields.includes(q.field) && typeof q.question === "string" && ["essential", "ambiguous"].includes(q.kind)
          && (q.reason == null || typeof q.reason === "string") && (q.helpText == null || typeof q.helpText === "string"))) throw new Error("Invalid clarification response");
      // A continuation is also returned for complete requests. Keep it in
      // onValidated for regeneration/retry; only actual questions are visible.
      if (extraction.questions.length) context?.onClarification?.({ pending: extraction.pending, questions: extraction.questions });
      else if (extraction.issues.length) context?.onClarification?.(null);
    } else if (extraction.issues.length) context?.onClarification?.(null);
    if (extraction.issues.length || !extraction.request) {
      return { ...failure(extraction.issues.join(" ") || "More information is needed before planning."), requestFailed: false, notes: extraction.notes };
    }
    context?.signal?.throwIfAborted();
    const extractedPreferences = interpretedPreferences(extraction.request);
    context?.onInterpreted?.(extractedPreferences);
    if (extraction.pending) context?.onValidated?.({ request: { ...extraction.request,
      ...(context?.locationContext?.maxFirstLegTravel !== undefined ? { maxFirstLegTravel: context.locationContext.maxFirstLegTravel, maxFirstLegTravelExclusive: false } : {}) },
      continuation: { pending: extraction.pending, questions: [] },
      explicitCost: !!preferences.costExplicit || preferences.cost !== "balanced" || extraction.interpretation?.cost != null,
      explicitTime: !!extraction.interpretation?.time_expressions?.length || !!extraction.pending.answers?.time });
    const response = await send("/api/plans/generate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...extraction.request, ...(context?.locationContext ?? {}), ...(context?.locationContext?.maxFirstLegTravel !== undefined ? { maxFirstLegTravelExclusive: false } : {}) }), cache: "no-store", signal: context?.signal ? AbortSignal.any([context.signal, AbortSignal.timeout(120000)]) : AbortSignal.timeout(120000) });
    if (!response.ok) {
      if (response.status === 400 || response.status === 422) {
        const error = await response.json();
        return failure(typeof error.message === "string" ? error.message : "Invalid outing request. Check your preferences and try again.");
      }
      return failure("Python planner unavailable. Start the backend and try again. No plan was generated.");
    }
    const result = adaptRanking(await response.json());
    result.notes = [...extraction.notes.filter((note: string) => result.dataMode !== "real" || !note.includes("Mock travel is mode-independent")), ...result.notes];
    context?.onComplete?.();
    return result;
  } catch {
    return failure("AI interpretation or Python planner unavailable, timed out, or returned an invalid response. Check both services and retry. No plan was generated.");
  }
}


export type LocationContext = {
  manualStartingPlace?: string;
  startingLocation?: { point: { id: string; coordinates: { latitude: number; longitude: number } }; explicitly_authorized: true; precision?: "device" | "address_or_place" | "postal_area" | "neighborhood" | "city" | "approximate_area" };
  currentArea?: { coordinates: { latitude: number; longitude: number } };
  searchRadius?: number; maxFirstLegTravel?: number;
};
