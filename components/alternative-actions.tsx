import * as React from "react";
export function AlternativeActions({real,canCombine,canExplore,busy,disabled,notice,onAction,onAdjust}:{
  real:boolean;canCombine:boolean;canExplore:boolean;busy:boolean;disabled:boolean;notice:string;
  onAction:(explore:boolean)=>void;onAdjust:()=>void;
}){
  return <div className="more-options" aria-busy={busy}>
    <div><button type="button" className="secondary-button" disabled={!canCombine||disabled||busy} onClick={()=>onAction(false)}>Show different options</button><p>Try different combinations from places already found.</p></div>
    {real&&<div><button type="button" className="secondary-button" disabled={!canExplore||disabled||busy} onClick={()=>onAction(true)}>Explore farther</button><p>Discover new places in a wider area.</p></div>}
    <p role="status">{notice}</p>
    <button type="button" className="plan-link" disabled={busy} onClick={onAdjust}>Adjust travel preference</button>
  </div>;
}
