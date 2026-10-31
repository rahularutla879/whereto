import * as React from "react";
import { DEMO_DISCLOSURE } from "../lib/results-presentation";
export function ResultsInformation({real=false}:{notes:string[];needsChecking:boolean;real?:boolean}){
 return <aside className="results-information" aria-label="Before you go"><strong>Before you go</strong>
  <p>{real?"Travel estimates use Google Maps. Check venue hours, availability and activity schedules before visiting.":DEMO_DISCLOSURE}</p>
  <details className="estimates-details"><summary>About these recommendations</summary><p>{real?"Recommendations cover places checked so far. Exploring can find better options. Suggested activities are not bookings, tickets or confirmed schedules. Area-based starting points are approximate; check venue addresses.":"Sample prices and times illustrate the plan. They do not confirm availability or bookings."} Return travel is not included. Missing travel estimates remain unknown.</p></details>
 </aside>;
}
