"use client";
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { StartingConfirmation } from "../lib/starting-confirmation";
import { requestStartingLocation } from "../lib/location";
import { StartingPlaceSession, type StartingMatch } from "../lib/starting-places";
import type { FirstTravel, OriginPreparation } from "../lib/starting-areas";
import { FirstPreference } from "../lib/first-preference";
import { GoogleCredits } from "./venue-details";
import type { LocationContext } from "../lib/planning-client";
export type StartingLocationHandle = { cancel: () => void; editTravel: () => void; prepare: (input?: OriginPreparation) => Promise<LocationContext | null> };
type Mode = "none" | "current" | "manual" | "surprise";
type Selection = NonNullable<LocationContext["startingLocation"]>;
export function LocationControls({ onChange,onStage,lookupEnabled=false,mock=false,ref }: {
  onChange:(value:LocationContext,preparing?:boolean)=>void;onStage?:(stage:string)=>void;lookupEnabled?:boolean;mock?:boolean;ref?:Ref<StartingLocationHandle>
}) {
  const disclosure=useRef<HTMLDetailsElement>(null),pending=useRef(new StartingConfirmation());
  const lookup=useRef(new StartingPlaceSession()),version=useRef(0);
  const preference=useRef(new FirstPreference()),between=useRef(new FirstPreference());
  const originInput=useRef<OriginPreparation|undefined>(undefined),removed=useRef("");
  const saved=useRef<Partial<Record<"current"|"manual",Selection>>>({});
  const [mode,setMode]=useState<Mode>("none"),[selected,setSelected]=useState<Selection|null>(null);
  const [manual,setManual]=useState(""),[notice,setNotice]=useState(""),[searching,setSearching]=useState(false);
  const [matches,setMatches]=useState<StartingMatch[]>([]),[credits,setCredits]=useState<StartingMatch["attributions"]>([]);
  const [first,setFirst]=useState(""),[unit,setUnit]=useState<FirstTravel["unit"]>("minutes"),[flexibility,setFlexibility]=useState<FirstTravel["mode"]>("strict");
  const [amount,setAmount]=useState(""),[betweenUnit,setBetweenUnit]=useState<FirstTravel["unit"]>("minutes"),[betweenMode,setBetweenMode]=useState<FirstTravel["mode"]>("strict");
  const [conflict,setConflict]=useState(false);
  const cancel=()=>pending.current.cancel();
  useEffect(()=>()=>{version.current++;pending.current.cancel();lookup.current.clear();},[]);
  const changed=(value:LocationContext)=>onChange(value,pending.current.waiting);
  function firstKey(input=originInput.current){return JSON.stringify([input?.sourceKey??null,input?.firstTravel??null,input?.maxFirstLegTravel??null]);}
  function hasConflict(){const input=originInput.current;return !!(input?.firstTravel||input?.maxFirstLegTravel!=null)&&removed.current!==firstKey();}
  function context(point:Selection|null=selected,surprise=mode==="surprise"):LocationContext {
    if(surprise)return {planningMode:"surprise",locationFirst:true,firstTravel:null,maxFirstLegTravel:null,betweenTravel:between.current.value};
    return {planningMode:"origin",locationFirst:true,firstTravel:preference.current.value,
      ...(point?{startingLocation:point,currentArea:{coordinates:point.point.coordinates}}:{}),
      ...(originInput.current?.betweenTravel?{betweenTravel:originInput.current.betweenTravel}:{})};
  }
  function prepareSurprise(){
    if(hasConflict()){
      setConflict(true);setNotice("Surprise Me starts at the first activity. Travel from an unspecified origin cannot be checked. Choose a location-based mode or explicitly remove that first-stop constraint.");
      onStage?.("Resolve first-stop preference");return null;
    }
    setConflict(false);setNotice("Surprise Me — your outing begins at the first activity. Travel is only between venues.");
    return context(null,true);
  }
  function chooseMode(next:Mode){
    version.current++;setSearching(false);setMatches([]);setCredits([]);setConflict(false);
    if(selected&&(mode==="current"||mode==="manual"))saved.current[mode]=selected;
    const restored=next==="current"||next==="manual"?saved.current[next]??null:null;
    setMode(next);setSelected(restored);
    if(next==="surprise"){
      const value=prepareSurprise();
      if(value&&!pending.current.confirm(value))changed(value);
      else if(!value)changed(context(null,true));
    }else{
      setNotice(restored?"Previously confirmed starting point restored. First-leg travel will be checked again.":next==="current"?"Select Share my location to request permission.":"Enter a place, then find and confirm the match.");
      const value=context(restored,false);
      if(restored&&pending.current.confirm(value))return;
      changed({...value,...(next==="manual"&&manual.trim()&&!restored?{manualStartingPlace:manual.trim()}:{} )});
    }
  }
  function editFirst(value=first,units=unit,flex=flexibility){
    preference.current.edit(value===""?null:{value:Number(value),unit:units,mode:flex,exclusive:false});
    setFirst(value);setUnit(units);setFlexibility(flex);changed(context());
  }
  function editBetween(value=amount,units=betweenUnit,flex=betweenMode){
    between.current.edit(value===""?null:{value:Number(value),unit:units,mode:flex,exclusive:false});
    setAmount(value);setBetweenUnit(units);setBetweenMode(flex);changed(context());
  }
  async function find(query=manual){
    if(!lookupEnabled&&!mock){setNotice("Starting-place lookup is disabled. Enable the documented local lookup switch, use current location, or choose Surprise Me.");cancel();return;}
    const current=++version.current;setSearching(true);setMatches([]);setNotice("Searching for starting place…");onStage?.("Searching for starting place");
    try{
      const found=mock?[{placeId:"Mock_origin_0",name:"Fictional Baltimore starting place",address:"Fictional reference, not an actual address",coordinates:{latitude:0,longitude:0},precision:"approximate_area" as const,attributions:[]}]:await lookup.current.get(query);
      if(current!==version.current)return;
      setMatches(found);setNotice(found.length?"Choose and confirm your starting place. The submitted outing will continue.":"No matches found. Your text is kept; add a city or choose another method.");
      if(found.length)onStage?.("Choose your starting place");else cancel();
    }catch(error){if(current===version.current){setNotice(error instanceof Error?error.message:"Starting-place search unavailable.");cancel();}}
    finally{if(current===version.current)setSearching(false);}
  }
  function confirm(match:StartingMatch){
    version.current++;setMatches([]);
    const point:Selection={point:{id:mock?match.placeId:"authorized-start",coordinates:match.coordinates},explicitly_authorized:true,
      source:mock?"mock":"manual",label:match.name,precision:match.precision};
    setSelected(point);saved.current.manual=point;setCredits(match.attributions);
    setNotice(mock?"Fictional mock starting reference confirmed. No actual location or route was verified.":"Starting point confirmed: "+match.name+". "+(match.precision==="address_or_place"?"Check the intended entrance.":"Travel estimates use this area's representative point."));
    const value=context(point,false);if(!pending.current.confirm(value))changed(value);
  }
  async function locate(){
    const current=++version.current;setNotice("Waiting for location permission…");
    try{
      const found=await requestStartingLocation(navigator.geolocation,window.isSecureContext);
      if(current!==version.current)return;
      const point:Selection={point:{id:"authorized-start",coordinates:found.coordinates},explicitly_authorized:true,source:"device",precision:"device",label:"Your permission-authorized device location",...(found.accuracyMeters!==undefined?{accuracy_m:found.accuracyMeters}:{})};
      setSelected(point);saved.current.current=point;
      setNotice("Starting location shared for this page only"+(found.accuracyMeters!==undefined?"; reported accuracy about "+Math.round(found.accuracyMeters)+" meters":"")+". Your destination stays separate.");
      if(!pending.current.confirm(context(point,false)))changed(context(point,false));
    }catch(error){if(current===version.current)setNotice(error instanceof Error?error.message:"Location unavailable. Enter a starting place or choose Surprise Me.");}
  }
  useImperativeHandle(ref,()=>({editTravel:()=>{if(disclosure.current){disclosure.current.open=true;disclosure.current.querySelector<HTMLInputElement>('input[type="number"]')?.focus();}},cancel:()=>{version.current++;originInput.current=undefined;setConflict(false);cancel();},prepare:async(input)=>{
    originInput.current=input;
    const incoming=preference.current.hydrate(input?.firstTravel);
    setFirst(incoming?String(incoming.value):"");setUnit(incoming?.unit??"minutes");setFlexibility(incoming?.mode??"strict");
    const extracted=input?.betweenTravel??(input?.maxLegTravel!=null?{value:input.maxLegTravel,unit:"minutes" as const,mode:"strict" as const,exclusive:input.maxLegTravelExclusive??false}:null);
    const onward=between.current.hydrate(extracted);
    setAmount(onward?String(onward.value):"");setBetweenUnit(onward?.unit??"minutes");setBetweenMode(onward?.mode??"strict");
    if(mode==="surprise"){
      const value=prepareSurprise();if(value)return value;
      if(disclosure.current)disclosure.current.open=true;return pending.current.wait();
    }
    if(selected)return context();
    if(disclosure.current)disclosure.current.open=true;
    let query=manual,nextMode=mode;
    const stated=input?.firstTravel?.originText;
    if(mode==="none"&&stated&&!/^my\b|^(?:me|the starting point)$/i.test(stated)){
      query=stated+", "+input?.location;setManual(query);setMode("manual");nextMode="manual";
    }
    if(nextMode==="manual"){
      if(query.trim().length<3){setNotice("Enter at least three characters for your starting place.");return null;}
      const answer=pending.current.wait();void find(query);return answer;
    }
    setNotice("Choose one of the three starting methods. Your submitted outing continues after selection or confirmation.");
    onStage?.("Choose how to start");return pending.current.wait();
  }}));
  return <details ref={disclosure} className="location-controls"><summary>Where should your outing start?</summary>
    <p>Your destination stays separate from your current or manual starting location. No location is requested on page load.</p>
    <fieldset><legend>Choose a starting method</legend>
      <label><input type="radio" name="starting-mode" checked={mode==="current"} onChange={()=>chooseMode("current")}/>Use my current location</label>
      <label><input type="radio" name="starting-mode" checked={mode==="manual"} onChange={()=>chooseMode("manual")}/>I&apos;ll choose where to start</label>
      <label><input type="radio" name="starting-mode" checked={mode==="surprise"} onChange={()=>chooseMode("surprise")}/>I&apos;m new to the city — Surprise me!</label>
    </fieldset>
    {mode==="surprise"&&<p>Discover unexpected places and let us plan your outing from the first activity.</p>}
    {mode==="current"&&<button type="button" className="secondary-button" onClick={locate}>Share my location</button>}
    <p role="status">{notice}</p>
    {conflict&&mode==="surprise"&&<div role="group" aria-label="First-stop constraint choice">
      <button type="button" onClick={()=>chooseMode("manual")}>Use a starting location instead</button>
      <button type="button" onClick={()=>{removed.current=firstKey();setConflict(false);const value=prepareSurprise();if(value&&!pending.current.confirm(value))changed(value);}}>Remove the first-stop constraint for Surprise Me</button>
    </div>}
    {selected&&mode!=="surprise"&&<><p>{selected.label}</p>{!mock&&<GoogleCredits credits={credits}/>}<button type="button" onClick={()=>{if(mode==="current"||mode==="manual")delete saved.current[mode];setSelected(null);changed(context(null,false));}}>Change starting point</button></>}
    {mode==="manual"&&<>
      <label>Starting place, address, neighborhood or ZIP code<input value={manual} maxLength={200} placeholder="e.g. hotel or Union Station, Washington DC" onChange={e=>{
        version.current++;setSearching(false);setMatches([]);setSelected(null);delete saved.current.manual;setManual(e.target.value);changed({...context(null,false),...(e.target.value.trim()?{manualStartingPlace:e.target.value.trim()}:{})});
        setNotice("Plan your outing to find this place, or select Find starting place. You will confirm the match.");
      }}/></label>
      <p>A neighborhood, city or ZIP code is an approximate representative point. Confirm the intended match.</p>
      <button type="button" className="secondary-button" disabled={searching||manual.trim().length<3} onClick={()=>void find()}>{searching?"Finding…":"Find starting place"}</button>
      {!!matches.length&&<ul className="starting-matches">{matches.map(match=><li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>{match.precision==="address_or_place"?"Address/place; confirm the intended entrance.":"Approximate area representative point."}</p><button type="button" onClick={()=>confirm(match)}>Use this starting place</button>{!mock&&<GoogleCredits credits={match.attributions}/>}</li>)}</ul>}
    </>}
    {mode==="surprise"?<div className="preferences-grid">
      <label>How far are you willing to travel between activities?<input type="number" min="0" max={betweenUnit==="miles"?200:1440} step={betweenUnit==="miles"?"0.1":"1"} value={amount} onChange={e=>editBetween(e.target.value)}/><small>Optional; no hard limit when blank.</small></label>
      <label>Between-activity unit<select value={betweenUnit} onChange={e=>editBetween(amount,e.target.value as FirstTravel["unit"])}><option value="minutes">Minutes</option><option value="miles">Miles</option></select></label>
      <label>Between-activity preference type<select value={betweenMode} onChange={e=>editBetween(amount,betweenUnit,e.target.value as FirstTravel["mode"])}><option value="strict">Strict maximum</option><option value="flexible">Flexible preference</option></select></label>
      {amount!==""&&betweenMode==="flexible"&&<p>Prefer {amount} {betweenUnit}; maximum {Number(amount)*2} {betweenUnit} per leg. Extra travel is labeled.</p>}
    </div>:<div className="preferences-grid">
      <label>First-stop travel preference (optional)<input type="number" min="0" max={unit==="miles"?200:1440} step={unit==="miles"?"0.1":"1"} value={first} onChange={e=>editFirst(e.target.value)}/></label>
      <label>First-stop unit<select value={unit} onChange={e=>editFirst(first,e.target.value as FirstTravel["unit"])}><option value="minutes">Minutes</option><option value="miles">Miles</option></select></label>
      <label>First-stop preference type<select value={flexibility} onChange={e=>editFirst(first,unit,e.target.value as FirstTravel["mode"])}><option value="strict">Strict maximum</option><option value="flexible">Flexible preference</option></select></label>
      {first!==""&&flexibility==="flexible"&&<p>Prefer {first} {unit}; maximum {Number(first)*2} {unit}. Extra first-stop travel is labeled.</p>}
    </div>}
  </details>;
}
