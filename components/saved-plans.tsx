"use client";
import { failureText } from "@/lib/failure-diagnostics";
import { useEffect, useState, useCallback, useRef } from "react";
import type { PlannerResult } from "@/lib/planner";
import { createPortal } from "react-dom";
import {mergeRefreshed,type RefreshedVenue} from "@/lib/saved-plan-refresh";
import { SavedCards } from "./saved-cards";
import { fragmentToken, privateLink, SAVED_KEY, TOKEN, validateSaved, type SavedPlan } from "@/lib/saved-plans";

export function SavedPlans({ result,active,onOpen,contextKey }: { result?: PlannerResult;active:boolean;onOpen:(open:boolean)=>void;contextKey:string }) {
  const openEpoch=useRef(0);
  const [container,setContainer]=useState<HTMLElement|null>(null);
  const [venues,setVenues]=useState<Record<string,RefreshedVenue>>({});
  const [refreshMessage,setRefreshMessage]=useState("");
  useEffect(()=>{queueMicrotask(()=>setContainer(document.getElementById("saved-results")));},[]);
  const [token, setToken] = useState("");
  const [savedReceipt, setSavedReceipt] = useState("");
  const [saved, setSaved] = useState<SavedPlan | null>(null);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [link, setLink] = useState("");
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ receipt: string; selected: string; token: string } | null>(null);
  useEffect(()=>{openEpoch.current+=1;queueMicrotask(()=>{setBusy(false);setMessage("");});},[contextKey]);
  const ready = !!result?.saveAccessToken && !!result?.saveReceipt && !!result.plans.length;
  const choice = result?.plans.some(p => p.id === selected) ? selected : result?.plans[0]?.id ?? "";

  const open=useCallback(async (accessToken: string) => {
    if (!TOKEN.test(accessToken)) { setMessage("Enter a valid private saved-plan link."); return; }
    const epoch=++openEpoch.current;
    setBusy(true); setMessage("Opening saved plan…");
    try {
      const response = await fetch("/api/plans/reopen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ accessToken }), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(failureText(data, data.message ?? "Saved plan unavailable."));
      const document = validateSaved(data);
      if(epoch!==openEpoch.current)return;
      setSaved(document);setVenues({});setRefreshMessage("");onOpen(true); setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { /* Private link still works without storage. */ }
      setMessage("Saved plan reopened. No live venue or route refresh was requested.");
    } catch (error) { if(epoch===openEpoch.current)setMessage(error instanceof Error ? error.message : "Saved plan unavailable. Try again later."); }
    finally { if(epoch===openEpoch.current)setBusy(false); }
  },[onOpen]);

  useEffect(() => {
    let active = true;
    function importLink(remembered = false) {
      const hash=window.location.hash;
      const fromLink=fragmentToken(hash);
      if(hash.startsWith("#saved=")) window.history.replaceState(null,"",window.location.pathname+window.location.search);
      let last="";
      if(remembered && !hash.startsWith("#saved=")) try { last=localStorage.getItem(SAVED_KEY)??""; } catch { /* Storage may be disabled. */ }
      if(hash.startsWith("#saved=") && !fromLink) {
        queueMicrotask(()=>{if(active)setMessage("This private link is malformed. Check the complete saved-plan link.");});
        return;
      }
      const key=fromLink??last;
      if(TOKEN.test(key)) queueMicrotask(()=>{if(active)void open(key);});
    }
    importLink(true);
    const changed=()=>importLink();
    window.addEventListener("hashchange",changed);
    return ()=>{active=false;window.removeEventListener("hashchange",changed);};
  }, [open]);

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
      if (!response.ok) throw new Error(failureText(data, data.message ?? "Saved plan unavailable."));
      if (data.saved !== true) throw new Error("The save was not confirmed. Retry before keeping a private link.");
      setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));
      let remembered = true;
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { remembered = false; }
      setMessage(remembered ? "Plan saved. You can refresh or use your private link to reopen it." : "Plan saved. Copy your private link; this browser cannot remember it.");
      setSavedReceipt(receipt);
      setSaved(null);onOpen(false);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed. Your current plan is kept.");
    }
    finally { setBusy(false); }
  }

  async function refresh(candidateId:string){
    setBusy(true);setRefreshMessage("Refreshing venue details…");
    try{
      const response=await fetch("/api/plans/refresh",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({accessToken:token,candidateId,refreshId:crypto.randomUUID()}),cache:"no-store"});
      const data=await response.json();
      if(!response.ok)throw new Error(failureText(data,data.message??"Venue details unavailable. Your saved plan is kept."));
      if(data.candidateId!==candidateId || !data.venues || typeof data.venues!=="object")throw new Error("Venue response could not be verified.");
      setVenues(previous=>mergeRefreshed(previous,data.venues));
      setRefreshMessage("Refresh finished. Some details may be unavailable; routes, hours and activity schedules were not refreshed.");
    }catch(error){setRefreshMessage(error instanceof Error?error.message:"Venue refresh unavailable. Your saved plan is kept.");}
    finally{setBusy(false);}
  }
  async function copy(){
    try{await navigator.clipboard.writeText(link);setMessage("Private link copied.");}
    catch{setMessage("Copy unavailable. Select and copy the link below.");}
  }
  return <section className="saved-plans" aria-label="Save and reopen plans">
    {active&&saved&&container&&createPortal(<SavedCards saved={saved} venues={venues} refresh={id=>void refresh(id)} busy={busy} message={refreshMessage}/>,container)}
    {ready && <div className="saved-controls"><label>Selected itinerary<select value={choice} disabled={busy || pending?.receipt === result?.saveReceipt} onChange={event => setSelected(event.target.value)}>{result!.plans.map((plan,i) => <option key={plan.id} value={plan.id}>Option {i+1}: {plan.venues.map(v=>v.name).join(" → ")}</option>)}</select></label><button type="button" className="secondary-button" disabled={busy || savedReceipt === result?.saveReceipt} aria-busy={busy} onClick={()=>void save()}>{savedReceipt === result?.saveReceipt ? "Plan saved" : "Save Plan"}</button><p>Saves these options and your selection.</p></div>}
    {message && <p role="status" aria-live="polite">{message}</p>}
    {link && <div className="saved-link"><h3>Your saved plan</h3><p>Copy this private link to reopen your plan for 30 days. Anyone with the link can view it.</p><button type="button" className="secondary-button" onClick={()=>void copy()}>Copy link</button><button type="button" className="secondary-button" disabled={busy} onClick={()=>void open(token)}>Open saved plan</button><details><summary>Link and help</summary><label>Private link<input readOnly value={link} onFocus={event=>event.target.select()} /></label><p>This is your last confirmed saved plan. A failed save does not replace it. If a response is lost, retry the same selection. Existing copies work until expiry.</p><button type="button" className="secondary-button" onClick={()=>{try { localStorage.removeItem(SAVED_KEY); } catch { /* Storage may be disabled. */ } setToken("");setLink("");setSaved(null);onOpen(false);setMessage("Link forgotten on this device.");}}>Forget on this device</button></details></div>}
    <details><summary>Reopen a saved plan</summary><label>Private saved-plan link<input type="text" value={input} onChange={event=>setInput(event.target.value)} placeholder="Paste your private link" autoComplete="off" spellCheck={false} /></label><button type="button" className="secondary-button" disabled={busy||!input} onClick={()=>{try { const url=new URL(input); void open(fragmentToken(url.hash)??""); } catch { setMessage("Enter a valid private saved-plan link."); }}}>Open private link</button></details>
  </section>;
}
