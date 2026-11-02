"use client";
import {savedLaunchToken,TAB_SAVED_KEY} from "@/lib/saved-navigation";
import { failureText } from "@/lib/failure-diagnostics";
import { useEffect, useState, useCallback, useRef } from "react";
import type { PlannerResult } from "@/lib/planner";
import { createPortal } from "react-dom";
import {mergeRefreshed,type RefreshedVenue} from "@/lib/saved-plan-refresh";
import {loadSavedDetails,detailsFeedback} from "@/lib/saved-details-request";
import { SavedCards } from "./saved-cards";
import { fragmentToken, privateLink, SAVED_KEY, TOKEN, validateSaved, type SavedPlan } from "@/lib/saved-plans";

function markExplicit(accessToken:string){
    try{sessionStorage.setItem(TAB_SAVED_KEY,accessToken);}catch{/* The copied link still works. */}
    window.history.replaceState({...window.history.state,wheretoSavedView:true},"",window.location.pathname+window.location.search);
  }

export function SavedPlans({ result,active,onOpen,contextKey }: { result?: PlannerResult;active:boolean;onOpen:(open:boolean)=>void;contextKey:string }) {
  const openEpoch=useRef(0);
  const opening=useRef("");
  const refreshing=useRef(false);
  const saving=useRef(false);
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
  const [copyMessage,setCopyMessage]=useState("");
  const [expanded,setExpanded]=useState(false);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ receipt: string; selected: string; token: string } | null>(null);
  useEffect(()=>{openEpoch.current+=1;queueMicrotask(()=>{setBusy(false);setMessage("");setCopyMessage("");});},[contextKey]);
  const ready = !!result?.saveAccessToken && !!result?.saveReceipt && !!result.plans.length;
  const choice = result?.plans.some(p => p.id === selected) ? selected : result?.plans[0]?.id ?? "";

  const open=useCallback(async (accessToken: string) => {
    if (!TOKEN.test(accessToken)) { openEpoch.current+=1;setSaved(null);onOpen(true);setExpanded(true);setBusy(false);setMessage("Enter a valid private saved-plan link."); return; }
    if(opening.current===accessToken)return;
    opening.current=accessToken;
    const epoch=++openEpoch.current;
    setBusy(true); setSaved(null);setVenues({});onOpen(true);setExpanded(true);setMessage("Opening saved plan…");
    try {
      const response = await fetch("/api/plans/reopen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ accessToken }), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(failureText(data, data.message ?? "Saved plan unavailable."));
      const document = validateSaved(data);
      if(epoch!==openEpoch.current)return;
      markExplicit(accessToken);setExpanded(true);
      setSaved(document);setVenues({});setRefreshMessage("");onOpen(true); setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));setCopyMessage("");
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { /* Private link still works without storage. */ }
      setMessage("");
      if(data.automaticVenueDetails===true&&document.dataMode==="real"){
        setRefreshMessage("Loading current venue details…");
        try{
          const updates=await loadSavedDetails(accessToken,document.selectedId);
          if(epoch===openEpoch.current){setVenues(updates);setRefreshMessage(detailsFeedback(updates));}
        }catch(error){if(epoch===openEpoch.current)setRefreshMessage(error instanceof Error?error.message:"Venue details unavailable. Your saved plan is kept.");}
      }
    } catch (error) { if(epoch===openEpoch.current)setMessage(error instanceof Error ? error.message : "Saved plan unavailable. Try again later."); }
    finally { if(opening.current===accessToken)opening.current=""; if(epoch===openEpoch.current)setBusy(false); }
  },[onOpen]);

  function closeView(){
    openEpoch.current+=1;onOpen(false);setSaved(null);setVenues({});setBusy(false);setMessage("");
    try{sessionStorage.removeItem(TAB_SAVED_KEY);}catch{/* No persisted provider content. */}
    window.history.replaceState({...window.history.state,wheretoSavedView:false},"",window.location.pathname+window.location.search);
  }
  useEffect(() => {
    let mounted=true;
    function importLink(initial=false){
      const hash=window.location.hash;
      let tabReference:string|null=null;
      try{tabReference=sessionStorage.getItem(TAB_SAVED_KEY);}catch{/* Storage may be disabled. */}
      const key=savedLaunchToken(hash,initial&&!!window.history.state?.wheretoSavedView,tabReference);
      if(hash.startsWith("#saved=")){
        window.history.replaceState({...window.history.state,wheretoSavedView:!!key},"",window.location.pathname+window.location.search);
        if(key)try{sessionStorage.setItem(TAB_SAVED_KEY,key);}catch{/* Copied link remains usable. */}
        else queueMicrotask(()=>{if(mounted){openEpoch.current+=1;setSaved(null);setVenues({});onOpen(true);setBusy(false);setExpanded(true);setMessage("This private link is malformed. Check the complete saved-plan link.");}});
      }
      if(key)queueMicrotask(()=>{if(mounted)void open(key);});
      else if(initial&&!hash.startsWith("#saved=")){
        let remembered="";
        try{remembered=localStorage.getItem(SAVED_KEY)??"";}catch{/* Storage may be disabled. */}
        if(TOKEN.test(remembered))queueMicrotask(()=>{if(mounted){setToken(remembered);setLink(privateLink(window.location.origin,remembered));}});
      }
    }
    importLink(true);
    const changed=()=>importLink();
    window.addEventListener("hashchange",changed);
    return()=>{mounted=false;window.removeEventListener("hashchange",changed);};
  },[open,onOpen]);

  async function save() {
    if (saving.current || !ready || !result?.saveReceipt || !result.saveAccessToken) return;
    saving.current=true;
    const epoch=openEpoch.current;
    const receipt = result.saveReceipt;
    const current = pending;
    const accessToken = current?.receipt === receipt ? current.token : result.saveAccessToken;
    // Keep this capability stable for timeout/commit-uncertainty retries.
    const selectedId = current?.receipt === receipt ? current.selected : choice;
    setPending({ receipt, selected: selectedId, token: accessToken });
    setExpanded(true);setBusy(true); setMessage("Saving plan…");
    try {
      const response = await fetch("/api/plans/save", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receipt, accessToken, candidateIds: result.plans.map(p => p.id), selectedId }), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(failureText(data, data.message ?? "Saved plan unavailable."));
      if(epoch!==openEpoch.current)return;
      if (data.saved !== true) throw new Error("The save was not confirmed. Retry before keeping a private link.");
      setToken(accessToken); setLink(privateLink(window.location.origin, accessToken));setCopyMessage("");
      let remembered = true;
      try { localStorage.setItem(SAVED_KEY, accessToken); } catch { remembered = false; }
      setExpanded(true);setMessage(remembered ? "" : "This browser cannot remember the link. Copy it to keep it.");
      setSavedReceipt(receipt);
      setSaved(null);onOpen(false);
    } catch (error) {
      if(epoch===openEpoch.current)setMessage(error instanceof Error ? error.message : "Save failed. Your current plan is kept.");
    }
    finally { saving.current=false;if(epoch===openEpoch.current)setBusy(false); }
  }

  async function refresh(candidateId:string,includeContacts=false,includeHours=false){
    if(refreshing.current)return;
    refreshing.current=true;
    const epoch=openEpoch.current;
    setBusy(true);setRefreshMessage(includeHours?"Loading opening hours…":"Loading current venue details…");
    try{
      const updates=await loadSavedDetails(token,candidateId,includeContacts,includeHours);
      if(epoch!==openEpoch.current)return;
      setVenues(previous=>mergeRefreshed(previous,updates,includeHours));setRefreshMessage(detailsFeedback(updates,includeHours));
    }catch(error){if(epoch===openEpoch.current)setRefreshMessage(error instanceof Error?error.message:"Venue refresh unavailable. Your saved plan is kept.");}
    finally{refreshing.current=false;if(epoch===openEpoch.current)setBusy(false);}
  }
  async function copy(){
    try{await navigator.clipboard.writeText(link);setCopyMessage("Private link copied.");}
    catch{setCopyMessage("Copy unavailable. Use your browser’s Copy link address action on Open saved plan.");}
  }
  return <section className="saved-plans" aria-label="Save and reopen plans">
    {active&&container&&createPortal(saved?<SavedCards saved={saved} venues={venues} refresh={(id,contacts,hours)=>void refresh(id,contacts,hours)} busy={busy} message={refreshMessage} onClose={closeView}/>:<section aria-label="Saved itinerary status"><p role="status">{message||"Opening saved plan…"}</p><button type="button" className="secondary-button" onClick={closeView}>Return to planning</button></section>,container)}
    {ready && savedReceipt !== result?.saveReceipt && <div className="saved-controls"><label>Selected itinerary<select value={choice} disabled={busy || pending?.receipt === result?.saveReceipt} onChange={event => setSelected(event.target.value)}>{result!.plans.map((plan,i) => <option key={plan.id} value={plan.id}>Option {i+1}: {plan.venues.map(v=>v.name).join(" → ")}</option>)}</select></label><button type="button" className="secondary-button" disabled={busy || savedReceipt === result?.saveReceipt} aria-busy={busy} onClick={()=>void save()}>Save Plan</button></div>}
    <details open={expanded} onToggle={event=>setExpanded(event.currentTarget.open)}><summary>Saved plans</summary>
    {message && !active && <p role="status" aria-live="polite">{message}</p>}
    {link && <div className="saved-link"><h3 aria-live="polite">{!active&&savedReceipt!==result?.saveReceipt?"Previously saved plan":"Your plan is saved"}</h3><p>Copy or open your private link. It expires in 30 days, and anyone with the link can view it.</p><div className="saved-actions"><button type="button" className="secondary-button" onClick={()=>void copy()}>Copy link</button><a className="secondary-button" href={link} target="_blank" rel="noopener noreferrer">Open saved plan<span className="sr-only"> (opens in a new tab)</span></a><button type="button" className="secondary-button saved-forget" onClick={()=>{try { localStorage.removeItem(SAVED_KEY); } catch { /* Storage may be disabled. */ } closeView();setToken("");setLink("");setMessage("Link forgotten on this device.");}}>Forget on this device</button></div>{copyMessage&&<p role="status">{copyMessage}</p>}</div>}
    <details><summary>Reopen another saved plan</summary><label>Private saved-plan link<input type="text" value={input} onChange={event=>setInput(event.target.value)} placeholder="Paste your private link" autoComplete="off" spellCheck={false} /></label><button type="button" className="secondary-button" disabled={busy||!input} onClick={()=>{try { const url=new URL(input); void open(fragmentToken(url.hash)??""); } catch { void open(""); }}}>Open private link</button></details>
    </details>
  </section>;
}
