import {supportedActivityGroups} from '@/lib/supported-activities';
export default function SupportedActivitiesPage(){
 return <main className="shell reference-page"><a href="/">Return to planner</a><h1>Supported activities</h1>
 <p>Start with these recognized categories, or describe another venue-based outing. Finding a place does not confirm availability or a booking.</p>
 {supportedActivityGroups().map(group=><section key={group.title} aria-label={group.title}><h2>{group.title}</h2><p>{group.scheduled?'These categories find event venues. They do not verify fixtures, performances, tickets or movie showtimes. Sports match categories do not mean a place to play or train.':'Search for places suited to these activities. Hours, prices and reservations need separate confirmation.'}</p><ul className="activity-reference-list">{group.items.map(item=><li key={item.label}>{item.label}</li>)}</ul></section>)}
 <section><h2>Other venue-based requests</h2><p>The categories above are not exhaustive. You can also describe retail brands, malls, pottery classes or other specific places. Discovery depends on relevant provider evidence; a class venue does not confirm a scheduled class.</p><p>For example: “Dinner and coffee in Jersey City tomorrow”, “Movie tomorrow in Hyderabad”, or “Zara outlet in Jersey City”. Store format is flexible unless you require outlets only; brand identity and hard geographic limits stay in effect.</p></section>
 <p>Unclear requests may need a follow-up.</p></main>;
}
