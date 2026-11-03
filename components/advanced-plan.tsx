"use client";
import {useRef,useState} from 'react';
import type {AdvancedState,AdvancedQuestion,AdvancedOption} from '@/lib/advanced-planning';
import {GoogleCredits} from './venue-details';
import {OpeningHours} from './opening-hours';
import {safeMapsUrl} from '@/lib/venue-details';
const relation=(value:string)=>({exact:'Exactly',minimum:'At least',maximum:'At most',under:'Under',approximate:'About'} as Record<string,string>)[value]??value;
const verdict=(value:string)=>({feasible:'fits the supplied estimates',infeasible:'does not fit',unverified:'not yet verified'} as Record<string,string>)[value]??value;
const minutes=(seconds:number)=>`${Math.round(seconds/6)/10} min`;

/** Only the extra itinerary content; the card shell is shared with ordinary plans. */
export function AdvancedDetails({option:p}:{option:AdvancedOption}){
 return <>
  <ol>{p.stops.map((s,i)=><li key={s.occurrence}><span className="stop-number">{i+1}</span><div>
   <strong>{s.name}</strong><span>{s.address}</span>
   <span>{s.requirement==='optional'?'Optional visit · ':''}{s.duration?`${relation(s.duration.relation)} ${s.duration.minutes} minutes (your duration)`:'Visit duration not supplied'}</span>
   {(s.arrival||s.departure)&&<span>Projected {s.arrival??'unknown arrival'} → {s.departure??'unknown departure'}</span>}
   <span>Visit hours: {s.hoursState}</span><OpeningHours hours={s.hours}/>
   {s.rating!==null&&<span>Provider rating: {s.rating}{s.ratingCount!==null?` (${s.ratingCount} reviews)`:''}</span>}
   {safeMapsUrl(s.mapsUrl)&&<a href={s.mapsUrl} target="_blank" rel="noopener noreferrer">View {s.name} on Google Maps</a>}
  </div></li>)}</ol>
  <ul aria-label="Travel legs">{p.legs.map((l,i)=><li key={i}>{({origin_to_first:'Start to first stop',inter_activity:'Between stops',return_to_origin:'Return to starting point',final_destination:'Final destination'} as Record<string,string>)[l.role]}: {l.seconds===null?'Unverified':minutes(l.seconds)} · {l.mode==='walk'?'Walking':'Driving'} estimate{l.meters!==null?` · ${(l.meters/1609.344).toFixed(2)} miles`:''}{l.mapsUrl&&safeMapsUrl(l.mapsUrl)&&<> · <a href={l.mapsUrl} target="_blank" rel="noopener noreferrer">View this leg on Google Maps</a></>}</li>)}</ul>
  {p.endpoint&&safeMapsUrl(p.endpoint.mapsUrl)&&<p>Finish at <a href={p.endpoint.mapsUrl} target="_blank" rel="noopener noreferrer">{p.endpoint.name}</a></p>}
  <p>Known route travel: {minutes(p.knownTravelSeconds)}.</p>
  <p>Whole journey: {p.elapsedUpperSeconds===null?`at least ${minutes(p.elapsedLowerSeconds)}; full duration unknown`:p.elapsedLowerSeconds===p.elapsedUpperSeconds?minutes(p.elapsedLowerSeconds):`${minutes(p.elapsedLowerSeconds)} to ${p.upperExclusive?'under ':''}${minutes(p.elapsedUpperSeconds)}`}.</p>
  {p.totalConstraint&&<p>Whole-trip requirement: {relation(p.totalConstraint.relation)} {p.totalConstraint.minutes} min · {verdict(p.durationState)}.</p>}
  {p.deadlineSource&&<p>Deadline: {p.deadlineSource} · {verdict(p.deadlineState)}.</p>}
  {p.travelException&&<p role="note">Shown under your explicit travel exception. Original limits are kept; this option exceeds them.</p>}
  {p.reasons.length>0&&<details><summary>Timing and requirements</summary><ul>{p.reasons.map(r=><li key={r}>{r}</li>)}</ul></details>}
  {p.omitted.length>0&&<p>Optional stops omitted: {p.omitted.map(s=>`${s.requested} (${s.reason.replaceAll('_',' ')})`).join('; ')}.</p>}
 </>;
}
function Answer({question,busy,onAnswer}:{question:AdvancedQuestion;busy:boolean;onAnswer:(answer:Record<string,unknown>)=>void}){
 const [value,setValue]=useState('');const [relation,setRelation]=useState('approximate');
 const input=useRef<HTMLInputElement>(null);
 if(question.field==='place')return <fieldset disabled={busy} className="endpoint-clarification"><legend>{question.question}</legend>{question.choices?.map(c=><div key={c.placeId}><button type="button" className="secondary-button" onClick={()=>onAnswer({choice:{occurrence:question.occurrence,placeId:c.placeId}})}>{c.name} — {c.address}</button><GoogleCredits credits={c.attributions}/></div>)}</fieldset>;
 if(question.field==='origin')return <p>{question.question} Confirm it using the starting-location controls above, then continue.</p>;
 return <div className="advanced-answer"><label><span>{question.question}</span>
  <input ref={input} required disabled={busy} type={question.field==='dwell'?'number':'time'} min={question.field==='dwell'?0:undefined} max={question.field==='dwell'?10080:undefined} step={question.field==='dwell'?1:60} value={value} onChange={e=>setValue(e.target.value)}/>
  {question.field==='departure'&&<small>Use the destination&apos;s local departure time.</small>}
 </label>{question.field==='dwell'&&<label><span>Duration meaning</span><select value={relation} onChange={e=>setRelation(e.target.value)} disabled={busy}><option value="approximate">My estimate (approximate)</option><option value="exact">Exactly this long</option><option value="minimum">At least this long</option><option value="maximum">At most this long</option><option value="under">Strictly under this long</option></select></label>}
 <button className="secondary-button" type="button" disabled={busy} onClick={()=>{if(input.current?.reportValidity())onAnswer(question.field==='dwell'?{dwell:{occurrence:question.occurrence,minutes:Number(value),relation}}:{departure:value});}}>Continue planning</button></div>;
}
export function AdvancedClarifications({state,busy,onAnswer,nearOrigin=false}:{state:AdvancedState;busy:boolean;onAnswer:(answer:Record<string,unknown>)=>void;nearOrigin?:boolean}){
 const questions=state.data.questions;
 if(!questions.length)return null;
 return <div className="clarification-panel" aria-label="Outing follow-up"><p className="details-heading">A little more detail</p><p role="status">{state.data.message}</p>
  {questions.some(q=>q.field==='date')&&<p>Choose the outing date in Date above, then continue planning.</p>}
  {questions.some(q=>q.field==='destination')&&<><p>Enter the search area in Location above, then continue planning.</p>{nearOrigin&&<button type="button" className="secondary-button" disabled={busy} onClick={()=>onAnswer({searchNearOrigin:true})}>Search near my confirmed starting point</button>}</>}
  <div className="preferences-grid">{questions.filter(q=>!['date','destination'].includes(q.field)).map(q=><Answer key={q.field+q.occurrence} question={q} busy={busy} onAnswer={onAnswer}/>)}</div>
 </div>;
}
