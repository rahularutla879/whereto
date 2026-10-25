"use client";
import { useState } from "react";
import { requestLocation } from "../lib/location";
import type { LocationContext } from "../lib/planning-client";
export function LocationControls({ onChange }: { onChange: (value: LocationContext) => void }) {
  const [point, setPoint] = useState<{ latitude: number; longitude: number } | null>(null);
  const [notice, setNotice] = useState("");
  const [first, setFirst] = useState("");
  const [radius, setRadius] = useState("");
  const [manual, setManual] = useState("");
  const publish = (coordinates: typeof point, limit = first, search = radius, place = manual) => onChange({
    ...(coordinates ? { startingLocation: { point: { id: "authorized-start", coordinates }, explicitly_authorized: true }, currentArea: { coordinates } } : {}),
    ...(!coordinates && place.trim() ? { manualStartingPlace: place.trim() } : {}),
    ...(limit !== "" ? { maxFirstLegTravel: Number(limit) } : {}), ...(search !== "" ? { searchRadius: Number(search) } : {}),
  });
  async function locate() {
    setNotice("Waiting for location permission…");
    try {
      const coordinates = await requestLocation(navigator.geolocation, window.isSecureContext);
      setPoint(coordinates); setManual(""); publish(coordinates);
      setNotice("Starting location shared for this page only. An explicit destination still takes priority.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Location unavailable. Enter a city/neighborhood in Set preferences."); }
  }
  return <details className="location-controls"><summary>Optional starting location</summary>
    <p>Your destination and starting point are separate. Location is requested only when you select the button.</p>
    <button type="button" className="secondary-button" onClick={locate}>Use my current location</button>
    {(point || manual) && <button type="button" onClick={() => { setPoint(null); setManual(""); publish(null, first, radius, ""); setNotice("Starting location removed."); }}>Remove starting location</button>}
    <p role="status">{notice}</p>
    <label>Starting place, address, neighborhood or ZIP code<input maxLength={200} value={manual} placeholder="e.g. Inner Harbor, Baltimore" aria-describedby="manual-start-help" onChange={e => {
      setManual(e.target.value); setPoint(null); publish(null, first, radius, e.target.value);
      setNotice(e.target.value.trim() ? "Manual starting-place lookup is not enabled yet. Use current location, or clear this field to plan without first-stop travel." : "Starting place cleared.");
    }} /></label>
    <p id="manual-start-help">Address lookup is not enabled yet. A neighborhood or ZIP code represents an approximate area, not your exact position. For destination-only searches, enter a city/neighborhood in Set preferences.</p>
    <div className="preferences-grid">
      <label>Maximum travel to first stop (minutes)<input type="number" min="0" max="1440" step="1" value={first} onChange={e => { setFirst(e.target.value); publish(point, e.target.value); }} /></label>
      <label>Search radius near me (meters)<input type="number" min="1" max="50000" value={radius} onChange={e => { setRadius(e.target.value); publish(point, first, e.target.value); }} /><small>Only for a coordinate-based “near me” search.</small></label>
    </div>
  </details>;
}
