import { ACTIVITY_LABELS, CATALOG, MOCK_EVENT_DATES, type Activity, type Venue } from "./mock-data";
import { parseRequest, resolveDate, todayInBaltimore, validDate } from "./request";
export { activityLabel, ACTIVITY_LABELS, MOCK_EVENT_DATES, VENUES } from "./mock-data";
export type { Activity, Venue } from "./mock-data";

export type CostPreference = "budget" | "balanced" | "experience";
export type Preferences = { location: string; date: string; people: string; budget: string; travel: string; cost: CostPreference; costExplicit?: boolean; transport?: "" | "driving" | "walking" };
export type OutingPayload = { activities: Activity[]; location: string; people?: number | null; date: string | null;
  budget: number | null; travel: number | null; cost: CostPreference; dinner: boolean };
export type Quality = Record<string, string>;
export type DisplayVenue = Omit<Venue, "price" | "duration" | "capacity" | "neighborhood"> & {
  price: number | null; duration: number | null; capacity: number | null; neighborhood: string | null;
  providerPlaceId?: string | null; address?: string | null; mapsUrl?: string | null;
  retailParents?: {id:string;displayName?:string|null;isMall?:boolean}[] | null;
  hoursEvidence?: import("./venue-hours").HoursEvidence | null;
  rating?: number | null; ratingCount?: number | null;
  evidenceLabels?: { claims?: Record<string, { message: string }>; attribution?: { third_party?: { provider?: string | null; uri?: string | null }[] } };
  eventDate?: string; dataQuality?: Quality; source?: string | null;
};
export type Stop = { venue: DisplayVenue; start: number | null; end: number | null };
export type Plan = {
  transport?: string | null;
  travelClassification?: "matching" | "outside_preference" | "beyond_limit" | "unverified"; travelDeviations?: string[];
  planningMode?: "origin" | "surprise"; surpriseRepeated?:boolean;
  dataMode?: "mock" | "real"; location?: string; detailsToken?: string;
  constraintIssues?: { code?: string; field?: string; status?: string; message: string }[];
  hardBudget?: boolean;
  firstLeg?: { mode?: string; approximate?: boolean; source?: "device" | "manual" | "suggested"; originLabel?: string | null; miles?: number | null; exceedsPreference?: boolean; accuracyMeters?: number | null; minutes: number | null; labels?: unknown } | null;
  routeEvidence?: { route: { mode: string; distance_meters?:number|null; duration_seconds?:number|null }; labels: { claims: Record<string, { message: string }> } }[];
  id: string; title: string; fullTitle?: string; description: string; theme: "peach" | "lavender" | "mint"; label: string;
  venues: DisplayVenue[]; stops: Stop[]; price: number | null; groupCost: number | null;
  travel: number | null; duration: number | null; people?: number | null; date: string;
  feasibility: "confirmed" | "provisional" | "violated" | "preview"; issues: string[];
  prices: { amount: number | null; status: string }[]; legs: { minutes: number | null; status: string }[];
};
export type PlannerResult = {
  saveReceipt?: string; saveAccessToken?: string;
  recoveryCode?: string; requestFailed?: boolean; optionsToken?: string; canExpand?: boolean; canDiscover?: boolean; continuationStatus?: {kind:string;message:string}; canShowBeyond?: boolean; dataMode?: "mock" | "real"; plans: Plan[]; alternativeBatches?: Plan[][]; message: string; location: string; activities: Activity[]; notes: string[] };
export type ResolvedOuting = { payload: OutingPayload; notes: string[]; error?: never } | { error: PlannerResult; payload?: never; notes?: never };
export const EXAMPLE_REQUEST = "Plan bowling, drinks, and a movie in Baltimore tomorrow.";
export const EMPTY_PREFERENCES: Preferences = { location: "", date: "", people: "", budget: "", travel: "", cost: "balanced" };
export const SUPPORTED_ACTIVITIES = Object.values(ACTIVITY_LABELS).join(", ");

// Historical Task 28 resolver retained for regression tests; the application uses Python AI.
export function resolveOuting(request: string, preferences: Preferences = EMPTY_PREFERENCES, context = { today: todayInBaltimore() }): ResolvedOuting {
  const parsed = parseRequest(request);
  const activities = parsed.activities;
  const location = preferences.location.trim() || parsed.location || "Baltimore";
  const notes: string[] = [];
  const fail = (message: string): ResolvedOuting => ({ error: { plans: [], message, location, activities, notes } });
  if (!request.trim()) return fail("Tell us which activities you want.");
  if (!/^baltimore(?:\s*,?\s*(?:md|maryland))?$/i.test(location)) return fail("This mock catalog only covers Baltimore. Choose Baltimore in Set preferences to try it.");
  if (parsed.remaining) return fail(`I couldn't match “${parsed.remaining}” to this mock planner. No partial plan was created. Open Supported activities & fictional event dates above, or simplify the request. Use Set preferences for exact dates and limits.`);
  if (!activities.length) return fail("No supported activity found. Try dinner and karaoke, a museum, or another supported activity from the list above. We won't substitute an unrelated outing.");
  if (activities.length > 4) return fail("This demo supports up to four activities in one outing. Please shorten the request; no activities have been silently removed.");
  if (!validDate(context.today)) return fail("The reference date is invalid. Please reload the planner.");
  const inferredPeople = request.match(/\b(\d+)\s+(?:friends|people|persons|of us)\b/i)?.[1] || request.match(/\b(?:group|party) of (\d+)\b/i)?.[1] || "4";
  const people = Number(preferences.people.trim() || inferredPeople);
  if (!Number.isInteger(people) || people < 1 || people > 100) return fail("Choose a whole-number group size between 1 and 100.");
  const inferredBudget = request.match(/\$\s*(\d+(?:\.\d+)?)\s*(?:per person|each|a person)/i)?.[1];
  const budgetText = preferences.budget.trim() || inferredBudget || "";
  const travelText = preferences.travel.trim();
  const budget = budgetText === "" ? Infinity : Number(budgetText);
  const maxTravel = travelText === "" ? Infinity : Number(travelText);
  if (budgetText && (!Number.isFinite(budget) || budget < 0 || budget > 100000)) return fail("Enter a budget from $0 to $100,000 per person, or leave it blank.");
  if (travelText && (!Number.isInteger(maxTravel) || maxTravel < 0 || maxTravel > 1440)) return fail("Enter a whole-number travel limit from 0 to 1440 minutes, or leave it blank.");
  if (!["budget", "balanced", "experience"].includes(preferences.cost)) return fail("Choose a valid cost preference.");
  const resolved = resolveDate(request, preferences.date, context.today);
  if (resolved.error) return fail(resolved.error);
  const date = resolved.date;
  const hasEvents = activities.some((activity) => "eventStart" in CATALOG[activity]);
  if (hasEvents && !date) return fail(`Scheduled events need an exact date. Choose one in Set preferences. Fictional event dates: ${MOCK_EVENT_DATES.join(" or ")}. No real events or tickets are checked.`);
  if (date) notes.push(`Planning date: ${date}. Relative days use Baltimore's calendar; the date preference overrides the request.`);
  if (hasEvents) notes.push("Event dates, start times, ticket capacities, and prices are invented mock data, not real schedules or availability.");
  if (activities.includes("shopping")) notes.push("Shopping estimates cover the visit only; purchases are not included.");
  if (activities.includes("picnic")) notes.push("Picnic prices are mock activity costs; bring your own food for the free option.");
  return { payload: { activities, location, people, date: date || null,
    budget: Number.isFinite(budget) ? budget : null, travel: Number.isFinite(maxTravel) ? maxTravel : null,
    cost: preferences.cost, dinner: /\bdinner\b/i.test(request) }, notes };
}

export function formatDuration(minutes: number | null) {
  if (minutes === null) return "Unknown";
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return [hours ? `${hours}h` : "", remainder ? `${remainder}m` : ""].filter(Boolean).join(" ") || "0m";
}
export function formatTime(minutes: number | null) {
  if (minutes === null) return "Unknown";
  const hours = Math.floor(minutes / 60) % 24;
  return `${hours % 12 || 12}:${String(minutes % 60).padStart(2, "0")} ${hours >= 12 ? "PM" : "AM"}`;
}
