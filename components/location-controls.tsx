"use client";
import { useEffect, useRef, useState } from "react";
import { requestStartingLocation } from "../lib/location";
import { StartingPlaceSession, type StartingMatch } from "../lib/starting-places";
import { GoogleCredits } from "./venue-details";
import type { LocationContext } from "../lib/planning-client";
export function LocationControls({ onChange }: { onChange: (value: LocationContext) => void }) {
  const lookupSession = useRef(new StartingPlaceSession());
  const version = useRef(0);
  useEffect(() => () => { version.current++; lookupSession.current.clear(); }, []);
  const [matches, setMatches] = useState<StartingMatch[]>([]);
  const [searching, setSearching] = useState(false);
  const [precision, setPrecision] = useState<StartingMatch["precision"] | "device">("device");
  const [point, setPoint] = useState<{ latitude: number; longitude: number } | null>(null);
  const [notice, setNotice] = useState("");
  const limits = useRef({ first: "", radius: "" });
  const [first, setFirst] = useState("");
  const [radius, setRadius] = useState("");
  const [manual, setManual] = useState("");
  const publish = (coordinates: typeof point, limit = first, search = radius, place = manual) => onChange({
    ...(coordinates ? { startingLocation: { point: { id: "authorized-start", coordinates }, explicitly_authorized: true, precision }, currentArea: { coordinates } } : {}),
    ...(!coordinates && place.trim() ? { manualStartingPlace: place.trim() } : {}),
    ...(limit !== "" ? { maxFirstLegTravel: Number(limit) } : {}), ...(search !== "" ? { searchRadius: Number(search) } : {}),
  });
  async function lookup() {
    const current = ++version.current;
    setSearching(true); setMatches([]); setNotice("Finding starting places…");
    try {
      const found = await lookupSession.current.get(manual);
      if (current !== version.current) return;
      setMatches(found); setNotice(found.length ? "Select the intended starting point below. Your destination stays separate." : "No matches in this search. Add a city/state or use current location.");
    } catch (error) { if (current === version.current) setNotice(error instanceof Error ? error.message : "Starting-place search unavailable."); }
    finally { if (current === version.current) setSearching(false); }
  }
  async function locate() {
    const current = ++version.current;
    setSearching(false); setMatches([]);
    setNotice("Waiting for location permission…");
    try {
      const { coordinates, first: latestFirst, radius: latestRadius } = await requestStartingLocation(navigator.geolocation, window.isSecureContext, () => limits.current);
      if (current !== version.current) return;
      setPoint(coordinates); setPrecision("device"); setManual(""); lookupSession.current.clear();
      onChange({ startingLocation: { point: { id: "authorized-start", coordinates }, explicitly_authorized: true, precision: "device" }, currentArea: { coordinates }, ...(latestFirst !== "" ? { maxFirstLegTravel: Number(latestFirst) } : {}), ...(latestRadius !== "" ? { searchRadius: Number(latestRadius) } : {}) });
      setNotice("Starting location shared for this page only. An explicit destination still takes priority.");
    } catch (error) { if (current === version.current) setNotice(error instanceof Error ? error.message : "Location unavailable. Enter a starting place below."); }
  }
  return <details className="location-controls"><summary>Optional starting location</summary>
    <p>Your destination and starting point are separate. Location is requested only when you select the button.</p>
    <button type="button" className="secondary-button" onClick={locate}>Use my current location</button>
    {(point || manual) && <button type="button" onClick={() => { version.current++; lookupSession.current.clear(); setSearching(false); setMatches([]); setPoint(null); setManual(""); publish(null, first, radius, ""); setNotice("Starting location removed."); }}>Remove starting location</button>}
    <p role="status">{notice}</p>
    <label>Starting place, address, neighborhood or ZIP code<input maxLength={200} value={manual} placeholder="e.g. Inner Harbor, Baltimore" aria-describedby="manual-start-help" onChange={e => {
      version.current++; setSearching(false); setMatches([]); setManual(e.target.value); setPoint(null); publish(null, first, radius, e.target.value);
      setNotice(e.target.value.trim() ? "Select Find starting place, then confirm a match before planning." : "Starting place cleared.");
    }} /></label>
    <p id="manual-start-help">A neighborhood, city or ZIP code represents an approximate area, not your exact position. Confirm a match before it is used for travel estimates.</p>
    <button type="button" className="secondary-button" disabled={searching || manual.trim().length < 3} onClick={lookup}>{searching ? "Finding…" : "Find starting place"}</button>
    {matches.length > 0 && <ul className="starting-matches">{matches.map(match => <li key={match.placeId}><strong>{match.name}</strong><p>{match.address}</p><p>{match.precision === "address_or_place" ? "Address/place location; confirm the intended entrance." : "Approximate area: travel limits will apply from this representative point, not your actual address."}</p><button type="button" className="secondary-button" onClick={() => {
      version.current++; setMatches([]); setPoint(match.coordinates); setPrecision(match.precision); setNotice(`Starting point confirmed: ${match.name}. ${match.precision === "address_or_place" ? "Check the intended entrance." : "Travel estimates use this area's representative point."}`);
      onChange({ startingLocation: { point: { id: "authorized-start", coordinates: match.coordinates }, explicitly_authorized: true, precision: match.precision }, currentArea: { coordinates: match.coordinates }, ...(first !== "" ? { maxFirstLegTravel: Number(first) } : {}), ...(radius !== "" ? { searchRadius: Number(radius) } : {}) });
    }}>{match.precision === "address_or_place" ? "Use this starting place" : "Use this representative point"}</button><GoogleCredits credits={match.attributions} /></li>)}</ul>}
    <div className="preferences-grid">
      <label>Maximum travel to first stop (minutes)<input type="number" min="0" max="1440" step="1" value={first} onChange={e => { limits.current.first = e.target.value; setFirst(e.target.value); publish(point, e.target.value); }} /></label>
      <label>Search radius near me (meters)<input type="number" min="1" max="50000" value={radius} onChange={e => { limits.current.radius = e.target.value; setRadius(e.target.value); publish(point, first, e.target.value); }} /><small>Only for a coordinate-based “near me” search.</small></label>
    </div>
  </details>;
}
