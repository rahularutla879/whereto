"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronDown, Clock3, Coffee, Footprints, MapPin, Palette, Popcorn, Settings2, Sparkles, Users, Utensils, Wine, CircleDollarSign, CircleHelp, CircleDot, X, Trophy, Music, Mic, Landmark, Theater, Laugh, Gamepad2, ShoppingBag, TreePine, Puzzle } from "lucide-react";
import { CardArtwork, HeroArtwork } from "@/components/artwork";
import { EXAMPLE_REQUEST, ACTIVITY_LABELS, MOCK_EVENT_DATES, SUPPORTED_ACTIVITIES, formatDuration, formatTime, type Activity, type CostPreference, type Plan, type PlannerResult } from "@/lib/planner";

import { emptyPreferenceState, editPreference, manualPreferences, displayInterpretedPreferences, type PreferenceField } from "@/lib/preferences";
import { PlanningSession } from "@/lib/planning-session";
import { generateOuting, type ValidatedOuting, type PendingOuting, type ClarificationAnswers } from "@/lib/planning-client";
import { ClarificationField } from "@/components/clarification-field";
import { OutingDateField } from "@/components/outing-date-field";
import { ResultsInformation } from "@/components/results-information";
import { planWarnings, resultsSummary } from "@/lib/results-presentation";
import { PlanningFeedback } from "@/components/planning-feedback";
import { OutingSummary, activityEditText } from "@/components/outing-summary";
import { LocationControls, type StartingLocationHandle } from "@/components/location-controls";
import { VenueDetails, GoogleCredits } from "@/components/venue-details";
import { VenueDetailsSession } from "@/lib/venue-details";
import type { LocationContext } from "@/lib/planning-client";
import { nextOptions, expandedOptions } from "@/lib/option-batches";
import { RealVenueFacts } from "@/components/real-venue-facts";
import { adaptRanking } from "@/lib/planning-client";
import { PlanCost } from "@/components/plan-cost";
import demoPlans from "@/data/demo-plans.json";

const activityIcons: Partial<Record<Activity, typeof Sparkles>> = { bowling: CircleDot, drinks: Wine, movie: Popcorn, food: Utensils, coffee: Coffee, outdoors: Footprints, art: Palette, museum: Landmark, karaoke: Mic, arcade: Gamepad2, escape: Puzzle, shopping: ShoppingBag,
  hiking: TreePine, picnic: TreePine, zoo: TreePine,
  baseball: Trophy, basketball: Trophy, football: Trophy, soccer: Trophy, hockey: Trophy, sports: Trophy,
  concert: Music, theater: Theater, musical: Theater, ballet: Theater, opera: Music, comedy: Laugh,
};
const activityLabels = ACTIVITY_LABELS;
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
      })}<small>Activity illustrations · not venue photos</small></div> : classic ? <CardArtwork theme={plan.theme} /> : <div className="activity-poster" aria-hidden="true"><PosterIcon size={62} strokeWidth={1.25} /><span>{activityLabels[plan.venues[0].activity]}</span></div>}
    </div>
    <div className="card-body">
      <p className="card-label">{plan.label}</p>
      <h3 className={real ? "real-plan-title" : undefined} title={plan.fullTitle}>{plan.title}</h3>
      <p className="card-description">{plan.description}</p>
      {warnings.length > 0 && <div className="plan-warning" role="note" aria-label="Important plan details"><strong>Before you choose</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="activity-route">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <span className="route-group" key={venue.id}><span className="activity"><Icon size={14} strokeWidth={1.7} />{activityLabels[venue.activity]}</span>{i < plan.venues.length - 1 && <ArrowRight size={12} className="route-arrow" />}</span>;
      })}</div>
      <div className="card-facts"><span><MapPin size={14} /> {plan.location ?? "Baltimore"}</span>{(!real || plan.duration !== null) && <span><Clock3 size={14} /> {plan.duration === null ? "Visit timing not verified" : `~${formatDuration(plan.duration)}`}</span>}</div>
      <div className="card-bottom">{!real && <div><PlanCost amount={plan.price} /><small>Sample price</small></div>}<button className="plan-link" aria-expanded={expanded} aria-controls={`details-${plan.id}`} onClick={() => setExpanded(!expanded)}>{expanded ? "Close plan" : "View plan"}{expanded ? <X size={16} /> : <ArrowUpRight size={18} />}</button></div>
      {real && <GoogleCredits credits={plan.venues.flatMap(venue => venue.evidenceLabels?.attribution?.third_party ?? []).filter((credit, i, credits) => credits.findIndex(c => c.provider === credit.provider && c.uri === credit.uri) === i)} />}
      <div hidden={!expanded} className="plan-details" id={`details-${plan.id}`}>
        <p className="details-heading">{real ? "Your provisional itinerary" : "Your sample itinerary"}</p>
        <p className="details-context">{plan.date.match(/^\d{4}-\d{2}-\d{2}$/) ? new Date(`${plan.date}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : plan.date} · {plan.people} {plan.people === 1 ? "person" : "people"}</p>
        <ol>{plan.stops.map(({ venue, start, end }, i) => <li key={venue.id}><span className="stop-number">{i + 1}</span><div><strong>{venue.name}</strong>{real ? <RealVenueFacts venue={venue} /> : <><span>{venue.kind === "event" ? `Sample event: ${venue.eventDate}` : "Fictional venue"} · {formatTime(start)}–{formatTime(end)}</span><span>{venue.neighborhood ?? "Neighborhood unknown"} · {formatDuration(venue.duration)}</span><span>{plan.prices[i]?.amount == null ? "Price not available" : `${money(plan.prices[i].amount)} per person (${plan.prices[i].status})`} · sample group limit: {venue.capacity ?? "Unknown"}</span></>}{i > 0 && <span>Travel from previous stop: {plan.legs[i - 1]?.minutes ?? "Unknown"} min ({real ? `${plan.routeEvidence?.[i - 1]?.route.mode ?? "drive"} estimate · Google Maps` : plan.legs[i - 1]?.status ?? "unknown"}).</span>}{real && <><VenueDetails venue={venue} token={plan.detailsToken} session={detailsSession} /><GoogleCredits credits={venue.evidenceLabels?.attribution?.third_party} /></>}</div></li>)}</ol>
        {!real && <div className="details-total"><span>Sample group total</span><PlanCost amount={plan.groupCost} group /></div>}
        <p className="details-note">~{plan.travel ?? "Unknown"} min of travel between stops. See About these estimates for what is included.</p>
        {real && plan.firstLeg && <p>From your starting point: {plan.firstLeg.minutes ?? "Unknown"} minutes (Google Maps estimate{plan.firstLeg.approximate ? " from the confirmed representative area point" : ""}), separate from inter-stop travel.</p>}
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
  const detailsSession = useRef(new VenueDetailsSession());
  useEffect(() => { let active = true; void fetch("/api/planning-mode", { cache: "no-store", signal: AbortSignal.timeout(5000) }).then(r => r.json()).then(value => { if (active && value.enabled && ["real", "mock"].includes(value.mode)) { setDataMode(value.mode); setLookupEnabled(value.startingLookupEnabled === true); } }).catch(() => {}); return () => { active = false; }; }, []);
  const [validated, setValidated] = useState<ValidatedOuting | null>(null);
  const [dirty, setDirty] = useState(false);
  const [request, setRequest] = useState("");
  const [preferenceState, setPreferenceState] = useState(emptyPreferenceState);
  const preferences = preferenceState.values;
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [result, setResult] = useState<PlannerResult>(demoPlans as PlannerResult);
  const [loading, setLoading] = useState(false);
  const session = useRef(new PlanningSession());
  const [clarification, setClarification] = useState<PendingOuting | null>(null);
  const [answers, setAnswers] = useState<ClarificationAnswers>({});
  const followupRef = useRef<HTMLDivElement>(null);
  const [generated, setGenerated] = useState(false);
  const resultsRef = useRef<HTMLHeadingElement>(null);
  const requestRef = useRef<HTMLTextAreaElement>(null);
  function updatePreference(key: PreferenceField, value: string) {
    invalidateResults();
    setPreferenceState(previous => editPreference(previous, key, value));
  }
  function invalidateResults() {
    startingControls.current?.cancel();
    session.current.cancel();
    detailsSession.current.clear();
    setLoading(false);
    setDirty(true);
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Details changed. Regenerate recommendations to use your corrections.", location: "", activities: [], notes: [] });
  }
  function replaceRequest() {
    cancelClarification();
    detailsSession.current.clear();
    setValidated(null);
    setDirty(false);
    setPreferenceState(previous => displayInterpretedPreferences(previous, emptyPreferenceState().values));
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Plan your new request to see recommendations.", location: "", activities: [], notes: [] });
  }
  function cancelClarification() {
    startingControls.current?.cancel();
    session.current.cancel();
    setLoading(false);
    setClarification(null);
    setAnswers({});
    setResult({ dataMode: dataMode === "real" ? "real" : "mock", plans: [], message: "Follow-up canceled. Edit your request or plan again.", location: "", activities: [], notes: [] });
  }
  const [optionsNotice, setOptionsNotice] = useState("");
  async function showDifferent(expandDiscovery = false) {
    if (!expandDiscovery && result.alternativeBatches?.length) { setResult(nextOptions); setOptionsNotice(""); return; }
    if (!result.optionsToken || !(expandDiscovery ? result.canDiscover : result.canExpand)) return;
    const controller = session.current.begin();
    if (!controller) return;
    setPlanningStage("Generating itinerary");
    setLoading(true); setOptionsNotice("Checking different combinations within this search…");
    try {
      const response = await fetch("/api/plans/options", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: result.optionsToken, expandDiscovery }), cache: "no-store", signal: controller.signal });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.message === "string" ? data.message : "More options are unavailable.");
      const next = adaptRanking(data);
      if (!session.current.current(controller)) return;
      if (next.plans.length) { setResult(previous => expandDiscovery ? expandedOptions(previous, next) : next); setOptionsNotice(""); }
      else { setResult(previous => ({ ...previous, canExpand: next.canExpand, canDiscover: next.canDiscover })); setOptionsNotice(next.message || "No more distinct options in the checked candidate pool."); }
    } catch (error) {
      if (session.current.current(controller)) { setResult(previous => ({ ...previous, canExpand: false, canDiscover: false })); setOptionsNotice(error instanceof Error ? error.message : "More options are unavailable. No automatic retry was made."); }
    } finally { if (session.current.finish(controller)) setLoading(false); }
  }
  async function runPlanning(followup: boolean) {
    const controller = session.current.begin();
    if (!controller) return;
    detailsSession.current.clear();
    setOptionsNotice("");
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
        signal: controller.signal, locationContext: dataMode === "real" ? origin : undefined,
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
  const preferencesCount = [preferences.location, preferences.date, preferences.people, preferences.budget, preferences.travel].filter(Boolean).length + (preferences.costExplicit || preferences.cost !== "balanced" ? 1 : 0);

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
          {dataMode === "real" && <LocationControls ref={startingControls} lookupEnabled={lookupEnabled} onStage={setPlanningStage} onChange={value => { invalidateResults(); setLocationContext(value); }} />}
          <div className="planner-actions"><button type="button" className="preferences-toggle" aria-expanded={preferencesOpen} aria-controls="preferences" onClick={() => setPreferencesOpen(!preferencesOpen)}><Settings2 size={16} /> Set preferences <span className="optional-label">{preferencesCount ? `${preferencesCount} set` : "optional"}</span><ChevronDown size={15} className={preferencesOpen ? "rotate" : ""} /></button><button type="submit" className="primary-button" disabled={loading || dataMode === "unavailable"} aria-busy={loading}>{loading ? planningStage === "Generating itinerary" ? "Planning…" : planningStage : result.requestFailed ? "Retry" : clarification ? "Continue planning" : validated ? "Regenerate plans" : "Plan my outing"} <ArrowRight size={18} /></button></div>
          <div id="preferences" hidden={!preferencesOpen} className="preferences-panel">
            <div className="preferences-intro"><p>A few details to make it yours.</p><button type="button" onClick={() => { invalidateResults(); setPreferenceState(emptyPreferenceState()); setValidated(null); setAnswers({}); }}>Reset preferences</button></div>
            <div className="preferences-grid">
              <label><span><MapPin size={14} /> Location</span><input type="text" placeholder="City or location" value={preferences.location} maxLength={80} onChange={(e) => updatePreference("location", e.target.value)} /><small>{dataMode === "real" ? "Destination city/neighborhood; separate from your start" : "Fictional Baltimore venues only"}</small></label>
              <OutingDateField real={dataMode === "real"} value={preferences.date} onChange={value => updatePreference("date", value)} />
              <label><span><Users size={14} /> Number of people</span><input type="number" inputMode="numeric" min="1" max="100" step="1" placeholder="e.g. 4" value={preferences.people} onChange={(e) => updatePreference("people", e.target.value)} /></label>
              <label><span><CircleDollarSign size={14} /> Maximum budget</span><div className="input-with-unit"><input type="number" inputMode="decimal" min="0" max="100000" step="0.01" placeholder="No limit" value={preferences.budget} onChange={(e) => updatePreference("budget", e.target.value)} /><span>$/person</span></div><small>{dataMode === "real" ? "Hard limit; compliance needs actual venue prices" : "Sample activities only; excludes extras"}</small></label>
              <label><span><Clock3 size={14} /> Maximum travel time</span><div className="input-with-unit"><input type="number" inputMode="numeric" min="0" max="1440" step="1" placeholder="No limit" value={preferences.travel} onChange={(e) => updatePreference("travel", e.target.value)} /><span>minutes</span></div><small>Total between stops; excludes getting there</small></label>
              <fieldset className="cost-field"><legend>Cost preference</legend><div className="cost-options">{([ ["budget", "Budget-friendly"], ["balanced", "Balanced"], ["experience", "Best experience"] ] as [CostPreference, string][]).map(([value, label]) => <label key={value} className={preferences.cost === value ? "selected" : ""}><input type="radio" name="cost" value={value} checked={preferences.cost === value} onClick={() => updatePreference("cost", value)} onChange={() => updatePreference("cost", value)} />{label}{preferences.cost === value && <Check size={12} />}</label>)}</div></fieldset>
              {validated && <label className="activity-editor"><span>Activities in order</span><input aria-describedby="activity-edit-help" value={answers.activities ?? activityEditText(validated.request)} maxLength={500} onChange={e => { invalidateResults(); setAnswers(previous => ({ ...previous, activities: e.target.value })); }} /><small id="activity-edit-help">Separate stops with commas, including repeats. Use “dinner” to keep dinner timing. Up to four stops.</small></label>}
            </div><p className="preference-note">Values from your last request appear here. Only settings you change take priority over new text. Clear a field or reset to use your words. You can supply missing details in your request.</p>
          </div>
        </form>
        {validated && <OutingSummary real={dataMode === "real"} value={validated} dirty={dirty} loading={loading} onEdit={() => { setPreferencesOpen(true); requestAnimationFrame(() => document.querySelector<HTMLInputElement>("#preferences input")?.focus()); }} />}
        {!loading && !!clarification?.questions.length && <div className="clarification-panel" ref={followupRef} aria-label="Outing follow-up">
          <p className="details-heading">A little more detail</p>
          <p>We’ve kept your original request and constraints. Edit your request above to correct it or plan a different outing.</p>
          {generated && <p role="status">{result.message}</p>}
          <form onSubmit={event => { event.preventDefault(); void runPlanning(true); }}>
            <div className="preferences-grid">{clarification.questions.map(question => <ClarificationField
              key={question.field} question={question} value={answers[question.field] ?? ""}
              onChange={value => setAnswers(previous => ({ ...previous, [question.field]: value }))} />)}</div>
            <div className="planner-actions"><button className="secondary-button" type="button" onClick={cancelClarification}>Cancel follow-up</button>
              <button className="primary-button" type="submit" disabled={loading} aria-busy={loading}>{result.requestFailed ? "Retry" : "Continue planning"}<ArrowRight size={18} /></button></div>
          </form>
        </div>}
        <p className="planner-disclaimer"><CircleHelp size={13} /> {dataMode === "real" ? "Real venues and route estimates. Prices, hours and availability require confirmation. No bookings." : "A preview of what’s possible. Local sample data, no live searches or bookings."}</p>
        <details className="catalog-help"><summary>Supported activities &amp; {dataMode === "real" ? "data limitations" : "fictional event dates"}</summary><p>{SUPPORTED_ACTIVITIES}.</p><p hidden={dataMode === "real"}>Every outing needs a specific date. Mock event dates: {MOCK_EVENT_DATES.join(" and ")}. Pick a date in Set preferences or type YYYY-MM-DD, tomorrow, or a weekday. Weekend-only requests need a specific day. These are invented schedules, not real events or tickets.</p><p hidden={dataMode === "real"}>List up to four activities in the order you want. If a request is unclear, we will ask you to simplify it. Group capacities are mock limits (4, 8, or 20 people); prices are per person. Regular venues have no verified opening hours. Without a requested time, regular stops start at 10 AM (or later today); evening/night defaults to 6 PM. Dinner starts no earlier than 5 PM. Event start times are fixed. All mock times use Baltimore local time.</p>{dataMode === "real" && <p>List up to four stops, in order, including repeated activities. Every outing needs a date. Real event venues do not establish scheduled performances or movie showtimes. Prices, hours, durations, group capacity and reservations need confirmation. Driving is used unless you request walking. No budget is verified while prices are unknown.</p>}</details>
      </section>

      <section id="plans" className="plans-section shell" aria-labelledby="plans-title">
        <div className="section-heading"><div><p className="eyebrow">{generated ? "FROM GROUP CHAT TO GAME PLAN" : "A LITTLE INSPIRATION"}</p><h2 ref={resultsRef} tabIndex={-1} id="plans-title">{generated ? "Your next good time." : "Good plans look like this."}</h2><p role="status" aria-live="polite">{loading ? planningStage + "…" : generated ? (result.plans.length ? resultsSummary(result.plans.length) : "Adjust your request or preferences using the explanation below.") : "One request. Three ways to make a day of it."}</p></div><span className="sample-data-label"><span /> {generated ? result.dataMode === "real" ? "Real venues · provisional" : "Sample results" : "Demo itineraries"}</span></div>
        {generated && !loading && <ResultsInformation real={result.dataMode === "real"} notes={result.notes} needsChecking={result.plans.some(plan => plan.feasibility === "provisional")} />}
        {!loading && !clarification?.questions.length && result.plans.length ? <div className="plans-grid">{result.plans.map((plan, index) => <PlanCard key={`${generated}-${plan.id}-${plan.people}-${plan.date}`} plan={plan} index={index} detailsSession={detailsSession.current} />)}</div> : <PlanningFeedback stage={planningStage} loading={loading} needsClarification={!!clarification?.questions.length} failed={!!result.requestFailed} message={result.message} onRetry={() => { void runPlanning(!!clarification || !!validated); }} onEdit={() => requestRef.current?.focus()} />}
        {generated && result.dataMode === "real" && (result.plans.length > 0 || result.canDiscover) && <div className="more-options"><button type="button" className="secondary-button" disabled={(!result.alternativeBatches?.length && !result.canExpand) || dirty || loading} onClick={() => { void showDifferent(); }}>Show different options</button>{result.canDiscover && <button type="button" className="secondary-button" disabled={dirty || loading} onClick={() => { void showDifferent(true); }}>Search for more venues</button>}<p role="status">{optionsNotice || (result.alternativeBatches?.length ? "Uses already checked combinations. No new provider requests." : result.canExpand ? "Checks unused combinations first; may calculate more routes within the same search budget." : "No more distinct options within this search coverage. Other venues may exist outside the checked pool.") }{result.canDiscover && " Search for more venues makes at most two additional same-area searches within this outing’s existing budget."}</p></div>}
        {!generated && <p className="sample-notice">All venues, events, schedules, capacities, prices, and travel times are fictional.</p>}
      </section>

      <section className="how-section shell" id="how-it-works" aria-labelledby="how-title"><div className="how-intro"><span className="tiny-spark"><Sparkles size={21} /></span><h2 id="how-title">Less back-and-forth.<br /><em>More “see you there.”</em></h2></div><div className="how-step"><span>01</span><h3>Give us the gist.</h3><p>Your people, your place, your idea of a good time.</p></div><div className="how-step"><span>02</span><h3>Find your kind of plan.</h3><p>Explore three options that bring it all together.</p></div><div className="how-step"><span>03</span><h3>Take it to the group chat.</h3><p>Pick a favorite. Check the real-world details. Go hang out.</p></div></section>

      <section id="about-demo" className="about-demo shell"><div><span className="status-dot" /><strong>A small demo. A big idea.</strong></div><p>Where To? is a first look at an AI-powered outing planner. This version uses local AI with fictional Baltimore venues by default. Deliberately enabled local real mode uses Google Maps venues and route estimates, with missing information clearly marked. It supports everyday outings, sports, concerts, and performances. Mock scheduled events require a matching fixture date; real event venues do not verify a session. Unclear or unsupported requests get an explanation. Live availability, verified prices, and bookings are not connected.</p><a href="#planner">Give it a go <ArrowDown size={14} /></a></section>
    </main>
    <nav className="shell" aria-label="Policies"><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></nav>
    <footer className="site-footer shell"><a href="#" className="brand footer-brand">where to<span className="brand-question">?</span></a><p>Good company. Great plans. Less effort.</p><span>Made for getting together <span aria-hidden="true">↗</span></span></footer>
  </>;
}
