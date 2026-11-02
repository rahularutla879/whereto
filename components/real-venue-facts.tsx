import {OpeningHours} from "./opening-hours";
import type { DisplayVenue } from "../lib/planner";
export function VenueRating({ venue }: { venue: DisplayVenue }) {
  return typeof venue.rating === "number" && Number.isFinite(venue.rating) && venue.rating >= 1 && venue.rating <= 5 && Number.isInteger(venue.ratingCount) && (venue.ratingCount ?? 0) > 0
    ? <span className="venue-rating">{venue.rating.toFixed(1)} ★ · {venue.ratingCount!.toLocaleString("en-US")} Google ratings</span> : null;
}
export function RealVenueFacts({ venue }: { venue: DisplayVenue }) {
  return <>{venue.address && <span>{venue.address}</span>}{venue.retailParents?.filter(parent=>parent.displayName).map(parent=><span key={parent.id}>Inside {parent.displayName} · Google containment evidence</span>)}<VenueRating venue={venue} /><OpeningHours hours={venue.hoursEvidence}/></>;
}
