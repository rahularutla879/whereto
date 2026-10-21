"use client";

import { useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowRight, ArrowUpRight, CalendarDays, Check, ChevronDown, Clock3, Coffee, Footprints, MapPin, Palette, Popcorn, Settings2, Sparkles, Users, Utensils, Wine, CircleDollarSign, CircleHelp, CircleDot, X, Trophy, Music, Mic, Landmark, Theater, Laugh, Gamepad2, ShoppingBag, TreePine, Puzzle } from "lucide-react";
import { CardArtwork, HeroArtwork } from "@/components/artwork";
import { EXAMPLE_REQUEST, ACTIVITY_LABELS, MOCK_EVENT_DATES, SUPPORTED_ACTIVITIES, formatDuration, formatTime, type Activity, type CostPreference, type Plan, type PlannerResult } from "@/lib/planner";

import { emptyPreferenceState, editPreference, manualPreferences, displayInterpretedPreferences, type PreferenceField } from "@/lib/preferences";
import { PlanningSession } from "@/lib/planning-session";
import { generateOuting, type PendingOuting, type ClarificationAnswers } from "@/lib/planning-client";
import { ResultsInformation } from "@/components/results-information";
import { failureMessage, planWarnings, resultsSummary } from "@/lib/results-presentation";
import demoPlans from "@/data/demo-plans.json";

const activityIcons: Partial<Record<Activity, typeof Sparkles>> = { bowling: CircleDot, drinks: Wine, movie: Popcorn, food: Utensils, coffee: Coffee, outdoors: Footprints, art: Palette, museum: Landmark, karaoke: Mic, arcade: Gamepad2, escape: Puzzle, shopping: ShoppingBag,
  hiking: TreePine, picnic: TreePine, zoo: TreePine,
  baseball: Trophy, basketball: Trophy, football: Trophy, soccer: Trophy, hockey: Trophy, sports: Trophy,
  concert: Music, theater: Theater, musical: Theater, ballet: Theater, opera: Music, comedy: Laugh,
};
const activityLabels = ACTIVITY_LABELS;
const money = (amount: number | null) => amount === null ? "Unknown" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(amount);

function PlanCard({ plan, index }: { plan: Plan; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const warnings = planWarnings(plan);
  const classic = plan.venues.map((venue) => venue.activity).join(",") === "bowling,drinks,movie";
  const PosterIcon = activityIcons[plan.venues[0].activity] ?? Sparkles;
  return <article className={`plan-card ${plan.theme}`}>
    <div className="card-visual">
      <span className="card-number">0{index + 1}</span><span className="demo-pill">{plan.feasibility === "preview" ? "DEMO PLAN" : "SAMPLE PLAN"}</span>
      {classic ? <CardArtwork theme={plan.theme} /> : <div className="activity-poster" aria-hidden="true"><PosterIcon size={62} strokeWidth={1.25} /><span>{activityLabels[plan.venues[0].activity]}</span></div>}
    </div>
    <div className="card-body">
      <p className="card-label">{plan.label}</p>
      <h3>{plan.title}</h3>
      <p className="card-description">{plan.description}</p>
      {warnings.length > 0 && <div className="plan-warning" role="note" aria-label="Important plan details"><strong>Before you choose</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="activity-route">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <span className="route-group" key={venue.id}><span className="activity"><Icon size={14} strokeWidth={1.7} />{activityLabels[venue.activity]}</span>{i < plan.venues.length - 1 && <ArrowRight size={12} className="route-arrow" />}</span>;
      })}</div>
      <div className="card-facts"><span><MapPin size={14} /> Baltimore</span><span><Clock3 size={14} /> ~{formatDuration(plan.duration)}</span></div>
      <div className="card-bottom"><div><strong>~{money(plan.price)}</strong><span> / person</span><small>Sample price</small></div><button className="plan-link" aria-expanded={expanded} aria-controls={`details-${plan.id}`} onClick={() => setExpanded(!expanded)}>{expanded ? "Close plan" : "View plan"}{expanded ? <X size={16} /> : <ArrowUpRight size={18} />}</button></div>
      {expanded && <div className="plan-details" id={`details-${plan.id}`}>
        <p className="details-heading">Your sample itinerary</p>
        <p className="details-context">{plan.date.match(/^\d{4}-\d{2}-\d{2}$/) ? new Date(`${plan.date}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : plan.date} · {plan.people} {plan.people === 1 ? "person" : "people"}</p>
        <ol>{plan.stops.map(({ venue, start, end }, i) => <li key={venue.id}><span className="stop-number">{i + 1}</span><div><strong>{venue.name}</strong><span>{venue.kind === "event" ? `Sample event: ${venue.eventDate}` : "Fictional venue"} · {formatTime(start)}–{formatTime(end)}</span><span>{venue.neighborhood ?? "Neighborhood unknown"} · {formatDuration(venue.duration)}</span><span>{money(plan.prices[i]?.amount ?? null)} per person ({plan.prices[i]?.status ?? "unknown"}) · sample group limit: {venue.capacity ?? "Unknown"}</span>{i > 0 && <span>Travel from previous stop: {plan.legs[i - 1]?.minutes ?? "Unknown"} min ({plan.legs[i - 1]?.status ?? "unknown"}).</span>}</div></li>)}</ol>
        <div className="details-total"><span>Sample group total</span><strong>~{money(plan.groupCost)}</strong></div>
        <p className="details-note">~{plan.travel ?? "Unknown"} min of travel between stops. See About these estimates for what is included.</p>
      </div>}
    </div>
  </article>;
}

export default function Home() {
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
    setPreferenceState(previous => editPreference(previous, key, value));
  }
  function cancelClarification() {
    session.current.cancel();
    setLoading(false);
    setClarification(null);
    setAnswers({});
  }
  async function runPlanning(followup: boolean) {
    const controller = session.current.begin();
    if (!controller) return;
    setLoading(true);
    let needsAnswer = false;
    const original = followup && clarification ? clarification.pending.text : request;
    try {
      const next = await generateOuting(original, manualPreferences(preferenceState), {
        continuation: followup ? clarification ?? undefined : undefined,
        answers: followup ? answers : undefined,
        signal: controller.signal,
        onInterpreted: values => { if (session.current.current(controller)) setPreferenceState(previous => displayInterpretedPreferences(previous, values)); },
        onClarification: value => {
          if (!session.current.current(controller)) return;
          needsAnswer = !!value?.questions.length;
          setClarification(value);
        },
        onComplete: () => { if (session.current.current(controller)) { setClarification(null); setAnswers({}); } },
      });
      if (!session.current.current(controller)) return;
      setResult(next);
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
    await runPlanning(!!clarification);
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
          <div className="planner-topline"><h2 id="planner-title"><Sparkles size={19} /> What are we getting into?</h2><span className="local-badge">LOCAL DEMO</span></div>
          <label htmlFor="outing" className="sr-only">Describe your outing</label>
          <textarea id="outing" ref={requestRef} value={request} onChange={(event) => { cancelClarification(); setRequest(event.target.value); event.target.setCustomValidity(""); }} placeholder={EXAMPLE_REQUEST} maxLength={1200} required rows={3} />
          <div className="prompt-help"><span>Big ideas, loose plans, oddly specific cravings. All welcome.</span><button type="button" onClick={() => { cancelClarification(); setRequest(EXAMPLE_REQUEST); requestRef.current?.setCustomValidity(""); requestRef.current?.focus(); }}>Try an example <ArrowUpRight size={13} /></button></div>
          <div className="planner-actions"><button type="button" className="preferences-toggle" aria-expanded={preferencesOpen} aria-controls="preferences" onClick={() => setPreferencesOpen(!preferencesOpen)}><Settings2 size={16} /> Set preferences <span className="optional-label">{preferencesCount ? `${preferencesCount} set` : "optional"}</span><ChevronDown size={15} className={preferencesOpen ? "rotate" : ""} /></button><button type="submit" className="primary-button" disabled={loading} aria-busy={loading}>{loading ? "Planning…" : clarification ? "Continue planning" : "Plan my outing"} <ArrowRight size={18} /></button></div>
          <div id="preferences" hidden={!preferencesOpen} className="preferences-panel">
            <div className="preferences-intro"><p>A few details to make it yours.</p><button type="button" onClick={() => setPreferenceState(emptyPreferenceState())}>Reset preferences</button></div>
            <div className="preferences-grid">
              <label><span><MapPin size={14} /> Location</span><input type="text" placeholder="City or location" value={preferences.location} maxLength={80} onChange={(e) => updatePreference("location", e.target.value)} /><small>Fictional Baltimore venues only</small></label>
              <label><span><CalendarDays size={14} /> Date</span><input type="date" value={preferences.date} onChange={(e) => updatePreference("date", e.target.value)} /><small>Every outing needs a date; event schedules are fictional</small></label>
              <label><span><Users size={14} /> Number of people</span><input type="number" inputMode="numeric" min="1" max="100" step="1" placeholder="e.g. 4" value={preferences.people} onChange={(e) => updatePreference("people", e.target.value)} /></label>
              <label><span><CircleDollarSign size={14} /> Maximum budget</span><div className="input-with-unit"><input type="number" inputMode="decimal" min="0" max="100000" step="0.01" placeholder="No limit" value={preferences.budget} onChange={(e) => updatePreference("budget", e.target.value)} /><span>$/person</span></div><small>Sample activities only; excludes extras</small></label>
              <label><span><Clock3 size={14} /> Maximum travel time</span><div className="input-with-unit"><input type="number" inputMode="numeric" min="0" max="1440" step="1" placeholder="No limit" value={preferences.travel} onChange={(e) => updatePreference("travel", e.target.value)} /><span>minutes</span></div><small>Total between stops; excludes getting there</small></label>
              <fieldset className="cost-field"><legend>Cost preference</legend><div className="cost-options">{([ ["budget", "Budget-friendly"], ["balanced", "Balanced"], ["experience", "Best experience"] ] as [CostPreference, string][]).map(([value, label]) => <label key={value} className={preferences.cost === value ? "selected" : ""}><input type="radio" name="cost" value={value} checked={preferences.cost === value} onClick={() => updatePreference("cost", value)} onChange={() => updatePreference("cost", value)} />{label}{preferences.cost === value && <Check size={12} />}</label>)}</div></fieldset>
            </div><p className="preference-note">Values from your last request appear here. Only settings you change take priority over new text. Clear a field or reset to use your words. You can supply missing details in your request.</p>
          </div>
        </form>
        {clarification && <div className="clarification-panel" ref={followupRef} aria-label="Outing follow-up">
          <p className="details-heading">{clarification.questions.length ? "A little more detail" : "Your request is ready to retry"}</p>
          <p>We’ve kept your original request and constraints. Edit your request above to correct it or plan a different outing.</p>
          {generated && <p role="status">{result.message}</p>}
          <form onSubmit={event => { event.preventDefault(); void runPlanning(true); }}>
            <div className="preferences-grid">{clarification.questions.map(question => <label key={question.field}>
              <span>{question.question}</span>
              <input aria-label={question.question} type="text" maxLength={question.field === "activities" ? 500 : question.field === "time" ? 150 : 80}
                value={answers[question.field] ?? ""} placeholder={question.field === "location" ? "City or location" : question.field === "people" ? "e.g. 4" : question.field === "date" ? "e.g. 2026-11-07 or Saturday" : question.field === "activities" ? "e.g. coffee, museum, then coffee" : "e.g. from 6 PM to 10 PM"}
                onChange={event => setAnswers(previous => ({ ...previous, [question.field]: event.target.value }))} />
            </label>)}</div>
            <div className="planner-actions"><button className="secondary-button" type="button" onClick={cancelClarification}>Cancel follow-up</button>
              <button className="primary-button" type="submit" disabled={loading} aria-busy={loading}>{loading ? "Planning…" : "Continue planning"}<ArrowRight size={18} /></button></div>
          </form>
        </div>}
        <p className="planner-disclaimer"><CircleHelp size={13} /> A preview of what’s possible. Local sample data, no live searches or bookings.</p>
        <details className="catalog-help"><summary>Supported activities &amp; fictional event dates</summary><p>{SUPPORTED_ACTIVITIES}.</p><p>Every outing needs a specific date. Mock event dates: {MOCK_EVENT_DATES.join(" and ")}. Pick a date in Set preferences or type YYYY-MM-DD, tomorrow, or a weekday. Weekend-only requests need a specific day. These are invented schedules, not real events or tickets.</p><p>List up to four activities in the order you want. If a request is unclear, we will ask you to simplify it. Group capacities are mock limits (4, 8, or 20 people); prices are per person. Regular venues have no verified opening hours. Without a requested time, regular stops start at 10 AM (or later today); evening/night defaults to 6 PM. Dinner starts no earlier than 5 PM. Event start times are fixed. All mock times use Baltimore local time.</p></details>
      </section>

      <section id="plans" className="plans-section shell" aria-labelledby="plans-title">
        <div className="section-heading"><div><p className="eyebrow">{generated ? "FROM GROUP CHAT TO GAME PLAN" : "A LITTLE INSPIRATION"}</p><h2 ref={resultsRef} tabIndex={-1} id="plans-title">{generated ? "Your next good time." : "Good plans look like this."}</h2><p role="status" aria-live="polite">{loading ? "Finding possible plans…" : generated ? (result.plans.length ? resultsSummary(result.plans.length) : "Adjust your request or preferences using the explanation below.") : "One request. Three ways to make a day of it."}</p></div><span className="sample-data-label"><span /> {generated ? "Sample results" : "Demo itineraries"}</span></div>
        {generated && <ResultsInformation notes={result.notes} needsChecking={result.plans.some(plan => plan.feasibility === "provisional")} />}
        {clarification?.questions.length ? <div className="empty-state" role="status"><CircleHelp size={28} /><h3>Just a little more detail.</h3><p>Answer the questions below your request to continue. Your original details are kept.</p></div> : result.plans.length ? <div className="plans-grid">{result.plans.map((plan, index) => <PlanCard key={`${generated}-${plan.id}-${plan.people}-${plan.date}`} plan={plan} index={index} />)}</div> : <div className="empty-state"><MapPin size={28} /><h3>Let’s tweak the plan.</h3><p>{failureMessage(result.message)}</p><button type="button" className="secondary-button" onClick={() => requestRef.current?.focus()}>Edit your request <ArrowUpRight size={16} /></button></div>}
        {!generated && <p className="sample-notice">All venues, events, schedules, capacities, prices, and travel times are fictional.</p>}
      </section>

      <section className="how-section shell" id="how-it-works" aria-labelledby="how-title"><div className="how-intro"><span className="tiny-spark"><Sparkles size={21} /></span><h2 id="how-title">Less back-and-forth.<br /><em>More “see you there.”</em></h2></div><div className="how-step"><span>01</span><h3>Give us the gist.</h3><p>Your people, your place, your idea of a good time.</p></div><div className="how-step"><span>02</span><h3>Find your kind of plan.</h3><p>Explore three options that bring it all together.</p></div><div className="how-step"><span>03</span><h3>Take it to the group chat.</h3><p>Pick a favorite. Check the real-world details. Go hang out.</p></div></section>

      <section id="about-demo" className="about-demo shell"><div><span className="status-dot" /><strong>A small demo. A big idea.</strong></div><p>Where To? is a first look at an AI-powered outing planner. This version uses local AI to help plan outings with fictional Baltimore venues. It supports everyday outings, sports, concerts, and performances. Scheduled events require a matching mock date; unclear or unsupported requests get an explanation. Live availability, verified prices, and bookings are not connected.</p><a href="#planner">Give it a go <ArrowDown size={14} /></a></section>
    </main>
    <footer className="site-footer shell"><a href="#" className="brand footer-brand">where to<span className="brand-question">?</span></a><p>Good company. Great plans. Less effort.</p><span>Made for getting together <span aria-hidden="true">↗</span></span></footer>
  </>;
}
