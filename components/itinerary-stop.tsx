import type {Plan} from '@/lib/planner';
import {formatDuration,formatTime} from '@/lib/planner';
import {VenueDetails} from './venue-details';
import {VenueDetailsSession,safeMapsUrl} from '@/lib/venue-details';
import {RealVenueFacts} from './real-venue-facts';
import {durationRelation} from '@/lib/advanced-preferences';
const travel=(seconds:number|null)=>formatDuration(seconds===null?null:seconds/60);
const clock=(value:string)=>{const m=/T(\d{2}):(\d{2})/.exec(value);return m?formatTime(Number(m[1])*60+Number(m[2])):'Time unavailable';};
export function ItineraryStop({plan,index,detailsSession}:{plan:Plan;index:number;detailsSession:VenueDetailsSession}){
 const {venue,start,end}=plan.stops[index];const advanced=plan.advanced?.stops[index];
 const incoming=advanced&&plan.advanced?.legs.find(l=>l.toOccurrence===advanced.occurrence);
 const real=plan.dataMode==='real';
 return <li><span className="stop-number">{index+1}</span><div><strong>{venue.name}</strong>
 {real?<><RealVenueFacts venue={venue} concise/>{safeMapsUrl(venue.mapsUrl)&&<a href={venue.mapsUrl??undefined} target="_blank" rel="noopener noreferrer">View {venue.name} on Google Maps</a>}</>:<><span>{venue.kind==='event'?`Sample event: ${venue.eventDate}`:'Fictional venue'} · {formatTime(start)}–{formatTime(end)}</span><span>{venue.neighborhood??'Neighborhood unknown'} · {formatDuration(venue.duration)}</span><span>{plan.prices[index]?.amount==null?'Price not available':`${new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(plan.prices[index].amount!)} per person (${plan.prices[index].status})`}</span></>}
 {advanced?.closedVisitException&&<span className="details-note">Closed at the planned visit time. Included at your request; access is not confirmed.</span>}
 {advanced?.duration&&<span>{advanced.duration.minutes===0?'Zero counted visit time; actual visit duration is not established':`${durationRelation(advanced.duration.relation)} ${advanced.duration.minutes} minutes`}</span>}
 {(advanced?.arrival||advanced?.departure)&&<span>{advanced.arrival&&clock(advanced.arrival)}{advanced.departure&&` – ${clock(advanced.departure)}`} (estimated)</span>}
 {index>0&&<span>Travel from previous stop: {incoming?travel(incoming.seconds):`${formatDuration(plan.legs[index-1]?.minutes)}`} ({real?`${plan.transport??'driving'} estimate`:plan.legs[index-1]?.status??'unknown'}).{!advanced&&real&&plan.routeEvidence?.[index-1]?.route.distance_meters!=null&&' / '+(plan.routeEvidence[index-1].route.distance_meters!/1609.344).toFixed(2)+' route miles'}{incoming?.mapsUrl&&safeMapsUrl(incoming.mapsUrl)&&<> <a href={incoming.mapsUrl} target="_blank" rel="noopener noreferrer">View this leg on Google Maps</a></>}</span>}
 {real&&<VenueDetails venue={venue} token={plan.detailsToken} session={detailsSession} primaryMaps primaryCredits={advanced?.credits??venue.evidenceLabels?.attribution?.third_party}/>}
 </div></li>;
}
export function EndingStep({plan}:{plan:Plan}){
 const advanced=plan.advanced;if(!advanced||advanced.ending==='last_activity')return null;
 const leg=advanced.legs.find(l=>l.role==='return_to_origin'||l.role==='final_destination');
 return <li><span className="stop-number">{advanced.stops.length+1}</span><div><strong>{advanced.ending==='origin'?'Return to starting point':advanced.endpoint?.name??'Final destination'}</strong>{leg&&<span>Travel from previous stop: {travel(leg.seconds)} ({plan.transport??'driving'} estimate).</span>}{advanced.endpoint&&safeMapsUrl(advanced.endpoint.mapsUrl)&&<a href={advanced.endpoint.mapsUrl} target="_blank" rel="noopener noreferrer">View final destination on Google Maps</a>}</div></li>;
}
