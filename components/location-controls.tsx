"use client";
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { StartingConfirmation } from "../lib/starting-confirmation";
import { requestStartingLocation } from "../lib/location";
import { StartingPlaceSession, type StartingMatch } from "../lib/starting-places";
import { StartingAreaSession, type FirstTravel, type OriginPreparation, type StartingSuggestion } from "../lib/starting-areas";
import { FirstPreference } from "../lib/first-preference";
import { GoogleCredits } from "./venue-details";
import type { LocationContext } from "../lib/planning-client";
export type StartingLocationHandle = { cancel: () => void; prepare: (input?: OriginPreparation) => Promise<LocationContext | null> };
type Mode = "none" | "current" | "manual" | "suggested";
type Selection = { coordinates: {latitude:number;longitude:number}; precision: NonNullable<LocationContext["startingLocation"]>["precision"]; source: "device"|"manual"|"suggested"|"mock"; label:string; id:string; accuracy_m?:number; referenceToken?:string; requestKey?:string };
export function LocationControls({ onChange, onStage, lookupEnabled = false, mock = false, ref }: { onChange: (value: LocationContext, preparing?:boolean) => void; onStage?: (stage: string) => void; lookupEnabled?: boolean; mock?: boolean; ref?: Ref<StartingLocationHandle> }) {
  const disclosure=useRef<HTMLDetailsElement>(null), pending=useRef(new StartingConfirmation());
  const lookupSession=useRef(new StartingPlaceSession()), suggestionSession=useRef(new StartingAreaSession());
  const version=useRef(0);
  const [credits,setCredits]=useState<StartingMatch["attributions"]>([]);
  const [mode,setMode]=useState<Mode>("none"), [selected,setSelected]=useState<Selection|null>(null);
  const [manual,setManual]=useState(""), [notice,setNotice]=useState(""), [searching,setSearching]=useState(false);
  const [matches,setMatches]=useState<StartingMatch[]>([]), [suggestions,setSuggestions]=useState<StartingSuggestion[]>([]);
  const [referenceToken,setReferenceToken]=useState<string|undefined>(undefined);
  const [first,setFirst]=useState(""), [unit,setUnit]=useState<FirstTravel["unit"]>("minutes"), [flexibility,setFlexibility]=useState<FirstTravel["mode"]>("strict");
  const preference=useRef(new FirstPreference());
  const originInput=useRef<OriginPreparation|undefined>(undefined);
  const cancel=()=>pending.current.cancel();
  const changed=(value:LocationContext)=>onChange(value,pending.current.waiting);
  useEffect(()=>()=>{version.current++;pending.current.cancel();lookupSession.current.clear();suggestionSession.current.clear();},[]);
  function requestKey(input:OriginPreparation) { return JSON.stringify([input.location,input.activities,input.transport??"driving",input.geography??{strictDestination:false,excludedRegions:[]},input.maxLegTravel??null,input.maxLegTravelExclusive??false,input.travel??null,input.travelExclusive??false,preference.current.value]); }
  function context(point:Selection|null=selected):LocationContext {
    return {locationFirst:true,
      ...(point?{startingLocation:{point:{id:point.id,coordinates:point.coordinates},explicitly_authorized:true,precision:point.precision,source:point.source,label:point.label,...(point.accuracy_m!==undefined?{accuracy_m:point.accuracy_m}:{})},currentArea:{coordinates:point.coordinates},...(point.referenceToken?{referenceToken:point.referenceToken}:{})}:{}),
      firstTravel:preference.current.value};
  }
  function editTravel(value=first,units=unit,flex=flexibility) {
    version.current++;setSearching(false);setSuggestions([]);preference.current.edit(value===""?null:{value:Number(value),unit:units,mode:flex,exclusive:false});
    setFirst(value);setUnit(units);setFlexibility(flex);
    changed(context(preferencePoint()));
  }
  function mockMatches():StartingMatch[] {
    return [0,1,2].map(i=>({placeId:`Mock_origin_${i}`,name:`Fictional Baltimore starting area ${i+1}`,address:"Fictional planning reference — not an actual address",coordinates:{latitude:0,longitude:i*.001},precision:"approximate_area",attributions:[]}));
  }
  function chooseMode(next:Mode) {
    version.current++;setCredits([]);setMode(next);setSelected(null);setMatches([]);setSuggestions([]);setSearching(false);setReferenceToken(undefined);
    if(next==="suggested"&&pending.current.waiting&&originInput.current)void suggest({...originInput.current,firstTravel:preference.current.value});
    setNotice(next==="suggested"?(mock?"Review and confirm a clearly fictional starting reference for mock planning.":"Plan your outing to compare verified public planning references. You will review and confirm the suggestion."):next==="current"?"Select Share my location to request permission.":"");
    changed({...context(null),...(next==="manual"&&manual.trim()?{manualStartingPlace:manual.trim()}:{} )});
  }
  function preferencePoint() {
    if(selected?.source!=="suggested")return selected;
    version.current++;setSelected(null);setCredits([]);suggestionSession.current.clear();
    setNotice("Travel preference changed. Plan your outing to compare and confirm a starting area again.");
    return null;
  }
  async function find(query=manual) {
    if (!lookupEnabled && !mock){setNotice("Starting-place lookup is disabled. Enable the documented local lookup switch, use current location, or choose a supported starting method.");cancel();return;}
    const current=++version.current;setSearching(true);setMatches([]);setSuggestions([]);setNotice("Searching for starting place…");onStage?.("Searching for starting place");
    try {
      const found=mock?mockMatches():await lookupSession.current.get(query);
      if(current!==version.current)return;
      setMatches(found);setNotice(found.length?"Choose your starting place. Your destination stays separate; a submitted outing will continue after confirmation.":"No matches found. Keep your text and add a city or address, or choose another starting option.");
      if(found.length)onStage?.("Choose your starting place");else cancel();
    } catch(error){if(current===version.current){setNotice(error instanceof Error?error.message:"Starting-place search unavailable.");cancel();}}
    finally{if(current===version.current)setSearching(false);}
  }
  async function suggest(input:OriginPreparation) {
    if(!lookupEnabled && !mock){setNotice("Starting-area suggestions are disabled. Enable the local starting-location lookup switch, use current location, or enter a manual place.");cancel();return;}
    const current=++version.current;setSearching(true);setSuggestions([]);setNotice("Comparing public starting areas…");onStage?.("Finding a starting area");
    try {
      const found=mock?{matches:mockMatches().map(p=>({...p,reason:"Fictional mock reference for simulated Baltimore outings.",score:0})),referenceToken:undefined}:await suggestionSession.current.get(input);
      if(current!==version.current)return;
      setSuggestions(found.matches);setReferenceToken(found.referenceToken);
      setNotice(found.matches.length?(mock?"Review a fictional mock reference. No real location has been verified.":"Review a verified planning reference below. This is not your actual position."):"No trustworthy starting area was found. Enter and confirm a manual starting place instead.");
      if(found.matches.length)onStage?.("Choose a starting area");else cancel();
    }catch(error){if(current===version.current){setNotice(error instanceof Error?error.message:"Starting-area suggestions unavailable.");cancel();}}
    finally{if(current===version.current)setSearching(false);}
  }
  useImperativeHandle(ref,()=>({cancel:()=>{version.current++;originInput.current=undefined;cancel();},prepare:async(input)=>{
    if(input) {
      originInput.current=input;
      const incoming=preference.current.hydrate(input.firstTravel);
      setFirst(incoming?String(incoming.value):"");setUnit(incoming?.unit??"minutes");setFlexibility(incoming?.mode??"strict");
    }
    const effective=input?{...input,firstTravel:preference.current.value}:undefined;
    if(selected&&(selected.source!=="suggested"||!effective||selected.requestKey===requestKey(effective)))return context();
    if(selected?.source==="suggested"){setSelected(null);suggestionSession.current.clear();}
    let query=manual;
    let nextMode=mode;
    const stated=input?.firstTravel?.originText;
    if(mode==="none"&&stated&&!/^my\b|^(?:me|the starting point)$/i.test(stated)){
      query=stated.toLowerCase().includes(input!.location.toLowerCase())?stated:`${stated}, ${input!.location}`;
      setManual(query);setMode("manual");nextMode="manual";
    }
    if(disclosure.current)disclosure.current.open=true;
    if(nextMode==="none"||nextMode==="current"){
      setNotice("Choose one of the three starting methods below. Your submitted outing will continue after confirmation.");onStage?.("Choose a starting point");
      cancel();return pending.current.wait();
    }
    if(nextMode==="manual"&&query.trim().length<3){setNotice("Enter at least three characters for your starting place.");return null;}
    if(!lookupEnabled && !mock){setNotice("Starting-place lookup is disabled. Enable the documented local lookup switch, use current location, or choose a supported starting method.");return null;}
    cancel();const answer=pending.current.wait();
    if(nextMode==="suggested"&&effective)void suggest(effective);else void find(query);
    return answer;
  }}));
  function confirm(match:StartingMatch,suggested=false) {
    version.current++;setMatches([]);setSuggestions([]);
    const point:Selection={coordinates:match.coordinates,precision:match.precision,source:mock?"mock":suggested?"suggested":"manual",label:match.name,
      id:mock?match.placeId:suggested?'reference_'+match.placeId:'authorized-start',...(suggested&&!mock?{referenceToken,requestKey:originInput.current?requestKey(originInput.current):undefined}: {})};
    setCredits(match.attributions);setSelected(point);setNotice(mock?`Fictional mock starting reference confirmed: ${match.name}. No actual location or route was verified.`:suggested?`Starting near ${match.name}. Chosen as a planning reference, not your actual position. You can change it.`:`Starting point confirmed: ${match.name}. ${match.precision==="address_or_place"?"Check the intended entrance.":"Travel estimates use this area's representative point."}`);
    const value=context(point);if(!pending.current.confirm(value))changed(value);
  }
  async function locate() {
    const current=++version.current;setMode("current");setSelected(null);setMatches([]);setSuggestions([]);setSearching(false);changed(context(null));setNotice("Waiting for location permission…");
    try {
      const found=await requestStartingLocation(navigator.geolocation,window.isSecureContext);
      if(current!==version.current)return;
      const point:Selection={coordinates:found.coordinates,precision:"device",source:"device",label:"Your permission-authorized device location",id:"authorized-start",...(found.accuracyMeters!==undefined?{accuracy_m:found.accuracyMeters}:{})};
      setSelected(point);if(!pending.current.confirm(context(point)))changed(context(point));
      setNotice(`Starting location shared for this page only${found.accuracyMeters!==undefined?`; reported accuracy about ${Math.round(found.accuracyMeters)} meters`:""}. Device coordinates do not establish your city. For a trip elsewhere, choose a manual place there or a suggested starting area.`);
    }catch(error){if(current===version.current)setNotice(error instanceof Error?error.message:"Location unavailable. Choose a manual or suggested starting area.");}
  }
  return <details ref={disclosure} className="location-controls"><summary>Where should your outing start?</summary>
    <p>Your starting point and destination are separate. For another city, enter a place there or let us suggest an area. No location is requested on page load.</p>
    <fieldset><legend>Choose a starting method</legend>
      <label><input type="radio" name="starting-mode" checked={mode==="current"} onChange={()=>chooseMode("current")} />Use my current location</label>
      <label><input type="radio" name="starting-mode" checked={mode==="manual"} onChange={()=>chooseMode("manual")} />Enter my starting location</label>
      <label><input type="radio" name="starting-mode" checked={mode==="suggested"} onChange={()=>chooseMode("suggested")} />Choose a starting area for me</label>
    </fieldset>
    {mode==="current"&&<button type="button" className="secondary-button" onClick={locate}>Share my location</button>}
    <p role="status">{notice}</p>
    {selected&&!mock&&<GoogleCredits credits={credits}/>}
    {selected&&<button type="button" className="secondary-button" onClick={()=>chooseMode(selected.source==="suggested"?"suggested":"manual")}>Change starting area</button>}
    {mode==="manual"&&<>
    <label>Starting place, address, neighborhood or ZIP code<input maxLength={200} value={manual} placeholder="e.g. hotel or Union Station, Washington DC" aria-describedby="manual-start-help" onChange={e=>{
      version.current++;setSearching(false);setMatches([]);setSuggestions([]);setSelected(null);setMode("manual");setManual(e.target.value);
      changed({...context(null),...(e.target.value.trim()?{manualStartingPlace:e.target.value.trim()}:{})});
      setNotice(e.target.value.trim()?"Plan your outing to find this starting place, or select Find starting place. You will confirm the match.":"Starting place cleared.");
    }} /></label>
    <p id="manual-start-help">A neighborhood, city or ZIP code is an approximate representative point. Confirm the match before using its travel estimates.</p>
    <button type="button" className="secondary-button" disabled={searching||manual.trim().length<3} onClick={()=>{setMode("manual");void find();}}>{searching?"Finding…":"Find starting place"}</button>
    {matches.length>0&&<ul className="starting-matches">{matches.map(match=><li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>{match.precision==="address_or_place"?"Address/place location; confirm the intended entrance.":"Approximate area: travel limits apply from this representative point."}</p><button type="button" className="secondary-button" onClick={()=>confirm(match)}>{match.precision==="address_or_place"?"Use this starting place":"Use this representative point"}</button>{!mock&&<GoogleCredits credits={match.attributions}/>}</li>)}</ul>}
    </>}
    {suggestions.length>0&&<ul className="starting-matches">{suggestions.map(match=><li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>Suggested planning reference, not your actual position. {match.reason}</p><button type="button" className="secondary-button" onClick={()=>confirm(match,true)}>Use this starting area</button>{!mock&&<GoogleCredits credits={match.attributions}/>}</li>)}</ul>}
    <div className="preferences-grid">
      <label>First-stop travel preference (optional)<input type="number" min="0" max={unit==="miles"?200:1440} step={unit==="miles"?"0.1":"1"} value={first} onChange={e=>{editTravel(e.target.value);}} /></label>
      <label>First-stop unit<select value={unit} onChange={e=>{const next=e.target.value as typeof unit;setUnit(next);editTravel(first,next);}}><option value="minutes">Minutes</option><option value="miles">Miles</option></select></label>
      <label>First-stop preference type<select value={flexibility} onChange={e=>{const next=e.target.value as typeof flexibility;setFlexibility(next);editTravel(first,unit,next);}}><option value="strict">Strict maximum</option><option value="flexible">Flexible preference</option></select></label>

    </div>
    {first!==""&&flexibility==="flexible"&&<p>Prefer {first} {unit}; maximum {Number(first)*2} {unit}. Extra first-stop travel is labeled.</p>}
    {mode==="suggested"&&!selected&&<button type="button" className="secondary-button" disabled={searching} onClick={()=>{const input=originInput.current;if(input)void suggest({...input,firstTravel:preference.current.value});else setNotice("Describe your outing and select Plan my outing to compare starting areas.");}}>Find starting areas</button>}
  </details>;
}
