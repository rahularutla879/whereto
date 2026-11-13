'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {MapPin,Sparkles,ArrowRight} from 'lucide-react';
import {ResultsInformation} from './results-information';
import {HeroArtwork} from './artwork';import {PlanCard} from './plan-card';import {OutingSummary} from './outing-summary';import {OutingDateField} from './outing-date-field';
import {PrivateOrdinaryClient,type OrdinaryView,UI_VERSION} from '@/lib/private-ordinary-client';
import {EMPTY_PREFERENCES} from '@/lib/planner';import {VenueDetailsSession} from '@/lib/venue-details';
import type {ClarificationAnswers} from '@/lib/planning-client';
async function dependencies(){try{const r=await fetch('/api/planning-mode',{cache:'no-store',redirect:'manual',signal:AbortSignal.timeout(5000)}),d=await r.json();return r.ok&&d.privateOrdinary?.version===UI_VERSION&&d.privateOrdinary.dependencyReady===true;}catch{return false;}}
export function PrivateOrdinaryExperience(){
 const [client]=useState(()=>new PrivateOrdinaryClient());const active=useRef<AbortController|null>(null);const [view,setView]=useState<OrdinaryView>(()=>client.view),[busy,setBusy]=useState(false),[ready,setReady]=useState(false);
 const [text,setText]=useState(''),[preferences,setPreferences]=useState({...EMPTY_PREFERENCES}),[answers,setAnswers]=useState<ClarificationAnswers>({}),[lat,setLat]=useState(''),[lon,setLon]=useState(''),[confirmed,setConfirmed]=useState(false);
 const [details]=useState(()=>new VenueDetailsSession());
 async function check(){setReady(await dependencies());}
 useEffect(()=>{
  let mounted=true;void dependencies().then(value=>{if(mounted)setReady(value);});const reset=()=>{active.current?.abort();active.current=null;client.clear();setView({...client.view});setBusy(false);setText('');setAnswers({});setConfirmed(false);setLat('');setLon('');setPreferences({...EMPTY_PREFERENCES});};
  const show=(event:PageTransitionEvent)=>{if(event.persisted)reset();};window.addEventListener('pagehide',reset);window.addEventListener('pageshow',show);
  const clock=setInterval(()=>{const before=client.view;client.expire();if(before!==client.view)setView({...client.view});},1000);
  return ()=>{mounted=false;active.current?.abort();clearInterval(clock);window.removeEventListener('pagehide',reset);window.removeEventListener('pageshow',show);};
 },[client]);
 async function action(work:(signal:AbortSignal)=>Promise<void>){if(active.current)return;const controller=new AbortController();active.current=controller;setBusy(true);try{await work(controller.signal);if(active.current===controller){setView({...client.view});if(client.view.phase==='empty')setConfirmed(false);}}finally{if(active.current===controller){active.current=null;setBusy(false);}}}
 function submit(e:FormEvent){e.preventDefault();if(!ready)return;if(view.phase==='empty')void action(s=>client.interpret(text,preferences,s));else if(view.phase==='pending')void action(s=>client.answer(answers,s));else if(view.phase==='ready'&&confirmed)void action(s=>client.generate(Number(lat),Number(lon),undefined,s));}
 const editable=view.phase==='empty'&&!busy;
 return <>
 <header className="site-header shell"><a href="#" className="brand"><MapPin size={20}/>where to?</a><nav><a href="/how-it-works">How it works</a></nav></header>
 <main><section className="hero shell"><div className="hero-copy"><p className="eyebrow">PRIVATE LOCAL SYNTHETIC WORKFLOW</p><h1>Less planning.<br/><em>More hanging out.</em></h1><p className="hero-description">Ordinary planning only. No real model or Maps requests.</p></div><div className="hero-art-wrap"><HeroArtwork/></div></section>
 <section className="planner-section shell" id="planner"><form className="planner" onSubmit={submit}>
 <div className="planner-topline"><h2><Sparkles size={19}/>What are we getting into?</h2></div>
 <p role="status">{ready?'Synthetic ordinary dependencies available. This is not production or financial authorization.':'Private ordinary dependencies unavailable. No provider request will be retried.'}</p><button type="button" className="secondary-button" disabled={busy} onClick={()=>void check()}>Check dependencies</button>
 <label htmlFor="outing">Describe your outing</label><textarea id="outing" value={text} disabled={!editable} maxLength={1200} required rows={3} onChange={e=>setText(e.target.value)}/>
 <div id="preferences" className="preferences-panel"><p>Set source preferences before interpretation. To change meaning later, discard this outing first.</p><div className="preferences-grid">
 <label>Location<input id="destination-preference" value={preferences.location} disabled={!editable} maxLength={80} onChange={e=>setPreferences({...preferences,location:e.target.value})}/></label>
 <fieldset disabled={!editable}><OutingDateField real value={preferences.date} onChange={value=>{if(editable)setPreferences({...preferences,date:value});}}/><p>{!editable?'Date changes require a new interpretation; use the requested clarification below when pending.':''}</p></fieldset>
 <label>Travel mode<select aria-label="Travel mode" value={preferences.transport||'driving'} disabled={!editable} onChange={e=>setPreferences({...preferences,transport:e.target.value as 'walking'|'driving'})}><option value="driving">Driving</option><option value="walking">Walking</option></select></label>
 </div></div>
 {view.summary&&<OutingSummary value={view.summary} real synthetic dirty={false} loading={busy} onEdit={()=>void action(s=>client.discard(s))}/>}
 {view.phase==='pending'&&<div className="clarification-panel" aria-label="Outing follow-up"><h3>A little more detail</h3>{view.questions.map(q=><label key={q.field}>{q.question}<input aria-label={'Answer '+q.field} value={answers[q.field]??''} maxLength={300} disabled={busy} onChange={e=>setAnswers({...answers,[q.field]:e.target.value})}/></label>)}</div>}
 {view.phase==='ready'&&<fieldset disabled={busy}><legend>Confirm execution controls</legend><p>Use explicitly confirmed coordinates. Lookup is unavailable. All resulting venues and routes are synthetic. Search-radius editing is unavailable because this profile does not establish an independent search point.</p><div className="preferences-grid"><label>Origin latitude<input aria-label="Origin latitude" type="number" step="any" min="-90" max="90" required value={lat} onChange={e=>{setLat(e.target.value);setConfirmed(false);}}/></label><label>Origin longitude<input aria-label="Origin longitude" type="number" step="any" min="-180" max="180" required value={lon} onChange={e=>{setLon(e.target.value);setConfirmed(false);}}/></label></div><label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I confirm this starting point for this synthetic outing.</label></fieldset>}
 <p role="status" aria-live="polite">{busy?'Checking the protected outing action…':view.message}</p>
 <div className="planner-actions">{['empty','pending','ready'].includes(view.phase)&&<button type="submit" className="primary-button" disabled={busy||!ready||view.phase==='ready'&&!confirmed}>{view.phase==='empty'?'Understand my outing':view.phase==='pending'?'Continue planning':'Generate itinerary'}<ArrowRight size={18}/></button>}
 {view.phase!=='empty'&&<button type="button" className="secondary-button" disabled={busy} onClick={()=>void action(s=>client.discard(s))}>Discard outing and edit</button>}</div>
 <p>No raw interpretation, source text, handle or itinerary is saved to browser storage. Refresh/back navigation discards this page and never resumes provider work. Lost responses require an explicit new outing.</p>
 </form></section>
 <section className="plans-section shell" id="plans"><div className="section-heading"><h2>Your next good time.</h2><span className="sample-data-label">Synthetic evidence only</span></div>{view.result&&<><p>{view.result.plans.length?`${view.result.plans.length} synthetic provisional options. Prices, hours and availability need confirmation.`:view.result.message}</p><div className="plans-grid">{view.result.plans.map((plan,index)=><PlanCard key={plan.id} plan={plan} index={index} detailsSession={details} synthetic/>)}</div><ResultsInformation notes={view.result.notes} needsChecking real={false}/></>}</section>
 </main></>;
}
