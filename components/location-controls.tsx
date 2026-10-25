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
  const publish = (coordinates: typeof point, limit = first, search = radius) => onChange({
    ...(coordinates ? { startingLocation: { point: { id: "authorized-start", coordinates }, explicitly_authorized: true }, currentArea: { coordinates } } : {}),
    ...(limit !== "" ? { maxFirstLegTravel: Number(limit) } : {}), ...(search !== "" ? { searchRadius: Number(search) } : {}),
  });
  async function locate() {
    setNotice("Waiting for location permission…");
    try {
      const coordinates = await requestLocation(navigator.geolocation, window.isSecureContext);
      setPoint(coordinates); publish(coordinates);
      setNotice("Starting location shared for this page only. An explicit destination still takes priority.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Location unavailable. Enter a city/neighborhood in Set preferences."); }
  }
  return <details className="location-controls"><summary>Optional starting location</summary>
    <p>Your destination and starting point are separate. Location is requested only when you select the button.</p>
    <button type="button" className="secondary-button" onClick={locate}>Use my current location</button>
    {point && <button type="button" onClick={() => { setPoint(null); setManual(""); publish(null); setNotice("Shared starting location removed."); }}>Remove shared location</button>}
    <p role="status">{notice}</p>
    <div className="preferences-grid">
      <label>Maximum travel to first stop (minutes)<input type="number" min="0" max="1440" step="1" value={first} onChange={e => { setFirst(e.target.value); publish(point, e.target.value); }} /></label>
      <label>Search radius near me (meters)<input type="number" min="1" max="50000" value={radius} onChange={e => { setRadius(e.target.value); publish(point, first, e.target.value); }} /><small>Only for a coordinate-based “near me” search.</small></label>
    </div>
    <details><summary>Enter a starting point manually</summary><p>Enter latitude, longitude from your chosen starting point. For a city/neighborhood search instead, use Location in Set preferences; it will not be treated as your starting position.</p>
      <label>Starting latitude, longitude<input value={manual} placeholder="latitude, longitude" onChange={e => setManual(e.target.value)} /></label>
      <button type="button" onClick={() => { const values = manual.split(",").map(v => v.trim()); const [latitude, longitude] = values.map(Number);
        if (values.length !== 2 || values.some(v => !v) || !Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) { setNotice("Enter valid latitude, longitude, or use a city/neighborhood in Set preferences."); return; }
        const coordinates = { latitude, longitude }; setPoint(coordinates); publish(coordinates); setNotice("Your chosen starting point is ready for this page only.");
      }}>Use this starting point</button>
    </details>
  </details>;
}
