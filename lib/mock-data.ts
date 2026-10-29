// Shared fictional values and keyword patterns for interpretation and legacy regression tests.
// Live planning runs exclusively in Python.
import fixture from "../data/mock-venues.json";

export const MOCK_EVENT_DATES = fixture.eventDates;
export type CanonicalActivity = keyof typeof fixture.catalog;
export type Activity = CanonicalActivity | `custom:${string}`;

type Definition = {
  label: string;
  pattern: RegExp;
  names: string[];
  prices: number[];
  duration: number;
  eventStart?: number;
};

const PATTERNS = {
  bowling: /\bbowl(?:ing)?\b/gi,
  drinks: /\b(?:drinks?|cocktails?|beers?|bars?|wine|mocktails?)\b/gi,
  movie: /\b(?:movies?|cinema|films?)\b/gi,
  food: /\b(?:food|dinner|lunch|pizza|eat|restaurants?|brunch|breakfast|dining)\b/gi,
  coffee: /\b(?:coffee|caf[eé]s?|tea)\b/gi,
  outdoors: /\b(?:outdoor(?:s| activities)?|parks?|walk(?:ing)?|nature)\b/gi,
  art: /\b(?:art galleries|art gallery|art|galleries|gallery)\b/gi,
  museum: /\b(?:(?:art|science|history) )?museums?\b/gi,
  karaoke: /\bkaraoke\b/gi,
  arcade: /\b(?:arcades?|video games?)\b/gi,
  escape: /\bescape rooms?\b/gi,
  miniGolf: /\b(?:mini(?:ature)?[ -]golf|putt[ -]putt)\b/gi,
  shopping: /\b(?:shopping|shops|thrifting)\b/gi,
  zoo: /\bzoos?\b/gi,
  hiking: /\b(?:hiking|hikes?|trails?)\b/gi,
  picnic: /\bpicnics?\b/gi,
  skating: /\b(?:(?:ice|roller) )?skat(?:ing|e)\b/gi,
  baseball: /\bbaseball(?: games?)?\b/gi,
  basketball: /\bbasketball(?: games?)?\b/gi,
  football: /\bfootball(?: games?)?\b/gi,
  soccer: /\bsoccer(?: (?:games?|matches|match))?\b/gi,
  hockey: /\bhockey(?: games?)?\b/gi,
  sports: /\b(?:sporting events?|sports (?:events?|games?))\b/gi,
  concert: /\b(?:concerts?|live music|gigs?)\b/gi,
  theater: /\b(?:theat(?:er|re)|plays?(?!\s+(?:baseball|basketball|football|soccer|hockey|bowling|mini|video))|performances?)\b/gi,
  musical: /\b(?:musical theat(?:er|re)|musicals?)\b/gi,
  ballet: /\bballet\b/gi,
  opera: /\bopera\b/gi,
  comedy: /\b(?:comedy(?: shows?)?|stand[ -]up)\b/gi,
} satisfies Record<CanonicalActivity, RegExp>;

export const CATALOG = Object.fromEntries(
  Object.entries(fixture.catalog).map(([id, item]) => [id, { ...item, pattern: PATTERNS[id as CanonicalActivity] }]),
) as Record<Activity, Definition>;
export const ACTIVITY_LABELS = Object.fromEntries(Object.entries(CATALOG).map(([id, item]) => [id, item.label])) as Record<Activity, string>;

export function activityLabel(activity: Activity): string {
  return ACTIVITY_LABELS[activity] ?? activity.replace(/^custom:/, "");
}

type BaseVenue = {
  id: string;
  name: string;
  activity: Activity;
  neighborhood: string;
  price: number;
  duration: number;
  zone: number;
  experience: number;
  capacity: number;
};
export type Venue = BaseVenue & ({ kind: "venue" } | { kind: "event"; eventDate: string; start: number });

export const VENUES: Venue[] = Object.entries(CATALOG).flatMap(([activity, definition]) => {
  const item: Definition = definition;
  return item.names.flatMap<Venue>((name, tier) => {
    const venue: BaseVenue = {
      id: `${activity}-${tier}`, name, activity: activity as Activity,
      neighborhood: fixture.tiers[tier].neighborhood,
      price: item.prices[tier], duration: item.duration, zone: fixture.tiers[tier].zone,
      experience: fixture.tiers[tier].experience, capacity: fixture.tiers[tier].capacity,
    };
    return item.eventStart === undefined
      ? [{ ...venue, kind: "venue" as const }]
      : MOCK_EVENT_DATES.map((date) => ({ ...venue, id: `${venue.id}-${date}`, kind: "event" as const, eventDate: date, start: item.eventStart! }));
  });
});
