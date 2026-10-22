import { interpretedPreferences } from "./preferences";
import { recommendationCopy } from "./recommendation-copy";
import { EMPTY_PREFERENCES, type Preferences, type PlannerResult, type Plan, type DisplayVenue } from "./planner";

// Pydantic JSON uses the existing camelCase names. This adapter only shapes cards;
// selection, scores, schedules, prices and travel all come from Python.
type Ranked = {
  candidate: { id: string; venues: DisplayVenue[]; people: number; date: string };
  feasibility: "confirmed" | "provisional";
  stops: Plan["stops"]; prices: Plan["prices"]; legs: Plan["legs"];
  costPerPerson: number | null; groupCost: number | null;
  totalTravel: number | null; elapsedDuration: number | null;
  issues: { message: string }[];
  score?: number; components?: { quality?: number };
};
type Ranking = { request: { location: string; activities: PlannerResult["activities"]; cost: string };
  plans: Ranked[]; provisionalPlans: Ranked[]; message: string; notes: string[]; errors: { message: string }[] };

export function adaptRanking(value: unknown): PlannerResult {
  // Reject broken upstream responses instead of displaying misleading empty success.
  const data = value as Ranking;
  if (!data || !data.request || !Array.isArray(data.request.activities) || typeof data.request.location !== "string"
    || !Array.isArray(data.plans) || !Array.isArray(data.provisionalPlans) || typeof data.message !== "string"
    || !Array.isArray(data.notes) || !data.notes.every(n => typeof n === "string") || !Array.isArray(data.errors)
    || data.plans.length + data.provisionalPlans.length > 3) throw new Error("Invalid planning response");
  const nullableNumber = (n: unknown) => n === null || (typeof n === "number" && Number.isFinite(n) && n >= 0);
  const selected = [...data.plans, ...data.provisionalPlans];
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
  const plans: Plan[] = selected.map((p, i) => ({
    id: p.candidate.id, title: copy[i].title, theme: themes[i],
    label: `${copy[i].label} · OPTION ${i + 1}`,
    description: copy[i].description,
    venues: p.stops.map(s => s.venue), stops: p.stops, price: p.costPerPerson, groupCost: p.groupCost,
    travel: p.totalTravel, duration: p.elapsedDuration, people: p.candidate.people, date: p.candidate.date,
    feasibility: p.feasibility, issues: [...new Set(p.issues.map(i => i.message.replaceAll("openingHours", "Opening hours")))], prices: p.prices, legs: p.legs,
  }));
  return { plans, location: data.request.location, activities: data.request.activities,
    message: plans.length ? data.message : [data.message, ...data.errors.map(e => e.message.replaceAll("openingHours", "Opening hours"))].join(" "), notes: data.notes };
}

export type ClarificationField = "location" | "people" | "date" | "activities" | "time";
export type ClarificationAnswers = Partial<Record<ClarificationField, string>>;
export type PendingOuting = {
  pending: { text: string; interpretation: unknown; answers: ClarificationAnswers; referenceTime: string };
  questions: { field: ClarificationField; question: string; kind: "essential" | "ambiguous" }[];
};

export type ValidatedOuting = {
  request: { location: string; date: string; people: number; activities: PlannerResult["activities"];
    budget: number | null; travel: number | null; cost: Preferences["cost"]; startTime: number; endTime: number;
    groupBudget: number | null; maxLegTravel: number | null; transport: string | null;
    dinnerStops: number[] | null };
  continuation: PendingOuting;
  explicitCost: boolean;
  explicitTime: boolean;
};

export async function generateOuting(text: string, preferences: Preferences = EMPTY_PREFERENCES,
  context?: { onValidated?: (value: ValidatedOuting) => void; today?: string; onInterpreted?: (values: Preferences) => void;
    continuation?: PendingOuting; answers?: ClarificationAnswers;
    onClarification?: (value: PendingOuting | null) => void; onComplete?: () => void; signal?: AbortSignal }, send: typeof fetch = fetch): Promise<PlannerResult> {
  // Raw text goes to Python AI; the legacy keyword resolver is never called.
  // `today` remains source-compatible; only the Python resolver owns the clock.
  const failure = (message: string): PlannerResult => ({ plans: [], message, location: "",
    activities: [], notes: [] });
  try {
    const interpreted = await send("/api/interpret", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, preferences, ...(context?.continuation ? { pending: context.continuation.pending, answers: context.answers ?? {} } : {}) }), cache: "no-store", signal: context?.signal ? AbortSignal.any([context.signal, AbortSignal.timeout(75000)]) : AbortSignal.timeout(75000) });
    const extraction = await interpreted.json();
    if (!interpreted.ok) return failure(typeof extraction?.message === "string" ? extraction.message : "AI interpretation unavailable. No plan was generated.");
    if (!Array.isArray(extraction?.issues) || !extraction.issues.every((s: unknown) => typeof s === "string")
      || !Array.isArray(extraction.notes) || !extraction.notes.every((s: unknown) => typeof s === "string")) throw new Error("Invalid interpretation response");
    if (extraction.pending) {
      const fields = ["location", "people", "date", "activities", "time"];
      if (extraction.pending.text !== text || !extraction.pending.interpretation
        || typeof extraction.pending.referenceTime !== "string" || !extraction.pending.answers
        || !Array.isArray(extraction.questions) || !extraction.questions.every((q: PendingOuting["questions"][number]) =>
          q && fields.includes(q.field) && typeof q.question === "string" && ["essential", "ambiguous"].includes(q.kind))) throw new Error("Invalid clarification response");
      context?.onClarification?.({ pending: extraction.pending, questions: extraction.questions });
    } else if (extraction.issues.length) context?.onClarification?.(null);
    if (extraction.issues.length || !extraction.request) {
      return { ...failure(extraction.issues.join(" ") || "More information is needed before planning."), notes: extraction.notes };
    }
    context?.signal?.throwIfAborted();
    const extractedPreferences = interpretedPreferences(extraction.request);
    context?.onInterpreted?.(extractedPreferences);
    if (extraction.pending) context?.onValidated?.({ request: extraction.request,
      continuation: { pending: extraction.pending, questions: [] },
      explicitCost: !!preferences.costExplicit || preferences.cost !== "balanced" || extraction.interpretation?.cost != null,
      explicitTime: !!extraction.interpretation?.time_expressions?.length || !!extraction.pending.answers?.time });
    const response = await send("/api/plans/generate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(extraction.request), cache: "no-store", signal: context?.signal ? AbortSignal.any([context.signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) });
    if (!response.ok) {
      if (response.status === 400 || response.status === 422) {
        const error = await response.json();
        return failure(typeof error.message === "string" ? error.message : "Invalid outing request. Check your preferences and try again.");
      }
      return failure("Python planner unavailable. Start the backend and try again. No plan was generated.");
    }
    const result = adaptRanking(await response.json());
    result.notes = [...extraction.notes, ...result.notes];
    context?.onComplete?.();
    return result;
  } catch {
    return failure("AI interpretation or Python planner unavailable, timed out, or returned an invalid response. Check both services and retry. No plan was generated.");
  }
}
