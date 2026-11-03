"use client";
import {useState} from 'react';
import type {Plan} from '@/lib/planner';
import type {AdvancedState,AdvancedQuestion} from '@/lib/advanced-planning';
import {GoogleCredits} from './venue-details';
import {OpeningHours} from './opening-hours';
import {safeMapsUrl} from '@/lib/venue-details';
const minutes=(seconds:number)=>`${Math.round(seconds/6)/10} min`;
export function AdvancedPlanCard({plan,index,onSelect,selected}:{plan:Plan;index:number;onSelect:()=>void;selected:boolean}){
 const [expanded,setExpanded]=useState(false);
 const p=plan.advanced!;
 return <article className={`plan-card ${plan.theme}`}>
  <div className="card-visual"><span className="card-number">0{index+1}</span><span className="demo-pill">REAL VENUES</span><div className="real-route-poster" aria-hidden="true">{p.stops.map((s,i)=><div key={s.occurrence}><span>{i+1}. {s.name}</span></div>)}{p.ending==='origin'&&<div>↩ Return to start</div>}{p.endpoint&&<div>→ {p.endpoint.name}</div>}</div></div>
  <div className="card-body"><p className="card-label">OPTION {index+1} · {plan.transport==='walking'?'Walking':'Driving'}</p><h3 className="real-plan-title">{plan.title}</h3><p>{plan.location} · {plan.date}</p>
   <div className={p.state==='unverified'?'plan-warning':'details-note'} role="note"><strong>{p.state==='feasible'?'Timing supported by the supplied evidence':'Requirements not fully verified'}</strong></div>
   <p>Known route travel: {minutes(p.knownTravelSeconds)}</p><p>Whole journey: {p.elapsedUpperSeconds===null?`at least ${minutes(p.elapsedLowerSeconds)}; full duration unknown`:p.elapsedLowerSeconds===p.elapsedUpperSeconds?minutes(p.elapsedLowerSeconds):`${minutes(p.elapsedLowerSeconds)} to ${p.upperExclusive?'under ':''}${minutes(p.elapsedUpperSeconds)}`}</p>
   {p.totalConstraint&&<p>Whole-trip limit: {p.totalConstraint.relation} {p.totalConstraint.minutes} min · {p.durationState}.</p>}{p.deadlineSource&&<p>Deadline: {p.deadlineSource} · {p.deadlineState}.</p>}
   {p.reasons.length>0&&<details><summary>What needs checking</summary><ul>{p.reasons.map(r=><li key={r}>{r}</li>)}</ul></details>}
   <div className="card-bottom"><button type="button" className="secondary-button" aria-pressed={selected} onClick={onSelect}>{selected?'Selected itinerary':'Select itinerary'}</button><button type="button" className="plan-link" aria-expanded={expanded} aria-controls={`details-${p.id}`} onClick={()=>setExpanded(!expanded)}>{expanded?'Close plan':'View plan'}</button></div>
   <div hidden={!expanded} id={`details-${p.id}`} className="plan-details"><p>{p.legs.some(l=>l.role==='origin_to_first')?'Start → ':''}{p.stops.map(s=>s.name).join(' → ')}{p.ending==='origin'?' → Return to Start':p.endpoint?' → '+p.endpoint.name:''}</p>
    <ol>{p.stops.map(s=><li key={s.occurrence}><div><strong>{s.name}</strong><p>{s.address}</p><p>Requested stop {s.occurrence+1}: {s.requested} · {s.requirement}</p><p>{s.duration?`${s.duration.relation} ${s.duration.minutes} min (user supplied)`:'Visit duration unknown'}</p>{(s.arrival||s.departure)&&<p>Projected {s.arrival??'unknown arrival'} → {s.departure??'unknown departure'}</p>}<p>Visit hours compatibility: {s.hoursState}</p><OpeningHours hours={s.hours}/>{s.rating!==null&&<p>Provider rating: {s.rating}{s.ratingCount!==null?` (${s.ratingCount} reviews)`:''}</p>}{safeMapsUrl(s.mapsUrl)&&<a href={s.mapsUrl} target="_blank" rel="noopener noreferrer">View {s.name} on Google Maps</a>}</div></li>)}</ol>
    <ul aria-label="Travel legs">{p.legs.map((l,i)=><li key={i}>{({origin_to_first:'Start to first stop',inter_activity:'Between stops',return_to_origin:'Return to starting point',final_destination:'Final destination'} as Record<string,string>)[l.role]}{l.fromOccurrence!==null?` (from requested stop ${l.fromOccurrence+1})`:''}: {l.seconds===null?'Unverified':minutes(l.seconds)} · {l.mode==='walk'?'Walking':'Driving'} estimate{l.meters!==null?` · ${(l.meters/1609.344).toFixed(2)} route miles`:''}{l.mapsUrl&&safeMapsUrl(l.mapsUrl)&&<> · <a href={l.mapsUrl} target="_blank" rel="noopener noreferrer">View this leg on Google Maps</a></>}</li>)}</ul>
    {p.endpoint&&safeMapsUrl(p.endpoint.mapsUrl)&&<a href={p.endpoint.mapsUrl} target="_blank" rel="noopener noreferrer">Final destination: {p.endpoint.name}</a>}
    {p.omitted.length>0&&<p>Optional stops omitted: {p.omitted.map(s=>`${s.requested} (${s.reason.replaceAll('_',' ')})`).join('; ')}.</p>}
   </div><GoogleCredits credits={[...p.stops.flatMap(s=>s.credits),...(p.endpoint?.credits??[])]}/>
  </div>
 </article>;
}
function Answer({question,busy,onAnswer}:{question:AdvancedQuestion;busy:boolean;onAnswer:(answer:Record<string,unknown>)=>void}){
 const [value,setValue]=useState('');const [relation,setRelation]=useState('approximate');
 if(question.field==='place')return <fieldset disabled={busy}><legend>{question.question}</legend>{question.choices?.map(c=><div key={c.placeId}><button type="button" className="secondary-button" onClick={()=>onAnswer({choice:{occurrence:question.occurrence,placeId:c.placeId}})}>{c.name} — {c.address}</button><GoogleCredits credits={c.attributions}/></div>)}</fieldset>;
 if(question.field==='origin')return <p>{question.question} Use “Where should your outing start?” above, then plan again.</p>;
 return <form onSubmit={event=>{event.preventDefault();const field=question.field;onAnswer(field==='dwell'?{dwell:{occurrence:question.occurrence,minutes:Number(value),relation}}:{[field]:value});}}><label>{question.question}<input placeholder={question.field==='date'?'YYYY-MM-DD':question.field==='departure'?'HH:MM, e.g. 14:00':undefined} required disabled={busy} type={question.field==='dwell'?'number':'text'} min={question.field==='dwell'?0:undefined} max={question.field==='dwell'?10080:undefined} step={question.field==='dwell'?1:undefined} value={value} onChange={e=>setValue(e.target.value)}/></label>{question.field==='departure'&&<small>Use destination-local 24-hour time: 14:00 means 2 PM.</small>}{question.field==='dwell'&&<label>Duration meaning<select value={relation} onChange={e=>setRelation(e.target.value)} disabled={busy}><option value="approximate">My estimate (approximate)</option><option value="exact">Exactly this long</option><option value="minimum">At least this long</option><option value="maximum">At most this long</option><option value="under">Strictly under this long</option></select></label>}<button className="secondary-button" type="submit" disabled={busy}>Apply answer</button></form>;
}
export function AdvancedClarifications({state,busy,onAnswer}:{state:AdvancedState;busy:boolean;onAnswer:(answer:Record<string,unknown>)=>void}){
 return <section aria-label="Advanced outing details"><p role="status">{state.data.message}</p>{state.data.questions.map(q=><Answer key={q.field+q.occurrence} question={q} busy={busy} onAnswer={onAnswer}/>)}<p className="details-note">Route estimates and stated visit durations do not guarantee actual arrival or availability. Up to three distinct options from a bounded search; additional discovery and beyond-limit exploration are unavailable for advanced outings.</p></section>;
}
