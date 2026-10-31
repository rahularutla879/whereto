"use client";
import { DevelopmentDiagnostics } from "@/components/development-diagnostics";
import { SavedPlans } from "@/components/saved-plans";
import { ItineraryPagination } from "@/components/itinerary-pagination";
import { ItineraryPages, beyondPage, BEYOND_NOTICE } from "@/lib/itinerary-pages";

import { explorationStage } from "../components/exploration-notice";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, ChevronDown, Clock3, Coffee, Footprints, MapPin, Palette, Popcorn, Settings2, Sparkles, Utensils, Wine, CircleHelp, CircleDot, X, Trophy, Music, Mic, Landmark, Theater, Laugh, Gamepad2, ShoppingBag, TreePine, Puzzle } from "lucide-react";
import { CardArtwork, HeroArtwork } from "@/components/artwork";
import { EXAMPLE_REQUEST, MOCK_EVENT_DATES, activityLabel, formatDuration, formatTime, type Activity, type Plan, type PlannerResult } from "@/lib/planner";

import { emptyPreferenceState, editPreference, manualPreferences, displayInterpretedPreferences, type PreferenceField } from "@/lib/preferences";
import { PlanningSession } from "@/lib/planning-session";
import { AlternativeActions } from "@/components/alternative-actions";
import { SurpriseHistory } from "@/lib/surprise-history";
import { generateOuting, type ValidatedOuting, type PendingOuting, type ClarificationAnswers } from "@/lib/planning-client";
import { ClarificationField } from "@/components/clarification-field";
import { OutingDateField } from "@/components/outing-date-field";
import { ResultsInformation } from "@/components/results-information";
import { consumerMessage, planWarnings, resultsSummary } from "@/lib/results-presentation";
import { PlanningFeedback } from "@/components/planning-feedback";
import { OutingSummary, activityEditText } from "@/components/outing-summary";
import { LocationControls, type StartingLocationHandle } from "@/components/location-controls";
import { VenueDetails, GoogleCredits } from "@/components/venue-details";
import { VenueDetailsSession } from "@/lib/venue-details";
import type { LocationContext } from "@/lib/planning-client";
import { nextOptions } from "@/lib/option-batches";
import { RealVenueFacts } from "@/components/real-venue-facts";
import { adaptRanking } from "@/lib/planning-client";
import { PlanCost } from "@/components/plan-cost";
import { FirstLegTravel } from "@/components/first-leg-travel";
import demoPlans from "@/data/demo-plans.json";

const activityIcons: Partial<Record<Activity, typeof Sparkles>> = { bowling: CircleDot, drinks: Wine, movie: Popcorn, food: Utensils, coffee: Coffee, outdoors: Footprints, art: Palette, museum: Landmark, karaoke: Mic, arcade: Gamepad2, escape: Puzzle, shopping: ShoppingBag,
  hiking: TreePine, picnic: TreePine, zoo: TreePine,
  baseball: Trophy, basketball: Trophy, football: Trophy, soccer: Trophy, hockey: Trophy, sports: Trophy,
  concert: Music, theater: Theater, musical: Theater, ballet: Theater, opera: Music, comedy: Laugh,
};
const money = (amount: number | null) => amount === null ? "Unknown" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(amount);

function PlanCard({ plan, index, detailsSession }: { plan: Plan; index: number; detailsSession: VenueDetailsSession }) {
  const real = plan.dataMode === "real";
  const [expanded, setExpanded] = useState(false);
  const warnings = planWarnings(plan);
  const classic = plan.venues.map((venue) => venue.activity).join(",") === "bowling,drinks,movie";
  const PosterIcon = activityIcons[plan.venues[0].activity] ?? Sparkles;
  return <article className={`plan-card ${plan.theme}`}>
    <div className="card-visual">
      <span className="card-number">0{index + 1}</span><span className="demo-pill">{real ? "REAL VENUES · PROVISIONAL" : plan.feasibility === "preview" ? "DEMO PLAN" : "SAMPLE PLAN"}</span>
      {real ? <div className="real-route-poster" aria-hidden="true">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <div key={venue.id}><Icon size={22} strokeWidth={1.5} /><span>{i + 1}. {venue.name}</span></div>;
      })}<small>Activity illustrations · not venue photos</small></div> : classic ? <CardArtwork theme={plan.theme} /> : <div className="activity-poster" aria-hidden="true"><PosterIcon size={62} strokeWidth={1.25} /><span>{activityLabel(plan.venues[0].activity)}</span></div>}
    </div>
    <div className="card-body">
      <p className="card-label">{plan.label}</p>
      <h3 className={real ? "real-plan-title" : undefined} title={plan.fullTitle}>{plan.title}</h3>
      <p className="card-description">{plan.description}</p>
      {plan.planningMode==="surprise"&&<p className="details-note">Surprise Me · Begins at {plan.venues[0].name}. {plan.surpriseRepeated?"This first venue has appeared before; the complete combination is different.":"A varied first venue from the checked eligible pool."} No travel from your location is included.</p>}
      {plan.travelClassification && plan.travelClassification!=="matching" && <div className="plan-warning" role="note"><strong>{{outside_preference:"Outside your preferred range",beyond_limit:"Beyond your travel limit",unverified:"Requirements not fully verified"}[plan.travelClassification]}</strong><ul>{plan.travelDeviations?.map(message=><li key={message}>{message}</li>)}</ul></div>}
      {warnings.length > 0 && <div className="plan-warning" role="note" aria-label="Important plan details"><strong>Check this option</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="activity-route">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <span className="route-group" key={venue.id}><span className="activity"><Icon size={14} strokeWidth={1.7} />{activityLabel(venue.activity)}</span>{i < plan.venues.length - 1 && <ArrowRight size={12} className="route-arrow" />}</span>;
      })}</div>
      <div className="card-facts"><span><MapPin size={14} /> {real ? plan.venues.length===1 ? plan.venues[0].address ?? "Address unavailable" : `Search area: ${plan.location ?? "Not specified"}` : plan.location ?? "Baltimore"}</span>{(!real || plan.duration !== null) && <span><Clock3 size={14} /> {plan.duration === null ? "Visit timing not verified" : `~${formatDuration(plan.duration)}`}</span>}</div>
      {plan.firstLeg && <FirstLegTravel plan={plan} />}
      <div className="card-bottom">{!real && <div><PlanCost amount={plan.price} /><small>Sample price</small></div>}<button className="plan-link" aria-expanded={expanded} aria-controls={`details-${plan.id}`} onClick={() => setExpanded(!expanded)}>{expanded ? "Close plan" : "View plan"}{expanded ? <X size={16} /> : <ArrowUpRight size={18} />}</button></div>
      {real && <GoogleCredits credits={plan.venues.flatMap(venue => venue.evidenceLabels?.attribution?.third_party ?? []).filter((credit, i, credits) => credits.findIndex(c => c.provider === credit.provider && c.uri === credit.uri) === i)} />}
      <div hidden={!expanded} className="plan-details" id={`details-${plan.id}`}>
        <p className="details-heading">{real ? "Your provisional itinerary" : "Your sample itinerary"}</p>
        <p className="details-context">{plan.date.match(/^\d{4}-\d{2}-\d{2}$/) ? new Date(`${plan.date}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : plan.date}</p>
        <ol>{plan.stops.map(({ venue, start, end }, i) => <li key={venue.id}><span className="stop-number">{i + 1}</span><div><strong>{venue.name}</strong>{real ? <RealVenueFacts venue={venue} /> : <><span>{venue.kind === "event" ? `Sample event: ${venue.eventDate}` : "Fictional venue"} · {formatTime(start)}–{formatTime(end)}</span><span>{venue.neighborhood ?? "Neighborhood unknown"} · {formatDuration(venue.duration)}</span><span>{plan.prices[i]?.amount == null ? "Price not available" : `${money(plan.prices[i].amount)} per person (${plan.prices[i].status})`}</span></>}{i > 0 && <span>Travel from previous stop: {plan.legs[i - 1]?.minutes ?? "Unknown"} min ({real ? `${plan.routeEvidence?.[i - 1]?.route.mode ?? "drive"} estimate · Google Maps` : plan.legs[i - 1]?.status ?? "unknown"}).{real&&plan.routeEvidence?.[i-1]?.route.distance_meters!=null&&" / "+(plan.routeEvidence[i-1].route.distance_meters!/1609.344).toFixed(2)+" road miles"}</span>}{real && <><VenueDetails venue={venue} token={plan.detailsToken} session={detailsSession} /><GoogleCredits credits={venue.evidenceLabels?.attribution?.third_party} /></>}</div></li>)}</ol>
        {plan.stops.length>1&&<p className="details-note">{plan.travel===null?"Travel between stops unavailable":`~${plan.travel} min between stops`}. Return travel is not included.</p>}
      </div>
    </div>
  </article>;
}

export default function Home() {
  const [dataMode, setDataMode] = useState<"mock" | "real" | "unavailable">("unavailable");
  const startingControls = useRef<StartingLocationHandle>(null);
  const [lookupEnabled, setLookupEnabled] = useState(false);
  const [planningStage, setPlanningStage] = useState("Generating itinerary");
  const [locationContext, setLocationContext] = useState<LocationContext>({});
  const [detailsSession] = useState(()=>new VenueDetailsSession());
  useEffect(() => { let active = true; void fetch("/api/planning-mode", { cache: "no-store", signal: AbortSignal.timeout(5000) }).then(r => r.json()).then(value => { if (active && value.enabled && ["real", "mock"].includes(value.mode)) { setDataMode(value.mode); setLookupEnabled(value.startingLookupEnabled === true); } }).catch(() => {}); return () => { active = false; }; }, []);
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
    invalidateResults();
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
    if (!active.optionsToken || !(showBeyond ? active.canShowBeyond : expandDiscovery ? active.canDiscover : active.canExpand)) return;
    const controller = session.current.begin();
    if (!controller) return;
    setPlanningStage(explorationStage(expandDiscovery));
    setLoading(true); setOptionsBusy(true); setOptionsNotice("");setRecovery(undefined);
    try {
      const response = await fetch("/api/plans/options", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: active.optionsToken, expandDiscovery, showBeyond }), cache: "no-store", signal: controller.signal });
      const data = await response.json();
      if (!session.current.current(controller)) return;
      if (!response.ok) { setRecovery(data.code);if(Array.isArray(data.diagnosticNotes))setResult(previous=>({...previous,notes:[...previous.notes,...data.diagnosticNotes]}));if(data.resumable===true){setOptionsNotice(consumerMessage(data.message));return;}throw new Error(typeof data.message === "string" ? data.message : "More options are unavailable."); }
      const next = adaptRanking(data);
      if (!session.current.current(controller)) return;
      setRecovery(next.recoveryCode);
      if (next.plans.length) { latest.current=next;if(pages.current.append(next)){setResult(structuredClone(pages.current.pages[pages.current.index]));syncPages();setOptionsNotice("");}else setOptionsNotice("No new complete combinations were returned. Your saved pages are unchanged."); }
      else { latest.current={...active,canExpand:next.canExpand,canDiscover:next.canDiscover,canShowBeyond:next.canShowBeyond};setResult(previous => ({ ...previous, canExpand: next.canExpand, canDiscover: next.canDiscover, canShowBeyond:next.canShowBeyond })); setOptionsNotice(consumerMessage(next.message) || "No more distinct options in the checked candidate pool."); }
    } catch (error) {
      if (session.current.current(controller)) { latest.current={...active,canExpand:false,canDiscover:false};setResult(previous => ({ ...previous, canExpand: false, canDiscover: false })); setOptionsNotice(error instanceof Error ? consumerMessage(error.message) : "More options are unavailable. No automatic retry was made."); }
    } finally { if (session.current.finish(controller)) {setLoading(false);setOptionsBusy(false);} }
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
    const original = followup && clarification ? clarification.pending.text : request;
    try {
      let origin = locationContext;
      if (dataMode === "real" && origin.manualStartingPlace) {
        const confirmed = await startingControls.current?.prepare();
        if (!session.current.current(controller)) return;
        if (!confirmed) { setResult(previous => ({ ...previous, message: "Your starting place needs attention. Check the message by the starting-place field." })); return; }
        origin = confirmed; setLocationContext(confirmed);
      }
      setPlanningStage("Generating itinerary");
      const next = await generateOuting(original, manualPreferences(preferenceState), {
        continuation: followup ? clarification ?? validated?.continuation : undefined,
        answers: followup ? { ...answers, ...(answers.activities !== undefined ? { activities: answers.activities.trim() || "," } : {}) } : undefined,
        signal: controller.signal, locationContext: {...origin,locationFirst:true},
        prepareOrigin: async input => {
          const confirmed=await startingControls.current?.prepare(input);
          if (!session.current.current(controller)) return null;
          if (confirmed) setLocationContext(confirmed);
          return confirmed ? {...confirmed,...(confirmed.planningMode==="surprise"?{recentSurpriseIds:surpriseHistory.current.ids()}:{})} : null;
        },
        onValidated: value => { if (session.current.current(controller)) { setValidated(value); setClarification(null); setDirty(false); } },
        onInterpreted: values => { if (session.current.current(controller)) setPreferenceState(previous => displayInterpretedPreferences(previous, values)); },
        onClarification: value => {
          if (!session.current.current(controller)) return;
          needsAnswer = !!value?.questions.length;
          setClarification(value);
        },
        onComplete: () => { if (session.current.current(controller)) { setClarification(null); setAnswers({}); setPreferencesOpen(false); } },
      });
      if (!session.current.current(controller)) return;
      setRecovery(next.recoveryCode);
      latest.current=next;pages.current.append(next);syncPages();
      setResult({ ...next, dataMode: next.dataMode ?? (dataMode === "real" ? "real" : "mock") });
      setGenerated(true);
      requestAnimationFrame(() => {
        if (needsAnswer) followupRef.current?.querySelector("input")?.focus();
        else resultsRef.current?.focus({ preventScroll: false });
      });
    } finally {
      if (session.current.finish(controller)) setLoading(false);
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!request.trim()) { requestRef.current?.setCustomValidity("Tell us a little about your outing, or use the example."); requestRef.current?.reportValidity(); return; }
    await runPlanning(!!clarification || !!validated);
  }
  const preferencesCount = [preferences.location, preferences.date, preferences.travel].filter(Boolean).length;

  return <>
    <a className="skip-link" href="#planner">Skip to planner</a>
    <header className="site-header shell">
      <a href="#" className="brand" aria-label="Where To? Home"><span className="brand-icon"><MapPin size={20} strokeWidth={2.3} /></span>where to<span className="brand-question">?</span></a>
      <nav aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#about-demo" className="nav-demo">A little demo <span className="status-dot" /></a></nav>
    </header>

    <main>
      <section className="hero shell" aria-labelledby="hero-title">
        <div className="hero-copy"><p className="eyebrow"><span /> LESS GROUP CHAT. MORE GOOD TIMES.</p><h1 id="hero-title">Less planning.<br /><em>More hanging out.</em></h1><p className="hero-description">The best plans start with “what if we…”<br className="desktop-break" /> Tell us your vibe. We’ll put the outing together.</p><div className="hero-footnote"><span className="mini-avatars" aria-hidden="true"><span>R</span><span>J</span><span>M</span></span><span>For your people. And your kind of plans.</span></div></div>
        <div className="hero-art-wrap"><HeroArtwork /></div>
      </section>

      <section className="planner-section shell" id="planner" aria-labelledby="planner-title">
        <form className="planner" onSubmit={submit}>
          <div className="planner-topline"><h2 id="planner-title"><Sparkles size={19} /> What are we getting into?</h2><span className="local-badge">{dataMode === "real" ? "REAL DATA · LOCAL DEV" : dataMode === "mock" ? "MOCK DATA" : "MODE UNAVAILABLE"}</span></div>
          {dataMode === "unavailable" && <p role="status">Checking the planner connection. If this stays unavailable, start the backend and reload this page before planning.</p>}
          <label htmlFor="outing" className="sr-only">Describe your outing</label>
          <textarea id="outing" ref={requestRef} value={request} onChange={(event) => { replaceRequest(); setRequest(event.target.value); event.target.setCustomValidity(""); }} placeholder={EXAMPLE_REQUEST} maxLength={1200} required rows={3} />
          <div className="prompt-help"><span>Big ideas, loose plans, oddly specific cravings. All welcome.</span><button type="button" onClick={() => { replaceRequest(); setRequest(EXAMPLE_REQUEST); requestRef.current?.setCustomValidity(""); requestRef.current?.focus(); }}>Try an example <ArrowUpRight size={13} /></button></div>
          {<LocationControls mock={dataMode!=="real"} ref={startingControls} lookupEnabled={lookupEnabled} onStage={setPlanningStage} onChange={(value,preparing) => { if(!preparing)invalidateResults(); setLocationContext(value); }} />}
          <div className="planner-actions"><button type="button" className="preferences-toggle" aria-expanded={preferencesOpen} aria-controls="preferences" onClick={() => setPreferencesOpen(!preferencesOpen)}><Settings2 size={16} /> Set preferences <span className="optional-label">{preferencesCount ? `${preferencesCount} set` : "optional"}</span><ChevronDown size={15} className={preferencesOpen ? "rotate" : ""} /></button><button type="submit" className="primary-button" disabled={loading || dataMode === "unavailable"} aria-busy={loading}>{loading ? planningStage === "Generating itinerary" ? "Planning…" : planningStage : result.requestFailed ? "Retry" : clarification ? "Continue planning" : validated ? "Regenerate plans" : "Plan my outing"} <ArrowRight size={18} /></button></div>
          {loading && <button type="button" className="secondary-button" onClick={cancelPlanning}>Cancel planning</button>}
          <div id="preferences" hidden={!preferencesOpen} className="preferences-panel">
            <div className="preferences-intro"><p>A few details to make it yours.</p><button type="button" onClick={() => { invalidateResults(); setPreferenceState(emptyPreferenceState()); setValidated(null); setAnswers({}); }}>Reset preferences</button></div>
            <div className="preferences-grid">
              <label><span><MapPin size={14} /> Location</span><input type="text" placeholder="City or location" value={preferences.location} maxLength={80} onChange={(e) => updatePreference("location", e.target.value)} /><small>{dataMode === "real" ? "Destination city/neighborhood; separate from your start" : "Fictional Baltimore venues only"}</small></label>
              <OutingDateField real={dataMode === "real"} value={preferences.date} onChange={value => updatePreference("date", value)} />
              <label><span><Clock3 size={14} /> Maximum travel time</span><div className="input-with-unit"><input type="number" inputMode="numeric" min="0" max="1440" step="1" placeholder="No limit" value={preferences.travel} onChange={(e) => updatePreference("travel", e.target.value)} /><span>minutes</span></div><small>Total between stops; excludes getting there</small></label>
              {validated && <label className="activity-editor"><span>Activities in order</span><input aria-describedby="activity-edit-help" value={answers.activities ?? activityEditText(validated.request)} maxLength={500} onChange={e => { invalidateResults(); setAnswers(previous => ({ ...previous, activities: e.target.value })); }} /><small id="activity-edit-help">Separate stops with commas, including repeats. Use “dinner” to keep dinner timing. Up to four stops.</small></label>}
            </div><p className="preference-note">Values from your last request appear here. Only settings you change take priority over new text. Clear a field or reset to use your words. You can supply missing details in your request.</p>
          </div>
        </form>
        {validated && <OutingSummary real={dataMode === "real"} value={validated} dirty={dirty} loading={loading} onEdit={() => { setPreferencesOpen(true); requestAnimationFrame(() => document.querySelector<HTMLInputElement>("#preferences input")?.focus()); }} />}
        {!loading && !!clarification?.questions.length && <div className="clarification-panel" ref={followupRef} aria-label="Outing follow-up">
          <p className="details-heading">A little more detail</p>
          <p>We’ve kept your original request and constraints. Edit your request above to correct it or plan a different outing.</p>
          {generated && <p role="status">{consumerMessage(result.message)}</p>}
          <form onSubmit={event => { event.preventDefault(); void runPlanning(true); }}>
            <div className="preferences-grid">{clarification.questions.map(question => <ClarificationField
              key={question.field} question={question} value={answers[question.field] ?? ""}
              onChange={value => setAnswers(previous => ({ ...previous, [question.field]: value }))} />)}</div>
            <div className="planner-actions"><button className="secondary-button" type="button" onClick={cancelClarification}>Cancel follow-up</button>
              <button className="primary-button" type="submit" disabled={loading} aria-busy={loading}>{result.requestFailed ? "Retry" : "Continue planning"}<ArrowRight size={18} /></button></div>
          </form>
        </div>}
        <p className="planner-disclaimer"><CircleHelp size={13} /> {dataMode === "real" ? "Real venue discovery · Google Maps." : "A preview of what’s possible. Local sample data, no live searches or bookings."}</p>
        <details className="catalog-help"><summary>Activities and data limitations</summary><p>Where To? can search for many kinds of outings using Google Places. Specific events, tickets, schedules and availability may require separate confirmation.</p><p hidden={dataMode === "real"}>Every outing needs a specific date. Mock event dates: {MOCK_EVENT_DATES.join(" and ")}. Pick a date in Set preferences or type YYYY-MM-DD, tomorrow, or a weekday. Weekend-only requests need a specific day. These are invented schedules, not real events or tickets.</p><p hidden={dataMode === "real"}>List up to four activities in the order you want. If a request is unclear, we will ask you to simplify it. Mock prices are per person; no capacity or booking is confirmed. Regular venues have no verified opening hours. Without a requested time, regular stops start at 10 AM (or later today); evening/night defaults to 6 PM. Dinner starts no earlier than 5 PM. Event start times are fixed. All mock times use Baltimore local time.</p>{dataMode === "real" && <p>List up to four stops, in order, including repeated activities. Every outing needs a date. Real event venues do not establish scheduled performances or movie showtimes. Prices, hours, durations and reservations need confirmation. Driving is used unless you request walking. No budget is verified while prices are unknown.</p>}</details>
      </section>

      <section id="plans" className="plans-section shell" aria-labelledby="plans-title">
        <div className="section-heading"><div><p className="eyebrow">{savedOpen ? "YOUR SAVED PLAN" : generated ? "FROM GROUP CHAT TO GAME PLAN" : "A LITTLE INSPIRATION"}</p><h2 ref={resultsRef} tabIndex={-1} id="plans-title">{savedOpen ? "Your saved outing." : generated ? "Your next good time." : "Good plans look like this."}</h2><p role="status" aria-live="polite">{savedOpen ? "Your original options and selection." : loading ? planningStage + "…" : generated ? (result.plans.length ? resultsSummary(result.plans.length) : "Adjust your request or preferences using the explanation below.") : "One request. Three ways to make a day of it."}</p></div><span className="sample-data-label"><span /> {savedOpen ? "Saved plan" : generated ? result.dataMode === "real" ? "Real venues · provisional" : "Sample results" : "Demo itineraries"}</span></div>
        <div id="saved-results" />
        <div hidden={savedOpen}>

        {generated && result.plans.length>0 && beyondPage(result) && <div className="plan-warning" role="note"><h3>Explore beyond your preferences</h3><p>{BEYOND_NOTICE}</p><p>These additional outings go beyond one or more of your travel preferences. We've included them so you can discover more places.</p></div>}
        {(!loading || optionsBusy) && !clarification?.questions.length && result.plans.length ? <div className="plans-grid">{result.plans.map((plan, index) => <PlanCard key={`${generated}-${plan.id}-${plan.date}`} plan={plan} index={index} detailsSession={detailsSession} />)}</div> : <PlanningFeedback stage={planningStage} loading={loading} needsClarification={!!clarification?.questions.length} failed={!!result.requestFailed} message={result.message} onRetry={() => { void runPlanning(!!clarification || !!validated); }} onEdit={() => requestRef.current?.focus()} />}
        {generated && pageState.count>0 && <ItineraryPagination index={pageState.index} count={pageState.count} busy={loading} onNavigate={direction=>{const page=pages.current.navigate(direction);if(page){setResult({...page,canExpand:latest.current.canExpand,canDiscover:latest.current.canDiscover,canShowBeyond:latest.current.canShowBeyond});syncPages();}}}/>}
        {generated && (result.dataMode === "real" || result.optionsToken) && (result.plans.length > 0 || result.canExpand || result.canDiscover || result.canShowBeyond) && <AlternativeActions
          real={result.dataMode==="real"} canCombine={!!result.alternativeBatches?.length||!!result.canExpand} canExplore={!!result.canDiscover}
          busy={loading} disabled={dirty} notice={optionsBusy?planningStage+"…":optionsNotice||(!result.canExpand&&!result.canDiscover?"No more options found in this search. Other suitable places may exist.":"")}
          nearby={!!validated?.request.firstTravel} canShowBeyond={!!result.canShowBeyond||pageState.hasBeyond}
          onBeyond={()=>{
            const saved=pages.current.pages.findLastIndex(page=>page.plans.some(plan=>plan.travelClassification==="beyond_limit"));
            if(saved>=0&&!result.plans.length){pages.current.index=saved;setResult(structuredClone(pages.current.pages[saved]));syncPages();setOptionsNotice("");}
            else void showDifferent(false,true);
          }} onCompliant={()=>{
            const index=pages.current.pages.findLastIndex(page=>page.plans.every(plan=>plan.travelClassification!=="beyond_limit"));
            if(index>=0){pages.current.index=index;setResult(structuredClone(pages.current.pages[index]));syncPages();}
            else setResult(previous=>({...previous,plans:[],message:"Search more nearby places to verify an outing within your limit."}));
            setOptionsNotice("Showing options within your travel maximum. Your original limits are unchanged.");
          }} showingBeyond={result.plans.some(plan=>plan.travelClassification==="beyond_limit")}
          onAction={explore=>void showDifferent(explore,result.plans.some(plan=>plan.travelClassification==="beyond_limit"))} onAdjust={()=>startingControls.current?.editTravel()}/>}
        {generated&&recovery&&["outing_date_expired","outing_time_expired"].includes(recovery)&&<div role="group" aria-label="Outing date recovery"><p>{optionsNotice||result.message} Your activities, destination and confirmed origin are kept.</p><button type="button" className="secondary-button" onClick={()=>{setPreferencesOpen(true);requestAnimationFrame(()=>document.querySelector<HTMLInputElement>('input[type="date"]')?.focus());}}>Choose another date</button><p>No date is changed until you select one and regenerate. You can keep browsing saved pages.</p></div>}
        {generated&&["destination_unresolved","destination_ambiguous","destination_verification_unavailable"].includes(recovery??"")&&<div role="group" aria-label="Destination recovery"><p>{locationContext.planningMode==="surprise"?"Clarify the destination city or neighborhood. Surprise Me keeps its mode and does not invent a starting location.":"Your original destination is kept. A nearby reference prioritizes that area; it does not verify an exact neighborhood boundary."}</p>{locationContext.planningMode!=="surprise"&&<button type="button" className="secondary-button" onClick={()=>{startingControls.current?.useAnchor();void runPlanning(!!validated);}}>Use confirmed start as nearby search reference</button>}<button type="button" onClick={()=>setPreferencesOpen(true)}>Correct destination</button></div>}
        {!generated && <p className="sample-notice">All venues, events, schedules, capacities, prices, and travel times are fictional.</p>}
        {generated && (!loading || optionsBusy) && <ResultsInformation real={result.dataMode === "real"} notes={result.notes} needsChecking={result.plans.some(plan => plan.feasibility === "provisional")} />}
        </div>
        <SavedPlans contextKey={request+(result.saveReceipt??"")} active={savedOpen} onOpen={setSavedOpen} result={!savedOpen && generated && !dirty && !loading ? result : undefined} />
        <DevelopmentDiagnostics />
      </section>

      <section className="how-section shell" id="how-it-works" aria-labelledby="how-title"><div className="how-intro"><span className="tiny-spark"><Sparkles size={21} /></span><h2 id="how-title">Less back-and-forth.<br /><em>More “see you there.”</em></h2></div><div className="how-step"><span>01</span><h3>Give us the gist.</h3><p>Your people, your place, your idea of a good time.</p></div><div className="how-step"><span>02</span><h3>Find your kind of plan.</h3><p>Explore three options that bring it all together.</p></div><div className="how-step"><span>03</span><h3>Take it to the group chat.</h3><p>Pick a favorite. Check the real-world details. Go hang out.</p></div></section>

      <section id="about-demo" className="about-demo shell"><div><span className="status-dot" /><strong>A small demo. A big idea.</strong></div><p>Where To? is a first look at an AI-powered outing planner. This version uses local AI with fictional Baltimore venues by default. Deliberately enabled local real mode uses Google Maps venues and route estimates, with missing information clearly marked. It supports everyday outings, sports, concerts, and performances. Mock scheduled events require a matching fixture date; real event venues do not verify a session. Unclear or unsupported requests get an explanation. Live availability, verified prices, and bookings are not connected.</p><a href="#planner">Give it a go <ArrowDown size={14} /></a></section>
    </main>
    <nav className="shell" aria-label="Policies"><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></nav>
    <footer className="site-footer shell"><a href="#" className="brand footer-brand">where to<span className="brand-question">?</span></a><p>Good company. Great plans. Less effort.</p><span>Made for getting together <span aria-hidden="true">↗</span></span></footer>
  </>;
}
