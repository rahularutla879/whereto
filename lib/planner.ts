import { ACTIVITY_LABELS, CATALOG, MOCK_EVENT_DATES, VENUES, type Activity, type Venue } from "./mock-data";
import { parseRequest, resolveDate, todayInBaltimore, validDate } from "./request";
export { ACTIVITY_LABELS, MOCK_EVENT_DATES, VENUES } from "./mock-data";
export type { Activity, Venue } from "./mock-data";

export type CostPreference = "budget" | "balanced" | "experience";
export type Preferences = { location: string; date: string; people: string; budget: string; travel: string; cost: CostPreference };
export type Stop = { venue: Venue; start: number; end: number };
export type Plan = {
  id: string; title: string; description: string; theme: "peach" | "lavender" | "mint"; label: string;
  venues: Venue[]; stops: Stop[]; price: number; travel: number; duration: number; people: number; date: string;
};
export type PlannerResult = { plans: Plan[]; message: string; location: string; activities: Activity[]; notes: string[] };
export const EXAMPLE_REQUEST = "We're 4 friends in Baltimore. We want bowling, drinks, and a movie this Saturday.";
export const EMPTY_PREFERENCES: Preferences = { location: "", date: "", people: "", budget: "", travel: "", cost: "balanced" };
export const SUPPORTED_ACTIVITIES = Object.values(ACTIVITY_LABELS).join(", ");

export function legTravel(from: Venue, to: Venue) {
  // Mock inter-stop model. Never a real distance, route, or traffic estimate.
  return 5 + Math.abs(from.zone - to.zone) * 8;
}

export function scheduleRoute(venues: Venue[], start: number, dinner = false): Stop[] | undefined {
  const stops: Stop[] = [];
  let earliest = start;
  for (const venue of venues) {
    const previous = stops.at(-1);
    if (previous) earliest = previous.end + legTravel(previous.venue, venue);
    if (dinner && venue.activity === "food") earliest = Math.max(earliest, 17 * 60);
    const begins = venue.kind === "event" ? venue.start : earliest;
    if (begins < earliest || begins + venue.duration > 24 * 60) return undefined;
    stops.push({ venue, start: begins, end: begins + venue.duration });
  }
  return stops;
}

// An explicit reference day keeps relative-date tests deterministic. The UI uses Baltimore's day.
export function makePlans(request: string, preferences: Preferences = EMPTY_PREFERENCES, context = { today: todayInBaltimore() }): PlannerResult {
  const parsed = parseRequest(request);
  const activities = parsed.activities;
  const location = preferences.location.trim() || parsed.location || "Baltimore";
  const notes: string[] = [];
  const fail = (message: string): PlannerResult => ({ plans: [], message, location, activities, notes });
  if (!request.trim()) return fail("Tell us which activities you want, or click Try an example.");
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
  const pools = activities.map((activity) => VENUES.filter((venue) => venue.activity === activity && (venue.kind === "venue" || venue.eventDate === date)));
  const missingIndex = pools.findIndex((pool) => !pool.length);
  if (missingIndex >= 0) return fail(`No mock ${ACTIVITY_LABELS[activities[missingIndex]].toLowerCase()} is scheduled on ${date}. No plan was created. Fictional event dates: ${MOCK_EVENT_DATES.join(" or ")}. This says nothing about real-world availability.`);
  const capacityPools = pools.map((pool) => pool.filter((venue) => venue.capacity >= people));
  if (capacityPools.some((pool) => !pool.length)) return fail(`No mock option can accommodate ${people} people for every requested activity. This catalog has invented capacities up to 20; reduce the group size. No live capacity was checked.`);
  let combinations: Venue[][] = [[]];
  for (const pool of capacityPools) combinations = combinations.flatMap((route) => pool.map((venue) => [...route, venue]));
  const dinner = /\bdinner\b/i.test(request);
  const candidates = combinations.flatMap((venues) => {
    const price = venues.reduce((sum, venue) => sum + venue.price, 0);
    const travel = venues.slice(1).reduce((sum, venue, i) => sum + legTravel(venues[i], venue), 0);
    if (price > budget || travel > maxTravel) return [];
    const stops = scheduleRoute(venues, 10 * 60, dinner);
    return stops ? [{ venues, stops, price, travel, experience: venues.reduce((sum, venue) => sum + venue.experience, 0) }] : [];
  });
  const strategies = {
    budget: { title: "Big fun. Small spend.", description: "All the good times, a little easier on the wallet.", theme: "peach" as const, label: "THE BUDGET PICK", score: (p: typeof candidates[number]) => p.price * 100 + p.travel },
    balanced: { title: "A little of everything.", description: "Your happy medium of fun, comfort, and cost.", theme: "lavender" as const, label: "THE SWEET SPOT", score: (p: typeof candidates[number]) => p.venues.reduce((sum, v) => sum + Math.abs(v.experience - 2) * 100, 0) + p.travel },
    experience: { title: "Make a night of it.", description: "A few little upgrades for a memorable get-together.", theme: "mint" as const, label: "THE TREAT-YOURSELF PICK", score: (p: typeof candidates[number]) => -p.experience * 1000 + p.travel + p.price },
  };
  const order: CostPreference[] = [preferences.cost, ...(["budget", "balanced", "experience"] as CostPreference[]).filter((key) => key !== preferences.cost)];
  const used = new Set<string>();
  const plans: Plan[] = [];
  for (const key of order) {
    const strategy = strategies[key];
    const candidate = [...candidates].sort((a, b) => strategy.score(a) - strategy.score(b) || a.venues.map((v) => v.id).join().localeCompare(b.venues.map((v) => v.id).join()))
      .at(0);
    if (!candidate) continue;
    const id = candidate.venues.map((venue) => venue.id).join("-");
    if (used.has(id)) continue;
    used.add(id);
    plans.push({ id, title: strategy.title, description: strategy.description, theme: strategy.theme, label: strategy.label,
      venues: candidate.venues, stops: candidate.stops, price: candidate.price, travel: candidate.travel,
      duration: candidate.stops.at(-1)!.end - candidate.stops[0].start, people, date: date || "Any day" });
  }
  if (!plans.length) return fail("No mock plan fits all your limits and activity timings. Try a higher per-person budget, more inter-stop travel time, a smaller group, or a different activity order. Scheduled events cannot overlap or start before earlier stops finish.");
  notes.push(`Mock group size: ${people}. Every stop has an invented capacity of at least ${people}. ${preferences.cost === "experience" ? "Best experience" : preferences.cost === "budget" ? "Budget-friendly" : "Balanced"} is ranked first; hard limits always apply.`);
  if (plans.length < 3) notes.push(`Only ${plans.length} distinct mock ${plans.length === 1 ? "plan fits" : "plans fit"}. We kept your date, activities, budget, travel, and group limits.`);
  return { plans, location: "Baltimore", activities, notes, message: `${plans.length} sample ${plans.length === 1 ? "plan" : "plans"} for ${people} ${people === 1 ? "person" : "people"} in Baltimore` };
}

export function formatDuration(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return [hours ? `${hours}h` : "", remainder ? `${remainder}m` : ""].filter(Boolean).join(" ") || "0m";
}
export function formatTime(minutes: number) {
  const hours = Math.floor(minutes / 60);
  return `${hours % 12 || 12}:${String(minutes % 60).padStart(2, "0")} ${hours >= 12 ? "PM" : "AM"}`;
}
