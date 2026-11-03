"use client";
import {useState} from 'react';
import {ArrowRight,ArrowUpRight,Clock3,Coffee,Footprints,MapPin,Palette,Popcorn,Sparkles,Utensils,Wine,CircleDot,X,Trophy,Music,Mic,Landmark,Theater,Laugh,Gamepad2,ShoppingBag,TreePine,Puzzle} from 'lucide-react';
import {CardArtwork} from './artwork';
import {activityLabel,formatDuration,type Activity,type Plan} from '@/lib/planner';
import {destinationLabel} from '@/lib/display-format';
import {planWarnings} from '@/lib/results-presentation';
import {GoogleCredits} from './venue-details';
import {VenueDetailsSession} from '@/lib/venue-details';
import {ItineraryStop,EndingStep} from './itinerary-stop';
import {PlanCost} from './plan-cost';
import {FirstLegTravel} from './first-leg-travel';
import {AdvancedDetails} from './advanced-plan';
const activityIcons: Partial<Record<Activity, typeof Sparkles>> = { bowling: CircleDot, drinks: Wine, movie: Popcorn, food: Utensils, coffee: Coffee, outdoors: Footprints, art: Palette, museum: Landmark, karaoke: Mic, arcade: Gamepad2, escape: Puzzle, shopping: ShoppingBag,
  hiking: TreePine, picnic: TreePine, zoo: TreePine,
  baseball: Trophy, basketball: Trophy, football: Trophy, soccer: Trophy, hockey: Trophy, sports: Trophy,
  concert: Music, theater: Theater, musical: Theater, ballet: Theater, opera: Music, comedy: Laugh,
};


export function PlanCard({ plan, index, detailsSession }: { plan: Plan; index: number; detailsSession: VenueDetailsSession }) {
  const real = plan.dataMode === "real";
  const [expanded, setExpanded] = useState(false);
  const warnings = plan.advanced ? [] : planWarnings(plan);
  const classic = plan.venues.map((venue) => venue.activity).join(",") === "bowling,drinks,movie";
  const PosterIcon = activityIcons[plan.venues[0].activity] ?? Sparkles;
  return <article className={`plan-card ${plan.theme}`}>
    <div className="card-visual">
      <span className="card-number">0{index + 1}</span><span className="demo-pill">{real ? "REAL VENUES" : plan.feasibility === "preview" ? "DEMO PLAN" : "SAMPLE PLAN"}</span>
      {real ? <div className="real-route-poster" aria-hidden="true">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <div key={venue.id}><Icon size={22} strokeWidth={1.5} /><span>{i + 1}. {venue.name}</span></div>;
      })}{plan.advanced?.ending==='origin'&&<div><MapPin size={22} strokeWidth={1.5}/><span>Return to starting point</span></div>}{plan.advanced?.endpoint&&<div><MapPin size={22} strokeWidth={1.5}/><span>{plan.advanced.endpoint.name}</span></div>}</div> : classic ? <CardArtwork theme={plan.theme} /> : <div className="activity-poster" aria-hidden="true"><PosterIcon size={62} strokeWidth={1.25} /><span>{activityLabel(plan.venues[0].activity)}</span></div>}
    </div>
    <div className="card-body">
      <p className="card-label">{plan.label}</p>
      <h3 className={real ? "real-plan-title" : undefined} title={plan.fullTitle}>{plan.title}</h3>
      <p className="card-description">{plan.description}</p>
      {plan.planningMode==="surprise"&&<p className="details-note">Surprise Me · Begins at {plan.venues[0].name}. {plan.surpriseRepeated?"This first venue has appeared before; the complete combination is different.":"A varied first venue from the checked eligible pool."} No travel from your location is included.</p>}
      {plan.travelClassification && plan.travelClassification!=="matching" && <div className="plan-warning" role="note"><strong>{{outside_preference:"Outside your preferred range",beyond_limit:"Beyond your travel limit",unverified:"Requirements not fully verified"}[plan.travelClassification]}</strong><ul>{plan.travelDeviations?.map(message=><li key={message}>{message}</li>)}</ul></div>}
      {warnings.length > 0 && <div className="plan-warning" role="note" aria-label="Important plan details"><strong>Check this option</strong><ul>{warnings.map(warning => <li key={warning}>{warning}</li>)}</ul></div>}
      {plan.advanced&&(plan.advanced.durationState==='unverified'&&plan.advanced.totalConstraint||plan.advanced.deadlineState==='unverified'&&plan.advanced.deadlineSource)&&<p className="details-note">Total time not yet verified</p>}
      <div className="activity-route">{plan.venues.map((venue, i) => {
        const Icon = activityIcons[venue.activity] ?? Sparkles;
        return <span className="route-group" key={venue.id}><span className="activity"><Icon size={14} strokeWidth={1.7} />{activityLabel(venue.activity)}</span>{i < plan.venues.length - 1 && <ArrowRight size={12} className="route-arrow" />}</span>;
      })}</div>
      <div className="card-facts"><span><MapPin size={14} /> {real ? plan.venues.length===1 ? plan.venues[0].address ?? "Address unavailable" : `Search area: ${destinationLabel(plan.location ?? "Not specified")}` : destinationLabel(plan.location ?? "Baltimore")}</span>{(!real || plan.duration !== null) && <span><Clock3 size={14} /> {plan.duration === null ? "Visit timing not verified" : `~${formatDuration(plan.duration)}`}</span>}</div>
      {plan.firstLeg && <FirstLegTravel plan={plan} />}
      <div className="card-bottom">{!real && <div><PlanCost amount={plan.price} /><small>Sample price</small></div>}<button className="plan-link" aria-expanded={expanded} aria-controls={`details-${plan.id}`} onClick={() => setExpanded(!expanded)}>{expanded ? "Close plan" : "View plan"}{expanded ? <X size={16} /> : <ArrowUpRight size={18} />}</button></div>
      {real && <GoogleCredits credits={plan.advanced ? [...plan.advanced.stops.flatMap(s=>s.credits),...(plan.advanced.endpoint?.credits??[])] : plan.venues.flatMap(venue => venue.evidenceLabels?.attribution?.third_party ?? []).filter((credit, i, credits) => credits.findIndex(c => c.provider === credit.provider && c.uri === credit.uri) === i)} />}
      <div hidden={!expanded} className="plan-details" id={`details-${plan.id}`}>
        <p className="details-heading">{real ? "Your itinerary" : "Your sample itinerary"}</p>
        <p className="details-context">{plan.date.match(/^\d{4}-\d{2}-\d{2}$/) ? new Date(`${plan.date}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : plan.date}</p>
        <ol>{plan.stops.map((_,i)=><ItineraryStop key={`${plan.stops[i].venue.id}-${i}`} plan={plan} index={i} detailsSession={detailsSession}/>)}{plan.advanced&&<EndingStep plan={plan}/>}</ol>
        {plan.advanced?<AdvancedDetails option={plan.advanced}/>:plan.stops.length>1&&<p className="details-note">{plan.travel===null?"Travel between stops unavailable":`~${plan.travel} min ${real ? plan.transport??"driving" : "simulated travel"} between stops`}. Return travel is not included.</p>}
      </div>
    </div>
  </article>;
}
