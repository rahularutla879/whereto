// Every name, capacity, price, duration, and event schedule below is fictional.
// Scheduled events exist ONLY on these dates; there is no live availability.
export const MOCK_EVENT_DATES = ["2026-11-07", "2026-11-14"] as const;

type Definition = {
  label: string;
  pattern: RegExp;
  names: [string, string, string];
  prices: [number, number, number];
  duration: number;
  eventStart?: number;
};

export const CATALOG = {
  bowling: { label: "Bowling", pattern: /\bbowl(?:ing)?\b/gi, names: ["Lucky Duck Lanes", "Sidekick Bowling Club", "The Golden Pin"], prices: [14, 22, 30], duration: 75 },
  drinks: { label: "Drinks", pattern: /\b(?:drinks?|cocktails?|beers?|bars?|wine|mocktails?)\b/gi, names: ["The Little Lime", "Good Company Social", "Juniper & Tonic"], prices: [8, 12, 18], duration: 45 },
  movie: { label: "Movie", pattern: /\b(?:movies?|cinema|films?)\b/gi, names: ["Pocket Picturehouse", "The Saturday Cinema", "Velvet Screen"], prices: [10, 15, 22], duration: 120 },
  food: { label: "Food", pattern: /\b(?:food|dinner|lunch|pizza|eat|restaurants?|brunch|breakfast|dining)\b/gi, names: ["Corner Slice", "Gather Kitchen", "The Supper Spot"], prices: [12, 20, 32], duration: 60 },
  coffee: { label: "Coffee", pattern: /\b(?:coffee|caf[eé]s?|tea)\b/gi, names: ["Daylight Coffee", "Sunday Kind Café", "Paper Cup Studio"], prices: [4, 6, 9], duration: 30 },
  outdoors: { label: "Outdoors", pattern: /\b(?:outdoor(?:s| activities)?|parks?|walk(?:ing)?|nature)\b/gi, names: ["Harbor Pocket Park", "Waterside Walk", "Greenway Gardens"], prices: [0, 0, 5], duration: 45 },
  art: { label: "Art gallery", pattern: /\b(?:art galleries|art gallery|art|galleries|gallery)\b/gi, names: ["Little Frame Gallery", "Color House", "The Makers' Loft"], prices: [0, 10, 20], duration: 60 },
  museum: { label: "Museum", pattern: /\b(?:(?:art|science|history) )?museums?\b/gi, names: ["Curiosity Museum", "Harbor Discovery Hall", "The Wonder Collection"], prices: [8, 16, 26], duration: 90 },
  karaoke: { label: "Karaoke", pattern: /\bkaraoke\b/gi, names: ["Pocket Mic Rooms", "Chorus Club", "Encore Singing Lounge"], prices: [10, 18, 28], duration: 60 },
  arcade: { label: "Arcade", pattern: /\b(?:arcades?|video games?)\b/gi, names: ["Pixel Pocket", "Extra Life Arcade", "High Score Hall"], prices: [10, 18, 28], duration: 60 },
  escape: { label: "Escape room", pattern: /\bescape rooms?\b/gi, names: ["The Puzzle Door", "Clue Collective", "The Last Key"], prices: [18, 28, 38], duration: 60 },
  miniGolf: { label: "Mini golf", pattern: /\b(?:mini(?:ature)?[ -]golf|putt[ -]putt)\b/gi, names: ["Tiny Tee Garden", "Happy Putt", "The Putting Parlor"], prices: [8, 14, 22], duration: 60 },
  shopping: { label: "Shopping", pattern: /\b(?:shopping|shops|thrifting)\b/gi, names: ["Pocket Market", "The Browse Arcade", "Harbor Boutique Walk"], prices: [0, 0, 0], duration: 60 },
  zoo: { label: "Zoo", pattern: /\bzoos?\b/gi, names: ["Little Wild Gardens", "Harbor Animal Park", "Canopy Wildlife Center"], prices: [12, 20, 30], duration: 120 },
  hiking: { label: "Hiking", pattern: /\b(?:hiking|hikes?|trails?)\b/gi, names: ["Pine Loop Trail", "Lookout Ridge", "Fern Valley Trail"], prices: [0, 0, 6], duration: 90 },
  picnic: { label: "Picnic", pattern: /\bpicnics?\b/gi, names: ["Clover Picnic Green", "Waterside Picnic Lawn", "The Garden Blanket"], prices: [0, 8, 16], duration: 60 },
  skating: { label: "Skating", pattern: /\b(?:(?:ice|roller) )?skat(?:ing|e)\b/gi, names: ["Little Loop Rink", "Glide House", "The Silver Rink"], prices: [10, 18, 28], duration: 75 },
  baseball: { label: "Baseball game", pattern: /\bbaseball(?: games?)?\b/gi, names: ["Harbor Herons vs. Bay Foxes", "Harbor Herons Club Seats", "Harbor Herons Suite Experience"], prices: [18, 35, 65], duration: 180, eventStart: 14 * 60 },
  basketball: { label: "Basketball game", pattern: /\bbasketball(?: games?)?\b/gi, names: ["Bay Comets Basketball", "Bay Comets Club Seats", "Bay Comets Courtside"], prices: [18, 35, 65], duration: 120, eventStart: 18 * 60 },
  football: { label: "Football game", pattern: /\bfootball(?: games?)?\b/gi, names: ["Harbor Oaks Football", "Harbor Oaks Club Seats", "Harbor Oaks Suite"], prices: [18, 35, 65], duration: 180, eventStart: 13 * 60 },
  soccer: { label: "Soccer match", pattern: /\bsoccer(?: (?:games?|matches|match))?\b/gi, names: ["Bay Lanterns Soccer", "Bay Lanterns Club Seats", "Bay Lanterns Sideline"], prices: [18, 35, 65], duration: 120, eventStart: 16 * 60 },
  hockey: { label: "Hockey game", pattern: /\bhockey(?: games?)?\b/gi, names: ["Harbor Gliders Hockey", "Harbor Gliders Club Seats", "Harbor Gliders Suite"], prices: [18, 35, 65], duration: 120, eventStart: 18 * 60 },
  sports: { label: "Sporting event", pattern: /\b(?:sporting events?|sports (?:events?|games?))\b/gi, names: ["Harbor Athletics Exhibition", "Harbor Athletics Club Seats", "Harbor Athletics Suite"], prices: [18, 35, 65], duration: 120, eventStart: 15 * 60 },
  concert: { label: "Concert", pattern: /\b(?:concerts?|live music|gigs?)\b/gi, names: ["Paper Satellites Live", "Paper Satellites Balcony", "Paper Satellites Front Row"], prices: [20, 40, 70], duration: 120, eventStart: 19 * 60 },
  theater: { label: "Theater", pattern: /\b(?:theat(?:er|re)|plays?(?!\s+(?:baseball|basketball|football|soccer|hockey|bowling|mini|video))|performances?)\b/gi, names: ["The Lantern Letters — Stage Play", "The Lantern Letters — Circle", "The Lantern Letters — Front Row"], prices: [18, 35, 60], duration: 120, eventStart: 19 * 60 + 30 },
  musical: { label: "Musical", pattern: /\b(?:musical theat(?:er|re)|musicals?)\b/gi, names: ["Paper Moon — The Musical", "Paper Moon — Circle", "Paper Moon — Front Row"], prices: [20, 38, 65], duration: 120, eventStart: 19 * 60 },
  ballet: { label: "Ballet", pattern: /\bballet\b/gi, names: ["The Willow Ballet", "The Willow Ballet — Circle", "The Willow Ballet — Front Row"], prices: [18, 35, 60], duration: 120, eventStart: 19 * 60 },
  opera: { label: "Opera", pattern: /\bopera\b/gi, names: ["The Harbor Aria — Opera", "The Harbor Aria — Circle", "The Harbor Aria — Front Row"], prices: [20, 40, 70], duration: 120, eventStart: 19 * 60 },
  comedy: { label: "Comedy show", pattern: /\b(?:comedy(?: shows?)?|stand[ -]up)\b/gi, names: ["Small Laughs Showcase", "Small Laughs Club Seats", "Small Laughs Front Row"], prices: [12, 22, 35], duration: 90, eventStart: 20 * 60 },
} satisfies Record<string, Definition>;

export type Activity = keyof typeof CATALOG;
export const ACTIVITY_LABELS = Object.fromEntries(Object.entries(CATALOG).map(([id, item]) => [id, item.label])) as Record<Activity, string>;

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
      neighborhood: ["Harbor East", "Fells Point", "Mount Vernon"][tier],
      price: item.prices[tier], duration: item.duration, zone: tier,
      experience: tier + 1, capacity: [4, 8, 20][tier],
    };
    return item.eventStart === undefined
      ? [{ ...venue, kind: "venue" as const }]
      : MOCK_EVENT_DATES.map((date) => ({ ...venue, id: `${venue.id}-${date}`, kind: "event" as const, eventDate: date, start: item.eventStart! }));
  });
});
