# Activity capability inventory — October 30, 2026

This is an implementation audit, not a claim of real venue availability. **29 canonical categories plus bounded open-ended venue intents** use one planner. Up to four ordered/repeated stops and independent up-to-100 unique relevant venue pools are supported. Place IDs prevent duplicate physical stops. All real tests in this pass use invented providers; no live searches.

## Capability classifications

- **A — explicitly implemented/tested:** canonical normalization, query mapping and relevance rules below. `test_activity_audit.py` adds a complete query-contract check this pass; older `test_places.py`, `test_venue_quality.py`, `test_real_planning.py`, `test_location_first.py`, `test_surprise.py` and `test_discovery100.py` exercise relevant categories and planner behavior. This does not mean all categories were end-to-end live-tested.
- **B — flexible discovery:** concrete grounded phrases use `custom:` IDs and their own text query, without invented Google types. The model must copy the actual phrase; deterministic validation checks source/order and asks about genuinely ambiguous intent.
- **C — venue discovery only:** every real category lacks confirmed date-specific availability or bookings. Movies, sports, concerts, theater and classes additionally lack actual session/event evidence. A theater's hours never establish a showtime.
- **D — unreliable/unsupported:** generic “something fun” without clarification, invented event schedules/tickets, arbitrary languages/spelling recovery, exact sports/performance availability, unsupported transport modes for real routing, and venues without enough relevance/geographic evidence.

## Complete canonical inventory and aliases

All rows are A for the dedicated code path and C for real occurrence/availability. Searches are Text Search New, initial + bounded refinements/pages and spatial regions. Only bowling applies Google's `bowling_alley` type restriction on its initial query; the other rows use text, followed by conservative evidence checks. Type evidence can establish venue relevance; name-only support remains uncertain. Neither verifies a requested activity session.

| Backend ID | Recognized exact aliases before action-prefix normalization | Initial query | Specific relevance types (name patterns also apply) | Session caveat |
|---|---|---|---|---|
| `bowling` | bowling, bowl | bowling alleys | bowling_alley | Activity/service availability not verified |
| `drinks` | drinks, drink, cocktails, cocktail, beer, beers, wine, mocktails, bar | bars | bar, bar_and_grill, beer_garden, brewery, brewpub, cocktail_bar, lounge_bar, night_club, pub, sports_bar, wine_bar | Activity/service availability not verified |
| `movie` | movie, movies, cinema, film, films, show movies, watch a movie, watch a film, go to the movies, see a film | movie theaters | movie_theater | Activity/service availability not verified |
| `food` | food, dinner, lunch, breakfast, brunch, pizza, restaurant, dining | restaurants | cafeteria, diner, food_court, meal_takeaway, restaurant | Activity/service availability not verified |
| `coffee` | coffee, coffees, tea, cafe, café | cafes | cafe, cat_cafe, coffee_shop, coffee_stand, dog_cafe | Activity/service availability not verified |
| `outdoors` | outdoor, outdoors, outdoor activities, park, walk, walking, nature | parks | botanical_garden, city_park, garden, hiking_area, national_park, park, state_park | Activity/service availability not verified |
| `art` | art, art gallery, gallery, art galleries | art galleries | art_gallery, art_museum | Activity/service availability not verified |
| `museum` | museum, museums, art museum, science museum, history museum | museums | art_museum, history_museum, museum | Activity/service availability not verified |
| `karaoke` | karaoke | karaoke venues | karaoke | Activity/service availability not verified |
| `arcade` | arcade, video games | video arcades | video_arcade | Activity/service availability not verified |
| `escape` | escape room, escape rooms | escape rooms | Specific name evidence required | Activity/service availability not verified |
| `miniGolf` | mini golf, mini-golf, miniature golf, putt-putt | miniature golf | miniature_golf_course | Activity/service availability not verified |
| `shopping` | shopping, thrifting | shopping malls | department_store, market, shopping_mall | Activity/service availability not verified |
| `zoo` | zoo | zoos | wildlife_park, zoo | Activity/service availability not verified |
| `hiking` | hiking, hike, trail | hiking trails | hiking_area | Activity/service availability not verified |
| `picnic` | picnic | picnic parks | barbecue_area, picnic_ground | Activity/service availability not verified |
| `skating` | skating, ice skating, roller skating | skating rinks | ice_skating_rink | Activity/service availability not verified |
| `baseball` | baseball, baseball game, watch a baseball game | baseball stadiums | Specific name evidence required | Event/session not verified |
| `basketball` | basketball, basketball game | basketball arenas | Specific name evidence required | Event/session not verified |
| `football` | football, football game | football stadiums | Specific name evidence required | Event/session not verified |
| `soccer` | soccer, soccer game, soccer match | soccer stadiums | Specific name evidence required | Event/session not verified |
| `hockey` | hockey, hockey game | ice hockey arenas | Specific name evidence required | Event/session not verified |
| `sports` | sports event, sporting event, sports game | sports stadiums | arena, athletic_field, sports_complex, stadium | Event/session not verified |
| `concert` | concert, live music, gig | concert venues | concert_hall, live_music_venue, philharmonic_hall | Event/session not verified |
| `theater` | theater, theatre, play | performing arts theaters | performing_arts_theater | Event/session not verified |
| `musical` | musical, musical theater | musical theater venues | Specific name evidence required | Event/session not verified |
| `ballet` | ballet | ballet theaters | Specific name evidence required | Event/session not verified |
| `opera` | opera | opera houses | opera_house | Event/session not verified |
| `comedy` | comedy, comedy show, stand-up | comedy clubs | comedy_club | Event/session not verified |

Restaurants/dining and drinks map to separate pools even for multi-activity establishments; one physical establishment cannot become two visits. Dinner service remains unverified. Thrifting maps to shopping malls/markets and can miss specialist stores. Football/soccer and broad stadium types do not establish a particular game. Park support does not establish picnic facilities or a safe hiking trail. Skating types may cover ice better than roller facilities. Sports/performance variants often require name evidence.

## Flexible activity families

The table is illustrative, **not a new whitelist**. All rows are B + C, not verified classes or facilities. New `test_activity_audit.py` supplies matching name evidence and an unrelated dental negative control for each listed phrase. Older `test_open_exploration.py` already covered pottery classes, painting/cooking workshops, swimming, laser tag, go-karting, aquariums and origami studios, including three-stop integration and independent 100/activity pools. Only these cited tests support the specific coverage claims.

| Family | Example normalized text query | Limitation |
|---|---|---|
| Pottery | pottery class | Name can establish pottery venue intent, not a class slot |
| Cooking | cooking workshop | A restaurant alone does not establish classes |
| Painting | painting workshop | A gallery alone does not establish workshops |
| Swimming | swimming | Generic leisure-center names may lack evidence; pool access unknown |
| Laser tag | laser tag | An arcade alone is insufficient |
| Go-karting | go-karting | Name token matching can miss variants such as kart racing |
| Rock climbing | rock climbing | Generic gym type/name insufficient |
| Fitness classes | fitness class | No class schedule, skill/age suitability or instructor verification |
| Dance | dance studio | No session availability or dance-style guarantee |
| Spas | spa | No service menus, reservations or prices verified |
| Bookstores | bookstore | No particular book inventory verified |
| Aquariums | aquarium | Not the zoo enum; custom evidence required |
| Gardens | garden | May use custom intent; no opening/access guarantees |
| Other concrete activities | original grounded phrase, grammatical normalization | Not universally tested; absence of name/type evidence can exclude a genuine venue |

`venue_quality.relevance` requires all meaningful custom tokens to appear in provider name/types after simple grammatical stemming; class/workshop words are not proof of a session. This prioritizes avoiding unsupported claims over recall. It is not semantic understanding of every business. Unsupported arcades remain rejected for bowling; mixed venues with actual bowling type/name evidence remain eligible.

## Mock versus real

The fictional Baltimore catalog has the 29 canonical categories and invented scheduled dates. Custom activities without mock records return an honest no-data explanation; no invented extension or real fallback. Mock schedules/prices are explicitly fictional and cannot verify real businesses. Real evidence uses the existing opt-in Places Pro fields, optional ratings and separate on-demand contacts; this audit adds no fields or provider methods.

## User-facing wording and future work

“Where To? can search for many kinds of outings using Google Places. Specific events, tickets, schedules and availability may require separate confirmation.”

Future work could add independently sourced session feeds, activity-specific evidence, multilingual/typo evaluation and richer relevance matching. Each needs dedicated correctness, licensing and cost review. None is implemented here. Read `backend/ai/ollama.py`, `interpretation.py`, `models.py`, `places.py`, `venue_quality.py`, `feasibility.py` and `lib/mock-data.ts` for the contracts. A stronger model cannot verify missing provider facts. Tasks 47–49 are complete; Task 50 and Tasks 50A–50E remain unstarted.


## Retail stores and malls — Tasks 46/49 refinement

Retail phrases preserve arbitrary brand names, flexible outlet/regular/flagship formats and explicit only-outlet requirements. Generic shopping destinations remain distinct from tenants. Name identity plus retail type is required; search hits and similarly named businesses are insufficient. A verified regular Zara location is eligible for “Zara outlet”; it is never relabeled as an outlet. Stores inside malls and multiple brands in one mall require containment IDs joined to actual mall facts. Missing evidence yields no verified match and explicit exploration, never invented tenants, sales, inventory or unrelated brand substitutions.

[Exact architecture, evidence rules, fields, billing, limits and verification](acceptance-refinements.md).

## Registry-driven activity help — November 1

The accessible `/supported-activities` reference derives its canonical labels from `data/mock-venues.json`, shared with Python; existing event metadata provides grouping. It distinguishes open-ended venue requests from the finite mock registry and event venues from verified schedules or places to play a sport. Activity-related follow-ups offer **View supported activities** using a secure new tab, preserving the original request. Address/date clarifications do not show that link. The reference performs zero provider calls. [Verification](sharing-ux49.md).

## November 2 — user-facing activity reference cleanup

The registry-driven `/supported-activities` page no longer discusses mock Baltimore or provider configuration. Categories, examples and honest open-ended/session/participation limitations remain. `/how-it-works` explains using the reference. Choosing Walking is a journey preference, not a replacement activity; walking/hiking as requested activities retain existing interpretation and discovery semantics.

[Acceptance details and evidence](ui-travel-mode49.md).

## Task 50A — destination identity and stop requirements

A named establishment is distinct from a discoverable activity or a brand with
multiple suitable branches. Grocery/supermarket/ATM/pharmacy intentions remain
open venue-backed activities, not invented availability. Exact destinations,
optional stops, advanced ordering, return/final endpoints and journey/dwell timing
are understood but safely blocked before execution where unsupported. The registry
and retail format flexibility remain. [Semantic contract](complex-interpretation.md).
