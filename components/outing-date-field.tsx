"use client";
import {useState} from "react";
import { CalendarDays } from "lucide-react";
import { formatOutingDate } from "./outing-summary";

export function OutingDateField({ value, onChange, real = false, allowNatural = false }: { real?: boolean; allowNatural?: boolean; value: string; onChange: (value: string) => void }) {
  const [words,setWords]=useState(false);
  const field=<label><span><CalendarDays size={14} /> Date</span>
    <input name="outing-date" type={allowNatural&&words?"text":"date"} placeholder={allowNatural&&words?"e.g. tomorrow or Nov 11":undefined} value={value} onChange={e => onChange(e.target.value)} aria-describedby="outing-date-help" />
    <small id="outing-date-help">{allowNatural&&words?"Use tomorrow, a weekday, Nov 11, or YYYY-MM-DD. ":value ? `Selected: ${formatOutingDate(value)}. ` : "Date format follows your browser. "}Every outing needs a date; {real ? "venue dates do not confirm event sessions." : "event schedules are fictional."}</small>
  </label>;
  return allowNatural?<div>{field}<button type="button" className="plan-link date-answer-mode" onClick={()=>{if(words&&!/^\d{4}-\d{2}-\d{2}$/.test(value))onChange('');setWords(!words);}}>{words?'Use the date picker':'Enter a date in words'}</button></div>:field;
}
