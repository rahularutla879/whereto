import {destinationLabel,transportLabel,activityDisplay} from "@/lib/display-format";
import { formatTime } from "../lib/planner";
import type { ValidatedOuting } from "../lib/planning-client";

export function activityEditText(request: ValidatedOuting["request"]) {
  return request.activities.map((activity, i) => request.dinnerStops?.includes(i) ? "dinner" : ({ miniGolf: "mini golf", escape: "escape room", sports: "sports event" } as Partial<Record<typeof activity, string>>)[activity] ?? activity).join(", ");
}

export function formatOutingDate(date: string) {
  return new Date(`${date}T12:00:00`).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export function outingDetails(value: ValidatedOuting, real = false): [string, string][] {
  const r = value.request;
  const details: [string, string][] = [
    ["Location", destinationLabel(r.location)],
    ["Date", formatOutingDate(r.date)],
    ["Activities", r.activities.map((a, i) => r.dinnerStops?.includes(i) ? "Dinner" : activityDisplay(a)).join(" → ")],
  ];
  if (r.travel !== null) details.push(["Travel", `${r.travelExclusive ? "Under " : ""}${r.travel} min ${r.travelExclusive ? "total between stops" : "maximum total between stops"}`]);
  if (value.explicitTime) details.push(["Time window", `${formatTime(r.startTime)}–${r.endTime === 1440 ? "midnight" : formatTime(r.endTime)} ${real ? "(destination local time where known; otherwise calendar reference shown in notes)" : "(Baltimore time)"}`]);
  if (r.maxLegTravel != null) details.push(["Each journey", `${r.maxLegTravelExclusive ? "Under " : ""}${r.maxLegTravel} min${r.maxLegTravelExclusive ? " between stops" : " maximum"}`]);
  if(r.planningMode==="surprise")details.push(["Beginning","Surprise Me — first activity venue; no origin journey"]);
  if(r.betweenTravel)details.push(["Between activities",(r.betweenTravel.mode==="flexible"?"Prefer ":r.betweenTravel.exclusive?"Under ":"At most ")+r.betweenTravel.value+" "+r.betweenTravel.unit+(r.betweenTravel.mode==="flexible"?"; maximum "+r.betweenTravel.value*2+" "+r.betweenTravel.unit+" per leg":" per leg")]);
  if (real && r.firstTravel) details.push(["First journey", `${r.firstTravel.mode === "flexible" ? "Prefer around" : r.firstTravel.exclusive ? "Under" : "At most"} ${r.firstTravel.value} ${r.firstTravel.unit} from the confirmed start${r.firstTravel.mode === "flexible" ? `; maximum ${r.firstTravel.value*2} ${r.firstTravel.unit}` : ""}`]);
  if (real && !r.firstTravel && r.maxFirstLegTravel != null) details.push(["First journey", `${r.maxFirstLegTravelExclusive ? "Under " : ""}${r.maxFirstLegTravel} min ${r.maxFirstLegTravelExclusive ? "from" : "maximum from"} your shared start`]);
  if (r.transport) details.push(["Transport", `${transportLabel(r.transport)}${real ? " (Google Maps estimates)" : " (simulated travel is mode-independent)"}`]);
  return details;
}

export function OutingSummary({ value, dirty, onEdit, real = false, loading = false }: { value: ValidatedOuting; dirty: boolean; onEdit: () => void; real?: boolean; loading?: boolean }) {
  return <section className="outing-summary" aria-labelledby="outing-summary-title">
    <div className="preferences-intro"><h3 id="outing-summary-title">Your outing</h3><button type="button" onClick={onEdit} aria-controls="preferences">Edit details</button></div>
    {dirty ? <p role="status">{loading ? "Checking your updated details…" : "Details changed. Regenerate plans to validate your edits. Previous recommendations are hidden."}</p> : <dl>{outingDetails(value, real).map(([label, detail]) => <div key={label}><dt>{label}</dt><dd>{detail}</dd></div>)}</dl>}
  </section>;
}
