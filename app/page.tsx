"use client";
import {restoreContinuation,continuationNotice} from "@/lib/continuation";
import {BeyondPreferences} from "@/components/beyond-preferences";
import { SavedPlans } from "@/components/saved-plans";
import { ItineraryPagination } from "@/components/itinerary-pagination";
import { ItineraryPages } from "@/lib/itinerary-pages";

import { explorationStage } from "../components/exploration-notice";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, ChevronDown, Clock3, Footprints, MapPin, Settings2, Sparkles, CircleHelp } from "lucide-react";
import { HeroArtwork } from "@/components/artwork";
import { EXAMPLE_REQUEST, MOCK_EVENT_DATES, type PlannerResult } from "@/lib/planner";

import { emptyPreferenceState, editPreference, manualPreferences, displayInterpretedPreferences, type PreferenceField } from "@/lib/preferences";
import { PlanningSession } from "@/lib/planning-session";
import { AlternativeActions } from "@/components/alternative-actions";
import { SurpriseHistory } from "@/lib/surprise-history";
import { generateOuting, type ValidatedOuting, type PendingOuting, type ClarificationAnswers } from "@/lib/planning-client";
import { ClarificationField } from "@/components/clarification-field";
import { OutingDateField } from "@/components/outing-date-field";
import { ResultsInformation } from "@/components/results-information";
import { consumerMessage, resultsSummary } from "@/lib/results-presentation";
import { PlanningFeedback } from "@/components/planning-feedback";
import { OutingSummary, activityEditText } from "@/components/outing-summary";
import { LocationControls, type StartingLocationHandle } from "@/components/location-controls";
import { VenueDetailsSession } from "@/lib/venue-details";
import type { LocationContext } from "@/lib/planning-client";
import { nextOptions } from "@/lib/option-batches";
import { adaptRanking } from "@/lib/planning-client";
import {AdvancedClarifications} from "@/components/advanced-plan";
import {continueAdvanced} from "@/lib/advanced-planning";
import {PlanCard} from '@/components/plan-card';
import demoPlans from "@/data/demo-plans.json";


export default function Home() {
  const [dataMode, setDataMode] = useState<"mock" | "real" | "unavailable">("unavailable");
  const startingControls = useRef<StartingLocationHandle>(null);
  const [lookupEnabled, setLookupEnabled] = useState(false);
  const [planningStage, setPlanningStage] = useState("Generating itinerary");
  const [locationContext, setLocationContext] = useState<LocationContext>({});
  const [detailsSession] = useState(()=>new VenueDetailsSession());
  useEffect(() => { let active = true; void fetch("/api/planning-mode", { cache: "no-store", signal: AbortSignal.timeout(5000) }).then(r => r.json()).then(value => { if (active && value.enabled && ["real", "mock"].includes(value.mode)) { setDataMode(value.mode); setLookupEnabled(value.startingLookupEnabled === true); } }).catch(() => {}); return () => { active = false; }; }, []);
  const advancedContinuation=useRef<PendingOuting|null>(null);
  const advancedAnswers=useRef<Record<string,unknown>[]>([]);
  const [validated, setValidated] = useState<ValidatedOuting | null>(null);
  const [dirty, setDirty] = useState(false);
  const [request, setRequest] = useState("");
  const [preferenceState, setPreferenceState] = useState(emptyPreferenceState);
  const preferences = preferenceState.values;
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [result, setResult] = useState<PlannerResult>(demoPlans as PlannerResult);
  const pages = useRef(new ItineraryPages());
  const latest = useRef<PlannerResult>(demoPlans as PlannerResult);
  const [pageState,setPageState]=useState({index:0,count:0,hasBeyond:false});
  function syncPages(){setPageState({index:pages.current.index,count:pages.current.pages.length,hasBeyond:pages.current.pages.some(page=>page.plans.some(plan=>plan.travelClassification==="beyond_limit"))});}
  const [loading, setLoading] = useState(false);
  const session = useRef(new PlanningSession());
  const surpriseHistory=useRef(new SurpriseHistory());
  useEffect(()=>{surpriseHistory.current.record(result.plans);},[result.plans]);
  const [clarification, setClarification] = useState<PendingOuting | null>(null);
  const [answers, setAnswers] = useState<ClarificationAnswers>({});
  const followupRef = useRef<HTMLDivElement>(null);
  const [generated, setGenerated] = useState(false);
  const [savedOpen,setSavedOpen]=useState(false);
  const resultsRef = useRef<HTMLHeadingElement>(null);
  const requestRef = useRef<HTMLTextAreaElement>(null);
  function updatePreference(key: PreferenceField, value: string) {
    const answering=result.advanced?.data.questions.some(q=>q.field===(key==='location'?'destination':key));
    if(!answering)invalidateResults();
    setPreferenceState(previous => editPreference(previous, key, value));
  }
  function invalidateResults() {
    setSavedOpen(false);
    setRecovery(undefined);setOptionsNotice("");
    pages.current.reset();syncPages();
    startingControls.current?.cancel();
    session.current.cancel();
    detailsSession.clear();
    setLoading(false);
    setDirty(true);
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Details changed. Regenerate recommendations to use your corrections.", location: "", activities: [], notes: [] });
  }
  function replaceRequest() {
    advancedContinuation.current=null;advancedAnswers.current=[];
    setSavedOpen(false);
    cancelClarification();
    detailsSession.clear();
    setValidated(null);
    setDirty(false);
    setPreferenceState(previous => displayInterpretedPreferences(previous, emptyPreferenceState().values));
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Plan your new request to see recommendations.", location: "", activities: [], notes: [] });
  }
  function cancelClarification() {
    setRecovery(undefined);setOptionsNotice("");
    pages.current.reset();syncPages();
    startingControls.current?.cancel();
    session.current.cancel();
    setLoading(false);
    setClarification(null);
    setAnswers({});
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Follow-up canceled. Edit your request or plan again.", location: "", activities: [], notes: [] });
  }
  const [optionsNotice, setOptionsNotice] = useState("");
  const [recovery,setRecovery]=useState<string|undefined>();
  const [optionsBusy,setOptionsBusy]=useState(false);
  function cancelPlanning() {
    session.current.cancel();
    startingControls.current?.cancel();
    setLoading(false);setOptionsBusy(false);
    setOptionsNotice("Planning cancelled. Your saved pages are still available; no further work is queued.");
    setResult(previous => previous.plans.length ? previous : { ...previous, requestFailed:false, message:"Planning cancelled. Your request is kept; submit again when ready." });
  }
  async function showDifferent(expandDiscovery = false, showBeyond = false) {
    const active=latest.current;
    if (!showBeyond && !expandDiscovery && active.alternativeBatches?.length) { const next=nextOptions(active);latest.current=next;if(pages.current.append(next)){setResult(structuredClone(pages.current.pages[pages.current.index]));syncPages();}setOptionsNotice("");return; }
    if ((!active.optionsToken&&!active.advanced) || !(expandDiscovery ? active.canDiscover : showBeyond ? (active.canShowBeyond||active.advanced&&active.canExpand) : active.canExpand)) return;
    const controller = session.current.begin();
    if (!controller) return;
    setPlanningStage(explorationStage(expandDiscovery));
    setLoading(true); setOptionsBusy(true); setOptionsNotice("");setRecovery(undefined);
    try {
      if(active.advanced){
        const next=await continueAdvanced(active.advanced,{action:expandDiscovery?'discover':showBeyond?'beyond':'different',includeBeyond:showBeyond},controller.signal);
        if(!session.current.current(controller))return;
        latest.current=next;
        if(pages.current.append(next)){setResult(structuredClone(pages.current.pages[pages.current.index]));syncPages();}
        else {setResult(previous=>({...previous,canExpand:next.canExpand,canDiscover:next.canDiscover,canShowBeyond:next.canShowBeyond}));setOptionsNotice(next.message);}
        return;
      }
      const response = await fetch("/api/plans/options", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: active.optionsToken, expandDiscovery, showBeyond }), cache: "no-store", signal: controller.signal });
      const data = await response.json();
      if (!session.current.current(controller)) return;
      if (!response.ok) { if(typeof data.continuation?.canExpand==="boolean"&&typeof data.continuation?.canDiscover==="boolean"){latest.current={...active,...data.continuation};setResult(previous=>({...previous,...data.continuation}));} setRecovery(data.code);if(Array.isArray(data.diagnosticNotes))setResult(previous=>({...previous,notes:[...previous.notes,...data.diagnosticNotes]}));if(data.resumable===true){setOptionsNotice(consumerMessage(data.message));return;}throw new Error(typeof data.message === "string" ? data.message : "More options are unavailable."); }
      const next = adaptRanking(data);
      if (!session.current.current(controller)) return;
      setRecovery(next.recoveryCode);
      if (next.plans.length) { latest.current=next;if(pages.current.append(next)){setResult(structuredClone(pages.current.pages[pages.current.index]));syncPages();setOptionsNotice("");}else setOptionsNotice("No new complete combinations were returned. Your saved pages are unchanged."); }
      else { latest.current={...active,canExpand:next.canExpand,canDiscover:next.canDiscover,canShowBeyond:next.canShowBeyond,continuationStatus:next.continuationStatus};setResult(previous => ({ ...previous, canExpand: next.canExpand, canDiscover: next.canDiscover, canShowBeyond:next.canShowBeyond,continuationStatus:next.continuationStatus })); setOptionsNotice(consumerMessage(next.message) || "No more distinct options in the checked candidate pool."); }
    } catch (error) {
      if(session.current.current(controller)&&active.advanced&&['invalid_request','provider_quota_rejected'].includes((error as {code?:string}).code??'')){
        latest.current={...active,canExpand:false,canDiscover:false,canShowBeyond:false};
        setResult(previous=>({...previous,canExpand:false,canDiscover:false,canShowBeyond:false}));
      }
      if (session.current.current(controller)) { setOptionsNotice(error instanceof Error ? consumerMessage(error.message) : "More options are unavailable. No automatic retry was made."); }
    } finally { if (session.current.finish(controller)) {setLoading(false);setOptionsBusy(false);} }
  }
  async function answerAdvanced(answer:Record<string,unknown>){
    if(!result.advanced||dirty)return;
    const controller=session.current.begin();if(!controller)return;
    setLoading(true);setPlanningStage("Applying your answer and checking the itinerary");setOptionsNotice("");
    try{
      const next=await continueAdvanced(result.advanced,answer,controller.signal);
      if(!session.current.current(controller))return;
      if(answer.dwell||answer.departure||answer.choice||answer.searchNearOrigin){
        advancedAnswers.current=advancedAnswers.current.filter(a=>!(answer.dwell&&a.dwell&&(a.dwell as {occurrence:number}).occurrence===(answer.dwell as {occurrence:number}).occurrence)&&!(answer.departure&&a.departure)&&!(answer.searchNearOrigin&&a.searchNearOrigin)&&!(answer.choice&&a.choice&&(a.choice as {occurrence:number}).occurrence===(answer.choice as {occurrence:number}).occurrence));
        advancedAnswers.current.push(answer);
      }
      if(typeof answer.date==='string')setPreferenceState(previous=>editPreference(previous,'date',next.advanced?.data.date&&!next.advanced.data.questions.some(q=>q.field==='date')?next.advanced.data.date:answer.date as string));
      if(typeof answer.destination==='string')setPreferenceState(previous=>editPreference(previous,'location',answer.destination as string));
      setResult(next);latest.current=next;
      focusFollowup(next);
      if(!pages.current.pages.length){pages.current.append(next);syncPages();}
      else {pages.current.pages[pages.current.index]=structuredClone(next);syncPages();}
    }catch(error){if(session.current.current(controller))setOptionsNotice(error instanceof Error?error.message:"Your answer could not be applied. Your itinerary is kept.");}
    finally{if(session.current.finish(controller))setLoading(false);}
  }
  function focusFollowup(next:PlannerResult){
    if(next.advanced){
      const data=next.advanced.data;
      setPreferenceState(previous=>displayInterpretedPreferences(previous,{...previous.values,date:data.questions.some(q=>q.field==='date'||q.field==='destination')?previous.values.date:data.date??previous.values.date,location:data.destination??previous.values.location}));
    }
    const fields=next.advanced?.data.questions.map(q=>q.field)??[];
    if(fields.some(f=>f==='date'||f==='destination'))setPreferencesOpen(true);
    requestAnimationFrame(()=>{
      if(fields.includes('date'))document.querySelector<HTMLInputElement>('#preferences input[name="outing-date"]')?.focus();
      else if(fields.includes('destination'))document.querySelector<HTMLInputElement>('#destination-preference')?.focus();
      else if(fields.length)document.querySelector<HTMLElement>('.planner .clarification-panel input, .planner .clarification-panel button')?.focus();
    });
  }
  async function runPlanning(followup: boolean) {
    setSavedOpen(false);
    const controller = session.current.begin();
    if (!controller) return;
    detailsSession.clear();
    pages.current.reset();syncPages();
    setOptionsBusy(false);
    setOptionsNotice("");setRecovery(undefined);
    setLoading(true);
    setPlanningStage("Generating itinerary");
    setGenerated(true);
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Planning…", location: "", activities: [], notes: [] });
    let needsAnswer = false;
    let questionField='';
    const original = followup && clarification ? clarification.pending.text : request;
    try {
      const origin = locationContext;
      setPlanningStage("Understanding your request");
      const planningPreferences=manualPreferences(preferenceState);
      const naturalDate=!!clarification?.questions.some(q=>q.field==='date')&&!!preferences.date&&!/^\d{4}-\d{2}-\d{2}$/.test(preferences.date);
      if(naturalDate)planningPreferences.date='';
      const next = await generateOuting(original, planningPreferences, {
        continuation: followup ? clarification ?? validated?.continuation ?? advancedContinuation.current ?? undefined : undefined,
        advancedAnswers: advancedAnswers.current,
        answers: followup ? { ...answers,...(naturalDate?{date:preferences.date}:{}), ...(answers.activities !== undefined ? { activities: answers.activities.trim() || "," } : {}) } : undefined,
        onStage:stage=>{if(session.current.current(controller))setPlanningStage(stage);},
        signal: controller.signal, locationContext: {...origin,locationFirst:true},
        prepareOrigin: async input => {
          const confirmed=await startingControls.current?.prepare(input);
          if (!session.current.current(controller)) return null;
          if (confirmed) setLocationContext(confirmed);
          return confirmed ? {...confirmed,...(confirmed.planningMode==="surprise"?{recentSurpriseIds:surpriseHistory.current.ids()}:{})} : null;
        },
        onValidated: value => { if (session.current.current(controller)) { setPlanningStage("Checking venues and travel"); setValidated(value); if(naturalDate)setPreferenceState(previous=>editPreference(previous,'date',value.request.date)); setClarification(null); setDirty(false); } },
        onInterpreted: values => { if (session.current.current(controller)) setPreferenceState(previous => displayInterpretedPreferences(previous, values)); },
        onClarification: value => {
          if (!session.current.current(controller)) return;
          needsAnswer = !!value?.questions.length;
          questionField=value?.questions[0]?.field??'';
          setClarification(value);
        },
        onComplete: () => { if (session.current.current(controller)) { setClarification(null); setAnswers({}); setPreferencesOpen(false); } },
      });
      if (!session.current.current(controller)) return;
      if(next.advanced){setDirty(false);advancedContinuation.current=next.advanced.continuation??null;}
      setRecovery(next.recoveryCode);
      latest.current=next;pages.current.append(next);syncPages();
      setResult({ ...next, dataMode: next.dataMode ?? (dataMode === "real" ? "real" : "mock") });
      setGenerated(true);
      focusFollowup(next);
      requestAnimationFrame(() => {
        if (needsAnswer) {
          setPreferencesOpen(true);
          requestAnimationFrame(()=>{
            const q=next.advanced?.data.questions;
            if(!q)document.querySelector<HTMLInputElement>(questionField==='date'?'#preferences input[name="outing-date"]':'#destination-preference')?.focus();
            followupRef.current?.querySelector("input")?.focus();
          });
        }
        else if(!next.advanced?.data.questions.length)resultsRef.current?.focus({ preventScroll: false });
      });
    } finally {
      if (session.current.finish(controller)) setLoading(false);
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!request.trim()) { requestRef.current?.setCustomValidity("Tell us a little about your outing."); requestRef.current?.reportValidity(); return; }
    if(result.advanced?.data.questions.length&&!dirty){
      const fields=result.advanced.data.questions.map(q=>q.field);
      if(fields.includes('date')||fields.includes('destination')){
        const answer:Record<string,unknown>={};
        if(fields.includes('date')&&preferences.date)answer.date=preferences.date;
        if(fields.includes('destination')&&preferences.location)answer.destination=preferences.location;
        if(Object.keys(answer).length)await answerAdvanced(answer);
        return;
      }
    }
    await runPlanning(!!clarification || !!validated || !!advancedContinuation.current);
  }
  const preferencesCount = [preferences.location, preferences.date, preferences.travel, preferenceState.manual.transport ? preferences.transport : ""].filter(Boolean).length;

  return <>
    <a className="skip-link" href="#planner">Skip to planner</a>
    <header className="site-header shell">
      <a href="#" className="brand" aria-label="Where To? Home"><span className="brand-icon"><MapPin size={20} strokeWidth={2.3} /></span>where to<span className="brand-question">?</span></a>
      <nav aria-label="Main navigation"><a href="/how-it-works" target="_blank" rel="noopener noreferrer">How it works<span className="sr-only"> (opens in a new tab)</span></a></nav>
    </header>

    <main>
      <section className="hero shell" aria-labelledby="hero-title">
        <div className="hero-copy"><p className="eyebrow"><span /> LESS GROUP CHAT. MORE GOOD TIMES.</p><h1 id="hero-title">Less planning.<br /><em>More hanging out.</em></h1><p className="hero-description">The best plans start with “what if we…”<br className="desktop-break" /> Tell us your vibe. We’ll put the outing together.</p><div className="hero-footnote"><span className="mini-avatars" aria-hidden="true"><span>R</span><span>J</span><span>M</span></span><span>For your people. And your kind of plans.</span></div></div>
        <div className="hero-art-wrap"><HeroArtwork /></div>
      </section>

      <section className="planner-section shell" id="planner" aria-labelledby="planner-title">
        <form className="planner" onSubmit={submit}>
          <div className="planner-topline"><h2 id="planner-title"><Sparkles size={19} /> What are we getting into?</h2></div>
          {dataMode === "unavailable" && <p role="status">Checking the planner connection. If this stays unavailable, start the backend and reload this page before planning.</p>}
          <label htmlFor="outing" className="sr-only">Describe your outing</label>
          <textarea id="outing" ref={requestRef} value={request} onChange={(event) => { replaceRequest(); setRequest(event.target.value); event.target.setCustomValidity(""); }} placeholder={EXAMPLE_REQUEST} maxLength={1200} required rows={3} />
          <p className="prompt-help">Big ideas, loose plans, oddly specific cravings. All welcome.</p>
          {<LocationControls mock={dataMode!=="real"} ref={startingControls} lookupEnabled={lookupEnabled} onStage={setPlanningStage} onChange={(value,preparing) => { if(!preparing)invalidateResults(); setLocationContext(value); }} />}
          <div className="planner-actions"><button type="button" className="preferences-toggle" aria-expanded={preferencesOpen} aria-controls="preferences" onClick={() => setPreferencesOpen(!preferencesOpen)}><Settings2 size={16} /> Set preferences <span className="optional-label">{preferencesCount ? `${preferencesCount} set` : "optional"}</span><ChevronDown size={15} className={preferencesOpen ? "rotate" : ""} /></button>{((!clarification?.questions.length && (!result.advanced?.data.questions.length||result.advanced.data.questions.some(q=>['date','destination','origin'].includes(q.field)))) || loading) && <button type="submit" className="primary-button" disabled={loading || dataMode === "unavailable"} aria-busy={loading}>{loading ? planningStage === "Generating itinerary" ? "Planning…" : planningStage : result.requestFailed ? "Retry" : clarification||result.advanced?.data.questions.length ? "Continue planning" : (validated||result.advanced||generated&&dirty) ? "Regenerate plans" : "Plan my outing"} <ArrowRight size={18} /></button>}</div>
          {loading && <button type="button" className="secondary-button" onClick={cancelPlanning}>Cancel planning</button>}
          <div id="preferences" hidden={!preferencesOpen} className="preferences-panel">
            <div className="preferences-intro"><p>A few details to make it yours.</p><button type="button" onClick={() => { invalidateResults(); setPreferenceState(emptyPreferenceState()); setValidated(null); setAnswers({}); }}>Reset preferences</button></div>
            <div className="preferences-grid">
              <label><span><MapPin size={14} /> Location</span><input id="destination-preference" type="text" placeholder="City or location" value={preferences.location} maxLength={80} onChange={(e) => updatePreference("location", e.target.value)} /><small>{dataMode === "real" ? "Destination city/neighborhood; separate from your start" : "Fictional Baltimore venues only"}</small></label>
              <label><span><Footprints size={14} /> Travel mode</span><select aria-label="Travel mode" value={preferences.transport||"driving"} onChange={e=>updatePreference("transport",e.target.value)}><option value="driving">Driving</option><option value="walking">Walking</option></select><small>One mode for every journey. Driving is the default.</small></label>
              <OutingDateField allowNatural={!!clarification?.questions.some(q=>q.field==="date")||!!result.advanced?.data.questions.some(q=>q.field==="date")} real={dataMode === "real"} value={preferences.date} onChange={value => updatePreference("date", value)} />
              <label><span><Clock3 size={14} /> Maximum travel time</span><div className="input-with-unit"><input type="number" inputMode="numeric" min="0" max="1440" step="1" placeholder="No limit" value={preferences.travel} onChange={(e) => updatePreference("travel", e.target.value)} /><span>minutes</span></div><small>Total between stops; excludes getting there</small></label>
              {validated && <label className="activity-editor"><span>Activities in order</span><input aria-describedby="activity-edit-help" value={answers.activities ?? activityEditText(validated.request)} maxLength={500} onChange={e => { invalidateResults(); setAnswers(previous => ({ ...previous, activities: e.target.value })); }} /><small id="activity-edit-help">Separate stops with commas, including repeats. Use “dinner” to keep dinner timing. Up to four stops.</small></label>}
            </div><p className="preference-note">Values from your last request appear here. Only settings you change take priority over new text. Clear a field or reset to use your words. You can supply missing details in your request.</p>
          </div>
        {validated && <OutingSummary real={dataMode === "real"} value={validated} dirty={dirty} loading={loading} onEdit={() => { setPreferencesOpen(true); requestAnimationFrame(() => document.querySelector<HTMLInputElement>("#preferences input")?.focus()); }} />}
        {!loading && !!clarification?.questions.length && <div className="clarification-panel" ref={followupRef} aria-label="Outing follow-up">
          <p className="details-heading">A little more detail</p>
          <p>Add the missing details to keep planning. Your original request is kept.</p>
          {clarification.questions.filter(q=>q.field==='date'||q.field==='location').map(q=><p key={q.field}>{q.question} Use {q.field==='date'?'Date':'Location'} in preferences above.</p>)}

            <div className="preferences-grid">{clarification.questions.filter(q=>!(["date","location"] as string[]).includes(q.field)).map(question => <ClarificationField
              key={question.field} question={question} value={answers[question.field] ?? ""}
              onChange={value => setAnswers(previous => ({ ...previous, [question.field]: value }))} />)}</div>
            <div className="planner-actions"><button className="secondary-button" type="button" onClick={cancelClarification}>Cancel follow-up</button>
              <button className="primary-button" type="submit" disabled={loading} aria-busy={loading}>{result.requestFailed ? "Retry" : "Continue planning"}<ArrowRight size={18} /></button></div>
        </div>}
        {generated&&result.advanced&&<AdvancedClarifications state={result.advanced} busy={loading} nearOrigin={!!locationContext.startingLocation} onAnswer={answer=>void answerAdvanced(answer)}/>}
        {result.advanced&&optionsNotice&&result.advanced.data.questions.length>0&&<p role="alert">{optionsNotice}</p>}
        </form>
        {!loading && dataMode!=="unavailable" && !clarification?.questions.length && !result.requestFailed && (!generated||result.plans.length>0) && <p className="planner-disclaimer"><CircleHelp size={13} /> Not finding what you’re looking for? Try adjusting your preferences or searching again.</p>}
        <details className="catalog-help"><summary>Activities and data limitations</summary><p>Where To? can search for many kinds of outings using Google Places. Specific events, tickets, schedules and availability may require separate confirmation.</p><p hidden={dataMode === "real"}>Every outing needs a specific date. Mock event dates: {MOCK_EVENT_DATES.join(" and ")}. Pick a date in Set preferences or type YYYY-MM-DD, tomorrow, or a weekday. Weekend-only requests need a specific day. These are invented schedules, not real events or tickets.</p><p hidden={dataMode === "real"}>List up to four activities in the order you want. If a request is unclear, we will ask you to simplify it. Mock prices are per person; no capacity or booking is confirmed. Regular venues have no verified opening hours. Without a requested time, regular stops start at 10 AM (or later today); evening/night defaults to 6 PM. Dinner starts no earlier than 5 PM. Event start times are fixed. All mock times use Baltimore local time.</p>{dataMode === "real" && <p>List up to four stops, in order, including repeated activities. Every outing needs a date. Real event venues do not establish scheduled performances or movie showtimes. Prices, hours, durations and reservations need confirmation. Choose Driving or Walking in Set preferences; driving is the default. No budget is verified while prices are unknown.</p>}</details>
      </section>

      <section id="plans" className="plans-section shell" aria-labelledby="plans-title">
        <div className="section-heading"><div><p className="eyebrow">{savedOpen ? "YOUR SAVED PLAN" : generated ? "FROM GROUP CHAT TO GAME PLAN" : "A LITTLE INSPIRATION"}</p><h2 ref={resultsRef} tabIndex={-1} id="plans-title">{savedOpen ? "Your saved outing." : generated ? "Your next good time." : "Good plans look like this."}</h2><p role="status" aria-live="polite">{savedOpen ? "Your selected itinerary and original requirements." : loading ? planningStage + "…" : generated ? (result.plans.length ? resultsSummary(result.plans.length) : (clarification?.questions.length||result.advanced?.data.questions.length) ? "Answer the follow-up above to continue." : result.advancedUnavailable ? "Your requirements are kept. Advanced route planning is still being added." : "Adjust your request or preferences using the explanation below.") : "One request. Three ways to make a day of it."}</p></div><span className="sample-data-label"><span /> {savedOpen ? "Saved plan" : generated ? result.dataMode === "real" ? "Real venues" : "Sample results" : "Demo itineraries"}</span></div>
        <div id="saved-results" />
        <div hidden={savedOpen}>

        {generated && <BeyondPreferences result={result}/>}
        {generated&&result.advanced&&!result.plans.length&&!result.advanced.data.questions.length&&<p role='status'>{result.message}</p>}
        {(!loading || optionsBusy) && !clarification?.questions.length && result.plans.length ? <div className="plans-grid">{result.plans.map((plan, index) => <PlanCard key={`${generated}-${plan.id}-${plan.date}`} plan={plan} index={index} detailsSession={detailsSession} />)}</div> : !clarification?.questions.length && (!result.advanced || loading) && <PlanningFeedback stage={planningStage} loading={loading} needsClarification={!!clarification?.questions.length} advancedUnavailable={result.advancedUnavailable} failed={!!result.requestFailed} message={result.message} onRetry={() => { void runPlanning(!!clarification || !!validated); }} onEdit={() => requestRef.current?.focus()} />}
        {generated && pageState.count>0 && <ItineraryPagination index={pageState.index} count={pageState.count} busy={loading} onNavigate={direction=>{const page=pages.current.navigate(direction);if(page){setResult(restoreContinuation(page,latest.current));syncPages();}}}/>}
        {generated && (result.dataMode === "real" || result.optionsToken) && (result.plans.length > 0 || result.optionsToken || result.canExpand || result.canDiscover || result.canShowBeyond) && <AlternativeActions
          real={result.dataMode==="real"} canCombine={!!result.alternativeBatches?.length||!!result.canExpand} canExplore={!!result.canDiscover}
          busy={loading} disabled={dirty} notice={optionsBusy?planningStage+"…":continuationNotice(result,optionsNotice)}
          nearby={!!result.advanced||!!validated?.request.firstTravel} canShowBeyond={!!result.canShowBeyond||(pageState.hasBeyond&&(!result.advanced||!result.plans.length))}
          onBeyond={()=>{
            const saved=pages.current.pages.findLastIndex(page=>page.plans.some(plan=>plan.travelClassification==="beyond_limit"));
            if(saved>=0&&!result.plans.length){pages.current.index=saved;setResult(restoreContinuation(structuredClone(pages.current.pages[saved]),latest.current));syncPages();setOptionsNotice("");}
            else void showDifferent(false,true);
          }} onCompliant={()=>{
            const index=pages.current.pages.findLastIndex(page=>page.plans.every(plan=>plan.travelClassification!=="beyond_limit"));
            if(index>=0){pages.current.index=index;setResult(restoreContinuation(structuredClone(pages.current.pages[index]),latest.current));syncPages();}
            else {setResult(previous=>({...previous,plans:[],message:"No checked options fit your travel maximum yet. Search more nearby places or adjust the preference."}));setOptionsNotice("No within-limit options have been found yet. Your original limits are unchanged.");return;}
            setOptionsNotice("Showing options within your travel maximum. Your original limits are unchanged.");
          }} showingBeyond={result.plans.some(plan=>plan.travelClassification==="beyond_limit")}
          onAction={explore=>void showDifferent(explore,result.plans.some(plan=>plan.travelClassification==="beyond_limit"))} onAdjust={()=>startingControls.current?.editTravel()}/>}
        {generated&&recovery&&["outing_date_expired","outing_time_expired"].includes(recovery)&&<div role="group" aria-label="Outing date recovery"><p>Your activities, destination and confirmed origin are kept.</p><button type="button" className="secondary-button" onClick={()=>{setPreferencesOpen(true);requestAnimationFrame(()=>document.querySelector<HTMLInputElement>('input[type="date"]')?.focus());}}>Choose another date</button><p>No date is changed until you select one and regenerate. You can keep browsing saved pages.</p></div>}
        {generated&&["destination_unresolved","destination_ambiguous","destination_verification_unavailable"].includes(recovery??"")&&<div role="group" aria-label="Destination recovery"><p>{locationContext.planningMode==="surprise"?"Clarify the destination city or neighborhood. Surprise Me keeps its mode and does not invent a starting location.":"Your original destination is kept. A nearby reference prioritizes that area; it does not verify an exact neighborhood boundary."}</p>{locationContext.planningMode!=="surprise"&&<button type="button" className="secondary-button" onClick={()=>{startingControls.current?.useAnchor();void runPlanning(!!validated);}}>Use confirmed start as nearby search reference</button>}<button type="button" onClick={()=>setPreferencesOpen(true)}>Correct destination</button></div>}
        {!generated && <p className="sample-notice">These example itineraries use fictional venues, prices and travel times.</p>}
        {generated && result.plans.length > 0 && (!loading || optionsBusy) && <ResultsInformation advanced={!!result.advanced} real={result.dataMode === "real"} walking={result.plans.some(plan=>plan.transport==="walking")} notes={result.notes} needsChecking={result.plans.some(plan => plan.feasibility === "provisional")} />}
        </div>
        <SavedPlans contextKey={request+(result.saveReceipt??"")} active={savedOpen} onOpen={setSavedOpen} result={!savedOpen && generated && !dirty && !loading ? result : undefined} />
      </section>

      <section className="how-section shell" id="how-it-works" aria-labelledby="how-title"><div className="how-intro"><span className="tiny-spark"><Sparkles size={21} /></span><h2 id="how-title">Less back-and-forth.<br /><em>More “see you there.”</em></h2></div><div className="how-step"><span>01</span><h3>Give us the gist.</h3><p>Your people, your place, your idea of a good time.</p></div><div className="how-step"><span>02</span><h3>Find your kind of plan.</h3><p>Explore three options that bring it all together.</p></div><div className="how-step"><span>03</span><h3>Take it to the group chat.</h3><p>Pick a favorite. Check the real-world details. Go hang out.</p></div></section>


    </main>
    <nav className="shell" aria-label="Policies"><a href="/privacy" target="_blank" rel="noopener noreferrer">Privacy<span className="sr-only"> (opens in a new tab)</span></a> · <a href="/terms" target="_blank" rel="noopener noreferrer">Terms<span className="sr-only"> (opens in a new tab)</span></a></nav>
    <footer className="site-footer shell"><a href="#" className="brand footer-brand">where to<span className="brand-question">?</span></a><p className="growing-message">Where To? is still growing. We’re adding new features and improving the experience to help you plan better outings.</p><span>Made for getting together <span aria-hidden="true">↗</span></span></footer>
  </>;
}
