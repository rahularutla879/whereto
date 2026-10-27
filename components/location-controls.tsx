"use client";
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { StartingConfirmation } from "../lib/starting-confirmation";
import { requestStartingLocation } from "../lib/location";
import { StartingPlaceSession, type StartingMatch } from "../lib/starting-places";
import { StartingAreaSession, type FirstTravel, type OriginPreparation, type StartingSuggestion } from "../lib/starting-areas";
import { GoogleCredits } from "./venue-details";
import type { LocationContext } from "../lib/planning-client";
export type StartingLocationHandle = { cancel: () => void; prepare: (input?: OriginPreparation) => Promise<LocationContext | null> };
type Mode = "none" | "current" | "manual" | "suggested";
type Selection = { coordinates: {latitude:number;longitude:number}; precision: NonNullable<LocationContext["startingLocation"]>["precision"]; source: "device"|"manual"|"suggested"; label:string; id:string; accuracy_m?:number; referenceToken?:string };
export function LocationControls({ onChange, onStage, lookupEnabled = false, ref }: { onChange: (value: LocationContext) => void; onStage?: (stage: string) => void; lookupEnabled?: boolean; ref?: Ref<StartingLocationHandle> }) {
  const disclosure=useRef<HTMLDetailsElement>(null), pending=useRef(new StartingConfirmation());
  const lookupSession=useRef(new StartingPlaceSession()), suggestionSession=useRef(new StartingAreaSession());
  const version=useRef(0);
  const [credits,setCredits]=useState<StartingMatch["attributions"]>([]);
  const [mode,setMode]=useState<Mode>("none"), [selected,setSelected]=useState<Selection|null>(null);
  const [manual,setManual]=useState(""), [notice,setNotice]=useState(""), [searching,setSearching]=useState(false);
  const [matches,setMatches]=useState<StartingMatch[]>([]), [suggestions,setSuggestions]=useState<StartingSuggestion[]>([]);
  const [referenceToken,setReferenceToken]=useState<string|undefined>(undefined);
  const [first,setFirst]=useState(""), [unit,setUnit]=useState<FirstTravel["unit"]>("minutes"), [flexibility,setFlexibility]=useState<FirstTravel["mode"]>("strict");
  const [radius,setRadius]=useState(""); const limits=useRef({first:"",radius:""});
  const cancel=()=>pending.current.cancel();
  useEffect(()=>()=>{version.current++;pending.current.cancel();lookupSession.current.clear();suggestionSession.current.clear();},[]);
  function context(point:Selection|null=selected, value=first, units=unit, flex=flexibility, searchRadius=radius):LocationContext {
    return {locationFirst:true,
      ...(point?{startingLocation:{point:{id:point.id,coordinates:point.coordinates},explicitly_authorized:true,precision:point.precision,source:point.source,label:point.label,...(point.accuracy_m!==undefined?{accuracy_m:point.accuracy_m}:{})},currentArea:{coordinates:point.coordinates},...(point.referenceToken?{referenceToken:point.referenceToken}:{})}:{}),
      ...(value!==""?{firstTravel:{value:Number(value),unit:units,mode:flex,exclusive:false}}:{}),
      ...(searchRadius!==""?{searchRadius:Number(searchRadius)}:{})};
  }
  function chooseMode(next:Mode) {
    cancel();version.current++;setCredits([]);suggestionSession.current.clear();setMode(next);setSelected(null);setMatches([]);setSuggestions([]);setSearching(false);setReferenceToken(undefined);
    setNotice(next==="suggested"?"Plan your outing to compare verified public planning references. You will review and confirm the suggestion.":next==="current"?"Select Use my current location to request permission.":"");
    onChange({...context(null),...(next==="manual"&&manual.trim()?{manualStartingPlace:manual.trim()}:{} )});
  }
  function preferencePoint() {
    if(selected?.source!=="suggested")return selected;
    version.current++;setSelected(null);setCredits([]);suggestionSession.current.clear();
    setNotice("Travel preference changed. Plan your outing to compare and confirm a starting area again.");
    return null;
  }
  async function find(query=manual) {
    if (!lookupEnabled){setNotice("Starting-place lookup is disabled. Enable the documented local lookup switch, use current location, or clear this field before planning.");cancel();return;}
    const current=++version.current;setSearching(true);setMatches([]);setSuggestions([]);setNotice("Searching for starting place…");onStage?.("Searching for starting place");
    try {
      const found=await lookupSession.current.get(query);
      if(current!==version.current)return;
      setMatches(found);setNotice(found.length?"Choose your starting place. Your destination stays separate; a submitted outing will continue after confirmation.":"No matches found. Keep your text and add a city or address, or choose another starting option.");
      if(found.length)onStage?.("Choose your starting place");else cancel();
    } catch(error){if(current===version.current){setNotice(error instanceof Error?error.message:"Starting-place search unavailable.");cancel();}}
    finally{if(current===version.current)setSearching(false);}
  }
  async function suggest(input:OriginPreparation) {
    if(!lookupEnabled){setNotice("Starting-area suggestions are disabled. Enable the local starting-location lookup switch, use current location, or plan without a starting point.");cancel();return;}
    const current=++version.current;setSearching(true);setSuggestions([]);setNotice("Comparing public starting areas…");onStage?.("Finding a starting area");
    try {
      const found=await suggestionSession.current.get(input);
      if(current!==version.current)return;
      setSuggestions(found.matches);setReferenceToken(found.referenceToken);
      setNotice(found.matches.length?"Review a verified planning reference below. This is not your actual position.":"No trustworthy starting area was found. Enter and confirm a manual starting place instead.");
      if(found.matches.length)onStage?.("Choose a starting area");else cancel();
    }catch(error){if(current===version.current){setNotice(error instanceof Error?error.message:"Starting-area suggestions unavailable.");cancel();}}
    finally{if(current===version.current)setSearching(false);}
  }
  useImperativeHandle(ref,()=>({cancel,prepare:async(input)=>{
    const effective=input?{...input,...(first!==""&&input.firstTravel?.mode!=="strict"?{firstTravel:{value:Number(first),unit,mode:flexibility,exclusive:false} as FirstTravel}:{})}:undefined;
    if(selected)return context();
    let query=manual;
    let nextMode=mode;
    const stated=input?.firstTravel?.originText;
    if(mode==="none"&&stated&&!/^my\b|^(?:me|the starting point)$/i.test(stated)){
      query=stated.toLowerCase().includes(input!.location.toLowerCase())?stated:`${stated}, ${input!.location}`;
      setManual(query);setMode("manual");nextMode="manual";
    }
    if(nextMode==="none"&&!input?.firstTravel&&first==="")return context(null);
    if(disclosure.current)disclosure.current.open=true;
    if(nextMode==="none"||nextMode==="current"){
      setNotice("Choose current location, enter and confirm a place, or choose a starting area for me. No point was invented.");return null;
    }
    if(nextMode==="manual"&&query.trim().length<3){setNotice("Enter at least three characters for your starting place.");return null;}
    if(!lookupEnabled){setNotice("Starting-place lookup is disabled. Enable the documented local lookup switch, use current location, or clear this field before planning.");return null;}
    cancel();const answer=pending.current.wait();
    if(nextMode==="suggested"&&effective)void suggest(effective);else void find(query);
    return answer;
  }}));
  function confirm(match:StartingMatch,suggested=false) {
    version.current++;setMatches([]);setSuggestions([]);
    const point:Selection={coordinates:match.coordinates,precision:match.precision,source:suggested?"suggested":"manual",label:match.name,
      id:suggested?'reference_'+match.placeId:'authorized-start',...(suggested?{referenceToken}: {})};
    setCredits(match.attributions);setSelected(point);setNotice(suggested?`Starting near ${match.name}. Chosen as a planning reference, not your actual position. You can change it.`:`Starting point confirmed: ${match.name}. ${match.precision==="address_or_place"?"Check the intended entrance.":"Travel estimates use this area's representative point."}`);
    const value=context(point);if(!pending.current.confirm(value))onChange(value);
  }
  async function locate() {
    cancel();const current=++version.current;setMode("current");setSelected(null);setMatches([]);setSuggestions([]);setSearching(false);onChange(context(null));setNotice("Waiting for location permission…");
    try {
      const found=await requestStartingLocation(navigator.geolocation,window.isSecureContext,()=>limits.current);
      if(current!==version.current)return;
      const point:Selection={coordinates:found.coordinates,precision:"device",source:"device",label:"Your permission-authorized device location",id:"authorized-start",...(found.accuracyMeters!==undefined?{accuracy_m:found.accuracyMeters}:{})};
      setSelected(point);onChange(context(point,found.first,unit,flexibility,found.radius));
      setNotice(`Starting location shared for this page only${found.accuracyMeters!==undefined?`; reported accuracy about ${Math.round(found.accuracyMeters)} meters`:""}. Device coordinates do not establish your city. For a trip elsewhere, choose a manual place there or a suggested starting area.`);
    }catch(error){if(current===version.current)setNotice(error instanceof Error?error.message:"Location unavailable. Choose a manual or suggested starting area.");}
  }
  return <details ref={disclosure} className="location-controls"><summary>Optional starting location</summary>
    <p>Your starting point and destination are separate. For another city, enter a place there or let us suggest an area. No location is requested on page load.</p>
    <fieldset><legend>Where should this outing start?</legend>
      <label><input type="radio" name="starting-mode" checked={mode==="current"} onChange={()=>chooseMode("current")} />Use my current location</label>
      <label><input type="radio" name="starting-mode" checked={mode==="manual"} onChange={()=>chooseMode("manual")} />Enter my starting location</label>
      <label><input type="radio" name="starting-mode" checked={mode==="suggested"} onChange={()=>chooseMode("suggested")} />Choose a starting area for me</label>
    </fieldset>
    <button type="button" className="secondary-button" onClick={locate}>Use my current location</button>
    {mode!=="none"&&<button type="button" onClick={()=>chooseMode("none")}>Plan without a starting point</button>}
    <p role="status">{notice}</p>
    {selected&&<GoogleCredits credits={credits}/>}
    {selected&&<button type="button" className="secondary-button" onClick={()=>chooseMode(selected.source==="suggested"?"suggested":"manual")}>Change starting area</button>}
    <label>Starting place, address, neighborhood or ZIP code<input maxLength={200} value={manual} placeholder="e.g. hotel or Union Station, Washington DC" aria-describedby="manual-start-help" onChange={e=>{
      cancel();version.current++;setSearching(false);setMatches([]);setSuggestions([]);setSelected(null);setMode("manual");setManual(e.target.value);
      onChange({...context(null),...(e.target.value.trim()?{manualStartingPlace:e.target.value.trim()}:{})});
      setNotice(e.target.value.trim()?"Plan your outing to find this starting place, or select Find starting place. You will confirm the match.":"Starting place cleared.");
    }} /></label>
    <p id="manual-start-help">A neighborhood, city or ZIP code is an approximate representative point. Confirm the match before using its travel estimates.</p>
    <button type="button" className="secondary-button" disabled={searching||manual.trim().length<3} onClick={()=>{setMode("manual");void find();}}>{searching?"Finding…":"Find starting place"}</button>
    {matches.length>0&&<ul className="starting-matches">{matches.map(match=><li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>{match.precision==="address_or_place"?"Address/place location; confirm the intended entrance.":"Approximate area: travel limits apply from this representative point."}</p><button type="button" className="secondary-button" onClick={()=>confirm(match)}>{match.precision==="address_or_place"?"Use this starting place":"Use this representative point"}</button><GoogleCredits credits={match.attributions}/></li>)}</ul>}
    {suggestions.length>0&&<ul className="starting-matches">{suggestions.map(match=><li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>Suggested planning reference, not your actual position. {match.reason}</p><button type="button" className="secondary-button" onClick={()=>confirm(match,true)}>Use this starting area</button><GoogleCredits credits={match.attributions}/></li>)}</ul>}
    <div className="preferences-grid">
      <label>First-stop travel preference (optional)<input type="number" min="0" max={unit==="miles"?200:1440} step={unit==="miles"?"0.1":"1"} value={first} onChange={e=>{cancel();limits.current.first=e.target.value;setFirst(e.target.value);onChange(context(preferencePoint(),e.target.value));}} /></label>
      <label>First-stop unit<select value={unit} onChange={e=>{cancel();const next=e.target.value as typeof unit;setUnit(next);onChange(context(preferencePoint(),first,next));}}><option value="minutes">Minutes</option><option value="miles">Miles</option></select></label>
      <label>First-stop preference type<select value={flexibility} onChange={e=>{cancel();const next=e.target.value as typeof flexibility;setFlexibility(next);onChange(context(preferencePoint(),first,unit,next));}}><option value="strict">Strict maximum</option><option value="flexible">Flexible preference</option></select></label>
      <label>Search radius near me (meters)<input type="number" min="1" max="50000" value={radius} onChange={e=>{cancel();limits.current.radius=e.target.value;setRadius(e.target.value);onChange({...context(),...(e.target.value!==""?{searchRadius:Number(e.target.value)}:{searchRadius:undefined})});}} /><small>Only for an explicit coordinate-based “near me” search; independent of road-distance limits.</small></label>
    </div>
  </details>;
}
