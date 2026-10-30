import * as React from "react";
export function AlternativeActions({real,canCombine,canExplore,busy,disabled,notice,onAction,onAdjust,nearby=false,canShowBeyond=false,onBeyond,onCompliant,showingBeyond=false}:{
  real:boolean;canCombine:boolean;canExplore:boolean;busy:boolean;disabled:boolean;notice:string;
  onAction:(explore:boolean)=>void;onAdjust:()=>void;nearby?:boolean;canShowBeyond?:boolean;onBeyond?:()=>void;onCompliant?:()=>void;showingBeyond?:boolean;
}){
  return <div className="more-options" aria-busy={busy}>
    <div className="alternative-row"><button type="button" className="secondary-button" disabled={!canCombine||disabled||busy} onClick={()=>onAction(false)}>Show different options</button><p>New combinations from places already found.</p></div>
    {real&&<div className="alternative-row"><button type="button" className="secondary-button" disabled={!canExplore||disabled||busy} onClick={()=>onAction(true)}>{nearby?"Search more nearby places":"Explore farther"}</button><p>Discover more places and expand the search. Your travel limits stay unchanged.</p></div>}
    {real&&canShowBeyond&&!showingBeyond&&<button type="button" className="plan-link beyond-choice" disabled={busy||disabled} onClick={onBeyond}>Show options beyond my limit</button>}
    {showingBeyond&&<button type="button" className="secondary-button" disabled={busy} onClick={onCompliant}>Return to within-limit options</button>}
    <p role="status">{notice}</p>
    {!/temporary .*limit|Google's current|accounting|couldn't verify enough travel/i.test(notice) && <button type="button" className="plan-link" disabled={busy} onClick={onAdjust}>Adjust travel preference</button>}
  </div>;
}
