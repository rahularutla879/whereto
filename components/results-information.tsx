import * as React from "react";
import { DEMO_DISCLOSURE } from "../lib/results-presentation";
export function ResultsInformation({real=false,walking=false,advanced=false}:{notes:string[];needsChecking:boolean;real?:boolean;walking?:boolean;advanced?:boolean}){
 return <aside className="results-information" aria-label="Before you go"><strong>Before you go</strong>
  <p>{real?"Travel estimates use Google Maps. Driving estimates exclude live traffic and may differ from Google Maps directions. Check venue hours, availability and activity schedules before visiting.":DEMO_DISCLOSURE}</p>
  {real&&walking&&<p role="note">Walking routes are in beta and may omit sidewalks or pedestrian paths. Check the route before setting out; safety and accessibility are not verified.</p>}
  <details className="estimates-details"><summary>About these recommendations</summary><p>{real?"Recommendations cover places checked so far. Exploring can find better options. Suggested activities are not bookings, tickets or confirmed schedules. Area-based starting points are approximate; check venue addresses.":"Sample prices and times illustrate the plan. They do not confirm availability or bookings."} {advanced?'Requested return/final legs are included. Whole-trip timing also needs visit durations.':'Return travel is not included.'} Missing travel estimates remain unknown.</p></details>
 </aside>;
}
