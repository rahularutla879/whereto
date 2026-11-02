"use client";
import {useEffect,useRef,useState} from "react";
import { activityLabel,formatTime,type Activity } from "@/lib/planner";
import { preferenceText,type SavedPlan } from "@/lib/saved-plans";
import { GoogleCredits } from "./venue-details";
import {safeWebsite,safeMapsUrl} from "@/lib/venue-details";
import type {RefreshedVenue} from "@/lib/saved-plan-refresh";
export function SavedCards({saved,venues,refresh,busy,message,onClose}:{saved:SavedPlan;venues:Record<string,RefreshedVenue>;refresh:(id:string,contacts?:boolean)=>void;busy:boolean;message:string;onClose?:()=>void}){
 const request=saved.constraints;
 const selectedCard=useRef<HTMLElement|null>(null);
 const [contacts,setContacts]=useState(false);
 useEffect(()=>{selectedCard.current?.focus();},[saved]);
 const index=saved.itineraries.findIndex(p=>p.candidateId===saved.selectedId);
 const option=saved.itineraries[index];
 const [cooldown,setCooldown]=useState(false);
 const blocked=Object.values(venues).some(v=>v.retryable===false);
 useEffect(()=>{
  const seconds=Math.max(0,...Object.values(venues).map(v=>v.retryAfterSeconds??0));
  if(!seconds){queueMicrotask(()=>setCooldown(false));return;}
  queueMicrotask(()=>setCooldown(true));
  const timer=setTimeout(()=>setCooldown(false),seconds*1000);
  return()=>clearTimeout(timer);
 },[venues]);
 const real=saved.dataMode==="real";
 const names=option.stops.map(s=>s.fictional?.name??venues[s.reference]?.name);
 const detailsReady=option.stops.every(s=>venues[s.reference]?.status==="refreshed");
 const credits=option.stops.flatMap(s=>venues[s.reference]?.attributions??[]);
 return <section aria-label="Saved itineraries" className="saved-results">
  <h3>Selected saved itinerary</h3>
  {onClose&&<button type="button" className="secondary-button" onClick={onClose}>Return to planning</button>}
  <article ref={selectedCard} tabIndex={-1} className="plan-card saved-itinerary lavender" aria-label={`Saved option ${index+1}, selected`}>
   <div className="card-body"><p className="card-label">Saved option {index+1} · Selected option</p>
   <h3 className="real-plan-title">{names.some(Boolean)?names.map((name,i)=>name??activityLabel(option.stops[i].activity as Activity)).join(" → "):"Your saved itinerary"}</h3>
   <p>{request.location} · {request.date} · {(request.transport??"driving")==="walking"?"Walking":(request.transport??"driving")==="driving"?"Driving":"Original travel preference"}{!real&&" · Fictional sample"}</p>
   {real&&<div className="saved-load"><p>{detailsReady?"Current venue information is shown below. Updating it contacts Google Maps and uses API quota.":"Load current names, addresses, status and map links. This contacts Google Maps and uses API quota."}</p>
    <label><input type="checkbox" checked={contacts} disabled={busy} onChange={e=>setContacts(e.target.checked)}/> Include phone number and website</label>
    <button type="button" className="secondary-button" disabled={busy||blocked||cooldown} aria-busy={busy} onClick={()=>refresh(option.candidateId,contacts)}>{detailsReady?"Update current venue details":"Load current venue details"}</button>
    <p className="details-note">Hours, tickets and routes are not loaded.</p>
   </div>}
   {message&&<p role="status" aria-live="polite">{message}</p>}
   <ol className="saved-stops">{option.stops.map(s=>{const detail=venues[s.reference];return <li key={s.position}>
    <span className="stop-number">{s.position+1}</span><div><h4>{s.fictional?.name??detail?.name??activityLabel(s.activity as Activity)}</h4><p>{request.activityIntents[s.activity]??activityLabel(s.activity as Activity)}</p>
    {s.fictional?<p>Fictional venue · {s.fictional.neighborhood}. {s.start!==null?`${formatTime(s.start)}–${formatTime(s.end)}`:"Sample timing unavailable"}</p>:<>
     <p>{detail?.address??"Current venue details not loaded."}</p>
     {detail?.status==="refreshed"?<p>Current details · {detail.refreshedAt?new Date(detail.refreshedAt).toLocaleString():"just retrieved"}. {detail.businessStatus==="OPERATIONAL"?"Reported operational; opening hours unverified.":detail.businessStatus?.startsWith("CLOSED")?"":"Business status unavailable."}</p>:detail?.status==="stale"?<p role="note">Earlier details from {detail.refreshedAt?new Date(detail.refreshedAt).toLocaleString():"a previous lookup"}. Refresh unavailable. {detail.message}</p>:detail?.message&&<p role="note">{detail.message}</p>}
     {detail?.businessStatus?.startsWith("CLOSED")&&<p className="plan-warning" role="note">{detail.businessStatus==="CLOSED_PERMANENTLY"?"Reported permanently closed":"Reported temporarily closed"}. Your original stop is kept.</p>}
     <div className="saved-venue-links">{safeMapsUrl(detail?.mapsUrl)&&<a href={safeMapsUrl(detail?.mapsUrl)!} target="_blank" rel="noopener noreferrer">View {detail?.name??"this stop"} on Google Maps</a>}
      {safeWebsite(detail?.website)&&<a href={safeWebsite(detail?.website)!} target="_blank" rel="noopener noreferrer">Official website</a>}
      {detail?.telephoneUrl&&/^tel:\+?[0-9]{7,15}$/.test(detail.telephoneUrl)&&<a href={detail.telephoneUrl}>{detail.phone??"Call venue"}</a>}</div>
    </>}
    </div></li>})}</ol>
   {real?<p className="details-note">Original route estimates were not retained. Travel to, between and after these stops is unavailable; stop order is preserved.</p>:option.stops.length>1&&<p>Fictional inter-stop travel: {option.fictionalMetrics?.totalTravel??"Unknown"} minutes.</p>}
   {real&&<GoogleCredits credits={credits}/>}
  </div></article>
  <details className="estimates-details"><summary>Saved preferences</summary>
   <dl className="saved-preferences">
    <div><dt>Date and time</dt><dd>{request.date}<br/>{formatTime(request.startTime)}{request.explicitStart===false?" (planning start, not a requested arrival)":""} – {request.endTime===1440?"midnight at the end of this date":formatTime(request.endTime)}{request.explicitEnd===false?" (planning cutoff)":""}</dd></div>
    <div><dt>Destination and timezone</dt><dd>{request.location}<br/>{request.calendarTimezone??"Timezone unavailable"}</dd></div>
    <div><dt>Travel mode</dt><dd>{request.transport==="walking"?"Walking":(request.transport??"driving")==="driving"?"Driving":request.transport}</dd></div>
    <div><dt>First-stop travel preference</dt><dd>{preferenceText(request.firstTravel)}{request.maxFirstLegTravel!=null&&<><br/>{request.maxFirstLegTravelExclusive?"Under":"Maximum"} {request.maxFirstLegTravel} minutes</>}</dd></div>
    <div><dt>Between-stop travel</dt><dd>{preferenceText(request.betweenTravel)}{request.travel!=null&&<><br/>{request.travelExclusive?"Under":"Maximum"} {request.travel} minutes in total</>}{request.maxLegTravel!=null&&<><br/>{request.maxLegTravelExclusive?"Under":"Maximum"} {request.maxLegTravel} minutes per journey</>}</dd></div>
    <div><dt>Activity order</dt><dd>{request.activities.map(a=>request.activityIntents[a]??activityLabel(a as Activity)).join(" → ")}<br/>{request.allowRevisits?"Revisits permitted.":"No repeated venues."}{request.dinner&&!request.dinnerStops?.length&&" Dinner requested."}{!!request.dinnerStops?.length&&` Dinner at ${request.dinnerStops.length===1?"stop":"stops"} ${request.dinnerStops.map(i=>i+1).join(", ")}.`}</dd></div>
    <div><dt>Starting point</dt><dd>{request.planningMode==="surprise"?"Begins at the first activity.":"Exact starting location was not retained."}</dd></div>
    {(request.geography.strictDestination||request.geography.excludedRegions.length>0||request.requireWheelchairAccess||request.requireAvailability)&&<div><dt>Other requirements</dt><dd>{request.geography.strictDestination&&"Stay within the destination. "}{request.geography.excludedRegions.length>0&&`Excluded areas: ${request.geography.excludedRegions.join(", ")}. `}{request.requireWheelchairAccess&&"Wheelchair access required; not reverified. "}{request.requireAvailability&&"Availability required; not reverified."}</dd></div>}
    {(request.budget!=null||request.groupBudget!=null)&&<div><dt>Budget</dt><dd>{request.budget!=null&&`$${request.budget} per person. `}{request.groupBudget!=null&&`$${request.groupBudget} for the group. `}Current prices are unverified.</dd></div>}
   </dl>
  </details>
 </section>;
}
