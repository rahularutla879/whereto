import type {HoursEvidence} from '@/lib/venue-hours';
import {formatTime} from '@/lib/planner';
import {outingDateLabel} from '@/lib/display-format';
function clock(value:number){return `${formatTime(((value%1440)+1440)%1440)}${value<0?' (previous day)':value>=1440?' (next day)':''}`;}
export function OpeningHours({hours,concise=false}:{hours?:HoursEvidence|null;concise?:boolean}){
 if(concise&&(!hours||hours.basis!=='current'&&hours.typicalClosed==null&&!hours.weekly.length))return null;
 return <section className="opening-hours" aria-label="Opening hours"><strong>Opening hours</strong>
 {!hours?<p>Hours unverified.</p>:<>
 {!concise&&<p>{outingDateLabel(hours.date)}{!concise&&hours.timezone?` · ${hours.timezone}`:''}{hours.specialDay?' · Special-day hours':''}</p>}
 {hours.basis==='current'&&<p>{hours.periods.length?hours.periods.map((p,i)=><span key={i}>{i>0?'; ':''}{p.start<=0&&p.end>=1440?'Open 24 hours':`${clock(p.start)}–${clock(p.end)}`}</span>):'Closed on this date.'}</p>}
 {hours.basis!=='current'&&hours.typicalClosed!=null&&<p>Typical hours: {hours.typicalClosed?'Closed':hours.typicalPeriods?.map(p=>p.start<=0&&p.end>=1440?'Open 24 hours':`${clock(p.start)}–${clock(p.end)}`).join('; ')}. Special-day changes are unverified.</p>}
 {(!concise||hours.basis!=='current')&&<p>{concise?'Hours need confirmation for this date.':hours.message}</p>}{!concise&&hours.observedAt&&<p className="details-note">Hours checked {new Date(hours.observedAt).toLocaleString()}.</p>}
 {!!hours.weekly.length&&<details><summary>Typical weekly hours</summary><ul>{hours.weekly.map((line,i)=><li key={i}>{line}</li>)}</ul><p>Typical hours may differ on special days.</p></details>}
 </>}
 </section>;
}
