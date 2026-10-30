"use client";
import { useEffect, useState } from "react";
import type { PlannerResult } from "@/lib/planner";
import { activityLabel, formatTime, type Activity } from "@/lib/planner";
import { fragmentToken, preferenceText, privateLink, SAVED_KEY, TOKEN, validateSaved, type SavedPlan } from "@/lib/saved-plans";

export function SavedPlans({ result }: { result?: PlannerResult }) {
  const [token, setToken] = useState("");
  const [savedReceipt, setSavedReceipt] = useState("");
  const [saved, setSaved] = useState<SavedPlan | null>(null);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [link, setLink] = useState("");
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ receipt: string; selected: string; token: string } | null>(null);
  const ready = !!result?.saveAccessToken && !!result?.saveReceipt && !!result.plans.length;
  const choice = result?.plans.some(p => p.id === selected) ? selected : result?.plans[0]?.id ?? "";

  async function open(accessToken: string) {
    if (!TOKEN.test(accessToken)) { setMessage("Enter a valid private saved-plan link."); return; }
    setBusy(true); setMessage("Opening saved plan…");
    try {
      const response = await fetch("/api/plans/reopen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ accessToken }), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      const document = validateSaved(data);
      setSaved(document); setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { /* Private link still works without storage. */ }
      setMessage("Saved plan reopened. No live venue or route refresh was requested.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Saved plan unavailable. Try again later."); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    const fromLink = fragmentToken(window.location.hash);
    if (window.location.hash.startsWith("#saved=")) window.history.replaceState(null, "", window.location.pathname + window.location.search);
    let last = "";
    try { last = localStorage.getItem(SAVED_KEY) ?? ""; } catch { /* Storage can be disabled. */ }
    const key = fromLink ?? last;
    let active = true;
    if (TOKEN.test(key)) queueMicrotask(() => {
      if (!active) return;
      setToken(key); setLink(privateLink(window.location.origin, key));
      void open(key);
    });
    return () => { active = false; };
  }, []);

  async function save() {
    if (!ready || !result?.saveReceipt || !result.saveAccessToken) return;
    const receipt = result.saveReceipt;
    const current = pending;
    const accessToken = current?.receipt === receipt ? current.token : result.saveAccessToken;
    // Keep this capability stable for timeout/commit-uncertainty retries.
    const selectedId = current?.receipt === receipt ? current.selected : choice;
    setPending({ receipt, selected: selectedId, token: accessToken });
    setBusy(true); setMessage("Saving plan…");
    try {
      const response = await fetch("/api/plans/save", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receipt, accessToken, candidateIds: result.plans.map(p => p.id), selectedId }), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));
      let remembered = true;
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { remembered = false; }
      setMessage(remembered ? "Plan saved. You can refresh or use your private link to reopen it." : "Plan saved. Copy your private link; this browser cannot remember it.");
      setSavedReceipt(receipt);
      setSaved(null);
    } catch (error) {
      setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));
      setMessage(error instanceof Error ? error.message : "Save failed. Your current plan is kept.");
    }
    finally { setBusy(false); }
  }

  const request = saved?.constraints;
  return <section className="saved-plans" aria-label="Save and reopen plans">
    {ready && <div className="saved-controls"><label>Selected itinerary<select value={choice} disabled={busy || pending?.receipt === result?.saveReceipt} onChange={event => setSelected(event.target.value)}>{result!.plans.map((plan,i) => <option key={plan.id} value={plan.id}>Option {i+1}: {plan.venues.map(v=>v.name).join(" → ")}</option>)}</select></label><button type="button" className="secondary-button" disabled={busy || savedReceipt === result?.saveReceipt} aria-busy={busy} onClick={()=>void save()}>{savedReceipt === result?.saveReceipt ? "Plan saved" : "Save Plan"}</button><p>Saves these {result!.plans.length} options and your selection. Your selection stays fixed after you submit. Generate again to save a different selection. Real venue details and travel estimates will need checking again.</p></div>}
    <details><summary>Reopen a saved plan</summary><label>Private saved-plan link<input type="text" value={input} onChange={event=>setInput(event.target.value)} placeholder="Paste your private link" autoComplete="off" spellCheck={false} /></label><button type="button" className="secondary-button" disabled={busy||!input} onClick={()=>{try { const url=new URL(input); void open(fragmentToken(url.hash)??""); } catch { setMessage("Enter a valid private saved-plan link."); }}}>Open private link</button>{token && <button type="button" className="secondary-button" disabled={busy} onClick={()=>void open(token)}>Reopen last saved plan</button>}</details>
    {message && <p role="status" aria-live="polite">{message}</p>}
    {link && <details><summary>Your private link</summary><p>Anyone with this link can read the saved plan for 30 days. It is not an account. Keep it private; avoid shared browsers. Only the last link is remembered on this device. If a save response was lost, reopening this link checks whether it saved.</p><label>Copy and keep this link<input readOnly value={link} onFocus={event=>event.target.select()} /></label><button type="button" className="secondary-button" onClick={()=>{try { localStorage.removeItem(SAVED_KEY); } catch { /* Storage may be disabled. */ } setToken("");setLink("");setSaved(null);setMessage("Link forgotten on this device. Existing copies still work until expiry.");}}>Forget on this device</button></details>}
    {saved && request && <article className="saved-document"><h3>Saved plan · {request.location} · {request.date}</h3><p>{saved.dataMode === "mock" ? "Saved fictional sample. All venues, prices, schedules and travel are mock data." : "Saved planning structure · Google Maps Place ID references only. Venue names, hours, prices, availability, geography checks and routes are unavailable until an intentional refresh. No live information was fetched."}</p><p>{request.planningMode === "surprise" ? "Surprise Me · Begins at the first activity." : "Origin-based plan · Exact starting location was not retained; first-leg travel is unavailable."} Saved order is preserved.</p><p>Time window: {formatTime(request.startTime)}–{formatTime(request.endTime)} {request.calendarTimezone ?? "destination time"}. {request.transport ? `Travel mode: ${request.transport}.` : ""}</p><p>First-stop travel: {preferenceText(request.firstTravel)}. Between activities: {preferenceText(request.betweenTravel)}.</p>{request.travel!==null&&<p>Total inter-stop travel limit: {request.travel} minutes.</p>}{request.maxLegTravel!==null&&<p>Per-leg limit: {request.maxLegTravel} minutes.</p>}{request.maxFirstLegTravel!==null&&<p>First-leg limit: {request.maxFirstLegTravel} minutes.</p>}
      <details><summary>Other saved requirements</summary><p>{request.geography.strictDestination ? "Stay within the destination. " : ""}{request.geography.excludedRegions.length ? `Excluded regions: ${request.geography.excludedRegions.join(", ")}. ` : ""}{request.requireWheelchairAccess ? "Wheelchair access required. " : ""}{request.requireAvailability ? "Availability required. " : ""}{request.allowRevisits ? "Revisits permitted. " : "No repeated venues. "}{request.dinner ? "Dinner requested. " : ""}These requirements are retained; live compliance is not reverified.</p></details>
      {saved.itineraries.map((option,i)=><details key={option.candidateId} open={option.candidateId===saved.selectedId}><summary>Saved option {i+1}{option.candidateId===saved.selectedId ? " · selected" : ""}</summary><ol>{option.stops.map(stop=><li key={stop.position}><strong>{stop.position+1}. {stop.fictional?.name ?? activityLabel(stop.activity as Activity)}</strong><p>{request.activityIntents[stop.activity]??activityLabel(stop.activity as Activity)}</p>{stop.fictional ? <p>Fictional venue · {stop.fictional.neighborhood}. {stop.start===null ? "Timing unavailable" : `${formatTime(stop.start)}–${formatTime(stop.end)}`}. {stop.fictional.price===null ? "Sample price unknown" : `$${stop.fictional.price} sample price`}</p> : <p>Google Maps Place ID: <code>{stop.reference}</code>. Saved reference; venue details and travel unavailable.</p>}</li>)}</ol>{option.fictionalMetrics&&<p>Fictional travel between stops: {option.fictionalMetrics.totalTravel??"Unknown"} minutes. No trip home is included.</p>}</details>)}<p>Private access expires {new Date(saved.expiresAt).toLocaleDateString()}.</p></article>}
  </section>;
}
