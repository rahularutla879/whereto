import type { Plan } from "../lib/planner";

export function FirstLegTravel({ plan }: { plan: Plan }) {
  const leg = plan.firstLeg;
  if (!leg) return null;
  const heading = leg.source === "device" ? "Travel from your current location"
    : leg.source === "suggested" ? "Travel from your planning reference"
    : "Travel from your confirmed starting place";
  const mode = leg.mode ?? plan.routeEvidence?.[0]?.route.mode ?? plan.transport ?? "driving";
  const label = ({ drive: "Driving", walk: "Walking", DRIVE: "Driving", WALK: "Walking", BICYCLE: "Cycling", driving: "Driving", walking: "Walking", cycling: "Cycling", transit: "Transit" } as Record<string, string>)[mode] ?? "Travel";
  return <div className="details-note">
    <strong>{heading}</strong>
    <p>{leg.minutes == null ? "Travel to the first stop is not verified." : <>About {leg.minutes} minutes{leg.miles != null ? ` (${leg.miles.toFixed(2)} miles)` : ""} to the first stop.</>}</p>
    <p>{plan.dataMode === "real" ? `${label} estimate from Google Maps.` : "Fictional mock travel estimate."}{(plan.stops?.length??0)>1&&" Travel between stops is shown separately."}{leg.approximate && " Based on the confirmed representative point."}{leg.exceedsPreference && " This journey exceeds your original preference; see the travel classification."}</p>
  </div>;
}
