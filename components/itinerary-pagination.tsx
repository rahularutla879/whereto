export function ItineraryPagination({ index, count, busy, onNavigate }: {
  index:number; count:number; busy:boolean; onNavigate:(direction:-1|1)=>void;
}) {
  return <nav className="itinerary-pagination" aria-label="Itinerary pages">
    <button type="button" aria-label="Previous itinerary page" disabled={index===0||busy} onClick={()=>onNavigate(-1)}>← Previous</button>
    <span aria-live="polite">Page {index+1} of {count}</span>
    <button type="button" aria-label="Next itinerary page" disabled={index===count-1||busy} onClick={()=>onNavigate(1)}>Next →</button>
    <small>Pages stay in this tab until you edit or reload. New options require an active search session (up to ten minutes).</small>
  </nav>;
}
