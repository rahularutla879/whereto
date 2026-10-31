"use client";
import {useEffect,useRef} from "react";
import { activityLabel,formatTime,type Activity } from "@/lib/planner";
import { preferenceText,type SavedPlan } from "@/lib/saved-plans";
import { GoogleCredits } from "./venue-details";
import type {RefreshedVenue} from "@/lib/saved-plan-refresh";
export function SavedCards({saved,venues,refresh,busy,message}:{saved:SavedPlan;venues:Record<string,RefreshedVenue>;refresh:(id:string)=>void;busy:boolean;message:string}){
 const request=saved.constraints;
 const selectedCard=useRef<HTMLElement|null>(null);
 useEffect(()=>{selectedCard.current?.focus();},[saved]);
 return <section aria-label="Saved itineraries" className="saved-results">
  <h3>Saved plan · {request.location} · {request.date}</h3>
  <p>{saved.dataMode==="mock"?"Saved fictional sample":"Saved itinerary · Venue details refresh only when you ask. Routes have not been refreshed."}</p>
  {message&&<p role="status" aria-live="polite">{message}</p>}
  <div className="plans-grid">{saved.itineraries.map((option,i)=><article key={option.candidateId} ref={option.candidateId===saved.selectedId?selectedCard:undefined} tabIndex={-1} className={`plan-card ${["lavender","peach","mint"][i]} ${option.candidateId===saved.selectedId?"saved-selected":""}`} aria-label={`Saved option ${i+1}${option.candidateId===saved.selectedId?", selected":""}`}>
   <div className="card-body"><p className="card-label">Saved option {i+1}{option.candidateId===saved.selectedId?" · Selected option":""}</p>
   <h3 className="real-plan-title">{option.stops.map(s=>s.fictional?.name??venues[s.reference]?.name??`${activityLabel(s.activity as Activity)} stop`).join(" → ")}</h3>
   <p>{request.location} · {request.date}</p>
   <ol className="saved-stops">{option.stops.map(s=>{const detail=venues[s.reference];return <li key={s.position}><strong>{s.position+1}. {s.fictional?.name??detail?.name??`${activityLabel(s.activity as Activity)} stop`}</strong><p>{request.activityIntents[s.activity]??activityLabel(s.activity as Activity)}</p>
    {s.fictional?<p>Fictional venue · {s.fictional.neighborhood}. {s.start!==null?`${formatTime(s.start)}–${formatTime(s.end)}`:"Sample timing unavailable"}</p>:<><p>{detail?.address??"Saved stop · Current venue details not loaded."}</p>{detail?.status==="refreshed"?<p>Details retrieved {detail.refreshedAt?new Date(detail.refreshedAt).toLocaleString():"now"}. Hours and availability not checked.</p>:detail?.status==="stale"?<p role="note">Earlier details from {detail.refreshedAt?new Date(detail.refreshedAt).toLocaleString():"a previous lookup"}. Refresh unavailable. {detail.message}</p>:detail?.message&&<p role="note">{detail.message}</p>}
    {detail?.businessStatus?.startsWith("CLOSED")&&<p className="plan-warning" role="note">{detail.businessStatus==="CLOSED_PERMANENTLY"?"Reported permanently closed":"Reported temporarily closed"}. Your original stop is kept.</p>}
    <GoogleCredits credits={detail?.attributions}/></>}
   </li>})}</ol>
   {saved.dataMode==="real"?<><p className="details-note">Travel estimates unavailable. Saved stop order is preserved.</p><button type="button" className="secondary-button" disabled={busy} aria-busy={busy} onClick={()=>refresh(option.candidateId)}>Refresh venue details<span className="sr-only"> for saved option {i+1}</span></button></>:option.stops.length>1&&<p>Fictional inter-stop travel: {option.fictionalMetrics?.totalTravel??"Unknown"} minutes.</p>}
  </div></article>)}</div>
  <details className="estimates-details"><summary>Saved planning constraints</summary><p>{formatTime(request.startTime)}–{formatTime(request.endTime)} · {request.calendarTimezone??"Timezone unavailable"} · {request.transport??"Travel mode unspecified"}</p><p>First-stop travel: {preferenceText(request.firstTravel)}. Between activities: {preferenceText(request.betweenTravel)}.</p><p>{request.planningMode==="surprise"?"Begins at the first activity.":"Exact starting location was not retained."} {request.geography.strictDestination?"Stay within the destination.":""} {request.requireWheelchairAccess?"Wheelchair access required; not reverified.":""} {request.requireAvailability?"Availability required; not reverified.":""}</p><p>{request.travel!==null?`Total inter-stop limit: ${request.travel} minutes. `:""}{request.maxLegTravel!==null?`Per-leg limit: ${request.maxLegTravel} minutes. `:""}{request.maxFirstLegTravel!==null?`First-leg limit: ${request.maxFirstLegTravel} minutes. `:""}{request.geography.excludedRegions.length?`Excluded: ${request.geography.excludedRegions.join(", ")}.`:""} {request.allowRevisits?"Revisits permitted.":"No repeated venues."} {request.dinner?"Dinner requested.":""} {request.dinnerStops?.length?`Dinner at stops: ${request.dinnerStops.map(i=>i+1).join(", ")}.`:""} {request.budget!=null?`Saved per-person budget: $${request.budget}; current prices are unverified.`:""} {request.groupBudget!=null?`Saved total-group budget: $${request.groupBudget}; current prices are unverified.`:""}</p></details>
 </section>;
}
