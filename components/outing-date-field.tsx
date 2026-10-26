import { CalendarDays } from "lucide-react";
import { formatOutingDate } from "./outing-summary";

export function OutingDateField({ value, onChange, real = false }: { real?: boolean; value: string; onChange: (value: string) => void }) {
  return <label><span><CalendarDays size={14} /> Date</span>
    <input type="date" value={value} onChange={e => onChange(e.target.value)} aria-describedby="outing-date-help" />
    <small id="outing-date-help">{value ? `Selected: ${formatOutingDate(value)}. ` : "Date format follows your browser. "}Every outing needs a date; {real ? "venue dates do not confirm event sessions." : "event schedules are fictional."}</small>
  </label>;
}
