"use client";
import type {AdvancedState,AdvancedOption} from '@/lib/advanced-planning';
const relation=(value:string)=>({exact:'Exactly',minimum:'At least',maximum:'At most',under:'Under',approximate:'About'} as Record<string,string>)[value]??value;
const verdict=(value:string)=>({feasible:'fits the supplied estimates',infeasible:'does not fit',unverified:'not yet verified'} as Record<string,string>)[value]??value;
import {formatSeconds as minutes} from '@/lib/duration-format';

/** Advanced constraints extend the shared ordered itinerary, never its venue facts. */
export function AdvancedDetails({option:p}:{option:AdvancedOption}){
 return <>
  <p className="details-note">Total route travel: {minutes(p.knownTravelSeconds)}{p.ending==='origin'?' including return':''}.</p>
  {(p.totalConstraint||p.deadlineSource)&&<details className="estimates-details"><summary>Timing and time budget</summary>
   {p.totalConstraint&&<p>{p.budgetScope==='travel'?'Travel-only':'Whole-trip'} requirement: {relation(p.totalConstraint.relation)} {p.totalConstraint.minutes} min {p.budgetScope==='travel'?'excluding visits (your explicit override)':'including visits and all route legs'} · {verdict(p.durationState)}.</p>}
   {p.budgetScope!=='travel'&&<p>Whole journey: {p.elapsedUpperSeconds===null?`at least ${minutes(p.elapsedLowerSeconds,'lower')}; visit timing needs confirmation`:p.elapsedLowerSeconds===p.elapsedUpperSeconds?minutes(p.elapsedLowerSeconds):`${minutes(p.elapsedLowerSeconds,'lower')} to ${p.upperExclusive?'under ':''}${minutes(p.elapsedUpperSeconds,'upper')}`}.</p>}
   {p.deadlineSource&&<p>Finish {p.deadlineSource} · {verdict(p.deadlineState)}. This includes time at stops.</p>}
   {p.state==='unverified'&&<p>Visit schedules still need confirmation. Approximate durations do not guarantee a finish time.</p>}
  </details>}
  {p.omitted.length>0&&<p className="details-note">Optional stops not included: {p.omitted.map(s=>s.requested).join('; ')}. {[...new Set(p.omitted.map(s=>s.explanation).filter(Boolean))].join(' ')}</p>}
 </>;
}
export function AdvancedClarifications({state,busy,onAnswer,onChooseTime,nearOrigin=false}:{state:AdvancedState;busy:boolean;onAnswer:(answer:Record<string,unknown>)=>void;nearOrigin?:boolean;onChooseTime?:()=>void}){
 const questions=state.data.questions;
 const offers=state.data.closureOffers??[];
 if(!questions.length&&!offers.length)return null;
 return <div className="clarification-panel" aria-label="Outing follow-up"><p className="details-heading">A little more detail</p>{!offers.length&&<p role="status">{state.data.message}</p>}
  {offers.map(o=><div key={o.occurrence}><p>{o.message}</p><button type="button" className="secondary-button" disabled={busy} onClick={onChooseTime}>Choose another time or date</button><button type="button" className="secondary-button" disabled={busy} onClick={()=>onAnswer({proceedClosed:o.token})}>Proceed anyway</button></div>)}
  {questions.some(q=>q.field==='date')&&<p>Choose the outing date in Date above, then continue planning.</p>}
  {questions.some(q=>q.field==='destination')&&<><p>Enter the search area in Location above, then continue planning.</p>{nearOrigin&&<button type="button" className="secondary-button" disabled={busy} onClick={()=>onAnswer({searchNearOrigin:true})}>Search near my confirmed starting point</button>}</>}
  {questions.filter(q=>!['date','destination'].includes(q.field)).map(q=><p key={q.field+q.occurrence}>{q.question} {q.field==='origin'?'Use Starting location above.':'Use Visit times and itinerary preferences above, then continue planning.'}</p>)}
 </div>;
}
