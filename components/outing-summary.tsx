import { ACTIVITY_LABELS, formatTime } from "../lib/planner";
import type { ValidatedOuting } from "../lib/planning-client";

export function activityEditText(request: ValidatedOuting["request"]) {
  return request.activities.map((activity, i) => request.dinnerStops?.includes(i) ? "dinner" : ({ miniGolf: "mini golf", escape: "escape room", sports: "sports event" } as Partial<Record<typeof activity, string>>)[activity] ?? activity).join(", ");
}

export function outingDetails(value: ValidatedOuting): [string, string][] {
  const r = value.request;
  const details: [string, string][] = [
    ["Location", r.location],
    ["Date", new Date(`${r.date}T12:00:00`).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })],
    ["Group", `${r.people} ${r.people === 1 ? "person" : "people"}`],
    ["Activities", r.activities.map((a, i) => r.dinnerStops?.includes(i) ? "Dinner" : ACTIVITY_LABELS[a]).join(" → ")],
    ["Budget", r.budget === null ? "Not specified" : `$${r.budget} maximum / person`],
    ["Travel", r.travel === null ? "Not specified" : `${r.travel} min maximum total between stops`],
    ["Experience", value.explicitCost ? ({ budget: "Cheap", balanced: "Balanced", experience: "Best Experience" })[r.cost] : "Not specified (Balanced ranking)"],
  ];
  if (value.explicitTime) details.push(["Time window", `${formatTime(r.startTime)}–${r.endTime === 1440 ? "midnight" : formatTime(r.endTime)} (Baltimore time)`]);
  if (r.groupBudget != null) details.push(["Group budget", `$${r.groupBudget} maximum total`]);
  if (r.maxLegTravel != null) details.push(["Each journey", `${r.maxLegTravel} min maximum`]);
  if (r.transport) details.push(["Transport", `${r.transport} (simulated travel is mode-independent)`]);
  return details;
}

export function OutingSummary({ value, dirty, onEdit }: { value: ValidatedOuting; dirty: boolean; onEdit: () => void }) {
  return <section className="outing-summary" aria-labelledby="outing-summary-title">
    <div className="preferences-intro"><h3 id="outing-summary-title">Your outing</h3><button type="button" onClick={onEdit} aria-controls="preferences">Edit details</button></div>
    {dirty ? <p role="status">Details changed. Regenerate plans to validate your edits. Previous recommendations are hidden.</p> : <dl>{outingDetails(value).map(([label, detail]) => <div key={label}><dt>{label}</dt><dd>{detail}</dd></div>)}</dl>}
  </section>;
}
